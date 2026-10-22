# GitHub Actions and branch rules

This document owns the GitHub Actions workflows, the checks they run, and the branch
rules. Workflows run on GitHub-hosted `ubuntu-latest` runners, pin every action by
commit SHA with its version in a comment, and start with `contents: read`
permissions.

## Developer validation

Two workflows check pull requests: `Static checks`, with independent
`Python static checks` and `Web static checks` jobs, and `Listed tests`.

The pull-request author lists the exact tests that prove the change in the body,
and the `Listed tests` job runs them (see [Listed tests](#listed-tests)). Tests
that need a service CI does not provide, such as a search engine, a provider or a
shared environment, run in the development or test environment; the pull request
records their commands, results, tested commit, and the relevant coverage that was
not run. After further changes, CI reruns the listed tests and the author reruns
the other affected tests and updates that evidence. Code owners review the change
and its validation together.

`Python static checks` first scans the tracked files for secrets with Trivy, before
it installs anything, and fails on any finding. It then installs the locked
dependencies, requires at most one Alembic head, and runs Ruff lint and format checks
over `src`, `tests`, `scripts` and `migrations`, followed by ty
([Python typing](python-typing.md)).
It collects every test under `tests` without running one
(`pytest --collect-only`, no database), so a test that imports a removed name fails
the pull request instead of waiting until a pull request lists it. Last, it checks
that async route handlers await (`scripts/ci/check_async_routes.py`) and that every
catalogue file is valid (`saudi-api catalog check`, [Catalogue files](catalogue.md)).

`Web static checks` runs lint and the production build in `web/` (`next build`,
which also type-checks the project). It needs `web/.nvmrc`, `web/package-lock.json`
and the `lint` and `build` scripts. `npm run lint` runs ESLint and checks that
`web/messages/en.json` and `web/messages/ar.json` have the same keys; Next.js 16's
build no longer lints. Playwright tests need the API and a database, so they run
locally and the pull request records them ([Web app](web.md)).

Both jobs run on every non-draft pull request targeting `development`, `staging` or
`main`, and on a draft marked ready for review. Title and body edits do not rerun
them. Newer runs cancel superseded runs for the same pull request. Each job has a
ten-minute safety timeout, not a runtime target.

Add an architecture check to `scripts/ci/` only for a concrete recurrence risk: a
failure that happened, or one a review found, that a rule in code can catch.

## Listed tests

`listed-tests.yml` runs the tests a pull request lists, and only those. List exact
pytest node IDs, one per line, in a fenced block whose info string is `tests`:

````markdown
```tests
tests/integration/<domain>/test_module.py::test_name
tests/integration/<domain>/test_module.py::test_name[case]
```
````

- The job reads the block from the body when the pull request opens, gets a push or
  is reopened, drafts included. Every new head runs its own listed cases. Without a
  block it runs nothing and passes.
- An edit-only selection job compares the old and current validated node-ID sets.
  A title edit, prose edit, reordered list or repeated ID does not rerun tests or
  cancel an active test run. An unchanged edit produces a separately named skipped
  check (`Listed tests unchanged`), so it cannot replace an earlier failed `Listed
  tests` check with a successful skip. Changed IDs run the actual cases. An invalid
  current list fails `Listed tests`.
- `scripts/ci/listed_tests.py` accepts only node IDs of a test function in an
  existing file under `tests/`: no files, directories, classes or discovery. Make
  expands the IDs, so their characters are limited; a parameter ID with other
  characters cannot be listed.
- `listed_tests.py collect` validates the IDs with pytest's own collection before any
  test runs. It names missing IDs and rejects selections that expand to unlisted
  parameter cases. It runs no fixture or test body; import and collection errors
  fail the check.
- Use the same entry point before pushing, from the task worktree:

  ```bash
  PR_BODY="$(cat /path/to/pr-body.md)" uv run --frozen python scripts/ci/listed_tests.py collect
  ```

- It runs `make test-focused`, which starts the test PostgreSQL container with the
  settings in `tests/support/postgres.conf`, as it does locally. Up to four
  pytest-xdist workers run the tests side by side; each test clones the migrated
  template.
- pytest-timeout stops a test after 60 seconds. A test that needs longer declares
  `@pytest.mark.timeout(<seconds>)` with a comment giving the reason. The job stops
  after 20 minutes.
- `listed_tests.py require-run` compares the JUnit report with the list. The job
  fails if a listed test is skipped or does not run, or if any other test runs, for
  example every case of a parametrized test listed without its parameter ID.

## Promotion source

`promotion-source.yml` runs the `Promotion source` job on every pull request into
`staging`, drafts included. It requires the head to contain the current `staging`
commit and its tree to equal one of the newest 500 `development` commits, using
`scripts/ci/promotion-source`. `merge-on-green` runs the
same check before waiting and before merging.

## Dependency scan

`dependency-scan.yml` scans `development` once a day with Trivy, run as a program,
not a container. It reads every lockfile, development dependencies included, and
fails when a high or critical vulnerability has a fixed version. GitHub sends the
failure of a scheduled run to the user who last changed the workflow's schedule. Secrets are a pull-request check
instead: `Python static checks` blocks a pull request whose files hold one.

`scripts/ci/install-trivy.sh` downloads one pinned Trivy version and checks its
SHA-256; no Trivy action runs. Trivy's release tags were once replaced with
credential-stealing code, so a moving tag is not trusted. To update Trivy, change
the version and the checksum together, from the release's checksum file.

A finding that has no usable fix is listed in `.trivyignore` with its reason and the
condition for removing it.

GitHub starts scheduled runs only from the default branch, `main`. Change the file
through a `development` pull request, then promote only that file to `main`.

## Dependency updates

`.github/dependabot.yml` asks Dependabot for weekly version updates of the
lockfiles on `development` (uv at the root, npm in `web/`), the base images the
Dockerfiles pin by digest, and the actions the workflows pin by commit. Minor and patch updates arrive
grouped per lockfile; major updates arrive one per pull request, so each breaking
change can be reviewed and reverted alone.

A Dependabot pull request has no `tests` block, so `Listed tests` passes without
running a test. Before merging one, add existing tests that use the updated packages
to its body. Passing static checks alone does not prove that the consumer starts.

GitHub reads the file from the default branch, `main`, and `target-branch` points
each entry at `development`. The scheduled workflows also live on `main`, so the
actions have a second entry without `target-branch`. Merge the two action updates
together, so the copies stay equal.

## Ownership and review

These are repository settings, not files. Create them by hand when the repository
is set up, and record any later change here.

- `main` is the default branch. Create `development` and `staging` from it when the
  repository is set up; pull requests land on `development`.
- `.github/CODEOWNERS` names the default owners. GitHub reads it from a pull
  request's target branch, so keep it equal on all three branches.
- Each of `development`, `staging` and `main` has a ruleset that requires a pull
  request, code-owner review, resolution of review conversations, and dismissal of
  approvals after reviewable changes. `development` requires one approval; `main`
  requires two. All allow squash merge only and block force pushes and deletion.
  `development` also requires linear history and a commit subject ending with the
  issue or pull-request number.
- The `development` and `staging` rulesets require the `Python static checks` and
  `Web static checks` job results from GitHub Actions, with strict freshness: a
  branch behind its base must be updated and pass again. The rulesets do not
  require `Listed tests`; `merge-on-green` waits for it.
- Only `malsabbagh05` merges into `development`, `staging` and `main`. Each
  ruleset restricts updates to its bypass list, which holds that one account,
  through pull requests only. The bypass is not permission to skip failing checks.
