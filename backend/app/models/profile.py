from enum import StrEnum
from typing import Any

from pydantic import Field

from app.models.common import ApiModel, AnalysisWarning, NonEmptyStr, Percentage


class InferredType(StrEnum):
    numeric = "numeric"
    categorical = "categorical"
    boolean = "boolean"
    datetime = "datetime"
    text = "text"
    unknown = "unknown"
    string = "text"
    number = "numeric"
    integer = "numeric"
    category = "categorical"


class ColumnRole(StrEnum):
    metric = "metric"
    dimension = "dimension"
    datetime = "datetime"
    id = "id"
    text = "text"
    ignored = "ignored"
    identifier = "id"
    flag = "dimension"
    free_text = "text"
    unknown = "ignored"


class TopValue(ApiModel):
    value: Any
    count: int = Field(ge=0)
    percentage: Percentage


class ColumnProfile(ApiModel):
    name: NonEmptyStr
    original_name: NonEmptyStr
    inferred_type: InferredType
    role: ColumnRole
    missing_count: int = Field(ge=0)
    missing_percentage: Percentage
    unique_count: int = Field(ge=0)
    unique_percentage: Percentage
    sample_values: list[Any] = Field(default_factory=list)
    min: Any | None = None
    max: Any | None = None
    mean: float | None = None
    median: float | None = None
    std: float | None = None
    top_values: list[TopValue] = Field(default_factory=list)
    warnings: list[AnalysisWarning] = Field(default_factory=list)


class DatasetProfile(ApiModel):
    dataset_id: NonEmptyStr
    row_count: int = Field(ge=0)
    column_count: int = Field(ge=0)
    duplicate_row_count: int = Field(ge=0)
    memory_usage: int = Field(ge=0)
    columns: list[ColumnProfile]
    numeric_columns: list[str] = Field(default_factory=list)
    categorical_columns: list[str] = Field(default_factory=list)
    datetime_columns: list[str] = Field(default_factory=list)
    id_like_columns: list[str] = Field(default_factory=list)
    text_columns: list[str] = Field(default_factory=list)
    quality_score: Percentage
    warnings: list[AnalysisWarning] = Field(default_factory=list)


# Backwards-compatible alias used by early architecture docs.
ColumnDType = InferredType
