"""The one path for requests to providers (ADR-004).

Every request is checked before it leaves: HTTPS, a host the catalogue lists for that
API, the default port, and only public addresses. The connection goes to the address
that was checked (the hostname stays in SNI and `Host`, so TLS still verifies it), which
closes the gap between the DNS check and its use. Redirects are followed by hand, each
hop checked again, up to MAX_REDIRECTS. The body is read in chunks up to a size cap and
an overall deadline. A per-host budget bounds the request rate to each provider.
"""

from __future__ import annotations

import ipaddress
import socket
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Literal
from urllib.parse import urljoin, urlsplit, urlunsplit

import httpx
from protego import Protego

from saudi_api import PROJECT_URL, __version__
from saudi_api.settings import Settings

# The redirect limit this stack already applies to remote fetches
# (`images.maximumRedirects` in Next.js 16).
MAX_REDIRECTS = 3
USER_AGENT = f"saudi-api/{__version__} (+{PROJECT_URL})"
# The budget for a provider whose entry states none: one request per second, the
# conservative rate the catalogue-curation skill sets for undocumented public endpoints.
DEFAULT_REQUESTS_PER_MINUTE = 60
_REDIRECTS = frozenset({301, 302, 303, 307, 308})
_CHUNK = 65_536

type Resolver = Callable[[str, int], list[str]]


class RefusalCode(StrEnum):
    """The request was not sent, or not followed, because a rule forbids it."""

    SCHEME_NOT_ALLOWED = "scheme_not_allowed"
    HOST_NOT_CATALOGUED = "host_not_catalogued"
    PORT_NOT_ALLOWED = "port_not_allowed"
    ADDRESS_NOT_PUBLIC = "address_not_public"
    TOO_MANY_REDIRECTS = "too_many_redirects"
    BUDGET_EXHAUSTED = "budget_exhausted"
    DISALLOWED_BY_ROBOTS = "disallowed_by_robots"


class FailureCode(StrEnum):
    """The request was sent and did not complete."""

    TIMEOUT = "timeout"
    CONNECTION_ERROR = "connection_error"
    TLS_ERROR = "tls_error"
    TOO_LARGE = "too_large"
    UNRESOLVABLE = "unresolvable"


class OutboundRefused(Exception):
    def __init__(self, code: RefusalCode, retry_after_seconds: float | None = None) -> None:
        super().__init__(code.value)
        self.code = code
        self.retry_after_seconds = retry_after_seconds


class OutboundFailed(Exception):
    def __init__(self, code: FailureCode) -> None:
        super().__init__(code.value)
        self.code = code


@dataclass(frozen=True)
class OutboundResponse:
    status: int
    url: str
    content_type: str | None
    body: bytes
    elapsed_ms: int


class HostBudget:
    """A per-host token bucket: `per_minute` requests, refilled continuously."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._buckets: dict[str, tuple[float, float]] = {}

    def take(self, host: str, per_minute: int, *, wait_seconds: float = 0.0) -> None:
        """Take one token, waiting up to `wait_seconds`; refuse when none comes."""
        deadline = time.monotonic() + wait_seconds
        while True:
            with self._lock:
                now = time.monotonic()
                tokens, updated = self._buckets.get(host, (float(per_minute), now))
                tokens = min(float(per_minute), tokens + (now - updated) * per_minute / 60.0)
                if tokens >= 1.0:
                    self._buckets[host] = (tokens - 1.0, now)
                    return
                self._buckets[host] = (tokens, now)
                needed = (1.0 - tokens) * 60.0 / per_minute
            if now + needed > deadline:
                raise OutboundRefused(RefusalCode.BUDGET_EXHAUSTED, retry_after_seconds=needed)
            time.sleep(needed)


BUDGET = HostBudget()

# RFC 9309 section 2.4: a crawler SHOULD NOT use a cached robots.txt for more than 24 hours.
ROBOTS_CACHE_SECONDS = 86_400


class RobotsCache:
    """robots.txt answers per origin, kept for ROBOTS_CACHE_SECONDS. A failed fetch is
    not cached: it disallows this attempt and the next attempt asks again."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._entries: dict[str, tuple[float, Protego | bool]] = {}

    def get(self, origin: str) -> Protego | bool | None:
        with self._lock:
            entry = self._entries.get(origin)
            if entry is None or entry[0] < time.monotonic():
                return None
            return entry[1]

    def put(self, origin: str, rules: Protego | bool) -> None:
        with self._lock:
            self._entries[origin] = (time.monotonic() + ROBOTS_CACHE_SECONDS, rules)


ROBOTS = RobotsCache()


def system_resolver(host: str, port: int) -> list[str]:
    try:
        infos = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    except socket.gaierror as error:
        raise OutboundFailed(FailureCode.UNRESOLVABLE) from error
    return list(dict.fromkeys(str(info[4][0]) for info in infos))


@dataclass
class OutboundClient:
    settings: Settings
    resolver: Resolver = system_resolver
    budget: HostBudget = field(default=BUDGET)
    robots: RobotsCache = field(default=ROBOTS)

    def get(
        self,
        url: str,
        *,
        allowed_hosts: frozenset[str],
        per_minute: int | None,
        wait_for_budget: bool,
        accept: str = "*/*",
        max_bytes: int | None = None,
    ) -> OutboundResponse:
        """GET `url`, following redirects by hand; raise OutboundRefused/OutboundFailed."""
        limit = max_bytes or self.settings.outbound_max_response_bytes
        deadline = time.monotonic() + self.settings.outbound_total_timeout_seconds
        started = time.monotonic()
        current = url
        for _hop in range(MAX_REDIRECTS + 1):
            target = self._check(current, allowed_hosts)
            if per_minute is not None:
                wait = max(0.0, deadline - time.monotonic()) if wait_for_budget else 0.0
                self.budget.take(target.host, per_minute, wait_seconds=wait)
            status, headers, body = self._send(target, accept, limit, deadline)
            location = headers.get("location")
            if status in _REDIRECTS and location:
                current = urljoin(current, location)
                continue
            return OutboundResponse(
                status=status,
                url=current,
                content_type=headers.get("content-type"),
                body=body,
                elapsed_ms=round((time.monotonic() - started) * 1000),
            )
        raise OutboundRefused(RefusalCode.TOO_MANY_REDIRECTS)

    def robots_allows(self, url: str, *, allowed_hosts: frozenset[str]) -> bool:
        """RFC 9309: a 4xx robots.txt allows all; 5xx or no answer disallows all."""
        parts = urlsplit(url)
        origin = f"{parts.scheme}://{parts.netloc}"
        cached = self.robots.get(origin)
        if cached is not None:
            return cached if isinstance(cached, bool) else bool(cached.can_fetch(url, "saudi-api"))
        robots_url = urlunsplit((parts.scheme, parts.netloc, "/robots.txt", "", ""))
        try:
            response = self.get(
                robots_url,
                allowed_hosts=allowed_hosts,
                per_minute=None,
                wait_for_budget=False,
                accept="text/plain",
                # RFC 9309 section 2.5: parse at least the first 500 KiB.
                max_bytes=512_000,
            )
        except OutboundFailed, OutboundRefused:
            return False
        if 400 <= response.status < 500:
            self.robots.put(origin, True)
            return True
        if not 200 <= response.status < 300:
            return False
        rules = Protego.parse(response.body.decode("utf-8", errors="replace"))
        self.robots.put(origin, rules)
        return bool(rules.can_fetch(url, "saudi-api"))

    def _check(self, url: str, allowed_hosts: frozenset[str]) -> _Target:
        parts = urlsplit(url)
        host = (parts.hostname or "").lower()
        loopback_mode = self.settings.outbound_allow_loopback_http
        if parts.scheme not in ("https", "http") or (parts.scheme == "http" and not loopback_mode):
            raise OutboundRefused(RefusalCode.SCHEME_NOT_ALLOWED)
        if parts.username or parts.password:
            raise OutboundRefused(RefusalCode.SCHEME_NOT_ALLOWED)
        if host not in allowed_hosts:
            raise OutboundRefused(RefusalCode.HOST_NOT_CATALOGUED)
        default_port = 443 if parts.scheme == "https" else 80
        port = parts.port or default_port
        if port != default_port and not loopback_mode:
            raise OutboundRefused(RefusalCode.PORT_NOT_ALLOWED)
        addresses = self.resolver(host, port)
        if not addresses:
            raise OutboundFailed(FailureCode.UNRESOLVABLE)
        for address in addresses:
            if not _allowed_address(address, loopback_mode):
                raise OutboundRefused(RefusalCode.ADDRESS_NOT_PUBLIC)
        if parts.scheme == "http" and not all(_is_loopback(a) for a in addresses):
            raise OutboundRefused(RefusalCode.SCHEME_NOT_ALLOWED)
        return _Target(
            scheme="https" if parts.scheme == "https" else "http",
            host=host,
            address=addresses[0],
            port=port,
            path=parts.path or "/",
            query=parts.query,
        )

    def _send(
        self, target: _Target, accept: str, limit: int, deadline: float
    ) -> tuple[int, dict[str, str], bytes]:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise OutboundFailed(FailureCode.TIMEOUT)
        timeout = httpx.Timeout(
            remaining, connect=min(self.settings.outbound_connect_timeout_seconds, remaining)
        )
        address = f"[{target.address}]" if ":" in target.address else target.address
        netloc = address if target.port in (80, 443) else f"{address}:{target.port}"
        pinned = urlunsplit((target.scheme, netloc, target.path, target.query, ""))
        host_header = target.host if target.port in (80, 443) else f"{target.host}:{target.port}"
        request_headers = {"Host": host_header, "User-Agent": USER_AGENT, "Accept": accept}
        extensions = {"sni_hostname": target.host} if target.scheme == "https" else {}
        # A new client per request: the pool keys connections by address, and a TLS
        # session verified for one catalogued host must not serve another on that address.
        try:
            with httpx.Client(follow_redirects=False, timeout=timeout, trust_env=False) as client:
                with client.stream(
                    "GET", pinned, headers=request_headers, extensions=extensions
                ) as r:
                    declared = r.headers.get("content-length")
                    if declared is not None and declared.isdigit() and int(declared) > limit:
                        raise OutboundFailed(FailureCode.TOO_LARGE)
                    # Decoded bytes count against the cap, so compression cannot
                    # carry a larger body past it.
                    body = bytearray()
                    for chunk in r.iter_bytes(_CHUNK):
                        body.extend(chunk)
                        if len(body) > limit:
                            raise OutboundFailed(FailureCode.TOO_LARGE)
                        if time.monotonic() > deadline:
                            raise OutboundFailed(FailureCode.TIMEOUT)
                    headers = {k.lower(): v for k, v in r.headers.items()}
                    return r.status_code, headers, bytes(body)
        except httpx.TimeoutException as error:
            raise OutboundFailed(FailureCode.TIMEOUT) from error
        except httpx.ConnectError as error:
            code = FailureCode.TLS_ERROR if "SSL" in str(error) else FailureCode.CONNECTION_ERROR
            raise OutboundFailed(code) from error
        except httpx.TransportError as error:
            raise OutboundFailed(FailureCode.CONNECTION_ERROR) from error


@dataclass(frozen=True)
class _Target:
    scheme: Literal["https", "http"]
    host: str
    address: str
    port: int
    path: str
    query: str


def _allowed_address(address: str, loopback_mode: bool) -> bool:
    ip = ipaddress.ip_address(address.split("%", 1)[0])
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped is not None:
        ip = ip.ipv4_mapped
    if ip.is_global:
        return True
    return loopback_mode and ip.is_loopback


def _is_loopback(address: str) -> bool:
    ip = ipaddress.ip_address(address.split("%", 1)[0])
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped is not None:
        ip = ip.ipv4_mapped
    return ip.is_loopback
