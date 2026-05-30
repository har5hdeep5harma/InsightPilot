from __future__ import annotations

from datetime import UTC, datetime
from typing import Iterable
from uuid import uuid4

from app.models.chart import ChartSpec
from app.models.dataset import Dataset
from app.models.insight import Insight, InsightCategory, InsightSeverity
from app.models.profile import DatasetProfile
from app.models.report import EvidenceAppendixItem, Report, ReportResponse
from app.services.ai.narrative_polisher import polish_report_narrative
from app.services.ai.providers import (
    NarrativeProvider,
    OpenAICompatibleNarrativeProvider,
)


def generate_executive_report(
    *,
    dataset: Dataset,
    profile: DatasetProfile,
    charts: list[ChartSpec],
    insights: list[Insight],
    enable_ai_narrative: bool = False,
    ai_narrative_api_key: str | None = None,
    ai_narrative_base_url: str = "https://api.openai.com/v1/chat/completions",
    ai_narrative_model: str = "gpt-4o-mini",
    narrative_provider: NarrativeProvider | None = None,
) -> Report:
    report = _deterministic_report(
        dataset=dataset,
        profile=profile,
        charts=charts,
        insights=insights,
    )
    return _polish_report_with_ai_if_enabled(
        report,
        enabled=enable_ai_narrative,
        api_key=ai_narrative_api_key,
        base_url=ai_narrative_base_url,
        model=ai_narrative_model,
        provider=narrative_provider,
    )


def report_to_response(report: Report) -> ReportResponse:
    return ReportResponse(
        report_id=report.id,
        title=report.title,
        dataset_overview=report.dataset_overview,
        executive_summary=report.executive_summary,
        key_findings=report.key_findings,
        risks=report.risks,
        opportunities=report.opportunities,
        recommendations=report.recommendations,
        data_quality_notes=report.data_quality_notes,
        evidence_appendix=report.evidence_appendix,
        chart_ids=report.chart_ids,
    )


def _deterministic_report(
    *,
    dataset: Dataset,
    profile: DatasetProfile,
    charts: list[ChartSpec],
    insights: list[Insight],
) -> Report:
    sorted_insights = sorted(insights, key=_insight_sort_key)
    title = f"Executive Analysis Memo: {dataset.original_filename}"
    dataset_overview = _dataset_overview(dataset, profile)
    executive_summary = _executive_summary(profile, sorted_insights)
    key_findings = _key_findings(sorted_insights)
    risks = _risks(profile, sorted_insights)
    opportunities = _opportunities(sorted_insights)
    recommendations = _recommendations(sorted_insights, profile)
    data_quality_notes = _data_quality_notes(profile, sorted_insights)
    evidence_appendix = _evidence_appendix(sorted_insights)
    chart_ids = [chart.id for chart in charts]

    return Report(
        id=f"report_{uuid4().hex}",
        dataset_id=dataset.id,
        title=title,
        dataset_overview=dataset_overview,
        executive_summary=executive_summary,
        key_findings=key_findings,
        risks=risks,
        opportunities=opportunities,
        recommendations=recommendations,
        data_quality_notes=data_quality_notes,
        evidence_appendix=evidence_appendix,
        chart_ids=chart_ids,
        charts=charts,
        insights=sorted_insights,
        created_at=datetime.now(UTC),
    )


def _dataset_overview(dataset: Dataset, profile: DatasetProfile) -> str:
    return (
        f"The uploaded dataset `{dataset.original_filename}` contains "
        f"{profile.row_count:,} rows and {profile.column_count:,} columns. "
        f"The profiling pass identified {len(profile.numeric_columns)} numeric metrics, "
        f"{len(profile.categorical_columns)} categorical dimensions, "
        f"{len(profile.datetime_columns)} datetime columns, "
        f"{len(profile.id_like_columns)} ID-like columns, and "
        f"{len(profile.text_columns)} text columns. "
        f"The current data quality score is {profile.quality_score}/100."
    )


def _executive_summary(profile: DatasetProfile, insights: list[Insight]) -> str:
    if not insights:
        return (
            "The dataset was profiled successfully, but no deterministic insight crossed "
            "the evidence thresholds. The report should be treated as a data inventory "
            "until stronger patterns are identified."
        )

    lead = insights[0]
    supporting = insights[1:3]
    summary_parts = [
        f"The strongest finding is: {lead.summary}",
    ]
    if supporting:
        summary_parts.append(
            "Additional material findings include "
            + "; ".join(insight.summary for insight in supporting)
            + "."
        )
    if profile.quality_score < 80:
        summary_parts.append(
            f"Because the quality score is {profile.quality_score}/100, conclusions should be presented with the noted data limitations."
        )
    else:
        summary_parts.append(
            "The data quality checks do not remove the need for review, but they support using the computed findings as a first-pass executive readout."
        )
    return " ".join(summary_parts)


def _key_findings(insights: list[Insight]) -> list[str]:
    findings = [
        _with_evidence_reference(insight)
        for insight in insights
        if insight.insight_type
        in {
            InsightCategory.trend,
            InsightCategory.top_category,
            InsightCategory.concentration,
            InsightCategory.correlation,
            InsightCategory.segment_difference,
            InsightCategory.distribution,
            InsightCategory.outlier,
        }
    ]
    return findings[:6]


def _risks(profile: DatasetProfile, insights: list[Insight]) -> list[str]:
    risks: list[str] = []
    for insight in insights:
        if insight.insight_type in {
            InsightCategory.dataset_quality,
            InsightCategory.missing_data_risk,
            InsightCategory.outlier,
        } or insight.severity == InsightSeverity.high:
            risks.append(_with_evidence_reference(insight))

    if profile.duplicate_row_count > 0 and not any("duplicate" in risk.lower() for risk in risks):
        risks.append(
            f"The profile found {profile.duplicate_row_count:,} duplicate rows, which can overstate totals if duplicates are not intentional records."
        )
    return risks[:5]


def _opportunities(insights: list[Insight]) -> list[str]:
    opportunities: list[str] = []
    for insight in insights:
        if insight.insight_type in {
            InsightCategory.trend,
            InsightCategory.top_category,
            InsightCategory.concentration,
            InsightCategory.segment_difference,
            InsightCategory.correlation,
        }:
            opportunities.append(
                f"Use the finding `{insight.title}` to prioritize follow-up analysis around {', '.join(insight.related_columns) or 'the related fields'}."
            )
    return opportunities[:4]


def _recommendations(insights: list[Insight], profile: DatasetProfile) -> list[str]:
    recommendations = [
        insight.recommendation
        for insight in insights
        if insight.recommendation
    ]
    if profile.quality_score < 80:
        recommendations.append(
            "Resolve or document the main quality warnings before presenting the memo as a final decision document."
        )
    recommendations.append(
        "Use the included chart IDs and evidence appendix when reviewing the report so each conclusion can be traced back to a computed value."
    )
    return _unique(recommendations)[:6]


def _data_quality_notes(profile: DatasetProfile, insights: list[Insight]) -> list[str]:
    notes = [
        f"Quality score: {profile.quality_score}/100.",
        f"Duplicate rows detected: {profile.duplicate_row_count:,}.",
    ]
    high_missing = [
        column
        for column in profile.columns
        if column.missing_percentage >= 30
    ]
    if high_missing:
        notes.append(
            "High-missingness columns: "
            + ", ".join(
                f"{column.original_name} ({column.missing_percentage}%)"
                for column in high_missing[:5]
            )
            + "."
        )
    quality_insights = [
        insight.summary
        for insight in insights
        if insight.insight_type in {
            InsightCategory.dataset_quality,
            InsightCategory.missing_data_risk,
        }
    ]
    notes.extend(quality_insights[:3])
    return _unique(notes)


def _evidence_appendix(insights: list[Insight]) -> list[EvidenceAppendixItem]:
    return [
        EvidenceAppendixItem(
            insight_id=insight.id,
            insight_title=insight.title,
            insight_type=insight.insight_type.value,
            evidence=insight.evidence.model_dump(mode="json"),
        )
        for insight in insights
    ]


def _with_evidence_reference(insight: Insight) -> str:
    evidence = insight.evidence
    value = evidence.value
    comparison = evidence.comparison_value
    if comparison is None:
        return f"{insight.summary} Evidence: {evidence.calculation} produced {value}."
    return (
        f"{insight.summary} Evidence: {evidence.calculation} produced {value} "
        f"compared with {comparison}."
    )


def _polish_report_with_ai_if_enabled(
    report: Report,
    *,
    enabled: bool,
    api_key: str | None,
    base_url: str,
    model: str,
    provider: NarrativeProvider | None,
) -> Report:
    if not enabled:
        return report
    if provider is None and api_key:
        provider = OpenAICompatibleNarrativeProvider(
            api_key=api_key,
            base_url=base_url,
            model=model,
        )
    return polish_report_narrative(report, provider=provider)


def _insight_sort_key(insight: Insight) -> tuple[int, float, str]:
    severity_rank = {
        InsightSeverity.high: 0,
        InsightSeverity.medium: 1,
        InsightSeverity.low: 2,
    }
    return (severity_rank[insight.severity], -insight.confidence, insight.title)


def _unique(items: Iterable[str | None]) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for item in items:
        if not item:
            continue
        if item in seen:
            continue
        seen.add(item)
        output.append(item)
    return output
