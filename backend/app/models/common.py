from enum import StrEnum
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field


class ApiModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        from_attributes=True,
        str_strip_whitespace=True,
    )


NonEmptyStr = Annotated[str, Field(min_length=1)]
Percentage = Annotated[float, Field(ge=0, le=100)]
Confidence = Annotated[float, Field(ge=0, le=1)]
JsonValue = Any


class AnalysisWarning(ApiModel):
    code: NonEmptyStr
    message: NonEmptyStr
    column: str | None = None
    details: dict[str, JsonValue] = Field(default_factory=dict)


class ProcessingStatus(StrEnum):
    pending = "pending"
    processing = "processing"
    completed = "completed"
    failed = "failed"

