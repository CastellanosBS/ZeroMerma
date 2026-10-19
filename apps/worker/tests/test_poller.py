from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from sqlalchemy.exc import OperationalError

from zeromerma_worker.core.logging import JsonFormatter
from zeromerma_worker.outbox.poller import OutboxPoller


def _event_context(*, historical: bool = False) -> dict[str, object]:
    return {
        "event_id": uuid4(),
        "event_type": "sale.confirmed",
        "entity_type": "sale",
        "entity_id": str(uuid4()),
        "context_version": 0 if historical else 1,
        "schema_version": 0 if historical else 1,
        "source_app": "UNKNOWN" if historical else "POS",
        "actor_type": "UNKNOWN" if historical else "USER",
        "operation_id": None if historical else uuid4(),
        "operation_code": None if historical else "sale.confirm",
        "correlation_id": None if historical else uuid4(),
        "causation_id": None,
        "idempotency_key": None if historical else uuid4(),
        "actor_id": None if historical else uuid4(),
        "branch_id": None if historical else uuid4(),
        "workstation_id": None if historical else uuid4(),
        "cash_session_id": None if historical else uuid4(),
        "request_id": "private-customer@example.test" if historical else str(uuid4()),
        "related_branch_ids": [] if historical else [str(uuid4())],
        "occurred_at": datetime.now(UTC),
        "recorded_at": None if historical else datetime.now(UTC),
        "attempts": 0,
    }


def test_empty_batch_reports_zero_without_writes(caplog: pytest.LogCaptureFixture) -> None:
    engine = MagicMock()
    connection = engine.begin.return_value.__enter__.return_value
    connection.execute.return_value.mappings.return_value.all.return_value = []
    caplog.set_level(logging.INFO)
    assert OutboxPoller(engine, batch_size=17).poll_once() == 0
    connection.execute.assert_called_once()
    statement, parameters = connection.execute.call_args.args
    assert str(statement).strip().startswith("SELECT")
    assert "payload" not in str(statement) and "headers" not in str(statement)
    assert parameters == {"limit": 17}
    assert caplog.records[-1].message_count == 0


def test_ready_metadata_is_logged_without_processing_or_payload_access(
    caplog: pytest.LogCaptureFixture,
) -> None:
    context = _event_context()
    engine = MagicMock()
    connection = engine.begin.return_value.__enter__.return_value
    connection.execute.return_value.mappings.return_value.all.return_value = [
        {
            **context,
            "payload": {"customer": "private-person"},
            "headers": {"cookie": "private-cookie"},
        }
    ]
    caplog.set_level(logging.INFO)
    assert OutboxPoller(engine, batch_size=5).poll_once() == 1
    assert connection.execute.call_count == 1
    assert caplog.records[0].event_id == context["event_id"]
    assert caplog.records[0].attempts == 0
    assert caplog.records[-1].message_count == 1
    rendered = JsonFormatter().format(caplog.records[0])
    event = json.loads(rendered)
    for field in (
        "event_id",
        "correlation_id",
        "operation_id",
        "actor_id",
        "branch_id",
        "workstation_id",
        "cash_session_id",
    ):
        assert event[field] == str(context[field])
    assert event["source_app"] == "POS"
    assert event["schema_version"] == 1 and event["context_version"] == 1
    assert event["request_id"] == context["request_id"]
    assert "private" not in rendered and "payload" not in event and "headers" not in event
    assert not hasattr(caplog.records[-1], "correlation_id")


def test_historical_context_is_unknown_without_inventing_identity_or_logging_free_text(
    caplog: pytest.LogCaptureFixture,
) -> None:
    engine = MagicMock()
    connection = engine.begin.return_value.__enter__.return_value
    connection.execute.return_value.mappings.return_value.all.return_value = [
        _event_context(historical=True)
    ]
    caplog.set_level(logging.INFO)
    assert OutboxPoller(engine, batch_size=5).poll_once() == 1
    rendered = JsonFormatter().format(caplog.records[0])
    event = json.loads(rendered)
    assert event["source_app"] == "UNKNOWN"
    assert event["context_version"] == 0
    assert event["schema_version"] == 0
    assert event["request_id"] is None and event["correlation_id"] is None
    assert event["actor_id"] is None and event["recorded_at"] is None
    assert "private-customer" not in rendered


def test_each_event_keeps_its_context_across_batches(caplog: pytest.LogCaptureFixture) -> None:
    first, second = _event_context(), _event_context()
    second["source_app"] = "BACKOFFICE"
    engine = MagicMock()
    connection = engine.begin.return_value.__enter__.return_value
    connection.execute.return_value.mappings.return_value.all.side_effect = [[first], [second]]
    caplog.set_level(logging.INFO)
    poller = OutboxPoller(engine, batch_size=1)
    assert poller.poll_once() == 1
    assert poller.poll_once() == 1
    events = [record for record in caplog.records if record.message == "outbox_message_ready"]
    assert [record.correlation_id for record in events] == [
        first["correlation_id"],
        second["correlation_id"],
    ]
    assert [record.source_app for record in events] == ["POS", "BACKOFFICE"]
    assert connection.execute.call_count == 2


def test_database_failure_releases_transaction_and_propagates() -> None:
    engine = MagicMock()
    connection = engine.begin.return_value.__enter__.return_value
    error = OperationalError("SELECT", {}, RuntimeError("unavailable"))
    connection.execute.side_effect = error
    with pytest.raises(OperationalError):
        OutboxPoller(engine, batch_size=5).poll_once()
    engine.begin.return_value.__exit__.assert_called_once()
    assert engine.begin.return_value.__exit__.call_args.args[0] is OperationalError


def test_worker_formatter_drops_unclassified_extra_without_losing_event_context() -> None:
    record = logging.LogRecord("worker", logging.INFO, __file__, 1, "event observed", (), None)
    record.event_id = str(uuid4())
    record.source_app = "POS"
    record.customer_email = "private@example.test"
    record.payload = {"note": "private note"}
    record.headers = {"Cookie": "private cookie"}
    rendered = JsonFormatter().format(record)
    result = json.loads(rendered)
    assert result["execution_source"] == "WORKER"
    assert result["source_app"] == "POS" and result["event_id"] == record.event_id
    assert not {"customer_email", "payload", "headers"} & result.keys()
    assert "private" not in rendered
