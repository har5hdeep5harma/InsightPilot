from datetime import datetime
from enum import StrEnum

from app.core.errors import ApiError
from app.models.common import ApiModel, NonEmptyStr


class ExportFormat(StrEnum):
    html = "html"
    pdf = "pdf"


class ExportStatus(StrEnum):
    queued = "queued"
    running = "running"
    completed = "completed"
    failed = "failed"
    unsupported = "unsupported"


class ExportJob(ApiModel):
    id: NonEmptyStr
    dataset_id: NonEmptyStr
    report_id: NonEmptyStr
    format: ExportFormat
    status: ExportStatus
    file_path: str | None = None
    download_url: str | None = None
    error: ApiError | None = None
    created_at: datetime
    completed_at: datetime | None = None
