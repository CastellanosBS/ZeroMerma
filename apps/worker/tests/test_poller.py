from __future__ import annotations

import logging
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from sqlalchemy.exc import OperationalError

from zeromerma_worker.outbox.poller import OutboxPoller


def test_empty_batch_reports_zero_without_writes(caplog: pytest.LogCaptureFixture) -> None:
    engine = MagicMock()
    connection = engine.begin.return_value.__enter__.return_value
    connection.execute.return_value.mappings.return_value.all.return_value = []
    caplog.set_level(logging.INFO)
    assert OutboxPoller(engine, batch_size=17).poll_once() == 0
    connection.execute.assert_called_once()
    statement, parameters = connection.execute.call_args.args
    assert str(statement).strip().startswith("SELECT")
    assert parameters == {"limit": 17}
    assert caplog.records[-1].message_count == 0


def test_ready_metadata_is_logged_without_processing_or_payload_access(
    caplog: pytest.LogCaptureFixture,
) -> None:
    event_id = uuid4()
    engine = MagicMock()
    connection = engine.begin.return_value.__enter__.return_value
    connection.execute.return_value.mappings.return_value.all.return_value = [
        {
            "id": event_id,
            "event_name": "unknown.event",
            "aggregate_type": "unknown",
            "aggregate_id": "opaque-id",
            "attempts": 0,
        }
    ]
    caplog.set_level(logging.INFO)
    assert OutboxPoller(engine, batch_size=5).poll_once() == 1
    assert connection.execute.call_count == 1
    assert caplog.records[0].outbox_id == str(event_id)
    assert caplog.records[0].attempts == 0
    assert caplog.records[-1].message_count == 1


def test_database_failure_releases_transaction_and_propagates() -> None:
    engine = MagicMock()
    connection = engine.begin.return_value.__enter__.return_value
    error = OperationalError("SELECT", {}, RuntimeError("unavailable"))
    connection.execute.side_effect = error
    with pytest.raises(OperationalError):
        OutboxPoller(engine, batch_size=5).poll_once()
    engine.begin.return_value.__exit__.assert_called_once()
    assert engine.begin.return_value.__exit__.call_args.args[0] is OperationalError
