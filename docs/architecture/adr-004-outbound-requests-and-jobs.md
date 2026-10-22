# ADR-004: Outbound requests, provider usage policy and scheduled jobs

- Status: accepted
- Date: 2026-10-22
- Deciders: @malsabbagh05 (project owner), accepted 2026-10-22
- Issue: none yet; the goal was set in the session of 2026-10-22

## Context

The platform calls providers in four places:

1. **Discovery** reads a provider's machine-readable index of datasets (ADR-002).
2. **Reachability checks** request each API's check URL to show whether it answers.
3. **Specification refresh** downloads a provider-published OpenAPI document.
4. **Invocation**: the MCP tool `call_endpoint` lets an agent call an endpoint the catalogue
   marks as invocable, and returns the provider's response.

Each call reaches a third party on behalf of the platform, and the fourth on behalf of an
anonymous agent. The risks:

- **Server-side request forgery**: a URL that resolves to a private, loopback, link-local or
  metadata address
  ([MCP security best practices](https://modelcontextprotocol.io/specification/latest/basic/security_best_practices),
  [OWASP SSRF Prevention](https://cheatsheetseries.owasp.org/cheatsheets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet.html)).
- **Provider usage policy**: robots rules
  ([RFC 9309](https://www.rfc-editor.org/rfc/rfc9309.html)), terms of use, and request
  rates that a provider did not agree to.
- **Credentials**: the platform holds no provider credential, and must never borrow one
  from the host (`AGENTS.md`, "Architecture").
- **Unbounded responses**: a large provider response that exhausts memory or an agent's
  context. Claude Code warns when an MCP tool output exceeds 10,000 tokens
  ([Claude Code MCP](https://code.claude.com/docs/en/mcp)).

## Decision

- **One owner for outbound HTTP**: `src/saudi_api/outbound.py`. Every provider request goes
  through it, and it enforces:
  - HTTPS only, to a host the catalogue lists for that API, on the default port;
  - every resolved address must be global (`ipaddress` `is_global`), checked before the
    request;
  - no automatic redirects: each hop is checked against the same rules, at most 3 hops,
    the limit this stack already applies to remote fetches (`images.maximumRedirects` in
    Next.js 16);
  - a connect timeout and a total deadline, and a response size cap read in chunks;
  - an identifying `User-Agent` that names the project and its repository URL;
  - a per-host request budget, so no process sends more than the catalogue entry's
    `usage.max_requests_per_minute` to one provider.
- **robots.txt**: discovery, specification refresh and invocation read the host's
  robots.txt first and follow it as RFC 9309 says: a 4xx answer allows everything, a 5xx
  or unreachable answer disallows everything, and an answer is cached for at most 24
  hours (section 2.4). Invocation follows it too, because an agent's request is automated
  even when a person asked for it: the Royal Commission for Riyadh City publishes a
  keyless API and disallows `/api/` for every agent but Googlebot (fetched 2026-10-22).
  Reachability checks request one documented page per API per interval; they are not
  crawling.
- **Invocation is opt-in per API**: an endpoint is invocable only when its API entry sets
  `usage.agent_invocation: allowed`, the API needs no credentials (`access.auth: [none]`),
  the endpoint is a `GET`, and the entry cites the terms or the evidence that allows
  automated access. Arguments are validated against the endpoint's declared parameters; an
  undeclared parameter is refused. The tool output is capped at 30,000 characters
  (the 10,000-token warning threshold × a conservative 3 characters per token for mixed
  Arabic and English text), and a truncated result says so.
- **No credentials**: the platform never sends a credential to a provider. Catalogue entries
  describe how a developer obtains their own.
- **Scheduled jobs**: the worker process runs `discover`, `check` and `refresh-specs` on the
  intervals in the settings. Each run takes a PostgreSQL session-level advisory lock named
  by its job, so two workers never run the same job at once, and it records its outcome in
  `job_runs`. Provider I/O happens outside any transaction; each write is a short
  transaction after the I/O finishes.

## Alternatives considered

- **Platform-scheduled one-shot jobs (cron, Kubernetes CronJob)**: the deployment platform is
  not chosen yet. The `saudi-api jobs run <job>` command serves that model unchanged, and
  the advisory lock makes both safe together.
- **A message queue for jobs**: the jobs are periodic and idempotent; a queue would be a
  second scheduler with no durable work to carry (`AGENTS.md`: a queue is transient
  transport).
- **Proxying any URL an agent supplies**: the SSRF and usage-policy risks above, with no
  reviewer for which provider is called.

## Consequences

- Hosts that block the platform's network (several `.gov.sa` hosts refused or timed out
  from a non-Saudi network on 2026-10-22) show as unreachable in checks. The check result
  records where it ran from, so a reader can tell a block from an outage.
- A deployment SHOULD also route provider traffic through an egress proxy that denies
  private ranges, which the MCP guidance recommends against DNS rebinding between check and
  use. That is part of the deployment ADR.
- The per-host budget is per process. The deployment ADR states how many processes run, and
  each entry's budget divides by that number.
