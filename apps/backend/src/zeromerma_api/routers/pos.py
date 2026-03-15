# apps/backend/src/zeromerma_api/routers/pos.py
# PURPOSE: POS endpoints (cash sessions) + mount sales/payments.
#
# AUTHORIZATION:
# - Only POS roles (ADMIN, CASHIER) can access POS endpoints.
# - Branch scoping:
#     * ADMIN -> any branch
#     * CASHIER -> only their own branch
#
# ANTI-IMPERSONATION:
# - opened_by_id and closed_by_id are derived from current_user.id, never from the client.

from __future__ import annotations

from typing import Generator

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from zeromerma_api.core.authz import (
    POS_ALLOWED_ROLES,
    enforce_branch_access,
    require_role,
)
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
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/cash-sessions/open", response_model=CashSessionOut)
def api_open_cash_session(
    payload: CashSessionOpenIn,
    db: Session = Depends(get_db),
    current_user: UserAccount = Depends(get_current_active_user),
):
    """
    Open a new cash session.
    Returns 409 if a session is already open for the branch.
    """
    role_code = require_role(
        db, current_user=current_user, allowed_roles=POS_ALLOWED_ROLES
    )
    enforce_branch_access(
        current_user=current_user, role_code=role_code, branch_id=payload.branch_id
    )

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
    Returns 404 if not found; 409 if already closed/canceled.
    """
    # Note: branch scoping is enforced inside service constraints (sale/session relations),
    # but we still enforce POS role here.
    _ = require_role(db, current_user=current_user, allowed_roles=POS_ALLOWED_ROLES)

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
    """
    role_code = require_role(
        db, current_user=current_user, allowed_roles=POS_ALLOWED_ROLES
    )
    enforce_branch_access(
        current_user=current_user, role_code=role_code, branch_id=branch_id
    )

    return get_current_open_session(db, branch_id=branch_id)


router.include_router(sales_router)
router.include_router(payments_router)
