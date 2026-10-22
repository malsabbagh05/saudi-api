# ADR-001: Platform stack and process layout

- Status: accepted
- Date: 2026-10-22
- Deciders: @malsabbagh05 (project owner), accepted 2026-10-22
- Issue: none yet; the goal was set in the session of 2026-10-22

## Context

The product is an open catalogue of Saudi APIs that people browse on a web directory and
that programs and AI agents read through a REST API and a Model Context Protocol (MCP)
server. Arabic and English are both first-class, including right-to-left layout.

The repository was bootstrapped from the engineering-standards kit. The kit assumes Python
3.14 with uv, Ruff, ty and pytest; PostgreSQL with SQLAlchemy and Alembic; and,
optionally, a Next.js app in `web/` with a `Web static checks` CI job. The bootstrap removed
the web variant because no web app existed then. The web directory is now a requirement, so
the kit's web variant applies.

Checked sources:

- MCP Python SDK 2.3.0: `MCPServer`, `streamable_http_app()`, mounting into a host app whose
  lifespan enters `session_manager.run()`, and the Host allowlist that rejects unknown hosts
  with `421` ([run/asgi](https://py.sdk.modelcontextprotocol.io/run/asgi/),
  [run/deploy](https://py.sdk.modelcontextprotocol.io/run/deploy/)). Protocol 2026-07-28 is
  stateless, so any replica serves any request.
- FastAPI runs `def` handlers in its thread pool and `async def` handlers on the event loop;
  `scripts/ci/check_async_routes.py` rejects an `async def` handler that never awaits.
- psycopg 3 cannot run its async mode on Windows' default `ProactorEventLoop`
  ([psycopg: Asynchronous operations](https://www.psycopg.org/psycopg3/docs/advanced/async.html#async)).
  Developers here work on Windows; production runs Linux containers.
- Next.js 16 replaces `middleware.ts` with `proxy.ts`, removes `next lint`, and requires
  Node.js 20.9+ ([Next.js 16](https://nextjs.org/blog/next-16)). next-intl 4 documents
  locale-prefixed routing for the App Router
  ([next-intl](https://next-intl.dev/docs/getting-started/app-router/with-i18n-routing)).
  shadcn/ui transforms components to logical, direction-aware classes when `rtl` is set
  ([shadcn RTL](https://ui.shadcn.com/docs/rtl)).

## Decision

- **API service** (`src/saudi_api`): one FastAPI application serves the REST API under
  `/v1`, the health probes, `/llms.txt`, and the MCP Streamable HTTP endpoint at `/mcp`. The
  FastAPI lifespan owns the MCP session manager. Database work is synchronous SQLAlchemy 2
  on psycopg 3 inside `def` handlers and `def` MCP tools, which both frameworks run in a
  thread pool. Outbound HTTP uses `httpx`.
- **Worker** (`saudi-api worker`): one long-running process runs the scheduled jobs
  (ADR-004). It shares the package, settings and database with the API service.
- **CLI** (`saudi-api`): migrations, catalogue validation and sync, single job runs, and
  the MCP stdio transport for self-hosters.
- **Web directory** (`web/`): a Next.js 16 App Router app in TypeScript. It renders on the
  server from the REST API, and never reads the database. next-intl owns locale routing
  (`/en/...`, `/ar/...`); the root layout sets `lang` and `dir`. Tailwind CSS v4 logical
  utilities and shadcn/ui components on Radix primitives, generated in RTL mode, provide the
  interface. Playwright drives its end-to-end tests.
- **Database**: PostgreSQL 18, with Alembic owning the schema
  (`docs/development/database.md`).

## Alternatives considered

- **Server-rendered Jinja templates inside the API**: one process fewer, and no Node.js
  toolchain. Rejected because the kit's web variant, frontend standards
  (`.agents/skills/engineering-standards/references/frontend.md`) and CI job are written for
  Next.js with Radix/shadcn, and an RTL-capable accessible component set would have to be
  built by hand.
- **Async SQLAlchemy**: would keep handlers on the event loop, but psycopg's async mode
  fails on Windows' default loop, and the catalogue's queries are short reads that the
  thread pool serves well.
- **A separate MCP service**: the MCP tools read the same catalogue as the REST API;
  mounting it in the same app keeps one deployment and one set of settings. The SDK
  documents this mounting.

## Consequences

- Two toolchains (uv and npm) and two CI jobs (`Python static checks`, `Web static checks`).
- The web app depends on the API's response contract; the API's OpenAPI document is that
  contract.
- The deployment path stays an owner decision (`AGENTS.md`, "Development environment").
  The Dockerfiles and `compose.yaml` in this repository are for building and local running
  only.
