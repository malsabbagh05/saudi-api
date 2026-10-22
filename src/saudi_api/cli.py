"""The `saudi-api` command: migrations, catalogue check and sync, jobs, worker, servers."""

from __future__ import annotations

import argparse
import logging
import signal
import sys
import threading
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import FrameType

import uvicorn
from alembic import command
from alembic.config import Config
from sqlalchemy.orm import sessionmaker

from saudi_api import logs
from saudi_api.api.app import openapi_json
from saudi_api.catalog.loader import CatalogError, load_catalog
from saudi_api.catalog.sync import sync_catalog
from saudi_api.db import build_engine, database_url
from saudi_api.jobs.base import JOB_NAMES, JobName
from saudi_api.jobs.runner import last_finished, run_job
from saudi_api.mcp_server import build_mcp
from saudi_api.settings import Settings, get_settings

_log = logging.getLogger("saudi_api.cli")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="saudi-api", description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)

    commands.add_parser("migrate", help="apply database migrations up to head")

    catalog = commands.add_parser("catalog", help="validate or sync catalog/")
    catalog_commands = catalog.add_subparsers(dest="action", required=True)
    check = catalog_commands.add_parser("check", help="validate every catalogue file")
    check.add_argument("--dir", type=Path, default=None, help="catalogue directory")
    catalog_commands.add_parser("sync", help="write the catalogue's database projection")

    jobs = commands.add_parser("jobs", help="run jobs now")
    jobs_commands = jobs.add_subparsers(dest="action", required=True)
    run = jobs_commands.add_parser("run", help="run one job, or all, once")
    run.add_argument("job", choices=[*JOB_NAMES, "all"])

    commands.add_parser("worker", help="run the jobs on their intervals until stopped")

    serve = commands.add_parser("serve", help="run the API service with uvicorn")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8000)
    serve.add_argument("--workers", type=int, default=1)

    commands.add_parser("mcp-stdio", help="serve the MCP tools over stdio")
    commands.add_parser("openapi", help="print the REST API's OpenAPI document")

    args = parser.parse_args(argv)
    if args.command == "catalog" and args.action == "check":
        return _catalog_check(args.dir or get_settings().catalog_dir)
    if args.command == "openapi":
        print(openapi_json(get_settings()))
        return 0

    settings = get_settings()
    logs.configure(settings.log_level, stderr=args.command == "mcp-stdio")
    match args.command:
        case "migrate":
            return _migrate(settings)
        case "catalog":
            return _catalog_sync(settings)
        case "jobs":
            return _jobs(settings, args.job)
        case "worker":
            return _worker(settings)
        case "serve":
            return _serve(args.host, args.port, args.workers)
        case "mcp-stdio":
            return _mcp_stdio(settings)
    return 2


def _catalog_check(directory: Path) -> int:
    try:
        catalog = load_catalog(directory)
    except CatalogError as error:
        for problem in error.problems:
            print(problem, file=sys.stderr)
        print(f"catalogue invalid: {len(error.problems)} problem(s)", file=sys.stderr)
        return 1
    print(
        f"catalogue valid: {len(catalog.sectors)} sectors, {len(catalog.providers)} providers,"
        f" {len(catalog.apis)} APIs, digest {catalog.digest[:12]}"
    )
    return 0


def _migrate(settings: Settings) -> int:
    root = Path(__file__).resolve().parents[2]
    config = Config(str(root / "alembic.ini"))
    rendered = database_url(settings).render_as_string(hide_password=False)
    # The configuration file interpolates "%"; a URL-encoded password contains it.
    config.set_main_option("sqlalchemy.url", rendered.replace("%", "%%"))
    command.upgrade(config, "head")
    return 0


def _catalog_sync(settings: Settings) -> int:
    try:
        catalog = load_catalog(
            settings.catalog_dir, allow_loopback_http=settings.outbound_allow_loopback_http
        )
    except CatalogError as error:
        for problem in error.problems:
            _log.error("catalogue problem", extra={"problem": problem})
        return 1
    engine = build_engine(settings)
    try:
        with sessionmaker(engine)() as db:
            result = sync_catalog(db, catalog)
    finally:
        engine.dispose()
    _log.info(
        "catalogue synced" if result.changed else "catalogue unchanged",
        extra={
            "digest": result.digest,
            "sectors": result.sectors,
            "providers": result.providers,
            "apis": result.apis,
        },
    )
    return 0


def _jobs(settings: Settings, job: str) -> int:
    engine = build_engine(settings)
    try:
        names: tuple[JobName, ...] = JOB_NAMES if job == "all" else (_job_name(job),)
        failed = [name for name in names if run_job(name, settings, engine).outcome == "failed"]
    finally:
        engine.dispose()
    return 1 if failed else 0


def _job_name(value: str) -> JobName:
    for name in JOB_NAMES:
        if name == value:
            return name
    raise ValueError(value)


def _worker(settings: Settings) -> int:
    """Run each job when its interval has passed since it last finished; stop on SIGTERM
    or SIGINT after the job in progress."""
    intervals: dict[JobName, int] = {
        "discover": settings.discover_interval_seconds,
        "check": settings.check_interval_seconds,
        "refresh-specs": settings.refresh_specs_interval_seconds,
    }
    stopping = threading.Event()

    def stop(_signal: int, _frame: FrameType | None) -> None:
        stopping.set()

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    engine = build_engine(settings)
    _log.info("worker started", extra={"intervals": intervals})
    try:
        while not stopping.is_set():
            finished = last_finished(engine)
            now = datetime.now(UTC)
            waits: list[float] = []
            for name, interval in intervals.items():
                due = finished.get(name, datetime.min.replace(tzinfo=UTC))
                due += timedelta(seconds=interval)
                if due <= now:
                    run_job(name, settings, engine)
                    if stopping.is_set():
                        break
                    waits.append(interval)
                else:
                    waits.append((due - now).total_seconds())
            # Wake at the next due job, and at least once a minute to see other workers' runs.
            stopping.wait(timeout=max(1.0, min([60.0, *waits])))
    finally:
        engine.dispose()
    _log.info("worker stopped")
    return 0


def _serve(host: str, port: int, workers: int) -> int:
    uvicorn.run(
        "saudi_api.api.app:app_from_environment",
        factory=True,
        host=host,
        port=port,
        workers=workers,
        proxy_headers=True,
        # The app logs one line per request without the query string.
        access_log=False,
        log_config=None,
    )
    return 0


def _mcp_stdio(settings: Settings) -> int:
    engine = build_engine(settings)
    try:
        build_mcp(settings, sessionmaker(engine, expire_on_commit=False)).run("stdio")
    finally:
        engine.dispose()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
