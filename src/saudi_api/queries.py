"""Catalogue reads for the REST API, the MCP tools and llms.txt (one query owner).

Every function takes a session and returns the shapes in `contracts.py`. Curated detail
comes from the projected `entry`, parsed back through the catalogue schema, so a reader
never sees a shape the schema did not accept.
"""

from __future__ import annotations

from collections.abc import Sequence
from urllib.parse import urlencode

from sqlalchemy import ColumnElement, and_, func, literal, select, union_all
from sqlalchemy.orm import Session

from saudi_api import search
from saudi_api.catalog.schema import (
    AccessLevel,
    AgentInvocation,
    Api,
    AuthScheme,
    LocalizedText,
    Provider,
    entry_context,
)
from saudi_api.contracts import (
    AccessOut,
    AccessSummary,
    ApiDetail,
    ApiKeyOut,
    ApiSummary,
    BaseUrlOut,
    CheckOut,
    DatasetDetail,
    DatasetSummary,
    DimensionOut,
    EndpointOut,
    JobOut,
    LevelOut,
    MeasureOut,
    OperationOut,
    Page,
    ParameterOut,
    ProviderOut,
    ProviderRef,
    ProviderSummary,
    PublisherOut,
    SearchHit,
    SectorOut,
    SpecOut,
    StatsOut,
    Text,
    UsageOut,
    VerificationOut,
)
from saudi_api.examples import code_examples, endpoint_url_template
from saudi_api.json_types import JsonValue
from saudi_api.models import (
    ApiCheckRow,
    ApiRow,
    ApiSectorRow,
    ApiSpecRow,
    CatalogState,
    DatasetRow,
    JobRunRow,
    ProviderRow,
    SectorRow,
)

MAX_PAGE = 100
# The DataSaudi query endpoint that a dataset's example arguments are for.
DATASET_QUERY_ENDPOINT = "query-cube"


def list_sectors(db: Session) -> list[SectorOut]:
    counts = (
        select(ApiSectorRow.sector_slug, func.count().label("n"))
        .group_by(ApiSectorRow.sector_slug)
        .subquery()
    )
    rows = db.execute(
        select(SectorRow, func.coalesce(counts.c.n, 0))
        .outerjoin(counts, counts.c.sector_slug == SectorRow.slug)
        .order_by(SectorRow.position)
    ).all()
    return [
        SectorOut(
            slug=s.slug,
            name=Text(en=s.name_en, ar=s.name_ar),
            description=Text(en=s.description_en, ar=s.description_ar),
            api_count=n,
        )
        for s, n in rows
    ]


def list_providers(db: Session) -> list[ProviderSummary]:
    counts = (
        select(ApiRow.provider_slug, func.count().label("n"))
        .group_by(ApiRow.provider_slug)
        .subquery()
    )
    rows = db.execute(
        select(ProviderRow, func.coalesce(counts.c.n, 0))
        .outerjoin(counts, counts.c.provider_slug == ProviderRow.slug)
        .order_by(ProviderRow.name_en)
    ).all()
    return [_provider_summary(Provider.model_validate(p.entry), n) for p, n in rows]


def get_provider(db: Session, slug: str) -> ProviderOut | None:
    row = db.get(ProviderRow, slug)
    if row is None:
        return None
    provider = Provider.model_validate(row.entry)
    apis = list_apis(db, provider=slug, limit=MAX_PAGE, offset=0).items
    summary = _provider_summary(provider, len(apis))
    return ProviderOut(**summary.model_dump(), description=_text(provider.description), apis=apis)


def list_apis(
    db: Session,
    *,
    q: str | None = None,
    sector: str | None = None,
    provider: str | None = None,
    access: AccessLevel | None = None,
    auth: AuthScheme | None = None,
    invocable: bool | None = None,
    limit: int = 20,
    offset: int = 0,
) -> Page[ApiSummary]:
    query = search.normalize_query(q)
    conditions: list[ColumnElement[bool]] = []
    if query is not None:
        conditions.append(search.match(ApiRow.search_vector, ApiRow.search_text, query))
    if sector is not None:
        conditions.append(
            ApiRow.slug.in_(select(ApiSectorRow.api_slug).where(ApiSectorRow.sector_slug == sector))
        )
    if provider is not None:
        conditions.append(ApiRow.provider_slug == provider)
    if access is not None:
        conditions.append(ApiRow.access_level == access.value)
    if auth is not None:
        conditions.append(ApiRow.auth.any_() == auth.value)
    if invocable is not None:
        conditions.append(ApiRow.agent_invocation.is_(invocable))
    where = and_(*conditions) if conditions else literal(True)

    total = db.scalar(select(func.count()).select_from(ApiRow).where(where)) or 0
    statement = select(ApiRow).where(where)
    if query is not None:
        relevance = search.score(ApiRow.search_vector, ApiRow.search_text, query)
        statement = statement.order_by(relevance.desc(), ApiRow.slug)
    else:
        statement = statement.order_by(ApiRow.name_en, ApiRow.slug)
    rows = db.scalars(statement.limit(limit).offset(offset)).all()
    return Page(items=_summaries(db, rows), total=total, limit=limit, offset=offset)


def get_api(db: Session, slug: str) -> ApiDetail | None:
    row = db.get(ApiRow, slug)
    if row is None:
        return None
    summary = _summaries(db, [row])[0]
    api = Api.model_validate(row.entry)
    spec_row = db.get(ApiSpecRow, slug)
    invocable = api.usage.agent_invocation is AgentInvocation.ALLOWED
    endpoints = [
        EndpointOut(
            id=e.id,
            method=e.method,
            path=e.path,
            url=endpoint_url_template(api, e),
            summary=_text(e.summary),
            parameters=[
                ParameterOut(
                    name=p.name,
                    location=p.location,
                    type=p.type.value,
                    required=p.required,
                    description=_text(p.description),
                    example=p.example,
                    allowed_values=p.allowed_values,
                )
                for p in e.parameters
            ],
            response_example=e.response_example,
            examples=code_examples(api, e),
            invocable=invocable,
        )
        for e in api.endpoints
    ]
    key = api.access.api_key
    fields = summary.model_dump(exclude={"access"})
    return ApiDetail(
        **fields,
        description=_text(api.description),
        status_note=_text(api.status_note) if api.status_note else None,
        documentation_url=api.documentation_url,
        openapi_url=api.openapi_url,
        signup_url=api.signup_url,
        terms_url=api.terms_url,
        base_urls=[BaseUrlOut(url=b.url, environment=b.environment.value) for b in api.base_urls],
        formats=[f.value for f in api.formats],
        tags=list(api.tags),
        access=AccessOut(
            level=api.access.level.value,
            auth=[a.value for a in api.access.auth],
            pricing=api.access.pricing.value,
            api_key=ApiKeyOut(location=key.location, name=key.name) if key else None,
            notes=_text(api.access.notes) if api.access.notes else None,
        ),
        usage=UsageOut(
            agent_invocation=invocable,
            max_requests_per_minute=api.usage.max_requests_per_minute,
            policy_evidence=list(api.usage.policy_evidence),
            notes=_text(api.usage.notes) if api.usage.notes else None,
        ),
        endpoints=endpoints,
        spec=_spec(spec_row) if spec_row else None,
        verification=VerificationOut(
            checked_on=api.verification.checked_on,
            method=api.verification.method.value,
            evidence=list(api.verification.evidence),
        ),
    )


def load_api_entry(db: Session, slug: str, *, allow_loopback_http: bool = False) -> Api | None:
    """The validated curated entry, for code that acts on it (invocation)."""
    row = db.get(ApiRow, slug)
    if row is None:
        return None
    return Api.model_validate(row.entry, context=entry_context(allow_loopback_http))


def get_spec_document(db: Session, slug: str) -> dict[str, JsonValue] | None:
    row = db.get(ApiSpecRow, slug)
    return None if row is None else row.document


def list_datasets(
    db: Session,
    *,
    q: str | None = None,
    api_slug: str | None = None,
    limit: int = 20,
    offset: int = 0,
) -> Page[DatasetSummary]:
    query = search.normalize_query(q)
    conditions: list[ColumnElement[bool]] = []
    if query is not None:
        conditions.append(search.match(DatasetRow.search_vector, DatasetRow.search_text, query))
    if api_slug is not None:
        conditions.append(DatasetRow.api_slug == api_slug)
    where = and_(*conditions) if conditions else literal(True)
    total = db.scalar(select(func.count()).select_from(DatasetRow).where(where)) or 0
    statement = select(DatasetRow).where(where)
    if query is not None:
        relevance = search.score(DatasetRow.search_vector, DatasetRow.search_text, query)
        statement = statement.order_by(relevance.desc(), DatasetRow.external_id)
    else:
        statement = statement.order_by(
            DatasetRow.topic_en, DatasetRow.name_en, DatasetRow.external_id
        )
    rows = db.scalars(statement.limit(limit).offset(offset)).all()
    return Page(items=[_dataset_summary(r) for r in rows], total=total, limit=limit, offset=offset)


def get_dataset(db: Session, api_slug: str, external_id: str) -> DatasetDetail | None:
    row = db.get(DatasetRow, (api_slug, external_id))
    if row is None:
        return None
    api = load_api_entry(db, api_slug)
    measures = [_measure(m) for m in _list(row.measures)]
    dimensions = [_dimension(d) for d in _list(row.dimensions)]
    query = _dataset_query(row.external_id, measures, dimensions)
    query_url = None
    if api is not None:
        endpoint = next((e for e in api.endpoints if e.id == DATASET_QUERY_ENDPOINT), None)
        template = endpoint_url_template(api, endpoint) if endpoint else None
        query_url = f"{template}?{urlencode(query)}" if template else None
    summary = _dataset_summary(row)
    return DatasetDetail(
        **summary.model_dump(),
        measures=measures,
        dimensions=dimensions,
        required_dimensions=[d.name for d in dimensions if d.required],
        query=query,
        query_url=query_url,
    )


def search_catalog(db: Session, q: str, limit: int = 20) -> list[SearchHit]:
    """APIs and datasets together, ranked by one score (ADR-003)."""
    query = search.normalize_query(q)
    if query is None:
        return []
    apis = select(
        literal("api").label("kind"),
        ApiRow.slug.label("api_slug"),
        literal(None).label("dataset_id"),
        ApiRow.name_en,
        ApiRow.name_ar,
        ApiRow.summary_en,
        ApiRow.summary_ar,
        search.score(ApiRow.search_vector, ApiRow.search_text, query).label("score"),
    ).where(search.match(ApiRow.search_vector, ApiRow.search_text, query))
    datasets = select(
        literal("dataset").label("kind"),
        DatasetRow.api_slug,
        DatasetRow.external_id.label("dataset_id"),
        DatasetRow.name_en,
        DatasetRow.name_ar,
        DatasetRow.topic_en.label("summary_en"),
        DatasetRow.topic_ar.label("summary_ar"),
        search.score(DatasetRow.search_vector, DatasetRow.search_text, query).label("score"),
    ).where(search.match(DatasetRow.search_vector, DatasetRow.search_text, query))
    combined = union_all(apis, datasets).subquery()
    rows = db.execute(
        select(combined).order_by(combined.c.score.desc(), combined.c.api_slug).limit(limit)
    ).all()
    return [
        SearchHit(
            kind=r.kind,
            api_slug=r.api_slug,
            dataset_id=r.dataset_id,
            name=Text(en=r.name_en, ar=r.name_ar),
            summary=Text(en=r.summary_en, ar=r.summary_ar),
            score=round(float(r.score), 4),
        )
        for r in rows
    ]


def catalog_stats(db: Session) -> StatsOut:
    state = db.get(CatalogState, 1)
    jobs = db.scalars(select(JobRunRow).order_by(JobRunRow.job)).all()
    return StatsOut(
        apis=db.scalar(select(func.count()).select_from(ApiRow)) or 0,
        providers=db.scalar(select(func.count()).select_from(ProviderRow)) or 0,
        sectors=db.scalar(select(func.count()).select_from(SectorRow)) or 0,
        datasets=db.scalar(select(func.count()).select_from(DatasetRow)) or 0,
        invocable_apis=db.scalar(
            select(func.count()).select_from(ApiRow).where(ApiRow.agent_invocation.is_(True))
        )
        or 0,
        catalog_digest=state.digest if state else None,
        catalog_synced_at=state.synced_at if state else None,
        jobs=[
            JobOut(job=j.job, outcome=j.outcome, started_at=j.started_at, finished_at=j.finished_at)
            for j in jobs
        ],
    )


def _summaries(db: Session, rows: Sequence[ApiRow]) -> list[ApiSummary]:
    if not rows:
        return []
    slugs = [r.slug for r in rows]
    sectors: dict[str, list[str]] = {}
    for api_slug, sector_slug in db.execute(
        select(ApiSectorRow.api_slug, ApiSectorRow.sector_slug)
        .join(SectorRow, SectorRow.slug == ApiSectorRow.sector_slug)
        .where(ApiSectorRow.api_slug.in_(slugs))
        .order_by(SectorRow.position)
    ):
        sectors.setdefault(api_slug, []).append(sector_slug)
    checks = {
        c.api_slug: c
        for c in db.scalars(select(ApiCheckRow).where(ApiCheckRow.api_slug.in_(slugs)))
    }
    # A Result has .keys(), so dict(result) would treat it as a mapping; build from rows.
    datasets = {
        api_slug: count
        for api_slug, count in db.execute(
            select(DatasetRow.api_slug, func.count())
            .where(DatasetRow.api_slug.in_(slugs))
            .group_by(DatasetRow.api_slug)
        )
    }
    providers = {
        p.slug: p
        for p in db.scalars(
            select(ProviderRow).where(ProviderRow.slug.in_({r.provider_slug for r in rows}))
        )
    }
    out: list[ApiSummary] = []
    for row in rows:
        provider = providers[row.provider_slug]
        check = checks.get(row.slug)
        out.append(
            ApiSummary(
                slug=row.slug,
                name=Text(en=row.name_en, ar=row.name_ar),
                summary=Text(en=row.summary_en, ar=row.summary_ar),
                provider=ProviderRef(
                    slug=provider.slug,
                    name=Text(en=provider.name_en, ar=provider.name_ar),
                    kind=provider.kind,
                ),
                sectors=sectors.get(row.slug, []),
                status=row.status,
                access=AccessSummary(
                    level=row.access_level, auth=list(row.auth), pricing=row.pricing
                ),
                agent_invocation=row.agent_invocation,
                endpoint_count=len(_list(row.entry.get("endpoints"))),
                dataset_count=datasets.get(row.slug, 0),
                check=_check(check) if check else None,
            )
        )
    return out


def _check(row: ApiCheckRow) -> CheckOut:
    return CheckOut.model_validate(
        {
            "outcome": row.outcome,
            "checked_at": row.checked_at,
            "http_status": row.http_status,
            "latency_ms": row.latency_ms,
            "consecutive_failures": row.consecutive_failures,
            "last_success_at": row.last_success_at,
            "region": row.region,
        }
    )


def _spec(row: ApiSpecRow) -> SpecOut:
    operations = [
        OperationOut(
            method=str(_get(o, "method") or ""),
            path=str(_get(o, "path") or ""),
            summary=_optional_str(_get(o, "summary")),
        )
        for o in _list(row.operations)
    ]
    return SpecOut(
        outcome=row.outcome,
        checked_at=row.checked_at,
        fetched_at=row.fetched_at,
        source_url=row.source_url,
        spec_version=row.spec_version,
        title=row.title,
        operation_count=len(operations),
        operations=operations,
    )


def _provider_summary(provider: Provider, api_count: int) -> ProviderSummary:
    return ProviderSummary(
        slug=provider.slug,
        name=_text(provider.name),
        kind=provider.kind.value,
        website_url=provider.website_url,
        api_count=api_count,
    )


def _dataset_summary(row: DatasetRow) -> DatasetSummary:
    return DatasetSummary(
        api_slug=row.api_slug,
        id=row.external_id,
        name=Text(en=row.name_en, ar=row.name_ar),
        topic=Text(en=row.topic_en, ar=row.topic_ar),
        subtopic=Text(en=row.subtopic_en, ar=row.subtopic_ar),
        publisher=PublisherOut(
            name=Text(en=row.publisher_en, ar=row.publisher_ar), url=row.publisher_url
        ),
        refreshed_at=row.refreshed_at,
    )


def _measure(value: JsonValue) -> MeasureOut:
    return MeasureOut(
        name=str(_get(value, "name") or ""),
        caption=_caption(value),
        unit=_optional_str(_get(value, "unit")),
    )


def _dimension(value: JsonValue) -> DimensionOut:
    return DimensionOut(
        name=str(_get(value, "name") or ""),
        caption=_caption(value),
        type=str(_get(value, "type") or "standard"),
        required=_get(value, "required") is True,
        levels=[
            LevelOut(name=str(_get(level, "name") or ""), caption=_caption(level))
            for level in _list(_get(value, "levels"))
        ],
    )


def _dataset_query(
    cube: str, measures: list[MeasureOut], dimensions: list[DimensionOut]
) -> dict[str, str]:
    """Arguments for the query endpoint: a required (else time, else first) dimension's
    first level, and the first measure."""
    with_levels = [d for d in dimensions if d.levels]
    drilldown = next((d for d in with_levels if d.required), None)
    drilldown = drilldown or next((d for d in with_levels if d.type == "time"), None)
    drilldown = drilldown or next(iter(with_levels), None)
    query = {"cube": cube, "limit": "100,0", "locale": "en"}
    if drilldown is not None:
        query["drilldowns"] = drilldown.levels[0].name
    if measures:
        query["measures"] = measures[0].name
    return query


def _caption(value: JsonValue) -> Text:
    name = str(_get(value, "name") or "")
    en = _optional_str(_get(value, "caption_en")) or name
    ar = _optional_str(_get(value, "caption_ar")) or en
    return Text(en=en, ar=ar)


def _text(value: LocalizedText) -> Text:
    return Text(en=value.en, ar=value.ar)


def _list(value: JsonValue | None) -> list[JsonValue]:
    return value if isinstance(value, list) else []


def _get(value: JsonValue, key: str) -> JsonValue:
    return value.get(key) if isinstance(value, dict) else None


def _optional_str(value: JsonValue) -> str | None:
    return value if isinstance(value, str) and value else None
