from __future__ import annotations

import logging
from uuid import UUID

from sqlalchemy import Engine, text

from zeromerma_worker.core.logging import EVENT_CONTEXT_FIELDS


def _safe_request_id(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    try:
        return str(UUID(value))
    except ValueError:
        # Historical free-text request identifiers are not safe logging context.
        return None


class OutboxPoller:
    def __init__(self, engine: Engine, batch_size: int) -> None:
        self._engine = engine
        self._batch_size = batch_size
        self._logger = logging.getLogger(__name__)

    def poll_once(self) -> int:
        query = text(
            """
            SELECT id AS event_id, event_name AS event_type,
                   aggregate_type AS entity_type, aggregate_id AS entity_id,
                   context_version, schema_version, source_app, actor_type,
                   operation_id, operation_code, correlation_id, causation_id,
                   idempotency_key, actor_id, branch_id, workstation_id, cash_session_id,
                   request_id, related_branch_ids, occurred_at, recorded_at, attempts
            FROM outbox_events
            WHERE status = 'pending'
              AND processed_at IS NULL
              AND available_at <= now()
            ORDER BY occurred_at ASC
            LIMIT :limit
            FOR UPDATE SKIP LOCKED
            """
        )

        with self._engine.begin() as connection:
            rows = connection.execute(query, {"limit": self._batch_size}).mappings().all()

        for row in rows:
            self._logger.info(
                "outbox_message_ready",
                extra={
                    **{field: row[field] for field in EVENT_CONTEXT_FIELDS},
                    "request_id": _safe_request_id(row["request_id"]),
                },
            )

        self._logger.info("outbox_poll_completed", extra={"message_count": len(rows)})
        return len(rows)
