"""Mapped tables. Alembic owns the schema (`migrations/`); these classes only read and
write it. The `catalog_*`, `sectors`, `providers`, `apis` and `api_sectors` tables are the
projection of `catalog/`, written only by `catalog.sync` (ADR-002).
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Computed,
    DateTime,
    ForeignKey,
    Integer,
    SmallInteger,
    Text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, TSVECTOR, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from saudi_api.json_types import JsonObject, JsonValue


class Base(DeclarativeBase):
    type_annotation_map = {  # noqa: RUF012 - SQLAlchemy reads this class attribute
        datetime: DateTime(timezone=True),
        JsonObject: JSONB,
        JsonValue: JSONB,
    }


# The generated search columns; the migration that creates them is the authority, and
# these expressions repeat it only so SQLAlchemy never writes them.
_API_VECTOR = (
    "setweight(to_tsvector('english'::regconfig, name_en), 'A')"
    " || setweight(to_tsvector('arabic'::regconfig, name_ar), 'A')"
    " || setweight(to_tsvector('simple'::regconfig, name_en || ' ' || name_ar), 'A')"
    " || setweight(to_tsvector('english'::regconfig, keywords || ' ' || provider_name_en), 'B')"
    " || setweight(to_tsvector('arabic'::regconfig, provider_name_ar), 'B')"
    " || setweight(to_tsvector('simple'::regconfig, keywords), 'B')"
    " || setweight(to_tsvector('english'::regconfig, summary_en), 'C')"
    " || setweight(to_tsvector('arabic'::regconfig, summary_ar), 'C')"
)
_API_TEXT = (
    "catalog_fold(name_en || ' ' || name_ar || ' ' || keywords || ' '"
    " || provider_name_en || ' ' || provider_name_ar)"
)
_DATASET_VECTOR = (
    "setweight(to_tsvector('english'::regconfig, name_en), 'A')"
    " || setweight(to_tsvector('arabic'::regconfig, name_ar), 'A')"
    " || setweight(to_tsvector('simple'::regconfig, name_en || ' ' || name_ar), 'A')"
    " || setweight(to_tsvector('english'::regconfig, topic_en || ' ' || subtopic_en"
    " || ' ' || publisher_en), 'B')"
    " || setweight(to_tsvector('arabic'::regconfig, topic_ar || ' ' || subtopic_ar"
    " || ' ' || publisher_ar), 'B')"
)
_DATASET_TEXT = (
    "catalog_fold(name_en || ' ' || name_ar || ' ' || topic_en || ' ' || topic_ar"
    " || ' ' || subtopic_en || ' ' || subtopic_ar || ' ' || publisher_en || ' ' || publisher_ar)"
)


class CatalogState(Base):
    __tablename__ = "catalog_state"

    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    digest: Mapped[str] = mapped_column(Text)
    synced_at: Mapped[datetime]


class SectorRow(Base):
    __tablename__ = "sectors"

    slug: Mapped[str] = mapped_column(Text, primary_key=True)
    name_en: Mapped[str] = mapped_column(Text)
    name_ar: Mapped[str] = mapped_column(Text)
    description_en: Mapped[str] = mapped_column(Text)
    description_ar: Mapped[str] = mapped_column(Text)
    position: Mapped[int] = mapped_column(Integer)


class ProviderRow(Base):
    __tablename__ = "providers"

    slug: Mapped[str] = mapped_column(Text, primary_key=True)
    name_en: Mapped[str] = mapped_column(Text)
    name_ar: Mapped[str] = mapped_column(Text)
    kind: Mapped[str] = mapped_column(Text)
    entry: Mapped[JsonObject]


class ApiRow(Base):
    __tablename__ = "apis"

    slug: Mapped[str] = mapped_column(Text, primary_key=True)
    provider_slug: Mapped[str] = mapped_column(
        Text, ForeignKey("providers.slug", ondelete="CASCADE")
    )
    name_en: Mapped[str] = mapped_column(Text)
    name_ar: Mapped[str] = mapped_column(Text)
    summary_en: Mapped[str] = mapped_column(Text)
    summary_ar: Mapped[str] = mapped_column(Text)
    provider_name_en: Mapped[str] = mapped_column(Text)
    provider_name_ar: Mapped[str] = mapped_column(Text)
    keywords: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text)
    access_level: Mapped[str] = mapped_column(Text)
    auth: Mapped[list[str]] = mapped_column(ARRAY(Text))
    pricing: Mapped[str] = mapped_column(Text)
    agent_invocation: Mapped[bool] = mapped_column(Boolean)
    entry: Mapped[JsonObject]
    search_vector: Mapped[str] = mapped_column(TSVECTOR, Computed(_API_VECTOR, persisted=True))
    search_text: Mapped[str] = mapped_column(Text, Computed(_API_TEXT, persisted=True))


class ApiSectorRow(Base):
    __tablename__ = "api_sectors"

    api_slug: Mapped[str] = mapped_column(
        Text, ForeignKey("apis.slug", ondelete="CASCADE"), primary_key=True
    )
    sector_slug: Mapped[str] = mapped_column(
        Text, ForeignKey("sectors.slug", ondelete="CASCADE"), primary_key=True
    )


class DatasetRow(Base):
    __tablename__ = "datasets"

    api_slug: Mapped[str] = mapped_column(
        Text, ForeignKey("apis.slug", ondelete="CASCADE"), primary_key=True
    )
    external_id: Mapped[str] = mapped_column(Text, primary_key=True)
    name_en: Mapped[str] = mapped_column(Text)
    name_ar: Mapped[str] = mapped_column(Text)
    topic_en: Mapped[str] = mapped_column(Text)
    topic_ar: Mapped[str] = mapped_column(Text)
    subtopic_en: Mapped[str] = mapped_column(Text)
    subtopic_ar: Mapped[str] = mapped_column(Text)
    publisher_en: Mapped[str] = mapped_column(Text)
    publisher_ar: Mapped[str] = mapped_column(Text)
    publisher_url: Mapped[str | None] = mapped_column(Text)
    measures: Mapped[JsonValue]
    dimensions: Mapped[JsonValue]
    refreshed_at: Mapped[datetime]
    search_vector: Mapped[str] = mapped_column(TSVECTOR, Computed(_DATASET_VECTOR, persisted=True))
    search_text: Mapped[str] = mapped_column(Text, Computed(_DATASET_TEXT, persisted=True))


class ApiCheckRow(Base):
    __tablename__ = "api_checks"

    api_slug: Mapped[str] = mapped_column(
        Text, ForeignKey("apis.slug", ondelete="CASCADE"), primary_key=True
    )
    checked_at: Mapped[datetime]
    outcome: Mapped[str] = mapped_column(Text)
    http_status: Mapped[int | None] = mapped_column(Integer)
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    consecutive_failures: Mapped[int] = mapped_column(Integer)
    last_success_at: Mapped[datetime | None]
    region: Mapped[str] = mapped_column(Text)


class ApiSpecRow(Base):
    __tablename__ = "api_specs"

    api_slug: Mapped[str] = mapped_column(
        Text, ForeignKey("apis.slug", ondelete="CASCADE"), primary_key=True
    )
    checked_at: Mapped[datetime]
    outcome: Mapped[str] = mapped_column(Text)
    fetched_at: Mapped[datetime | None]
    source_url: Mapped[str] = mapped_column(Text)
    sha256: Mapped[str | None] = mapped_column(Text)
    spec_version: Mapped[str | None] = mapped_column(Text)
    title: Mapped[str | None] = mapped_column(Text)
    operations: Mapped[JsonValue | None]
    document: Mapped[JsonObject | None]


class JobRunRow(Base):
    __tablename__ = "job_runs"

    job: Mapped[str] = mapped_column(Text, primary_key=True)
    run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    started_at: Mapped[datetime]
    finished_at: Mapped[datetime | None]
    outcome: Mapped[str] = mapped_column(Text)
    summary: Mapped[JsonObject]
