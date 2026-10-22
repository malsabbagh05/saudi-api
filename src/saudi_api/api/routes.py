"""The REST API (`/v1`). Handlers are plain `def`: FastAPI runs them in its thread pool,
where the synchronous database work belongs (ADR-001)."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import JSONResponse, PlainTextResponse
from sqlalchemy.orm import Session, sessionmaker

from saudi_api import queries
from saudi_api.catalog.schema import AccessLevel, AuthScheme
from saudi_api.contracts import (
    ApiDetail,
    ApiSummary,
    DatasetDetail,
    DatasetSummary,
    ErrorOut,
    Page,
    ProviderOut,
    ProviderSummary,
    SearchHit,
    SectorOut,
    StatsOut,
)
from saudi_api.llms import render_guide
from saudi_api.settings import Settings

# OFFSET scans the rows it skips; the catalogue holds far fewer than this.
MAX_OFFSET = 10_000

router = APIRouter(prefix="/v1", responses={404: {"model": ErrorOut}, 422: {"model": ErrorOut}})
root_router = APIRouter()


def get_db(request: Request) -> Iterator[Session]:
    sessions = request.app.state.sessions
    assert isinstance(sessions, sessionmaker)
    with sessions() as db:
        yield db


def get_settings(request: Request) -> Settings:
    settings = request.app.state.settings
    assert isinstance(settings, Settings)
    return settings


Db = Annotated[Session, Depends(get_db)]
Limit = Annotated[int, Query(ge=1, le=queries.MAX_PAGE)]
Offset = Annotated[int, Query(ge=0, le=MAX_OFFSET)]
SearchText = Annotated[str | None, Query(max_length=200, description="Arabic or English words.")]


def _not_found(kind: str) -> HTTPException:
    return HTTPException(
        status_code=404, detail={"code": "not_found", "message": f"no such {kind}"}
    )


@router.get("/sectors", summary="Sectors with their API counts")
def sectors(db: Db) -> list[SectorOut]:
    return queries.list_sectors(db)


@router.get("/providers", summary="Providers with their API counts")
def providers(db: Db) -> list[ProviderSummary]:
    return queries.list_providers(db)


@router.get("/providers/{slug}", summary="One provider and its APIs")
def provider(slug: str, db: Db) -> ProviderOut:
    found = queries.get_provider(db, slug)
    if found is None:
        raise _not_found("provider")
    return found


@router.get("/apis", summary="Search and filter APIs")
def apis(
    db: Db,
    q: SearchText = None,
    sector: str | None = None,
    provider: str | None = None,
    access: AccessLevel | None = None,
    auth: AuthScheme | None = None,
    invocable: bool | None = None,
    limit: Limit = 20,
    offset: Offset = 0,
) -> Page[ApiSummary]:
    return queries.list_apis(
        db,
        q=q,
        sector=sector,
        provider=provider,
        access=access,
        auth=auth,
        invocable=invocable,
        limit=limit,
        offset=offset,
    )


@router.get("/apis/{slug}", summary="One API with endpoints, examples and evidence")
def api(slug: str, db: Db) -> ApiDetail:
    found = queries.get_api(db, slug)
    if found is None:
        raise _not_found("API")
    return found


@router.get(
    "/apis/{slug}/openapi",
    summary="The provider's OpenAPI document, as last fetched",
    response_model=None,
)
def api_openapi(slug: str, db: Db) -> JSONResponse:
    document = queries.get_spec_document(db, slug)
    if document is None:
        raise _not_found("OpenAPI document")
    return JSONResponse(document)


@router.get("/datasets", summary="Search statistical datasets")
def datasets(
    db: Db,
    q: SearchText = None,
    api: str | None = None,
    limit: Limit = 20,
    offset: Offset = 0,
) -> Page[DatasetSummary]:
    return queries.list_datasets(db, q=q, api_slug=api, limit=limit, offset=offset)


@router.get("/datasets/{api_slug}/{dataset_id}", summary="One dataset with its query")
def dataset(api_slug: str, dataset_id: str, db: Db) -> DatasetDetail:
    found = queries.get_dataset(db, api_slug, dataset_id)
    if found is None:
        raise _not_found("dataset")
    return found


@router.get("/search", summary="APIs and datasets together, best match first")
def search(
    db: Db,
    q: Annotated[str, Query(min_length=1, max_length=200)],
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
) -> list[SearchHit]:
    return queries.search_catalog(db, q, limit)


@router.get("/stats", summary="Catalogue counts, sync state and the latest job runs")
def stats(db: Db) -> StatsOut:
    return queries.catalog_stats(db)


@root_router.get("/llms.txt", response_class=PlainTextResponse, include_in_schema=False)
def llms_txt(db: Db, settings: Annotated[Settings, Depends(get_settings)]) -> str:
    return render_guide(db, settings)
