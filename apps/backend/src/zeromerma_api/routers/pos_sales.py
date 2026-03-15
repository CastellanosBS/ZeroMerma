# apps/backend/src/zeromerma_api/routers/pos_sales.py
# PURPOSE:
#   Sales endpoints under the POS area.
#
# AUTHORIZATION:
#   - Only POS roles (ADMIN, CASHIER) can create/list sales.
#   - Branch scoping:
#       * ADMIN -> any branch
#       * CASHIER -> only their own branch
#
# ANTI-IMPERSONATION:
#   - created_by_id is derived from current_user.id, never from the client.

from __future__ import annotations

from typing import Generator, List, Optional

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
from zeromerma_api.schemas.sale import SaleCreate, SaleOut
from zeromerma_api.services.sale_service import create_sale, list_sales

router = APIRouter(prefix="/sales", tags=["pos"])  # final path: /pos/sales


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("", response_model=SaleOut)
def api_create_sale(
    payload: SaleCreate,
    db: Session = Depends(get_db),
    current_user: UserAccount = Depends(get_current_active_user),
):
    """
    Create a sale + items transactionally.
    """
    role_code = require_role(
        db, current_user=current_user, allowed_roles=POS_ALLOWED_ROLES
    )
    enforce_branch_access(
        current_user=current_user, role_code=role_code, branch_id=payload.branch_id
    )

    try:
        sale = create_sale(
            db,
            branch_id=payload.branch_id,
            cash_session_id=payload.cash_session_id,
            created_by_id=int(current_user.id),  # derived from token
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
    current_user: UserAccount = Depends(get_current_active_user),
):
    """
    List sales (newest first) with optional filters and paging.

    Branch scoping:
      - If branch_id is omitted, default to user's own branch.
      - If branch_id is provided, enforce authorization for that branch.
    """
    role_code = require_role(
        db, current_user=current_user, allowed_roles=POS_ALLOWED_ROLES
    )

    effective_branch_id = (
        branch_id if branch_id is not None else int(current_user.branch_id)
    )
    enforce_branch_access(
        current_user=current_user,
        role_code=role_code,
        branch_id=int(effective_branch_id),
    )

    return list_sales(
        db,
        branch_id=int(effective_branch_id),
        cash_session_id=cash_session_id,
        limit=limit,
        offset=offset,
    )
