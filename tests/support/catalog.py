"""Catalogue directories, settings and synced databases for tests.

A test writes catalogue files the way a contributor does and syncs them through the real
`sync_catalog`; nothing writes the projected tables directly (ADR-002).
"""

from __future__ import annotations

import shutil
from pathlib import Path

import yaml
from sqlalchemy import Engine
from sqlalchemy.engine import URL
from sqlalchemy.orm import sessionmaker

from saudi_api.catalog.loader import load_catalog
from saudi_api.catalog.sync import SyncResult, sync_catalog
from saudi_api.settings import Settings

REPOSITORY_CATALOG = Path(__file__).resolve().parents[2] / "catalog"


def copy_repository_catalog(target: Path) -> Path:
    """A copy of the repository's catalogue that a test may change."""
    directory = target / "catalog"
    shutil.copytree(REPOSITORY_CATALOG, directory)
    return directory


def settings_for(url: URL, catalog_dir: Path = REPOSITORY_CATALOG, **overrides: object) -> Settings:
    values: dict[str, object] = {
        "environment": "test",
        "database_url": url.render_as_string(hide_password=False),
        "catalog_dir": catalog_dir,
        "outbound_allow_loopback_http": True,
        "check_region": "test",
        "public_base_url": "http://testserver",
    }
    values.update(overrides)
    return Settings.model_validate(values)


def sync(engine: Engine, directory: Path) -> SyncResult:
    with sessionmaker(engine)() as db:
        return sync_catalog(db, load_catalog(directory, allow_loopback_http=True))


def write_provider(directory: Path, slug: str = "test-provider") -> None:
    document = {
        "slug": slug,
        "name": {"en": "Test Provider", "ar": "جهة اختبار"},
        "kind": "government",
        "website_url": "https://provider.example",
        "description": {"en": "A provider for tests.", "ar": "جهة لأغراض الاختبار."},
    }
    _write(directory / "providers" / f"{slug}.yaml", document)


def api_entry(
    slug: str, *, provider: str = "test-provider", **overrides: object
) -> dict[str, object]:
    """A valid API entry; overrides replace top-level fields."""
    document: dict[str, object] = {
        "slug": slug,
        "provider": provider,
        "name": {"en": f"Test API {slug}", "ar": "واجهة اختبار"},
        "summary": {"en": "A test API.", "ar": "واجهة لأغراض الاختبار."},
        "description": {
            "en": "A test API used by the test suite.",
            "ar": "واجهة يستخدمها الاختبار.",
        },
        "sectors": ["statistics"],
        "documentation_url": "https://provider.example/docs",
        "access": {"level": "open", "auth": ["none"], "pricing": "free"},
        "verification": {
            "checked_on": "2026-10-22",
            "method": "official_documentation",
            "evidence": ["https://provider.example/docs"],
        },
    }
    document.update(overrides)
    return document


def write_api(directory: Path, document: dict[str, object]) -> None:
    _write(directory / "apis" / f"{document['slug']}.yaml", document)


def write_sectors(directory: Path) -> None:
    document = {
        "sectors": [
            {
                "slug": "statistics",
                "name": {"en": "Statistics", "ar": "الإحصاءات"},
                "description": {"en": "Official statistics.", "ar": "الإحصاءات الرسمية."},
            }
        ]
    }
    _write(directory / "sectors.yaml", document)


def new_catalog(target: Path) -> Path:
    """An empty catalogue directory with one sector and one provider."""
    directory = target / "catalog"
    write_sectors(directory)
    write_provider(directory)
    return directory


def _write(path: Path, document: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(document, allow_unicode=True, sort_keys=False), encoding="utf-8")
