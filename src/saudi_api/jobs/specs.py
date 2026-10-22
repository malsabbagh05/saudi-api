"""Specification refresh: keep the latest provider-published OpenAPI document per API.

For each entry with `openapi_url`, the job follows robots.txt, downloads the document
(JSON or YAML, at most the outbound size cap), checks that it is an OpenAPI 3.x or
Swagger 2.0 document with `paths`, and stores it with its operation list. An unchanged
document only advances `checked_at`; a failed attempt keeps the last good document.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from hashlib import sha256
from typing import override

import yaml
from pydantic import TypeAdapter, ValidationError
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from saudi_api.catalog.schema import Api, entry_context
from saudi_api.jobs.base import JobContext
from saudi_api.json_types import JsonObject, JsonValue
from saudi_api.models import ApiRow, ApiSpecRow
from saudi_api.outbound import (
    DEFAULT_REQUESTS_PER_MINUTE,
    FailureCode,
    OutboundFailed,
    OutboundRefused,
)

_JSON_OBJECT: TypeAdapter[JsonObject] = TypeAdapter(JsonObject)
_METHODS = ("get", "put", "post", "delete", "patch", "head", "options", "trace")


def run_spec_refresh(context: JobContext) -> JsonObject:
    with context.sessions() as db:
        validation = entry_context(context.settings.outbound_allow_loopback_http)
        entries = [
            Api.model_validate(e, context=validation) for e in db.scalars(select(ApiRow.entry))
        ]
    counts: dict[str, int] = {}
    for api in entries:
        if api.openapi_url is None:
            continue
        outcome = refresh_spec(context, api)
        counts[outcome] = counts.get(outcome, 0) + 1
    summary: JsonObject = {outcome: n for outcome, n in counts.items()}
    return summary


def refresh_spec(context: JobContext, api: Api) -> str:
    assert api.openapi_url is not None
    url = api.openapi_url
    hosts = api.catalogued_hosts()
    if not context.client.robots_allows(url, allowed_hosts=hosts):
        return _record_attempt(context, api, "disallowed_by_robots")
    try:
        response = context.client.get(
            url,
            allowed_hosts=hosts,
            per_minute=api.usage.max_requests_per_minute or DEFAULT_REQUESTS_PER_MINUTE,
            wait_for_budget=True,
            accept="application/json, application/yaml;q=0.9, text/yaml;q=0.8, */*;q=0.5",
        )
    except OutboundRefused:
        return _record_attempt(context, api, "refused_by_policy")
    except OutboundFailed as error:
        code = "too_large" if error.code is FailureCode.TOO_LARGE else error.code.value
        return _record_attempt(context, api, "connection_error" if code == "unresolvable" else code)
    if response.status != 200:
        return _record_attempt(context, api, "http_error")

    digest = sha256(response.body).hexdigest()
    with context.sessions() as db:
        previous = db.get(ApiSpecRow, api.slug)
        if previous is not None and previous.sha256 == digest and previous.source_url == url:
            previous.checked_at = datetime.now(UTC)
            previous.outcome = "unchanged"
            db.commit()
            return "unchanged"

    document = _parse(response.body)
    if document is None:
        return _record_attempt(context, api, "invalid_document")
    version = document.get("openapi") or document.get("swagger")
    info = document.get("info")
    title = info.get("title") if isinstance(info, dict) else None
    now = datetime.now(UTC)
    _upsert(
        context,
        {
            "api_slug": api.slug,
            "checked_at": now,
            "outcome": "fetched",
            "fetched_at": now,
            "source_url": url,
            "sha256": digest,
            "spec_version": str(version),
            "title": title if isinstance(title, str) else None,
            "operations": _operations(document),
            "document": document,
        },
    )
    return "fetched"


class _NoAliasLoader(yaml.SafeLoader):
    """Safe YAML without aliases: an alias can expand a small document without bound."""

    @override
    def compose_node(self, parent: yaml.Node | None, index: int) -> yaml.Node | None:
        if self.check_event(yaml.AliasEvent):
            raise yaml.YAMLError("aliases are not accepted")
        return super().compose_node(parent, index)


def _parse(body: bytes) -> JsonObject | None:
    try:
        text = body.decode("utf-8")
        if text.lstrip().startswith("{"):
            document = json.loads(text)
        else:
            loaded = yaml.load(text, Loader=_NoAliasLoader)  # noqa: S506 - a SafeLoader subclass
            # A JSON round trip turns YAML-only values (dates) into JSON text.
            document = json.loads(json.dumps(loaded, default=str))
        document = _JSON_OBJECT.validate_python(document)
    except UnicodeDecodeError, yaml.YAMLError, ValueError, RecursionError, ValidationError:
        return None
    version = document.get("openapi") or document.get("swagger")
    if not isinstance(version, str) or not version.startswith(("3.", "2.")):
        return None
    if not isinstance(document.get("paths"), dict):
        return None
    return document


def _operations(document: JsonObject) -> list[JsonValue]:
    paths = document.get("paths")
    operations: list[JsonValue] = []
    if not isinstance(paths, dict):
        return operations
    for path, item in paths.items():
        if not isinstance(item, dict):
            continue
        for method in _METHODS:
            operation = item.get(method)
            if not isinstance(operation, dict):
                continue
            summary = operation.get("summary") or operation.get("operationId")
            operations.append(
                {
                    "method": method.upper(),
                    "path": path,
                    "summary": summary if isinstance(summary, str) else None,
                }
            )
    return operations


def _record_attempt(context: JobContext, api: Api, outcome: str) -> str:
    """Record a failed attempt, keeping the last good document if there is one."""
    assert api.openapi_url is not None
    now = datetime.now(UTC)
    with context.sessions() as db:
        previous = db.get(ApiSpecRow, api.slug)
        if previous is not None:
            previous.checked_at = now
            previous.outcome = outcome
            db.commit()
            return outcome
    _upsert(
        context,
        {
            "api_slug": api.slug,
            "checked_at": now,
            "outcome": outcome,
            "fetched_at": None,
            "source_url": api.openapi_url,
            "sha256": None,
            "spec_version": None,
            "title": None,
            "operations": None,
            "document": None,
        },
    )
    return outcome


def _upsert(context: JobContext, values: dict[str, object]) -> None:
    statement = insert(ApiSpecRow).values(values)
    with context.sessions() as db:
        _ = db.execute(
            statement.on_conflict_do_update(
                index_elements=[ApiSpecRow.api_slug],
                set_={k: statement.excluded[k] for k in values if k != "api_slug"},
            )
        )
        db.commit()
