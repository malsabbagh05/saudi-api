# Tests

- The project has no unit-test level: no `tests/unit/` or `web/tests/unit/`. Test
  behavior through its real boundaries.
- Put cross-owner and real database, filesystem, queue, object-store, provider,
  API-composition, and process-boundary tests under
  `tests/integration/<domain>/`.
- Put assembled application and runtime workflows exercised through their real
  entrypoints under `tests/e2e/<domain>/`.
- Put reusable cross-domain test infrastructure under `tests/support/`. Keep
  domain-specific helpers beside their tests and scope fixtures with the nearest
  `conftest.py` ([Test fixtures](../docs/development/test-fixtures.md)).
- Build database rows with shared builders in `tests/support/`: one builder per
  table, which writes a valid row, creates missing parents and takes column
  overrides. A test does not import helpers from another test module; move a helper
  that two test modules need into `tests/support/`. A migration test writes rows at
  an older revision with its own small builders, only for the tables that migration
  changes, because the current models do not match the older schema.
- For PostgreSQL, use `postgres_engine()` or `postgres_migrated_database_url()` from
  `tests/support/postgres.py`. Each clones a head-migrated template, built once per
  set of migration sources, so tests get the triggers, functions, grants and seed
  rows that only migrations install. Do not create or hand-write tables the
  migrations own. Use `postgres_empty_database_url()` only for a test that needs an
  incomplete schema, such as one migration applied to its predecessor's tables
  (`migrate()` applies it).
- `make test-focused` supplies the test PostgreSQL unless `TEST_POSTGRES_DSN` is set.
  It starts the container `saudi-api-test-postgres` once (override with
  `TEST_POSTGRES_CONTAINER`) and reuses it across runs, worktrees and sessions. Every
  test gets its own database, and the migrated template is named by a digest of the
  migration sources, so only the first run after a migration change pays for
  migrating. The container takes its server settings from
  `tests/support/postgres.conf`, the same in CI, and runs with `--shm-size=1g`: with
  Docker's default 64 MiB, PostgreSQL can fail mid-suite with `DiskFull`. An
  existing container keeps the settings it started with; remove it with
  `docker rm -f -v saudi-api-test-postgres` to start clean.
- Code that reads a provider (discovery, reachability checks, specification refresh,
  MCP invocation) is tested through its real HTTP client and `src/saudi_api/outbound.py`
  against a local HTTP server, started by the test, that serves an authentic, minimal
  payload recorded from the provider
  ([Test fixtures](../docs/development/test-fixtures.md): "retain a minimal, authentic
  external payload"). Keep the payload beside its test, trimmed to what the test needs,
  with the command and date of the recording in the test's docstring. A test against
  the live provider runs locally, and the pull request records its command and result.
- The web directory's tests are Playwright tests in `web/tests/e2e/`, run against the
  production build, the real API and a migrated, synced database
  ([Web app](../docs/development/web.md)). CI does not run them yet; the pull request
  records the command, the result and the commit.
- The directory owns the test level. Do not duplicate it with pytest level markers.
- Name test files by behavior. Do not use issue, ticket, milestone, or epic numbers.
- Keep `tests/` itself free of test modules.

Run only exact test cases, never files or directories: the new or changed tests and at
most two or three existing cases that run the changed code:

```bash
make test-focused TEST="tests/path/test_module.py::test_name tests/path/test_other.py::test_case[param]"
```

In a pull request, list the exact node IDs in the body's `tests` block; the
`Listed tests` CI job runs them through `make test-focused` (see
[GitHub Actions](../docs/development/github-actions.md#listed-tests)). CI stops a
test after 60 seconds. A test that needs longer declares
`@pytest.mark.timeout(<seconds>)` with a comment giving the reason.

Each new test must fail without the change. To prove it, commit the work, put the
base source back with `git checkout origin/development -- src`, run the new tests,
and restore with `git checkout HEAD -- src`. `PYTHONPATH` cannot do this: the
`pythonpath` setting in `pyproject.toml` puts the worktree's `src` first.
