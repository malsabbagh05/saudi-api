"""The REST API through FastAPI's TestClient (the real app and lifespan) on a real database."""

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from saudi_api.api.app import create_app, openapi_json
from tests.support.catalog import REPOSITORY_CATALOG, settings_for, sync
from tests.support.postgres import postgres_engine

WEB_OPENAPI = Path(__file__).resolve().parents[3] / "web" / "openapi.json"


@pytest.fixture(scope="module")
def client():
    engine = postgres_engine("rest")
    sync(engine, REPOSITORY_CATALOG)
    app = create_app(settings_for(engine.url))
    with TestClient(app) as test_client:
        yield test_client
    engine.dispose()


def test_readiness_fails_closed_until_the_catalogue_is_synced():
    engine = postgres_engine("rest_ready")
    try:
        with TestClient(create_app(settings_for(engine.url))) as unsynced:
            response = unsynced.get("/readyz")
            assert response.status_code == 503
            assert response.json() == {"status": "unavailable", "reason": "catalog_not_synced"}
            sync(engine, REPOSITORY_CATALOG)
            assert unsynced.get("/readyz").status_code == 200
            assert unsynced.get("/healthz").json() == {"status": "ok"}
    finally:
        engine.dispose()


def test_filters_narrow_the_list(client):
    open_apis = client.get("/v1/apis", params={"access": "open"}).json()
    assert {item["slug"] for item in open_apis["items"]} == {"datasaudi", "rcrc-open-data"}
    invocable = client.get("/v1/apis", params={"invocable": "true"}).json()
    assert [item["slug"] for item in invocable["items"]] == ["datasaudi"]
    payments = client.get("/v1/apis", params={"sector": "payments", "auth": "bearer"}).json()
    assert {item["slug"] for item in payments["items"]} == {"tamara-payments", "tabby-payments"}


def test_detail_carries_examples_with_credential_placeholders_only(client):
    detail = client.get("/v1/apis/wathq-commercial-registration").json()
    endpoint = next(e for e in detail["endpoints"] if e["id"] == "full-info")
    curl = next(x["code"] for x in endpoint["examples"] if x["language"] == "curl")
    assert '"https://api.wathq.sa/commercial-registration/fullinfo/7000000000?language=en"' in curl
    assert '-H "apiKey: $API_KEY"' in curl
    assert detail["access"]["api_key"] == {"in": "header", "name": "apiKey"}
    assert detail["verification"]["evidence"]
    assert detail["name"]["ar"] == "واجهة السجل التجاري (واثق)"


def test_errors_are_bounded_codes(client):
    missing = client.get("/v1/apis/no-such-api")
    assert missing.status_code == 404
    assert missing.json() == {"code": "not_found", "message": "no such API"}
    route = client.get("/v1/nothing-here")
    assert route.status_code == 404 and route.json()["code"] == "not_found"
    invalid = client.get("/v1/apis", params={"limit": 1000, "access": "everyone"})
    assert invalid.status_code == 422
    assert invalid.json() == {
        "code": "invalid_request",
        "message": "invalid parameters: access, limit",
    }


def test_security_headers_and_request_identity(client):
    response = client.get("/v1/sectors", headers={"X-Request-ID": "trace-123"})
    assert response.headers["x-request-id"] == "trace-123"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert "frame-ancestors 'none'" in response.headers["content-security-policy"]
    hostile = client.get("/v1/sectors", headers={"X-Request-ID": "bad id\nwith newline"})
    assert hostile.headers["x-request-id"] != "bad id\nwith newline"
    assert len(hostile.headers["x-request-id"]) == 32


def test_public_reads_allow_any_origin_but_mcp_does_not(client):
    read = client.get("/v1/sectors", headers={"Origin": "https://somewhere.example"})
    assert read.headers["access-control-allow-origin"] == "*"
    preflight = client.options(
        "/mcp",
        headers={"Origin": "https://somewhere.example", "Access-Control-Request-Method": "POST"},
    )
    assert "access-control-allow-origin" not in preflight.headers


def test_llms_txt_lists_the_catalogue(client):
    body = client.get("/llms.txt").text
    assert body.startswith("# Saudi API Catalogue")
    assert "/v1/apis/datasaudi" in body and "## Sectors" in body


def test_the_web_apps_openapi_copy_matches_the_api():
    """web/src/lib/api-schema.ts is generated from web/openapi.json; regenerate both with
    `saudi-api openapi > web/openapi.json && npm run generate:api` when this fails."""
    engine_url = "postgresql+psycopg://unused@127.0.0.1/unused"
    from sqlalchemy.engine import make_url

    current = json.loads(openapi_json(settings_for(make_url(engine_url))))
    assert json.loads(WEB_OPENAPI.read_text(encoding="utf-8")) == current
