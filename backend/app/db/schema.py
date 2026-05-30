from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class DatasetRecord(Base):
    __tablename__ = "datasets"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_type: Mapped[str] = mapped_column(String(16), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    stored_file_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    artifact_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    column_metadata: Mapped[list[dict[str, object]]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )
    warnings: Mapped[list[dict[str, object]]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )
    row_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    column_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    profile: Mapped[DatasetProfileRecord | None] = relationship(
        back_populates="dataset",
        cascade="all, delete-orphan",
    )
    columns: Mapped[list[ColumnProfileRecord]] = relationship(
        back_populates="dataset",
        cascade="all, delete-orphan",
    )
    charts: Mapped[list[ChartSpecRecord]] = relationship(
        back_populates="dataset",
        cascade="all, delete-orphan",
    )
    insights: Mapped[list[InsightRecord]] = relationship(
        back_populates="dataset",
        cascade="all, delete-orphan",
    )
    reports: Mapped[list[ReportRecord]] = relationship(
        back_populates="dataset",
        cascade="all, delete-orphan",
    )
    export_jobs: Mapped[list[ExportJobRecord]] = relationship(
        back_populates="dataset",
        cascade="all, delete-orphan",
    )


class ColumnProfileRecord(Base):
    __tablename__ = "column_profiles"

    dataset_id: Mapped[str] = mapped_column(
        ForeignKey("datasets.id", ondelete="CASCADE"),
        primary_key=True,
    )
    name: Mapped[str] = mapped_column(String(255), primary_key=True)
    original_name: Mapped[str] = mapped_column(String(255), nullable=False)
    inferred_type: Mapped[str] = mapped_column(String(32), nullable=False)
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    missing_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    missing_percentage: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    unique_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    unique_percentage: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    sample_values: Mapped[list[object]] = mapped_column(JSON, nullable=False, default=list)
    min_value: Mapped[object | None] = mapped_column(JSON, nullable=True)
    max_value: Mapped[object | None] = mapped_column(JSON, nullable=True)
    mean: Mapped[float | None] = mapped_column(Float, nullable=True)
    median: Mapped[float | None] = mapped_column(Float, nullable=True)
    std: Mapped[float | None] = mapped_column(Float, nullable=True)
    top_values: Mapped[list[dict[str, object]]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )
    warnings: Mapped[list[dict[str, object]]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )

    dataset: Mapped[DatasetRecord] = relationship(back_populates="columns")


class DatasetProfileRecord(Base):
    __tablename__ = "dataset_profiles"

    dataset_id: Mapped[str] = mapped_column(
        ForeignKey("datasets.id", ondelete="CASCADE"),
        primary_key=True,
    )
    row_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    column_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    duplicate_row_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    memory_usage: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    numeric_columns: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    categorical_columns: Mapped[list[str]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )
    datetime_columns: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    id_like_columns: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    text_columns: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    quality_score: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    warnings: Mapped[list[dict[str, object]]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )

    dataset: Mapped[DatasetRecord] = relationship(back_populates="profile")


class ChartSpecRecord(Base):
    __tablename__ = "chart_specs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    dataset_id: Mapped[str] = mapped_column(
        ForeignKey("datasets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    chart_type: Mapped[str] = mapped_column(String(32), nullable=False)
    x_column: Mapped[str | None] = mapped_column(String(255), nullable=True)
    y_column: Mapped[str | None] = mapped_column(String(255), nullable=True)
    group_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    reasoning: Mapped[str] = mapped_column(Text, nullable=False)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=50)
    data: Mapped[list[dict[str, object]]] = mapped_column(JSON, nullable=False, default=list)

    dataset: Mapped[DatasetRecord] = relationship(back_populates="charts")


class InsightRecord(Base):
    __tablename__ = "insights"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    dataset_id: Mapped[str] = mapped_column(
        ForeignKey("datasets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    insight_type: Mapped[str] = mapped_column(String(64), nullable=False)
    severity: Mapped[str] = mapped_column(String(32), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    evidence: Mapped[dict[str, object]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )
    recommendation: Mapped[str | None] = mapped_column(Text, nullable=True)
    related_columns: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    related_chart_id: Mapped[str | None] = mapped_column(String(64), nullable=True)

    dataset: Mapped[DatasetRecord] = relationship(back_populates="insights")


class ReportRecord(Base):
    __tablename__ = "reports"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    dataset_id: Mapped[str] = mapped_column(
        ForeignKey("datasets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    dataset_overview: Mapped[str] = mapped_column(Text, nullable=False, default="")
    executive_summary: Mapped[str] = mapped_column(Text, nullable=False)
    key_findings: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    risks: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    opportunities: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    recommendations: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    data_quality_notes: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    evidence_appendix: Mapped[list[dict[str, object]]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )
    chart_ids: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    insight_ids: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    dataset: Mapped[DatasetRecord] = relationship(back_populates="reports")


class ExportJobRecord(Base):
    __tablename__ = "export_jobs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    dataset_id: Mapped[str] = mapped_column(
        ForeignKey("datasets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    report_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    format: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    file_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    download_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    error: Mapped[dict[str, object] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    dataset: Mapped[DatasetRecord] = relationship(back_populates="export_jobs")
