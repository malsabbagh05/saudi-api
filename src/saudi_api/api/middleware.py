"""HTTP middleware: request identity, access log, security headers, path-aware CORS."""

from __future__ import annotations

import logging
import re
import time
import uuid

from starlette.middleware.cors import CORSMiddleware
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from saudi_api.logs import request_id

_log = logging.getLogger("saudi_api.http")
_REQUEST_ID = re.compile(r"^[A-Za-z0-9._-]{1,64}$")
# Swagger UI loads its assets from a CDN, so its pages carry no CSP of ours.
_DOCS_PATHS = ("/docs",)
_API_CSP = "default-src 'none'; frame-ancestors 'none'"
_MCP_HEADERS = [
    "Content-Type",
    "Last-Event-ID",
    "Mcp-Method",
    "Mcp-Name",
    "Mcp-Protocol-Version",
    "Mcp-Session-Id",
]


class RequestContext:
    """Sets the request ID (kept from `X-Request-ID` when well-formed), returns it, adds
    security headers, and logs one line per request with the route template, never the
    raw query string."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        incoming = dict(scope["headers"]).get(b"x-request-id", b"").decode("latin-1")
        current = incoming if _REQUEST_ID.match(incoming) else uuid.uuid4().hex
        token = request_id.set(current)
        started = time.perf_counter()
        status = 500
        path: str = scope["path"]

        async def send_with_headers(message: Message) -> None:
            nonlocal status
            if message["type"] == "http.response.start":
                status = message["status"]
                headers = list(message.get("headers", []))
                headers.append((b"x-request-id", current.encode()))
                headers.append((b"x-content-type-options", b"nosniff"))
                headers.append((b"referrer-policy", b"no-referrer"))
                if not path.startswith(_DOCS_PATHS):
                    headers.append((b"content-security-policy", _API_CSP.encode()))
                message["headers"] = headers
            await send(message)

        try:
            await self.app(scope, receive, send_with_headers)
        finally:
            route = scope.get("route")
            template = getattr(route, "path", None) or ("/mcp" if path.startswith("/mcp") else "-")
            _log.info(
                "request",
                extra={
                    "method": scope["method"],
                    "route": template,
                    "status": status,
                    "duration_ms": round((time.perf_counter() - started) * 1000, 1),
                },
            )
            request_id.reset(token)


class PathCors:
    """Public, credential-free GET access everywhere; MCP access only from the configured
    origins, mirroring the transport's own Origin allowlist."""

    def __init__(self, app: ASGIApp, mcp_origins: list[str]) -> None:
        self.public = CORSMiddleware(
            app,
            allow_origins=["*"],
            allow_methods=["GET", "HEAD"],
            allow_headers=["Accept", "Accept-Language", "X-Request-ID"],
            expose_headers=["X-Request-ID"],
            max_age=600,
        )
        self.mcp = CORSMiddleware(
            app,
            allow_origins=mcp_origins,
            allow_methods=["GET", "POST", "DELETE"],
            allow_headers=_MCP_HEADERS,
            expose_headers=["Mcp-Session-Id"],
            max_age=600,
        )

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http" and scope["path"].startswith("/mcp"):
            await self.mcp(scope, receive, send)
        else:
            await self.public(scope, receive, send)
