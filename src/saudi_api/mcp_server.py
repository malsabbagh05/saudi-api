"""The MCP server: how AI agents discover, understand and call the catalogued APIs.

Tools read through `queries.py`, the same owner as the REST API, and return the shapes
in `contracts.py`. `call_endpoint` reaches a provider only through `invoke.py`. Rules:
`.agents/skills/engineering-standards/references/mcp.md`.
"""

from __future__ import annotations

from typing import Annotated

from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session, sessionmaker

from saudi_api import __version__, queries
from saudi_api.catalog.schema import AccessLevel
from saudi_api.contracts import (
    ApiDetail,
    ApiSummary,
    DatasetDetail,
    DatasetSummary,
    Page,
    ProviderSummary,
    SearchHit,
    SectorOut,
)
from saudi_api.invoke import MAX_OUTPUT_CHARACTERS, ArgumentValue, InvocationError, invoke
from saudi_api.llms import render_guide
from saudi_api.outbound import OutboundClient
from saudi_api.settings import Settings

_READ = ToolAnnotations(read_only_hint=True, open_world_hint=False)
_CALL = ToolAnnotations(read_only_hint=True, open_world_hint=True)

INSTRUCTIONS = """\
Saudi API Catalogue: a verified, bilingual (Arabic and English) catalogue of Saudi
government, open-data, financial, business and other APIs, and of the statistical
datasets they publish (GASTAT, SAMA and others through DataSaudi).

Start with `search_catalog` (any language). Then `get_api` gives documentation,
authentication, endpoints and ready-to-run examples, and `get_dataset` gives a dataset's
measures, dimensions and example query. `call_endpoint` calls an endpoint for you only
when the API needs no credentials and allows automated access (`agent_invocation`);
otherwise use the examples with the user's own credentials. Every text field has `en`
and `ar`; answer in the user's language.
"""


class SearchResult(BaseModel):
    hits: list[SearchHit]


class SectorList(BaseModel):
    sectors: list[SectorOut]


class ProviderList(BaseModel):
    providers: list[ProviderSummary]


class ApiDetailResult(BaseModel):
    api: ApiDetail
    truncated: bool = Field(description="True when examples or operations were cut to fit.")


class InvocationResult(BaseModel):
    api_slug: str
    endpoint_id: str
    url: str
    status: int = Field(description="The provider's HTTP status.")
    content_type: str | None
    body: str = Field(description="The provider's response body, as text.")
    truncated: bool
    elapsed_ms: int


def build_mcp(settings: Settings, sessions: sessionmaker[Session]) -> MCPServer:
    mcp = MCPServer(
        "saudi-api",
        title="Saudi API Catalogue",
        description="Discover, understand and call Saudi APIs, in Arabic and English.",
        instructions=INSTRUCTIONS,
        website_url=settings.public_base_url,
        version=__version__,
    )
    client = OutboundClient(settings)

    @mcp.tool(title="Search the catalogue", annotations=_READ)
    def search_catalog(
        query: Annotated[
            str,
            Field(min_length=1, max_length=200, description="Words in Arabic or English."),
        ],
        limit: Annotated[int, Field(ge=1, le=50)] = 10,
    ) -> SearchResult:
        """Search APIs and datasets together, best match first.

        Use this first. Follow an `api` hit with get_api and a `dataset` hit with
        get_dataset.
        """
        with sessions() as db:
            return SearchResult(hits=queries.search_catalog(db, query, limit))

    @mcp.tool(title="List APIs", annotations=_READ)
    def list_apis(
        sector: Annotated[str | None, Field(description="A sector slug from list_sectors.")] = None,
        provider: Annotated[
            str | None, Field(description="A provider slug from list_providers.")
        ] = None,
        access: AccessLevel | None = None,
        invocable: Annotated[
            bool | None, Field(description="Only APIs call_endpoint can call.")
        ] = None,
        query: Annotated[str | None, Field(max_length=200)] = None,
        limit: Annotated[int, Field(ge=1, le=50)] = 20,
        offset: Annotated[int, Field(ge=0, le=10_000)] = 0,
    ) -> Page[ApiSummary]:
        """List catalogued APIs, filtered by sector, provider, access level or invocability."""
        with sessions() as db:
            return queries.list_apis(
                db,
                q=query,
                sector=sector,
                provider=provider,
                access=access,
                invocable=invocable,
                limit=limit,
                offset=offset,
            )

    @mcp.tool(title="Get an API", annotations=_READ)
    def get_api(
        slug: Annotated[str, Field(max_length=64, description="The API slug.")],
    ) -> ApiDetailResult:
        """Everything about one API: documentation and terms links, access and
        authentication, base URLs, endpoints with parameters and code examples (curl,
        Python, JavaScript), the provider's OpenAPI operations, and verification evidence.
        """
        with sessions() as db:
            detail = queries.get_api(db, slug)
        if detail is None:
            raise ToolError("unknown_api: no API has this slug; use search_catalog")
        return _fit_api(detail)

    @mcp.tool(title="List sectors", annotations=_READ)
    def list_sectors() -> SectorList:
        """The sectors APIs are grouped by, with how many APIs each has."""
        with sessions() as db:
            return SectorList(sectors=queries.list_sectors(db))

    @mcp.tool(title="List providers", annotations=_READ)
    def list_providers() -> ProviderList:
        """The government entities and companies that publish the catalogued APIs."""
        with sessions() as db:
            return ProviderList(providers=queries.list_providers(db))

    @mcp.tool(title="Search datasets", annotations=_READ)
    def search_datasets(
        query: Annotated[str | None, Field(max_length=200)] = None,
        api_slug: Annotated[
            str | None, Field(description="Only datasets of this API (e.g. datasaudi).")
        ] = None,
        limit: Annotated[int, Field(ge=1, le=50)] = 20,
        offset: Annotated[int, Field(ge=0, le=10_000)] = 0,
    ) -> Page[DatasetSummary]:
        """Search statistical datasets (GASTAT, SAMA, ministries) that APIs publish."""
        with sessions() as db:
            return queries.list_datasets(db, q=query, api_slug=api_slug, limit=limit, offset=offset)

    @mcp.tool(title="Get a dataset", annotations=_READ)
    def get_dataset(
        api_slug: Annotated[str, Field(max_length=64)],
        dataset_id: Annotated[str, Field(max_length=128)],
    ) -> DatasetDetail:
        """A dataset's measures, dimensions and levels, and example arguments for
        call_endpoint (endpoint `query-cube`) that return its data."""
        with sessions() as db:
            detail = queries.get_dataset(db, api_slug, dataset_id)
        if detail is None:
            raise ToolError("unknown_dataset: use search_datasets to find one")
        return detail

    @mcp.tool(title="Call an endpoint", annotations=_CALL)
    def call_endpoint(
        api_slug: Annotated[str, Field(max_length=64)],
        endpoint_id: Annotated[str, Field(max_length=64)],
        arguments: Annotated[
            dict[str, ArgumentValue],
            Field(description="Path and query parameters by name, as get_api lists them."),
        ] = {},  # noqa: B006 - the SDK copies arguments per call; never mutated
    ) -> InvocationResult:
        """Call a GET endpoint of an API whose `agent_invocation` is true, and return the
        provider's response. The provider's rate budget applies; a refusal says when to
        retry. Bodies over the size cap are cut and marked `truncated`."""
        with sessions() as db:
            api = queries.load_api_entry(
                db, api_slug, allow_loopback_http=settings.outbound_allow_loopback_http
            )
        if api is None:
            raise ToolError("unknown_api: no API has this slug; use search_catalog")
        try:
            result = invoke(client, api, endpoint_id, arguments)
        except InvocationError as error:
            raise ToolError(_invocation_message(error)) from error
        return InvocationResult(
            api_slug=api_slug,
            endpoint_id=endpoint_id,
            url=result.url,
            status=result.status,
            content_type=result.content_type,
            body=result.body,
            truncated=result.truncated,
            elapsed_ms=result.elapsed_ms,
        )

    @mcp.resource(
        "saudi-api://guide",
        name="guide",
        title="How to use the Saudi API Catalogue",
        mime_type="text/markdown",
    )
    def guide() -> str:
        """The catalogue's guide for agents: what it holds and how to use the tools."""
        with sessions() as db:
            return render_guide(db, settings)

    return mcp


def _fit_api(detail: ApiDetail) -> ApiDetailResult:
    """Cut examples, then the spec's operation list, until the result fits the cap."""
    if len(detail.model_dump_json()) <= MAX_OUTPUT_CHARACTERS:
        return ApiDetailResult(api=detail, truncated=False)
    lighter = detail.model_copy(
        update={
            "endpoints": [
                e.model_copy(update={"examples": [x for x in e.examples if x.language == "curl"]})
                for e in detail.endpoints
            ]
        }
    )
    spec = lighter.spec
    if spec is not None:
        operations = list(spec.operations)
        while operations and len(lighter.model_dump_json()) > MAX_OUTPUT_CHARACTERS:
            operations = operations[: len(operations) // 2]
            lighter = lighter.model_copy(
                update={"spec": spec.model_copy(update={"operations": operations})}
            )
    return ApiDetailResult(api=lighter, truncated=True)


def _invocation_message(error: InvocationError) -> str:
    match error.code.value:
        case "not_invocable":
            return (
                "not_invocable: this API needs credentials or does not allow automated "
                "access; use the examples from get_api with the user's own credentials"
            )
        case "unknown_endpoint":
            return "unknown_endpoint: use an endpoint id that get_api lists for this API"
        case "invalid_arguments":
            parts = []
            if error.fields:
                parts.append("missing or invalid: " + ", ".join(error.fields[:20]))
            if error.undeclared:
                parts.append(f"{error.undeclared} parameter(s) this endpoint does not declare")
            return "invalid_arguments: " + "; ".join(parts) + "; see get_api"
        case "disallowed_by_robots":
            return (
                "disallowed_by_robots: the provider's robots.txt does not allow automated "
                "requests to this path; use get_api's examples instead"
            )
        case "budget_exhausted":
            wait = error.retry_after_seconds or 1.0
            return f"budget_exhausted: the provider's rate budget is spent; retry in {wait:.0f} s"
        case code:
            return f"{code}: the provider could not be reached; try again later"
