from collections.abc import Generator
from io import BytesIO
from html import escape
from types import SimpleNamespace
from zipfile import ZIP_DEFLATED, ZipFile

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import get_settings
from app.db.init_db import init_database
from app.db.session import get_db
from app.main import app


@pytest.fixture()
def client(tmp_path) -> Generator[TestClient, None, None]:
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

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


def test_csv_upload_stores_metadata_and_preview(client: TestClient) -> None:
    csv_bytes = b"Region,Revenue,Revenue\nWest,1200,1300\nEast,900,950\n"

    response = client.post(
        "/api/datasets/upload",
        files={"file": ("sales.csv", csv_bytes, "text/csv")},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["filename"] == "sales.csv"
    assert payload["row_count"] == 2
    assert payload["column_count"] == 3
    assert payload["columns"] == [
        {"name": "region", "original_name": "Region"},
        {"name": "revenue", "original_name": "Revenue"},
        {"name": "revenue_2", "original_name": "Revenue"},
    ]
    assert payload["preview_rows"][0]["region"] == "West"
    assert payload["warnings"][0]["code"] == "DUPLICATE_COLUMN_HEADERS"

    dataset_id = payload["dataset_id"]
    detail_response = client.get(f"/api/datasets/{dataset_id}")
    assert detail_response.status_code == 200
    assert detail_response.json()["dataset_id"] == dataset_id

    preview_response = client.get(f"/api/datasets/{dataset_id}/preview?limit=1")
    assert preview_response.status_code == 200
    preview_payload = preview_response.json()
    assert preview_payload["row_count"] == 2
    assert len(preview_payload["preview_rows"]) == 1
    assert preview_payload["preview_rows"][0]["revenue_2"] == 1300


def test_xlsx_upload_reads_first_sheet(client: TestClient) -> None:
    workbook = _xlsx_bytes(
        [
            ["Region", "Revenue"],
            ["West", 1200],
            ["East", 900],
        ]
    )

    response = client.post(
        "/api/datasets/upload",
        files={
            "file": (
                "sales.xlsx",
                workbook,
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["filename"] == "sales.xlsx"
    assert payload["row_count"] == 2
    assert payload["columns"][1] == {"name": "revenue", "original_name": "Revenue"}
    assert payload["preview_rows"][1]["revenue"] == 900


def test_empty_file_is_rejected(client: TestClient) -> None:
    response = client.post(
        "/api/datasets/upload",
        files={"file": ("empty.csv", b"", "text/csv")},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "EMPTY_FILE"
    assert response.json()["error"]["suggested_fix"]


def test_unsupported_file_is_rejected(client: TestClient) -> None:
    response = client.post(
        "/api/datasets/upload",
        files={"file": ("notes.txt", b"hello", "text/plain")},
    )

    assert response.status_code == 415
    assert response.json()["error"]["code"] == "UNSUPPORTED_FILE_TYPE"


def test_malformed_csv_is_rejected(client: TestClient) -> None:
    malformed_csv = b'Name,Revenue\n"West,1200\nEast,900\n'

    response = client.post(
        "/api/datasets/upload",
        files={"file": ("broken.csv", malformed_csv, "text/csv")},
    )

    assert response.status_code == 422
    payload = response.json()
    assert payload["error"]["code"] == "MALFORMED_CSV"
    assert payload["error"]["technical_detail"]


def _xlsx_bytes(rows: list[list[object]]) -> bytes:
    buffer = BytesIO()
    with ZipFile(buffer, "w", ZIP_DEFLATED) as workbook:
        workbook.writestr(
            "[Content_Types].xml",
            """<?xml version="1.0" encoding="UTF-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
  <Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
</Types>""",
        )
        workbook.writestr(
            "_rels/.rels",
            """<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>""",
        )
        workbook.writestr(
            "xl/workbook.xml",
            """<?xml version="1.0" encoding="UTF-8"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"
  xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <sheets>
    <sheet name="Sheet1" sheetId="1" r:id="rId1"/>
  </sheets>
</workbook>""",
        )
        workbook.writestr(
            "xl/_rels/workbook.xml.rels",
            """<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
</Relationships>""",
        )
        workbook.writestr("xl/worksheets/sheet1.xml", _sheet_xml(rows))
    return buffer.getvalue()


def _sheet_xml(rows: list[list[object]]) -> str:
    row_xml = []
    for row_index, row in enumerate(rows, start=1):
        cells = []
        for column_index, value in enumerate(row):
            reference = f"{_column_letters(column_index)}{row_index}"
            if isinstance(value, str):
                cells.append(
                    f'<c r="{reference}" t="inlineStr"><is><t>{escape(value)}</t></is></c>'
                )
            else:
                cells.append(f'<c r="{reference}"><v>{value}</v></c>')
        row_xml.append(f'<row r="{row_index}">{"".join(cells)}</row>')
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f'<sheetData>{"".join(row_xml)}</sheetData>'
        "</worksheet>"
    )


def _column_letters(index: int) -> str:
    letters = ""
    index += 1
    while index:
        index, remainder = divmod(index - 1, 26)
        letters = chr(ord("A") + remainder) + letters
    return letters
