from __future__ import annotations

import time

from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError


def wait_for_database(
    database_url: str,
    *,
    timeout_seconds: int = 60,
    interval_seconds: float = 1.0,
) -> None:
    deadline = time.monotonic() + timeout_seconds
    last_error: OperationalError | None = None

    engine = create_engine(
        database_url,
        connect_args={"connect_timeout": 2},
        pool_pre_ping=True,
    )

    try:
        while time.monotonic() < deadline:
            try:
                with engine.connect() as connection:
                    connection.execute(text("SELECT 1"))
                return
            except OperationalError as exc:
                last_error = exc
                time.sleep(interval_seconds)
    finally:
        engine.dispose()

    raise TimeoutError(
        f"Database did not become ready within {timeout_seconds} seconds."
    ) from last_error
