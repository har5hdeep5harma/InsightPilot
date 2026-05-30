from __future__ import annotations

import json
import math
import re
import warnings as py_warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from app.core.errors import AppError
from app.models.common import AnalysisWarning
from app.models.profile import (
    ColumnProfile,
    ColumnRole,
    DatasetProfile,
    InferredType,
    TopValue,
)
from app.models.upload import DatasetColumn


HIGH_MISSING_THRESHOLD = 30.0
MOSTLY_MISSING_THRESHOLD = 80.0
DATETIME_CONFIDENCE_THRESHOLD = 0.85
SUSPICIOUS_DATETIME_THRESHOLD = 0.35
NUMERIC_TEXT_CONFIDENCE_THRESHOLD = 0.9
BOOLEAN_CONFIDENCE_THRESHOLD = 0.95
ID_UNIQUE_THRESHOLD = 95.0
HIGH_CARDINALITY_THRESHOLD = 80.0
LOW_CARDINALITY_MAX_UNIQUE = 20
LONG_TEXT_AVG_LENGTH = 50
LONG_TEXT_MAX_LENGTH = 120


@dataclass(frozen=True)
class LoadedDatasetArtifact:
    columns: list[DatasetColumn]
    dataframe: pd.DataFrame


def profile_dataset_artifact(dataset_id: str, artifact_path: str) -> DatasetProfile:
    artifact = _load_dataset_artifact(dataset_id, artifact_path)
    dataframe = artifact.dataframe
    row_count = int(len(dataframe.index))
    column_count = int(len(dataframe.columns))
    duplicate_row_count = int(dataframe.duplicated().sum())
    memory_usage = int(dataframe.memory_usage(deep=True).sum())

    column_profiles: list[ColumnProfile] = []
    dataset_warnings: list[AnalysisWarning] = []

    for column in artifact.columns:
        column_profiles.append(_profile_column(dataframe[column.name], column, row_count))

    numeric_columns = [
        profile.name
        for profile in column_profiles
        if profile.inferred_type == InferredType.numeric
    ]
    categorical_columns = [
        profile.name
        for profile in column_profiles
        if profile.inferred_type in {InferredType.categorical, InferredType.boolean}
    ]
    datetime_columns = [
        profile.name
        for profile in column_profiles
        if profile.inferred_type == InferredType.datetime
    ]
    id_like_columns = [
        profile.name for profile in column_profiles if profile.role == ColumnRole.id
    ]
    text_columns = [
        profile.name for profile in column_profiles if profile.role == ColumnRole.text
    ]

    if duplicate_row_count > 0:
        duplicate_percentage = _percentage(duplicate_row_count, row_count)
        dataset_warnings.append(
            AnalysisWarning(
                code="DUPLICATE_ROWS",
                message="The dataset contains duplicate rows.",
                details={
                    "duplicate_row_count": duplicate_row_count,
                    "duplicate_percentage": duplicate_percentage,
                },
            )
        )

    missing_cells = int(dataframe.isna().sum().sum())
    total_cells = row_count * column_count
    missing_cell_percentage = _percentage(missing_cells, total_cells)
    column_warning_count = sum(len(profile.warnings) for profile in column_profiles)
    quality_score = _quality_score(
        missing_cell_percentage=missing_cell_percentage,
        duplicate_percentage=_percentage(duplicate_row_count, row_count),
        warning_count=column_warning_count + len(dataset_warnings),
    )

    return DatasetProfile(
        dataset_id=dataset_id,
        row_count=row_count,
        column_count=column_count,
        duplicate_row_count=duplicate_row_count,
        memory_usage=memory_usage,
        columns=column_profiles,
        numeric_columns=numeric_columns,
        categorical_columns=categorical_columns,
        datetime_columns=datetime_columns,
        id_like_columns=id_like_columns,
        text_columns=text_columns,
        quality_score=quality_score,
        warnings=dataset_warnings,
    )


def _load_dataset_artifact(dataset_id: str, artifact_path: str) -> LoadedDatasetArtifact:
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
    artifact_dataset_id = payload.get("dataset_id")
    if artifact_dataset_id != dataset_id:
        raise AppError(
            status_code=409,
            code="DATASET_ARTIFACT_MISMATCH",
            message="The parsed dataset artifact does not match the requested dataset.",
            technical_detail=f"Artifact dataset_id is {artifact_dataset_id!r}; requested {dataset_id!r}.",
            suggested_fix="Upload the dataset again to recreate a consistent local artifact.",
        )

    columns = [
        DatasetColumn.model_validate(column) for column in payload.get("columns", [])
    ]
    rows = payload.get("rows", [])
    column_names = [column.name for column in columns]
    dataframe = pd.DataFrame(rows, columns=column_names)
    return LoadedDatasetArtifact(columns=columns, dataframe=dataframe)


def _profile_column(
    series: pd.Series,
    column: DatasetColumn,
    row_count: int,
) -> ColumnProfile:
    missing_count = int(series.isna().sum())
    missing_percentage = _percentage(missing_count, row_count)
    non_null = series.dropna()
    unique_count = int(non_null.nunique(dropna=True))
    unique_percentage = _percentage(unique_count, len(non_null))
    warnings: list[AnalysisWarning] = []

    inferred_type, role, parsed_numeric, parsed_datetime = _infer_type_and_role(
        series,
        column,
        missing_percentage,
        unique_count,
        unique_percentage,
        warnings,
    )

    if missing_percentage >= HIGH_MISSING_THRESHOLD:
        warnings.append(
            AnalysisWarning(
                code="HIGH_MISSINGNESS",
                message="This column has a high percentage of missing values.",
                column=column.name,
                details={
                    "missing_count": missing_count,
                    "missing_percentage": missing_percentage,
                },
            )
        )

    if missing_percentage >= MOSTLY_MISSING_THRESHOLD and role != ColumnRole.ignored:
        role = ColumnRole.ignored
        warnings.append(
            AnalysisWarning(
                code="MOSTLY_MISSING_COLUMN",
                message="This column is mostly missing and was marked as ignored.",
                column=column.name,
                details={"missing_percentage": missing_percentage},
            )
        )

    if unique_count <= 1 and len(non_null) > 0:
        warnings.append(
            AnalysisWarning(
                code="CONSTANT_COLUMN",
                message="This column has one distinct non-missing value.",
                column=column.name,
                details={"unique_count": unique_count},
            )
        )

    if role == ColumnRole.id:
        warnings.append(
            AnalysisWarning(
                code="POSSIBLE_ID_COLUMN",
                message="This column appears to identify rows rather than describe a business dimension.",
                column=column.name,
                details={"unique_percentage": unique_percentage},
            )
        )

    if unique_percentage >= HIGH_CARDINALITY_THRESHOLD and role in {
        ColumnRole.dimension,
        ColumnRole.text,
    }:
        warnings.append(
            AnalysisWarning(
                code="HIGH_CARDINALITY",
                message="This column has high cardinality and may not be useful as a compact grouping dimension.",
                column=column.name,
                details={"unique_percentage": unique_percentage},
            )
        )

    numeric_series = (
        parsed_numeric.dropna()
        if parsed_numeric is not None
        else pd.Series(dtype="float64")
    )
    min_value: Any | None = None
    max_value: Any | None = None
    mean: float | None = None
    median: float | None = None
    std: float | None = None

    if inferred_type == InferredType.numeric and not numeric_series.empty:
        min_value = _json_safe_number(numeric_series.min())
        max_value = _json_safe_number(numeric_series.max())
        mean = _json_safe_float(numeric_series.mean())
        median = _json_safe_float(numeric_series.median())
        std = _json_safe_float(numeric_series.std(ddof=0))
        skew = _json_safe_float(numeric_series.skew())
        if skew is not None and abs(skew) >= 2 and len(numeric_series) >= 8:
            warnings.append(
                AnalysisWarning(
                    code="SKEWED_DISTRIBUTION",
                    message="This numeric column has a strongly skewed distribution.",
                    column=column.name,
                    details={"skew": skew},
                )
            )

    if inferred_type == InferredType.datetime and parsed_datetime is not None:
        valid_datetime = parsed_datetime.dropna()
        if not valid_datetime.empty:
            min_value = valid_datetime.min().isoformat()
            max_value = valid_datetime.max().isoformat()

    return ColumnProfile(
        name=column.name,
        original_name=column.original_name or column.name,
        inferred_type=inferred_type,
        role=role,
        missing_count=missing_count,
        missing_percentage=missing_percentage,
        unique_count=unique_count,
        unique_percentage=unique_percentage,
        sample_values=_sample_values(non_null),
        min=min_value,
        max=max_value,
        mean=mean,
        median=median,
        std=std,
        top_values=_top_values(non_null, len(non_null)),
        warnings=warnings,
    )


def _infer_type_and_role(
    series: pd.Series,
    column: DatasetColumn,
    missing_percentage: float,
    unique_count: int,
    unique_percentage: float,
    warnings: list[AnalysisWarning],
) -> tuple[InferredType, ColumnRole, pd.Series | None, pd.Series | None]:
    non_null = series.dropna()
    if non_null.empty:
        return InferredType.unknown, ColumnRole.ignored, None, None

    column_name = f"{column.name} {column.original_name}".lower()
    parsed_numeric = pd.to_numeric(series, errors="coerce")
    numeric_confidence = _parse_confidence(parsed_numeric, series)
    with py_warnings.catch_warnings():
        py_warnings.simplefilter("ignore", UserWarning)
        parsed_datetime = pd.to_datetime(series, errors="coerce", utc=False)
    datetime_confidence = _parse_confidence(parsed_datetime, series)
    boolean_confidence = _boolean_confidence(non_null)

    text_lengths = non_null.astype(str).str.len()
    average_text_length = float(text_lengths.mean()) if not text_lengths.empty else 0.0
    max_text_length = int(text_lengths.max()) if not text_lengths.empty else 0

    if boolean_confidence >= BOOLEAN_CONFIDENCE_THRESHOLD:
        return InferredType.boolean, ColumnRole.dimension, None, None

    if numeric_confidence >= NUMERIC_TEXT_CONFIDENCE_THRESHOLD:
        if series.dtype == object:
            warnings.append(
                AnalysisWarning(
                    code="NUMERIC_STORED_AS_TEXT",
                    message="This column is numeric but was stored as text in the uploaded file.",
                    column=column.name,
                    details={"numeric_parse_confidence": round(numeric_confidence, 4)},
                )
            )
        if _looks_id_named(column_name) or _looks_unique_integer_identifier(
            parsed_numeric,
            unique_percentage,
        ):
            return InferredType.numeric, ColumnRole.id, parsed_numeric, None
        return InferredType.numeric, ColumnRole.metric, parsed_numeric, None

    if datetime_confidence >= DATETIME_CONFIDENCE_THRESHOLD:
        return InferredType.datetime, ColumnRole.datetime, None, parsed_datetime

    if datetime_confidence >= SUSPICIOUS_DATETIME_THRESHOLD and _looks_date_named(column_name):
        warnings.append(
            AnalysisWarning(
                code="SUSPICIOUS_DATE_PARSING",
                message="This column name suggests dates, but only some values could be parsed as dates.",
                column=column.name,
                details={"datetime_parse_confidence": round(datetime_confidence, 4)},
            )
        )

    if average_text_length >= LONG_TEXT_AVG_LENGTH or max_text_length >= LONG_TEXT_MAX_LENGTH:
        return InferredType.text, ColumnRole.text, None, None

    if unique_percentage >= ID_UNIQUE_THRESHOLD:
        role = ColumnRole.id if _looks_id_named(column_name) else ColumnRole.text
        return InferredType.text, role, None, None

    if unique_count <= LOW_CARDINALITY_MAX_UNIQUE or unique_percentage <= 50:
        return InferredType.categorical, ColumnRole.dimension, None, None

    if missing_percentage >= MOSTLY_MISSING_THRESHOLD:
        return InferredType.unknown, ColumnRole.ignored, None, None

    return InferredType.text, ColumnRole.text, None, None


def _boolean_confidence(non_null: pd.Series) -> float:
    true_false_values = {
        "true",
        "false",
        "yes",
        "no",
        "y",
        "n",
        "1",
        "0",
    }
    normalized = non_null.astype(str).str.strip().str.lower()
    if normalized.empty:
        return 0.0
    boolean_like = normalized.isin(true_false_values).sum()
    return float(boolean_like / len(normalized))


def _parse_confidence(parsed_series: pd.Series, original_series: pd.Series) -> float:
    non_missing = int(original_series.notna().sum())
    if non_missing == 0:
        return 0.0
    parsed_count = int(parsed_series.notna().sum())
    return parsed_count / non_missing


def _looks_id_named(column_name: str) -> bool:
    return bool(
        re.search(r"(^|[_\s-])(id|uuid|guid|key|code|number|no)([_\s-]|$)", column_name)
        or column_name.endswith("_id")
    )


def _looks_date_named(column_name: str) -> bool:
    return any(token in column_name for token in ("date", "time", "month", "year"))


def _looks_unique_integer_identifier(
    parsed_numeric: pd.Series,
    unique_percentage: float,
) -> bool:
    numeric_values = parsed_numeric.dropna()
    if len(numeric_values) < 25 or unique_percentage < ID_UNIQUE_THRESHOLD:
        return False

    integer_like = (numeric_values % 1 == 0).all()
    monotonic = numeric_values.is_monotonic_increasing or numeric_values.is_monotonic_decreasing
    return bool(integer_like and monotonic)


def _top_values(non_null: pd.Series, denominator: int) -> list[TopValue]:
    if denominator <= 0:
        return []

    value_counts = non_null.astype(object).value_counts(dropna=True).head(5)
    top_values: list[TopValue] = []
    for value, count in value_counts.items():
        top_values.append(
            TopValue(
                value=_json_safe_value(value),
                count=int(count),
                percentage=_percentage(int(count), denominator),
            )
        )
    return top_values


def _sample_values(non_null: pd.Series) -> list[Any]:
    values: list[Any] = []
    for value in non_null.head(5).tolist():
        values.append(_json_safe_value(value))
    return values


def _quality_score(
    *,
    missing_cell_percentage: float,
    duplicate_percentage: float,
    warning_count: int,
) -> float:
    score = 100.0
    score -= min(35.0, missing_cell_percentage * 0.8)
    score -= min(25.0, duplicate_percentage * 0.7)
    score -= min(25.0, warning_count * 3.0)
    return round(max(0.0, min(100.0, score)), 2)


def _percentage(numerator: int | float, denominator: int | float) -> float:
    if denominator <= 0:
        return 0.0
    return round(float(numerator) / float(denominator) * 100, 2)


def _json_safe_value(value: Any) -> Any:
    if pd.isna(value):
        return None
    if hasattr(value, "item"):
        value = value.item()
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def _json_safe_number(value: Any) -> int | float | None:
    value = _json_safe_value(value)
    if value is None:
        return None
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return value


def _json_safe_float(value: Any) -> float | None:
    value = _json_safe_value(value)
    if value is None:
        return None
    return round(float(value), 6)
