from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.db.schema import (
    ChartSpecRecord,
    ColumnProfileRecord,
    DatasetProfileRecord,
    DatasetRecord,
    ExportJobRecord,
    InsightRecord,
    ReportRecord,
)
from app.db.serializers import (
    chart_spec_from_record,
    chart_spec_to_record,
    column_profile_to_record,
    dataset_from_record,
    dataset_profile_from_record,
    dataset_profile_to_record,
    dataset_to_record,
    export_job_from_record,
    export_job_to_record,
    insight_from_record,
    insight_to_record,
    report_from_record,
    report_to_record,
)
from app.models.chart import ChartSpec
from app.models.common import AnalysisWarning
from app.models.dataset import Dataset, DatasetStatus
from app.models.export import ExportJob, ExportStatus
from app.models.insight import Insight
from app.models.profile import DatasetProfile
from app.models.report import Report
from app.models.upload import DatasetColumn


def create_dataset(db: Session, dataset: Dataset) -> Dataset:
    record = dataset_to_record(dataset)
    db.add(record)
    db.commit()
    db.refresh(record)
    return dataset_from_record(record)


def create_uploaded_dataset(
    db: Session,
    dataset: Dataset,
    *,
    file_size_bytes: int,
    stored_file_path: str,
    artifact_path: str,
    columns: list[DatasetColumn],
    warnings: list[AnalysisWarning],
) -> Dataset:
    record = dataset_to_record(dataset)
    record.file_size_bytes = file_size_bytes
    record.stored_file_path = stored_file_path
    record.artifact_path = artifact_path
    record.column_metadata = [column.model_dump(mode="json") for column in columns]
    record.warnings = [warning.model_dump(mode="json") for warning in warnings]
    db.add(record)
    db.commit()
    db.refresh(record)
    return dataset_from_record(record)


def get_dataset_record(db: Session, dataset_id: str) -> DatasetRecord | None:
    return db.get(DatasetRecord, dataset_id)


def get_dataset(db: Session, dataset_id: str) -> Dataset | None:
    record = db.get(DatasetRecord, dataset_id)
    return dataset_from_record(record) if record else None


def list_datasets(db: Session, limit: int = 50, offset: int = 0) -> list[Dataset]:
    statement = (
        select(DatasetRecord)
        .order_by(DatasetRecord.uploaded_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return [dataset_from_record(record) for record in db.scalars(statement)]


def update_dataset_status(
    db: Session,
    dataset_id: str,
    status: DatasetStatus,
    error_message: str | None = None,
) -> Dataset | None:
    if status in {DatasetStatus.failed, DatasetStatus.analysis_failed} and not error_message:
        raise ValueError("failed dataset statuses require an error_message")

    record = db.get(DatasetRecord, dataset_id)
    if record is None:
        return None

    record.status = status.value
    record.error_message = error_message
    db.commit()
    db.refresh(record)
    return dataset_from_record(record)


def save_dataset_profile(db: Session, profile: DatasetProfile) -> DatasetProfile:
    db.execute(
        delete(ColumnProfileRecord).where(
            ColumnProfileRecord.dataset_id == profile.dataset_id
        )
    )
    db.merge(dataset_profile_to_record(profile))
    for column in profile.columns:
        db.add(column_profile_to_record(profile.dataset_id, column))
    db.commit()
    return get_dataset_profile(db, profile.dataset_id) or profile


def get_dataset_profile(db: Session, dataset_id: str) -> DatasetProfile | None:
    profile_record = db.get(DatasetProfileRecord, dataset_id)
    if profile_record is None:
        return None

    column_statement = (
        select(ColumnProfileRecord)
        .where(ColumnProfileRecord.dataset_id == dataset_id)
        .order_by(ColumnProfileRecord.name.asc())
    )
    columns = list(db.scalars(column_statement))
    return dataset_profile_from_record(profile_record, columns)


def save_chart_specs(db: Session, dataset_id: str, charts: list[ChartSpec]) -> list[ChartSpec]:
    db.execute(delete(ChartSpecRecord).where(ChartSpecRecord.dataset_id == dataset_id))
    for chart in charts:
        db.add(chart_spec_to_record(chart))
    db.commit()
    return list_chart_specs(db, dataset_id)


def list_chart_specs(db: Session, dataset_id: str) -> list[ChartSpec]:
    statement = (
        select(ChartSpecRecord)
        .where(ChartSpecRecord.dataset_id == dataset_id)
        .order_by(ChartSpecRecord.priority.asc(), ChartSpecRecord.title.asc())
    )
    return [chart_spec_from_record(record) for record in db.scalars(statement)]


def get_chart_spec(db: Session, chart_id: str) -> ChartSpec | None:
    record = db.get(ChartSpecRecord, chart_id)
    return chart_spec_from_record(record) if record else None


def save_insights(db: Session, dataset_id: str, insights: list[Insight]) -> list[Insight]:
    db.execute(delete(InsightRecord).where(InsightRecord.dataset_id == dataset_id))
    for insight in insights:
        db.add(insight_to_record(insight))
    db.commit()
    return list_insights(db, dataset_id)


def list_insights(db: Session, dataset_id: str) -> list[Insight]:
    statement = (
        select(InsightRecord)
        .where(InsightRecord.dataset_id == dataset_id)
        .order_by(InsightRecord.title.asc())
    )
    insights = [insight_from_record(record) for record in db.scalars(statement)]
    severity_rank = {"high": 0, "medium": 1, "low": 2}
    return sorted(
        insights,
        key=lambda insight: (
            severity_rank.get(insight.severity.value, 3),
            -insight.confidence,
            insight.title,
        ),
    )


def get_insight(db: Session, insight_id: str) -> Insight | None:
    record = db.get(InsightRecord, insight_id)
    return insight_from_record(record) if record else None


def save_report(db: Session, report: Report) -> Report:
    db.merge(report_to_record(report))
    db.commit()
    return get_report(db, report.id) or report


def get_report(db: Session, report_id: str) -> Report | None:
    report_record = db.get(ReportRecord, report_id)
    if report_record is None:
        return None

    chart_statement = select(ChartSpecRecord).where(
        ChartSpecRecord.dataset_id == report_record.dataset_id
    )
    insight_statement = select(InsightRecord).where(
        InsightRecord.dataset_id == report_record.dataset_id
    )
    return report_from_record(
        report_record,
        list(db.scalars(chart_statement)),
        list(db.scalars(insight_statement)),
    )


def create_export_job(db: Session, export_job: ExportJob) -> ExportJob:
    record = export_job_to_record(export_job)
    db.add(record)
    db.commit()
    db.refresh(record)
    return export_job_from_record(record)


def get_export_job(db: Session, export_job_id: str) -> ExportJob | None:
    record = db.get(ExportJobRecord, export_job_id)
    return export_job_from_record(record) if record else None


def update_export_job_status(
    db: Session,
    export_job_id: str,
    status: ExportStatus,
    file_path: str | None = None,
    download_url: str | None = None,
) -> ExportJob | None:
    record = db.get(ExportJobRecord, export_job_id)
    if record is None:
        return None

    record.status = status.value
    if file_path is not None:
        record.file_path = file_path
    if download_url is not None:
        record.download_url = download_url
    db.commit()
    db.refresh(record)
    return export_job_from_record(record)
