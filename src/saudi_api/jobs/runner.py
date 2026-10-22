"""The job runner (ADR-004).

`run_job` takes a session-level advisory lock named by the job on its own autocommit
connection, so two workers never run one job at once and no transaction stays open
across provider I/O. It records the run in `job_runs` before and after, with a bounded
summary. A job writes its results in short transactions after each provider response.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal

from sqlalchemy import Engine, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session, sessionmaker

from saudi_api.jobs.base import Job, JobContext, JobName
from saudi_api.jobs.checks import run_checks
from saudi_api.jobs.discover import run_discovery
from saudi_api.jobs.specs import run_spec_refresh
from saudi_api.json_types import JsonObject
from saudi_api.models import JobRunRow
from saudi_api.outbound import OutboundClient
from saudi_api.settings import Settings

_log = logging.getLogger(__name__)
_JOBS: dict[JobName, Job] = {
    "discover": run_discovery,
    "check": run_checks,
    "refresh-specs": run_spec_refresh,
}


@dataclass(frozen=True)
class JobResult:
    job: JobName
    run_id: uuid.UUID
    outcome: Literal["succeeded", "failed", "skipped_locked"]
    summary: JsonObject


def run_job(
    name: JobName, settings: Settings, engine: Engine, client: OutboundClient | None = None
) -> JobResult:
    run_id = uuid.uuid4()
    sessions = sessionmaker(engine, expire_on_commit=False)
    key = f"job:{name}"
    with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as lock:
        acquired = lock.scalar(text("SELECT pg_try_advisory_lock(hashtext(:key))"), {"key": key})
        if not acquired:
            _log.info("job skipped: another run holds the lock", extra={"job": name})
            return JobResult(name, run_id, "skipped_locked", {})
        try:
            started = datetime.now(UTC)
            _record(sessions, name, run_id, started, None, "running", {})
            context = JobContext(settings, sessions, client or OutboundClient(settings), run_id)
            _log.info("job started", extra={"job": name, "run_id": str(run_id)})
            try:
                summary = _JOBS[name](context)
            except Exception as error:
                summary: JsonObject = {"error": type(error).__name__}
                _record(sessions, name, run_id, started, datetime.now(UTC), "failed", summary)
                _log.exception("job failed", extra={"job": name, "run_id": str(run_id)})
                return JobResult(name, run_id, "failed", summary)
            _record(sessions, name, run_id, started, datetime.now(UTC), "succeeded", summary)
            _log.info("job finished", extra={"job": name, "run_id": str(run_id), **summary})
            return JobResult(name, run_id, "succeeded", summary)
        finally:
            _ = lock.execute(text("SELECT pg_advisory_unlock(hashtext(:key))"), {"key": key})


def _record(
    sessions: sessionmaker[Session],
    name: JobName,
    run_id: uuid.UUID,
    started: datetime,
    finished: datetime | None,
    outcome: str,
    summary: JsonObject,
) -> None:
    values = {
        "job": name,
        "run_id": run_id,
        "started_at": started,
        "finished_at": finished,
        "outcome": outcome,
        "summary": summary,
    }
    statement = insert(JobRunRow).values(values)
    with sessions() as db:
        _ = db.execute(
            statement.on_conflict_do_update(
                index_elements=[JobRunRow.job],
                set_={k: statement.excluded[k] for k in values if k != "job"},
            )
        )
        db.commit()


def last_finished(engine: Engine) -> dict[str, datetime]:
    """When each job last finished, whatever its outcome, for the worker's schedule."""
    with Session(engine) as db:
        rows = db.execute(
            text("SELECT job, finished_at FROM job_runs WHERE finished_at IS NOT NULL")
        )
        return {job: finished for job, finished in rows}
