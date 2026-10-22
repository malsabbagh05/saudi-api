"""The test database contract that tests/README.md states, checked on the real server."""

from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import text

from tests.support.postgres import postgres_engine


def test_each_test_gets_its_own_database():
    first, second = postgres_engine("first"), postgres_engine("second")
    try:
        with first.begin() as connection:
            connection.execute(text("CREATE TABLE written_by_first (id integer)"))
            first_name = connection.execute(text("SELECT current_database()")).scalar()
        with second.connect() as connection:
            second_name = connection.execute(text("SELECT current_database()")).scalar()
            leaked = connection.execute(text("SELECT to_regclass('written_by_first')")).scalar()
        assert first_name != second_name
        assert leaked is None
    finally:
        first.dispose()
        second.dispose()


def test_a_new_database_is_at_the_migration_head():
    heads = set(ScriptDirectory.from_config(Config("alembic.ini")).get_heads())
    engine = postgres_engine("head")
    try:
        with engine.connect() as connection:
            assert set(MigrationContext.configure(connection).get_current_heads()) == heads
    finally:
        engine.dispose()
