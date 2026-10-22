# Python typing

The project uses ty for Python type checking and Ruff for linting and formatting.
The repository configuration in `pyproject.toml` owns the policy; `uv.lock` owns the
tool versions.

## Local commands

From the active checkout or worktree:

```sh
uv sync --frozen
uv run --frozen ruff check src tests scripts migrations
uv run --frozen ruff format --check src tests scripts migrations
uv run --frozen ty check
```

`make check` and the `Python static checks` CI job run the same commands. ty
checks production source, scripts and migrations. Its default scan excludes
`tests/`, nested `tests/` directories, `test_*.py`, `*_test.py`, and
`conftest.py` files. Ruff still lints and formats tests; neither tool executes
them.
List the behavior tests that prove the change in the PR's `tests` block; CI runs
them (see [GitHub Actions](github-actions.md#listed-tests)).

## Policy

- Keep meaningful parameter, return, field, and generic types. Validate external
  data at its boundary; do not replace a contract with `Any` or `object` to make
  a diagnostic disappear.
- ty checks normal type errors, strict generic narrowing, strict equality,
  unsound returns and yields, disjoint casts, missing generic arguments, and
  missing override declarations. Warnings also fail the command.
- Ruff requires annotations and enforces stub quality, specific suppression
  codes, unused-suppression cleanup, selected correctness rules, security rules
  (`S`, with the rules that only match a code shape listed with their reason in
  `pyproject.toml`), and restrictions on explicit `Any` and `no_type_check` imports.
- Tests are outside the default ty scope. Ruff still checks their correctness,
  suppression hygiene, and formatting, but annotation, stub-specific, and banned
  typing API rules do not apply to tests. Test fixture typing cleanup is not a
  prerequisite for the production type check.
- Use `# ty: ignore[rule-name]` only for an inspected, justified exception. Plain
  `# type: ignore` does not suppress ty diagnostics. Remove unnecessary casts
  rather than carrying checker workarounds forward.

The optional `unsound-assignment` rule stays off: SQLAlchemy's standard
`mapped_column` factory returns `MappedColumn[Any]`, which the rule rejects.
Ordinary assignment checking stays on. Dynamic assignment propagation is therefore
not fully checked; do not treat a clean run as proof that all dynamic values are
safe.

Ruff's explicit `Any` restrictions do not track every inferred dynamic value, and ty
does not prove field initialization or exhaustiveness. Use typed boundaries and
`assert_never` where exhaustive dispatch is part of the contract. Enable an optional
rule for a named defect it catches, not all of them at once, and do not add a second
type checker.

## Editor setup

Install the official ty and Ruff extensions and select this worktree's `.venv`
as the Python interpreter. Keep ty's `importStrategy` set to `fromEnvironment`
so the editor uses the repository-pinned executable. If the environment is not
installed, the extension can fall back to its bundled version; run the setup
command above before comparing editor and command-line diagnostics.

Keep typing rules in `pyproject.toml`, without duplicating them in editor inline
configuration. Disable other Python type-checker extensions for this workspace to
avoid duplicate diagnostics. Each worktree owns its environment; do not change global
editor settings or point an active worktree at another checkout's environment.

Official references: [ty editor setup](https://docs.astral.sh/ty/editors/) and
[editor settings](https://docs.astral.sh/ty/reference/editor-settings/).
