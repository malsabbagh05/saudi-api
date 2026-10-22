"""Read the tests a pull request lists, and require that each of them ran.

A pull request lists exact pytest node IDs, one per line, in a fenced block whose
info string is ``tests``. CI runs only those tests: never files,
directories, suites or tests found by import or coverage.
"""

from __future__ import annotations

import argparse
import os
from collections.abc import Sequence
from pathlib import Path, PurePosixPath
import re
import sys
from xml.etree import ElementTree

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pytest

_OPEN_FENCE = "```tests"
_FENCE = "```"
# Make expands the IDs and the shell splits them, so the characters are limited:
# a test file under tests/, an optional class, a test function and a parameter ID.
# A class alone would select all its tests. A parametrized test without its
# parameter ID passes syntax validation; collection rejects the cases it expands to.
_NODE_ID = re.compile(
    r"tests/[A-Za-z0-9_./-]+\.py(?:::[A-Za-z_][A-Za-z0-9_]*)?::test[A-Za-z0-9_]*"
    r"(?:\[[A-Za-z0-9_.,:=+/-]+\])?"
)
# The most pytest-xdist workers one job starts. Keep it at or below the CPU count
# of the runner that listed-tests.yml uses.
_MAX_WORKERS = 4


class ListedTestsError(ValueError):
    """The pull request body lists something that is not an exact test."""


def listed_tests(body: str, *, root: Path) -> list[str]:
    """The node IDs in the body's tests blocks, in order and without repeats."""
    listed: dict[str, None] = {}
    inside = False
    for raw_line in body.splitlines():
        line = raw_line.strip()
        if not inside:
            inside = line == _OPEN_FENCE
            continue
        if line.startswith(_FENCE):
            inside = False
            continue
        if not line or line.startswith("#"):
            continue
        if not _NODE_ID.fullmatch(line):
            raise ListedTestsError(f"not an exact test node ID: {line!r}")
        path = PurePosixPath(line.split("::", 1)[0])
        if ".." in path.parts or not (root / path).is_file():
            raise ListedTestsError(f"no such test file: {path}")
        listed[line] = None
    if inside:
        raise ListedTestsError("the tests block is not closed")
    return list(listed)


def require_collection(listed: Sequence[str]) -> int:
    """Collect only the selected IDs, without workers, fixtures or test bodies."""
    if not listed:
        print("No tests listed.")
        return 0

    # Syntax/selection commands run before CI installs the test dependencies.
    import pytest  # noqa: PLC0415 - syntax commands must work before dependency installation.

    collected: set[str] = set()
    selected: set[str] = set()

    class Selection:
        def pytest_collectreport(self, report: pytest.CollectReport) -> None:
            # The session report retains matched IDs even when another ID is
            # missing and pytest aborts before filling session.items. Pytest's
            # missing-parameter diagnostic can omit the parameter suffix.
            if report.nodeid == "" and report.passed:
                selected.update(node.nodeid for node in report.result)

        def pytest_collection_finish(self, session: pytest.Session) -> None:
            collected.update(item.nodeid for item in session.items)

    status = pytest.main(
        ["--collect-only", "-q", "-n", "0", "-p", "no:cacheprovider", *listed],
        plugins=[Selection()],
    )
    if status != pytest.ExitCode.OK:
        # Keep pytest's actual missing-ID/import-error diagnostics in the log.
        print("::error::Listed test collection failed; no tests were executed.", file=sys.stderr)
        collected = selected
    expected = set(listed)
    problems = [f"listed but not collected: {node_id}" for node_id in sorted(expected - collected)]
    problems += [f"collected but not listed: {node_id}" for node_id in sorted(collected - expected)]
    for problem in problems:
        print(f"::error::{problem}", file=sys.stderr)
    return 1 if status != pytest.ExitCode.OK or problems else 0


def _junit_case(node_id: str) -> tuple[str, str]:
    """The JUnit classname and name pytest reports for a node ID."""
    address, bracket, parameters = node_id.partition("[")
    names = address.split("::")
    names[0] = names[0].removesuffix(".py").replace("/", ".")
    return ".".join(names[:-1]), names[-1] + bracket + parameters


def require_run(report: Path, listed: Sequence[str] = ()) -> list[str]:
    """Problems in a JUnit report: no test ran, a test was skipped, or the tests
    that ran differ from the listed ones (an expanded or a missing case)."""
    # The report is the JUnit file pytest wrote earlier in the same job, not outside input.
    root = ElementTree.parse(report).getroot()  # noqa: S314
    cases = [(case.get("classname", ""), case.get("name", "")) for case in root.iter("testcase")]
    if not cases:
        return ["no test ran"]
    problems = [
        f"skipped: {case.get('classname')}::{case.get('name')}"
        for case in root.iter("testcase")
        if case.find("skipped") is not None
    ]
    if listed:
        expected = {_junit_case(node_id): node_id for node_id in listed}
        ran = set(cases)
        problems += [
            f"ran but not listed: {classname}::{name}"
            for classname, name in sorted(ran - expected.keys())
        ]
        problems += [
            f"listed but did not run: {node_id}"
            for case, node_id in expected.items()
            if case not in ran
        ]
    return problems


def _write_targets(body: str, *, root: Path, output: Path | None) -> int:
    try:
        targets = listed_tests(body, root=root)
    except ListedTestsError as error:
        print(f"::error::{error}", file=sys.stderr)
        return 1
    workers = min(len(targets), _MAX_WORKERS)
    lines = (
        f"targets={' '.join(targets)}",
        f"count={len(targets)}",
        # One test runs without worker processes.
        f"workers={0 if workers == 1 else workers}",
    )
    if output is not None:
        with output.open("a", encoding="utf-8") as stream:
            _ = stream.write("".join(f"{line}\n" for line in lines))
    print("\n".join(targets) if targets else "No tests listed.")
    return 0


def _write_selection(body: str, previous_body: str, *, root: Path, output: Path | None) -> int:
    try:
        current = set(listed_tests(body, root=root))
    except ListedTestsError as error:
        print(f"::error::{error}", file=sys.stderr)
        return 1
    try:
        unchanged = current == set(listed_tests(previous_body, root=root))
    except ListedTestsError:
        # Correcting an invalid selection must execute the now-valid list.
        unchanged = False
    line = f"unchanged={str(unchanged).lower()}\n"
    if output is not None:
        with output.open("a", encoding="utf-8") as stream:
            _ = stream.write(line)
    print(line, end="")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    _ = commands.add_parser("targets", help="read the tests block from PR_BODY")
    _ = commands.add_parser("selection", help="compare an edited PR's old and current test IDs")
    _ = commands.add_parser(
        "collect", help="require the PR_BODY IDs to collect exactly, without execution"
    )
    check = commands.add_parser("require-run", help="fail unless exactly the listed tests ran")
    _ = check.add_argument("report", type=Path)
    _ = check.add_argument("listed", nargs="*", help="the listed node IDs; omit to skip the match")
    arguments = parser.parse_args(argv)
    output_value = os.environ.get("GITHUB_OUTPUT")
    output = Path(output_value) if output_value else None
    if arguments.command == "selection":
        body = os.environ.get("PR_BODY", "")
        previous_body = (
            os.environ.get("PREVIOUS_PR_BODY", "")
            if os.environ.get("PR_BODY_EDITED") == "true"
            else body
        )
        return _write_selection(body, previous_body, root=Path.cwd(), output=output)
    if arguments.command == "collect":
        try:
            targets = listed_tests(os.environ.get("PR_BODY", ""), root=Path.cwd())
        except ListedTestsError as error:
            print(f"::error::{error}", file=sys.stderr)
            return 1
        return require_collection(targets)
    if arguments.command == "targets":
        return _write_targets(
            os.environ.get("PR_BODY", ""),
            root=Path.cwd(),
            output=output,
        )
    problems = require_run(arguments.report, arguments.listed)
    for problem in problems:
        print(f"::error::{problem}", file=sys.stderr)
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
