from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.datasets import router as datasets_router
from app.api.health import router as health_router
from app.api.reports import router as reports_router
from app.core.config import get_settings
from app.core.errors import AppError, app_error_handler
from app.db.init_db import init_database


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_database()
    yield


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="InsightPilot API",
        version="0.1.0",
        description="Deterministic analytics API for spreadsheet-to-report workflows.",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.add_exception_handler(AppError, app_error_handler)
    app.include_router(health_router)
    app.include_router(datasets_router)
    app.include_router(reports_router)

    return app


app = create_app()
