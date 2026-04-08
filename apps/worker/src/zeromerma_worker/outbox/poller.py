from __future__ import annotations

import logging

from sqlalchemy import Engine, text


class OutboxPoller:
    def __init__(self, engine: Engine, batch_size: int) -> None:
        self._engine = engine
        self._batch_size = batch_size
        self._logger = logging.getLogger(__name__)

    def poll_once(self) -> int:
        query = text(
            """
            SELECT id, event_name, aggregate_type, aggregate_id, attempts
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
                    "outbox_id": str(row["id"]),
                    "event_name": row["event_name"],
                    "aggregate_type": row["aggregate_type"],
                    "aggregate_id": row["aggregate_id"],
                    "attempts": row["attempts"],
                },
            )

        self._logger.info("outbox_poll_completed", extra={"message_count": len(rows)})
        return len(rows)
