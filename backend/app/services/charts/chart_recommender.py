from __future__ import annotations

import hashlib
import json
import math
import warnings as py_warnings
from pathlib import Path
from typing import Any

import pandas as pd

from app.core.errors import AppError
from app.models.chart import ChartSpec, ChartType
from app.models.profile import ColumnProfile, ColumnRole, DatasetProfile


MAX_RECOMMENDATIONS = 8
TOP_CATEGORY_LIMIT = 10
MAX_SCATTER_POINTS = 500


def recommend_charts(
    *,
    dataset_id: str,
    artifact_path: str,
    profile: DatasetProfile,
) -> list[ChartSpec]:
    dataframe = _load_dataframe(dataset_id, artifact_path)

    metrics = _metric_columns(profile)
    dimensions = _dimension_columns(profile)
    datetime_columns = _datetime_columns(profile)

    chart_specs: list[ChartSpec] = []

    chart_specs.extend(_time_series_charts(dataset_id, dataframe, datetime_columns, metrics))
    chart_specs.extend(_bar_charts(dataset_id, dataframe, dimensions, metrics))
    chart_specs.extend(_concentration_charts(dataset_id, dataframe, dimensions, metrics))
    chart_specs.extend(_histogram_charts(dataset_id, dataframe, metrics))
    chart_specs.extend(_scatter_charts(dataset_id, dataframe, metrics))
    chart_specs.extend(_correlation_heatmap_charts(dataset_id, dataframe, metrics))
    chart_specs.extend(_box_plot_charts(dataset_id, dataframe, dimensions, metrics))
    chart_specs.extend(_stacked_bar_charts(dataset_id, dataframe, dimensions, metrics))

    deduped = _dedupe_chart_specs(chart_specs)
    return sorted(deduped, key=lambda chart: (chart.priority, chart.title))[
        :MAX_RECOMMENDATIONS
    ]


def _load_dataframe(dataset_id: str, artifact_path: str) -> pd.DataFrame:
    path = Path(artifact_path)
    if not path.exists():
        raise AppError(
            status_code=410,
            code="DATASET_ARTIFACT_MISSING",
            message="The parsed dataset artifact is missing.",
            technical_detail=f"Expected parsed artifact at {artifact_path}.",
            suggested_fix="Upload the dataset again so InsightPilot can recreate the parsed artifact.",
        )

    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("dataset_id") != dataset_id:
        raise AppError(
            status_code=409,
            code="DATASET_ARTIFACT_MISMATCH",
            message="The parsed dataset artifact does not match the requested dataset.",
            technical_detail=f"Artifact dataset_id is {payload.get('dataset_id')!r}; requested {dataset_id!r}.",
            suggested_fix="Upload the dataset again to recreate a consistent local artifact.",
        )

    column_names = [column["name"] for column in payload.get("columns", [])]
    return pd.DataFrame(payload.get("rows", []), columns=column_names)


def _metric_columns(profile: DatasetProfile) -> list[ColumnProfile]:
    metrics = [
        column
        for column in profile.columns
        if column.role == ColumnRole.metric
        and column.name not in profile.id_like_columns
        and column.unique_count > 1
        and column.missing_percentage < 80
        and (column.std is None or column.std > 0)
    ]
    return sorted(metrics, key=_metric_sort_key)


def _dimension_columns(profile: DatasetProfile) -> list[ColumnProfile]:
    dimensions = [
        column
        for column in profile.columns
        if column.role == ColumnRole.dimension
        and column.name not in profile.id_like_columns
        and 1 < column.unique_count
        and column.missing_percentage < 80
    ]
    return sorted(dimensions, key=_dimension_sort_key)


def _datetime_columns(profile: DatasetProfile) -> list[ColumnProfile]:
    return [
        column
        for column in profile.columns
        if column.role == ColumnRole.datetime and column.missing_percentage < 80
    ]


def _time_series_charts(
    dataset_id: str,
    dataframe: pd.DataFrame,
    datetime_columns: list[ColumnProfile],
    metrics: list[ColumnProfile],
) -> list[ChartSpec]:
    if not datetime_columns or not metrics:
        return []

    datetime_column = datetime_columns[0]
    metric = metrics[0]
    chart_data = _time_series_data(dataframe, datetime_column.name, metric.name)
    if len(chart_data) < 2:
        return []

    return [
        _chart_spec(
            dataset_id=dataset_id,
            chart_type=ChartType.line,
            title=f"{_title(metric.original_name)} over time",
            x_column=datetime_column.name,
            y_column=metric.name,
            group_by=None,
            description=f"Tracks {_label(metric)} by {_label(datetime_column)}.",
            reasoning="A datetime column and a numeric metric support a time series view, which is often the fastest way to spot trend, seasonality, or sudden changes.",
            priority=1,
            chart_data=chart_data,
        )
    ]


def _bar_charts(
    dataset_id: str,
    dataframe: pd.DataFrame,
    dimensions: list[ColumnProfile],
    metrics: list[ColumnProfile],
) -> list[ChartSpec]:
    if not dimensions or not metrics:
        return []

    charts: list[ChartSpec] = []
    for dimension in dimensions[:2]:
        metric = metrics[0]
        chart_data = _top_category_metric_data(
            dataframe,
            dimension.name,
            metric.name,
            top_n=TOP_CATEGORY_LIMIT,
        )
        if len(chart_data) < 2:
            continue
        charts.append(
            _chart_spec(
                dataset_id=dataset_id,
                chart_type=ChartType.bar,
                title=f"{_title(metric.original_name)} by {_title(dimension.original_name)}",
                x_column=dimension.name,
                y_column=metric.name,
                group_by=None,
                description=f"Compares {_label(metric)} across top {_label(dimension)} values.",
                reasoning="A categorical dimension and numeric metric support an aggregated bar chart. Categories are sorted by aggregate value and limited to top values to avoid noisy charts.",
                priority=2 + len(charts),
                chart_data=chart_data,
            )
        )
    return charts


def _concentration_charts(
    dataset_id: str,
    dataframe: pd.DataFrame,
    dimensions: list[ColumnProfile],
    metrics: list[ColumnProfile],
) -> list[ChartSpec]:
    charts: list[ChartSpec] = []
    for dimension in dimensions[:2]:
        if metrics:
            metric = metrics[0]
            chart_data = _top_category_metric_data(
                dataframe,
                dimension.name,
                metric.name,
                top_n=TOP_CATEGORY_LIMIT,
            )
            value_column = metric.name
            title_metric = _title(metric.original_name)
            reasoning_metric = "aggregate metric value"
        else:
            chart_data = _top_category_count_data(
                dataframe,
                dimension.name,
                top_n=TOP_CATEGORY_LIMIT,
            )
            value_column = "count"
            title_metric = "Record Count"
            reasoning_metric = "record count"

        if len(chart_data) < 2 or not _has_meaningful_concentration(chart_data, value_column):
            continue

        charts.append(
            _chart_spec(
                dataset_id=dataset_id,
                chart_type=ChartType.horizontal_bar,
                title=f"Top {_title(dimension.original_name)} concentration",
                x_column=value_column,
                y_column=dimension.name,
                group_by=None,
                description=f"Highlights where {title_metric} is concentrated across {_label(dimension)}.",
                reasoning=f"The top categories represent a meaningful share of {reasoning_metric}, so a ranked horizontal bar chart can reveal concentration or dependency.",
                priority=4 + len(charts),
                chart_data=chart_data,
            )
        )
    return charts[:1]


def _histogram_charts(
    dataset_id: str,
    dataframe: pd.DataFrame,
    metrics: list[ColumnProfile],
) -> list[ChartSpec]:
    charts: list[ChartSpec] = []
    for metric in metrics[:2]:
        chart_data = _histogram_data(dataframe, metric.name)
        if len(chart_data) < 2:
            continue
        charts.append(
            _chart_spec(
                dataset_id=dataset_id,
                chart_type=ChartType.histogram,
                title=f"{_title(metric.original_name)} distribution",
                x_column="bin",
                y_column="count",
                group_by=None,
                description=f"Shows the distribution of {_label(metric)} values.",
                reasoning="A histogram helps identify spread, skew, and unusual concentrations in a numeric metric.",
                priority=5 + len(charts),
                chart_data=chart_data,
            )
        )
    return charts[:1]


def _scatter_charts(
    dataset_id: str,
    dataframe: pd.DataFrame,
    metrics: list[ColumnProfile],
) -> list[ChartSpec]:
    if len(metrics) < 2:
        return []

    x_metric, y_metric = metrics[0], metrics[1]
    chart_data = _scatter_data(dataframe, x_metric.name, y_metric.name)
    if len(chart_data) < 5:
        return []

    return [
        _chart_spec(
            dataset_id=dataset_id,
            chart_type=ChartType.scatter,
            title=f"{_title(y_metric.original_name)} vs {_title(x_metric.original_name)}",
            x_column=x_metric.name,
            y_column=y_metric.name,
            group_by=None,
            description=f"Compares {_label(y_metric)} against {_label(x_metric)} row by row.",
            reasoning="Two numeric metrics with meaningful variation support a scatter plot for spotting relationships, clusters, and outliers.",
            priority=6,
            chart_data=chart_data,
        )
    ]


def _correlation_heatmap_charts(
    dataset_id: str,
    dataframe: pd.DataFrame,
    metrics: list[ColumnProfile],
) -> list[ChartSpec]:
    if len(metrics) < 3:
        return []

    metric_names = [metric.name for metric in metrics[:6]]
    chart_data = _correlation_heatmap_data(dataframe, metric_names)
    if len(chart_data) < 9:
        return []

    return [
        _chart_spec(
            dataset_id=dataset_id,
            chart_type=ChartType.correlation_heatmap,
            title="Metric correlation heatmap",
            x_column="metric_x",
            y_column="metric_y",
            group_by=None,
            description="Shows pairwise correlation strength across numeric metrics.",
            reasoning="At least three numeric metrics are available, so a correlation heatmap can quickly surface strong positive or negative relationships.",
            priority=7,
            chart_data=chart_data,
        )
    ]


def _box_plot_charts(
    dataset_id: str,
    dataframe: pd.DataFrame,
    dimensions: list[ColumnProfile],
    metrics: list[ColumnProfile],
) -> list[ChartSpec]:
    if not dimensions or not metrics:
        return []

    dimension = next((item for item in dimensions if 2 <= item.unique_count <= 10), None)
    if dimension is None:
        return []

    metric = metrics[0]
    chart_data = _box_plot_data(dataframe, dimension.name, metric.name)
    if len(chart_data) < 2:
        return []

    return [
        _chart_spec(
            dataset_id=dataset_id,
            chart_type=ChartType.box_plot,
            title=f"{_title(metric.original_name)} spread by {_title(dimension.original_name)}",
            x_column=dimension.name,
            y_column=metric.name,
            group_by=None,
            description=f"Compares {_label(metric)} distribution across {_label(dimension)} groups.",
            reasoning="A box plot is feasible because the grouping column has a manageable number of categories and the metric has enough numeric observations.",
            priority=8,
            chart_data=chart_data,
        )
    ]


def _stacked_bar_charts(
    dataset_id: str,
    dataframe: pd.DataFrame,
    dimensions: list[ColumnProfile],
    metrics: list[ColumnProfile],
) -> list[ChartSpec]:
    if len(dimensions) < 2 or not metrics:
        return []

    primary = next((item for item in dimensions if 2 <= item.unique_count <= 8), None)
    secondary = next(
        (item for item in dimensions if item.name != primary.name and 2 <= item.unique_count <= 6),
        None,
    ) if primary else None
    if primary is None or secondary is None:
        return []

    metric = metrics[0]
    chart_data = _stacked_bar_data(dataframe, primary.name, secondary.name, metric.name)
    if len(chart_data) < 2:
        return []

    return [
        _chart_spec(
            dataset_id=dataset_id,
            chart_type=ChartType.stacked_bar,
            title=f"{_title(metric.original_name)} by {_title(primary.original_name)} and {_title(secondary.original_name)}",
            x_column=primary.name,
            y_column=metric.name,
            group_by=secondary.name,
            description=f"Breaks down {_label(metric)} by {_label(primary)} and {_label(secondary)}.",
            reasoning="Two manageable categorical dimensions and one numeric metric support a stacked bar chart without overwhelming the reader.",
            priority=9,
            chart_data=chart_data,
        )
    ]


def _time_series_data(
    dataframe: pd.DataFrame,
    datetime_column: str,
    metric_column: str,
) -> list[dict[str, object]]:
    frame = dataframe[[datetime_column, metric_column]].copy()
    with py_warnings.catch_warnings():
        py_warnings.simplefilter("ignore", UserWarning)
        frame[datetime_column] = pd.to_datetime(
            frame[datetime_column],
            errors="coerce",
        )
    frame[metric_column] = pd.to_numeric(frame[metric_column], errors="coerce")
    frame = frame.dropna()
    if frame.empty:
        return []

    frame[datetime_column] = frame[datetime_column].dt.strftime("%Y-%m-%d")
    grouped = (
        frame.groupby(datetime_column, as_index=False)[metric_column]
        .sum()
        .sort_values(datetime_column)
    )
    return _records(grouped)


def _top_category_metric_data(
    dataframe: pd.DataFrame,
    dimension_column: str,
    metric_column: str,
    *,
    top_n: int,
) -> list[dict[str, object]]:
    frame = dataframe[[dimension_column, metric_column]].copy()
    frame[metric_column] = pd.to_numeric(frame[metric_column], errors="coerce")
    frame = frame.dropna(subset=[dimension_column, metric_column])
    if frame.empty:
        return []

    grouped = (
        frame.groupby(dimension_column, dropna=True)[metric_column]
        .sum()
        .sort_values(ascending=False)
    )
    top = grouped.head(top_n).reset_index()
    if len(grouped) > top_n:
        other_value = grouped.iloc[top_n:].sum()
        other = pd.DataFrame([{dimension_column: "Other", metric_column: other_value}])
        top = pd.concat([top, other], ignore_index=True)
    return _records(top)


def _top_category_count_data(
    dataframe: pd.DataFrame,
    dimension_column: str,
    *,
    top_n: int,
) -> list[dict[str, object]]:
    series = dataframe[dimension_column].dropna()
    if series.empty:
        return []

    grouped = series.value_counts().head(top_n).reset_index()
    grouped.columns = [dimension_column, "count"]
    return _records(grouped)


def _histogram_data(dataframe: pd.DataFrame, metric_column: str) -> list[dict[str, object]]:
    values = pd.to_numeric(dataframe[metric_column], errors="coerce").dropna()
    if len(values) < 5 or values.nunique() < 3:
        return []

    bins = min(10, max(3, int(math.sqrt(len(values)))))
    bucketed = pd.cut(values, bins=bins, duplicates="drop")
    counts = bucketed.value_counts(sort=False)
    records: list[dict[str, object]] = []
    for interval, count in counts.items():
        if count <= 0:
            continue
        records.append(
            {
                "bin": f"{_round(interval.left)} - {_round(interval.right)}",
                "bin_start": _round(interval.left),
                "bin_end": _round(interval.right),
                "count": int(count),
            }
        )
    return records


def _scatter_data(
    dataframe: pd.DataFrame,
    x_column: str,
    y_column: str,
) -> list[dict[str, object]]:
    frame = dataframe[[x_column, y_column]].copy()
    frame[x_column] = pd.to_numeric(frame[x_column], errors="coerce")
    frame[y_column] = pd.to_numeric(frame[y_column], errors="coerce")
    frame = frame.dropna()
    if frame[x_column].nunique() < 2 or frame[y_column].nunique() < 2:
        return []
    return _records(frame.head(MAX_SCATTER_POINTS))


def _correlation_heatmap_data(
    dataframe: pd.DataFrame,
    metric_columns: list[str],
) -> list[dict[str, object]]:
    numeric_frame = dataframe[metric_columns].apply(pd.to_numeric, errors="coerce")
    if len(numeric_frame.dropna(how="all")) < 3:
        return []
    correlation = numeric_frame.corr(method="pearson")

    records: list[dict[str, object]] = []
    for x_column in metric_columns:
        for y_column in metric_columns:
            value = correlation.loc[y_column, x_column]
            if pd.isna(value):
                continue
            records.append(
                {
                    "metric_x": x_column,
                    "metric_y": y_column,
                    "correlation": _round(float(value)),
                }
            )
    return records


def _box_plot_data(
    dataframe: pd.DataFrame,
    dimension_column: str,
    metric_column: str,
) -> list[dict[str, object]]:
    frame = dataframe[[dimension_column, metric_column]].copy()
    frame[metric_column] = pd.to_numeric(frame[metric_column], errors="coerce")
    frame = frame.dropna(subset=[dimension_column, metric_column])
    if frame.empty:
        return []

    records: list[dict[str, object]] = []
    for dimension_value, group in frame.groupby(dimension_column):
        values = group[metric_column].dropna()
        if len(values) < 2:
            continue
        records.append(
            {
                dimension_column: _json_safe_value(dimension_value),
                "min": _round(values.min()),
                "q1": _round(values.quantile(0.25)),
                "median": _round(values.median()),
                "q3": _round(values.quantile(0.75)),
                "max": _round(values.max()),
                "count": int(len(values)),
            }
        )
    return records


def _stacked_bar_data(
    dataframe: pd.DataFrame,
    primary_dimension: str,
    secondary_dimension: str,
    metric_column: str,
) -> list[dict[str, object]]:
    frame = dataframe[[primary_dimension, secondary_dimension, metric_column]].copy()
    frame[metric_column] = pd.to_numeric(frame[metric_column], errors="coerce")
    frame = frame.dropna(subset=[primary_dimension, secondary_dimension, metric_column])
    if frame.empty:
        return []

    pivot = frame.pivot_table(
        index=primary_dimension,
        columns=secondary_dimension,
        values=metric_column,
        aggfunc="sum",
        fill_value=0,
    )
    pivot["_total"] = pivot.sum(axis=1)
    pivot = pivot.sort_values("_total", ascending=False).head(TOP_CATEGORY_LIMIT)
    pivot = pivot.drop(columns=["_total"]).reset_index()
    return _records(pivot)


def _has_meaningful_concentration(
    chart_data: list[dict[str, object]],
    value_column: str,
) -> bool:
    values = [
        float(row.get(value_column, 0))
        for row in chart_data
        if isinstance(row.get(value_column, 0), int | float)
    ]
    total = sum(values)
    if total <= 0 or len(values) < 2:
        return False
    return max(values) / total >= 0.3


def _chart_spec(
    *,
    dataset_id: str,
    chart_type: ChartType,
    title: str,
    x_column: str | None,
    y_column: str | None,
    group_by: str | None,
    description: str,
    reasoning: str,
    priority: int,
    chart_data: list[dict[str, object]],
) -> ChartSpec:
    chart_id = _chart_id(dataset_id, chart_type.value, x_column, y_column, group_by)
    return ChartSpec(
        id=chart_id,
        dataset_id=dataset_id,
        chart_type=chart_type,
        title=title,
        x_column=x_column,
        y_column=y_column,
        group_by=group_by,
        description=description,
        reasoning=reasoning,
        priority=priority,
        chart_data=chart_data,
    )


def _chart_id(
    dataset_id: str,
    chart_type: str,
    x_column: str | None,
    y_column: str | None,
    group_by: str | None,
) -> str:
    digest = hashlib.sha1(
        f"{dataset_id}:{chart_type}:{x_column}:{y_column}:{group_by}".encode("utf-8")
    ).hexdigest()[:16]
    return f"chart_{digest}"


def _dedupe_chart_specs(chart_specs: list[ChartSpec]) -> list[ChartSpec]:
    seen: set[tuple[str, str | None, str | None, str | None]] = set()
    deduped: list[ChartSpec] = []
    for chart in chart_specs:
        if len(chart.chart_data) < 2:
            continue
        key = (chart.chart_type.value, chart.x_column, chart.y_column, chart.group_by)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(chart)
    return deduped


def _metric_sort_key(column: ColumnProfile) -> tuple[int, float, str]:
    business_terms = (
        "revenue",
        "sales",
        "profit",
        "amount",
        "cost",
        "margin",
        "price",
        "total",
        "units",
        "quantity",
    )
    label = f"{column.name} {column.original_name}".lower()
    return (_term_rank(label, business_terms), column.missing_percentage, column.name)


def _dimension_sort_key(column: ColumnProfile) -> tuple[int, float, str]:
    business_terms = ("region", "category", "product", "segment", "market", "channel")
    label = f"{column.name} {column.original_name}".lower()
    return (_term_rank(label, business_terms), column.unique_percentage, column.name)


def _term_rank(label: str, terms: tuple[str, ...]) -> int:
    for index, term in enumerate(terms):
        if term in label:
            return index
    return len(terms)


def _records(dataframe: pd.DataFrame) -> list[dict[str, object]]:
    rows = json.loads(dataframe.to_json(orient="records", date_format="iso"))
    return [_json_safe_row(row) for row in rows] if isinstance(rows, list) else []


def _json_safe_row(row: dict[str, object]) -> dict[str, object]:
    return {key: _json_safe_value(value) for key, value in row.items()}


def _json_safe_value(value: Any) -> Any:
    if pd.isna(value):
        return None
    if hasattr(value, "item"):
        value = value.item()
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, float):
        return _round(value)
    return value


def _round(value: Any) -> int | float:
    numeric = float(value)
    if numeric.is_integer():
        return int(numeric)
    return round(numeric, 6)


def _label(column: ColumnProfile) -> str:
    return column.original_name or column.name


def _title(value: str) -> str:
    return value.replace("_", " ").strip().title()
