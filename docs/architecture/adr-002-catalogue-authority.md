# ADR-002: Catalogue authority and its database projection

- Status: accepted
- Date: 2026-10-22
- Deciders: @malsabbagh05 (project owner), accepted 2026-10-22
- Issue: none yet; the goal was set in the session of 2026-10-22

## Context

The platform holds three kinds of catalogue state:

1. **Curated entries**: providers and their APIs, with documentation links, base URLs,
   access and authentication requirements, endpoints, usage policy and verification
   evidence. A person checks each fact against the provider's own documentation or a live
   request. These are the facts a developer or an agent acts on, so each change needs
   review.
2. **Discovered datasets**: records that a discovery job reads from a provider's own
   machine-readable index, such as the 278 bilingual cubes that
   `https://api.datasaudi.sa/tesseract/cubes` lists. The upstream index is their source,
   and the job refreshes them.
3. **Observations**: the latest reachability check of each API, the latest snapshot of a
   provider-published OpenAPI document, and the latest run of each job.

Open API directories keep curated entries as reviewed files in a repository: APIs.guru
keeps one definition file per API in git
([APIs-guru/openapi-directory](https://github.com/APIs-guru/openapi-directory)), and
Backstage reads `catalog-info.yaml` files from repositories
([Backstage descriptor format](https://backstage.io/docs/features/software-catalog/descriptor-format)).
A pull request then gives every catalogue change a reviewer, a history and an author.

The REST API, the MCP server and the web directory need one query path that searches
curated APIs and discovered datasets together, in Arabic and English (ADR-003).

## Decision

- **Curated entries**: the YAML files under `catalog/` in this repository are the one
  authority. `catalog/providers/<slug>.yaml` holds a provider, and `catalog/apis/<slug>.yaml`
  holds an API. The typed schema in `src/saudi_api/catalog/schema.py` validates them, and
  `saudi-api catalog check` runs that validation. A change lands only through a reviewed
  pull request.
- **The projection**: PostgreSQL holds a read model of the curated entries, so that they
  can be searched together with datasets. `saudi-api catalog sync` writes it in one
  transaction: it upserts every entry, deletes rows whose entry was removed, and records
  the catalogue's content digest in `catalog_state`. A sync of an unchanged digest writes
  nothing. Nothing else writes the curated tables. The readiness probe fails while the
  database digest differs from the digest of the catalogue files the process was built
  with, so a stale projection fails closed.
- **Discovered datasets**: the provider's index is their source; the `datasets` table is
  the one store, written only by the discovery job of that source. A run replaces that
  source's datasets: it upserts what the index lists and deletes what it no longer lists,
  with no grace period (`AGENTS.md`, "Architecture").
- **Observations**: `api_checks`, `api_specs` and `job_runs` hold only the latest value per
  API or job, which is all the features show. Their writers are the jobs of ADR-004.

## Alternatives considered

- **The database as the authority, edited through an admin API**: an admin API adds
  authentication, an authorization model and an audit trail, and contributors outside the
  project could not propose a change. Review in pull requests already provides all three.
- **Loading the YAML files into memory in each process, with no projection**: there would
  be two search implementations, one in memory for curated APIs and one in SQL for datasets,
  and their ranking could not be merged.

## Consequences

- Each deployment runs `alembic upgrade head` and then `saudi-api catalog sync` before
  traffic, and readiness enforces that order.
- A catalogue fix ships like a code change: through a pull request and a release.
- Removing an entry removes its rows, observations and datasets in the next sync, through
  foreign keys with `ON DELETE CASCADE`.
