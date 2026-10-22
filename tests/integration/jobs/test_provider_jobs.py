"""Discovery, reachability checks and specification refresh through the real runner, the
real database and a provider server on 127.0.0.1.

datasaudi_cubes_en.json and datasaudi_cubes_ar.json are the authentic DataSaudi index,
recorded on 2026-10-22 with `curl 'https://api.datasaudi.sa/tesseract/cubes?locale=en'`
(and `locale=ar`) and trimmed to two public cubes and one the provider hides.
"""

import json
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from saudi_api.jobs.runner import run_job
from saudi_api.models import ApiCheckRow, ApiSpecRow, DatasetRow, JobRunRow
from tests.support.catalog import api_entry, new_catalog, settings_for, sync, write_api
from tests.support.http_server import Route, provider_server
from tests.support.postgres import postgres_engine

HERE = Path(__file__).parent
CUBES_EN = (HERE / "datasaudi_cubes_en.json").read_bytes()
CUBES_AR = (HERE / "datasaudi_cubes_ar.json").read_bytes()
JSON = {"Content-Type": "application/json"}


def tesseract_entry(base: str) -> dict[str, object]:
    return api_entry(
        "stats",
        documentation_url=f"{base}/docs",
        base_urls=[{"url": f"{base}/tesseract"}],
        discovery={"kind": "tesseract_cubes", "base_url": f"{base}/tesseract"},
    )


def test_discovery_reads_the_index_in_both_languages_and_skips_hidden_cubes(tmp_path):
    engine = postgres_engine("discover")
    url = engine.url
    routes = {
        "/tesseract/cubes?locale=en": Route(body=CUBES_EN, headers=JSON),
        "/tesseract/cubes?locale=ar": Route(body=CUBES_AR, headers=JSON),
    }
    try:
        with provider_server(routes) as server:
            directory = new_catalog(tmp_path)
            write_api(directory, tesseract_entry(server.url))
            sync(engine, directory)
            result = run_job("discover", settings_for(url, directory), engine)
        assert result.outcome == "succeeded"
        assert result.summary == {"stats": {"outcome": "succeeded", "datasets": 2, "removed": 0}}
        with Session(engine) as db:
            wages = db.get(DatasetRow, ("stats", "avg_monthly_wages_per_paid_employee"))
            assert wages is not None
            assert wages.publisher_en == "Labour Market Statistics (GASTAT)"
            assert "​" not in wages.name_ar  # the provider's zero-width spaces are stripped
            assert wages.name_ar.startswith("متوسط الأجور الشهرية")
            dimensions = {d["name"]: d for d in wages.dimensions}
            assert dimensions["Quarter"]["required"] is True
            assert db.get(DatasetRow, ("stats", "dim_countries")) is None
            run = db.get(JobRunRow, "discover")
            assert run is not None and run.outcome == "succeeded"
    finally:
        engine.dispose()


def test_a_cube_the_index_drops_is_deleted_and_a_failed_read_keeps_the_rest(tmp_path):
    engine = postgres_engine("discover_drop")
    url = engine.url
    full = {
        "/tesseract/cubes?locale=en": Route(body=CUBES_EN, headers=JSON),
        "/tesseract/cubes?locale=ar": Route(body=CUBES_AR, headers=JSON),
    }
    try:
        with provider_server(full) as server:
            directory = new_catalog(tmp_path)
            write_api(directory, tesseract_entry(server.url))
            sync(engine, directory)
            settings = settings_for(url, directory)
            run_job("discover", settings, engine)
            index = json.loads(CUBES_EN)
            index["cubes"] = [c for c in index["cubes"] if c["name"] != "gastat_inflation"]
            full["/tesseract/cubes?locale=en"] = Route(
                body=json.dumps(index).encode(), headers=JSON
            )
            dropped = run_job("discover", settings, engine)
            full["/tesseract/cubes?locale=en"] = Route(status=503)
            failed = run_job("discover", settings, engine)
        assert dropped.summary == {"stats": {"outcome": "succeeded", "datasets": 1, "removed": 1}}
        assert failed.summary == {"stats": {"outcome": "http_error", "http_status": 503}}
        with Session(engine) as db:
            remaining = db.scalars(select(DatasetRow.external_id)).all()
        assert remaining == ["avg_monthly_wages_per_paid_employee"]
    finally:
        engine.dispose()


def test_checks_record_each_outcome_and_count_consecutive_failures(tmp_path):
    engine = postgres_engine("checks")
    url = engine.url
    routes = {"/up": Route(body=b"ok"), "/down": Route(status=500)}
    try:
        with provider_server(routes) as server:
            directory = new_catalog(tmp_path)
            write_api(directory, api_entry("up", documentation_url=f"{server.url}/up"))
            write_api(directory, api_entry("down", documentation_url=f"{server.url}/down"))
            sync(engine, directory)
            settings = settings_for(url, directory)
            run_job("check", settings, engine)
            second = run_job("check", settings, engine)
        assert second.summary == {"checked": 2, "reachable": 1, "http_error": 1}
        with Session(engine) as db:
            up = db.get(ApiCheckRow, "up")
            down = db.get(ApiCheckRow, "down")
            assert up is not None and up.outcome == "reachable" and up.consecutive_failures == 0
            assert up.last_success_at is not None and up.region == "test"
            assert down is not None and down.outcome == "http_error" and down.http_status == 500
            assert down.consecutive_failures == 2 and down.last_success_at is None
    finally:
        engine.dispose()


def test_spec_refresh_stores_operations_skips_unchanged_and_follows_robots(tmp_path):
    engine = postgres_engine("specs")
    url = engine.url
    spec = (
        b"swagger: '2.0'\ninfo: {title: Test, version: '1'}\npaths:\n"
        b"  /items/{id}:\n    get: {summary: One item}\n  /items:\n    post: {operationId: create}\n"
    )
    routes = {
        "/spec.yaml": Route(body=spec),
        "/broken.yaml": Route(body=b"not: [an, openapi, document]"),
        "/robots.txt": Route(body=b"User-agent: *\nDisallow: /private\n"),
        "/private/spec.yaml": Route(body=spec),
    }
    try:
        with provider_server(routes) as server:
            directory = new_catalog(tmp_path)
            for slug, path in (
                ("good", "/spec.yaml"),
                ("broken", "/broken.yaml"),
                ("blocked", "/private/spec.yaml"),
            ):
                write_api(
                    directory,
                    api_entry(
                        slug,
                        documentation_url=f"{server.url}/docs",
                        openapi_url=f"{server.url}{path}",
                    ),
                )
            sync(engine, directory)
            settings = settings_for(url, directory)
            first = run_job("refresh-specs", settings, engine)
            second = run_job("refresh-specs", settings, engine)
            assert "/private/spec.yaml" not in server.requests
        assert first.summary == {"fetched": 1, "invalid_document": 1, "disallowed_by_robots": 1}
        assert second.summary == {"unchanged": 1, "invalid_document": 1, "disallowed_by_robots": 1}
        with Session(engine) as db:
            good = db.get(ApiSpecRow, "good")
            assert good is not None and good.spec_version == "2.0" and good.title == "Test"
            assert good.operations == [
                {"method": "GET", "path": "/items/{id}", "summary": "One item"},
                {"method": "POST", "path": "/items", "summary": "create"},
            ]
            assert db.scalar(select(func.count()).select_from(ApiSpecRow)) == 3
    finally:
        engine.dispose()
