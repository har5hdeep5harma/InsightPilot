from __future__ import annotations

import json
import math
import re
import sys
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from typing import Any

import pandas as pd
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.config import get_settings  # noqa: E402
from app.db.init_db import init_database  # noqa: E402
from app.db.session import get_db  # noqa: E402
from app.main import app  # noqa: E402


EXPECTED_PATH = Path(__file__).with_name("expected_insights.json")
RESULTS_PATH = Path(__file__).with_name("eval_results.json")
NUMBER_PATTERN = re.compile(r"[-+]?\d[\d,]*(?:\.\d+)?%?")


@dataclass
class Check:
    name: str
    passed: bool
    score: float
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class Suite:
    name: str
    checks: list[Check] = field(default_factory=list)

    @property
    def score(self) -> float:
        if not self.checks:
            return 0.0
        return round(sum(check.score for check in self.checks) / len(self.checks), 4)

    @property
    def passed(self) -> bool:
        return all(check.passed for check in self.checks)


def main() -> int:
    expected = json.loads(EXPECTED_PATH.read_text(encoding="utf-8"))
    dataset_path = (EXPECTED_PATH.parent / expected["dataset"]["path"]).resolve()

    runtime = _run_pipeline(dataset_path)
    raw_data = pd.read_csv(dataset_path)

    suites = [
        _eval_column_roles(runtime["profile"], expected),
        _eval_missing_values(runtime["profile"], expected),
        _eval_duplicate_rows(runtime["profile"], expected),
        _eval_outliers(raw_data, runtime["insights"], expected),
        _eval_trend(raw_data, runtime["insights"], expected),
        _eval_top_category(runtime["insights"], expected),
        _eval_concentration(raw_data, runtime["insights"], expected),
        _eval_correlation(raw_data, runtime["insights"], expected),
        _eval_report(runtime["report"], runtime["insights"], expected),
        _eval_exports(runtime["html_export"], runtime["pdf_export"]),
    ]

    overall_score = round(sum(suite.score for suite in suites) / len(suites), 4)
    threshold = float(expected["minimum_overall_score"])
    output = {
        "generated_at": datetime.now(UTC).isoformat(),
        "dataset": expected["dataset"]["name"],
        "dataset_path": str(dataset_path.relative_to(REPO_ROOT)),
        "overall_score": overall_score,
        "minimum_overall_score": threshold,
        "passed": overall_score >= threshold and all(suite.passed for suite in suites),
        "suites": [
            {
                "name": suite.name,
                "score": suite.score,
                "passed": suite.passed,
                "checks": [
                    {
                        "name": check.name,
                        "passed": check.passed,
                        "score": round(check.score, 4),
                        "details": check.details,
                    }
                    for check in suite.checks
                ],
            }
            for suite in suites
        ],
    }
    RESULTS_PATH.write_text(json.dumps(output, indent=2, ensure_ascii=True), encoding="utf-8")

    print(f"InsightPilot eval score: {overall_score:.3f}")
    for suite in suites:
        status = "PASS" if suite.passed else "FAIL"
        print(f"- {status} {suite.name}: {suite.score:.3f}")
    print(f"Wrote {RESULTS_PATH.relative_to(REPO_ROOT)}")
    return 0 if output["passed"] else 1


def _run_pipeline(dataset_path: Path) -> dict[str, Any]:
    with TemporaryDirectory() as tmp_dir:
        with _test_client(tmp_dir) as client:
            with dataset_path.open("rb") as file:
                upload_response = client.post(
                    "/api/datasets/upload",
                    files={"file": (dataset_path.name, file, "text/csv")},
                )
            _raise_for_eval(upload_response, "upload dataset")
            dataset_id = upload_response.json()["dataset_id"]

            profile_response = client.get(f"/api/datasets/{dataset_id}/profile")
            _raise_for_eval(profile_response, "profile dataset")

            charts_response = client.get(f"/api/datasets/{dataset_id}/charts")
            _raise_for_eval(charts_response, "generate charts")

            insights_response = client.get(f"/api/datasets/{dataset_id}/insights")
            _raise_for_eval(insights_response, "generate insights")

            report_response = client.post(f"/api/datasets/{dataset_id}/report")
            _raise_for_eval(report_response, "generate report")
            report = report_response.json()

            html_response = client.get(f"/api/reports/{report['report_id']}/export/html")
            pdf_response = client.get(f"/api/reports/{report['report_id']}/export/pdf")

            return {
                "upload": upload_response.json(),
                "profile": profile_response.json(),
                "charts": charts_response.json(),
                "insights": insights_response.json(),
                "report": report,
                "html_export": {
                    "status_code": html_response.status_code,
                    "content_type": html_response.headers.get("content-type"),
                    "content_disposition": html_response.headers.get("content-disposition"),
                    "body": html_response.text,
                },
                "pdf_export": {
                    "status_code": pdf_response.status_code,
                    "content_type": pdf_response.headers.get("content-type"),
                    "content_disposition": pdf_response.headers.get("content-disposition"),
                    "body": _safe_response_body(pdf_response),
                },
            }


@contextmanager
def _test_client(tmp_dir: str):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    init_database(engine)
    session_factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    def override_get_db():
        session: Session = session_factory()
        try:
            yield session
        finally:
            session.close()

    settings = SimpleNamespace(
        upload_dir=str(Path(tmp_dir) / "uploads"),
        max_upload_mb=10,
        preview_row_limit=20,
        enable_ai_narrative=False,
        ai_narrative_api_key=None,
        ai_narrative_base_url="https://api.openai.com/v1/chat/completions",
        ai_narrative_model="gpt-4o-mini",
        enable_llm_report_rewrite=False,
        llm_api_key=None,
    )

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_settings] = lambda: settings
    try:
        with TestClient(app) as client:
            yield client
    finally:
        app.dependency_overrides.clear()


def _eval_column_roles(profile: dict[str, Any], expected: dict[str, Any]) -> Suite:
    suite = Suite("column role detection")
    columns = {column["name"]: column for column in profile["columns"]}
    for name, expectation in expected["profile_expectations"]["column_roles"].items():
        actual = columns.get(name)
        passed = (
            actual is not None
            and actual["inferred_type"] == expectation["inferred_type"]
            and actual["role"] == expectation["role"]
        )
        suite.checks.append(
            _check(
                name,
                passed,
                actual={
                    "inferred_type": actual.get("inferred_type") if actual else None,
                    "role": actual.get("role") if actual else None,
                },
                expected=expectation,
            )
        )
    return suite


def _eval_missing_values(profile: dict[str, Any], expected: dict[str, Any]) -> Suite:
    suite = Suite("missing value detection")
    columns = {column["name"]: column for column in profile["columns"]}
    for name, expected_count in expected["profile_expectations"]["missing_counts"].items():
        actual_count = columns[name]["missing_count"]
        suite.checks.append(
            _check(
                name,
                actual_count == expected_count,
                actual_count=actual_count,
                expected_count=expected_count,
                missing_percentage=columns[name]["missing_percentage"],
            )
        )
    return suite


def _eval_duplicate_rows(profile: dict[str, Any], expected: dict[str, Any]) -> Suite:
    expected_count = expected["profile_expectations"]["duplicate_row_count"]
    actual_count = profile["duplicate_row_count"]
    return Suite(
        "duplicate detection",
        [
            _check(
                "duplicate_row_count",
                actual_count == expected_count,
                actual_count=actual_count,
                expected_count=expected_count,
            )
        ],
    )


def _eval_outliers(
    data: pd.DataFrame,
    insights: list[dict[str, Any]],
    expected: dict[str, Any],
) -> Suite:
    suite = Suite("outlier detection")
    outliers = expected["expected_data_facts"]["outliers"]
    suite.checks.append(
        _check(
            "monthly_revenue_above_50000",
            int((data["monthly_revenue"] > 50000).sum()) == outliers["monthly_revenue_above_50000"],
            actual_count=int((data["monthly_revenue"] > 50000).sum()),
            expected_count=outliers["monthly_revenue_above_50000"],
        )
    )
    suite.checks.append(
        _check(
            "support_tickets_at_least_30",
            int((data["support_tickets"] >= 30).sum()) == outliers["support_tickets_at_least_30"],
            actual_count=int((data["support_tickets"] >= 30).sum()),
            expected_count=outliers["support_tickets_at_least_30"],
        )
    )

    expectation = expected["generated_insight_expectations"]["outlier"]
    insight = _find_insight(
        insights,
        insight_type=expectation["insight_type"],
        required_columns=expectation["required_columns"],
        metric=expectation["metric"],
    )
    suite.checks.extend(_score_insight_quality(insight, expectation, "monthly_revenue_outlier_insight"))
    return suite


def _eval_trend(
    data: pd.DataFrame,
    insights: list[dict[str, Any]],
    expected: dict[str, Any],
) -> Suite:
    suite = Suite("trend detection")
    facts = expected["expected_data_facts"]["monthly_revenue_growth"]
    dated = data.copy()
    dated["date"] = pd.to_datetime(dated["date"])
    monthly = dated.groupby(dated["date"].dt.to_period("M"))["monthly_revenue"].sum()
    growth = (monthly.iloc[-1] - monthly.iloc[0]) / abs(monthly.iloc[0]) * 100
    suite.checks.append(
        _check(
            "encoded_monthly_revenue_growth",
            growth >= facts["minimum_growth_percentage"],
            actual_growth_percentage=round(float(growth), 2),
            expected_minimum=facts["minimum_growth_percentage"],
            first_month=str(monthly.index[0]),
            last_month=str(monthly.index[-1]),
        )
    )

    expectation = expected["generated_insight_expectations"]["trend"]
    insight = _find_insight(
        insights,
        insight_type=expectation["insight_type"],
        required_columns=expectation["required_columns"],
    )
    suite.checks.extend(_score_insight_quality(insight, expectation, "monthly_revenue_trend_insight"))
    if insight:
        value = float(insight["evidence"]["value"])
        suite.checks.append(
            _check(
                "trend_direction_and_magnitude",
                value >= expectation["minimum_change_percentage"],
                actual_change_percentage=value,
                expected_minimum=expectation["minimum_change_percentage"],
            )
        )
    return suite


def _eval_top_category(insights: list[dict[str, Any]], expected: dict[str, Any]) -> Suite:
    suite = Suite("top category insight")
    expectation = expected["generated_insight_expectations"]["top_category"]
    insight = next(
        (
            item
            for item in insights
            if item["insight_type"] in expectation["insight_types"]
            and set(expectation["required_columns"]).issubset(set(item["evidence"].get("columns", [])))
            and item["evidence"].get("metric") == expectation["metric"]
        ),
        None,
    )
    suite.checks.extend(_score_insight_quality(insight, expectation, "region_top_category_insight"))
    if insight:
        values = insight["evidence"].get("values", {})
        suite.checks.append(
            _check(
                "top_category_is_expected_segment",
                values.get("top_category") == expectation["expected_category"],
                actual_category=values.get("top_category"),
                expected_category=expectation["expected_category"],
            )
        )
        suite.checks.append(
            _check(
                "top_category_share_is_material",
                float(insight["evidence"]["value"]) >= expectation["minimum_share_percentage"],
                actual_share=insight["evidence"]["value"],
                expected_minimum=expectation["minimum_share_percentage"],
            )
        )
    return suite


def _eval_concentration(
    data: pd.DataFrame,
    insights: list[dict[str, Any]],
    expected: dict[str, Any],
) -> Suite:
    suite = Suite("concentration insight")
    facts = expected["expected_data_facts"]["plan_concentration"]
    grouped = data.groupby(facts["dimension"])[facts["metric"]].sum().sort_values(ascending=False)
    top_category = str(grouped.index[0])
    share = float(grouped.iloc[0] / grouped.sum() * 100)
    suite.checks.append(
        _check(
            "enterprise_plan_revenue_concentration_encoded",
            top_category == facts["top_category"] and share >= facts["minimum_share_percentage"],
            actual_category=top_category,
            actual_share=round(share, 2),
            expected_category=facts["top_category"],
            expected_minimum_share=facts["minimum_share_percentage"],
        )
    )
    concentration_like = [
        insight
        for insight in insights
        if insight["insight_type"] in {"top_category", "concentration"}
        and insight["evidence"].get("metric") == "top_category_share"
    ]
    suite.checks.append(
        _check(
            "generated_concentration_like_insight_present",
            bool(concentration_like),
            generated_count=len(concentration_like),
            insight_titles=[insight["title"] for insight in concentration_like],
        )
    )
    for insight in concentration_like[:1]:
        suite.checks.extend(_score_insight_quality(insight, {}, "concentration_quality"))
    return suite


def _eval_correlation(
    data: pd.DataFrame,
    insights: list[dict[str, Any]],
    expected: dict[str, Any],
) -> Suite:
    suite = Suite("correlation insight")
    for name, fact in expected["expected_data_facts"]["correlations"].items():
        value = data[[fact["left"], fact["right"]]].corr().iloc[0, 1]
        expected_direction = fact["expected_direction"]
        direction_ok = value < 0 if expected_direction == "negative" else value > 0
        suite.checks.append(
            _check(
                name,
                direction_ok and abs(value) >= fact["minimum_absolute_value"],
                actual_correlation=round(float(value), 3),
                expected_direction=expected_direction,
                expected_min_abs=fact["minimum_absolute_value"],
            )
        )

    expectation = expected["generated_insight_expectations"]["correlation"]
    insight = _find_insight(
        insights,
        insight_type=expectation["insight_type"],
        metric=expectation["metric"],
    )
    suite.checks.extend(_score_insight_quality(insight, expectation, "generated_correlation_insight"))
    if insight:
        coefficient = abs(float(insight["evidence"]["value"]))
        suite.checks.append(
            _check(
                "generated_correlation_strength",
                coefficient >= expectation["minimum_absolute_value"],
                actual_absolute_correlation=coefficient,
                expected_minimum=expectation["minimum_absolute_value"],
            )
        )
    return suite


def _eval_report(
    report: dict[str, Any],
    insights: list[dict[str, Any]],
    expected: dict[str, Any],
) -> Suite:
    suite = Suite("report generation")
    expectation = expected["report_expectations"]
    suite.checks.append(
        _check(
            "minimum_report_sections_populated",
            len(report["key_findings"]) >= expectation["minimum_key_findings"]
            and len(report["risks"]) >= expectation["minimum_risks"]
            and len(report["recommendations"]) >= expectation["minimum_recommendations"],
            key_findings=len(report["key_findings"]),
            risks=len(report["risks"]),
            recommendations=len(report["recommendations"]),
        )
    )
    suite.checks.append(
        _check(
            "evidence_appendix_populated",
            len(report["evidence_appendix"]) >= expectation["minimum_evidence_items"],
            evidence_items=len(report["evidence_appendix"]),
            expected_minimum=expectation["minimum_evidence_items"],
        )
    )
    suite.checks.append(
        _check(
            "key_findings_reference_evidence",
            all("Evidence:" in finding for finding in report["key_findings"]),
            key_findings=report["key_findings"],
        )
    )
    suite.checks.append(
        _check(
            "no_generic_unsupported_report_language",
            "data-driven insights" not in json.dumps(report).lower(),
            banned_phrase="data-driven insights",
        )
    )
    suite.checks.append(
        _check(
            "report_has_useful_recommendations",
            any(_looks_actionable(item) for item in report["recommendations"]),
            recommendations=report["recommendations"],
        )
    )
    suite.checks.append(
        _check(
            "report_evidence_matches_insight_count",
            len(report["evidence_appendix"]) == len(insights),
            evidence_items=len(report["evidence_appendix"]),
            insight_count=len(insights),
        )
    )
    return suite


def _eval_exports(
    html_export: dict[str, Any],
    pdf_export: dict[str, Any],
) -> Suite:
    suite = Suite("export generation")
    suite.checks.append(
        _check(
            "html_export_downloadable",
            html_export["status_code"] == 200
            and "text/html" in str(html_export["content_type"])
            and "attachment" in str(html_export["content_disposition"])
            and "Evidence appendix" in html_export["body"],
            status_code=html_export["status_code"],
            content_type=html_export["content_type"],
            content_disposition=html_export["content_disposition"],
        )
    )
    pdf_ok = (
        pdf_export["status_code"] == 200
        and "application/pdf" in str(pdf_export["content_type"])
        and "attachment" in str(pdf_export["content_disposition"])
    )
    suite.checks.append(
        _check(
            "pdf_export_downloadable",
            pdf_ok,
            status_code=pdf_export["status_code"],
            content_type=pdf_export["content_type"],
            content_disposition=pdf_export["content_disposition"],
        )
    )
    return suite


def _score_insight_quality(
    insight: dict[str, Any] | None,
    expectation: dict[str, Any],
    prefix: str,
) -> list[Check]:
    if insight is None:
        return [
            _check(
                f"{prefix}_present",
                False,
                reason="No matching generated insight was found.",
            )
        ]

    evidence = insight.get("evidence") or {}
    checks = [
        _check(f"{prefix}_present", True, title=insight["title"]),
        _check(
            f"{prefix}_evidence_present",
            bool(evidence.get("calculation")) and evidence.get("value") is not None,
            evidence=evidence,
        ),
        _check(
            f"{prefix}_recommendation_useful",
            _looks_actionable(insight.get("recommendation")),
            recommendation=insight.get("recommendation"),
        ),
        _check(
            f"{prefix}_severity_appropriate",
            not expectation.get("allowed_severities")
            or insight["severity"] in expectation["allowed_severities"],
            severity=insight["severity"],
            allowed=expectation.get("allowed_severities"),
        ),
        _check(
            f"{prefix}_confidence_reasonable",
            float(insight["confidence"]) >= float(expectation.get("minimum_confidence", 0.6))
            and float(insight["confidence"]) <= 1,
            confidence=insight["confidence"],
            expected_minimum=expectation.get("minimum_confidence", 0.6),
        ),
        _check(
            f"{prefix}_no_unsupported_claim_shape",
            bool(evidence.get("explanation")) and not _contains_empty_numeric_claim(insight),
            summary=insight.get("summary"),
            evidence_explanation=evidence.get("explanation"),
        ),
    ]
    return checks


def _find_insight(
    insights: list[dict[str, Any]],
    *,
    insight_type: str,
    required_columns: list[str] | None = None,
    metric: str | None = None,
) -> dict[str, Any] | None:
    required = set(required_columns or [])
    for insight in insights:
        evidence = insight.get("evidence") or {}
        if insight.get("insight_type") != insight_type:
            continue
        if metric is not None and evidence.get("metric") != metric:
            continue
        if required and not required.issubset(set(evidence.get("columns", []))):
            continue
        return insight
    return None


def _check(name: str, passed: bool, **details: Any) -> Check:
    normalized_passed = bool(passed)
    return Check(
        name=name,
        passed=normalized_passed,
        score=1.0 if normalized_passed else 0.0,
        details=_jsonable(details),
    )


def _looks_actionable(value: str | None) -> bool:
    if not value:
        return False
    lowered = value.lower()
    verbs = ("review", "compare", "inspect", "check", "use", "resolve", "document", "separate")
    return any(verb in lowered for verb in verbs) and len(value.split()) >= 8


def _contains_empty_numeric_claim(insight: dict[str, Any]) -> bool:
    text = f"{insight.get('summary', '')} {insight.get('recommendation', '')}"
    return bool(NUMBER_PATTERN.search(text)) and not insight.get("evidence")


def _safe_response_body(response: Any) -> str:
    try:
        return json.dumps(response.json(), ensure_ascii=True)
    except Exception:
        return response.text[:500]


def _raise_for_eval(response: Any, action: str) -> None:
    if response.status_code >= 400:
        raise RuntimeError(f"Could not {action}: HTTP {response.status_code} {response.text}")


def _jsonable(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    if isinstance(value, tuple):
        return [_jsonable(item) for item in value]
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None
    if hasattr(value, "item"):
        return _jsonable(value.item())
    return value


if __name__ == "__main__":
    raise SystemExit(main())
