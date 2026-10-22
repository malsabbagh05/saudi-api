# Test Fixtures

A test fixture is the defined, repeatable context needed to run a test. In
pytest, it is normally a function decorated with `@pytest.fixture` and requested
explicitly through a test argument.

A JSON, YAML, document, or image file is test data, not automatically a pytest
fixture. Proof, certification, issue, and review artifacts are not fixtures.

## Accepted Uses

Use a fixture when it makes a test clearer or safely manages setup and cleanup:

- create and roll back isolated database state;
- provide a temporary file, service, clock, or other test dependency;
- share small setup that several tests genuinely need;
- retain a minimal, authentic external payload or binary artifact that the
  project does not control; or
- reproduce the smallest input that caused a real defect.

Fixtures must be deterministic, minimal, free of secrets and customer data, and
consumed by an active test that exercises a production path. Cleanup belongs in
the fixture when it owns resources.

Fixtures are test support, not production concepts. Production models, services,
workers, APIs, and configuration must accept production types and must not
contain fixture-specific modes, models, runners, or branches.

Prefer explicit fixture arguments. Use `autouse` only for a true suite-wide
invariant; it must not select behavior by test name, hide production
dependencies, skip tests, or patch unrelated modules.

## Do Not Use a Fixture

Do not add a fixture when:

- constructing a production type the project owns directly in the test is clearer;
- it duplicates a Pydantic model, schema, default, or production rule;
- it exists to prove that an issue, epic, review, or release is complete;
- it feeds a fixture-only validator, report, manifest, matrix, or runner;
- it models a large synthetic world for a narrow assertion;
- it is unused, has no clear owning test, or preserves historical acceptance
  data; or
- maintaining it costs more than the setup it removes.

Use ordinary production tests and their exact commands as validation evidence.
Do not build a parallel proof or certification system around fixture data.

## Placement

- Keep a pytest fixture beside its tests. Put it in `conftest.py` only when its
  scope is genuinely shared.
- Keep external sample files under the consuming test area, named for the
  behavior or provider format they represent.
- Do not organize test data by roadmap epic, issue, proof gate, or review.
- Do not add a repository-level `fixtures/` directory.

## Review Questions

Before adding or retaining a fixture, answer:

1. Which active test owns it?
2. What information does it add that production code cannot express clearly?
3. Does the test exercise the real production boundary?
4. Is this the smallest deterministic setup or sample?
5. Will deleting it make development less safe or merely remove ceremony?

If these questions do not have concrete answers, do not keep the fixture.

## Resources

- [pytest: About fixtures](https://docs.pytest.org/en/stable/explanation/fixtures.html)
- [pytest: How to use fixtures](https://docs.pytest.org/en/stable/how-to/fixtures.html)
- [Stack Overflow: What are fixtures in programming?](https://stackoverflow.com/questions/12071344/what-are-fixtures-in-programming)
