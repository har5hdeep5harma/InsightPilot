from __future__ import annotations

import json
import logging
import re
from decimal import Decimal, InvalidOperation
from typing import Any

from pydantic import BaseModel, Field, ValidationError

from app.models.report import Report
from app.services.ai.providers import NarrativeProvider


SYSTEM_PROMPT = (
    "You are rewriting an analytical report using only the provided facts. "
    "Do not introduce new claims, numbers, causes, or recommendations. "
    "Preserve uncertainty. Keep the tone precise, executive, and concise."
)

LOGGER = logging.getLogger(__name__)
NUMBER_PATTERN = re.compile(r"(?<![A-Za-z])[-+]?\d[\d,]*(?:\.\d+)?%?")


class ReportNarrativeRewrite(BaseModel):
    title: str
    dataset_overview: str
    executive_summary: str
    key_findings: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    opportunities: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    data_quality_notes: list[str] = Field(default_factory=list)


def polish_report_narrative(
    report: Report,
    *,
    provider: NarrativeProvider | None,
) -> Report:
    if provider is None:
        LOGGER.info(
            "ai_narrative_skipped",
            extra={"report_id": report.id, "reason": "provider_unavailable"},
        )
        return report

    facts = _report_facts(report)
    try:
        raw_rewrite = provider.rewrite_json(system_prompt=SYSTEM_PROMPT, facts=facts)
        rewrite = ReportNarrativeRewrite.model_validate(raw_rewrite)
        _validate_rewrite(report, facts, rewrite)
    except Exception as exc:
        LOGGER.warning(
            "ai_narrative_fallback",
            extra={
                "report_id": report.id,
                "reason": exc.__class__.__name__,
                "detail": str(exc),
            },
        )
        return report

    LOGGER.info(
        "ai_narrative_applied",
        extra={
            "report_id": report.id,
            "provider_result": "validated",
            "rewritten_fields": list(rewrite.model_dump().keys()),
        },
    )
    return report.model_copy(
        update={
            "title": rewrite.title,
            "dataset_overview": rewrite.dataset_overview,
            "executive_summary": rewrite.executive_summary,
            "key_findings": rewrite.key_findings,
            "risks": rewrite.risks,
            "opportunities": rewrite.opportunities,
            "recommendations": rewrite.recommendations,
            "data_quality_notes": rewrite.data_quality_notes,
        }
    )


def _report_facts(report: Report) -> dict[str, Any]:
    return {
        "title": report.title,
        "dataset_overview": report.dataset_overview,
        "executive_summary": report.executive_summary,
        "key_findings": report.key_findings,
        "risks": report.risks,
        "opportunities": report.opportunities,
        "recommendations": report.recommendations,
        "data_quality_notes": report.data_quality_notes,
        "chart_ids": report.chart_ids,
        "evidence_appendix": [
            item.model_dump(mode="json") for item in report.evidence_appendix
        ],
        "insights": [
            {
                "id": insight.id,
                "title": insight.title,
                "summary": insight.summary,
                "insight_type": insight.insight_type.value,
                "severity": insight.severity.value,
                "confidence": insight.confidence,
                "evidence": insight.evidence.model_dump(mode="json"),
                "recommendation": insight.recommendation,
                "related_columns": insight.related_columns,
                "related_chart_id": insight.related_chart_id,
            }
            for insight in report.insights
        ],
    }


def _validate_rewrite(
    source_report: Report,
    facts: dict[str, Any],
    rewrite: ReportNarrativeRewrite,
) -> None:
    _validate_list_lengths(source_report, rewrite)
    _validate_unsupported_numbers(facts, rewrite)
    _validate_non_empty(rewrite)


def _validate_list_lengths(source_report: Report, rewrite: ReportNarrativeRewrite) -> None:
    fields = (
        "key_findings",
        "risks",
        "opportunities",
        "recommendations",
        "data_quality_notes",
    )
    for field_name in fields:
        expected = len(getattr(source_report, field_name))
        actual = len(getattr(rewrite, field_name))
        if actual != expected:
            raise ValueError(
                f"AI rewrite changed list length for {field_name}: expected {expected}, got {actual}."
            )


def _validate_unsupported_numbers(
    facts: dict[str, Any],
    rewrite: ReportNarrativeRewrite,
) -> None:
    supported_numbers = _numbers_from_value(facts)
    rewrite_numbers = _numbers_from_value(rewrite.model_dump())
    unsupported = sorted(rewrite_numbers - supported_numbers)
    if unsupported:
        raise ValueError(
            "AI rewrite introduced unsupported numeric values: "
            + ", ".join(str(number) for number in unsupported[:10])
        )


def _validate_non_empty(rewrite: ReportNarrativeRewrite) -> None:
    try:
        ReportNarrativeRewrite.model_validate(rewrite.model_dump())
    except ValidationError as exc:
        raise ValueError("AI rewrite failed report schema validation.") from exc

    if not rewrite.title.strip():
        raise ValueError("AI rewrite returned an empty title.")
    if not rewrite.dataset_overview.strip():
        raise ValueError("AI rewrite returned an empty dataset overview.")
    if not rewrite.executive_summary.strip():
        raise ValueError("AI rewrite returned an empty executive summary.")


def _numbers_from_value(value: Any) -> set[Decimal]:
    text = json.dumps(value, ensure_ascii=True, sort_keys=True, default=str)
    numbers: set[Decimal] = set()
    for match in NUMBER_PATTERN.findall(text):
        normalized = match.replace(",", "").removesuffix("%")
        try:
            numbers.add(Decimal(normalized))
        except InvalidOperation:
            continue
    return numbers
