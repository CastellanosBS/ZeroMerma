# apps/backend/src/zeromerma_api/routers/pos.py
# PURPOSE: POS endpoints (starting with cash sessions).
#          Later we will add sales/payments here.

from __future__ import annotations

from typing import Generator

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from zeromerma_api.db.engine import SessionLocal
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
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/cash-sessions/open", response_model=CashSessionOut)
def api_open_cash_session(payload: CashSessionOpenIn, db: Session = Depends(get_db)):
    """
    Open a new cash session.
    Returns 409 if a session is already open for the branch.
    """
    try:
        cs = open_cash_session(
            db=db,
            branch_id=payload.branch_id,
            opened_by_id=payload.opened_by_id,
            opening_amount=payload.opening_amount,
        )
        db.commit()
        db.refresh(cs)
        return cs
    except ValueError as e:
        db.rollback()
        # 409 Conflict: resource state prevents the action (session already open).
        raise HTTPException(status_code=409, detail=str(e)) from e


@router.post("/cash-sessions/{session_id}/close", response_model=CashSessionOut)
def api_close_cash_session(
    session_id: int, payload: CashSessionCloseIn, db: Session = Depends(get_db)
):
    """
    Close an OPEN cash session.
    Returns 404 if not found; 409 if already closed/canceled.
    """
    try:
        cs = close_cash_session(
            db=db,
            session_id=session_id,
            closed_by_id=payload.closed_by_id,
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
):
    """
    Return the current OPEN cash session for a branch (or null if none).
    """
    cs = get_current_open_session(db, branch_id=branch_id)
    return cs


router.include_router(sales_router)
