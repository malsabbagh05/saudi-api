# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Developers first (confirmed 2026-10-22): engineers in and outside Saudi Arabia who need to
find a Saudi API, judge whether they can use it (access level, authentication, pricing,
terms), and integrate it quickly with working examples. They read in Arabic or English and
switch between them. AI agents (Claude, ChatGPT, Cursor and others) are the second audience;
they use the MCP server and the REST API, not the web pages, but developers come to the web
directory to learn how to connect them.

## Product Purpose

An open, verified, bilingual catalogue of Saudi APIs: government services, open data,
statistics, finance and payments, tax, commerce, transport, health and more. Each entry
states what the API does, who may use it and how to get access, its base URLs, endpoints and
ready-to-run examples, and the evidence behind every fact. Success is a developer going from
a question ("is there an API for Saudi national addresses?") to a first working request
without leaving the page, and an agent doing the same through MCP.

## Positioning

Every curated fact is checked at the provider's own source and dated, with the evidence
linked, and the catalogue says plainly when a provider could not be reached or does not
publish a detail. Arabic and English are equal. Statistical datasets (GASTAT, SAMA,
ministries) are discovered automatically from DataSaudi and searchable beside the APIs. The
same catalogue is an MCP server that can call keyless, policy-permitted endpoints for agents.

## Operating Context

Developers arrive from search engines, from links shared in chats, or from an AI assistant.
They scan, filter by sector, access level and authentication, compare a few entries, copy a
curl or code example, and follow the link to the provider's portal to sign up. Code,
URLs and JSON stay left-to-right inside Arabic pages.

## Capabilities and Constraints

- Web directory (Next.js), REST API under /v1, MCP at /mcp, llms.txt.
- Catalogue: 21 APIs from 17 providers in 16 sectors, and 252 discovered datasets
  (2026-10-22); grows by reviewed pull requests to catalog/.
- Reachability checks show whether each API answered, and from where.
- The platform never holds provider credentials; agents invoke only keyless APIs whose
  terms and robots.txt allow it.
- Open decisions: project name and logo, licence of the code and of the catalogue content,
  deployment target and public URLs.

## Brand Commitments

No brand yet; start fresh (confirmed 2026-10-22). Working name: "Saudi API Catalogue" /
"دليل الواجهات البرمجية السعودية". The site is independent: it must not imitate a
government portal or suggest official endorsement, and it names providers only as the
sources of their own APIs.

## Evidence on Hand

The catalogue itself (catalog/), live reachability results, discovered datasets with their
publishers, and each entry's dated evidence links. There are no testimonials, user counts,
partner logos or endorsements, and none may be invented.

## Product Principles

1. Evidence over claims: show the source and date of every fact; say what is unknown.
2. Both languages are first-class: same content, same quality, correct direction.
3. From question to first request on one page: access, auth and a runnable example together.
4. Respect providers: link to their portals and terms, follow their usage policies.
5. Agents and people read the same catalogue.

## Accessibility & Inclusion

WCAG 2.2 AA (confirmed 2026-10-22), in both Arabic (RTL) and English (LTR): keyboard
operation, visible focus, contrast, screen-reader labels, reduced motion.
