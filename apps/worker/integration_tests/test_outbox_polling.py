from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

from sqlalchemy import Engine, text

from zeromerma_api.testing.database_safety import DestructiveTestDatabaseConfig
from zeromerma_worker.outbox.poller import OutboxPoller


def _insert_event(
    engine: Engine,
    *,
    age_seconds: int = 0,
    status: str = "pending",
    processed: bool = False,
    available_after_seconds: int = 0,
) -> str:
    event_id = str(uuid4())
    now = datetime.now(UTC)
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                INSERT INTO outbox_events (
                    id, aggregate_type, aggregate_id, event_name, payload, headers,
                    occurred_at, available_at, processed_at, status, attempts, last_error
                ) VALUES (
                    :id, 'foundation-test', :aggregate_id, 'unknown.foundation.event',
                    CAST(:payload AS jsonb), '{}'::jsonb, :occurred_at,
                    :available_at, :processed_at, :status, 0, NULL
                )
                """
            ),
            {
                "id": event_id,
                "aggregate_id": event_id,
                # A valid JSON scalar is malformed for a domain event; polling must not consume it.
                "payload": json.dumps("malformed-domain-payload-with-private-data"),
                "occurred_at": now - timedelta(seconds=age_seconds),
                "available_at": now + timedelta(seconds=available_after_seconds),
                "processed_at": now if processed else None,
                "status": status,
            },
        )
    return event_id


def _snapshot(engine: Engine) -> list[dict[str, object]]:
    with engine.connect() as connection:
        return [
            dict(row)
            for row in connection.execute(text("SELECT * FROM outbox_events")).mappings().all()
        ]


def test_empty_outbox_poll_returns_zero(worker_test_engine: Engine) -> None:
    assert OutboxPoller(worker_test_engine, batch_size=25).poll_once() == 0
    assert _snapshot(worker_test_engine) == []


def test_poll_filters_due_pending_rows_limits_batch_and_preserves_all_columns(
    worker_test_engine: Engine,
) -> None:
    _insert_event(worker_test_engine, age_seconds=30)
    _insert_event(worker_test_engine, age_seconds=20)
    _insert_event(worker_test_engine, age_seconds=10)
    _insert_event(worker_test_engine, status="processed")
    _insert_event(worker_test_engine, processed=True)
    _insert_event(worker_test_engine, available_after_seconds=3600)
    before = _snapshot(worker_test_engine)
    assert OutboxPoller(worker_test_engine, batch_size=2).poll_once() == 2
    assert _snapshot(worker_test_engine) == before
    assert OutboxPoller(worker_test_engine, batch_size=20).poll_once() == 3
    assert _snapshot(worker_test_engine) == before


def test_two_pollers_skip_locked_row_but_reobserve_it_after_transaction_ends(
    worker_test_engine: Engine,
) -> None:
    event_id = _insert_event(worker_test_engine)
    first = OutboxPoller(worker_test_engine, batch_size=25)
    second = OutboxPoller(worker_test_engine, batch_size=25)
    before = _snapshot(worker_test_engine)
    with worker_test_engine.begin() as connection:
        connection.execute(
            text("SELECT id FROM outbox_events WHERE id = :id FOR UPDATE"), {"id": event_id}
        )
        assert first.poll_once() == 0
        assert second.poll_once() == 0
    assert first.poll_once() == 1
    assert second.poll_once() == 1
    assert _snapshot(worker_test_engine) == before


def test_actual_worker_once_reads_ephemeral_outbox_without_processing(
    worker_test_engine: Engine,
    worker_test_database_config: DestructiveTestDatabaseConfig,
    tmp_path: Path,
) -> None:
    _insert_event(worker_test_engine)
    before = _snapshot(worker_test_engine)
    environment = {
        key: value for key, value in os.environ.items() if not key.startswith("ZEROMERMA_WORKER_")
    }
    environment.update(
        ZEROMERMA_WORKER_ENVIRONMENT="test",
        ZEROMERMA_WORKER_DATABASE_URL=worker_test_database_config.database_url,
    )
    result = subprocess.run(
        [sys.executable, "-m", "zeromerma_worker", "--once"],
        env=environment,
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    records = [json.loads(line) for line in result.stderr.splitlines()]
    assert [record["message"] for record in records] == [
        "worker_booted",
        "outbox_message_ready",
        "outbox_poll_completed",
        "worker_stopped",
    ]
    assert records[-1]["reason"] == "poll_once_completed"
    assert "private-data" not in result.stderr
    assert _snapshot(worker_test_engine) == before
