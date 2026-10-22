# AGENTS.md

Start every task with
[`.agents/skills/engineering-workflow/SKILL.md`](.agents/skills/engineering-workflow/SKILL.md).
It is the route from an issue to a merged and accepted change, and names the file
that owns each step. The skills in `.agents/skills/` and the workflows in
`.claude/workflows/` are ignored by git: they exist only in the main checkout, not in
task worktrees or on GitHub, so read and run them from the main checkout.

## Repository authority

- GitHub Issues own issue-backed scope, milestone, Project state, and delivery
  history.
- This file holds only the rules no other file owns. When it and a linked file
  disagree, the linked file owns the detail; correct this file.

## Product

saudi-api is an open catalogue of Saudi APIs, in Arabic and English, for developers and
AI agents. Its parts, and the ADR that decided each:

- `catalog/`: the curated provider and API entries, the authority for every curated
  fact ([ADR-002](docs/architecture/adr-002-catalogue-authority.md)).
- `src/saudi_api/`: the FastAPI service (REST API under `/v1`, MCP at `/mcp`), the
  worker that runs discovery, reachability checks and specification refresh, and the
  `saudi-api` CLI ([ADR-001](docs/architecture/adr-001-platform-stack.md),
  [ADR-004](docs/architecture/adr-004-outbound-requests-and-jobs.md)).
- `web/`: the Next.js directory, which reads only the REST API.
- PostgreSQL: the projection of the catalogue, discovered datasets, observations and
  bilingual search ([ADR-003](docs/architecture/adr-003-bilingual-search.md)).

## How to work

- Start every design, code change and review from the problem, not from the
  mechanism that was asked for. Find the documented practice for that problem: the
  vendor or framework documentation at the pinned version, the standard, or an
  existing use in `src`. Follow it, or state `deviates: <why the practice fails
  here>`. A mechanism of our own needs that named reason.
- When an issue, an earlier decision or a prompt asks for something that differs
  from the practice, do the correct thing in its place. Before you build it, post on
  the issue under `Common practice against the issue`: the quoted line, the practice
  with its source, and what you do in its place. Stop and ask in place of building
  only when the correction changes who may read or do something and no owner
  decision settles it.
  - This covers how we build, never a business requirement from the product owner
    (`@malsabbagh05`). Build their requirement as written; only the project owner
    (also `@malsabbagh05`) overrides it, and a conflict with access, security or
    architecture goes to the project owner first, not to the issue.
- Use `.agents/skills/engineering-standards/SKILL.md` for every implementation and
  review. It owns how to research, decide at the owner, and verify.
- Use `.agents/skills/git-standards/SKILL.md` for every repository change. It owns
  branches, commits, the pull-request body (`Direction:` and `Common practice:`),
  promotion from `development` to `staging` and `main`, and merging.
- Use `.agents/skills/pr-readiness/SKILL.md` before you open or update a pull
  request, and before you quote a number in one.
- Use `.agents/skills/catalogue-curation/SKILL.md` for every change under `catalog/`.
  It owns what counts as evidence for a catalogue fact and when agents may invoke an
  API.
- For interface design, use the design skills in `.claude/skills/` (`impeccable`,
  `design-taste-frontend`) with engineering-standards' frontend and bilingual
  references, which own behavior, accessibility and direction.

## Architecture

Record architecture decisions in `docs/architecture/` as ADRs
([template](docs/architecture/adr-000-template.md)). These rules hold until an ADR
replaces one:

- Each kind of durable state has one authority. Name that authority in an ADR
  before any second store holds the same state. No competing persistence, queue,
  metadata, configuration or certification authority.
- A table, field, or stored object exists only for a named current need. Keep only
  what a feature or a running operation needs, for as long as it needs it.
- Once data is authorized and marked for deletion, delete it without an added
  grace period or speculative recovery hold, unless a written requirement sets one.
- A message queue is transient transport, never a durable work authority.
- Keep provider, model, object-storage, search-index and other network I/O outside
  database transactions and row-lock windows.
- Use explicit typed contracts and state. Validate external data at the transport
  boundary.
- An integration reaches its provider only with the credentials its own tenant or
  account configured. Never fall back to the host's ambient identity (cloud metadata
  endpoints, environment variables, profile or token files on the host, a managed
  identity); refuse when it has none. The project's own infrastructure, such as its
  secret store, keeps its deployment identity.
- API, worker, CLI, and UI state derive from the same authority.
- Durable transitions are explicit and idempotent. Stale or ambiguous authority
  fails closed.
- Preserve tenant, actor, request, run, and trace identity across the full data
  path.
- Every provider request goes through `src/saudi_api/outbound.py`, which enforces
  HTTPS to catalogued hosts, public addresses only, robots rules, the per-host budget
  and the response cap (ADR-004). No other module opens a connection to a provider,
  and the platform never sends a credential to one.
- Text a person or an agent reads exists in Arabic and English, and every page works
  right-to-left (`.agents/skills/engineering-standards/references/bilingual.md`).
  Errors cross the API and MCP boundaries as bounded codes, never as provider text.

## Validation

- Select and list tests as `tests/README.md` says. The `Listed tests` CI job runs
  the listed node IDs (`docs/development/github-actions.md`), so do not also run
  them locally. Run locally only the tests that need a service CI does not provide,
  and record their results in the pull-request body.
- Before every push, run Ruff format, Ruff check and ty on the changed Python files
  (`docs/development/python-typing.md`). CI collects tests but does not import
  every module, so byte-compile and import the touched modules and the entry points
  that load them.
- Migration changes keep one Alembic head and apply safely to populated data.
  Number revisions and drop schema as `docs/development/database.md` describes.
- Run `uv run --frozen saudi-api catalog check` after any change under `catalog/` or to
  the catalogue schema.
- For a change under `web/`, run `npm run lint` and `npm run build` there (the
  `Web static checks` job), and the affected Playwright tests against the production
  build and the real API (`docs/development/web.md`).
- Runtime and provider claims require evidence from the real API or runtime.
- No proof-only tooling or certification machinery without an explicit external
  requirement.

## SQL work

- Check SQL with PostgreSQL's own tools, not by reading the code. A change that adds
  or changes a query, an index, or a worker's claim or poll statement records in its
  pull request the plan of the statement as the code sends it (`EXPLAIN (ANALYZE,
  BUFFERS)` on representative data). For a statement that already runs, it also
  records the calls, time and pages per call from `pg_stat_statements`, before and
  after.
- Start a database performance diagnosis from `pg_stat_statements` and the
  `auto_explain` plans in the PostgreSQL log, before any change.
- A statement that runs on every poll or request never reads a whole table. State a
  partial index's predicate in the query as the index states it, and prove with a
  plan that the index is used.
- `docs/development/database.md` ("SQL performance") has the commands.

## Development environment

- Each environment has one configuration file: `.env.development` for local
  development, and one file per shared environment. Never commit them, never copy
  them into task worktrees, and never use one environment's file for another.
  git-standards ("Worktree environment") owns how task worktrees reach them.
- CI builds and checks; it never deploys. Deploy only through the reviewed
  deployment path. There is none yet: `@malsabbagh05` sets it, in an ADR, before
  the first deployment.
- Never run `docker compose down -v`, flush a shared search index, drop shared
  database state, clear shared object storage, stop Docker globally, or prune
  unfiltered resources.
