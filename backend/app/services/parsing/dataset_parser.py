from __future__ import annotations

import csv
import io
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import uuid4
from xml.etree import ElementTree
from zipfile import BadZipFile, ZipFile

import pandas as pd
from pandas.errors import EmptyDataError, ParserError

from app.core.errors import AppError
from app.models.common import AnalysisWarning
from app.models.upload import DatasetColumn


SUPPORTED_EXTENSIONS = {".csv", ".xlsx"}
CSV_ENCODINGS = ("utf-8-sig", "utf-8", "utf-16", "cp1252", "latin-1")


@dataclass(frozen=True)
class ParsedDataset:
    dataset_id: str
    filename: str
    original_filename: str
    file_type: str
    file_size_bytes: int
    row_count: int
    column_count: int
    columns: list[DatasetColumn]
    preview_rows: list[dict[str, Any]]
    warnings: list[AnalysisWarning]
    stored_file_path: str
    artifact_path: str


def parse_and_store_upload(
    *,
    original_filename: str | None,
    file_bytes: bytes,
    upload_dir: str,
    max_upload_mb: int,
    preview_limit: int = 20,
) -> ParsedDataset:
    filename = _safe_filename(original_filename)
    suffix = Path(filename).suffix.lower()

    if suffix not in SUPPORTED_EXTENSIONS:
        raise AppError(
            status_code=415,
            code="UNSUPPORTED_FILE_TYPE",
            message="Only CSV and XLSX files are supported.",
            technical_detail=f"Received file extension '{suffix or 'none'}'.",
            suggested_fix="Upload a .csv or .xlsx file exported from your spreadsheet tool.",
        )

    if not file_bytes:
        raise AppError(
            status_code=422,
            code="EMPTY_FILE",
            message="The uploaded file is empty.",
            technical_detail="The request body contained zero file bytes.",
            suggested_fix="Choose a CSV or XLSX file that contains a header row and data rows.",
        )

    max_bytes = max_upload_mb * 1024 * 1024
    if len(file_bytes) > max_bytes:
        raise AppError(
            status_code=413,
            code="FILE_TOO_LARGE",
            message=f"The file is larger than the {max_upload_mb} MB local MVP limit.",
            technical_detail=f"Received {len(file_bytes)} bytes; limit is {max_bytes} bytes.",
            suggested_fix="Use a smaller extract for local analysis or reduce unnecessary columns.",
        )

    if suffix == ".csv":
        dataframe, raw_headers, warnings = _read_csv(file_bytes)
        file_type = "csv"
    else:
        dataframe, raw_headers, warnings = _read_xlsx(file_bytes)
        file_type = "xlsx"

    _validate_dataframe(dataframe)
    columns, column_warnings = _normalize_columns(raw_headers, dataframe)
    warnings.extend(column_warnings)
    dataframe.columns = [column.name for column in columns]

    dataset_id = f"ds_{uuid4().hex}"
    dataset_dir = Path(upload_dir).resolve() / dataset_id
    dataset_dir.mkdir(parents=True, exist_ok=True)

    stored_file_path = dataset_dir / f"original{suffix}"
    stored_file_path.write_bytes(file_bytes)

    rows = _dataframe_rows(dataframe)
    artifact = {
        "dataset_id": dataset_id,
        "filename": filename,
        "columns": [column.model_dump(mode="json") for column in columns],
        "row_count": len(rows),
        "column_count": len(columns),
        "rows": rows,
        "warnings": [warning.model_dump(mode="json") for warning in warnings],
    }
    artifact_path = dataset_dir / "parsed_dataset.json"
    artifact_path.write_text(json.dumps(artifact, ensure_ascii=True), encoding="utf-8")

    return ParsedDataset(
        dataset_id=dataset_id,
        filename=filename,
        original_filename=original_filename or filename,
        file_type=file_type,
        file_size_bytes=len(file_bytes),
        row_count=len(dataframe.index),
        column_count=len(dataframe.columns),
        columns=columns,
        preview_rows=rows[:preview_limit],
        warnings=warnings,
        stored_file_path=str(stored_file_path),
        artifact_path=str(artifact_path),
    )


def load_artifact_rows(
    artifact_path: str,
    *,
    limit: int = 20,
    offset: int = 0,
) -> tuple[list[DatasetColumn], list[dict[str, Any]], int]:
    path = Path(artifact_path)
    if not path.exists():
        raise AppError(
            status_code=410,
            code="DATASET_ARTIFACT_MISSING",
            message="The parsed dataset artifact is missing.",
            technical_detail=f"Expected parsed artifact at {artifact_path}.",
            suggested_fix="Upload the dataset again so InsightPilot can recreate the parsed artifact.",
        )

    payload = json.loads(path.read_text(encoding="utf-8"))
    columns = [
        DatasetColumn.model_validate(column) for column in payload.get("columns", [])
    ]
    rows = payload.get("rows", [])
    total_rows = int(payload.get("row_count", len(rows)))
    return columns, rows[offset : offset + limit], total_rows


def _safe_filename(filename: str | None) -> str:
    raw_filename = Path(filename or "uploaded_dataset").name.strip()
    if not raw_filename:
        return "uploaded_dataset"
    return raw_filename


def _read_csv(
    file_bytes: bytes,
) -> tuple[pd.DataFrame, list[Any], list[AnalysisWarning]]:
    decode_errors: list[str] = []
    parser_errors: list[str] = []

    for encoding in CSV_ENCODINGS:
        try:
            decoded = file_bytes.decode(encoding)
            if "\x00" in decoded and encoding != "utf-16":
                decode_errors.append(f"{encoding}: decoded text contains null bytes")
                continue
            raw_headers = _csv_headers(decoded)
            dataframe = pd.read_csv(
                io.BytesIO(file_bytes),
                encoding=encoding,
                header=0,
                engine="python",
                on_bad_lines="error",
            )
            warnings: list[AnalysisWarning] = []
            if encoding not in {"utf-8-sig", "utf-8"}:
                warnings.append(
                    AnalysisWarning(
                        code="CSV_ENCODING_FALLBACK",
                        message=f"Parsed CSV using {encoding} encoding.",
                        details={"encoding": encoding},
                    )
                )
            return dataframe, raw_headers, warnings
        except UnicodeDecodeError as exc:
            decode_errors.append(f"{encoding}: {exc}")
        except ParserError as exc:
            parser_errors.append(f"{encoding}: {exc}")
            break
        except EmptyDataError:
            raise AppError(
                status_code=422,
                code="EMPTY_FILE",
                message="The uploaded CSV does not contain readable data.",
                technical_detail="pandas raised EmptyDataError while reading the CSV.",
                suggested_fix="Export the spreadsheet again with a header row and at least one data row.",
            ) from None
        except csv.Error as exc:
            parser_errors.append(f"{encoding}: {exc}")
            break

    if parser_errors:
        raise AppError(
            status_code=422,
            code="MALFORMED_CSV",
            message="The uploaded CSV could not be parsed.",
            technical_detail="; ".join(parser_errors),
            suggested_fix="Check for unclosed quotes, inconsistent delimiters, or broken rows, then export the CSV again.",
        )

    raise AppError(
        status_code=422,
        code="UNSUPPORTED_ENCODING",
        message="The CSV encoding is not supported.",
        technical_detail="; ".join(decode_errors),
        suggested_fix="Save the file as UTF-8 CSV and upload it again.",
    )


def _csv_headers(decoded_csv: str) -> list[Any]:
    try:
        reader = csv.reader(io.StringIO(decoded_csv), strict=True)
        return next(reader)
    except StopIteration:
        raise AppError(
            status_code=422,
            code="EMPTY_FILE",
            message="The uploaded CSV does not contain a header row.",
            technical_detail="csv.reader did not find any rows.",
            suggested_fix="Add a header row and at least one data row.",
        ) from None


def _read_xlsx(
    file_bytes: bytes,
) -> tuple[pd.DataFrame, list[Any], list[AnalysisWarning]]:
    try:
        workbook = pd.ExcelFile(io.BytesIO(file_bytes))
        if not workbook.sheet_names:
            raise AppError(
                status_code=422,
                code="EMPTY_WORKBOOK",
                message="The uploaded workbook does not contain any sheets.",
                technical_detail="pandas returned an empty sheet list.",
                suggested_fix="Upload an XLSX workbook with at least one visible sheet.",
            )

        sheet_name = workbook.sheet_names[0]
        header_frame = pd.read_excel(
            io.BytesIO(file_bytes),
            sheet_name=sheet_name,
            header=None,
            nrows=1,
        )
        if header_frame.empty:
            raw_headers: list[Any] = []
        else:
            raw_headers = header_frame.iloc[0].tolist()
        dataframe = pd.read_excel(
            io.BytesIO(file_bytes),
            sheet_name=sheet_name,
            header=0,
        )
        return dataframe, raw_headers, []
    except (ImportError, ModuleNotFoundError):
        dataframe, raw_headers = _read_xlsx_with_stdlib(file_bytes)
        return dataframe, raw_headers, [
            AnalysisWarning(
                code="XLSX_STDLIB_PARSER_USED",
                message="Parsed XLSX with the built-in fallback parser because the spreadsheet engine is unavailable.",
                details={"fallback": "stdlib_xlsx"},
            )
        ]
    except AppError:
        raise
    except BadZipFile as exc:
        raise AppError(
            status_code=422,
            code="MALFORMED_XLSX",
            message="The uploaded XLSX file could not be opened.",
            technical_detail=str(exc),
            suggested_fix="Open the workbook locally, save it again as .xlsx, and retry.",
        ) from exc
    except ValueError as exc:
        raise AppError(
            status_code=422,
            code="XLSX_PARSE_FAILED",
            message="The uploaded XLSX file could not be parsed.",
            technical_detail=str(exc),
            suggested_fix="Use a standard XLSX workbook with a header row on the first sheet.",
        ) from exc


def _read_xlsx_with_stdlib(file_bytes: bytes) -> tuple[pd.DataFrame, list[Any]]:
    try:
        with ZipFile(io.BytesIO(file_bytes)) as workbook:
            sheet_path = _first_sheet_path(workbook)
            shared_strings = _shared_strings(workbook)
            rows = _worksheet_rows(workbook, sheet_path, shared_strings)
    except BadZipFile as exc:
        raise AppError(
            status_code=422,
            code="MALFORMED_XLSX",
            message="The uploaded XLSX file could not be opened.",
            technical_detail=str(exc),
            suggested_fix="Open the workbook locally, save it again as .xlsx, and retry.",
        ) from exc
    except KeyError as exc:
        raise AppError(
            status_code=422,
            code="XLSX_PARSE_FAILED",
            message="The uploaded XLSX file is missing required workbook parts.",
            technical_detail=str(exc),
            suggested_fix="Save the workbook again as a standard .xlsx file and retry.",
        ) from exc

    if not rows:
        raise AppError(
            status_code=422,
            code="EMPTY_WORKBOOK",
            message="The uploaded workbook does not contain readable rows.",
            technical_detail="The fallback XLSX parser found no worksheet rows.",
            suggested_fix="Add a header row and at least one data row on the first sheet.",
        )

    raw_headers = rows[0]
    max_columns = max(len(row) for row in rows)
    normalized_rows = [row + [None] * (max_columns - len(row)) for row in rows]
    raw_headers = raw_headers + [None] * (max_columns - len(raw_headers))
    dataframe = pd.DataFrame(normalized_rows[1:], columns=raw_headers)
    return dataframe, raw_headers


def _first_sheet_path(workbook: ZipFile) -> str:
    namespace = {
        "main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
        "rel": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
        "pkgrel": "http://schemas.openxmlformats.org/package/2006/relationships",
    }
    workbook_xml = ElementTree.fromstring(workbook.read("xl/workbook.xml"))
    first_sheet = workbook_xml.find("main:sheets/main:sheet", namespace)
    if first_sheet is None:
        raise KeyError("xl/workbook.xml has no sheet entries")

    relationship_id = first_sheet.attrib[
        "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"
    ]
    relationships_xml = ElementTree.fromstring(
        workbook.read("xl/_rels/workbook.xml.rels")
    )
    for relationship in relationships_xml.findall("pkgrel:Relationship", namespace):
        if relationship.attrib.get("Id") == relationship_id:
            target = relationship.attrib["Target"]
            return f"xl/{target}" if not target.startswith("xl/") else target

    raise KeyError(f"Workbook relationship {relationship_id} was not found")


def _shared_strings(workbook: ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in workbook.namelist():
        return []

    namespace = {"main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    shared_xml = ElementTree.fromstring(workbook.read("xl/sharedStrings.xml"))
    values: list[str] = []
    for item in shared_xml.findall("main:si", namespace):
        text_parts = [
            text_node.text or ""
            for text_node in item.findall(".//main:t", namespace)
        ]
        values.append("".join(text_parts))
    return values


def _worksheet_rows(
    workbook: ZipFile,
    sheet_path: str,
    shared_strings: list[str],
) -> list[list[Any]]:
    namespace = {"main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    sheet_xml = ElementTree.fromstring(workbook.read(sheet_path))
    parsed_rows: list[list[Any]] = []

    for row in sheet_xml.findall(".//main:sheetData/main:row", namespace):
        values: list[Any] = []
        for position, cell in enumerate(row.findall("main:c", namespace)):
            cell_reference = cell.attrib.get("r")
            column_index = (
                _column_index(cell_reference)
                if cell_reference is not None
                else position
            )
            while len(values) <= column_index:
                values.append(None)
            values[column_index] = _cell_value(cell, shared_strings, namespace)
        parsed_rows.append(values)

    return parsed_rows


def _cell_value(
    cell: ElementTree.Element,
    shared_strings: list[str],
    namespace: dict[str, str],
) -> Any:
    cell_type = cell.attrib.get("t")
    if cell_type == "inlineStr":
        text_parts = [
            text_node.text or ""
            for text_node in cell.findall(".//main:t", namespace)
        ]
        return "".join(text_parts)

    value_node = cell.find("main:v", namespace)
    if value_node is None or value_node.text is None:
        return None

    raw_value = value_node.text
    if cell_type == "s":
        try:
            return shared_strings[int(raw_value)]
        except (IndexError, ValueError):
            return raw_value
    if cell_type == "b":
        return raw_value == "1"
    return _number_or_text(raw_value)


def _number_or_text(value: str) -> int | float | str:
    try:
        parsed_float = float(value)
    except ValueError:
        return value

    if parsed_float.is_integer():
        return int(parsed_float)
    return parsed_float


def _column_index(cell_reference: str) -> int:
    letters = re.match(r"([A-Z]+)", cell_reference.upper())
    if letters is None:
        return 0

    index = 0
    for letter in letters.group(1):
        index = index * 26 + (ord(letter) - ord("A") + 1)
    return index - 1


def _validate_dataframe(dataframe: pd.DataFrame) -> None:
    if dataframe.shape[1] == 0:
        raise AppError(
            status_code=422,
            code="EMPTY_DATASET",
            message="The uploaded file does not contain any columns.",
            technical_detail="The parsed dataframe has zero columns.",
            suggested_fix="Upload a file with a header row and at least one column.",
        )

    if dataframe.shape[0] == 0:
        raise AppError(
            status_code=422,
            code="EMPTY_DATASET",
            message="The uploaded file does not contain any data rows.",
            technical_detail="The parsed dataframe has column headers but zero rows.",
            suggested_fix="Add at least one data row beneath the header row.",
        )

    if dataframe.dropna(how="all").empty:
        raise AppError(
            status_code=422,
            code="EMPTY_DATASET",
            message="The uploaded file only contains empty rows.",
            technical_detail="All parsed rows were empty after removing all-null rows.",
            suggested_fix="Upload a dataset with actual cell values.",
        )


def _normalize_columns(
    raw_headers: list[Any],
    dataframe: pd.DataFrame,
) -> tuple[list[DatasetColumn], list[AnalysisWarning]]:
    warnings: list[AnalysisWarning] = []

    if len(raw_headers) != len(dataframe.columns):
        raw_headers = list(dataframe.columns)
        warnings.append(
            AnalysisWarning(
                code="HEADER_LENGTH_MISMATCH",
                message="Column headers were recovered from the parsed dataframe.",
                details={
                    "raw_header_count": len(raw_headers),
                    "parsed_column_count": len(dataframe.columns),
                },
            )
        )

    original_names = [_header_to_string(header) for header in raw_headers]
    missing_indexes = [
        index for index, name in enumerate(original_names) if not name.strip()
    ]

    if len(missing_indexes) == len(original_names):
        raise AppError(
            status_code=422,
            code="MISSING_HEADERS",
            message="The uploaded file does not have usable column headers.",
            technical_detail="Every parsed column header was blank or generated by the parser.",
            suggested_fix="Add a clear header row with names like Date, Region, Revenue, or Cost.",
        )

    if missing_indexes:
        warnings.append(
            AnalysisWarning(
                code="MISSING_COLUMN_HEADERS",
                message="Some blank column headers were replaced with generated names.",
                details={"column_indexes": missing_indexes},
            )
        )

    duplicate_names = _duplicates(
        [name.strip().casefold() for name in original_names if name.strip()]
    )
    if duplicate_names:
        warnings.append(
            AnalysisWarning(
                code="DUPLICATE_COLUMN_HEADERS",
                message="Duplicate column headers were disambiguated internally.",
                details={"duplicates": sorted(duplicate_names)},
            )
        )

    used: dict[str, int] = {}
    columns: list[DatasetColumn] = []
    for index, original_name in enumerate(original_names, start=1):
        base_name = _slugify(original_name) or f"column_{index}"
        count = used.get(base_name, 0) + 1
        used[base_name] = count
        internal_name = base_name if count == 1 else f"{base_name}_{count}"
        columns.append(
            DatasetColumn(
                name=internal_name,
                original_name=original_name,
            )
        )

    return columns, warnings


def _header_to_string(header: Any) -> str:
    if header is None or pd.isna(header):
        return ""

    text = str(header).strip()
    if re.fullmatch(r"Unnamed: \d+(_level_\d+)?", text):
        return ""
    return text


def _slugify(value: str) -> str:
    normalized = re.sub(r"[^0-9a-zA-Z]+", "_", value.strip().lower())
    return normalized.strip("_")


def _duplicates(values: list[str]) -> set[str]:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for value in values:
        if value in seen:
            duplicates.add(value)
        seen.add(value)
    return duplicates


def _dataframe_rows(dataframe: pd.DataFrame) -> list[dict[str, Any]]:
    dataframe = dataframe.copy()
    json_rows = dataframe.to_json(orient="records", date_format="iso")
    rows = json.loads(json_rows)
    return rows if isinstance(rows, list) else []
