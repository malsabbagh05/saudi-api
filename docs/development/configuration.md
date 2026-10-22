# Configuration

Each process reads its settings once from the environment, and from the file `ENV_FILE`
names when it is set (`src/saudi_api/settings.py`). Each environment has one configuration
file (`AGENTS.md`, "Development environment"): `.env.development` locally, copied from
[`.env.example`](../../.env.example). Never commit a filled-in file.

## API service, worker and CLI

| Setting | Default | What it does |
| --- | --- | --- |
| `ENVIRONMENT` | `development` | `development`, `test` or `production`. Production refuses `OUTBOUND_ALLOW_LOOPBACK_HTTP`. |
| `DATABASE_URL` | `postgresql+psycopg://postgres@127.0.0.1:5432/saudi_api` | The PostgreSQL database. Use `127.0.0.1`, not `localhost`: on Windows `localhost` can resolve to `::1`, where a Docker port bound to `127.0.0.1` never answers. |
| `DATABASE_POOL_SIZE`, `DATABASE_MAX_OVERFLOW` | `10`, `30` | Connections per process. Their sum, 40, is AnyIO's default thread limiter for FastAPI's `def` handlers, so a handler thread never waits for a connection. |
| `DATABASE_CONNECT_TIMEOUT_SECONDS` | `5` | libpq waits forever by default; a wrong address fails readiness instead. |
| `CATALOG_DIR` | `catalog/` in the source tree | The catalogue the process syncs and checks readiness against. The image sets `/app/catalog`. |
| `PUBLIC_BASE_URL` | `http://localhost:8000` | The API's public origin, used in `/llms.txt`, the MCP guide and `/`. |
| `WEB_BASE_URL` | `http://localhost:3000` | The web directory's public origin, linked from `/llms.txt`. |
| `MCP_ALLOWED_HOSTS` | empty | Comma-separated hostnames the MCP endpoint answers for. Empty keeps the SDK's localhost-only default, so a deployment behind a real hostname answers `421` until this is set ([MCP: Deploy & scale](https://py.sdk.modelcontextprotocol.io/run/deploy/)). |
| `MCP_ALLOWED_ORIGINS` | empty | Origins that may call `/mcp` from a browser (CORS and the transport's own Origin check). |
| `OUTBOUND_CONNECT_TIMEOUT_SECONDS` | `5` | Connect timeout for provider requests: about 15 times the slowest connect measured on 2026-10-22 (0.32 s). |
| `OUTBOUND_TOTAL_TIMEOUT_SECONDS` | `20` | Deadline for one provider request, redirects included: about 12 times the slowest response measured (1.68 s, DataSaudi `/cubes`, 572 KB). |
| `OUTBOUND_MAX_RESPONSE_BYTES` | `4194304` | Largest provider body read: the MCP SDK's `max_request_body_size`, the largest single message the stack accepts. |
| `OUTBOUND_ALLOW_LOOPBACK_HTTP` | `false` | Development and test only: allow `http://` to loopback addresses, the explicit opt-out the MCP security guidance asks for. Refused in production. |
| `CHECK_REGION` | `unspecified` | Where reachability checks run from; shown with every result, because several Saudi hosts refuse connections from abroad. |
| `DISCOVER_INTERVAL_SECONDS` | `86400` | How often the worker refreshes discovered datasets. |
| `CHECK_INTERVAL_SECONDS` | `3600` | How often the worker checks each API's reachability. |
| `REFRESH_SPECS_INTERVAL_SECONDS` | `86400` | How often the worker refreshes provider OpenAPI documents. |
| `LOG_LEVEL` | `INFO` | `DEBUG`, `INFO`, `WARNING` or `ERROR`. Logs are JSON lines on stdout (stderr for `mcp-stdio`). |

## Web directory

| Setting | Read | What it does |
| --- | --- | --- |
| `API_BASE_URL` | at request time | Where the server reaches the REST API (`http://api:8000` in compose). Never sent to browsers. |
| `PUBLIC_API_URL` | at build time | The API's public origin shown in the MCP setup, REST links and examples. |
| `NEXT_PUBLIC_SITE_URL` | at build time | The site's public origin, used in metadata, `sitemap.xml` and `robots.txt`. |

`PUBLIC_API_URL` and `NEXT_PUBLIC_SITE_URL` are part of the prerendered shell, so an image
is built for one public origin (`docker build --build-arg PUBLIC_API_URL=...`).
