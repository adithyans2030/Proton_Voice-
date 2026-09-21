"""FastAPI application factory. Run with: uvicorn app.main:create_app --factory"""
import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app import __version__
from app.api import health
from app.config import Settings

logger = logging.getLogger("studybot")


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        settings.ensure_dirs()
        logger.info("StudyBot %s starting; data home: %s", __version__, settings.home)
        yield

    app = FastAPI(title="StudyBot", version=__version__, lifespan=lifespan)
    app.state.settings = settings
    app.state.started_at = time.monotonic()
    app.include_router(health.router)
    return app
