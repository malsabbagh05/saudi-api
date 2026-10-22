# Engineering guide

How work reaches this repository. `AGENTS.md` holds the rules every contributor and
agent follows, and `.agents/skills/engineering-workflow/SKILL.md` the route each
change takes.

## Work policy

- Use `development` as the base branch unless a maintainer explicitly chooses a
  different base.
- Keep each branch scoped to one issue or one tightly related implementation slice.
- Planning and issue authority stay in the issue tracker; shipped implementation
  belongs in this repository.
- Do not merge report-only, proof-only, fixture-only, or documentation-only artifacts
  as substitutes for production code when the issue owns runtime behavior.
- Do not commit secrets, local `.env` files, service-account JSON, tokens, or
  machine-specific hook paths.
- Treat pull-request merge as code integration, not product readiness. Readiness
  requires the issue's concrete validation evidence.

## Catalogue contributions

To add or correct an API, change `catalog/` in a pull request. The
[catalogue reference](docs/development/catalogue.md) explains every field. Each entry cites
the provider's own documentation or a live request, with the date it was checked, and its
text exists in Arabic and English. Run `make catalog-check` before you push; CI runs it too.

## Development setup

Prerequisites: Python at the version in `.python-version`, `uv`, Node.js at the version
in `web/.nvmrc`, and Docker for the test database and local service stacks. `make help`
lists the local workflow (database, migrations, catalogue sync, API, worker, web).

```bash
uv sync --frozen
uvx pre-commit install
uvx pre-commit run --all-files
```

The pre-commit hook is required for local commits; a checkout does not install it
automatically. It runs `ruff check --fix` and `ruff format` with the Ruff version
`uv.lock` pins. If it changes files, include them in the next commit. Do not bypass
commit hooks unless a maintainer approves it for a named emergency.

## Formatting, linting and type checking

Configuration lives in `pyproject.toml`; versions resolve through `uv.lock`. See
[Python typing](docs/development/python-typing.md) for editor setup, rule coverage
and suppression rules.

```bash
make check
```

For the web app, `Web static checks` runs
([GitHub Actions](docs/development/github-actions.md)):

```bash
(cd web && npm ci && npm run lint && npm run build)
```

The secret scan in `Python static checks` reads every file:

```bash
trivy fs --scanners secret --exit-code 1 .
```

Run it on a clean checkout: it also reads ignored files such as `.env.development`.

## Pull-request expectations

Before opening or updating a pull request, run the smallest validation that covers
the changed code, and report the exact commands and results in the body
([`.agents/skills/pr-readiness/SKILL.md`](.agents/skills/pr-readiness/SKILL.md)).
List the tests that prove the change in the body's `tests` block
([tests/README.md](tests/README.md)). Formatting, linting and report-only output do
not replace runtime tests when the change affects production behavior.

Pull requests target `development`. The linked issue remains the source for
milestone, Project status, acceptance gate and production evidence.
