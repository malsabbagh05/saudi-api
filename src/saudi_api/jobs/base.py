"""What every job receives (ADR-004)."""

from __future__ import annotations

import uuid
from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal

from sqlalchemy.orm import Session, sessionmaker

from saudi_api.json_types import JsonObject
from saudi_api.outbound import OutboundClient
from saudi_api.settings import Settings

type JobName = Literal["discover", "check", "refresh-specs"]
JOB_NAMES: tuple[JobName, ...] = ("discover", "check", "refresh-specs")


@dataclass(frozen=True)
class JobContext:
    settings: Settings
    sessions: sessionmaker[Session]
    client: OutboundClient
    run_id: uuid.UUID


type Job = Callable[[JobContext], JsonObject]
