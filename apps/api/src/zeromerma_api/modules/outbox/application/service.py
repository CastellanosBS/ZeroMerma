from __future__ import annotations

from dataclasses import replace
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from zeromerma_api.db.operation_context import get_operation_context
from zeromerma_api.modules.outbox.infrastructure.models import OutboxEvent


class _ContextDefault:
    """Distinguish omitted context from an explicitly global or anonymous event."""


_CONTEXT_DEFAULT = _ContextDefault()


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
        actor_id: UUID | None | _ContextDefault = _CONTEXT_DEFAULT,
        branch_id: UUID | None | _ContextDefault = _CONTEXT_DEFAULT,
        workstation_id: UUID | None | _ContextDefault = _CONTEXT_DEFAULT,
        cash_session_id: UUID | None | _ContextDefault = _CONTEXT_DEFAULT,
        schema_version: int = 1,
    ) -> OutboxEvent:
        if schema_version < 1:
            raise ValueError("An outbox schema version must be positive.")
        context = get_operation_context(session)
        context = replace(
            context,
            actor_id=context.actor_id if isinstance(actor_id, _ContextDefault) else actor_id,
            branch_id=context.branch_id if isinstance(branch_id, _ContextDefault) else branch_id,
            workstation_id=context.workstation_id
            if isinstance(workstation_id, _ContextDefault)
            else workstation_id,
            cash_session_id=context.cash_session_id
            if isinstance(cash_session_id, _ContextDefault)
            else cash_session_id,
        )
        event = OutboxEvent(
            aggregate_type=aggregate_type,
            aggregate_id=aggregate_id,
            event_name=event_name,
            schema_version=schema_version,
            context_version=1,
            source_app=context.source_app,
            actor_type=context.actor_type,
            actor_id=context.actor_id,
            branch_id=context.branch_id,
            request_id=context.request_id,
            operation_id=context.operation_id,
            correlation_id=context.correlation_id,
            causation_id=context.causation_id,
            idempotency_key=context.idempotency_key,
            operation_code=context.operation_code,
            workstation_id=context.workstation_id,
            cash_session_id=context.cash_session_id,
            related_branch_ids=[
                str(value)
                for value in sorted(
                    {
                        *context.related_branch_ids,
                        *([context.branch_id] if context.branch_id else []),
                    },
                    key=str,
                )
            ],
            payload=payload,
            headers=headers or {},
        )
        session.add(event)
        return event
