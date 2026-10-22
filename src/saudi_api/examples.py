"""Usage examples derived from a catalogue endpoint (one owner: an entry never stores them).

Examples use each parameter's documented example value, and `$NAME` placeholders that
read credentials from environment variables; they never contain a real credential.
"""

from __future__ import annotations

import json
import re
from urllib.parse import quote, urlencode

from saudi_api.catalog.schema import Api, AuthScheme, Endpoint
from saudi_api.contracts import CodeExample

_PLACEHOLDER = re.compile(r"\$([A-Z][A-Z0-9_]*)")


def endpoint_url_template(api: Api, endpoint: Endpoint) -> str | None:
    base = api.production_base_url()
    return None if base is None else base.rstrip("/") + endpoint.path


def example_request(api: Api, endpoint: Endpoint) -> tuple[str, dict[str, str]] | None:
    """The example URL, with path and query filled from examples, and its headers."""
    base = api.production_base_url()
    if base is None:
        return None
    path = endpoint.path
    query: list[tuple[str, str]] = []
    headers: dict[str, str] = {}
    for parameter in endpoint.parameters:
        if parameter.example is None:
            continue
        if parameter.location == "path":
            path = path.replace("{" + parameter.name + "}", quote(parameter.example, safe=""))
        elif parameter.location == "query":
            query.append((parameter.name, parameter.example))
        else:
            headers[parameter.name] = parameter.example
    key = api.access.api_key
    if key is not None and key.location == "query":
        query.append((key.name, "$API_KEY"))
    if key is not None and key.location == "header":
        headers[key.name] = "$API_KEY"
    if AuthScheme.BEARER in api.access.auth:
        headers["Authorization"] = "Bearer $API_TOKEN"
    elif AuthScheme.OAUTH2 in api.access.auth or AuthScheme.JWT in api.access.auth:
        headers["Authorization"] = "Bearer $ACCESS_TOKEN"
    url = base.rstrip("/") + path
    if query:
        url += "?" + urlencode(query, safe="$:,")
    return url, headers


def code_examples(api: Api, endpoint: Endpoint) -> list[CodeExample]:
    request = example_request(api, endpoint)
    if request is None:
        return []
    url, headers = request
    basic = AuthScheme.BASIC in api.access.auth
    mtls = AuthScheme.MTLS in api.access.auth
    return [
        CodeExample(language="curl", code=_curl(endpoint.method, url, headers, basic, mtls)),
        CodeExample(language="python", code=_python(endpoint.method, url, headers, basic, mtls)),
        CodeExample(language="javascript", code=_javascript(endpoint.method, url, headers)),
    ]


def _curl(method: str, url: str, headers: dict[str, str], basic: bool, mtls: bool) -> str:
    # Double quotes keep the $NAME placeholders expandable by a POSIX shell.
    parts = ["curl"] + ([f"-X {method}"] if method != "GET" else []) + [_shell(url)]
    parts += [f"-H {_shell(f'{name}: {value}')}" for name, value in headers.items()]
    if basic:
        parts.append('-u "$USERNAME:$PASSWORD"')
    if mtls:
        parts.append("--cert client.crt --key client.key")
    return " \\\n  ".join(parts)


def _shell(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"').replace("`", "\\`")
    return f'"{escaped}"'


def _python(method: str, url: str, headers: dict[str, str], basic: bool, mtls: bool) -> str:
    needs_os = basic or any(_PLACEHOLDER.search(v) for v in [url, *headers.values()])
    lines = (["import os", ""] if needs_os else []) + ["import httpx", ""]
    lines += ["response = httpx.request(", f"    {method!r},", f"    {_python_str(url)},"]
    if headers:
        lines.append("    headers={")
        lines += [f"        {name!r}: {_python_str(v)}," for name, v in headers.items()]
        lines.append("    },")
    if basic:
        lines.append('    auth=(os.environ["USERNAME"], os.environ["PASSWORD"]),')
    if mtls:
        lines.append('    cert=("client.crt", "client.key"),')
    lines += ["    timeout=30,", ")", "response.raise_for_status()", "print(response.text)"]
    return "\n".join(lines)


def _python_str(value: str) -> str:
    if not _PLACEHOLDER.search(value):
        return repr(value)
    pieces = []
    for index, piece in enumerate(_PLACEHOLDER.split(value)):
        if index % 2:
            pieces.append("{os.environ[" + repr(piece) + "]}")
        else:
            pieces.append(piece.replace("{", "{{").replace("}", "}}"))
    return "f" + json.dumps("".join(pieces), ensure_ascii=False)


def _javascript(method: str, url: str, headers: dict[str, str]) -> str:
    lines = [f"const response = await fetch({_js_str(url)}, {{", f"  method: {json.dumps(method)},"]
    if headers:
        lines.append("  headers: {")
        lines += [f"    {json.dumps(name)}: {_js_str(v)}," for name, v in headers.items()]
        lines.append("  },")
    lines += [
        "});",
        "if (!response.ok) throw new Error(`HTTP ${response.status}`);",
        "console.log(await response.text());",
    ]
    return "\n".join(lines)


def _js_str(value: str) -> str:
    if not _PLACEHOLDER.search(value):
        return json.dumps(value, ensure_ascii=False)
    pieces = []
    for index, piece in enumerate(_PLACEHOLDER.split(value)):
        if index % 2:
            pieces.append("${process.env." + piece + "}")
        else:
            pieces.append(piece.replace("\\", "\\\\").replace("`", "\\`").replace("${", "\\${"))
    return "`" + "".join(pieces) + "`"
