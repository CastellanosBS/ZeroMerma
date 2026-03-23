# apps/backend/src/zeromerma_api/services/cash_session_service.py
# PURPOSE:
#   Business logic for cash sessions (open/close).
#   Keeps routers minimal, deterministic, and aligned with canonical domain errors.

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from zeromerma_api.core.domain_errors import (
    DomainConflictError,
    DomainNotFoundError,
    DomainValidationError,
)
from zeromerma_api.models.cash_session import CashSession, CashSessionStatus


def utcnow() -> datetime:
    """
    Return a timezone-aware UTC timestamp.

    We prefer explicit UTC at the application layer even if DB defaults exist.
    """
    return datetime.now(timezone.utc)


def to_decimal(value: Decimal | float | int | str) -> Decimal:
    """
    Convert numeric-like input to Decimal safely.
    """
    return Decimal(str(value))


def get_current_open_session(db: Session, branch_id: int) -> CashSession | None:
    """
    Find the current OPEN cash session for a branch, if any.
    """
    stmt = select(CashSession).where(
        CashSession.branch_id == branch_id,
        CashSession.status == CashSessionStatus.OPEN.value,
    )
    return db.scalar(stmt)


def open_cash_session(
    db: Session,
    *,
    branch_id: int,
    opened_by_id: int,
    opening_amount: Decimal | float | int | str,
) -> CashSession:
    """
    Open a new cash session for a branch.

    Rules:
      - Only one OPEN session per branch.
      - opening_amount must be >= 0.
      - The INSERT must remain transactional.
      - Concurrent opens are prevented by the DB unique partial index.
    """
    opening_amount_dec = to_decimal(opening_amount)
    if opening_amount_dec < 0:
        raise DomainValidationError(
            message="Opening amount must be greater than or equal to zero.",
            details={"opening_amount": str(opening_amount_dec)},
        )

    existing = get_current_open_session(db, branch_id)
    if existing is not None:
        raise DomainConflictError(
            message=f"Branch {branch_id} already has an OPEN cash session.",
            details={
                "branch_id": int(branch_id),
                "cash_session_id": int(existing.id),
                "status": str(existing.status),
            },
        )

    cs = CashSession(
        branch_id=branch_id,
        opened_by_id=opened_by_id,
        opening_amount=opening_amount_dec,
        status=CashSessionStatus.OPEN.value,
        opened_at=utcnow(),
    )

    db.add(cs)

    try:
        db.flush()
    except IntegrityError as e:
        raise DomainConflictError(
            message="Cash session already open for this branch.",
            details={"branch_id": int(branch_id)},
        ) from e

    return cs


def close_cash_session(
    db: Session,
    *,
    session_id: int,
    closed_by_id: int,
    closing_amount: Decimal | float | int | str,
) -> CashSession:
    """
    Close an OPEN cash session.

    Rules:
      - Session must exist.
      - Session must be OPEN.
      - closing_amount must be >= 0.
      - On close we set:
          * status = CLOSED
          * closed_at
          * closed_by_id
          * closing_amount
    """
    closing_amount_dec = to_decimal(closing_amount)
    if closing_amount_dec < 0:
        raise DomainValidationError(
            message="Closing amount must be greater than or equal to zero.",
            details={"closing_amount": str(closing_amount_dec)},
        )

    cs = db.get(CashSession, session_id)
    if cs is None:
        raise DomainNotFoundError(
            message=f"Cash session {session_id} not found.",
            details={"cash_session_id": int(session_id)},
        )

    if cs.status != CashSessionStatus.OPEN.value:
        raise DomainConflictError(
            message=f"Cash session {session_id} is not OPEN.",
            details={
                "cash_session_id": int(session_id),
                "status": str(cs.status),
            },
        )

    cs.status = CashSessionStatus.CLOSED.value
    cs.closed_at = utcnow()
    cs.closed_by_id = closed_by_id
    cs.closing_amount = closing_amount_dec

    db.flush()
    return cs
