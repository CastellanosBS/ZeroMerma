from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import timedelta
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from zeromerma_api.modules.idempotency.domain.constants import IdempotencyStatus


class CommandContext(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    actor_user_id: UUID
    surface: Literal["POS", "BACKOFFICE"]
    branch_id: UUID | None = None
    workstation_id: UUID | None = None
    cash_session_id: UUID | None = None
    related_branch_ids: tuple[UUID, ...] = ()


@dataclass(frozen=True)
class CommandResult:
    status_code: int
    snapshot: BaseModel
    resource_type: str | None = None
    resource_id: str | None = None
    reference: BaseModel | None = None


@dataclass(frozen=True)
class ResponsePolicy:
    snapshot_model: type[BaseModel]
    schema_version: str = "1"
    reference_model: type[BaseModel] | None = None
    restore: Callable[[Session, BaseModel], BaseModel] | None = None
    payload_retention: timedelta | None = None
    rejection_model: type[BaseModel] | None = None


@dataclass(frozen=True)
class IdempotencyResult:
    record_id: UUID
    status: IdempotencyStatus
    status_code: int
    payload: dict[str, Any]
    replayed: bool
    error_code: str | None = None
    error_message: str | None = None
