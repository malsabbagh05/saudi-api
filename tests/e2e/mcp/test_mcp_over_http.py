"""The MCP server through its real transport: uvicorn serving the app, the MCP SDK's own
client over Streamable HTTP, the real database, and a provider on 127.0.0.1."""

import socket
import threading
import time
from collections.abc import Iterator
from contextlib import contextmanager

import httpx
import pytest
import uvicorn
from mcp import Client

from saudi_api.api.app import create_app
from saudi_api.settings import Settings
from tests.support.catalog import (
    api_entry,
    copy_repository_catalog,
    settings_for,
    sync,
    write_api,
    write_provider,
)
from tests.support.http_server import Route, provider_server
from tests.support.postgres import postgres_engine


@pytest.fixture
def anyio_backend():
    return "asyncio"


@contextmanager
def serve(settings: Settings) -> Iterator[str]:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    server = uvicorn.Server(
        uvicorn.Config(create_app(settings), host="127.0.0.1", port=port, log_level="warning")
    )
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    deadline = time.monotonic() + 20
    while not server.started:
        if time.monotonic() > deadline:
            raise RuntimeError("the API did not start")
        time.sleep(0.05)
    try:
        yield f"http://127.0.0.1:{port}"
    finally:
        server.should_exit = True
        thread.join(timeout=10)


def invocable_entry(base: str) -> dict[str, object]:
    return api_entry(
        "local-stats",
        documentation_url=f"{base}/docs",
        base_urls=[{"url": base}],
        endpoints=[
            {
                "id": "figures",
                "method": "GET",
                "path": "/figures/{series}",
                "summary": {"en": "Figures of a series.", "ar": "أرقام سلسلة."},
                "parameters": [
                    {
                        "name": "series",
                        "in": "path",
                        "required": True,
                        "description": {"en": "Series.", "ar": "السلسلة."},
                        "example": "cpi",
                    },
                    {
                        "name": "year",
                        "in": "query",
                        "type": "integer",
                        "description": {"en": "Year.", "ar": "السنة."},
                    },
                ],
            }
        ],
        usage={
            "agent_invocation": "allowed",
            "max_requests_per_minute": 60,
            "policy_evidence": ["https://provider.example/terms"],
        },
    )


@pytest.mark.anyio
@pytest.mark.timeout(120)  # starts a server, a provider and a database clone
async def test_an_agent_discovers_reads_and_calls_an_api_over_mcp(tmp_path):
    engine = postgres_engine("mcp_e2e")
    figures = Route(
        body=b'{"series":"cpi","year":2025,"value":1.9}',
        headers={"Content-Type": "application/json"},
    )
    try:
        with provider_server({"/figures/cpi": figures}) as provider:
            directory = copy_repository_catalog(tmp_path)
            write_provider(directory)
            write_api(directory, invocable_entry(provider.url))
            sync(engine, directory)
            with serve(settings_for(engine.url, directory)) as base:
                async with Client(f"{base}/mcp") as client:
                    assert client.protocol_version == "2026-07-28"
                    tools = {tool.name for tool in (await client.list_tools()).tools}
                    assert {"search_catalog", "get_api", "get_dataset", "call_endpoint"} <= tools

                    hits = await client.call_tool(
                        "search_catalog", {"query": "الفوترة الإلكترونية"}
                    )
                    assert hits.structured_content["hits"][0]["api_slug"] == "zatca-e-invoicing"

                    detail = await client.call_tool("get_api", {"slug": "spl-national-address"})
                    assert (
                        detail.structured_content["api"]["access"]["api_key"]["name"] == "api_key"
                    )

                    called = await client.call_tool(
                        "call_endpoint",
                        {
                            "api_slug": "local-stats",
                            "endpoint_id": "figures",
                            "arguments": {"series": "cpi", "year": 2025},
                        },
                    )
                    assert not called.is_error
                    assert called.structured_content["status"] == 200
                    assert '"value":1.9' in called.structured_content["body"]

                    refused = await client.call_tool(
                        "call_endpoint",
                        {
                            "api_slug": "wathq-commercial-registration",
                            "endpoint_id": "full-info",
                            "arguments": {"id": "1"},
                        },
                    )
                    assert refused.is_error and "not_invocable" in refused.content[0].text

                    invented = await client.call_tool(
                        "call_endpoint",
                        {
                            "api_slug": "local-stats",
                            "endpoint_id": "figures",
                            "arguments": {"series": "cpi", "token": "x"},
                        },
                    )
                    assert invented.is_error
                    assert (
                        "1 parameter(s) this endpoint does not declare" in invented.content[0].text
                    )
                    assert "token" not in invented.content[0].text
            # robots.txt first, then the one call; refused calls never reached the provider.
            assert provider.requests == ["/robots.txt", "/figures/cpi?year=2025"]
    finally:
        engine.dispose()


def test_mcp_answers_only_the_configured_hosts():
    engine = postgres_engine("mcp_hosts")
    try:
        settings = settings_for(engine.url, mcp_allowed_hosts=["catalogue.example"])
        with serve(settings) as base:
            response = httpx.post(
                f"{base}/mcp",
                json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"},
                headers={"Accept": "application/json, text/event-stream"},
            )
        assert response.status_code == 421
    finally:
        engine.dispose()
