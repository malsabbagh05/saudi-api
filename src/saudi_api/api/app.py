"""The API service: REST under `/v1`, `/llms.txt`, probes, and MCP at `/mcp` (ADR-001)."""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from mcp.server.transport_security import TransportSecuritySettings
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.routing import Route

from saudi_api import PROJECT_URL, __version__
from saudi_api.api.middleware import PathCors, RequestContext
from saudi_api.api.routes import root_router, router
from saudi_api.catalog.loader import catalog_digest
from saudi_api.catalog.sync import projected_digest
from saudi_api.db import build_engine
from saudi_api.mcp_server import build_mcp
from saudi_api.settings import Settings, get_settings

_log = logging.getLogger(__name__)
_STATUS_CODES = {404: "not_found", 405: "method_not_allowed", 406: "not_acceptable"}

DESCRIPTION = """\
A verified, bilingual (Arabic and English) catalogue of Saudi APIs and the datasets they
publish. Every text field has `en` and `ar`. Errors are `{"code", "message"}` with a
bounded `code`. The same catalogue is available to AI agents over MCP at `/mcp`.
"""


def create_app(settings: Settings) -> FastAPI:
    engine = build_engine(settings)
    sessions = sessionmaker(engine, expire_on_commit=False)
    bundled_digest = catalog_digest(settings.catalog_dir)
    mcp = build_mcp(settings, sessions)
    mcp_app = mcp.streamable_http_app(
        # Legacy (2025-era) clients get no server-side session, so any replica serves
        # them; protocol 2026-07-28 is stateless already.
        stateless_http=True,
        transport_security=_transport_security(settings),
    )

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncGenerator[None]:
        # A mounted MCP app's own lifespan never runs; the host app enters it.
        async with mcp.session_manager.run():
            yield
        engine.dispose()

    app = FastAPI(
        title="Saudi API Catalogue",
        version=__version__,
        description=DESCRIPTION,
        lifespan=lifespan,
        redoc_url=None,
        license_info={"name": "Apache-2.0", "url": f"{PROJECT_URL}/blob/main/LICENSE"},
    )
    app.state.settings = settings
    app.state.sessions = sessions
    app.state.bundled_digest = bundled_digest
    app.include_router(router)
    app.include_router(root_router)

    @app.get("/healthz", include_in_schema=False)
    # on-event-loop: liveness probe without I/O; it must answer while the pool is full
    async def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/readyz", include_in_schema=False)
    def readyz() -> JSONResponse:
        try:
            with sessions() as db:
                digest = projected_digest(db)
        except SQLAlchemyError:
            return JSONResponse({"status": "unavailable", "reason": "database"}, status_code=503)
        if digest != bundled_digest:
            return JSONResponse(
                {"status": "unavailable", "reason": "catalog_not_synced"}, status_code=503
            )
        return JSONResponse({"status": "ready", "catalog_digest": digest})

    @app.get("/", include_in_schema=False)
    def index() -> dict[str, str]:
        base = settings.public_base_url.rstrip("/")
        return {
            "name": "Saudi API Catalogue",
            "version": __version__,
            "openapi": f"{base}/openapi.json",
            "docs": f"{base}/docs",
            "mcp": f"{base}/mcp",
            "llms": f"{base}/llms.txt",
            "web": settings.web_base_url,
            "source": PROJECT_URL,
        }

    # The exact path /mcp, so a request never takes the /mcp -> /mcp/ redirect and other
    # paths keep this app's JSON errors.
    app.router.routes.append(Route("/mcp", mcp_app, include_in_schema=False))

    app.add_exception_handler(StarletteHTTPException, _http_error)
    app.add_exception_handler(RequestValidationError, _validation_error)
    app.add_exception_handler(Exception, _unexpected_error)
    app.add_middleware(PathCors, mcp_origins=settings.mcp_allowed_origins)
    app.add_middleware(RequestContext)
    return app


def openapi_json(settings: Settings) -> str:
    """The REST API's OpenAPI document as JSON text; building the app opens no connection."""
    return json.dumps(create_app(settings).openapi(), indent=2, ensure_ascii=False)


def app_from_environment() -> FastAPI:
    """The uvicorn factory: `uvicorn --factory saudi_api.api.app:app_from_environment`."""
    return create_app(get_settings())


def _transport_security(settings: Settings) -> TransportSecuritySettings | None:
    if not settings.mcp_allowed_hosts:
        return None
    hosts = [h for host in settings.mcp_allowed_hosts for h in (host, f"{host}:*")]
    return TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=hosts,
        allowed_origins=settings.mcp_allowed_origins,
    )


async def _http_error(_: Request, error: Exception) -> JSONResponse:
    assert isinstance(error, StarletteHTTPException)
    detail = error.detail
    if isinstance(detail, dict) and "code" in detail:
        body = detail
    else:
        code = _STATUS_CODES.get(error.status_code, f"http_{error.status_code}")
        body = {"code": code, "message": code.replace("_", " ")}
    return JSONResponse(body, status_code=error.status_code, headers=error.headers)


async def _validation_error(_: Request, error: Exception) -> JSONResponse:
    assert isinstance(error, RequestValidationError)
    names = sorted({str(e["loc"][-1]) for e in error.errors() if e.get("loc")})
    return JSONResponse(
        {"code": "invalid_request", "message": "invalid parameters: " + ", ".join(names)},
        status_code=422,
    )


async def _unexpected_error(_: Request, error: Exception) -> JSONResponse:
    _log.error("unhandled error", exc_info=error)
    return JSONResponse({"code": "internal_error", "message": "internal error"}, status_code=500)
