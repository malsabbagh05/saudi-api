# Security policy

## Reporting a vulnerability

Report vulnerabilities privately through GitHub's private vulnerability reporting
("Report a vulnerability" on the repository's Security tab). Do not open a public issue,
pull request or discussion for a vulnerability.

Include what an attacker can do, the affected component (REST API, MCP server, worker,
web directory or catalogue), the steps to reproduce, and the version or commit. You will
get an acknowledgement, and a fix or a decision with its reasons, through the same advisory.

## Scope

In scope: the code in this repository and the containers it builds, including
server-side request forgery through provider requests or `call_endpoint`, injection,
cross-site scripting in the web directory, MCP transport and Host or Origin checks,
leakage of request data in logs, and catalogue entries that point agents at unsafe or
unintended endpoints.

Out of scope: the providers' own APIs and portals listed in the catalogue (report those to
the provider), denial of service by volume, and findings that need a compromised host.

## Design commitments

- The platform holds no provider credentials and never sends one to a provider.
- Provider requests go only to HTTPS hosts a reviewed catalogue entry lists, refuse private,
  loopback and link-local addresses, follow robots.txt, and stay within per-provider budgets
  ([ADR-004](docs/architecture/adr-004-outbound-requests-and-jobs.md)).
- The MCP endpoint answers only the configured hostnames and origins.
- Errors cross the API and MCP boundaries as bounded codes; logs never carry credentials,
  provider bodies or search terms.
