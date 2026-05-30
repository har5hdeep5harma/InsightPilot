from collections.abc import Generator
from contextlib import contextmanager
from types import SimpleNamespace

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import get_settings
from app.db.init_db import init_database
from app.db.session import get_db
from app.main import app


def test_report_generation_and_retrieval_are_evidence_backed(tmp_path) -> None:
    with _test_client(tmp_path) as client:
        upload_response = client.post(
            "/api/datasets/upload",
            files={
                "file": (
                    "memo_dataset.csv",
                    _memo_dataset_csv().encode("utf-8"),
                    "text/csv",
                )
            },
        )
        assert upload_response.status_code == 200
        dataset_id = upload_response.json()["dataset_id"]

        report_response = client.post(f"/api/datasets/{dataset_id}/report")

        assert report_response.status_code == 200
        report = report_response.json()
        retrieved_response = client.get(f"/api/reports/{report['report_id']}")

    assert retrieved_response.status_code == 200
    retrieved = retrieved_response.json()
    assert retrieved == report

    assert report["report_id"].startswith("report_")
    assert report["title"] == "Executive Analysis Memo: memo_dataset.csv"
    assert "13 rows" in report["dataset_overview"]
    assert "8 columns" in report["dataset_overview"]
    assert report["executive_summary"]
    assert "data-driven insights" not in report["executive_summary"].lower()
    assert report["key_findings"]
    assert report["risks"]
    assert report["opportunities"]
    assert report["recommendations"]
    assert "data_quality_notes" in report
    assert report["chart_ids"]
    assert report["evidence_appendix"]

    for finding in report["key_findings"]:
        assert "Evidence:" in finding

    appendix_item = report["evidence_appendix"][0]
    assert appendix_item["insight_id"].startswith("ins_")
    assert appendix_item["insight_title"]
    assert appendix_item["evidence"]["calculation"]
    assert appendix_item["evidence"]["explanation"]


def test_report_generation_with_ai_enabled_without_key_uses_deterministic_report(tmp_path) -> None:
    with _test_client(tmp_path, enable_ai_narrative=True) as client:
        upload_response = client.post(
            "/api/datasets/upload",
            files={
                "file": (
                    "memo_dataset.csv",
                    _memo_dataset_csv().encode("utf-8"),
                    "text/csv",
                )
            },
        )
        dataset_id = upload_response.json()["dataset_id"]

        report_response = client.post(f"/api/datasets/{dataset_id}/report")

    assert report_response.status_code == 200
    report = report_response.json()
    assert report["title"] == "Executive Analysis Memo: memo_dataset.csv"
    assert report["executive_summary"]
    assert report["evidence_appendix"]


def test_report_html_export_returns_downloadable_report(tmp_path) -> None:
    with _test_client(tmp_path) as client:
        upload_response = client.post(
            "/api/datasets/upload",
            files={
                "file": (
                    "memo_dataset.csv",
                    _memo_dataset_csv().encode("utf-8"),
                    "text/csv",
                )
            },
        )
        dataset_id = upload_response.json()["dataset_id"]
        report_response = client.post(f"/api/datasets/{dataset_id}/report")
        report = report_response.json()

        export_response = client.get(
            f"/api/reports/{report['report_id']}/export/html"
        )

    assert export_response.status_code == 200
    assert "text/html" in export_response.headers["content-type"]
    assert "attachment" in export_response.headers["content-disposition"]
    assert ".html" in export_response.headers["content-disposition"]

    html = export_response.text
    assert "<!doctype html>" in html
    assert "InsightPilot Executive Report" in html
    assert "Executive Analysis Memo: memo_dataset.csv" in html
    assert "Dataset overview" in html
    assert "Executive summary" in html
    assert "Key findings" in html
    assert "Risks" in html
    assert "Opportunities" in html
    assert "Recommended actions" in html
    assert "Data quality notes" in html
    assert "Charts included" in html
    assert "Exhibit 1" in html
    assert "Recommendation logic" not in html
    assert "<svg" in html or "bar-row" in html or "chart-table" in html
    assert "Evidence appendix" in html
    assert "Generated" in html
    assert '"evidence":' not in html


def test_report_pdf_export_returns_downloadable_pdf(tmp_path) -> None:
    with _test_client(tmp_path) as client:
        upload_response = client.post(
            "/api/datasets/upload",
            files={
                "file": (
                    "memo_dataset.csv",
                    _memo_dataset_csv().encode("utf-8"),
                    "text/csv",
                )
            },
        )
        dataset_id = upload_response.json()["dataset_id"]
        report_response = client.post(f"/api/datasets/{dataset_id}/report")
        report = report_response.json()

        export_response = client.get(
            f"/api/reports/{report['report_id']}/export/pdf"
        )

    assert export_response.status_code == 200
    assert export_response.headers["content-type"] == "application/pdf"
    assert "attachment" in export_response.headers["content-disposition"]
    assert ".pdf" in export_response.headers["content-disposition"]
    assert export_response.content.startswith(b"%PDF")
    assert len(export_response.content) > 1000


def test_report_not_found_returns_structured_error(tmp_path) -> None:
    with _test_client(tmp_path) as client:
        response = client.get("/api/reports/report_missing")

    assert response.status_code == 404
    payload = response.json()
    assert payload["error"]["code"] == "REPORT_NOT_FOUND"
    assert payload["error"]["suggested_fix"]


def test_report_html_export_not_found_returns_structured_error(tmp_path) -> None:
    with _test_client(tmp_path) as client:
        response = client.get("/api/reports/report_missing/export/html")

    assert response.status_code == 404
    payload = response.json()
    assert payload["error"]["code"] == "REPORT_NOT_FOUND"
    assert payload["error"]["suggested_fix"]


def test_report_pdf_export_not_found_returns_structured_error(tmp_path) -> None:
    with _test_client(tmp_path) as client:
        response = client.get("/api/reports/report_missing/export/pdf")

    assert response.status_code == 404
    payload = response.json()
    assert payload["error"]["code"] == "REPORT_NOT_FOUND"
    assert payload["error"]["suggested_fix"]


@contextmanager
def _test_client(
    tmp_path,
    *,
    enable_ai_narrative: bool = False,
) -> Generator[TestClient, None, None]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    init_database(engine)
    session_factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    def override_get_db() -> Generator[Session, None, None]:
        session = session_factory()
        try:
            yield session
        finally:
            session.close()

    settings = SimpleNamespace(
        upload_dir=str(tmp_path / "uploads"),
        max_upload_mb=1,
        preview_row_limit=20,
        enable_ai_narrative=enable_ai_narrative,
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


def _memo_dataset_csv() -> str:
    rows = [
        "order_id,order_date,region,channel,revenue,ad_spend,profit,cost",
        "ORD-001,2026-01-01,East,Online,100,50,30,70",
        "ORD-002,2026-01-02,East,Online,120,60,36,",
        "ORD-002,2026-01-02,East,Online,120,60,36,",
        "ORD-003,2026-01-03,South,Online,140,70,42,",
        "ORD-004,2026-01-04,South,Partner,160,80,48,100",
        "ORD-005,2026-01-05,North,Partner,180,90,54,",
        "ORD-006,2026-01-06,North,Direct,200,100,60,130",
        "ORD-007,2026-01-07,West,Direct,800,400,240,",
        "ORD-008,2026-01-08,West,Online,900,450,270,500",
        "ORD-009,2026-01-09,West,Partner,1000,500,300,",
        "ORD-010,2026-01-10,West,Direct,1200,600,360,700",
        "ORD-011,2026-01-11,West,Online,1500,750,450,900",
        "ORD-012,2026-01-12,West,Partner,5000,2500,1500,3000",
    ]
    return "\n".join(rows)
