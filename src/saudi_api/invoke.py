"""Agent invocation of a catalogued endpoint (ADR-004), behind the MCP tool `call_endpoint`.

Only an API whose entry allows agent invocation can be called, only its declared GET
endpoints, and only with its declared path and query parameters. The request goes
through `outbound.py` without waiting for the per-host budget: an exhausted budget is a
refusal with a retry time. The result is capped at MAX_OUTPUT_CHARACTERS.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import StrEnum
from urllib.parse import quote, urlencode

from saudi_api.catalog.schema import AgentInvocation, Api, Parameter, ParameterType
from saudi_api.outbound import (
    DEFAULT_REQUESTS_PER_MINUTE,
    OutboundClient,
    OutboundFailed,
    OutboundRefused,
    RefusalCode,
)

# ADR-004: Claude Code's 10,000-token warning threshold x 3 characters per token.
MAX_OUTPUT_CHARACTERS = 30_000
# Room for the result's own fields around the provider body.
_BODY_CHARACTERS = MAX_OUTPUT_CHARACTERS - 2_000
_MAX_ARGUMENT_LENGTH = 1_000

type ArgumentValue = str | int | float | bool


class InvocationCode(StrEnum):
    NOT_INVOCABLE = "not_invocable"
    DISALLOWED_BY_ROBOTS = "disallowed_by_robots"
    UNKNOWN_ENDPOINT = "unknown_endpoint"
    INVALID_ARGUMENTS = "invalid_arguments"
    BUDGET_EXHAUSTED = "budget_exhausted"
    REFUSED_BY_POLICY = "refused_by_policy"
    TIMEOUT = "timeout"
    CONNECTION_ERROR = "connection_error"
    TLS_ERROR = "tls_error"
    TOO_LARGE = "too_large"


class InvocationError(Exception):
    def __init__(
        self,
        code: InvocationCode,
        *,
        fields: list[str] | None = None,
        undeclared: int = 0,
        retry_after_seconds: float | None = None,
    ) -> None:
        super().__init__(code.value)
        self.code = code
        # Declared parameters that are missing or invalid; undeclared ones are only
        # counted, so an error never echoes a name the caller made up.
        self.fields = fields or []
        self.undeclared = undeclared
        self.retry_after_seconds = retry_after_seconds


@dataclass(frozen=True)
class Invocation:
    status: int
    url: str
    content_type: str | None
    body: str
    truncated: bool
    elapsed_ms: int


def invoke(
    client: OutboundClient, api: Api, endpoint_id: str, arguments: dict[str, ArgumentValue]
) -> Invocation:
    if api.usage.agent_invocation is not AgentInvocation.ALLOWED:
        raise InvocationError(InvocationCode.NOT_INVOCABLE)
    endpoint = next((e for e in api.endpoints if e.id == endpoint_id), None)
    if endpoint is None or endpoint.method != "GET":
        raise InvocationError(InvocationCode.UNKNOWN_ENDPOINT)
    base = api.production_base_url()
    if base is None:
        raise InvocationError(InvocationCode.UNKNOWN_ENDPOINT)

    declared = {p.name: p for p in endpoint.parameters if p.location in ("path", "query")}
    undeclared = sum(1 for name in arguments if name not in declared)
    problems: list[str] = []
    values: dict[str, str] = {}
    for name, parameter in declared.items():
        if name not in arguments:
            if parameter.required:
                problems.append(name)
            continue
        value = _coerce(parameter, arguments[name])
        if value is None:
            problems.append(name)
        else:
            values[name] = value
    if problems or undeclared:
        raise InvocationError(
            InvocationCode.INVALID_ARGUMENTS, fields=sorted(problems), undeclared=undeclared
        )

    path = endpoint.path
    query: list[tuple[str, str]] = []
    for name, value in values.items():
        if declared[name].location == "path":
            path = path.replace("{" + name + "}", quote(value, safe=""))
        else:
            query.append((name, value))
    url = base.rstrip("/") + path + (("?" + urlencode(query)) if query else "")

    hosts = api.catalogued_hosts()
    if not client.robots_allows(url, allowed_hosts=hosts):
        raise InvocationError(InvocationCode.DISALLOWED_BY_ROBOTS)
    try:
        response = client.get(
            url,
            allowed_hosts=hosts,
            per_minute=api.usage.max_requests_per_minute or DEFAULT_REQUESTS_PER_MINUTE,
            wait_for_budget=False,
            accept="application/json, text/csv;q=0.9, */*;q=0.5",
        )
    except OutboundRefused as error:
        if error.code is RefusalCode.BUDGET_EXHAUSTED:
            raise InvocationError(
                InvocationCode.BUDGET_EXHAUSTED, retry_after_seconds=error.retry_after_seconds
            ) from error
        raise InvocationError(InvocationCode.REFUSED_BY_POLICY) from error
    except OutboundFailed as error:
        code = {
            "timeout": InvocationCode.TIMEOUT,
            "tls_error": InvocationCode.TLS_ERROR,
            "too_large": InvocationCode.TOO_LARGE,
        }.get(error.code.value, InvocationCode.CONNECTION_ERROR)
        raise InvocationError(code) from error

    text = response.body.decode("utf-8", errors="replace")
    if response.content_type and "json" in response.content_type:
        try:
            text = json.dumps(json.loads(text), ensure_ascii=False, separators=(",", ":"))
        except ValueError:
            pass
    truncated = len(text) > _BODY_CHARACTERS
    return Invocation(
        status=response.status,
        url=url,
        content_type=response.content_type,
        body=text[:_BODY_CHARACTERS],
        truncated=truncated,
        elapsed_ms=response.elapsed_ms,
    )


def _coerce(parameter: Parameter, value: ArgumentValue) -> str | None:
    """The argument as the string sent on the wire, or None when it is not valid."""
    if isinstance(value, bool):
        text = "true" if value else "false"
        valid = parameter.type in (ParameterType.BOOLEAN, ParameterType.STRING)
    else:
        text = str(value).strip()
        match parameter.type:
            case ParameterType.INTEGER:
                valid = text.lstrip("-").isdigit()
            case ParameterType.NUMBER:
                valid = _is_number(text)
            case ParameterType.BOOLEAN:
                valid = text in ("true", "false")
            case ParameterType.STRING:
                valid = True
    if not valid or not text or len(text) > _MAX_ARGUMENT_LENGTH:
        return None
    if parameter.allowed_values is not None and text not in parameter.allowed_values:
        return None
    return text


def _is_number(text: str) -> bool:
    try:
        float(text)
    except ValueError:
        return False
    return True
