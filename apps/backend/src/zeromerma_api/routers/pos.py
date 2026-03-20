# apps/backend/src/zeromerma_api/routers/pos.py
# PURPOSE:
#   POS endpoints (cash sessions) and mounting of sales/payments routers.
#
# AUTHORIZATION (role-based + branch scoping):
#   - Allowed roles: ADMIN, CASHIER
#   - Branch scope:
#       * ADMIN -> any branch
#       * CASHIER -> only their own branch
#
# FAST-PATH (role-coded JWT):
#   - role_code is read from JWT claims via AuthContext.
#   - No per-request DB lookup to resolve role.code.
#
# ANTI-IMPERSONATION:
#   - opened_by_id and closed_by_id are derived from ctx.user.id (token identity),
#     never from client payload.

from __future__ import annotations

from typing import Generator

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from zeromerma_api.core.auth_context import AuthContext
from zeromerma_api.core.authz import (
    POS_ALLOWED_ROLES,
    enforce_branch_access,
    require_ctx_role,
)
from zeromerma_api.core.deps_auth import get_current_active_auth_context
from zeromerma_api.db.engine import SessionLocal
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
    FastAPI DB dependency: open a session, yield it to the handler,
    and always close it afterwards.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _cash_session_branch_id(db: Session, *, session_id: int) -> int | None:
    """
    Resolve cash_session.branch_id for authorization checks.

    We do this because closing a session uses a path parameter (session_id),
    and we must ensure the session belongs to a branch the user can access.
    """
    return db.execute(
        text("SELECT branch_id FROM cash_session WHERE id = :id"),
        {"id": int(session_id)},
    ).scalar_one_or_none()


@router.post("/cash-sessions/open", response_model=CashSessionOut)
def api_open_cash_session(
    payload: CashSessionOpenIn,
    db: Session = Depends(get_db),
    ctx: AuthContext = Depends(get_current_active_auth_context),
):
    """
    Open a new cash session.

    Security:
      - Role check is performed using ctx.role_code (JWT claim).
      - Branch scoping is enforced:
          * ADMIN can open for any branch
          * CASHIER can only open for their own branch
      - opened_by_id is derived from ctx.user.id (token identity).
    """
    role_code = require_ctx_role(ctx=ctx, allowed_roles=POS_ALLOWED_ROLES)
    enforce_branch_access(
        current_user=ctx.user,
        role_code=role_code,
        branch_id=int(payload.branch_id),
    )

    try:
        cs = open_cash_session(
            db=db,
            branch_id=int(payload.branch_id),
            opened_by_id=int(ctx.user.id),  # derived from token
            opening_amount=payload.opening_amount,
        )
        db.commit()
        db.refresh(cs)
        return cs
    except ValueError as e:
        db.rollback()
        # 409 Conflict: business rule conflict (already open, etc.)
        raise HTTPException(status_code=409, detail=str(e)) from e


@router.post("/cash-sessions/{session_id}/close", response_model=CashSessionOut)
def api_close_cash_session(
    session_id: int,
    payload: CashSessionCloseIn,
    db: Session = Depends(get_db),
    ctx: AuthContext = Depends(get_current_active_auth_context),
):
    """
    Close an OPEN cash session.

    Security:
      - Role check via ctx.role_code.
      - Branch scoping based on the session's branch_id:
          * ADMIN can close any session
          * CASHIER can only close sessions in their own branch
      - closed_by_id is derived from ctx.user.id (token identity).
    """
    role_code = require_ctx_role(ctx=ctx, allowed_roles=POS_ALLOWED_ROLES)

    branch_id = _cash_session_branch_id(db, session_id=session_id)
    if branch_id is None:
        # Align with service behavior: session not found
        raise HTTPException(
            status_code=404, detail=f"Cash session {session_id} not found."
        )

    enforce_branch_access(
        current_user=ctx.user,
        role_code=role_code,
        branch_id=int(branch_id),
    )

    try:
        cs = close_cash_session(
            db=db,
            session_id=int(session_id),
            closed_by_id=int(ctx.user.id),  # derived from token
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
    ctx: AuthContext = Depends(get_current_active_auth_context),
):
    """
    Return the current OPEN cash session for a branch (or null if none).

    Security:
      - Role check via ctx.role_code.
      - Branch scoping enforced.
    """
    role_code = require_ctx_role(ctx=ctx, allowed_roles=POS_ALLOWED_ROLES)
    enforce_branch_access(
        current_user=ctx.user,
        role_code=role_code,
        branch_id=int(branch_id),
    )

    return get_current_open_session(db, branch_id=int(branch_id))


# Mount sub-routers under /pos
router.include_router(sales_router)
router.include_router(payments_router)
