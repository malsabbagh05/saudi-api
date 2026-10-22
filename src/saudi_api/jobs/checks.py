"""Reachability checks: one GET per API to its check URL, latest result in `api_checks`.

The check URL is the entry's `check.url`, or its documentation page. The outcome is a
closed set; a redirect or a 2xx counts as reachable. Each result records the region the
check ran from (`CHECK_REGION`), because several Saudi hosts refuse other networks.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from saudi_api.catalog.schema import Api, entry_context
from saudi_api.jobs.base import JobContext
from saudi_api.json_types import JsonObject
from saudi_api.models import ApiCheckRow, ApiRow
from saudi_api.outbound import (
    DEFAULT_REQUESTS_PER_MINUTE,
    FailureCode,
    OutboundFailed,
    OutboundRefused,
)

_FAILURE_OUTCOME = {
    FailureCode.TIMEOUT: "timeout",
    FailureCode.CONNECTION_ERROR: "connection_error",
    FailureCode.UNRESOLVABLE: "connection_error",
    FailureCode.TLS_ERROR: "tls_error",
    # The host answered with more than the cap: it is reachable.
    FailureCode.TOO_LARGE: "reachable",
}


def run_checks(context: JobContext) -> JsonObject:
    with context.sessions() as db:
        validation = entry_context(context.settings.outbound_allow_loopback_http)
        entries = [
            Api.model_validate(e, context=validation) for e in db.scalars(select(ApiRow.entry))
        ]
    counts: dict[str, int] = {}
    for api in entries:
        outcome = check_api(context, api)
        counts[outcome] = counts.get(outcome, 0) + 1
    return {"checked": len(entries), **counts}


def check_api(context: JobContext, api: Api) -> str:
    url = api.check.url if api.check else api.documentation_url
    status: int | None = None
    latency: int | None = None
    try:
        response = context.client.get(
            url,
            allowed_hosts=api.catalogued_hosts(),
            per_minute=api.usage.max_requests_per_minute or DEFAULT_REQUESTS_PER_MINUTE,
            wait_for_budget=True,
            accept="text/html,application/json;q=0.9,*/*;q=0.8",
        )
        status = response.status
        latency = response.elapsed_ms
        outcome = "reachable" if response.status < 400 else "http_error"
    except OutboundRefused:
        outcome = "refused_by_policy"
    except OutboundFailed as error:
        outcome = _FAILURE_OUTCOME[error.code]
    _record(context, api.slug, outcome, status, latency)
    return outcome


def _record(
    context: JobContext, slug: str, outcome: str, status: int | None, latency: int | None
) -> None:
    now = datetime.now(UTC)
    reachable = outcome == "reachable"
    with context.sessions() as db:
        previous = db.get(ApiCheckRow, slug)
        failures = 0 if reachable else (previous.consecutive_failures + 1 if previous else 1)
        last_success = now if reachable else (previous.last_success_at if previous else None)
        values = {
            "api_slug": slug,
            "checked_at": now,
            "outcome": outcome,
            "http_status": status,
            "latency_ms": latency,
            "consecutive_failures": failures,
            "last_success_at": last_success,
            "region": context.settings.check_region,
        }
        statement = insert(ApiCheckRow).values(values)
        _ = db.execute(
            statement.on_conflict_do_update(
                index_elements=[ApiCheckRow.api_slug],
                set_={k: statement.excluded[k] for k in values if k != "api_slug"},
            )
        )
        db.commit()
