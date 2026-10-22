# Catalogue files

`catalog/` is the authority for every curated fact
([ADR-002](../architecture/adr-002-catalogue-authority.md)). The typed schema in
`src/saudi_api/catalog/schema.py` owns the shape; this page explains each field. How an
entry is researched, what counts as evidence and when agents may invoke an API belong to
the catalogue-curation skill (`.agents/skills/catalogue-curation/SKILL.md`).

```text
catalog/
  sectors.yaml               the sectors, in display order
  providers/<slug>.yaml      one provider per file
  apis/<slug>.yaml           one API per file
```

A slug is lowercase letters, digits and single hyphens, and equals the file name. Every
human-readable text is a pair `{en: ..., ar: ...}`; the Arabic half must contain Arabic.

## Provider

| Field | Meaning |
| --- | --- |
| `slug`, `name`, `description` | Identity and a short description, in both languages. |
| `kind` | `government`, `regulator`, `state_owned` or `private`. |
| `website_url` | The provider's own site. |

## API

| Field | Meaning |
| --- | --- |
| `slug`, `provider` | Identity; `provider` names a file in `providers/`. |
| `name`, `summary`, `description` | Bilingual name, one-sentence summary and description, in our own words. |
| `sectors`, `tags` | Sector slugs from `sectors.yaml`, and free search keywords. |
| `status`, `status_note` | `active`, `beta` or `deprecated`; a deprecated API needs a note. |
| `documentation_url` | The provider's documentation. Required. |
| `openapi_url` | A provider-published OpenAPI or Swagger document; the `refresh-specs` job keeps its operation list. |
| `signup_url`, `terms_url` | Where to get access, and the terms of use. |
| `base_urls` | `{url, environment}` with `production` or `sandbox`. |
| `formats` | `json`, `xml`, `csv`, `xlsx`, `geojson`, `pdf`. |
| `access.level` | `open`, `registration`, `approval`, `contract` or `restricted`. |
| `access.auth` | `none`, `undisclosed`, `api_key`, `bearer`, `oauth2`, `mtls`, `basic`, `jwt`. `none` and `undisclosed` stand alone. |
| `access.api_key` | `{in: header|query, name}`; required exactly when `auth` has `api_key`. |
| `access.pricing`, `access.notes` | `free`, `freemium`, `paid` or `unknown`; bilingual notes. |
| `usage.agent_invocation` | `allowed` or `not_allowed` (default). `allowed` needs `auth: [none]`, `GET` endpoints only, no header parameters, `max_requests_per_minute` and `policy_evidence`. |
| `usage.max_requests_per_minute` | The per-host budget for agent calls and jobs. |
| `usage.policy_evidence`, `usage.notes` | Pages that allow automated use, and bilingual notes. |
| `check.url` | The page the reachability check requests; defaults to `documentation_url`. |
| `discovery` | `{kind: tesseract_cubes, base_url}`: discover datasets from that index. `base_url` must be one of `base_urls`. |
| `endpoints` | `{id, method, path, summary, parameters, response_example}`. Path parameters in `{braces}` must be declared and required; a required parameter needs an `example`. |
| `verification` | `{checked_on, method: live_request|official_documentation, evidence: [urls]}`. |

Examples in curl, Python and JavaScript are generated from the endpoints
(`src/saudi_api/examples.py`); entries never store them.

## Commands

```bash
uv run --frozen saudi-api catalog check   # validate every file (CI does too)
uv run --frozen saudi-api catalog sync    # write the database projection
```
