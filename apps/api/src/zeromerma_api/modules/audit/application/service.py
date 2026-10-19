from __future__ import annotations

import uuid
from dataclasses import replace
from typing import Any

from sqlalchemy.orm import Session

from zeromerma_api.db.operation_context import get_operation_context
from zeromerma_api.modules.audit.infrastructure.models import AuditLog


class _ContextDefault:
    """Preserve the operation value unless a caller explicitly supplies another value."""


_CONTEXT_DEFAULT = _ContextDefault()


class AuditRecorder:
    def record(
        self,
        session: Session,
        *,
        actor_id: uuid.UUID | None,
        action: str,
        resource_type: str,
        resource_id: str | None,
        branch_id: uuid.UUID | None,
        request_id: str | None,
        metadata: dict[str, Any],
        workstation_id: uuid.UUID | None | _ContextDefault = _CONTEXT_DEFAULT,
        cash_session_id: uuid.UUID | None | _ContextDefault = _CONTEXT_DEFAULT,
    ) -> AuditLog:
        context = replace(get_operation_context(session), actor_id=actor_id, branch_id=branch_id)
        context = replace(
            context,
            workstation_id=context.workstation_id
            if isinstance(workstation_id, _ContextDefault)
            else workstation_id,
            cash_session_id=context.cash_session_id
            if isinstance(cash_session_id, _ContextDefault)
            else cash_session_id,
        )
        record = AuditLog(
            actor_id=actor_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            branch_id=branch_id,
            request_id=context.request_id,
            context_version=1,
            source_app=context.source_app,
            actor_type=context.actor_type,
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
            metadata_=metadata,
        )
        session.add(record)
        return record
