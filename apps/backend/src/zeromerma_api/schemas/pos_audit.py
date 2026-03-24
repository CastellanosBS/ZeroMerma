from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import Field

from .common import ORMReadSchema


class PosAuditEventOut(ORMReadSchema):
    """
    Canonical read model for persisted POS audit events.
    """

    id: int
    branch_id: int
    actor_user_id: int | None = None

    entity_type: str
    entity_id: int | None = None

    event_type: str
    occurred_at: datetime

    payload: dict[str, Any] = Field(default_factory=dict)

    created_at: datetime
    updated_at: datetime
