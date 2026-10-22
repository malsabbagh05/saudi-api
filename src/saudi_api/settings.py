"""Process settings, read once from the environment (and `ENV_FILE` when set).

Each environment has one configuration file (`AGENTS.md`, "Development environment");
`docs/development/configuration.md` documents every setting.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Annotated, Literal, Self

from pydantic import Field, PostgresDsn, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

_REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=os.environ.get("ENV_FILE"),
        env_file_encoding="utf-8",
        extra="ignore",
        frozen=True,
    )

    environment: Literal["development", "test", "production"] = "development"
    database_url: PostgresDsn = PostgresDsn(
        "postgresql+psycopg://postgres@127.0.0.1:5432/saudi_api"
    )
    # Pool size + overflow = 40, AnyIO's default thread limiter for FastAPI's `def`
    # handlers, so a handler thread never waits for a connection.
    database_pool_size: int = Field(default=10, ge=1)
    database_max_overflow: int = Field(default=30, ge=0)
    # libpq waits forever by default; the same bound as an outbound connect, so a wrong
    # address fails readiness instead of hanging it.
    database_connect_timeout_seconds: int = Field(default=5, ge=1)

    catalog_dir: Path = _REPOSITORY_ROOT / "catalog"

    # The public origins of the API service and of the web directory, used in llms.txt
    # and the MCP guide.
    public_base_url: str = "http://localhost:8000"
    web_base_url: str = "http://localhost:3000"
    # Host headers the MCP transport accepts. Empty keeps the SDK's localhost-only default.
    mcp_allowed_hosts: Annotated[list[str], NoDecode] = []
    # Origins that may call /mcp from a browser. Empty allows none.
    mcp_allowed_origins: Annotated[list[str], NoDecode] = []

    # Outbound requests (ADR-004). Measured on 2026-10-22 from a non-Saudi network: the
    # slowest provider response was 1.68 s (DataSaudi /cubes, 572 KB) and the slowest
    # connect 0.32 s; the timeouts sit an order of magnitude above both.
    outbound_connect_timeout_seconds: float = Field(default=5.0, gt=0)
    outbound_total_timeout_seconds: float = Field(default=20.0, gt=0)
    # The largest single message the stack accepts: the MCP SDK's max_request_body_size.
    outbound_max_response_bytes: int = Field(default=4_194_304, gt=0)
    # Development and test only: allow http:// to loopback addresses, the explicit opt-out
    # the MCP security guidance calls for. Refused when environment is production.
    outbound_allow_loopback_http: bool = False
    # Where checks run from, recorded with each result so a block reads as a block.
    check_region: str = Field(default="unspecified", max_length=64)

    # Worker intervals, in seconds.
    discover_interval_seconds: int = Field(default=86_400, ge=60)
    check_interval_seconds: int = Field(default=3_600, ge=60)
    refresh_specs_interval_seconds: int = Field(default=86_400, ge=60)

    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"

    @field_validator("mcp_allowed_hosts", "mcp_allowed_origins", mode="before")
    @classmethod
    def _split_list(cls, value: object) -> object:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @model_validator(mode="after")
    def _no_loopback_in_production(self) -> Self:
        if self.outbound_allow_loopback_http and self.environment == "production":
            raise ValueError("OUTBOUND_ALLOW_LOOPBACK_HTTP is not allowed in production")
        return self


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
