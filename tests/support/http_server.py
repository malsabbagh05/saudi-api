"""A real HTTP server on 127.0.0.1 that stands in for a provider in tests.

Code that reads providers goes through its real HTTP client and `outbound.py` against
this server, which serves authentic recorded payloads (tests/README.md). Routes match the
path and query exactly, then the path alone.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


@dataclass
class Route:
    status: int = 200
    body: bytes = b""
    headers: dict[str, str] = field(default_factory=dict)
    delay_seconds: float = 0.0


@dataclass
class ProviderServer:
    url: str
    routes: dict[str, Route]
    requests: list[str]

    @property
    def host(self) -> str:
        return "127.0.0.1"


@contextmanager
def provider_server(routes: dict[str, Route]) -> Iterator[ProviderServer]:
    requests: list[str] = []

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            requests.append(self.path)
            route = routes.get(self.path) or routes.get(self.path.split("?", 1)[0])
            if route is None:
                route = Route(status=404, body=b"not found")
            if route.delay_seconds:
                time.sleep(route.delay_seconds)
            self.send_response(route.status)
            for name, value in route.headers.items():
                self.send_header(name, value)
            self.send_header("Content-Length", str(len(route.body)))
            self.end_headers()
            self.wfile.write(route.body)

        def log_message(self, format: str, *args: object) -> None:
            return

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield ProviderServer(f"http://127.0.0.1:{server.server_port}", routes, requests)
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
