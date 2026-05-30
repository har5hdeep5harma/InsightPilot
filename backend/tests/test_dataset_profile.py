from collections.abc import Generator
import json
from types import SimpleNamespace

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import get_settings
from app.db.init_db import init_database
from app.db.session import get_db
from app.main import app
from app.services.profiling.dataset_profiler import profile_dataset_artifact


def test_profile_endpoint_infers_types_roles_and_warnings(tmp_path) -> None:
    client = _test_client(tmp_path)
    try:
        with client as test_client:
            response = test_client.post(
                "/api/datasets/upload",
                files={
                    "file": (
                        "profile.csv",
                        _profile_csv().encode("utf-8"),
                        "text/csv",
                    )
                },
            )
            assert response.status_code == 200
            dataset_id = response.json()["dataset_id"]

            profile_response = test_client.get(f"/api/datasets/{dataset_id}/profile")
    finally:
        app.dependency_overrides.clear()

    assert profile_response.status_code == 200
    profile = profile_response.json()
    columns = {column["name"]: column for column in profile["columns"]}

    assert profile["dataset_id"] == dataset_id
    assert profile["row_count"] == 10
    assert profile["column_count"] == 8
    assert profile["duplicate_row_count"] == 0
    assert 0 <= profile["quality_score"] <= 100
    assert "revenue" in profile["numeric_columns"]
    assert "region" in profile["categorical_columns"]
    assert "order_date" in profile["datetime_columns"]
    assert "order_id" in profile["id_like_columns"]
    assert "notes" in profile["text_columns"]

    assert columns["revenue"]["inferred_type"] == "numeric"
    assert columns["revenue"]["role"] == "metric"
    assert columns["revenue"]["mean"] == 593.6
    assert columns["region"]["inferred_type"] == "categorical"
    assert columns["region"]["role"] == "dimension"
    assert columns["order_date"]["inferred_type"] == "datetime"
    assert columns["order_date"]["role"] == "datetime"
    assert columns["is_returned"]["inferred_type"] == "boolean"
    assert columns["order_id"]["role"] == "id"
    assert columns["notes"]["role"] == "text"
    assert columns["mostly_missing"]["role"] == "ignored"

    assert _has_warning(columns["mostly_missing"], "HIGH_MISSINGNESS")
    assert _has_warning(columns["mostly_missing"], "MOSTLY_MISSING_COLUMN")
    assert _has_warning(columns["constant"], "CONSTANT_COLUMN")
    assert _has_warning(columns["order_id"], "POSSIBLE_ID_COLUMN")
    assert _has_warning(columns["revenue"], "SKEWED_DISTRIBUTION")


def test_profiler_detects_duplicates_text_numerics_and_suspicious_dates(tmp_path) -> None:
    artifact_path = tmp_path / "parsed_dataset.json"
    artifact_path.write_text(
        json.dumps(
            {
                "dataset_id": "ds_profile_direct",
                "columns": [
                    {"name": "sale_date", "original_name": "Sale Date"},
                    {"name": "amount_text", "original_name": "Amount Text"},
                    {"name": "customer_number", "original_name": "Customer Number"},
                ],
                "rows": [
                    {
                        "sale_date": "2026-01-01",
                        "amount_text": "100",
                        "customer_number": "1001",
                    },
                    {
                        "sale_date": "2026-01-02",
                        "amount_text": "200",
                        "customer_number": "1002",
                    },
                    {
                        "sale_date": "not a date",
                        "amount_text": "300",
                        "customer_number": "1003",
                    },
                    {
                        "sale_date": "not a date",
                        "amount_text": "300",
                        "customer_number": "1003",
                    },
                ],
            }
        ),
        encoding="utf-8",
    )

    profile = profile_dataset_artifact("ds_profile_direct", str(artifact_path))
    columns = {column.name: column for column in profile.columns}

    assert profile.duplicate_row_count == 1
    assert any(warning.code == "DUPLICATE_ROWS" for warning in profile.warnings)
    assert columns["amount_text"].inferred_type == "numeric"
    assert columns["amount_text"].role == "metric"
    assert any(
        warning.code == "NUMERIC_STORED_AS_TEXT"
        for warning in columns["amount_text"].warnings
    )
    assert any(
        warning.code == "SUSPICIOUS_DATE_PARSING"
        for warning in columns["sale_date"].warnings
    )
    assert columns["customer_number"].role == "id"
    assert any(
        warning.code == "POSSIBLE_ID_COLUMN"
        for warning in columns["customer_number"].warnings
    )


def _test_client(tmp_path) -> TestClient:
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

    return TestClient(app)


def _profile_csv() -> str:
    long_note = (
        "This customer note is intentionally long enough to be treated as "
        "free-form text rather than a compact category."
    )
    rows = [
        "order_id,order_date,region,revenue,is_returned,notes,mostly_missing,constant",
        f"ORD-001,2026-01-01,West,100,false,{long_note},present,same",
        f"ORD-002,2026-01-02,East,101,false,{long_note},,same",
        f"ORD-003,2026-01-03,West,102,false,{long_note},,same",
        f"ORD-004,2026-01-04,South,103,true,{long_note},,same",
        f"ORD-005,2026-01-05,North,104,false,{long_note},,same",
        f"ORD-006,2026-01-06,West,105,false,{long_note},,same",
        f"ORD-007,2026-01-07,East,106,false,{long_note},,same",
        f"ORD-008,2026-01-08,South,107,false,{long_note},,same",
        f"ORD-009,2026-01-09,North,108,true,{long_note},,same",
        f"ORD-010,2026-01-10,West,5000,false,{long_note},,same",
    ]
    return "\n".join(rows)


def _has_warning(column: dict[str, object], code: str) -> bool:
    warnings = column.get("warnings")
    assert isinstance(warnings, list)
    return any(warning.get("code") == code for warning in warnings)
