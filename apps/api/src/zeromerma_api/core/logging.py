from __future__ import annotations

import json
import logging
import logging.config
from datetime import UTC, datetime
from typing import Any

from zeromerma_api.core.log_redaction import redact_log
from zeromerma_api.core.operation_context import OperationContext, current_operation_context


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(tz=UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exception_type"] = type(record.exc_info[1]).__name__
        context = getattr(record, "operation_context", None) or current_operation_context()
        if isinstance(context, OperationContext):
            payload.update(context.log_fields())
        status = getattr(record, "http_status", None)
        if isinstance(status, int):
            payload["http_status"] = status
        return json.dumps(redact_log(payload), separators=(",", ":"))


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
