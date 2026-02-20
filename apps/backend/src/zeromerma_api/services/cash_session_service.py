# apps/backend/src/zeromerma_api/services/cash_session_service.py
# PURPOSE: Business logic for cash sessions (open/close).
#          Keeps routers minimal and consistent.

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from zeromerma_api.models.cash_session import CashSession, CashSessionStatus


def utcnow() -> datetime:
    """
    Return a timezone-aware UTC timestamp.
    We prefer explicit UTC at the app layer even if DB defaults exist.
    """
    return datetime.now(timezone.utc)


def get_current_open_session(db: Session, branch_id: int) -> CashSession | None:
    """
    Find the current OPEN cash session for a branch (if any).
    """
    stmt = select(CashSession).where(
        CashSession.branch_id == branch_id,
        CashSession.status == CashSessionStatus.OPEN.value,
    )
    return db.scalar(stmt)


def open_cash_session(
    db: Session, branch_id: int, opened_by_id: int, opening_amount: float
) -> CashSession:
    """
    Open a new cash session for a branch.

    Rules:
      - Only one OPEN session per branch.
      - Insert must be transactional.
      - If concurrent opens happen, DB unique index prevents duplicates.
    """
    # 1) Friendly app-level check (better UX than raw IntegrityError)
    existing = get_current_open_session(db, branch_id)
    if existing is not None:
        raise ValueError(
            f"Branch {branch_id} already has an OPEN cash session (id={existing.id})."
        )

    # 2) Create the new session row.
    cs = CashSession(
        branch_id=branch_id,
        opened_by_id=opened_by_id,
        opening_amount=opening_amount,
        status=CashSessionStatus.OPEN.value,
        opened_at=utcnow(),
    )

    db.add(cs)

    # 3) Flush to force INSERT now (so we catch DB constraint errors here, inside this function).
    try:
        db.flush()
    except IntegrityError as e:
        # DB-level protection (race condition): two opens at same time.
        raise ValueError(
            "Cash session already open for this branch (DB constraint)."
        ) from e

    # 4) Return ORM object (still inside transaction; caller should commit).
    return cs


def close_cash_session(
    db: Session, session_id: int, closed_by_id: int, closing_amount: float
) -> CashSession:
    """
    Close an OPEN cash session.

    Rules:
      - Session must exist.
      - Must be OPEN to close.
      - Set status=CLOSED, closed_at, closed_by_id, closing_amount.
    """
    cs = db.get(CashSession, session_id)
    if cs is None:
        raise LookupError(f"Cash session {session_id} not found.")

    if cs.status != CashSessionStatus.OPEN.value:
        raise ValueError(
            f"Cash session {session_id} is not OPEN (current status={cs.status})."
        )

    cs.status = CashSessionStatus.CLOSED.value
    cs.closed_at = utcnow()
    cs.closed_by_id = closed_by_id
    cs.closing_amount = closing_amount

    db.flush()
    return cs
