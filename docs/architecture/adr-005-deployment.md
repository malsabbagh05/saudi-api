# ADR-005: First deployment on Google Cloud in Dammam

- Status: proposed
- Date: 2026-10-22
- Deciders: @malsabbagh05 (project owner); proposed, not yet accepted
- Issue: [#2](https://github.com/malsabbagh05/saudi-api/issues/2)

## Context

The platform has no deployment path, and `AGENTS.md` ("Development environment") requires
one in an ADR before the first deployment. CI builds and checks; it never deploys. The
Dockerfiles and `compose.yaml` are for building and local running only (ADR-001).

The project owner decided on 2026-10-22 that the first deployment runs in a Saudi cloud
region. Several `.gov.sa` hosts refuse connections from outside the Kingdom (ADR-004,
"Consequences"), so reachability checks and agent calls are only complete from inside it.

The deployment has to keep these rules from earlier records:

- ADR-002: each release runs `alembic upgrade head` and then `saudi-api catalog sync`
  before traffic; readiness fails while the projection is stale.
- ADR-004: provider traffic should leave through an egress path that denies private
  ranges; the per-host request budget is per process, so the deployment states how many
  processes call providers.
- `AGENTS.md`: integrations never use the host's ambient identity. The project's own
  infrastructure (its database and secret store) keeps its deployment identity.

Saudi regions with a managed PostgreSQL service, checked on 2026-10-22:

| Provider | Saudi region | Managed PostgreSQL | Source |
| --- | --- | --- | --- |
| Google Cloud | `me-central2` (Dammam), live since 2023 | Cloud SQL lists `me-central2`; PostgreSQL 18 is generally available in Cloud SQL since 2025-11-20 | [Google, 2023-11-15](https://www.googlecloudpresscorner.com/2023-11-15-Google-Cloud-Expands-Regional-Presence-with-Opening-of-Dammam-Cloud-Region-Forecast-to-Boost-Economy-by-USD-109-Billion-by-2030), [Cloud Run locations](https://docs.cloud.google.com/run/docs/locations), [Cloud SQL regions](https://docs.cloud.google.com/sql/docs/postgres/region-availability-overview), [Cloud SQL release notes](https://docs.cloud.google.com/sql/docs/postgres/release-notes) |
| Oracle Cloud | `me-jeddah-1`, `me-riyadh-1` | OCI Database with PostgreSQL supports up to 17 (added 2026-04-29); Jeddah allows two database systems per tenancy | [OCI PostgreSQL release notes](https://docs.oracle.com/en-us/iaas/releasenotes/services/postgresql), [known issues](https://docs.oracle.com/en-us/iaas/Content/postgresql/known-issues.htm) |
| Microsoft Azure | Saudi Arabia East, announced for November 2026 | not live | [Microsoft, 2026-08](https://news.microsoft.com/source/emea/2026/08/microsoft-announces-saudi-arabia-east-datacenter-region-will-be-available-in-november-2026/) |
| AWS | announced for December 2026 | not live | [Amazon](https://www.aboutamazon.com/news/aws/aws-cloud-region-saudi-arabia) |

Google Cloud's Dammam region has an access condition: "If you have a KSA billing address,
you are required to purchase Google Cloud services ... through CNTXT", and a customer
billed outside the Kingdom needs Invoiced Billing to reach the region
([Dammam region access](https://docs.cloud.google.com/docs/dammam-region-access), updated
2026-10-20).

## Decision

- **Provider and region**: Google Cloud, `me-central2` (Dammam). The billing account is
  bought through CNTXT when the billing address is in the Kingdom, and set up for
  Invoiced Billing otherwise.
- **Images**: the repository's `Dockerfile` and `web/Dockerfile`, built from a tagged
  revision of `main` and pushed to Artifact Registry in `me-central2`.
- **API and web**: two Cloud Run services, `api` (`saudi-api serve`) and `web` (the
  Next.js standalone server). The API runs at most 2 instances and the web at most 4.
- **Release**: a Cloud Run job, `release`, runs `saudi-api migrate` and then
  `saudi-api catalog sync`. A deployment creates the new API revision without traffic,
  runs `release`, and moves traffic only after the new revision's readiness probe passes.
- **Scheduled jobs**: Cloud Scheduler starts three Cloud Run jobs, `discover`, `check` and
  `refresh-specs`, each running `saudi-api jobs run <job>` on the intervals of the
  settings. ADR-004 already allows this model, and its advisory lock keeps one run per
  job. The long-running `saudi-api worker` stays for local and self-hosted use.
- **Request budget across processes**: at most 2 API processes and 3 job processes call
  providers at once. Before the first deployment, the per-host budget either divides each
  catalogue budget by that count (a setting) or moves to one shared authority in
  PostgreSQL. That change has its own pull request.
- **Database**: Cloud SQL for PostgreSQL 18, Enterprise edition, in `me-central2`, on a
  private IP only, with automated daily backups and point-in-time recovery. Cloud SQL is
  the one authority for the database state (ADR-002).
- **Egress**: Cloud Run sends all traffic through Direct VPC egress. VPC firewall egress
  rules deny `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`, `100.64.0.0/10` and
  `169.254.0.0/16`, with a higher-priority allow for the Cloud SQL private range. Cloud NAT
  with a reserved static address carries the provider traffic, so providers see one
  address. `outbound.py` keeps its own checks (ADR-004).
- **Secrets and identity**: Secret Manager holds the database password. Each service and
  job runs as its own service account: `api` and the jobs may read that secret and connect
  to Cloud SQL; `web` has no role. No provider credential exists to store (ADR-004).
- **Public entry**: a global external Application Load Balancer with serverless network
  endpoint groups and Google-managed certificates serves the web, `/v1`, `/llms.txt` and
  `/mcp`. The domain is the project owner's decision; `PUBLIC_BASE_URL`, `WEB_BASE_URL`
  and `MCP_ALLOWED_HOSTS` follow it (`docs/development/configuration.md`).
- **Logs**: Cloud Logging, with the log bucket located in `me-central2` and the default
  30-day retention. The application does not log client addresses (`cli.py` turns off
  uvicorn's access log), but Cloud Run and the load balancer write request logs that
  include them, so those logs stay in the region.
- **Deployment path**: `docs/development/deployment.md` records the commands. The project
  owner runs them from a clean, tagged checkout of `main`. CI never deploys.
- **Region label**: `CHECK_REGION=gcp-me-central2`, so each reachability check shows where
  it ran from.

## Alternatives considered

- **Oracle Cloud in Riyadh or Jeddah**: live in the Kingdom, but its managed PostgreSQL
  stops at 17 while ADR-001 decided 18, and Jeddah allows two database systems per
  tenancy.
- **Azure Saudi Arabia East or the AWS Saudi region**: neither is live on 2026-10-22.
  Revisit after launch if their managed PostgreSQL offers 18 in the region.
- **One virtual machine running `compose.yaml` in a Saudi region**: the fewest moving
  parts, but this project would then own operating system patching, TLS renewal, backups
  and a database server, and `compose.yaml` is not reviewed as a production path
  (ADR-001).
- **A region outside the Kingdom**: providers that refuse foreign networks would show as
  unreachable, and agents could not call them.

## Consequences

- Before acceptance, the project owner confirms in the console or with `gcloud` that a
  PostgreSQL 18 instance can be created in `me-central2`. The release notes list
  PostgreSQL 18 regions without naming Dammam.
- The procurement path (CNTXT or Invoiced Billing) comes before any resource exists.
- Before the first deployment, the request budget holds across processes (see
  Decision), `docs/development/deployment.md` exists, and the public domain is chosen.
- Cloud Run in Dammam is billed at Tier 2 prices.
- A later change of provider or region supersedes this record.
