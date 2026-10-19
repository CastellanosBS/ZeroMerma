"""Observe real lock waits on guarded disposable PostgreSQL, without timing guesses."""

from __future__ import annotations

import os
from dataclasses import dataclass
from time import monotonic, sleep

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from zeromerma_api.db.session import engine
from zeromerma_api.testing.database_safety import (
    assert_authorized_destructive_connection,
    load_destructive_test_database_config,
)


@dataclass(frozen=True)
class TransactionProbe:
    backend_pid: int
    transaction_id: int


def transaction_probe(session: Session) -> TransactionProbe:
    config = load_destructive_test_database_config(os.environ)
    connection = session.connection()
    assert_authorized_destructive_connection(connection, config)
    pid, transaction_id = connection.execute(
        select(func.pg_backend_pid(), func.pg_current_xact_id())
    ).one()
    probe = TransactionProbe(int(pid), int(transaction_id))
    print(f"PostgreSQL concurrency probe: {probe}")
    return probe


def wait_until_blocked(
    waiter_pid: int, blocker_pid: int, *, timeout_seconds: float = 5
) -> None:
    """Return only after PostgreSQL confirms the expected blocking connection."""
    config = load_destructive_test_database_config(os.environ)
    deadline = monotonic() + timeout_seconds
    with engine.connect() as connection:
        assert_authorized_destructive_connection(connection, config)
        while monotonic() < deadline:
            blockers = connection.scalar(select(func.pg_blocking_pids(waiter_pid))) or []
            if blocker_pid in blockers:
                print(f"PostgreSQL lock wait observed: waiter={waiter_pid}; blocker={blocker_pid}")
                return
            sleep(0.01)
    raise AssertionError(f"Backend {waiter_pid} did not wait for backend {blocker_pid}.")
