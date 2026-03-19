from __future__ import annotations

import logging
import sys
from collections.abc import Mapping

from zeromerma_api.core.request_context import (
    get_branch_id,
    get_request_id,
    get_role_code,
    get_user_id,
)

LEVELS: Mapping[str, int] = {
    "CRITICAL": logging.CRITICAL,
    "ERROR": logging.ERROR,
    "WARNING": logging.WARNING,
    "INFO": logging.INFO,
    "DEBUG": logging.DEBUG,
    "NOTSET": logging.NOTSET,
}


class RequestContextFilter(logging.Filter):
    """
    Inject request context fields into every log record.

    This allows format strings to reference:
      - %(request_id)s
      - %(user_id)s
      - %(role_code)s
      - %(branch_id)s

    Without this filter, adding those fields in the formatter could crash
    if a log record is emitted outside a request.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = get_request_id()
        record.user_id = get_user_id()
        record.role_code = get_role_code()
        record.branch_id = get_branch_id()
        return True


def setup_logging(level_name: str = "INFO") -> None:
    """Configure stdlib logging and align Uvicorn loggers.

    Goals:
    - Consistent formatting across app & Uvicorn logs.
    - Include request correlation fields when available.
    """
    level = LEVELS.get(level_name.upper(), logging.INFO)

    # Create a filter instance once and reuse it.
    ctx_filter = RequestContextFilter()

    # Configure root logger handlers explicitly so we can attach filters.
    root = logging.getLogger()
    root.setLevel(level)

    # Remove existing handlers (important during reload to avoid duplicates).
    for h in list(root.handlers):
        root.removeHandler(h)

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)

    # Format includes request context fields.
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s | %(levelname)s | %(name)s | "
            "rid=%(request_id)s uid=%(user_id)s role=%(role_code)s bid=%(branch_id)s | "
            "%(message)s"
        )
    )
    handler.addFilter(ctx_filter)
    root.addHandler(handler)

    # Align Uvicorn loggers and attach same filter/handler behavior.
    for logger_name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        lg = logging.getLogger(logger_name)
        lg.setLevel(level)
        # Ensure they also include request context fields (when they log inside requests).
        for h in lg.handlers:
            h.addFilter(ctx_filter)
