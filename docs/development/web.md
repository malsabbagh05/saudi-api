# Web app

The web directory in `web/` is a Next.js 16 App Router app in TypeScript
([ADR-001](../architecture/adr-001-platform-stack.md)). It renders on the server from the
REST API and never reads the database. Its engineering rules are in
`.agents/skills/engineering-standards/references/frontend.md` and `bilingual.md`; its visual
direction is in `.impeccable/surfaces/web-src-app.md` and `DESIGN.md`.

## Layout

| Path | What it owns |
| --- | --- |
| `src/app/[locale]/` | The pages; `[locale]` (`en`, `ar`) is the root segment, so the root layout sets `lang` and `dir`. |
| `src/i18n/` | next-intl routing, the locale-aware `Link`, and the request configuration. |
| `src/proxy.ts` | Locale detection and the redirect from `/` (Next.js 16's `proxy.ts`). |
| `messages/en.json`, `messages/ar.json` | Every UI string, with the same keys. |
| `src/lib/api.ts` | The server-only API client; types come from `src/lib/api-schema.ts`. |
| `src/lib/api-schema.ts` | Generated from `openapi.json` with openapi-typescript. Do not edit. |
| `src/components/` | Site components; `ui/` holds shadcn/ui components added with the CLI (RTL on). |
| `tests/e2e/` | Playwright tests. |

## Commands

```bash
cd web
npm ci
npm run dev            # http://localhost:3000, with the API on API_BASE_URL
npm run lint           # ESLint (warnings fail) and the en/ar message key check
npm run build          # production build; it also type-checks
npm run generate:api   # regenerate src/lib/api-schema.ts from openapi.json
```

After a change to the API's response shapes, regenerate both copies of the contract:
`make web-types`. `tests/integration/api/test_rest_api.py` fails while `web/openapi.json`
differs from the API.

## Rendering and caching

Cache Components and Partial Prerendering are on. The static shell (layout, headings,
forms) is prerendered; every read of catalogue data happens inside `<Suspense>` at request
time, because the catalogue changes with each sync and job run and the build has no API to
call. A page that reads runtime `params` (a slug) reads them inside its `<Suspense>` child.

## End-to-end tests

The Playwright tests run against the production build, the real API and a migrated, synced
database. CI does not run them yet; record the command, the result and the commit in the
pull request.

```bash
make dev-db migrate sync                 # database, schema, catalogue
make serve                               # the API on 127.0.0.1:8000 (another terminal)
cd web && npm run build && npm start     # the web app on 127.0.0.1:3000 (another terminal)
cd web && npx playwright install chromium && npx playwright test
```

`docker compose up --build` runs the same stack in containers. The tests cover both
locales, search, filters, the API page, right-to-left layout with left-to-right code, the
language switch, the localized 404, keyboard skip link, and horizontal overflow at desktop
and phone widths.
