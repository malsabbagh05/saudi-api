# ADR-003: Bilingual search in PostgreSQL

- Status: accepted
- Date: 2026-10-22
- Deciders: @malsabbagh05 (project owner), accepted 2026-10-22
- Issue: none yet; the goal was set in the session of 2026-10-22

## Context

People and agents search the catalogue in Arabic and English, often with partial words,
missing diacritics and different spellings of the same letter (أ, إ, آ, ا; ة and ه; ى and
ي). The catalogue holds hundreds of curated APIs and thousands of discovered datasets, so
size is not the constraint; matching quality and a query that never reads a whole table are
(`AGENTS.md`, "SQL work").

PostgreSQL 18 ships an `arabic` text search configuration (Snowball stemmer). Measured on
`postgres:18` (18.6) on 2026-10-22:

| Expression | Result |
| --- | --- |
| `to_tsvector('arabic', 'البيانات المفتوحة')` | `'بيان':1 'مفتوح':2` |
| `websearch_to_tsquery('arabic', 'بيانات')` | `'يانا'` |
| `to_tsvector('arabic', 'البيانات المفتوحة') @@ websearch_to_tsquery('arabic', 'بيانات')` | `false` |
| `websearch_to_tsquery('arabic', 'أسعار')` | `'اسعار'` (hamza normalized) |

The stemmer treats the leading ب of بيانات as a preposition, so a stemmed match alone misses
an obvious query. Trigram word similarity
([pg_trgm](https://www.postgresql.org/docs/18/pgtrgm.html)) matches a query against any
part of the text and tolerates spelling variants, and a GIN trigram index serves its `<%`
operator.

## Decision

- Each searchable table (`apis`, `datasets`) has two stored generated columns:
  - `search_vector`: the weighted union of `to_tsvector('english', …)`,
    `to_tsvector('arabic', …)` and `to_tsvector('simple', …)` over its names (weight A),
    tags (B) and descriptions (C), with a GIN index.
  - `search_text`: the names and tags folded by the SQL function `catalog_fold(text)`, which
    lowercases, removes Arabic diacritics and tatweel, and maps the letter variants above to
    one form, with a GIN `gin_trgm_ops` index.
- A query matches when `search_vector @@ <the English, Arabic and simple tsqueries combined
  with OR>` or when `catalog_fold(<query>) <% search_text`. Results rank by
  `ts_rank_cd(search_vector, <tsquery>) + word_similarity(catalog_fold(<query>), search_text)`.
  The trigram threshold is pg_trgm's default `word_similarity_threshold` (0.6).
- One owner: `src/saudi_api/search.py` builds every search statement. The REST API, the MCP
  tools and the web directory (through the REST API) all use it.

## Alternatives considered

- **A search engine (Meilisearch, OpenSearch)**: better typo tolerance at large scale, but a
  second store of the catalogue with its own sync, deployment and failure mode, for a corpus
  that PostgreSQL indexes in milliseconds. Revisit when a measurement shows PostgreSQL
  misses a latency target.
- **The `arabic` configuration alone**: the measurement above shows it misses common
  queries.
- **Trigram similarity alone**: no stemming, so English plurals and Arabic prefixes rank
  poorly against exact stems.

## Consequences

- The fold function is `IMMUTABLE` so the generated column and the query apply the same
  folding; a change to it is a migration that rewrites the generated columns.
- A ranking change is a tuned rule (pr-readiness rule 15): it ships with measurements on
  the evaluation queries in `tests/integration/search/`.
