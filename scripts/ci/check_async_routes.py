"""Fail when a FastAPI route handler is `async def` but never awaits.

FastAPI runs `async def` handlers on the API's one event loop and plain `def`
handlers in its thread pool. An `async def` handler without an await does its
work synchronously on the loop, so its database or file I/O stops every other
request until it returns. Such a handler must be `def`.

A handler that must stay on the loop has `# on-event-loop: <reason>` on the line
directly above its `async def`: a probe without I/O that must answer while the
thread pool is full, or an owner whose process-wide state only the loop's
one-at-a-time execution protects (name the issue that removes that state).
"""

import ast
import re
import sys
from collections.abc import Iterator
from pathlib import Path

_ON_EVENT_LOOP = re.compile(r"^\s*# on-event-loop: \S")
_ROUTE_METHODS = frozenset(
    {"get", "post", "put", "patch", "delete", "head", "options", "api_route", "websocket"}
)


def _is_route_decorator(decorator: ast.expr) -> bool:
    """`@app.<method>(...)` or `@<name>router.<method>(...)`."""
    return (
        isinstance(decorator, ast.Call)
        and isinstance(decorator.func, ast.Attribute)
        and decorator.func.attr in _ROUTE_METHODS
        and isinstance(decorator.func.value, ast.Name)
        and (decorator.func.value.id == "app" or decorator.func.value.id.endswith("router"))
    )


def _body_nodes(function: ast.AsyncFunctionDef) -> Iterator[ast.AST]:
    """Nodes of the function body, without nested functions, lambdas and classes."""
    pending: list[ast.AST] = list(function.body)
    while pending:
        node = pending.pop()
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.Lambda | ast.ClassDef):
            continue
        yield node
        pending.extend(ast.iter_child_nodes(node))


def _uses_async(node: ast.AST) -> bool:
    return isinstance(
        node, ast.Await | ast.AsyncFor | ast.AsyncWith | ast.Yield | ast.YieldFrom
    ) or (isinstance(node, ast.comprehension) and bool(node.is_async))


def await_free_routes(root: Path) -> list[str]:
    found: list[str] = []
    for path in sorted(root.rglob("*.py")):
        source = path.read_text(encoding="utf-8")
        lines = source.splitlines()
        for node in ast.walk(ast.parse(source, filename=str(path))):
            if (
                isinstance(node, ast.AsyncFunctionDef)
                and any(_is_route_decorator(decorator) for decorator in node.decorator_list)
                and not (node.lineno >= 2 and _ON_EVENT_LOOP.match(lines[node.lineno - 2]))
                and not any(_uses_async(child) for child in _body_nodes(node))
            ):
                found.append(
                    f"{path}:{node.lineno}: route handler `{node.name}` is async but never"
                    + " awaits; make it `def`, or mark why it must stay on the event loop"
                )
    return found


def main() -> int:
    found = await_free_routes(Path(sys.argv[1] if len(sys.argv) > 1 else "src"))
    for line in found:
        print(line)
    return 1 if found else 0


if __name__ == "__main__":
    raise SystemExit(main())
