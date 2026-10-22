"""The catalogue schema migration applies, reverts to an empty schema and applies again."""

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.pool import NullPool

from tests.support.postgres import migrate, postgres_empty_database_url

TABLES = {
    "catalog_state",
    "sectors",
    "providers",
    "apis",
    "api_sectors",
    "datasets",
    "api_checks",
    "api_specs",
    "job_runs",
}


def test_the_migration_round_trips():
    url = postgres_empty_database_url("migration")
    migrate(url, "head")
    migrate(url, "base", downgrade=True)
    engine = create_engine(url, poolclass=NullPool)
    try:
        with engine.connect() as db:
            assert TABLES.isdisjoint(inspect(db).get_table_names())
            assert db.scalar(text("SELECT to_regproc('catalog_fold')")) is None
        migrate(url, "head")
        with engine.connect() as db:
            assert TABLES <= set(inspect(db).get_table_names())
            folded = db.scalar(text("SELECT catalog_fold('الإِحْصَاءُ Riyadh')"))
            assert folded == "الاحصاء riyadh"
            indexes = {i["name"] for i in inspect(db).get_indexes("apis")}
            assert {"apis_search_vector", "apis_search_text"} <= indexes
    finally:
        engine.dispose()
