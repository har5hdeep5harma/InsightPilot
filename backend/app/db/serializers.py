from app.core.errors import ApiError
from app.db.schema import (
    ChartSpecRecord,
    ColumnProfileRecord,
    DatasetProfileRecord,
    DatasetRecord,
    ExportJobRecord,
    InsightRecord,
    ReportRecord,
)
from app.models.chart import ChartSpec
from app.models.common import AnalysisWarning
from app.models.dataset import Dataset
from app.models.export import ExportJob
from app.models.insight import Insight
from app.models.profile import ColumnProfile, DatasetProfile, TopValue
from app.models.report import EvidenceAppendixItem, Report


def dataset_to_record(dataset: Dataset) -> DatasetRecord:
    return DatasetRecord(
        id=dataset.id,
        filename=dataset.filename,
        original_filename=dataset.original_filename,
        file_type=dataset.file_type.value,
        row_count=dataset.row_count,
        column_count=dataset.column_count,
        uploaded_at=dataset.uploaded_at,
        status=dataset.status.value,
        error_message=dataset.error_message,
    )


def dataset_from_record(record: DatasetRecord) -> Dataset:
    return Dataset(
        id=record.id,
        filename=record.filename,
        original_filename=record.original_filename,
        file_type=record.file_type,
        row_count=record.row_count,
        column_count=record.column_count,
        uploaded_at=record.uploaded_at,
        status=record.status,
        error_message=record.error_message,
    )


def column_profile_to_record(
    dataset_id: str,
    profile: ColumnProfile,
) -> ColumnProfileRecord:
    return ColumnProfileRecord(
        dataset_id=dataset_id,
        name=profile.name,
        original_name=profile.original_name,
        inferred_type=profile.inferred_type.value,
        role=profile.role.value,
        missing_count=profile.missing_count,
        missing_percentage=profile.missing_percentage,
        unique_count=profile.unique_count,
        unique_percentage=profile.unique_percentage,
        sample_values=profile.sample_values,
        min_value=profile.min,
        max_value=profile.max,
        mean=profile.mean,
        median=profile.median,
        std=profile.std,
        top_values=[item.model_dump(mode="json") for item in profile.top_values],
        warnings=[item.model_dump(mode="json") for item in profile.warnings],
    )


def column_profile_from_record(record: ColumnProfileRecord) -> ColumnProfile:
    return ColumnProfile(
        name=record.name,
        original_name=record.original_name,
        inferred_type=record.inferred_type,
        role=record.role,
        missing_count=record.missing_count,
        missing_percentage=record.missing_percentage,
        unique_count=record.unique_count,
        unique_percentage=record.unique_percentage,
        sample_values=record.sample_values or [],
        min=record.min_value,
        max=record.max_value,
        mean=record.mean,
        median=record.median,
        std=record.std,
        top_values=[TopValue.model_validate(item) for item in record.top_values or []],
        warnings=[
            AnalysisWarning.model_validate(item) for item in record.warnings or []
        ],
    )


def dataset_profile_to_record(profile: DatasetProfile) -> DatasetProfileRecord:
    return DatasetProfileRecord(
        dataset_id=profile.dataset_id,
        row_count=profile.row_count,
        column_count=profile.column_count,
        duplicate_row_count=profile.duplicate_row_count,
        memory_usage=profile.memory_usage,
        numeric_columns=profile.numeric_columns,
        categorical_columns=profile.categorical_columns,
        datetime_columns=profile.datetime_columns,
        id_like_columns=profile.id_like_columns,
        text_columns=profile.text_columns,
        quality_score=profile.quality_score,
        warnings=[item.model_dump(mode="json") for item in profile.warnings],
    )


def dataset_profile_from_record(
    record: DatasetProfileRecord,
    columns: list[ColumnProfileRecord],
) -> DatasetProfile:
    return DatasetProfile(
        dataset_id=record.dataset_id,
        row_count=record.row_count,
        column_count=record.column_count,
        duplicate_row_count=record.duplicate_row_count,
        memory_usage=record.memory_usage,
        columns=[column_profile_from_record(column) for column in columns],
        numeric_columns=record.numeric_columns or [],
        categorical_columns=record.categorical_columns or [],
        datetime_columns=record.datetime_columns or [],
        id_like_columns=record.id_like_columns or [],
        text_columns=record.text_columns or [],
        quality_score=record.quality_score,
        warnings=[
            AnalysisWarning.model_validate(item) for item in record.warnings or []
        ],
    )


def chart_spec_to_record(chart: ChartSpec) -> ChartSpecRecord:
    return ChartSpecRecord(
        id=chart.id,
        dataset_id=chart.dataset_id,
        title=chart.title,
        chart_type=chart.chart_type.value,
        x_column=chart.x_column,
        y_column=chart.y_column,
        group_by=chart.group_by,
        description=chart.description,
        reasoning=chart.reasoning,
        priority=chart.priority,
        data=chart.chart_data,
    )


def chart_spec_from_record(record: ChartSpecRecord) -> ChartSpec:
    return ChartSpec(
        id=record.id,
        dataset_id=record.dataset_id,
        title=record.title,
        chart_type=record.chart_type,
        x_column=record.x_column,
        y_column=record.y_column,
        group_by=record.group_by,
        description=record.description,
        reasoning=record.reasoning,
        priority=record.priority,
        chart_data=record.data or [],
    )


def insight_to_record(insight: Insight) -> InsightRecord:
    return InsightRecord(
        id=insight.id,
        dataset_id=insight.dataset_id,
        title=insight.title,
        summary=insight.summary,
        insight_type=insight.insight_type.value,
        severity=insight.severity.value,
        confidence=insight.confidence,
        evidence=insight.evidence.model_dump(mode="json"),
        recommendation=insight.recommendation,
        related_columns=insight.related_columns,
        related_chart_id=insight.related_chart_id,
    )


def insight_from_record(record: InsightRecord) -> Insight:
    return Insight(
        id=record.id,
        dataset_id=record.dataset_id,
        title=record.title,
        summary=record.summary,
        insight_type=record.insight_type,
        severity=record.severity,
        confidence=record.confidence,
        evidence=record.evidence,
        recommendation=record.recommendation,
        related_columns=record.related_columns or [],
        related_chart_id=record.related_chart_id,
    )


def report_to_record(report: Report) -> ReportRecord:
    return ReportRecord(
        id=report.id,
        dataset_id=report.dataset_id,
        title=report.title,
        dataset_overview=report.dataset_overview,
        executive_summary=report.executive_summary,
        key_findings=report.key_findings,
        risks=report.risks,
        opportunities=report.opportunities,
        recommendations=report.recommendations,
        data_quality_notes=report.data_quality_notes,
        evidence_appendix=[
            item.model_dump(mode="json") for item in report.evidence_appendix
        ],
        chart_ids=report.chart_ids or [chart.id for chart in report.charts],
        insight_ids=[insight.id for insight in report.insights],
        created_at=report.created_at,
    )


def report_from_record(
    record: ReportRecord,
    charts: list[ChartSpecRecord],
    insights: list[InsightRecord],
) -> Report:
    charts_by_id = {chart.id: chart for chart in charts}
    insights_by_id = {insight.id: insight for insight in insights}

    return Report(
        id=record.id,
        dataset_id=record.dataset_id,
        title=record.title,
        dataset_overview=record.dataset_overview
        or "Dataset overview was not stored for this report.",
        executive_summary=record.executive_summary,
        key_findings=record.key_findings or [],
        risks=record.risks or [],
        opportunities=record.opportunities or [],
        recommendations=record.recommendations or [],
        data_quality_notes=record.data_quality_notes or [],
        evidence_appendix=[
            EvidenceAppendixItem.model_validate(item)
            for item in record.evidence_appendix or []
        ],
        chart_ids=record.chart_ids or [],
        charts=[
            chart_spec_from_record(charts_by_id[chart_id])
            for chart_id in record.chart_ids or []
            if chart_id in charts_by_id
        ],
        insights=[
            insight_from_record(insights_by_id[insight_id])
            for insight_id in record.insight_ids or []
            if insight_id in insights_by_id
        ],
        created_at=record.created_at,
    )


def export_job_to_record(export_job: ExportJob) -> ExportJobRecord:
    return ExportJobRecord(
        id=export_job.id,
        dataset_id=export_job.dataset_id,
        report_id=export_job.report_id,
        format=export_job.format.value,
        status=export_job.status.value,
        file_path=export_job.file_path,
        download_url=export_job.download_url,
        error=export_job.error.model_dump(mode="json") if export_job.error else None,
        created_at=export_job.created_at,
        completed_at=export_job.completed_at,
    )


def export_job_from_record(record: ExportJobRecord) -> ExportJob:
    return ExportJob(
        id=record.id,
        dataset_id=record.dataset_id,
        report_id=record.report_id,
        format=record.format,
        status=record.status,
        file_path=record.file_path,
        download_url=record.download_url,
        error=ApiError.model_validate(record.error) if record.error else None,
        created_at=record.created_at,
        completed_at=record.completed_at,
    )
