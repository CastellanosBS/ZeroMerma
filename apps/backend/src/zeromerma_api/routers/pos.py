# apps/backend/src/zeromerma_api/routers/pos.py
# PURPOSE:
#   POS endpoints (cash sessions + mount sales/payments).
#
# SECURITY NOTE (anti-impersonation):
#   - The client must NOT be trusted for actor identifiers (opened_by_id/closed_by_id).
#   - We derive the actor from the authenticated user (JWT -> current_user.id).

from __future__ import annotations

from typing import Generator

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from zeromerma_api.core.deps_auth import get_current_active_user
from zeromerma_api.db.engine import SessionLocal
from zeromerma_api.models.user_account import UserAccount
from zeromerma_api.routers.pos_payments import router as payments_router
from zeromerma_api.routers.pos_sales import router as sales_router
from zeromerma_api.schemas.cash_session import (
    CashSessionCloseIn,
    CashSessionOpenIn,
    CashSessionOut,
)
from zeromerma_api.services.cash_session_service import (
    close_cash_session,
    get_current_open_session,
    open_cash_session,
)

router = APIRouter(prefix="/pos", tags=["pos"])


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI DB dependency: open a session, yield it, always close it.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _enforce_branch_scope(*, current_user: UserAccount, branch_id: int) -> None:
    """
    Enforce that the authenticated user can only operate on their own branch.

    This is a minimal authorization rule until we add roles (ADMIN multi-branch).
    """
    if int(current_user.branch_id) != int(branch_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: user cannot operate on the requested branch.",
        )


@router.post("/cash-sessions/open", response_model=CashSessionOut)
def api_open_cash_session(
    payload: CashSessionOpenIn,
    db: Session = Depends(get_db),
    current_user: UserAccount = Depends(get_current_active_user),
):
    """
    Open a new cash session.

    Anti-impersonation:
      - We ignore any opened_by_id sent by the client.
      - The opener is always the authenticated user.
    """
    _enforce_branch_scope(current_user=current_user, branch_id=payload.branch_id)

    try:
        cs = open_cash_session(
            db=db,
            branch_id=payload.branch_id,
            opened_by_id=int(current_user.id),  # derived from token
            opening_amount=payload.opening_amount,
        )
        db.commit()
        db.refresh(cs)
        return cs
    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(e)) from e


@router.post("/cash-sessions/{session_id}/close", response_model=CashSessionOut)
def api_close_cash_session(
    session_id: int,
    payload: CashSessionCloseIn,
    db: Session = Depends(get_db),
    current_user: UserAccount = Depends(get_current_active_user),
):
    """
    Close an OPEN cash session.

    Anti-impersonation:
      - We ignore any closed_by_id sent by the client.
      - The closer is always the authenticated user.
    """
    try:
        cs = close_cash_session(
            db=db,
            session_id=session_id,
            closed_by_id=int(current_user.id),  # derived from token
            closing_amount=payload.closing_amount,
        )
        db.commit()
        db.refresh(cs)
        return cs

    except LookupError as e:
        db.rollback()
        raise HTTPException(status_code=404, detail=str(e)) from e

    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(e)) from e


@router.get("/cash-sessions/current", response_model=CashSessionOut | None)
def api_current_cash_session(
    branch_id: int = Query(..., ge=1),
    db: Session = Depends(get_db),
    current_user: UserAccount = Depends(get_current_active_user),
):
    """
    Return the current OPEN cash session for a branch (or null if none).

    Authorization:
      - Users can only query their own branch for now.
    """
    _enforce_branch_scope(current_user=current_user, branch_id=branch_id)
    return get_current_open_session(db, branch_id=branch_id)


# Mount sub-routers under /pos
router.include_router(sales_router)
router.include_router(payments_router)
