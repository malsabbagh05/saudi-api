"""PostgreSQL databases for tests: each test gets its own clone of a migrated template.

`make test-focused` starts the test server and sets `TEST_POSTGRES_DSN`
(tests/README.md). The template's name carries a digest of `alembic.ini` and the
migration sources, so it is built once per set of migrations; each test then clones
it with `CREATE DATABASE ... TEMPLATE` instead of migrating. Databases a process
creates are dropped when it exits.
"""

from __future__ import annotations

import atexit
from collections.abc import Iterator
from contextlib import contextmanager
from hashlib import sha256
import os
from pathlib import Path
import re
from uuid import uuid4

from alembic import command
from alembic.config import Config
from sqlalchemy import Connection, Engine, create_engine, text
from sqlalchemy.engine import URL, make_url
from sqlalchemy.pool import NullPool

_ROOT = Path(__file__).resolve().parents[2]
_ALEMBIC_INI = _ROOT / "alembic.ini"
_TEMPLATE_PREFIX = "test_template_"
# One lock key serializes template builds across processes, worktrees and sessions.
_BUILD_LOCK = "SELECT pg_advisory_lock(hashtext('test-template-build'))"
_BUILD_UNLOCK = "SELECT pg_advisory_unlock(hashtext('test-template-build'))"
_created: list[str] = []


def postgres_dsn() -> URL:
    """The maintenance database of the test server."""
    dsn = os.environ.get("TEST_POSTGRES_DSN")
    if not dsn:
        raise RuntimeError("TEST_POSTGRES_DSN is not set; run tests with make test-focused")
    return make_url(dsn)


def postgres_migrated_database_url(prefix: str) -> URL:
    """A new database at the migration head, cloned from the template."""
    with _maintenance() as connection:
        template = _migrated_template(connection)
        name = _new_database_name(prefix)
        _ = connection.execute(text(f'CREATE DATABASE "{name}" TEMPLATE "{template}"'))
    _created.append(name)
    return postgres_dsn().set(database=name)


def postgres_empty_database_url(prefix: str) -> URL:
    """A new database without any migration, for a test that applies migrations itself."""
    with _maintenance() as connection:
        name = _new_database_name(prefix)
        _ = connection.execute(text(f'CREATE DATABASE "{name}" TEMPLATE template0'))
    _created.append(name)
    return postgres_dsn().set(database=name)


def postgres_engine(prefix: str) -> Engine:
    """An engine on a new migrated database. Dispose it at the end of the test."""
    return create_engine(postgres_migrated_database_url(prefix), poolclass=NullPool)


def migrate(url: URL, revision: str = "heads", *, downgrade: bool = False) -> None:
    """Upgrade or downgrade one database with the repository's Alembic configuration.

    `env.py` must read the database URL from the configuration's `sqlalchemy.url`, as
    the file `alembic init` writes does.
    """
    config = Config(str(_ALEMBIC_INI))
    rendered = url.render_as_string(hide_password=False)
    # The configuration file interpolates "%"; a URL-encoded password contains it.
    config.set_main_option("sqlalchemy.url", rendered.replace("%", "%%"))
    if downgrade:
        command.downgrade(config, revision)
    else:
        command.upgrade(config, revision)


@contextmanager
def _maintenance() -> Iterator[Connection]:
    """An autocommit connection to the maintenance database: CREATE and DROP DATABASE
    cannot run inside a transaction."""
    engine = create_engine(postgres_dsn(), isolation_level="AUTOCOMMIT", poolclass=NullPool)
    try:
        with engine.connect() as connection:
            yield connection
    finally:
        engine.dispose()


def _migrated_template(connection: Connection) -> str:
    name = _TEMPLATE_PREFIX + _migration_digest()[:16]
    _ = connection.execute(text(_BUILD_LOCK))
    try:
        exists = connection.execute(
            text("SELECT 1 FROM pg_database WHERE datname = :name"), {"name": name}
        ).scalar()
        if exists is None:
            # Build under another name and rename at the end, so a build that fails
            # half-way never leaves a half-migrated template under the final name.
            build = f"{name}_build"
            _ = connection.execute(text(f'DROP DATABASE IF EXISTS "{build}" WITH (FORCE)'))
            _ = connection.execute(text(f'CREATE DATABASE "{build}" TEMPLATE template0'))
            if _ALEMBIC_INI.is_file():
                migrate(postgres_dsn().set(database=build))
            # A clone needs a source without sessions; end any the migration left open.
            _ = connection.execute(
                text(
                    "SELECT pg_terminate_backend(pid) FROM pg_stat_activity"
                    + " WHERE datname = :build AND pid <> pg_backend_pid()"
                ),
                {"build": build},
            )
            _ = connection.execute(text(f'ALTER DATABASE "{build}" RENAME TO "{name}"'))
    finally:
        _ = connection.execute(text(_BUILD_UNLOCK))
    return name


def _migration_digest() -> str:
    """A digest of alembic.ini and every file of its script location."""
    digest = sha256()
    if not _ALEMBIC_INI.is_file():
        return digest.hexdigest()
    digest.update(_ALEMBIC_INI.read_bytes())
    location = Config(str(_ALEMBIC_INI)).get_main_option("script_location")
    if location:
        directory = Path(location) if Path(location).is_absolute() else _ROOT / location
        for path in sorted(directory.rglob("*")):
            if path.is_file() and "__pycache__" not in path.parts:
                digest.update(path.relative_to(directory).as_posix().encode())
                digest.update(path.read_bytes())
    return digest.hexdigest()


def _new_database_name(prefix: str) -> str:
    safe = re.sub(r"[^a-z0-9_]", "_", prefix.lower())[:32]
    return f"test_{safe}_{uuid4().hex[:12]}"


@atexit.register
def _drop_created_databases() -> None:
    if not _created:
        return
    with _maintenance() as connection:
        for name in _created:
            _ = connection.execute(text(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)'))
