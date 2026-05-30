from fastapi import Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field


class ApiError(BaseModel):
    code: str
    message: str
    technical_detail: str | None = None
    suggested_fix: str | None = None
    details: dict[str, object] = Field(default_factory=dict)


class ErrorResponse(BaseModel):
    error: ApiError


class AppError(Exception):
    def __init__(
        self,
        *,
        status_code: int,
        code: str,
        message: str,
        technical_detail: str | None = None,
        suggested_fix: str | None = None,
        details: dict[str, object] | None = None,
    ) -> None:
        self.status_code = status_code
        self.error = ApiError(
            code=code,
            message=message,
            technical_detail=technical_detail,
            suggested_fix=suggested_fix,
            details=details or {},
        )


async def app_error_handler(_: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.error.model_dump(exclude_none=True)},
    )
