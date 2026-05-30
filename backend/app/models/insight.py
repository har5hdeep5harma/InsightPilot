from enum import StrEnum
from typing import Any

from pydantic import Field, field_validator, model_validator

from app.models.common import ApiModel, Confidence, NonEmptyStr

class InsightSeverity(StrEnum):
    low = "low"
    medium = "medium"
    high = "high"
    info = "low"
    warning = "medium"
    critical = "high"


class InsightCategory(StrEnum):
    dataset_quality = "dataset_quality"
    data_quality = "dataset_quality"
    trend = "trend"
    top_category = "top_category"
    correlation = "correlation"
    outlier = "outlier"
    concentration = "concentration"
    distribution = "distribution"
    missing_data_risk = "missing_data_risk"
    segment_difference = "segment_difference"


class EvidenceType(StrEnum):
    statistic = "statistic"
    comparison = "comparison"
    correlation = "correlation"
    outlier = "outlier"
    data_quality = "data_quality"
    distribution = "distribution"


class Evidence(ApiModel):
    type: EvidenceType
    column: str | None = None
    columns: list[str] = Field(default_factory=list)
    metric: NonEmptyStr
    value: Any
    comparison_value: Any | None = None
    values: dict[str, Any] = Field(default_factory=dict)
    comparison_values: dict[str, Any] = Field(default_factory=dict)
    rows_affected: int | None = Field(default=None, ge=0)
    calculation: NonEmptyStr
    explanation: NonEmptyStr

    @model_validator(mode="after")
    def include_single_column_in_columns(self) -> "Evidence":
        if self.column and self.column not in self.columns:
            self.columns.insert(0, self.column)
        return self


class Insight(ApiModel):
    id: NonEmptyStr
    dataset_id: NonEmptyStr
    title: NonEmptyStr
    summary: NonEmptyStr
    insight_type: InsightCategory
    severity: InsightSeverity
    confidence: Confidence
    evidence: Evidence
    recommendation: str | None = None
    related_columns: list[str] = Field(default_factory=list)
    related_chart_id: str | None = None

    @field_validator("evidence", mode="before")
    @classmethod
    def accept_legacy_evidence_list(cls, value: object) -> object:
        if isinstance(value, list):
            if not value:
                raise ValueError("insights require evidence")
            return value[0]
        return value
