"""FastAPI entrypoint. The lifespan starts the beacon loop; the routes only observe it."""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import sys
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import Settings, get_settings
from app.publisher import NullPublisher, Publisher, S3Publisher
from app.routes import router
from app.runner import Beacon

_RESERVED = set(vars(logging.makeLogRecord({})))


class _JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        entry = {"level": record.levelname, "logger": record.name, "msg": record.getMessage()}
        entry.update({k: v for k, v in vars(record).items() if k not in _RESERVED})
        if record.exc_info:
            entry["exc"] = self.formatException(record.exc_info)
        return json.dumps(entry, default=str)


def _configure_logging(level: str) -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(_JsonFormatter())
    logging.basicConfig(level=level, handlers=[handler], force=True)


def make_publisher(settings: Settings) -> Publisher:
    """S3 when PUBLISH_ENABLED, otherwise a dry run that publishes nothing."""
    if settings.publish_enabled:
        return S3Publisher(
            settings.s3_bucket, settings.s3_key, settings.s3_cache_control, settings.aws_region
        )
    return NullPublisher()


def create_app(settings: Settings | None = None, *, start_loop: bool = True) -> FastAPI:
    """The app. Tests pass start_loop=False and drive cycles themselves."""
    resolved = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        _configure_logging(resolved.log_level)
        app.state.beacon = Beacon(resolved, make_publisher(resolved))
        task = asyncio.create_task(app.state.beacon.run_forever()) if start_loop else None
        yield
        if task is not None:
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task

    app = FastAPI(
        title="halifirien",
        version=resolved.app_version,
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
        redoc_url=None,
        lifespan=lifespan,
    )
    app.include_router(router)
    return app


app = create_app()
