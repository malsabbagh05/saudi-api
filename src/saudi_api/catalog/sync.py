"""Write the database projection of the curated catalogue (ADR-002).

`sync_catalog` is the only writer of `catalog_state`, `sectors`, `providers`, `apis` and
`api_sectors`. It runs in one transaction under a transaction-level advisory lock, so
two syncs never interleave, and an unchanged digest writes nothing.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import delete, select, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from saudi_api.catalog.loader import Catalog
from saudi_api.models import ApiRow, ApiSectorRow, CatalogState, ProviderRow, SectorRow

_LOCK = text("SELECT pg_advisory_xact_lock(hashtext('catalog-sync'))")


@dataclass(frozen=True)
class SyncResult:
    changed: bool
    digest: str
    sectors: int
    providers: int
    apis: int


def projected_digest(db: Session) -> str | None:
    return db.scalar(select(CatalogState.digest).where(CatalogState.id == 1))


def sync_catalog(db: Session, catalog: Catalog) -> SyncResult:
    """Make the projection equal the catalogue, then commit."""
    _ = db.execute(_LOCK)
    counts = (len(catalog.sectors), len(catalog.providers), len(catalog.apis))
    if projected_digest(db) == catalog.digest:
        db.rollback()
        return SyncResult(False, catalog.digest, *counts)

    now = datetime.now(UTC)
    sector_slugs = [s.slug for s in catalog.sectors]
    provider_slugs = [p.slug for p in catalog.providers]
    api_slugs = [a.slug for a in catalog.apis]

    # Removed entries go first; foreign keys cascade to their dependent rows.
    _ = db.execute(delete(ApiRow).where(ApiRow.slug.not_in(api_slugs)))
    _ = db.execute(delete(ProviderRow).where(ProviderRow.slug.not_in(provider_slugs)))
    _ = db.execute(delete(SectorRow).where(SectorRow.slug.not_in(sector_slugs)))

    if catalog.sectors:
        rows = [
            {
                "slug": s.slug,
                "name_en": s.name.en,
                "name_ar": s.name.ar,
                "description_en": s.description.en,
                "description_ar": s.description.ar,
                "position": position,
            }
            for position, s in enumerate(catalog.sectors)
        ]
        statement = insert(SectorRow).values(rows)
        _ = db.execute(
            statement.on_conflict_do_update(
                index_elements=[SectorRow.slug],
                set_={c: statement.excluded[c] for c in rows[0] if c != "slug"},
            )
        )

    providers = {p.slug: p for p in catalog.providers}
    if catalog.providers:
        rows = [
            {
                "slug": p.slug,
                "name_en": p.name.en,
                "name_ar": p.name.ar,
                "kind": p.kind.value,
                "entry": p.model_dump(mode="json", by_alias=True),
            }
            for p in catalog.providers
        ]
        statement = insert(ProviderRow).values(rows)
        _ = db.execute(
            statement.on_conflict_do_update(
                index_elements=[ProviderRow.slug],
                set_={c: statement.excluded[c] for c in rows[0] if c != "slug"},
            )
        )

    if catalog.apis:
        rows = []
        for api in catalog.apis:
            provider = providers[api.provider]
            rows.append(
                {
                    "slug": api.slug,
                    "provider_slug": api.provider,
                    "name_en": api.name.en,
                    "name_ar": api.name.ar,
                    "summary_en": api.summary.en,
                    "summary_ar": api.summary.ar,
                    "provider_name_en": provider.name.en,
                    "provider_name_ar": provider.name.ar,
                    "keywords": " ".join(api.tags),
                    "status": api.status.value,
                    "access_level": api.access.level.value,
                    "auth": [scheme.value for scheme in api.access.auth],
                    "pricing": api.access.pricing.value,
                    "agent_invocation": api.usage.agent_invocation.value == "allowed",
                    "entry": api.model_dump(mode="json", by_alias=True),
                }
            )
        statement = insert(ApiRow).values(rows)
        _ = db.execute(
            statement.on_conflict_do_update(
                index_elements=[ApiRow.slug],
                set_={c: statement.excluded[c] for c in rows[0] if c != "slug"},
            )
        )
        _ = db.execute(delete(ApiSectorRow))
        _ = db.execute(
            insert(ApiSectorRow).values(
                [
                    {"api_slug": api.slug, "sector_slug": sector}
                    for api in catalog.apis
                    for sector in api.sectors
                ]
            )
        )

    state = insert(CatalogState).values(id=1, digest=catalog.digest, synced_at=now)
    _ = db.execute(
        state.on_conflict_do_update(
            index_elements=[CatalogState.id],
            set_={"digest": state.excluded.digest, "synced_at": state.excluded.synced_at},
        )
    )
    db.commit()
    return SyncResult(True, catalog.digest, *counts)
