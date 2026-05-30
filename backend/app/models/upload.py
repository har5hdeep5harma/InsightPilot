from datetime import datetime
from typing import Any

from pydantic import Field

from app.models.common import ApiModel, AnalysisWarning, NonEmptyStr
from app.models.dataset import DatasetStatus, FileType


class DatasetColumn(ApiModel):
    name: NonEmptyStr
    original_name: str


class DatasetUploadResponse(ApiModel):
    dataset_id: NonEmptyStr
    filename: NonEmptyStr
    row_count: int = Field(ge=0)
    column_count: int = Field(ge=0)
    columns: list[DatasetColumn]
    preview_rows: list[dict[str, Any]]
    warnings: list[AnalysisWarning] = Field(default_factory=list)


class DatasetDetailResponse(ApiModel):
    dataset_id: NonEmptyStr
    filename: NonEmptyStr
    original_filename: NonEmptyStr
    file_type: FileType
    row_count: int = Field(ge=0)
    column_count: int = Field(ge=0)
    uploaded_at: datetime
    status: DatasetStatus
    error_message: str | None = None
    columns: list[DatasetColumn]
    warnings: list[AnalysisWarning] = Field(default_factory=list)


class DatasetPreviewResponse(ApiModel):
    dataset_id: NonEmptyStr
    columns: list[DatasetColumn]
    preview_rows: list[dict[str, Any]]
    limit: int = Field(ge=1)
    offset: int = Field(ge=0)
    row_count: int = Field(ge=0)
