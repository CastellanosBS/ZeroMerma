from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from zeromerma_api.modules.outbox.infrastructure.models import OutboxEvent


class OutboxWriter:
    def append(
        self,
        session: Session,
        *,
        aggregate_type: str,
        aggregate_id: str,
        event_name: str,
        payload: dict[str, Any],
        headers: dict[str, Any] | None = None,
    ) -> OutboxEvent:
        event = OutboxEvent(
            aggregate_type=aggregate_type,
            aggregate_id=aggregate_id,
            event_name=event_name,
            payload=payload,
            headers=headers or {},
        )
        session.add(event)
        return event
