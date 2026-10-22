"""Catalogue projection, datasets, observations and bilingual search (ADR-002, ADR-003).

Revision ID: 20261022_0001
Revises:
Create Date: 2026-10-22
"""

from collections.abc import Sequence
from datetime import datetime

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20261022_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Lowercase, drop Arabic diacritics (U+064B-U+065F, U+0670) and tatweel (U+0640), then
# fold alef forms to ا, taa marbuta to ه and alef maqsura to ي (ADR-003).
_FOLD = """
CREATE FUNCTION catalog_fold(value text) RETURNS text
LANGUAGE sql IMMUTABLE PARALLEL SAFE STRICT
RETURN translate(
    regexp_replace(lower(value), '[\\u064B-\\u065F\\u0670\\u0640]', '', 'g'),
    'أإآٱةى',
    'ااااهي'
)
"""

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


def _timestamp(name: str, *, nullable: bool = False) -> sa.Column[datetime]:
    return sa.Column(name, sa.DateTime(timezone=True), nullable=nullable)


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.execute(_FOLD)

    op.create_table(
        "catalog_state",
        sa.Column("id", sa.SmallInteger, primary_key=True, autoincrement=False),
        sa.Column("digest", sa.Text, nullable=False),
        _timestamp("synced_at"),
        sa.CheckConstraint("id = 1", name="catalog_state_single_row"),
    )
    op.create_table(
        "sectors",
        sa.Column("slug", sa.Text, primary_key=True),
        sa.Column("name_en", sa.Text, nullable=False),
        sa.Column("name_ar", sa.Text, nullable=False),
        sa.Column("description_en", sa.Text, nullable=False),
        sa.Column("description_ar", sa.Text, nullable=False),
        sa.Column("position", sa.Integer, nullable=False),
    )
    op.create_table(
        "providers",
        sa.Column("slug", sa.Text, primary_key=True),
        sa.Column("name_en", sa.Text, nullable=False),
        sa.Column("name_ar", sa.Text, nullable=False),
        sa.Column("kind", sa.Text, nullable=False),
        sa.Column("entry", postgresql.JSONB, nullable=False),
    )
    op.create_table(
        "apis",
        sa.Column("slug", sa.Text, primary_key=True),
        sa.Column(
            "provider_slug",
            sa.Text,
            sa.ForeignKey("providers.slug", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name_en", sa.Text, nullable=False),
        sa.Column("name_ar", sa.Text, nullable=False),
        sa.Column("summary_en", sa.Text, nullable=False),
        sa.Column("summary_ar", sa.Text, nullable=False),
        sa.Column("provider_name_en", sa.Text, nullable=False),
        sa.Column("provider_name_ar", sa.Text, nullable=False),
        sa.Column("keywords", sa.Text, nullable=False),
        sa.Column("status", sa.Text, nullable=False),
        sa.Column("access_level", sa.Text, nullable=False),
        sa.Column("auth", postgresql.ARRAY(sa.Text), nullable=False),
        sa.Column("pricing", sa.Text, nullable=False),
        sa.Column("agent_invocation", sa.Boolean, nullable=False),
        sa.Column("entry", postgresql.JSONB, nullable=False),
        sa.Column("search_vector", postgresql.TSVECTOR, sa.Computed(_API_VECTOR, persisted=True)),
        sa.Column("search_text", sa.Text, sa.Computed(_API_TEXT, persisted=True)),
    )
    op.create_index("apis_provider_slug", "apis", ["provider_slug"])
    op.create_index("apis_search_vector", "apis", ["search_vector"], postgresql_using="gin")
    op.create_index(
        "apis_search_text",
        "apis",
        ["search_text"],
        postgresql_using="gin",
        postgresql_ops={"search_text": "gin_trgm_ops"},
    )
    op.create_table(
        "api_sectors",
        sa.Column(
            "api_slug",
            sa.Text,
            sa.ForeignKey("apis.slug", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "sector_slug",
            sa.Text,
            sa.ForeignKey("sectors.slug", ondelete="CASCADE"),
            primary_key=True,
        ),
    )
    op.create_index("api_sectors_sector_slug", "api_sectors", ["sector_slug"])

    op.create_table(
        "datasets",
        sa.Column(
            "api_slug",
            sa.Text,
            sa.ForeignKey("apis.slug", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("external_id", sa.Text, primary_key=True),
        sa.Column("name_en", sa.Text, nullable=False),
        sa.Column("name_ar", sa.Text, nullable=False),
        sa.Column("topic_en", sa.Text, nullable=False),
        sa.Column("topic_ar", sa.Text, nullable=False),
        sa.Column("subtopic_en", sa.Text, nullable=False),
        sa.Column("subtopic_ar", sa.Text, nullable=False),
        sa.Column("publisher_en", sa.Text, nullable=False),
        sa.Column("publisher_ar", sa.Text, nullable=False),
        sa.Column("publisher_url", sa.Text),
        sa.Column("measures", postgresql.JSONB, nullable=False),
        sa.Column("dimensions", postgresql.JSONB, nullable=False),
        _timestamp("refreshed_at"),
        sa.Column(
            "search_vector", postgresql.TSVECTOR, sa.Computed(_DATASET_VECTOR, persisted=True)
        ),
        sa.Column("search_text", sa.Text, sa.Computed(_DATASET_TEXT, persisted=True)),
    )
    op.create_index("datasets_search_vector", "datasets", ["search_vector"], postgresql_using="gin")
    op.create_index(
        "datasets_search_text",
        "datasets",
        ["search_text"],
        postgresql_using="gin",
        postgresql_ops={"search_text": "gin_trgm_ops"},
    )

    op.create_table(
        "api_checks",
        sa.Column(
            "api_slug",
            sa.Text,
            sa.ForeignKey("apis.slug", ondelete="CASCADE"),
            primary_key=True,
        ),
        _timestamp("checked_at"),
        sa.Column("outcome", sa.Text, nullable=False),
        sa.Column("http_status", sa.Integer),
        sa.Column("latency_ms", sa.Integer),
        sa.Column("consecutive_failures", sa.Integer, nullable=False),
        _timestamp("last_success_at", nullable=True),
        sa.Column("region", sa.Text, nullable=False),
        sa.CheckConstraint(
            "outcome IN ('reachable', 'http_error', 'timeout', 'connection_error',"
            " 'tls_error', 'refused_by_policy')",
            name="api_checks_outcome",
        ),
    )
    op.create_table(
        "api_specs",
        sa.Column(
            "api_slug",
            sa.Text,
            sa.ForeignKey("apis.slug", ondelete="CASCADE"),
            primary_key=True,
        ),
        _timestamp("checked_at"),
        sa.Column("outcome", sa.Text, nullable=False),
        _timestamp("fetched_at", nullable=True),
        sa.Column("source_url", sa.Text, nullable=False),
        sa.Column("sha256", sa.Text),
        sa.Column("spec_version", sa.Text),
        sa.Column("title", sa.Text),
        sa.Column("operations", postgresql.JSONB),
        sa.Column("document", postgresql.JSONB),
        sa.CheckConstraint(
            "outcome IN ('fetched', 'unchanged', 'disallowed_by_robots', 'http_error',"
            " 'timeout', 'connection_error', 'tls_error', 'refused_by_policy',"
            " 'too_large', 'invalid_document')",
            name="api_specs_outcome",
        ),
    )
    op.create_table(
        "job_runs",
        sa.Column("job", sa.Text, primary_key=True),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=False),
        _timestamp("started_at"),
        _timestamp("finished_at", nullable=True),
        sa.Column("outcome", sa.Text, nullable=False),
        sa.Column("summary", postgresql.JSONB, nullable=False),
        sa.CheckConstraint(
            "outcome IN ('running', 'succeeded', 'failed')", name="job_runs_outcome"
        ),
    )


def downgrade() -> None:
    for table in (
        "job_runs",
        "api_specs",
        "api_checks",
        "datasets",
        "api_sectors",
        "apis",
        "providers",
        "sectors",
        "catalog_state",
    ):
        op.drop_table(table)
    op.execute("DROP FUNCTION catalog_fold(text)")
