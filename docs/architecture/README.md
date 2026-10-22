# Architecture decisions

Each architecture decision is recorded as an ADR (architecture decision record):
a short file that states the context, the decision and its consequences
([Michael Nygard, "Documenting Architecture Decisions"](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions)).
The architecture rules in `AGENTS.md` hold until an ADR here replaces one.

- Copy [the template](./adr-000-template.md) to `adr-<NNN>-<slug>.md`, numbered one
  more than the newest record.
- An ADR is decided through a pull request that the project owner approves. Once
  accepted, it is not rewritten: a later ADR supersedes it, and both say so in their
  status lines.
- Write an ADR before a change adds a second authority for any kind of state, a new
  service or store, or a new trust boundary.

## Records

- [ADR-001: Platform stack and process layout](./adr-001-platform-stack.md)
- [ADR-002: Catalogue authority and its database projection](./adr-002-catalogue-authority.md)
- [ADR-003: Bilingual search in PostgreSQL](./adr-003-bilingual-search.md)
- [ADR-004: Outbound requests, provider usage policy and scheduled jobs](./adr-004-outbound-requests-and-jobs.md)
