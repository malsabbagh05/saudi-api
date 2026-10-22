"""Database engines. Each entry point (app, worker, CLI) builds one from its settings."""

from __future__ import annotations

from sqlalchemy import Engine, create_engine
from sqlalchemy.engine import URL, make_url

from saudi_api.settings import Settings


def database_url(settings: Settings) -> URL:
    return make_url(str(settings.database_url))


def build_engine(settings: Settings) -> Engine:
    return create_engine(
        database_url(settings),
        pool_size=settings.database_pool_size,
        max_overflow=settings.database_max_overflow,
        pool_pre_ping=True,
        connect_args={"connect_timeout": settings.database_connect_timeout_seconds},
    )
