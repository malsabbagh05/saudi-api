# ADR-005: First deployment on Oracle Cloud Always Free in Saudi Arabia

- Status: accepted
- Date: 2026-10-23
- Deciders: @malsabbagh05 (project owner) chose Oracle Cloud Always Free in a Saudi region
  on 2026-10-23, and delegated the remaining choices the same day
- Issue: [#2](https://github.com/malsabbagh05/saudi-api/issues/2)

## Context

The platform has no deployment path, and `AGENTS.md` ("Development environment") requires
one in an ADR before the first deployment. CI builds and checks; it never deploys.

The project owner decided on 2026-10-22 that the first deployment runs in a Saudi region:
several `.gov.sa` hosts refuse connections from outside the Kingdom (ADR-004,
"Consequences"), so reachability checks and agent calls are only complete from inside it.
On 2026-10-23 the owner compared the options below and chose Oracle Cloud Always Free.

| Option, checked 2026-10-22 and 23 | In Saudi Arabia | Cost a month | Database |
| --- | --- | --- | --- |
| Oracle Cloud Always Free, Jeddah or Riyadh | yes | $0 within the Always Free limits | PostgreSQL 18 in a container, run by this project |
| Google Cloud, Dammam (`me-central2`) | yes | paid; Invoiced Billing or CNTXT required ([Dammam access](https://docs.cloud.google.com/docs/dammam-region-access)) | Cloud SQL for PostgreSQL 18 |
| AWS | not until the Saudi region opens, targeted for December 2026 ([AWS](https://aws.amazon.com/blogs/migration-and-modernization/how-to-plan-your-migration-to-the-aws-region-in-saudi-arabia/)); UAE (`me-central-1`) meanwhile | ≈ $36 for one t4g.medium VM, from AWS's price list files | RDS or a container |

Oracle's Always Free resources
([Always Free resources](https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm)):

- Arm Ampere A1 compute equal to 2 OCPUs and 12 GB of memory, 200 GB of block volume
  storage in total, and two AMD micro instances, all in the tenancy's home region, which is
  chosen at sign-up and cannot change. The Free Tier excludes only US Government Cloud
  regions ([Free Tier](https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier.htm)).
- "Idle Always Free compute instances may be reclaimed by Oracle": an instance whose
  95th-percentile CPU, network and (for A1) memory use all stay under 20% for 7 days.

The database holds no state of its own (ADR-002). The curated tables are a projection of
`catalog/` that `saudi-api catalog sync` rebuilds, the discovery job rebuilds the datasets,
and the observations are the latest check, specification and job run, which the jobs
refresh. Rebuilding them is the recovery.

TLS needs a hostname. Let's Encrypt limits certificates per registered domain, which it
finds with the Public Suffix List
([rate limits](https://letsencrypt.org/docs/rate-limits/)). `sslip.io` and `nip.io` are
not on that list, so all their users share one limit; `duckdns.org` is on it, so each
DuckDNS subdomain has its own (checked against
[the list](https://publicsuffix.org/list/public_suffix_list.dat) on 2026-10-23).

## Decision

- **Host**: one `VM.Standard.A1.Flex` instance with 2 OCPUs and 12 GB of memory, running
  Ubuntu 24.04 for Arm, in the tenancy's home region: Riyadh (`me-riyadh-1`), or Jeddah
  (`me-jeddah-1`) when Riyadh has no A1 capacity at sign-up. Its boot volume is 100 GB of
  the 200 GB allowance.
- **Account**: upgraded to Pay As You Go with a budget alert at $1, so a resource outside
  Always Free is noticed at once. Oracle's reclamation notices offer this upgrade to keep an
  idle instance; its documentation does not say so, so the deployment also watches for a
  stopped instance (see `docs/development/deployment.md`).
- **Stack**: `deploy/compose.yaml` runs `db` (`postgres:18`, password authentication, a
  named volume), `release` (`saudi-api migrate`, then `saudi-api catalog sync`), `api`,
  `worker`, `web` and `caddy`. The images build on the VM from a tagged checkout of `main`;
  the base images are multi-architecture, so the same Dockerfiles build for Arm. Only
  `caddy` publishes ports (80 and 443).
- **One hostname**: Caddy serves HTTPS with automatic certificates and sends `/v1/*`,
  `/mcp`, `/llms.txt`, `/healthz`, `/readyz`, `/openapi.json` and `/docs` to the API and
  everything else to the web directory. `SITE_ADDRESS` names the host; until a domain is
  bought it is a free DuckDNS subdomain.
- **Request budget**: `OUTBOUND_PROCESSES=2`, the API and the worker (ADR-004, #6).
- **Secrets**: the database password and the settings live in `/srv/saudi-api/.env.production`
  on the VM, mode 600, never committed (`AGENTS.md`).
- **Egress**: `outbound.py` keeps its rules (ADR-004). The host adds one rule in Docker's
  `DOCKER-USER` chain that drops container traffic to `169.254.0.0/16`, so no container
  reaches the instance metadata service. ADR-004's egress proxy is not needed:
  `outbound.py` pins each connection to the address it checked, which is the rebinding
  case the proxy was for.
- **Backups**: none. A lost database is rebuilt by running the release step and the jobs.
- **Logs**: Docker's `json-file` driver, rotated at 10 MB with 3 files per service.
- **Region label**: `CHECK_REGION` is `oci-me-riyadh-1` or `oci-me-jeddah-1`.
- **Deployment path**: `docs/development/deployment.md`. It is run on the VM from a tagged
  checkout of `main`; CI never deploys.

## Alternatives considered

- **Google Cloud in Dammam**: managed and in the Kingdom, but paid, and it needs Invoiced
  Billing or a purchase through CNTXT.
- **AWS**: no Saudi region until it opens; the UAE region costs about $36 a month for the
  same single-VM design, and `.gov.sa` reachability from it is untested.
- **OCI Database with PostgreSQL**: managed but paid, and it offers PostgreSQL up to 17
  ([release notes](https://docs.oracle.com/en-us/iaas/releasenotes/services/postgresql)),
  while ADR-001 decided 18.
- **A `sslip.io` hostname**: no sign-up, but every user of `sslip.io` shares one
  certificate limit.

## Consequences

- One VM: a reboot or an upgrade is a short outage, and a lost instance is rebuilt from the
  deployment document. The project accepts this for a free first deployment.
- If Oracle reclaims the instance, or A1 capacity is unavailable, a later ADR moves the
  deployment; the stack and the document carry over to any Ubuntu host with Docker.
- Moving to a bought domain changes `SITE_ADDRESS` and the public URLs in the settings,
  and rebuilds the web image.
- The Google Cloud design this record first proposed (2026-10-22) is not pursued.
