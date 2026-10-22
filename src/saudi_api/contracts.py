"""Response shapes shared by the REST API and the MCP tools (one owner per shape)."""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class _Out(BaseModel):
    model_config = ConfigDict(frozen=True, populate_by_name=True)


class Text(_Out):
    """The same text in English and Arabic."""

    en: str
    ar: str


class Page[T](_Out):
    items: list[T]
    total: int
    limit: int
    offset: int


class SectorOut(_Out):
    slug: str
    name: Text
    description: Text
    api_count: int


class ProviderRef(_Out):
    slug: str
    name: Text
    kind: str


class CheckOut(_Out):
    outcome: Literal[
        "reachable", "http_error", "timeout", "connection_error", "tls_error", "refused_by_policy"
    ]
    checked_at: datetime
    http_status: int | None
    latency_ms: int | None
    consecutive_failures: int
    last_success_at: datetime | None
    region: str = Field(description="Where the check ran from; Saudi hosts may block others.")


class AccessSummary(_Out):
    level: str
    auth: list[str]
    pricing: str


class ApiSummary(_Out):
    slug: str
    name: Text
    summary: Text
    provider: ProviderRef
    sectors: list[str]
    status: str
    access: AccessSummary
    agent_invocation: bool = Field(
        description="True when the MCP tool call_endpoint may request this API's endpoints."
    )
    endpoint_count: int
    dataset_count: int
    check: CheckOut | None


class ProviderSummary(ProviderRef):
    website_url: str
    api_count: int


class ProviderOut(ProviderSummary):
    description: Text
    apis: list[ApiSummary]


class ApiKeyOut(_Out):
    location: Literal["header", "query"] = Field(alias="in")
    name: str


class AccessOut(AccessSummary):
    api_key: ApiKeyOut | None
    notes: Text | None


class UsageOut(_Out):
    agent_invocation: bool
    max_requests_per_minute: int | None
    policy_evidence: list[str]
    notes: Text | None


class ParameterOut(_Out):
    name: str
    location: Literal["path", "query", "header"] = Field(alias="in")
    type: str
    required: bool
    description: Text
    example: str | None
    allowed_values: list[str] | None


class CodeExample(_Out):
    language: Literal["curl", "python", "javascript"]
    code: str


class EndpointOut(_Out):
    id: str
    method: str
    path: str
    url: str | None = Field(description="The production URL with path parameters unfilled.")
    summary: Text
    parameters: list[ParameterOut]
    response_example: str | None
    examples: list[CodeExample]
    invocable: bool


class BaseUrlOut(_Out):
    url: str
    environment: str


class OperationOut(_Out):
    method: str
    path: str
    summary: str | None


class SpecOut(_Out):
    outcome: str
    checked_at: datetime
    fetched_at: datetime | None
    source_url: str
    spec_version: str | None
    title: str | None
    operation_count: int
    operations: list[OperationOut]


class VerificationOut(_Out):
    checked_on: date
    method: str
    evidence: list[str]


class ApiDetail(ApiSummary):
    description: Text
    status_note: Text | None
    documentation_url: str
    openapi_url: str | None
    signup_url: str | None
    terms_url: str | None
    base_urls: list[BaseUrlOut]
    formats: list[str]
    tags: list[str]
    access: AccessOut
    usage: UsageOut
    endpoints: list[EndpointOut]
    spec: SpecOut | None
    verification: VerificationOut


class PublisherOut(_Out):
    name: Text
    url: str | None


class DatasetSummary(_Out):
    api_slug: str
    id: str
    name: Text
    topic: Text
    subtopic: Text
    publisher: PublisherOut
    refreshed_at: datetime


class MeasureOut(_Out):
    name: str
    caption: Text
    unit: str | None


class LevelOut(_Out):
    name: str
    caption: Text


class DimensionOut(_Out):
    name: str
    caption: Text
    type: str
    required: bool = Field(description="The provider requires this dimension in a query.")
    levels: list[LevelOut]


class DatasetDetail(DatasetSummary):
    measures: list[MeasureOut]
    dimensions: list[DimensionOut]
    required_dimensions: list[str]
    query: dict[str, str] = Field(
        description="Example arguments for the API's query endpoint (call_endpoint)."
    )
    query_url: str | None


class SearchHit(_Out):
    kind: Literal["api", "dataset"]
    api_slug: str
    dataset_id: str | None
    name: Text
    summary: Text
    score: float


class JobOut(_Out):
    job: str
    outcome: str
    started_at: datetime
    finished_at: datetime | None


class StatsOut(_Out):
    apis: int
    providers: int
    sectors: int
    datasets: int
    invocable_apis: int
    catalog_digest: str | None
    catalog_synced_at: datetime | None
    jobs: list[JobOut]


class ErrorOut(_Out):
    code: str
    message: str
