# apps/backend/src/zeromerma_api/routers/pos_sales.py
# PURPOSE:
#   Sales endpoints under the POS area.
#
# AUTHORIZATION:
#   - Allowed roles: ADMIN, CASHIER
#   - Branch scoping:
#       * ADMIN -> any branch
#       * CASHIER -> only their own branch
#
# FAST-PATH (role-coded JWT):
#   - role_code is read from JWT claims via AuthContext.
#   - No per-request DB lookup to resolve role.code.

from __future__ import annotations

from typing import Generator, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from zeromerma_api.core.auth_context import AuthContext
from zeromerma_api.core.authz import (
    POS_ALLOWED_ROLES,
    enforce_branch_access,
    require_ctx_role,
)
from zeromerma_api.core.deps_auth import get_current_active_auth_context
from zeromerma_api.db.engine import SessionLocal
from zeromerma_api.schemas.sale import SaleCreate, SaleOut
from zeromerma_api.services.sale_service import create_sale, list_sales

router = APIRouter(prefix="/sales", tags=["pos"])  # final path: /pos/sales


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI DB dependency: open a session, yield it, always close it.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("", response_model=SaleOut)
def api_create_sale(
    payload: SaleCreate,
    db: Session = Depends(get_db),
    ctx: AuthContext = Depends(get_current_active_auth_context),
):
    """
    Create a sale + items transactionally.

    Anti-impersonation:
      - created_by_id is derived from ctx.user.id (JWT identity), never from client.

    Error mapping:
      - 404: referenced objects do not exist
      - 409: business rule conflicts (session not OPEN / wrong branch / insufficient stock)
    """
    # Enforce role without DB lookup (role_code comes from token claim)
    role_code = require_ctx_role(ctx=ctx, allowed_roles=POS_ALLOWED_ROLES)

    # Enforce branch scope
    enforce_branch_access(
        current_user=ctx.user,
        role_code=role_code,
        branch_id=int(payload.branch_id),
    )

    try:
        sale = create_sale(
            db,
            branch_id=int(payload.branch_id),
            cash_session_id=int(payload.cash_session_id),
            created_by_id=int(ctx.user.id),  # derived from token
            items=[it.model_dump() for it in payload.items],
        )
        db.commit()
        db.refresh(sale)
        return sale

    except LookupError as e:
        db.rollback()
        raise HTTPException(status_code=404, detail=str(e)) from e

    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(e)) from e

    except Exception:
        db.rollback()
        raise


@router.get("", response_model=List[SaleOut])
def api_list_sales(
    branch_id: Optional[int] = Query(None, ge=1),
    cash_session_id: Optional[int] = Query(None, ge=1),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    ctx: AuthContext = Depends(get_current_active_auth_context),
):
    """
    List sales (newest first) with optional filters and paging.

    Branch scoping:
      - If branch_id is omitted, default to ctx.user.branch_id.
      - If branch_id is provided, enforce scope (ADMIN can query any branch).
    """
    role_code = require_ctx_role(ctx=ctx, allowed_roles=POS_ALLOWED_ROLES)

    effective_branch_id = (
        int(branch_id) if branch_id is not None else int(ctx.user.branch_id)
    )
    enforce_branch_access(
        current_user=ctx.user,
        role_code=role_code,
        branch_id=effective_branch_id,
    )

    return list_sales(
        db,
        branch_id=effective_branch_id,
        cash_session_id=cash_session_id,
        limit=int(limit),
        offset=int(offset),
    )
