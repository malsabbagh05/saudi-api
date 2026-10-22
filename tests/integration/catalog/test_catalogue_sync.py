"""The database projection of the catalogue (ADR-002), on the real server."""

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from saudi_api.catalog.loader import load_catalog
from saudi_api.models import ApiRow, ApiSectorRow, CatalogState, ProviderRow
from tests.support.catalog import (
    REPOSITORY_CATALOG,
    api_entry,
    copy_repository_catalog,
    new_catalog,
    sync,
    write_api,
)
from tests.support.postgres import postgres_engine


def test_sync_projects_the_repository_catalogue_and_a_second_sync_writes_nothing():
    engine = postgres_engine("sync_repo")
    try:
        catalog = load_catalog(REPOSITORY_CATALOG)
        first = sync(engine, REPOSITORY_CATALOG)
        with engine.connect() as db:
            synced_at = db.scalar(select(CatalogState.synced_at))
        second = sync(engine, REPOSITORY_CATALOG)
        with engine.connect() as db:
            assert db.scalar(select(func.count()).select_from(ApiRow)) == len(catalog.apis)
            assert db.scalar(select(func.count()).select_from(ProviderRow)) == len(
                catalog.providers
            )
            assert db.scalar(select(CatalogState.digest)) == catalog.digest
            assert db.scalar(select(CatalogState.synced_at)) == synced_at
        assert first.changed and not second.changed
    finally:
        engine.dispose()


def test_removing_an_entry_removes_its_rows_on_the_next_sync(tmp_path):
    engine = postgres_engine("sync_remove")
    try:
        directory = copy_repository_catalog(tmp_path)
        sync(engine, directory)
        (directory / "apis" / "taqnyat-messaging.yaml").unlink()
        (directory / "providers" / "taqnyat.yaml").unlink()
        result = sync(engine, directory)
        with Session(engine) as db:
            assert db.get(ApiRow, "taqnyat-messaging") is None
            assert db.get(ProviderRow, "taqnyat") is None
            orphans = db.scalar(
                select(func.count())
                .select_from(ApiSectorRow)
                .where(ApiSectorRow.api_slug == "taqnyat-messaging")
            )
            assert orphans == 0
        assert result.changed
    finally:
        engine.dispose()


def test_a_changed_entry_updates_its_row_and_search_columns(tmp_path):
    engine = postgres_engine("sync_update")
    try:
        directory = new_catalog(tmp_path)
        write_api(directory, api_entry("weather", name={"en": "Weather", "ar": "الطقس"}))
        sync(engine, directory)
        write_api(directory, api_entry("weather", name={"en": "Climate", "ar": "المناخ"}))
        sync(engine, directory)
        with engine.connect() as db:
            row = db.execute(
                text("SELECT name_en, search_text FROM apis WHERE slug = 'weather'")
            ).one()
        assert row.name_en == "Climate"
        assert "climate" in row.search_text and "weather" not in row.search_text
    finally:
        engine.dispose()
