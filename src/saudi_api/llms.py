"""The catalogue's guide for language models: `/llms.txt` and the MCP `guide` resource.

The format follows the llms.txt proposal (https://llmstxt.org/): a title, a summary
quote, then sections of links. It is rendered from the database on each request.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from saudi_api import queries
from saudi_api.settings import Settings


def render_guide(db: Session, settings: Settings) -> str:
    api_base = settings.public_base_url.rstrip("/")
    web_base = settings.web_base_url.rstrip("/")
    stats = queries.catalog_stats(db)
    sectors = queries.list_sectors(db)
    apis = queries.list_apis(db, limit=queries.MAX_PAGE, offset=0)
    lines = [
        "# Saudi API Catalogue",
        "",
        "> A verified, bilingual (Arabic and English) catalogue of Saudi government, "
        "open-data, financial, business and other APIs, and of the statistical datasets "
        f"they publish. {stats.apis} APIs from {stats.providers} providers, "
        f"{stats.datasets} datasets.",
        "",
        "Every curated fact links to the provider's own documentation, with the date it was "
        "checked. Text fields carry `en` and `ar`. The platform never holds provider "
        "credentials: follow each API's access instructions with your own.",
        "",
        "## For agents",
        "",
        f"- [MCP server (Streamable HTTP)]({api_base}/mcp): tools search_catalog, list_apis, "
        "get_api, list_sectors, list_providers, search_datasets, get_dataset, call_endpoint",
        f"- [REST API reference (OpenAPI)]({api_base}/openapi.json)",
        f"- [Search APIs and datasets]({api_base}/v1/search?q=statistics): `GET /v1/search?q=`",
        f"- [All APIs]({api_base}/v1/apis): filters `sector`, `provider`, `access`, `auth`, "
        "`invocable`, `q`",
        f"- [Datasets]({api_base}/v1/datasets): statistical datasets, searchable with `q`",
        "",
        "## Sectors",
        "",
    ]
    lines += [
        f"- [{s.name.en} / {s.name.ar}]({web_base}/en/apis?sector={s.slug}): {s.api_count} APIs"
        for s in sectors
        if s.api_count
    ]
    lines += ["", "## APIs", ""]
    for api in apis.items:
        access = f"{api.access.level}, auth: {', '.join(api.access.auth)}"
        lines.append(
            f"- [{api.name.en}]({api_base}/v1/apis/{api.slug}): {api.summary.en} "
            f"({api.provider.name.en}; {access})"
        )
    if apis.total > len(apis.items):
        lines.append(f"- {apis.total - len(apis.items)} more: {api_base}/v1/apis?offset=100")
    lines += [
        "",
        "## Optional",
        "",
        f"- [Web directory, English]({web_base}/en)",
        f"- [Web directory, Arabic]({web_base}/ar)",
        "",
    ]
    return "\n".join(lines)
