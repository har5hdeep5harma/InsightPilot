from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.db.repositories import get_report
from app.db.session import get_db
from app.models.report import ReportResponse
from app.services.export.html_report import render_report_html, report_html_filename
from app.services.export.pdf_report import render_report_pdf, report_pdf_filename
from app.services.reports.memo_generator import report_to_response

router = APIRouter(prefix="/api/reports", tags=["reports"])


@router.get("/{report_id}", response_model=ReportResponse)
def get_report_by_id(
    report_id: str,
    db: Session = Depends(get_db),
) -> ReportResponse:
    report = get_report(db, report_id)
    if report is None:
        raise AppError(
            status_code=404,
            code="REPORT_NOT_FOUND",
            message="No report was found for the provided report_id.",
            technical_detail=f"Report id '{report_id}' does not exist in SQLite.",
            suggested_fix="Generate a report for a dataset first, then use the returned report_id.",
        )

    return report_to_response(report)


@router.get("/{report_id}/export/html")
def export_report_html(
    report_id: str,
    db: Session = Depends(get_db),
) -> Response:
    report = get_report(db, report_id)
    if report is None:
        raise AppError(
            status_code=404,
            code="REPORT_NOT_FOUND",
            message="No report was found for the provided report_id.",
            technical_detail=f"Report id '{report_id}' does not exist in SQLite.",
            suggested_fix="Generate a report for a dataset first, then export it.",
        )

    html = render_report_html(report)
    filename = report_html_filename(report)
    return Response(
        content=html,
        media_type="text/html; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/{report_id}/export/pdf")
def export_report_pdf(
    report_id: str,
    db: Session = Depends(get_db),
) -> Response:
    report = get_report(db, report_id)
    if report is None:
        raise AppError(
            status_code=404,
            code="REPORT_NOT_FOUND",
            message="No report was found for the provided report_id.",
            technical_detail=f"Report id '{report_id}' does not exist in SQLite.",
            suggested_fix="Generate a report for a dataset first, then export it.",
        )

    pdf = render_report_pdf(report)
    filename = report_pdf_filename(report)
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
