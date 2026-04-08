from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.orm import Session

from zeromerma_api.modules.audit.infrastructure.models import AuditLog


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
    ) -> AuditLog:
        record = AuditLog(
            actor_id=actor_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            branch_id=branch_id,
            request_id=request_id,
            metadata_=metadata,
        )
        session.add(record)
        return record
