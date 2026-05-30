from __future__ import annotations

import hashlib
import json
import math
import warnings as py_warnings
from pathlib import Path
from typing import Any

import pandas as pd

from app.core.errors import AppError
from app.models.chart import ChartSpec
from app.models.insight import (
    Evidence,
    EvidenceType,
    Insight,
    InsightCategory,
    InsightSeverity,
)
from app.models.profile import ColumnProfile, ColumnRole, DatasetProfile


MAX_INSIGHTS = 12
MIN_INSIGHTS_TARGET = 8
CORRELATION_THRESHOLD = 0.65
TOP_CATEGORY_SHARE_THRESHOLD = 35.0
CONCENTRATION_SHARE_THRESHOLD = 60.0
SEGMENT_RATIO_THRESHOLD = 2.0
TREND_CHANGE_THRESHOLD = 10.0
OUTLIER_PERCENT_THRESHOLD = 2.0
SKEW_THRESHOLD = 1.25
ZERO_CONCENTRATION_THRESHOLD = 30.0


def generate_insights(
    *,
    dataset_id: str,
    artifact_path: str,
    profile: DatasetProfile,
    charts: list[ChartSpec],
) -> list[Insight]:
    dataframe = _load_dataframe(dataset_id, artifact_path)
    chart_lookup = _chart_lookup(charts)

    metrics = _metric_columns(profile)
    dimensions = _dimension_columns(profile)
    datetime_columns = _datetime_columns(profile)

    insights: list[Insight] = []
    insights.extend(_dataset_quality_insights(dataset_id, profile))
    insights.extend(_missing_data_risk_insights(dataset_id, profile))
    insights.extend(_trend_insights(dataset_id, dataframe, datetime_columns, metrics, chart_lookup))
    insights.extend(_top_category_insights(dataset_id, dataframe, dimensions, metrics, chart_lookup))
    insights.extend(_segment_difference_insights(dataset_id, dataframe, dimensions, metrics, chart_lookup))
    insights.extend(_outlier_insights(dataset_id, dataframe, metrics))
    insights.extend(_correlation_insights(dataset_id, dataframe, metrics, chart_lookup))
    insights.extend(_distribution_insights(dataset_id, dataframe, metrics))

    deduped = _dedupe_insights(insights)
    return sorted(deduped, key=_insight_sort_key)[:MAX_INSIGHTS]


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


def _dataset_quality_insights(dataset_id: str, profile: DatasetProfile) -> list[Insight]:
    insights: list[Insight] = []
    high_missing_columns = [
        column
        for column in profile.columns
        if column.missing_percentage >= 30
    ]

    if profile.duplicate_row_count > 0:
        duplicate_pct = _percentage(profile.duplicate_row_count, profile.row_count)
        severity = InsightSeverity.high if duplicate_pct >= 10 else InsightSeverity.medium
        insights.append(
            _insight(
                dataset_id=dataset_id,
                insight_type=InsightCategory.dataset_quality,
                severity=severity,
                confidence=min(0.95, 0.72 + duplicate_pct / 100),
                title="Duplicate rows may affect analysis accuracy",
                summary=f"{profile.duplicate_row_count} rows are exact duplicates, representing {duplicate_pct}% of the dataset.",
                evidence=Evidence(
                    type=EvidenceType.data_quality,
                    metric="duplicate_row_count",
                    value=profile.duplicate_row_count,
                    comparison_value=f"{duplicate_pct}% of rows",
                    rows_affected=profile.duplicate_row_count,
                    calculation="count(exact duplicate rows)",
                    explanation="Exact duplicate rows can overstate totals, counts, and segment-level comparisons if they are not intentional repeat records.",
                ),
                recommendation="Confirm whether duplicate rows are legitimate repeated events before using totals or averages in decisions.",
                related_columns=[],
            )
        )

    if high_missing_columns:
        worst = max(high_missing_columns, key=lambda column: column.missing_percentage)
        severity = InsightSeverity.high if worst.missing_percentage >= 60 else InsightSeverity.medium
        insights.append(
            _insight(
                dataset_id=dataset_id,
                insight_type=InsightCategory.dataset_quality,
                severity=severity,
                confidence=min(0.95, 0.7 + worst.missing_percentage / 200),
                title=f"{_title(worst.original_name)} has substantial missing data",
                summary=f"{_title(worst.original_name)} is missing in {worst.missing_percentage}% of rows, which may limit analysis that depends on this column.",
                evidence=Evidence(
                    type=EvidenceType.data_quality,
                    column=worst.name,
                    metric="missing_percentage",
                    value=worst.missing_percentage,
                    comparison_value="30% high-missingness threshold",
                    rows_affected=worst.missing_count,
                    calculation=f"missing_count({worst.name}) / row_count",
                    explanation="The missingness threshold is deterministic and flags columns where a large share of rows lacks usable values.",
                ),
                recommendation="Review whether the missing values are expected. If the column is important, filter affected analyses or document the limitation in the report.",
                related_columns=[worst.name],
            )
        )

    quality_warning_count = sum(len(column.warnings) for column in profile.columns) + len(profile.warnings)
    if profile.quality_score < 75 and quality_warning_count > 0:
        insights.append(
            _insight(
                dataset_id=dataset_id,
                insight_type=InsightCategory.dataset_quality,
                severity=InsightSeverity.medium if profile.quality_score >= 50 else InsightSeverity.high,
                confidence=0.78,
                title="Dataset quality needs review before executive reporting",
                summary=f"The deterministic quality score is {profile.quality_score}/100 with {quality_warning_count} quality warnings.",
                evidence=Evidence(
                    type=EvidenceType.data_quality,
                    metric="quality_score",
                    value=profile.quality_score,
                    comparison_value="75 review threshold",
                    rows_affected=profile.row_count,
                    calculation="100 minus penalties for missing cells, duplicate rows, and profile warnings",
                    explanation="The score is a deterministic summary of data quality risks detected during profiling.",
                ),
                recommendation="Resolve or document major data quality warnings before relying on the generated analysis for decisions.",
                related_columns=[column.name for column in high_missing_columns[:5]],
            )
        )

    return insights


def _missing_data_risk_insights(dataset_id: str, profile: DatasetProfile) -> list[Insight]:
    important_columns = [
        column
        for column in profile.columns
        if column.role in {ColumnRole.metric, ColumnRole.datetime, ColumnRole.dimension}
        and column.missing_percentage >= 10
    ]
    if not important_columns:
        return []

    column = max(important_columns, key=lambda item: item.missing_percentage)
    return [
        _insight(
            dataset_id=dataset_id,
            insight_type=InsightCategory.missing_data_risk,
            severity=InsightSeverity.high if column.missing_percentage >= 30 else InsightSeverity.medium,
            confidence=min(0.9, 0.65 + column.missing_percentage / 150),
            title=f"Missing {_title(column.original_name)} values may bias downstream insights",
            summary=f"{_title(column.original_name)} is missing in {column.missing_percentage}% of rows. Analyses using this column will be based on fewer records.",
            evidence=Evidence(
                type=EvidenceType.data_quality,
                column=column.name,
                metric="missing_count",
                value=column.missing_count,
                comparison_value=f"{column.missing_percentage}% missing",
                rows_affected=column.missing_count,
                calculation=f"count(null {column.name})",
                explanation="Missing values reduce the sample available for charts, correlations, and segment comparisons involving this column.",
            ),
            recommendation="Use sample-size notes when presenting findings that depend on this column, and avoid overinterpreting small segment differences.",
            related_columns=[column.name],
        )
    ]


def _trend_insights(
    dataset_id: str,
    dataframe: pd.DataFrame,
    datetime_columns: list[ColumnProfile],
    metrics: list[ColumnProfile],
    chart_lookup: dict[tuple[str, str | None, str | None, str | None], str],
) -> list[Insight]:
    if not datetime_columns or not metrics:
        return []

    datetime_column = datetime_columns[0]
    metric = metrics[0]
    frame = dataframe[[datetime_column.name, metric.name]].copy()
    with py_warnings.catch_warnings():
        py_warnings.simplefilter("ignore", UserWarning)
        frame[datetime_column.name] = pd.to_datetime(frame[datetime_column.name], errors="coerce")
    frame[metric.name] = pd.to_numeric(frame[metric.name], errors="coerce")
    frame = frame.dropna()
    if frame.empty:
        return []

    frame[datetime_column.name] = frame[datetime_column.name].dt.date
    grouped = (
        frame.groupby(datetime_column.name)[metric.name]
        .sum()
        .sort_index()
    )
    if len(grouped) < 2:
        return []

    first_value = float(grouped.iloc[0])
    last_value = float(grouped.iloc[-1])
    if first_value == 0:
        return []

    pct_change = _round((last_value - first_value) / abs(first_value) * 100)
    if abs(pct_change) < TREND_CHANGE_THRESHOLD:
        return []

    direction = "increased" if pct_change > 0 else "decreased"
    severity = InsightSeverity.medium if abs(pct_change) >= 25 else InsightSeverity.low
    chart_id = chart_lookup.get(("line", datetime_column.name, metric.name, None))

    return [
        _insight(
            dataset_id=dataset_id,
            insight_type=InsightCategory.trend,
            severity=severity,
            confidence=min(0.92, 0.7 + min(abs(pct_change), 100) / 300),
            title=f"{_title(metric.original_name)} {direction} over time",
            summary=f"{_title(metric.original_name)} {direction} from {_format_number(first_value)} in the first period to {_format_number(last_value)} in the last period, a {abs(pct_change)}% change.",
            evidence=Evidence(
                type=EvidenceType.comparison,
                column=metric.name,
                columns=[datetime_column.name, metric.name],
                metric="period_change_percentage",
                value=pct_change,
                comparison_value={
                    "first_period_value": _round(first_value),
                    "last_period_value": _round(last_value),
                },
                values={
                    "first_period": str(grouped.index[0]),
                    "last_period": str(grouped.index[-1]),
                    "slope_direction": "positive" if pct_change > 0 else "negative",
                },
                rows_affected=int(len(frame)),
                calculation=f"(last sum({metric.name}) - first sum({metric.name})) / abs(first sum({metric.name}))",
                explanation="The trend is based on aggregated metric values ordered by the detected datetime column.",
            ),
            recommendation="Check whether this movement aligns with known seasonality, campaigns, or operational changes before treating it as a durable trend.",
            related_columns=[datetime_column.name, metric.name],
            related_chart_id=chart_id,
        )
    ]


def _top_category_insights(
    dataset_id: str,
    dataframe: pd.DataFrame,
    dimensions: list[ColumnProfile],
    metrics: list[ColumnProfile],
    chart_lookup: dict[tuple[str, str | None, str | None, str | None], str],
) -> list[Insight]:
    if not dimensions:
        return []

    dimension = dimensions[0]
    metric = metrics[0] if metrics else None
    if metric is None:
        grouped = dataframe[dimension.name].dropna().value_counts()
        calculation = f"count(rows) grouped by {dimension.name}"
        chart_id = chart_lookup.get(("horizontal_bar", "count", dimension.name, None))
    else:
        frame = dataframe[[dimension.name, metric.name]].copy()
        frame[metric.name] = pd.to_numeric(frame[metric.name], errors="coerce")
        frame = frame.dropna(subset=[dimension.name, metric.name])
        grouped = frame.groupby(dimension.name)[metric.name].sum().sort_values(ascending=False)
        calculation = f"sum({metric.name}) grouped by {dimension.name}"
        chart_id = (
            chart_lookup.get(("bar", dimension.name, metric.name, None))
            or chart_lookup.get(("horizontal_bar", metric.name, dimension.name, None))
        )

    if len(grouped) < 2:
        return []
    total = float(grouped.sum())
    if total == 0:
        return []

    top_category = str(grouped.index[0])
    top_value = float(grouped.iloc[0])
    share = _round(top_value / total * 100)
    if share < TOP_CATEGORY_SHARE_THRESHOLD:
        return []

    severity = InsightSeverity.medium if share < CONCENTRATION_SHARE_THRESHOLD else InsightSeverity.high
    metric_label = _title(metric.original_name) if metric else "records"
    dimension_label = _title(dimension.original_name)
    insight_type = (
        InsightCategory.concentration
        if share >= CONCENTRATION_SHARE_THRESHOLD
        else InsightCategory.top_category
    )

    return [
        _insight(
            dataset_id=dataset_id,
            insight_type=insight_type,
            severity=severity,
            confidence=min(0.93, 0.68 + share / 250),
            title=f"{metric_label} is concentrated in {top_category}",
            summary=f"{top_category} contributes {share}% of total {metric_label} across {dimension_label}.",
            evidence=Evidence(
                type=EvidenceType.comparison,
                column=dimension.name,
                columns=[dimension.name] + ([metric.name] if metric else []),
                metric="top_category_share",
                value=share,
                comparison_value="share of total",
                values={
                    "top_category": top_category,
                    "top_value": _round(top_value),
                    "total_value": _round(total),
                },
                rows_affected=int(dataframe[dimension.name].notna().sum()),
                calculation=calculation,
                explanation="The top category share is computed directly from grouped totals and is only emitted when concentration is materially high.",
            ),
            recommendation="Review whether performance depends too heavily on this segment before making broad assumptions from aggregate results.",
            related_columns=[dimension.name] + ([metric.name] if metric else []),
            related_chart_id=chart_id,
        )
    ]


def _segment_difference_insights(
    dataset_id: str,
    dataframe: pd.DataFrame,
    dimensions: list[ColumnProfile],
    metrics: list[ColumnProfile],
    chart_lookup: dict[tuple[str, str | None, str | None, str | None], str],
) -> list[Insight]:
    if not dimensions or not metrics:
        return []

    dimension = dimensions[0]
    metric = metrics[0]
    frame = dataframe[[dimension.name, metric.name]].copy()
    frame[metric.name] = pd.to_numeric(frame[metric.name], errors="coerce")
    frame = frame.dropna(subset=[dimension.name, metric.name])
    if frame.empty:
        return []

    grouped = frame.groupby(dimension.name)[metric.name].mean().sort_values(ascending=False)
    if len(grouped) < 2:
        return []

    highest_category = str(grouped.index[0])
    lowest_category = str(grouped.index[-1])
    highest_value = float(grouped.iloc[0])
    lowest_value = float(grouped.iloc[-1])
    if lowest_value <= 0:
        return []

    ratio = _round(highest_value / lowest_value)
    if ratio < SEGMENT_RATIO_THRESHOLD:
        return []

    chart_id = chart_lookup.get(("bar", dimension.name, metric.name, None))
    severity = InsightSeverity.high if ratio >= 4 else InsightSeverity.medium

    return [
        _insight(
            dataset_id=dataset_id,
            insight_type=InsightCategory.segment_difference,
            severity=severity,
            confidence=min(0.9, 0.68 + min(ratio, 5) / 20),
            title=f"{_title(metric.original_name)} differs materially across {_title(dimension.original_name)}",
            summary=f"{highest_category} averages {_format_number(highest_value)} while {lowest_category} averages {_format_number(lowest_value)}, a {ratio}x difference.",
            evidence=Evidence(
                type=EvidenceType.comparison,
                column=metric.name,
                columns=[dimension.name, metric.name],
                metric="highest_to_lowest_mean_ratio",
                value=ratio,
                comparison_value={
                    "highest_category": highest_category,
                    "highest_mean": _round(highest_value),
                    "lowest_category": lowest_category,
                    "lowest_mean": _round(lowest_value),
                },
                rows_affected=int(len(frame)),
                calculation=f"max(mean({metric.name}) grouped by {dimension.name}) / min(mean({metric.name}) grouped by {dimension.name})",
                explanation="The difference is based on category-level means, not inferred business causality.",
            ),
            recommendation="Compare sample sizes and operational context for the highest and lowest segments before acting on this gap.",
            related_columns=[dimension.name, metric.name],
            related_chart_id=chart_id,
        )
    ]


def _outlier_insights(
    dataset_id: str,
    dataframe: pd.DataFrame,
    metrics: list[ColumnProfile],
) -> list[Insight]:
    insights: list[Insight] = []
    for metric in metrics[:4]:
        values = pd.to_numeric(dataframe[metric.name], errors="coerce").dropna()
        if len(values) < 8 or values.nunique() < 4:
            continue

        q1 = float(values.quantile(0.25))
        q3 = float(values.quantile(0.75))
        iqr = q3 - q1
        if iqr <= 0:
            continue
        lower_bound = q1 - 1.5 * iqr
        upper_bound = q3 + 1.5 * iqr
        outliers = values[(values < lower_bound) | (values > upper_bound)]
        outlier_count = int(len(outliers))
        outlier_pct = _percentage(outlier_count, len(values))
        if outlier_count == 0 or outlier_pct < OUTLIER_PERCENT_THRESHOLD:
            continue

        insights.append(
            _insight(
                dataset_id=dataset_id,
                insight_type=InsightCategory.outlier,
                severity=InsightSeverity.medium if outlier_pct < 10 else InsightSeverity.high,
                confidence=min(0.92, 0.7 + outlier_pct / 100),
                title=f"{_title(metric.original_name)} contains outliers",
                summary=f"{outlier_count} {_title(metric.original_name)} values ({outlier_pct}% of valid rows) fall outside the IQR outlier range.",
                evidence=Evidence(
                    type=EvidenceType.outlier,
                    column=metric.name,
                    metric="iqr_outlier_count",
                    value=outlier_count,
                    comparison_value={
                        "lower_bound": _round(lower_bound),
                        "upper_bound": _round(upper_bound),
                    },
                    rows_affected=outlier_count,
                    calculation=f"values below Q1 - 1.5*IQR or above Q3 + 1.5*IQR for {metric.name}",
                    explanation="The IQR rule is deterministic and flags values far from the central distribution.",
                ),
                recommendation="Inspect the outlier records before using averages or totals; they may be valid exceptional events or data quality issues.",
                related_columns=[metric.name],
            )
        )

    return insights[:2]


def _correlation_insights(
    dataset_id: str,
    dataframe: pd.DataFrame,
    metrics: list[ColumnProfile],
    chart_lookup: dict[tuple[str, str | None, str | None, str | None], str],
) -> list[Insight]:
    if len(metrics) < 2:
        return []

    metric_names = [metric.name for metric in metrics[:8]]
    metric_by_name = {metric.name: metric for metric in metrics}
    numeric_frame = dataframe[metric_names].apply(pd.to_numeric, errors="coerce")
    correlation = numeric_frame.corr(method="pearson")

    pairs: list[tuple[str, str, float]] = []
    for index, left in enumerate(metric_names):
        for right in metric_names[index + 1:]:
            value = correlation.loc[left, right]
            if pd.isna(value) or abs(float(value)) < CORRELATION_THRESHOLD:
                continue
            pairs.append((left, right, float(value)))

    if not pairs:
        return []

    strongest_positive = max((pair for pair in pairs if pair[2] > 0), key=lambda item: item[2], default=None)
    strongest_negative = min((pair for pair in pairs if pair[2] < 0), key=lambda item: item[2], default=None)

    insights: list[Insight] = []
    for pair, direction in ((strongest_positive, "positive"), (strongest_negative, "negative")):
        if pair is None:
            continue
        left, right, coefficient = pair
        left_label = _title(metric_by_name[left].original_name)
        right_label = _title(metric_by_name[right].original_name)
        insights.append(
            _insight(
                dataset_id=dataset_id,
                insight_type=InsightCategory.correlation,
                severity=InsightSeverity.medium if abs(coefficient) < 0.85 else InsightSeverity.high,
                confidence=min(0.94, 0.6 + abs(coefficient) * 0.35),
                title=f"{left_label} and {right_label} have a strong {direction} correlation",
                summary=f"The Pearson correlation between {left_label} and {right_label} is {_round(coefficient)}.",
                evidence=Evidence(
                    type=EvidenceType.correlation,
                    column=left,
                    columns=[left, right],
                    metric="pearson_correlation",
                    value=_round(coefficient),
                    comparison_value=f"absolute threshold {CORRELATION_THRESHOLD}",
                    rows_affected=int(numeric_frame[[left, right]].dropna().shape[0]),
                    calculation=f"pearson_corr({left}, {right})",
                    explanation="Correlation is computed from paired numeric rows and does not imply causation.",
                ),
                recommendation="Use this relationship as a signal for further investigation, not as proof that one metric causes the other.",
                related_columns=[left, right],
                related_chart_id=(
                    chart_lookup.get(("scatter", left, right, None))
                    or chart_lookup.get(("scatter", right, left, None))
                    or chart_lookup.get(("correlation_heatmap", "metric_x", "metric_y", None))
                ),
            )
        )

    return insights


def _distribution_insights(
    dataset_id: str,
    dataframe: pd.DataFrame,
    metrics: list[ColumnProfile],
) -> list[Insight]:
    insights: list[Insight] = []
    for metric in metrics[:4]:
        values = pd.to_numeric(dataframe[metric.name], errors="coerce").dropna()
        if len(values) < 8 or values.nunique() < 4:
            continue

        skew = float(values.skew())
        mean = float(values.mean())
        std = float(values.std(ddof=0))
        zero_share = _percentage(int((values == 0).sum()), len(values))

        if abs(skew) >= SKEW_THRESHOLD:
            direction = "right-skewed" if skew > 0 else "left-skewed"
            insights.append(
                _insight(
                    dataset_id=dataset_id,
                    insight_type=InsightCategory.distribution,
                    severity=InsightSeverity.medium,
                    confidence=min(0.88, 0.62 + min(abs(skew), 4) / 10),
                    title=f"{_title(metric.original_name)} is {direction}",
                    summary=f"{_title(metric.original_name)} has skew of {_round(skew)}, meaning the distribution is not balanced around the average.",
                    evidence=Evidence(
                        type=EvidenceType.distribution,
                        column=metric.name,
                        metric="skew",
                        value=_round(skew),
                        comparison_value=f"absolute threshold {SKEW_THRESHOLD}",
                        rows_affected=int(len(values)),
                        calculation=f"skew({metric.name})",
                        explanation="Skew is computed from valid numeric values and flags asymmetric distributions.",
                    ),
                    recommendation="Use medians or percentile views alongside averages when presenting this metric.",
                    related_columns=[metric.name],
                )
            )
            continue

        if mean != 0:
            coefficient_of_variation = abs(std / mean)
            if coefficient_of_variation >= 1.5:
                insights.append(
                    _insight(
                        dataset_id=dataset_id,
                        insight_type=InsightCategory.distribution,
                        severity=InsightSeverity.medium,
                        confidence=min(0.86, 0.6 + min(coefficient_of_variation, 3) / 10),
                        title=f"{_title(metric.original_name)} varies widely",
                        summary=f"The standard deviation is {_round(std)} against a mean of {_round(mean)}, a coefficient of variation of {_round(coefficient_of_variation)}.",
                        evidence=Evidence(
                            type=EvidenceType.distribution,
                            column=metric.name,
                            metric="coefficient_of_variation",
                            value=_round(coefficient_of_variation),
                            comparison_value="1.5 high-variance threshold",
                            rows_affected=int(len(values)),
                            calculation=f"std({metric.name}) / abs(mean({metric.name}))",
                            explanation="High relative variation means averages may hide materially different records or segments.",
                        ),
                        recommendation="Compare this metric by segment or inspect percentiles before relying on the mean.",
                        related_columns=[metric.name],
                    )
                )
                continue

        if zero_share >= ZERO_CONCENTRATION_THRESHOLD:
            insights.append(
                _insight(
                    dataset_id=dataset_id,
                    insight_type=InsightCategory.distribution,
                    severity=InsightSeverity.low,
                    confidence=min(0.85, 0.58 + zero_share / 200),
                    title=f"{_title(metric.original_name)} is often zero",
                    summary=f"{zero_share}% of valid {_title(metric.original_name)} values are zero.",
                    evidence=Evidence(
                        type=EvidenceType.distribution,
                        column=metric.name,
                        metric="zero_share",
                        value=zero_share,
                        comparison_value=f"{ZERO_CONCENTRATION_THRESHOLD}% threshold",
                        rows_affected=int((values == 0).sum()),
                        calculation=f"count({metric.name} = 0) / count(valid {metric.name})",
                        explanation="A large zero share can affect averages and may indicate a meaningful inactive or no-activity segment.",
                    ),
                    recommendation="Separate zero and non-zero records when comparing averages or segment performance.",
                    related_columns=[metric.name],
                )
            )

    return insights[:2]


def _metric_columns(profile: DatasetProfile) -> list[ColumnProfile]:
    return sorted(
        [
            column
            for column in profile.columns
            if column.role == ColumnRole.metric
            and column.name not in profile.id_like_columns
            and column.unique_count > 1
            and column.missing_percentage < 80
            and (column.std is None or column.std > 0)
        ],
        key=_metric_sort_key,
    )


def _dimension_columns(profile: DatasetProfile) -> list[ColumnProfile]:
    return sorted(
        [
            column
            for column in profile.columns
            if column.role == ColumnRole.dimension
            and column.name not in profile.id_like_columns
            and 1 < column.unique_count
            and column.missing_percentage < 80
        ],
        key=_dimension_sort_key,
    )


def _datetime_columns(profile: DatasetProfile) -> list[ColumnProfile]:
    return [
        column
        for column in profile.columns
        if column.role == ColumnRole.datetime and column.missing_percentage < 80
    ]


def _chart_lookup(charts: list[ChartSpec]) -> dict[tuple[str, str | None, str | None, str | None], str]:
    return {
        (chart.chart_type.value, chart.x_column, chart.y_column, chart.group_by): chart.id
        for chart in charts
    }


def _insight(
    *,
    dataset_id: str,
    insight_type: InsightCategory,
    severity: InsightSeverity,
    confidence: float,
    title: str,
    summary: str,
    evidence: Evidence,
    recommendation: str,
    related_columns: list[str],
    related_chart_id: str | None = None,
) -> Insight:
    insight_id = _insight_id(dataset_id, insight_type.value, title, related_columns)
    return Insight(
        id=insight_id,
        dataset_id=dataset_id,
        title=title,
        summary=summary,
        insight_type=insight_type,
        severity=severity,
        confidence=_round_confidence(confidence),
        evidence=evidence,
        recommendation=recommendation,
        related_columns=related_columns,
        related_chart_id=related_chart_id,
    )


def _insight_id(
    dataset_id: str,
    insight_type: str,
    title: str,
    related_columns: list[str],
) -> str:
    digest = hashlib.sha1(
        f"{dataset_id}:{insight_type}:{title}:{','.join(related_columns)}".encode("utf-8")
    ).hexdigest()[:16]
    return f"ins_{digest}"


def _dedupe_insights(insights: list[Insight]) -> list[Insight]:
    seen: set[tuple[str, tuple[str, ...], str]] = set()
    deduped: list[Insight] = []
    for insight in insights:
        key = (
            insight.insight_type.value,
            tuple(sorted(insight.related_columns)),
            insight.evidence.metric,
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(insight)
    return deduped


def _insight_sort_key(insight: Insight) -> tuple[int, float, str]:
    severity_rank = {
        InsightSeverity.high: 0,
        InsightSeverity.medium: 1,
        InsightSeverity.low: 2,
    }
    return (severity_rank[insight.severity], -insight.confidence, insight.title)


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


def _percentage(numerator: int | float, denominator: int | float) -> float:
    if denominator <= 0:
        return 0.0
    return _round(float(numerator) / float(denominator) * 100)


def _round(value: Any) -> int | float:
    numeric = float(value)
    if not math.isfinite(numeric):
        return 0
    if numeric.is_integer():
        return int(numeric)
    return round(numeric, 2)


def _round_confidence(value: float) -> float:
    return round(max(0.0, min(1.0, value)), 2)


def _format_number(value: float) -> str:
    rounded = _round(value)
    return f"{rounded:,}" if isinstance(rounded, int) else f"{rounded:,.2f}"


def _title(value: str) -> str:
    return value.replace("_", " ").strip().title()
