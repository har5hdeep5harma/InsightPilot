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


def test_recommends_time_series_for_date_and_revenue(tmp_path) -> None:
    with _test_client(tmp_path) as client:
        dataset_id = _upload_csv(client, "time_series.csv", _time_series_csv())
        response = client.get(f"/api/datasets/{dataset_id}/charts")

    assert response.status_code == 200
    charts = response.json()
    line_chart = _chart_by_type(charts, "line")
    assert line_chart is not None
    assert line_chart["x_column"] == "order_date"
    assert line_chart["y_column"] == "revenue"
    assert len(line_chart["chart_data"]) == 8
    assert line_chart["chart_data"][0]["order_date"] == "2026-01-01"
    assert line_chart["chart_data"][0]["revenue"] == 100
    assert line_chart["reasoning"]


def test_recommends_top_n_bar_for_categories_and_sales(tmp_path) -> None:
    with _test_client(tmp_path) as client:
        dataset_id = _upload_csv(client, "categories.csv", _categories_csv())
        response = client.get(f"/api/datasets/{dataset_id}/charts")

    assert response.status_code == 200
    charts = response.json()
    bar_chart = _chart_by_type(charts, "bar")
    assert bar_chart is not None
    assert bar_chart["x_column"] == "product_category"
    assert bar_chart["y_column"] == "sales"
    assert 2 <= len(bar_chart["chart_data"]) <= 11
    assert bar_chart["chart_data"][0]["sales"] >= bar_chart["chart_data"][1]["sales"]

    concentration_chart = _chart_by_type(charts, "horizontal_bar")
    assert concentration_chart is not None
    assert concentration_chart["chart_data"]
    assert concentration_chart["reasoning"]


def test_recommends_scatter_and_correlation_for_numeric_pairs(tmp_path) -> None:
    with _test_client(tmp_path) as client:
        dataset_id = _upload_csv(client, "numeric_pairs.csv", _numeric_pairs_csv())
        response = client.get(f"/api/datasets/{dataset_id}/charts")

    assert response.status_code == 200
    charts = response.json()
    chart_types = {chart["chart_type"] for chart in charts}
    assert "scatter" in chart_types
    assert "correlation_heatmap" in chart_types

    scatter = _chart_by_type(charts, "scatter")
    assert scatter is not None
    assert scatter["x_column"] in {"ad_spend", "revenue", "profit"}
    assert scatter["y_column"] in {"ad_spend", "revenue", "profit"}
    assert len(scatter["chart_data"]) >= 5

    heatmap = _chart_by_type(charts, "correlation_heatmap")
    assert heatmap is not None
    assert heatmap["x_column"] == "metric_x"
    assert heatmap["y_column"] == "metric_y"
    assert len(heatmap["chart_data"]) >= 9


def test_returns_no_charts_for_too_few_usable_columns(tmp_path) -> None:
    with _test_client(tmp_path) as client:
        dataset_id = _upload_csv(client, "too_few.csv", _too_few_usable_columns_csv())
        response = client.get(f"/api/datasets/{dataset_id}/charts")

    assert response.status_code == 200
    assert response.json() == []


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


def _upload_csv(client: TestClient, filename: str, csv_text: str) -> str:
    response = client.post(
        "/api/datasets/upload",
        files={"file": (filename, csv_text.encode("utf-8"), "text/csv")},
    )
    assert response.status_code == 200
    return response.json()["dataset_id"]


def _chart_by_type(charts: list[dict[str, object]], chart_type: str):
    return next((chart for chart in charts if chart["chart_type"] == chart_type), None)


def _time_series_csv() -> str:
    rows = ["order_date,region,revenue,cost"]
    for index, revenue in enumerate([100, 140, 160, 200, 260, 300, 340, 420], start=1):
        rows.append(f"2026-01-{index:02d},West,{revenue},{round(revenue * 0.4, 2)}")
    return "\n".join(rows)


def _categories_csv() -> str:
    rows = ["product_category,channel,sales"]
    categories = [
        ("Software", "Online", 900),
        ("Software", "Direct", 820),
        ("Software", "Partner", 780),
        ("Hardware", "Online", 420),
        ("Hardware", "Direct", 380),
        ("Services", "Partner", 360),
        ("Accessories", "Online", 180),
        ("Training", "Direct", 150),
        ("Support", "Partner", 120),
        ("Consulting", "Direct", 110),
        ("Licensing", "Online", 90),
        ("Other Tools", "Partner", 80),
        ("Data Packs", "Online", 70),
    ]
    rows.extend(f"{category},{channel},{sales}" for category, channel, sales in categories)
    return "\n".join(rows)


def _numeric_pairs_csv() -> str:
    rows = ["ad_spend,revenue,profit"]
    for index in range(1, 13):
        ad_spend = index * 100
        revenue = index * 260 + (index % 3) * 35
        profit = revenue - ad_spend * 0.55
        rows.append(f"{ad_spend},{revenue},{round(profit, 2)}")
    return "\n".join(rows)


def _too_few_usable_columns_csv() -> str:
    rows = ["order_id,notes"]
    for index in range(1, 6):
        rows.append(
            "ORD-{0:03d},This is a long free-form operational note number {0} "
            "that should not be treated as a compact categorical dimension.".format(index)
        )
    return "\n".join(rows)
