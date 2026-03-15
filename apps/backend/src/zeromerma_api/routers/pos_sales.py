# apps/backend/src/zeromerma_api/routers/pos_sales.py
# PURPOSE:
#   Sales endpoints under the POS area.
#   Mounted under /pos via routers/pos.py (so this file uses prefix="/sales").
#
# SECURITY NOTE (anti-impersonation):
#   - The client must NOT control created_by_id.
#   - created_by_id is derived from the authenticated user (JWT -> current_user.id).
#   - Optional branch scoping: user can only operate on their own branch for now.

from __future__ import annotations

from typing import Generator, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from zeromerma_api.core.deps_auth import get_current_active_user
from zeromerma_api.db.engine import SessionLocal
from zeromerma_api.models.user_account import UserAccount
from zeromerma_api.schemas.sale import SaleCreate, SaleOut
from zeromerma_api.services.sale_service import create_sale, list_sales

router = APIRouter(prefix="/sales", tags=["pos"])  # final path becomes /pos/sales


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
    Minimal authorization rule:
    - Non-admin users can only operate within their own branch.
    """
    if int(current_user.branch_id) != int(branch_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: user cannot operate on the requested branch.",
        )


@router.post("", response_model=SaleOut)
def api_create_sale(
    payload: SaleCreate,
    db: Session = Depends(get_db),
    current_user: UserAccount = Depends(get_current_active_user),
):
    """
    Create a sale + items transactionally.

    Anti-impersonation:
      - Ignore payload.created_by_id (if present in the schema).
      - Use current_user.id as the canonical actor.

    Authorization:
      - Enforce that the sale branch matches current_user.branch_id (for now).
    """
    _enforce_branch_scope(current_user=current_user, branch_id=payload.branch_id)

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

    Authorization defaults:
      - If branch_id is not provided, default to current_user.branch_id.
      - If branch_id is provided and differs, reject (403).
    """
    effective_branch_id = (
        branch_id if branch_id is not None else int(current_user.branch_id)
    )
    _enforce_branch_scope(current_user=current_user, branch_id=effective_branch_id)

    return list_sales(
        db,
        branch_id=effective_branch_id,
        cash_session_id=cash_session_id,
        limit=limit,
        offset=offset,
    )
