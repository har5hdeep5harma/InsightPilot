from datetime import datetime
from enum import StrEnum

from pydantic import Field, model_validator

from app.models.common import ApiModel, NonEmptyStr

class FileType(StrEnum):
    csv = "csv"
    xlsx = "xlsx"


class DatasetStatus(StrEnum):
    uploaded = "uploaded"
    parsing = "parsing"
    parsed = "parsed"
    profiling = "profiling"
    analyzed = "analyzed"
    failed = "failed"
    analysis_failed = "analysis_failed"
    deleted = "deleted"


class Dataset(ApiModel):
    id: NonEmptyStr
    filename: NonEmptyStr
    original_filename: NonEmptyStr
    file_type: FileType
    row_count: int = Field(ge=0)
    column_count: int = Field(ge=0)
    uploaded_at: datetime
    status: DatasetStatus
    error_message: str | None = None

    @model_validator(mode="after")
    def failed_status_requires_error(self) -> "Dataset":
        if self.status in {DatasetStatus.failed, DatasetStatus.analysis_failed}:
            if not self.error_message:
                raise ValueError("failed datasets require an error_message")
        return self


class DatasetStatusUpdate(ApiModel):
    status: DatasetStatus
    error_message: str | None = None
