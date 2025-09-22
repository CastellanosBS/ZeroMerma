from __future__ import annotations

import logging
import sys
from collections.abc import Mapping

LEVELS: Mapping[str, int] = {
    "CRITICAL": logging.CRITICAL,
    "ERROR": logging.ERROR,
    "WARNING": logging.WARNING,
    "INFO": logging.INFO,
    "DEBUG": logging.DEBUG,
    "NOTSET": logging.NOTSET,
}


def setup_logging(level_name: str = "INFO") -> None:
    """Configure stdlib logging and align Uvicorn loggers.

    Consistent formatting across your app & Uvicorn's access/error logs.
    """
    level = LEVELS.get(level_name.upper(), logging.INFO)

    # Root logger format: timestamp level logger message
    logging.basicConfig(
        level=level,
        stream=sys.stdout,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )

    # Align Uvicorn loggers with the chosen level
    for logger_name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        logging.getLogger(logger_name).setLevel(level)
