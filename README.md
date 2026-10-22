# Saudi API Catalogue · دليل الواجهات البرمجية السعودية

An open, verified, bilingual catalogue of Saudi APIs for developers and AI agents.

It catalogues government services, open data, statistics, finance and payments, tax,
commerce, transport, health and business APIs. Each entry says who may use the API and how to
get access, how it authenticates, its base URLs and endpoints, and gives ready-to-run
examples in curl, Python and JavaScript. Every fact links to the provider's own
documentation, with the date it was checked. Statistical datasets from GASTAT, SAMA and
ministries are discovered automatically and searchable beside the APIs, in Arabic and
English.

The same catalogue is served three ways:

- **Web directory**: Arabic and English, right-to-left and left-to-right, searchable and
  filterable by sector, access level and authentication.
- **REST API** under `/v1`, documented with OpenAPI at `/docs`, plus `/llms.txt`.
- **MCP server** at `/mcp`, so Claude, ChatGPT, Cursor and other MCP clients can search the
  catalogue, read an API's documentation and examples, and call keyless endpoints whose
  terms allow it.

> Independent project: not affiliated with, endorsed by or operated by any government
> entity or provider listed. Provider names identify the sources of their own APIs.

## What is in the catalogue

21 APIs from 17 providers in 16 sectors, and 252 statistical datasets (2026-10-22),
including DataSaudi (GASTAT, SAMA, Ministry of Health statistics), the National Address,
ZATCA FATOORA e-invoicing, Wathq commercial registration, company contracts, real estate
deeds, powers of attorney and employee information, Najiz, nphies, SAMA Open Banking, Al
Rajhi Bank, Lean, Moyasar, Tamara, Tabby, Salla, Zid, Taqnyat and Riyadh's open data
(metro, bus, traffic). The catalogue grows by reviewed pull requests; see
[Contributing](#contributing).

## Quick start

Requirements: Docker. For development without containers: Python 3.14 with
[uv](https://docs.astral.sh/uv/), Node.js 24 and Docker for PostgreSQL.

```bash
cp .env.example .env.development
docker compose up --build
```

- Web directory: <http://localhost:3000>
- REST API and its reference: <http://localhost:8000/docs>
- MCP endpoint: `http://localhost:8000/mcp`

From source:

```bash
uv sync --frozen
cp .env.example .env.development
make dev-db migrate sync     # PostgreSQL, schema, catalogue projection
make serve                   # API on 127.0.0.1:8000
make worker                  # discovery, reachability checks, spec refresh (another terminal)
cd web && npm ci && npm run dev   # web on localhost:3000 (another terminal)
```

## Connect an AI agent

```bash
claude mcp add --transport http saudi-api http://localhost:8000/mcp
```

Cursor (`.cursor/mcp.json`):

```json
{ "mcpServers": { "saudi-api": { "url": "http://localhost:8000/mcp" } } }
```

Tools: `search_catalog`, `list_apis`, `get_api`, `list_sectors`, `list_providers`,
`search_datasets`, `get_dataset` and `call_endpoint`. `call_endpoint` reaches only `GET`
endpoints of APIs that need no credentials, whose terms allow automated access and whose
robots.txt does not forbid it, within each provider's request budget. The platform never
holds or forwards provider credentials. Self-hosters can also run `saudi-api mcp-stdio`.

## REST API

```bash
curl "http://localhost:8000/v1/search?q=العنوان الوطني"
curl "http://localhost:8000/v1/apis?sector=payments&auth=bearer"
curl "http://localhost:8000/v1/apis/zatca-e-invoicing"
curl "http://localhost:8000/v1/datasets?q=inflation"
```

Every text field has `en` and `ar`. Errors are `{"code", "message"}` with a bounded code.

## How it works

| Part | Where | Decision |
| --- | --- | --- |
| Curated catalogue (YAML, reviewed in pull requests) | `catalog/` | [ADR-002](docs/architecture/adr-002-catalogue-authority.md) |
| API service, MCP server, worker, CLI (FastAPI, MCP SDK, SQLAlchemy) | `src/saudi_api/` | [ADR-001](docs/architecture/adr-001-platform-stack.md) |
| Bilingual search (PostgreSQL full-text search and trigrams) | `src/saudi_api/search.py` | [ADR-003](docs/architecture/adr-003-bilingual-search.md) |
| Provider requests, robots.txt, budgets, discovery, checks | `src/saudi_api/outbound.py`, `jobs/` | [ADR-004](docs/architecture/adr-004-outbound-requests-and-jobs.md) |
| Web directory (Next.js, next-intl, shadcn/ui) | `web/` | [ADR-001](docs/architecture/adr-001-platform-stack.md) |

The worker discovers datasets from DataSaudi's index daily, checks each API's
reachability hourly, and refreshes provider-published OpenAPI documents daily. Provider
requests use HTTPS to catalogued hosts only, refuse private addresses, follow robots.txt
(RFC 9309), stay within a per-provider budget and identify themselves.

More: [configuration](docs/development/configuration.md),
[operations](docs/development/operations.md), [catalogue files](docs/development/catalogue.md),
[web app](docs/development/web.md), [all docs](docs/README.md).

## Contributing

Add or correct an API with a pull request that changes `catalog/`; the
[catalogue reference](docs/development/catalogue.md) explains every field, and an entry
needs evidence from the provider's own documentation or a live request. Code changes follow
[CONTRIBUTING.md](CONTRIBUTING.md). Report vulnerabilities as [SECURITY.md](SECURITY.md)
describes.

## License

[Apache License 2.0](LICENSE).
