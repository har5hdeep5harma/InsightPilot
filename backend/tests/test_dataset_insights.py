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


def test_insights_are_evidence_backed_for_known_synthetic_dataset(tmp_path) -> None:
    with _test_client(tmp_path) as client:
        upload_response = client.post(
            "/api/datasets/upload",
            files={
                "file": (
                    "known_insights.csv",
                    _known_insights_csv().encode("utf-8"),
                    "text/csv",
                )
            },
        )
        assert upload_response.status_code == 200
        dataset_id = upload_response.json()["dataset_id"]

        response = client.get(f"/api/datasets/{dataset_id}/insights")

    assert response.status_code == 200
    insights = response.json()
    assert 8 <= len(insights) <= 12

    insight_types = {insight["insight_type"] for insight in insights}
    assert "dataset_quality" in insight_types
    assert "missing_data_risk" in insight_types
    assert "trend" in insight_types
    assert "concentration" in insight_types
    assert "segment_difference" in insight_types
    assert "outlier" in insight_types
    assert "correlation" in insight_types
    assert "distribution" in insight_types

    for insight in insights:
        assert insight["title"]
        assert insight["summary"]
        assert insight["severity"] in {"low", "medium", "high"}
        assert 0 <= insight["confidence"] <= 1
        assert isinstance(insight["evidence"], dict)
        assert insight["evidence"]["calculation"]
        assert insight["evidence"]["explanation"]
        assert insight["related_columns"] is not None

    trend = _first_insight(insights, "trend")
    assert trend["evidence"]["value"] > 100
    assert trend["evidence"]["values"]["slope_direction"] == "positive"
    assert set(trend["related_columns"]) == {"order_date", "revenue"}
    assert trend["related_chart_id"]

    concentration = _first_insight(insights, "concentration")
    assert concentration["evidence"]["value"] >= 60
    assert concentration["evidence"]["values"]["top_category"] == "West"
    assert set(concentration["related_columns"]) == {"region", "revenue"}

    duplicate_quality = next(
        insight
        for insight in insights
        if insight["insight_type"] == "dataset_quality"
        and insight["evidence"]["metric"] == "duplicate_row_count"
    )
    assert duplicate_quality["evidence"]["value"] == 1
    assert duplicate_quality["evidence"]["rows_affected"] == 1

    missing_risk = _first_insight(insights, "missing_data_risk")
    assert missing_risk["evidence"]["column"] == "cost"
    assert missing_risk["evidence"]["value"] >= 5

    outlier = _first_insight(insights, "outlier")
    assert outlier["evidence"]["metric"] == "iqr_outlier_count"
    assert outlier["evidence"]["value"] >= 1

    correlation = _first_insight(insights, "correlation")
    assert abs(correlation["evidence"]["value"]) >= 0.65
    assert len(correlation["evidence"]["columns"]) == 2

    segment = _first_insight(insights, "segment_difference")
    assert segment["evidence"]["value"] >= 2
    assert set(segment["related_columns"]) == {"region", "revenue"}


@contextmanager
def _test_client(tmp_path) -> Generator[TestClient, None, None]:
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
    )

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_settings] = lambda: settings

    try:
        with TestClient(app) as client:
            yield client
    finally:
        app.dependency_overrides.clear()


def _first_insight(insights: list[dict[str, object]], insight_type: str):
    return next(insight for insight in insights if insight["insight_type"] == insight_type)


def _known_insights_csv() -> str:
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

