from datetime import datetime
from typing import Any

from pydantic import Field

from app.models.chart import ChartSpec
from app.models.common import ApiModel, NonEmptyStr
from app.models.insight import Insight


class EvidenceAppendixItem(ApiModel):
    insight_id: NonEmptyStr
    insight_title: NonEmptyStr
    insight_type: NonEmptyStr
    evidence: dict[str, Any]


class Report(ApiModel):
    id: NonEmptyStr
    dataset_id: NonEmptyStr
    title: NonEmptyStr
    dataset_overview: NonEmptyStr
    executive_summary: NonEmptyStr
    key_findings: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    opportunities: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    data_quality_notes: list[str] = Field(default_factory=list)
    evidence_appendix: list[EvidenceAppendixItem] = Field(default_factory=list)
    chart_ids: list[str] = Field(default_factory=list)
    charts: list[ChartSpec] = Field(default_factory=list)
    insights: list[Insight] = Field(default_factory=list)
    created_at: datetime


class ReportResponse(ApiModel):
    report_id: NonEmptyStr
    title: NonEmptyStr
    dataset_overview: NonEmptyStr
    executive_summary: NonEmptyStr
    key_findings: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    opportunities: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    data_quality_notes: list[str] = Field(default_factory=list)
    evidence_appendix: list[EvidenceAppendixItem] = Field(default_factory=list)
    chart_ids: list[str] = Field(default_factory=list)
