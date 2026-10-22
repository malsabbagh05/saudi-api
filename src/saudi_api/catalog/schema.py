"""The typed shape of the curated catalogue files in `catalog/` (ADR-002).

Every file is parsed through these models; nothing else reads the YAML.
`docs/development/catalogue.md` documents each field, and the catalogue-curation skill
owns how a value is researched.
"""

from __future__ import annotations

import re
from datetime import date
from enum import StrEnum
from typing import Annotated, Literal, Self
from urllib.parse import urlsplit

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    ValidationInfo,
    model_validator,
)

_ARABIC_LETTER = re.compile(r"[؀-ۿ]")
_PATH_PARAMETER = re.compile(r"\{([A-Za-z0-9_]+)\}")

Slug = Annotated[str, StringConstraints(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$", max_length=64)]
NonEmpty = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


_LOOPBACK_HOSTS = frozenset({"127.0.0.1", "localhost", "::1"})
# Validation context key: accept http:// to a loopback host. Only the jobs and invocation
# pass it, and only when OUTBOUND_ALLOW_LOOPBACK_HTTP is set (refused in production), so
# tests can stand a provider up on 127.0.0.1. `catalog check` never passes it.
ALLOW_LOOPBACK_HTTP = "allow_loopback_http"


def _https_url(value: str, info: ValidationInfo) -> str:
    parts = urlsplit(value)
    loopback = (
        isinstance(info.context, dict)
        and info.context.get(ALLOW_LOOPBACK_HTTP) is True
        and parts.scheme == "http"
        and parts.hostname in _LOOPBACK_HOSTS
    )
    if (parts.scheme != "https" and not loopback) or not parts.hostname:
        raise ValueError("must be an https:// URL with a host")
    if parts.username or parts.password:
        raise ValueError("must not carry credentials")
    return value


HttpsUrl = Annotated[str, StringConstraints(max_length=2048), AfterValidator(_https_url)]


def entry_context(allow_loopback_http: bool) -> dict[str, bool]:
    """The validation context for code that acts on an entry's URLs."""
    return {ALLOW_LOOPBACK_HTTP: allow_loopback_http}


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class LocalizedText(_Model):
    """Text in English and Arabic; both are required (bilingual.md)."""

    en: NonEmpty
    ar: NonEmpty

    @model_validator(mode="after")
    def _arabic_is_arabic(self) -> Self:
        if not _ARABIC_LETTER.search(self.ar):
            raise ValueError("the `ar` text contains no Arabic letter")
        return self


class ProviderKind(StrEnum):
    GOVERNMENT = "government"
    REGULATOR = "regulator"
    STATE_OWNED = "state_owned"
    PRIVATE = "private"


class AccessLevel(StrEnum):
    OPEN = "open"
    REGISTRATION = "registration"
    APPROVAL = "approval"
    CONTRACT = "contract"
    RESTRICTED = "restricted"


class AuthScheme(StrEnum):
    NONE = "none"
    # The provider does not publish how clients authenticate (restricted programmes).
    UNDISCLOSED = "undisclosed"
    API_KEY = "api_key"
    # A static token the provider issues, sent as "Authorization: Bearer <token>".
    BEARER = "bearer"
    OAUTH2 = "oauth2"
    MTLS = "mtls"
    BASIC = "basic"
    JWT = "jwt"


class Pricing(StrEnum):
    FREE = "free"
    FREEMIUM = "freemium"
    PAID = "paid"
    UNKNOWN = "unknown"


class ApiStatus(StrEnum):
    ACTIVE = "active"
    BETA = "beta"
    DEPRECATED = "deprecated"


class Environment(StrEnum):
    PRODUCTION = "production"
    SANDBOX = "sandbox"


class DataFormat(StrEnum):
    JSON = "json"
    XML = "xml"
    CSV = "csv"
    XLSX = "xlsx"
    GEOJSON = "geojson"
    PDF = "pdf"


class VerificationMethod(StrEnum):
    LIVE_REQUEST = "live_request"
    OFFICIAL_DOCUMENTATION = "official_documentation"


class AgentInvocation(StrEnum):
    ALLOWED = "allowed"
    NOT_ALLOWED = "not_allowed"


class DiscoveryKind(StrEnum):
    TESSERACT_CUBES = "tesseract_cubes"


class Sector(_Model):
    slug: Slug
    name: LocalizedText
    description: LocalizedText


class SectorsFile(_Model):
    sectors: list[Sector] = Field(min_length=1)


class Provider(_Model):
    slug: Slug
    name: LocalizedText
    kind: ProviderKind
    website_url: HttpsUrl
    description: LocalizedText


class BaseUrl(_Model):
    url: HttpsUrl
    environment: Environment = Environment.PRODUCTION


class ApiKeyLocation(_Model):
    location: Literal["header", "query"] = Field(alias="in")
    name: NonEmpty


class Access(_Model):
    level: AccessLevel
    auth: list[AuthScheme] = Field(min_length=1)
    pricing: Pricing
    api_key: ApiKeyLocation | None = None
    notes: LocalizedText | None = None

    @model_validator(mode="after")
    def _consistent(self) -> Self:
        for alone in (AuthScheme.NONE, AuthScheme.UNDISCLOSED):
            if alone in self.auth and len(self.auth) > 1:
                raise ValueError(f"auth `{alone.value}` stands alone")
        if len(set(self.auth)) != len(self.auth):
            raise ValueError("auth lists a scheme twice")
        if (AuthScheme.API_KEY in self.auth) != (self.api_key is not None):
            raise ValueError("api_key location is required exactly when auth has api_key")
        if self.auth == [AuthScheme.NONE] and self.level is not AccessLevel.OPEN:
            raise ValueError("an API with auth `none` has access level `open`")
        return self


class Usage(_Model):
    agent_invocation: AgentInvocation = AgentInvocation.NOT_ALLOWED
    max_requests_per_minute: int | None = Field(default=None, ge=1, le=600)
    policy_evidence: list[HttpsUrl] = []
    notes: LocalizedText | None = None


class ParameterType(StrEnum):
    STRING = "string"
    INTEGER = "integer"
    NUMBER = "number"
    BOOLEAN = "boolean"


class Parameter(_Model):
    name: Annotated[str, StringConstraints(pattern=r"^[A-Za-z0-9_.\-\[\] ]{1,64}$")]
    location: Literal["path", "query", "header"] = Field(alias="in")
    type: ParameterType = ParameterType.STRING
    required: bool = False
    description: LocalizedText
    example: str | None = None
    allowed_values: list[str] | None = None

    @model_validator(mode="after")
    def _example_for_required(self) -> Self:
        if self.required and self.example is None:
            raise ValueError(f"required parameter {self.name!r} needs an example")
        if self.allowed_values is not None and self.example is not None:
            if self.example not in self.allowed_values:
                raise ValueError(f"example of {self.name!r} is not an allowed value")
        return self


class Endpoint(_Model):
    id: Slug
    method: Literal["GET", "POST", "PUT", "PATCH", "DELETE"]
    path: Annotated[str, StringConstraints(pattern=r"^/[^\s?#]*$", max_length=512)]
    summary: LocalizedText
    parameters: list[Parameter] = []
    response_example: str | None = Field(default=None, max_length=4000)

    @model_validator(mode="after")
    def _path_parameters_declared(self) -> Self:
        in_path = set(_PATH_PARAMETER.findall(self.path))
        declared = {p.name for p in self.parameters if p.location == "path"}
        if in_path != declared:
            raise ValueError(
                f"path parameters {sorted(in_path)} differ from declared {sorted(declared)}"
            )
        if any(not p.required for p in self.parameters if p.location == "path"):
            raise ValueError("path parameters are required")
        names = [(p.location, p.name) for p in self.parameters]
        if len(set(names)) != len(names):
            raise ValueError("a parameter is declared twice")
        return self


class Check(_Model):
    url: HttpsUrl


class Discovery(_Model):
    kind: DiscoveryKind
    base_url: HttpsUrl


class Verification(_Model):
    checked_on: date
    method: VerificationMethod
    evidence: list[HttpsUrl] = Field(min_length=1)


class Api(_Model):
    slug: Slug
    provider: Slug
    name: LocalizedText
    summary: LocalizedText
    description: LocalizedText
    sectors: list[Slug] = Field(min_length=1)
    tags: list[Annotated[str, StringConstraints(min_length=1, max_length=40)]] = []
    status: ApiStatus = ApiStatus.ACTIVE
    status_note: LocalizedText | None = None
    documentation_url: HttpsUrl
    openapi_url: HttpsUrl | None = None
    signup_url: HttpsUrl | None = None
    terms_url: HttpsUrl | None = None
    base_urls: list[BaseUrl] = []
    formats: list[DataFormat] = []
    access: Access
    usage: Usage = Usage()
    check: Check | None = None
    discovery: Discovery | None = None
    endpoints: list[Endpoint] = []
    verification: Verification

    @model_validator(mode="after")
    def _consistent(self) -> Self:
        ids = [e.id for e in self.endpoints]
        if len(set(ids)) != len(ids):
            raise ValueError("endpoint ids repeat")
        if self.endpoints and not self.base_urls:
            raise ValueError("endpoints need at least one base URL")
        if self.discovery is not None and self.discovery.base_url not in {
            b.url for b in self.base_urls
        }:
            raise ValueError("discovery.base_url must be one of base_urls")
        if self.status is ApiStatus.DEPRECATED and self.status_note is None:
            raise ValueError("a deprecated API needs a status_note")
        if len(set(self.sectors)) != len(self.sectors):
            raise ValueError("sectors repeat")
        if self.usage.agent_invocation is AgentInvocation.ALLOWED:
            if self.access.auth != [AuthScheme.NONE]:
                raise ValueError("agent invocation needs auth `none`")
            if not self.endpoints or any(e.method != "GET" for e in self.endpoints):
                raise ValueError("agent invocation needs GET endpoints only")
            if self.usage.max_requests_per_minute is None:
                raise ValueError("agent invocation needs usage.max_requests_per_minute")
            if not self.usage.policy_evidence:
                raise ValueError("agent invocation needs usage.policy_evidence")
            if any(p.location == "header" for e in self.endpoints for p in e.parameters):
                raise ValueError("invocable endpoints take no header parameters")
        return self

    def production_base_url(self) -> str | None:
        for base in self.base_urls:
            if base.environment is Environment.PRODUCTION:
                return base.url
        return self.base_urls[0].url if self.base_urls else None

    def catalogued_hosts(self) -> frozenset[str]:
        """Every host this entry names: the only hosts outbound.py may reach for it."""
        urls = [self.documentation_url, *(b.url for b in self.base_urls)]
        urls += [u for u in (self.openapi_url, self.check.url if self.check else None) if u]
        return frozenset(h for u in urls if (h := urlsplit(u).hostname))
