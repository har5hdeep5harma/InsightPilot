from datetime import UTC, datetime
from typing import Any

from app.models.insight import Evidence, EvidenceType, Insight, InsightCategory, InsightSeverity
from app.models.report import EvidenceAppendixItem, Report
from app.services.ai.narrative_polisher import polish_report_narrative


class FakeNarrativeProvider:
    def __init__(self, payload: dict[str, Any] | Exception) -> None:
        self.payload = payload
        self.facts: dict[str, Any] | None = None

    def rewrite_json(
        self,
        *,
        system_prompt: str,
        facts: dict[str, Any],
    ) -> dict[str, Any]:
        assert "Do not introduce new claims" in system_prompt
        self.facts = facts
        if isinstance(self.payload, Exception):
            raise self.payload
        return self.payload


def test_ai_narrative_polishes_valid_rewrite_without_changing_evidence() -> None:
    report = _report()
    provider = FakeNarrativeProvider(
        {
            "title": "Executive Analysis Memo: SaaS Growth",
            "dataset_overview": "The dataset contains 2,400 rows and a quality score of 85.31/100.",
            "executive_summary": "Revenue increased by 115.5%, with quality risks noted in the evidence.",
            "key_findings": [
                "Monthly revenue increased by 115.5% across the observed period."
            ],
            "risks": ["The quality score is 85.31/100, so caveats should remain visible."],
            "opportunities": ["Review the growth finding with the same 115.5% evidence."],
            "recommendations": ["Use the evidence appendix before acting on the 115.5% trend."],
            "data_quality_notes": ["Quality score: 85.31/100."],
        }
    )

    polished = polish_report_narrative(report, provider=provider)

    assert polished.executive_summary.startswith("Revenue increased")
    assert polished.evidence_appendix == report.evidence_appendix
    assert polished.insights == report.insights
    assert provider.facts is not None
    assert provider.facts["evidence_appendix"]


def test_ai_narrative_falls_back_when_rewrite_introduces_unsupported_number() -> None:
    report = _report()
    provider = FakeNarrativeProvider(
        {
            "title": report.title,
            "dataset_overview": "The dataset contains 9,999 rows.",
            "executive_summary": report.executive_summary,
            "key_findings": report.key_findings,
            "risks": report.risks,
            "opportunities": report.opportunities,
            "recommendations": report.recommendations,
            "data_quality_notes": report.data_quality_notes,
        }
    )

    polished = polish_report_narrative(report, provider=provider)

    assert polished == report


def test_ai_narrative_falls_back_when_provider_fails() -> None:
    report = _report()
    provider = FakeNarrativeProvider(RuntimeError("network unavailable"))

    polished = polish_report_narrative(report, provider=provider)

    assert polished == report


def test_ai_narrative_falls_back_when_no_provider_is_configured() -> None:
    report = _report()

    polished = polish_report_narrative(report, provider=None)

    assert polished == report


def _report() -> Report:
    insight = Insight(
        id="ins_trend",
        dataset_id="ds_1",
        title="Revenue increased over time",
        summary="Revenue increased by 115.5% from first period to last period.",
        insight_type=InsightCategory.trend,
        severity=InsightSeverity.medium,
        confidence=0.86,
        evidence=Evidence(
            type=EvidenceType.comparison,
            column="monthly_revenue",
            columns=["date", "monthly_revenue"],
            metric="period_change_percentage",
            value=115.5,
            comparison_value={
                "first_period_value": 359725.52,
                "last_period_value": 775039.71,
            },
            rows_affected=2400,
            calculation="(last sum(monthly_revenue) - first sum(monthly_revenue)) / abs(first sum(monthly_revenue))",
            explanation="The trend is based on aggregated metric values ordered by date.",
        ),
        recommendation="Check whether this movement aligns with known campaigns.",
        related_columns=["date", "monthly_revenue"],
    )
    return Report(
        id="report_1",
        dataset_id="ds_1",
        title="Executive Analysis Memo: saas_growth_sample.csv",
        dataset_overview="The uploaded dataset contains 2,400 rows and has a quality score of 85.31/100.",
        executive_summary="The strongest finding is: Revenue increased by 115.5% from first period to last period.",
        key_findings=[
            "Revenue increased by 115.5% from first period to last period. Evidence: period change produced 115.5."
        ],
        risks=["The quality score is 85.31/100."],
        opportunities=["Use the finding `Revenue increased over time` to prioritize follow-up analysis."],
        recommendations=["Use the evidence appendix before acting on the trend."],
        data_quality_notes=["Quality score: 85.31/100."],
        evidence_appendix=[
            EvidenceAppendixItem(
                insight_id=insight.id,
                insight_title=insight.title,
                insight_type=insight.insight_type.value,
                evidence=insight.evidence.model_dump(mode="json"),
            )
        ],
        chart_ids=["chart_1"],
        insights=[insight],
        created_at=datetime.now(UTC),
    )
