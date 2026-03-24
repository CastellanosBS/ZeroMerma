from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from zeromerma_api.models.pos_audit_event import PosAuditEvent


def _to_jsonable(value: Any) -> Any:
    """
    Recursively normalize Python/domain values into JSON-safe values.

    Conversions:
    - Decimal -> string (exact monetary representation)
    - datetime/date -> ISO 8601 string
    - Enum -> enum.value
    - dict/list/tuple/set -> recursively converted
    """
    if isinstance(value, Decimal):
        return str(value)

    if isinstance(value, (datetime, date)):
        return value.isoformat()

    if isinstance(value, Enum):
        return value.value

    if isinstance(value, dict):
        return {str(k): _to_jsonable(v) for k, v in value.items()}

    if isinstance(value, (list, tuple, set)):
        return [_to_jsonable(v) for v in value]

    return value


def record_pos_audit_event(
    db: Session,
    *,
    branch_id: int,
    actor_user_id: int | None,
    entity_type: str,
    entity_id: int | None,
    event_type: str,
    payload: dict[str, Any] | None = None,
    occurred_at: datetime | None = None,
) -> PosAuditEvent:
    """
    Persist one POS audit event inside the current transaction.

    Design:
    - The caller owns transaction boundaries.
    - This function only appends an immutable event row.
    """
    event = PosAuditEvent(
        branch_id=int(branch_id),
        actor_user_id=int(actor_user_id) if actor_user_id is not None else None,
        entity_type=str(entity_type).strip().upper(),
        entity_id=int(entity_id) if entity_id is not None else None,
        event_type=str(event_type).strip().upper(),
        occurred_at=occurred_at if occurred_at is not None else datetime.utcnow(),
        payload=_to_jsonable(payload or {}),
    )

    db.add(event)
    db.flush()
    return event


def list_pos_audit_events(
    db: Session,
    *,
    branch_id: int,
    entity_type: str | None = None,
    entity_id: int | None = None,
    event_type: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[PosAuditEvent]:
    """
    List persisted POS audit events for one branch, newest first.
    """
    stmt = select(PosAuditEvent).where(PosAuditEvent.branch_id == int(branch_id))

    if entity_type is not None:
        stmt = stmt.where(PosAuditEvent.entity_type == str(entity_type).strip().upper())

    if entity_id is not None:
        stmt = stmt.where(PosAuditEvent.entity_id == int(entity_id))

    if event_type is not None:
        stmt = stmt.where(PosAuditEvent.event_type == str(event_type).strip().upper())

    stmt = (
        stmt.order_by(PosAuditEvent.occurred_at.desc(), PosAuditEvent.id.desc())
        .limit(int(limit))
        .offset(int(offset))
    )

    return list(db.scalars(stmt).all())
