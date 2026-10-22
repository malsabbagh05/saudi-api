"""The rules every provider request passes (ADR-004), through the real client and a real
HTTP server on 127.0.0.1 (loopback HTTP is the explicit development and test opt-out)."""

import pytest
from sqlalchemy.engine import make_url

from saudi_api.outbound import (
    FailureCode,
    HostBudget,
    OutboundClient,
    OutboundFailed,
    OutboundRefused,
    RefusalCode,
    RobotsCache,
)
from saudi_api.settings import Settings
from tests.support.catalog import settings_for
from tests.support.http_server import Route, provider_server

LOOPBACK = frozenset({"127.0.0.1"})


def client(**overrides: object) -> OutboundClient:
    settings = settings_for(make_url("postgresql+psycopg://unused@127.0.0.1/unused"), **overrides)
    return OutboundClient(settings, budget=HostBudget(), robots=RobotsCache())


def test_a_catalogued_host_is_fetched():
    with provider_server(
        {"/data": Route(body=b'{"ok": true}', headers={"Content-Type": "application/json"})}
    ) as server:
        response = client().get(
            f"{server.url}/data", allowed_hosts=LOOPBACK, per_minute=None, wait_for_budget=False
        )
    assert response.status == 200
    assert response.body == b'{"ok": true}'
    assert response.content_type == "application/json"


@pytest.mark.parametrize(
    ("url", "code"),
    [
        ("https://example.com/", RefusalCode.HOST_NOT_CATALOGUED),
        ("ftp://127.0.0.1/", RefusalCode.SCHEME_NOT_ALLOWED),
        ("https://user:secret@127.0.0.1/", RefusalCode.SCHEME_NOT_ALLOWED),
    ],
    ids=["host-not-catalogued", "ftp-scheme", "userinfo"],
)
def test_requests_outside_the_rules_are_refused_before_sending(url, code):
    with pytest.raises(OutboundRefused) as error:
        client().get(
            url, allowed_hosts=LOOPBACK | {"example.org"}, per_minute=None, wait_for_budget=False
        )
    assert error.value.code is code


def test_without_the_opt_out_loopback_and_private_addresses_are_refused():
    strict = client(outbound_allow_loopback_http=False)
    with pytest.raises(OutboundRefused) as error:
        strict.get(
            "http://127.0.0.1/", allowed_hosts=LOOPBACK, per_minute=None, wait_for_budget=False
        )
    assert error.value.code is RefusalCode.SCHEME_NOT_ALLOWED
    for address in ("10.0.0.1", "169.254.169.254", "192.168.1.1"):
        with pytest.raises(OutboundRefused) as error:
            strict.get(
                f"https://{address}/",
                allowed_hosts=frozenset({address}),
                per_minute=None,
                wait_for_budget=False,
            )
        assert error.value.code is RefusalCode.ADDRESS_NOT_PUBLIC


def test_production_settings_refuse_the_loopback_opt_out():
    with pytest.raises(ValueError, match="not allowed in production"):
        Settings(environment="production", outbound_allow_loopback_http=True)


def test_redirects_are_followed_within_catalogued_hosts_up_to_the_limit():
    routes = {
        "/one": Route(status=302, headers={"Location": "/two"}),
        "/two": Route(status=302, headers={"Location": "/end"}),
        "/end": Route(body=b"done"),
        "/loop": Route(status=302, headers={"Location": "/loop"}),
        "/away": Route(status=302, headers={"Location": "https://example.com/"}),
    }
    with provider_server(routes) as server:
        outbound = client()
        response = outbound.get(
            f"{server.url}/one", allowed_hosts=LOOPBACK, per_minute=None, wait_for_budget=False
        )
        assert response.body == b"done"
        with pytest.raises(OutboundRefused) as loop:
            outbound.get(
                f"{server.url}/loop", allowed_hosts=LOOPBACK, per_minute=None, wait_for_budget=False
            )
        with pytest.raises(OutboundRefused) as away:
            outbound.get(
                f"{server.url}/away", allowed_hosts=LOOPBACK, per_minute=None, wait_for_budget=False
            )
    assert loop.value.code is RefusalCode.TOO_MANY_REDIRECTS
    assert away.value.code is RefusalCode.HOST_NOT_CATALOGUED


def test_a_body_over_the_cap_is_refused():
    with provider_server({"/big": Route(body=b"x" * 2048)}) as server:
        with pytest.raises(OutboundFailed) as error:
            client(outbound_max_response_bytes=1024).get(
                f"{server.url}/big", allowed_hosts=LOOPBACK, per_minute=None, wait_for_budget=False
            )
    assert error.value.code is FailureCode.TOO_LARGE


def test_a_slow_provider_times_out():
    with provider_server({"/slow": Route(body=b"late", delay_seconds=1.5)}) as server:
        with pytest.raises(OutboundFailed) as error:
            client(outbound_total_timeout_seconds=0.5).get(
                f"{server.url}/slow", allowed_hosts=LOOPBACK, per_minute=None, wait_for_budget=False
            )
    assert error.value.code is FailureCode.TIMEOUT


def test_robots_rules_follow_rfc_9309():
    rules = b"User-agent: *\nDisallow: /private\nUser-agent: Googlebot\nAllow: /\n"
    with provider_server({"/robots.txt": Route(body=rules)}) as server:
        outbound = client()
        assert outbound.robots_allows(f"{server.url}/public", allowed_hosts=LOOPBACK)
        assert not outbound.robots_allows(f"{server.url}/private/data", allowed_hosts=LOOPBACK)
        # The answer is cached: the file is read once.
        assert server.requests.count("/robots.txt") == 1
    with provider_server({}) as missing:
        assert client().robots_allows(f"{missing.url}/anything", allowed_hosts=LOOPBACK)
    with provider_server({"/robots.txt": Route(status=503)}) as failing:
        assert not client().robots_allows(f"{failing.url}/anything", allowed_hosts=LOOPBACK)


def test_the_budget_refuses_with_a_retry_time_once_spent():
    with provider_server({"/data": Route(body=b"ok")}) as server:
        outbound = client()
        outbound.get(
            f"{server.url}/data", allowed_hosts=LOOPBACK, per_minute=1, wait_for_budget=False
        )
        with pytest.raises(OutboundRefused) as error:
            outbound.get(
                f"{server.url}/data", allowed_hosts=LOOPBACK, per_minute=1, wait_for_budget=False
            )
    assert error.value.code is RefusalCode.BUDGET_EXHAUSTED
    assert error.value.retry_after_seconds and error.value.retry_after_seconds > 0
