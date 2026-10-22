# Operations

How the services run, release and report. Choosing where they run is the project owner's
decision, recorded in an ADR before the first deployment (`AGENTS.md`); `compose.yaml` and
the Dockerfiles build and run the stack locally and are not that decision.

## Processes

| Process | Command | Notes |
| --- | --- | --- |
| API service | `saudi-api serve --host 0.0.0.0 --port 8000 [--workers N]` | REST `/v1`, `/llms.txt`, MCP at `/mcp`, probes. Stateless: run several behind a load balancer. |
| Worker | `saudi-api worker` | Runs `discover`, `check` and `refresh-specs` on their intervals. Safe to run more than one: each job takes a PostgreSQL advisory lock, so a second worker skips a job already running. Stops after the job in progress on SIGTERM. |
| Web | `node server.js` in the web image | Next.js standalone server. |

A platform scheduler can replace the worker: `saudi-api jobs run discover|check|refresh-specs|all`
runs one job once, under the same lock (ADR-004).

## Release order

1. `saudi-api migrate`: apply Alembic migrations.
2. `saudi-api catalog sync`: write the catalogue projection. It writes nothing when the
   catalogue's digest is unchanged.
3. Start or roll the API services and the worker.

`GET /readyz` answers `503 {"reason": "catalog_not_synced"}` until the database holds the
projection of the catalogue the process was built with, and `503 {"reason": "database"}`
when PostgreSQL is unreachable. `GET /healthz` is the liveness probe; it does no I/O.

## Behind a proxy

- Set `MCP_ALLOWED_HOSTS` to the public hostname, or `/mcp` answers `421 Misdirected Request`.
- Run uvicorn with `--proxy-headers --forwarded-allow-ips=<proxy address>` (the
  `serve` command enables proxy headers; set `FORWARDED_ALLOW_IPS`) so redirects keep HTTPS.
- Rate-limit public traffic at the edge. The application bounds provider traffic itself
  (per-host budgets), not visitors.
- Route provider traffic through an egress proxy that denies private ranges, as the MCP
  security guidance recommends; `outbound.py` already refuses non-public addresses and
  pins each connection to the address it checked.

## Jobs and their outcomes

`GET /v1/stats` lists the latest run of each job. Each run is also one `job started` and one
`job finished` (or `job failed`) log line with its `run_id`.

| Job | Writes | Outcomes per API |
| --- | --- | --- |
| `discover` | `datasets` | `succeeded`, `disallowed_by_robots`, `http_error`, `timeout`, `connection_error`, `tls_error`, `invalid_payload`, refusal codes. A failed read keeps the stored datasets. |
| `check` | `api_checks` | `reachable`, `http_error`, `timeout`, `connection_error`, `tls_error`, `refused_by_policy`, with `consecutive_failures` and `region`. |
| `refresh-specs` | `api_specs` | `fetched`, `unchanged`, `disallowed_by_robots`, `invalid_document`, `too_large`, transport failures. A failed attempt keeps the last good document. |

Several government hosts refuse connections from outside Saudi Arabia, so checks run from
abroad report them unreachable; set `CHECK_REGION` so readers can tell.

## Logs

JSON lines on stdout: `time`, `level`, `logger`, `message`, and fields such as
`request_id`, `run_id`, `job`, `route` (the route template, never the query string),
`status` and `duration_ms`. Logs never carry credentials, provider bodies or search terms.
The API returns the request ID in `X-Request-ID`; the web app forwards a visitor's
`X-Request-ID` to the API.

## SQL performance

Start a diagnosis from `pg_stat_statements` (`docs/development/database.md`). The search
statements use GIN indexes on `search_vector` and `search_text`
(`tests/integration/search/test_bilingual_search.py` proves the plan).
