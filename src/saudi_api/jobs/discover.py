"""Discovery: read each discovery-enabled API's dataset index into `datasets` (ADR-002).

The `tesseract_cubes` source reads a Tesseract OLAP server's `/cubes` index in English and
Arabic (DataSaudi: `https://api.datasaudi.sa/tesseract/cubes?locale=en`). The payload is
validated at this boundary. A run replaces the source's datasets: it upserts what the
index lists and deletes what it no longer lists. When the index cannot be read, the
stored datasets stay as they are, with their `refreshed_at`.
"""

from __future__ import annotations

import json
import logging
import re
from datetime import UTC, datetime
from typing import Annotated
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, ValidationError
from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert

from saudi_api.catalog.schema import Api, entry_context, DiscoveryKind
from saudi_api.jobs.base import JobContext
from saudi_api.json_types import JsonObject, JsonValue
from saudi_api.models import ApiRow, DatasetRow
from saudi_api.outbound import DEFAULT_REQUESTS_PER_MINUTE, OutboundFailed, OutboundRefused

_log = logging.getLogger(__name__)
_INVISIBLE = re.compile("[​-‏‪-‮⁦-⁩﻿]")


class _Level(BaseModel):
    model_config = ConfigDict(extra="ignore")
    name: str
    caption: str | None = None


class _Hierarchy(BaseModel):
    model_config = ConfigDict(extra="ignore")
    name: str
    levels: list[_Level] = []


class _Dimension(BaseModel):
    model_config = ConfigDict(extra="ignore")
    name: str
    caption: str | None = None
    type: str = "standard"
    hierarchies: list[_Hierarchy] = []


class _Measure(BaseModel):
    model_config = ConfigDict(extra="ignore")
    name: str
    caption: str | None = None
    annotations: dict[str, str] = {}


class _Cube(BaseModel):
    model_config = ConfigDict(extra="ignore")
    name: Annotated[str, StringConstraints(pattern=r"^[A-Za-z0-9_]{1,128}$")]
    caption: str | None = None
    annotations: dict[str, str] = {}
    dimensions: list[_Dimension] = []
    measures: list[_Measure] = []


class _CubeIndex(BaseModel):
    model_config = ConfigDict(extra="ignore")
    cubes: list[_Cube] = Field(max_length=10_000)


def run_discovery(context: JobContext) -> JsonObject:
    with context.sessions() as db:
        validation = entry_context(context.settings.outbound_allow_loopback_http)
        entries = [
            Api.model_validate(e, context=validation) for e in db.scalars(select(ApiRow.entry))
        ]
    summary: JsonObject = {}
    for api in entries:
        if api.discovery is None:
            continue
        if api.discovery.kind is DiscoveryKind.TESSERACT_CUBES:
            summary[api.slug] = _discover_tesseract(context, api)
    return summary


def _discover_tesseract(context: JobContext, api: Api) -> JsonObject:
    assert api.discovery is not None
    base = api.discovery.base_url.rstrip("/")
    hosts = api.catalogued_hosts()
    per_minute = api.usage.max_requests_per_minute or DEFAULT_REQUESTS_PER_MINUTE
    index_url = f"{base}/cubes"
    if not context.client.robots_allows(index_url, allowed_hosts=hosts):
        return {"outcome": "disallowed_by_robots"}
    indexes: dict[str, _CubeIndex] = {}
    for locale in ("en", "ar"):
        try:
            response = context.client.get(
                f"{index_url}?locale={locale}",
                allowed_hosts=hosts,
                per_minute=per_minute,
                wait_for_budget=True,
                accept="application/json",
            )
        except (OutboundRefused, OutboundFailed) as error:
            return {"outcome": error.code.value}
        if response.status != 200:
            return {"outcome": "http_error", "http_status": response.status}
        try:
            indexes[locale] = _CubeIndex.model_validate_json(response.body)
        except ValidationError:
            return {"outcome": "invalid_payload"}

    arabic = {c.name: c for c in indexes["ar"].cubes}
    now = datetime.now(UTC)
    rows = [
        _row(api.slug, cube, arabic.get(cube.name), now)
        for cube in indexes["en"].cubes
        if cube.annotations.get("hide_in_ui") != "true"
    ]
    with context.sessions() as db:
        keep = [r["external_id"] for r in rows]
        removed = db.execute(
            delete(DatasetRow)
            .where(DatasetRow.api_slug == api.slug, DatasetRow.external_id.not_in(keep))
            .returning(DatasetRow.external_id)
        ).all()
        if rows:
            statement = insert(DatasetRow).values(rows)
            _ = db.execute(
                statement.on_conflict_do_update(
                    index_elements=[DatasetRow.api_slug, DatasetRow.external_id],
                    set_={
                        k: statement.excluded[k]
                        for k in rows[0]
                        if k not in ("api_slug", "external_id")
                    },
                )
            )
        db.commit()
    _log.info(
        "datasets discovered",
        extra={"api": api.slug, "datasets": len(rows), "removed": len(removed)},
    )
    return {"outcome": "succeeded", "datasets": len(rows), "removed": len(removed)}


def _row(api_slug: str, en: _Cube, ar: _Cube | None, now: datetime) -> dict[str, object]:
    notes = en.annotations
    name_en = _clean(notes.get("table_en")) or _clean(en.caption) or en.name
    name_ar = _clean(notes.get("table_ar")) or name_en
    topic_en = _clean(notes.get("topic_en"))
    topic_ar = _clean(notes.get("topic_ar")) or topic_en
    subtopic_en = _clean(notes.get("subtopic_en"))
    subtopic_ar = _clean(notes.get("subtopic_ar")) or subtopic_en
    publisher_en = _clean(notes.get("source_name"))
    publisher_ar = _clean(notes.get("source_name_ar")) or publisher_en
    required = {
        part.strip() for part in (notes.get("required_dimensions") or "").split(",") if part
    }
    ar_measures = {m.name: m for m in ar.measures} if ar else {}
    ar_dimensions = {d.name: d for d in ar.dimensions} if ar else {}
    measures: list[JsonValue] = [
        {
            "name": m.name,
            "caption_en": _clean(m.caption) or m.name,
            "caption_ar": _clean(ar_measures[m.name].caption) if m.name in ar_measures else None,
            "unit": _clean(m.annotations.get("units_of_measurement")) or None,
        }
        for m in en.measures
    ]
    dimensions: list[JsonValue] = []
    for dimension in en.dimensions:
        arabic = ar_dimensions.get(dimension.name)
        ar_levels = {lv.name: lv for h in arabic.hierarchies for lv in h.levels} if arabic else {}
        levels: list[JsonValue] = []
        seen: set[str] = set()
        for hierarchy in dimension.hierarchies:
            for level in hierarchy.levels:
                if level.name in seen:
                    continue
                seen.add(level.name)
                levels.append(
                    {
                        "name": level.name,
                        "caption_en": _clean(level.caption) or level.name,
                        "caption_ar": _clean(ar_levels[level.name].caption)
                        if level.name in ar_levels
                        else None,
                    }
                )
        dimensions.append(
            {
                "name": dimension.name,
                "caption_en": _clean(dimension.caption) or dimension.name,
                "caption_ar": _clean(arabic.caption) if arabic else None,
                "type": dimension.type,
                "required": dimension.name in required,
                "levels": levels,
            }
        )
    return {
        "api_slug": api_slug,
        "external_id": en.name,
        "name_en": name_en,
        "name_ar": name_ar,
        "topic_en": topic_en,
        "topic_ar": topic_ar,
        "subtopic_en": subtopic_en,
        "subtopic_ar": subtopic_ar,
        "publisher_en": publisher_en,
        "publisher_ar": publisher_ar,
        "publisher_url": _https_or_none(notes.get("source_link")),
        # A JSON round trip keeps exactly what JSONB will store.
        "measures": json.loads(json.dumps(measures, ensure_ascii=False)),
        "dimensions": json.loads(json.dumps(dimensions, ensure_ascii=False)),
        "refreshed_at": now,
    }


def _clean(value: str | None) -> str:
    """Strip invisible formatting characters and collapse whitespace."""
    if not value:
        return ""
    return " ".join(_INVISIBLE.sub("", value).split())


def _https_or_none(value: str | None) -> str | None:
    if not value:
        return None
    parts = urlsplit(value.strip())
    return value.strip() if parts.scheme == "https" and parts.hostname else None
