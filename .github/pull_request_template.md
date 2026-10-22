Closes #N <!-- or "Refs #N" when the issue has an acceptance item that needs the real environment -->

## Problem

<!-- The cause, with evidence a reviewer can reproduce: file:line, a plan, a log line, a measurement and its method. -->

## Changes

- <!-- Each change with its kind (cut, refactor, redesign) and any owner decision with its date and link. -->

Direction: <!-- Is this the right design against the decided architecture? Does it keep an old path alive? -->
Common practice: <!-- The practice for the problem and each mechanism added, where it was checked (URL or file:line), and "follows" or "deviates: <why>". -->

## Failure modes

| Failure | Test |
| --- | --- |
| | |

## Validation

The `Listed tests` CI job runs these exact pytest node IDs, one per line, and fails
if any is skipped or if other tests run. Delete the block if CI has no test to run.

```tests
tests/integration/<domain>/test_module.py::test_name
```

<!-- Tests that need another service: the command, the result and the tested commit. Say when a pass could be a skip. -->

## Not verified

<!-- What still needs the real environment, and where it will be verified. -->
