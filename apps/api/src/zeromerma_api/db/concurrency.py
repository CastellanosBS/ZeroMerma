"""Retryable PostgreSQL transaction conflicts, independent of business outcomes."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

RETRYABLE_SQLSTATES = frozenset({"55P03", "40P01", "40001"})


class CommandConcurrencyConflict(Exception):
    """The whole command rolled back; its original intention can be retried."""

    code = "CONCURRENCY_RETRY"
    message = "Another operation conflicted with this command. Retry the same intention."


def is_retryable_transaction_error(error: BaseException) -> bool:
    return isinstance(error, DBAPIError) and getattr(error.orig, "sqlstate", None) in (
        RETRYABLE_SQLSTATES
    )


def set_command_lock_timeout(session: Session, milliseconds: int) -> str:
    """Bound each lock wait only for the current transaction, preserving its prior value."""
    previous = str(session.scalar(select(func.current_setting("lock_timeout"))))
    session.execute(select(func.set_config("lock_timeout", f"{milliseconds}ms", True)))
    return previous


def restore_command_lock_timeout(session: Session, previous: str) -> None:
    session.execute(select(func.set_config("lock_timeout", previous, True)))
