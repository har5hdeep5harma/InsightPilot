from datetime import UTC, datetime

from fastapi import APIRouter, Depends, File, Query, UploadFile
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.errors import AppError
from app.db.repositories import (
    create_uploaded_dataset,
    get_dataset as get_dataset_model,
    get_dataset_record,
    save_chart_specs,
    save_dataset_profile,
    save_insights,
    save_report,
)
from app.db.session import get_db
from app.models.common import AnalysisWarning
from app.models.chart import ChartSpec
from app.models.dataset import Dataset, DatasetStatus, FileType
from app.models.insight import Insight
from app.models.profile import DatasetProfile
from app.models.report import ReportResponse
from app.models.upload import (
    DatasetColumn,
    DatasetDetailResponse,
    DatasetPreviewResponse,
    DatasetUploadResponse,
)
from app.services.parsing.dataset_parser import (
    load_artifact_rows,
    parse_and_store_upload,
)
from app.services.charts.chart_recommender import recommend_charts
from app.services.insights.insight_generator import generate_insights
from app.services.profiling.dataset_profiler import profile_dataset_artifact
from app.services.reports.memo_generator import (
    generate_executive_report,
    report_to_response,
)

router = APIRouter(prefix="/api/datasets", tags=["datasets"])


@router.post("/upload", response_model=DatasetUploadResponse)
async def upload_dataset(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> DatasetUploadResponse:
    file_bytes = await file.read()
    parsed_dataset = parse_and_store_upload(
        original_filename=file.filename,
        file_bytes=file_bytes,
        upload_dir=settings.upload_dir,
        max_upload_mb=settings.max_upload_mb,
        preview_limit=settings.preview_row_limit,
    )

    dataset = Dataset(
        id=parsed_dataset.dataset_id,
        filename=parsed_dataset.filename,
        original_filename=parsed_dataset.original_filename,
        file_type=FileType(parsed_dataset.file_type),
        row_count=parsed_dataset.row_count,
        column_count=parsed_dataset.column_count,
        uploaded_at=datetime.now(UTC),
        status=DatasetStatus.parsed,
    )
    create_uploaded_dataset(
        db,
        dataset,
        file_size_bytes=parsed_dataset.file_size_bytes,
        stored_file_path=parsed_dataset.stored_file_path,
        artifact_path=parsed_dataset.artifact_path,
        columns=parsed_dataset.columns,
        warnings=parsed_dataset.warnings,
    )

    return DatasetUploadResponse(
        dataset_id=parsed_dataset.dataset_id,
        filename=parsed_dataset.filename,
        row_count=parsed_dataset.row_count,
        column_count=parsed_dataset.column_count,
        columns=parsed_dataset.columns,
        preview_rows=parsed_dataset.preview_rows,
        warnings=parsed_dataset.warnings,
    )


@router.get("/{dataset_id}", response_model=DatasetDetailResponse)
def get_dataset(
    dataset_id: str,
    db: Session = Depends(get_db),
) -> DatasetDetailResponse:
    record = _dataset_record_or_404(db, dataset_id)

    return DatasetDetailResponse(
        dataset_id=record.id,
        filename=record.filename,
        original_filename=record.original_filename,
        file_type=FileType(record.file_type),
        row_count=record.row_count,
        column_count=record.column_count,
        uploaded_at=record.uploaded_at,
        status=DatasetStatus(record.status),
        error_message=record.error_message,
        columns=[
            DatasetColumn.model_validate(column)
            for column in record.column_metadata or []
        ],
        warnings=[
            AnalysisWarning.model_validate(warning)
            for warning in record.warnings or []
        ],
    )


@router.get("/{dataset_id}/preview", response_model=DatasetPreviewResponse)
def get_dataset_preview(
    dataset_id: str,
    limit: int = Query(default=20, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> DatasetPreviewResponse:
    record = _dataset_record_or_404(db, dataset_id)
    if not record.artifact_path:
        raise AppError(
            status_code=410,
            code="DATASET_ARTIFACT_MISSING",
            message="The parsed dataset artifact is missing.",
            technical_detail="The dataset row exists but artifact_path is empty.",
            suggested_fix="Upload the dataset again so InsightPilot can recreate the parsed artifact.",
        )

    columns, preview_rows, row_count = load_artifact_rows(
        record.artifact_path,
        limit=limit,
        offset=offset,
    )
    return DatasetPreviewResponse(
        dataset_id=record.id,
        columns=columns,
        preview_rows=preview_rows,
        limit=limit,
        offset=offset,
        row_count=row_count,
    )


@router.get("/{dataset_id}/profile", response_model=DatasetProfile)
def get_dataset_profile(
    dataset_id: str,
    db: Session = Depends(get_db),
):
    record = _dataset_record_or_404(db, dataset_id)
    if not record.artifact_path:
        raise AppError(
            status_code=410,
            code="DATASET_ARTIFACT_MISSING",
            message="The parsed dataset artifact is missing.",
            technical_detail="The dataset row exists but artifact_path is empty.",
            suggested_fix="Upload the dataset again so InsightPilot can recreate the parsed artifact.",
        )

    profile = profile_dataset_artifact(record.id, record.artifact_path)
    return save_dataset_profile(db, profile)


@router.get("/{dataset_id}/charts", response_model=list[ChartSpec])
def get_dataset_charts(
    dataset_id: str,
    db: Session = Depends(get_db),
) -> list[ChartSpec]:
    record = _dataset_record_or_404(db, dataset_id)
    if not record.artifact_path:
        raise AppError(
            status_code=410,
            code="DATASET_ARTIFACT_MISSING",
            message="The parsed dataset artifact is missing.",
            technical_detail="The dataset row exists but artifact_path is empty.",
            suggested_fix="Upload the dataset again so InsightPilot can recreate the parsed artifact.",
        )

    profile = profile_dataset_artifact(record.id, record.artifact_path)
    save_dataset_profile(db, profile)
    chart_specs = recommend_charts(
        dataset_id=record.id,
        artifact_path=record.artifact_path,
        profile=profile,
    )
    return save_chart_specs(db, record.id, chart_specs)


@router.get("/{dataset_id}/insights", response_model=list[Insight])
def get_dataset_insights(
    dataset_id: str,
    db: Session = Depends(get_db),
) -> list[Insight]:
    record = _dataset_record_or_404(db, dataset_id)
    if not record.artifact_path:
        raise AppError(
            status_code=410,
            code="DATASET_ARTIFACT_MISSING",
            message="The parsed dataset artifact is missing.",
            technical_detail="The dataset row exists but artifact_path is empty.",
            suggested_fix="Upload the dataset again so InsightPilot can recreate the parsed artifact.",
        )

    profile = profile_dataset_artifact(record.id, record.artifact_path)
    save_dataset_profile(db, profile)
    chart_specs = recommend_charts(
        dataset_id=record.id,
        artifact_path=record.artifact_path,
        profile=profile,
    )
    persisted_charts = save_chart_specs(db, record.id, chart_specs)
    insights = generate_insights(
        dataset_id=record.id,
        artifact_path=record.artifact_path,
        profile=profile,
        charts=persisted_charts,
    )
    return save_insights(db, record.id, insights)


@router.post("/{dataset_id}/report", response_model=ReportResponse)
def create_dataset_report(
    dataset_id: str,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> ReportResponse:
    record = _dataset_record_or_404(db, dataset_id)
    dataset = get_dataset_model(db, dataset_id)
    if dataset is None:
        raise AppError(
            status_code=404,
            code="DATASET_NOT_FOUND",
            message="No dataset was found for the provided dataset_id.",
            technical_detail=f"Dataset id '{dataset_id}' does not exist in SQLite.",
            suggested_fix="Upload a dataset first, then use the returned dataset_id.",
        )
    if not record.artifact_path:
        raise AppError(
            status_code=410,
            code="DATASET_ARTIFACT_MISSING",
            message="The parsed dataset artifact is missing.",
            technical_detail="The dataset row exists but artifact_path is empty.",
            suggested_fix="Upload the dataset again so InsightPilot can recreate the parsed artifact.",
        )

    profile = profile_dataset_artifact(record.id, record.artifact_path)
    persisted_profile = save_dataset_profile(db, profile)
    charts = recommend_charts(
        dataset_id=record.id,
        artifact_path=record.artifact_path,
        profile=persisted_profile,
    )
    persisted_charts = save_chart_specs(db, record.id, charts)
    insights = generate_insights(
        dataset_id=record.id,
        artifact_path=record.artifact_path,
        profile=persisted_profile,
        charts=persisted_charts,
    )
    persisted_insights = save_insights(db, record.id, insights)
    report = generate_executive_report(
        dataset=dataset,
        profile=persisted_profile,
        charts=persisted_charts,
        insights=persisted_insights,
        enable_ai_narrative=settings.enable_ai_narrative,
        ai_narrative_api_key=settings.ai_narrative_api_key,
        ai_narrative_base_url=settings.ai_narrative_base_url,
        ai_narrative_model=settings.ai_narrative_model,
    )
    persisted_report = save_report(db, report)
    return report_to_response(persisted_report)


def _dataset_record_or_404(db: Session, dataset_id: str):
    record = get_dataset_record(db, dataset_id)
    if record is None:
        raise AppError(
            status_code=404,
            code="DATASET_NOT_FOUND",
            message="No dataset was found for the provided dataset_id.",
            technical_detail=f"Dataset id '{dataset_id}' does not exist in SQLite.",
            suggested_fix="Upload a dataset first, then use the returned dataset_id.",
        )
    return record
