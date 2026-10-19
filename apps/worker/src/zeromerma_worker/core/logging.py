from __future__ import annotations

import json
import logging
import logging.config
from datetime import UTC, datetime
from typing import Any

from zeromerma_worker.core.log_redaction import redact_log

EVENT_CONTEXT_FIELDS = (
    "event_id",
    "event_type",
    "context_version",
    "schema_version",
    "source_app",
    "actor_type",
    "operation_id",
    "operation_code",
    "correlation_id",
    "causation_id",
    "idempotency_key",
    "entity_type",
    "entity_id",
    "actor_id",
    "branch_id",
    "workstation_id",
    "cash_session_id",
    "related_branch_ids",
    "occurred_at",
    "recorded_at",
    "attempts",
)
_LOG_FIELDS = frozenset(EVENT_CONTEXT_FIELDS) | {
    "request_id",
    "message_count",
    "environment",
    "poll_interval_seconds",
    "batch_size",
    "skip_db_check",
    "reason",
    "error_type",
    "fields",
}


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(tz=UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "execution_source": "WORKER",
        }
        for key, value in record.__dict__.items():
            if key in _LOG_FIELDS:
                payload[key] = value
        if record.exc_info:
            payload["exception_type"] = type(record.exc_info[1]).__name__
        return json.dumps(redact_log(payload), separators=(",", ":"), default=str)


def configure_logging(level: str) -> None:
    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {"json": {"()": JsonFormatter}},
            "handlers": {
                "default": {
                    "class": "logging.StreamHandler",
                    "formatter": "json",
                }
            },
            "root": {
                "handlers": ["default"],
                "level": level,
            },
            "loggers": {
                name: {"handlers": ["default"], "level": level, "propagate": False}
                for name in ("uvicorn", "uvicorn.error", "uvicorn.access", "httpx")
            },
        }
    )
