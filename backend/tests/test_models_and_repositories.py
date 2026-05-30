from datetime import UTC, datetime

import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.init_db import init_database
from app.db.repositories import (
    create_dataset,
    create_export_job,
    get_dataset,
    get_dataset_profile,
    get_export_job,
    get_report,
    save_chart_specs,
    save_dataset_profile,
    save_insights,
    save_report,
    update_dataset_status,
    update_export_job_status,
)
from app.models.chart import ChartSpec, ChartType
from app.models.dataset import Dataset, DatasetStatus, FileType
from app.models.export import ExportFormat, ExportJob, ExportStatus
from app.models.insight import (
    Evidence,
    EvidenceType,
    Insight,
    InsightCategory,
    InsightSeverity,
)
from app.models.profile import (
    ColumnProfile,
    ColumnRole,
    DatasetProfile,
    InferredType,
    TopValue,
)
from app.models.report import Report


@pytest.fixture()
def db_session() -> Session:
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    init_database(engine)
    session_factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = session_factory()
    try:
        yield session
    finally:
        session.close()


def test_dataset_failed_status_requires_error_message() -> None:
    with pytest.raises(ValidationError):
        Dataset(
            id="ds_failed",
            filename="bad.csv",
            original_filename="bad.csv",
            file_type=FileType.csv,
            row_count=0,
            column_count=0,
            uploaded_at=datetime.now(UTC),
            status=DatasetStatus.failed,
        )


def test_insight_requires_evidence() -> None:
    with pytest.raises(ValidationError):
        Insight(
            id="ins_empty",
            dataset_id="ds_test",
            title="Unsupported finding",
            summary="This should not validate without evidence.",
            insight_type=InsightCategory.distribution,
            severity=InsightSeverity.info,
            confidence=0.7,
            evidence=[],
        )


def test_repository_round_trip_persisted_artifacts(db_session: Session) -> None:
    uploaded_at = datetime.now(UTC)
    dataset = Dataset(
        id="ds_test",
        filename="sample_retail_sales.csv",
        original_filename="sample_retail_sales.csv",
        file_type=FileType.csv,
        row_count=2,
        column_count=2,
        uploaded_at=uploaded_at,
        status=DatasetStatus.parsed,
    )

    created_dataset = create_dataset(db_session, dataset)
    assert created_dataset.id == "ds_test"
    assert get_dataset(db_session, "ds_test") == created_dataset

    revenue_column = ColumnProfile(
        name="revenue",
        original_name="Revenue",
        inferred_type=InferredType.number,
        role=ColumnRole.metric,
        missing_count=0,
        missing_percentage=0,
        unique_count=2,
        unique_percentage=100,
        sample_values=[1200, 900],
        min=900,
        max=1200,
        mean=1050,
        median=1050,
        std=150,
    )
    region_column = ColumnProfile(
        name="region",
        original_name="Region",
        inferred_type=InferredType.category,
        role=ColumnRole.dimension,
        missing_count=0,
        missing_percentage=0,
        unique_count=2,
        unique_percentage=100,
        sample_values=["West", "East"],
        top_values=[
            TopValue(value="West", count=1, percentage=50),
            TopValue(value="East", count=1, percentage=50),
        ],
    )
    profile = DatasetProfile(
        dataset_id="ds_test",
        row_count=2,
        column_count=2,
        duplicate_row_count=0,
        memory_usage=256,
        columns=[revenue_column, region_column],
        numeric_columns=["revenue"],
        categorical_columns=["region"],
        datetime_columns=[],
        id_like_columns=[],
        text_columns=[],
        quality_score=98,
    )

    saved_profile = save_dataset_profile(db_session, profile)
    loaded_profile = get_dataset_profile(db_session, "ds_test")
    assert loaded_profile == saved_profile
    assert loaded_profile is not None
    assert loaded_profile.numeric_columns == ["revenue"]
    assert len(loaded_profile.columns) == 2

    chart = ChartSpec(
        id="chart_revenue_by_region",
        dataset_id="ds_test",
        title="Revenue by Region",
        chart_type=ChartType.bar,
        x_column="region",
        y_column="revenue",
        group_by=None,
        description="Compares revenue across regions.",
        reasoning="A categorical dimension and numeric metric support a bar chart.",
        priority=1,
        data=[{"region": "West", "revenue": 1200}, {"region": "East", "revenue": 900}],
    )
    saved_charts = save_chart_specs(db_session, "ds_test", [chart])
    assert saved_charts == [chart]

    insight = Insight(
        id="ins_region_revenue",
        dataset_id="ds_test",
        title="West has the larger revenue contribution",
        summary="West revenue is higher than East revenue in the persisted sample.",
        insight_type=InsightCategory.concentration,
        severity=InsightSeverity.info,
        confidence=0.85,
        evidence=[
            Evidence(
                type=EvidenceType.comparison,
                column="revenue",
                metric="sum_by_region",
                value=1200,
                comparison_value=900,
                rows_affected=2,
                calculation="sum(revenue) grouped by region",
                explanation="West totals 1200 while East totals 900 in the test rows.",
            )
        ],
        recommendation="Review regional performance drivers before acting.",
        related_columns=["region", "revenue"],
        related_chart_id="chart_revenue_by_region",
    )
    saved_insights = save_insights(db_session, "ds_test", [insight])
    assert saved_insights == [insight]

    report = Report(
        id="report_test",
        dataset_id="ds_test",
        title="Sample Retail Sales Report",
        dataset_overview="The test dataset contains two rows and two columns.",
        executive_summary="This report summarizes persisted test analysis artifacts.",
        key_findings=["West revenue is higher than East revenue."],
        risks=[],
        opportunities=["Investigate regional drivers."],
        recommendations=["Use the regional chart as supporting evidence."],
        charts=[chart],
        insights=[insight],
        created_at=datetime.now(UTC),
    )
    saved_report = save_report(db_session, report)
    loaded_report = get_report(db_session, "report_test")
    assert loaded_report == saved_report
    assert loaded_report is not None
    assert loaded_report.charts == [chart]
    assert loaded_report.insights == [insight]

    export_job = ExportJob(
        id="export_test",
        dataset_id="ds_test",
        report_id="report_test",
        format=ExportFormat.html,
        status=ExportStatus.queued,
        created_at=datetime.now(UTC),
    )
    create_export_job(db_session, export_job)
    updated_export = update_export_job_status(
        db_session,
        "export_test",
        ExportStatus.completed,
        file_path="sample-data/exports/export_test/report.html",
        download_url="/exports/export_test/download",
    )
    loaded_export = get_export_job(db_session, "export_test")
    assert updated_export == loaded_export
    assert loaded_export is not None
    assert loaded_export.status == ExportStatus.completed

    updated_dataset = update_dataset_status(
        db_session,
        "ds_test",
        DatasetStatus.analyzed,
    )
    assert updated_dataset is not None
    assert updated_dataset.status == DatasetStatus.analyzed
