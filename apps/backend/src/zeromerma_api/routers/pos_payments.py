# apps/backend/src/zeromerma_api/routers/pos_payments.py
# PURPOSE:
#   Payments endpoints under POS.
#   Mounted under /pos via routers/pos.py.
#
# SECURITY NOTE:
#   - Although payments do not carry created_by_id yet, we still enforce:
#       1) authenticated user
#       2) branch scoping (sale must belong to current_user.branch_id)

from __future__ import annotations

from typing import Generator

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from zeromerma_api.core.deps_auth import get_current_active_user
from zeromerma_api.db.engine import SessionLocal
from zeromerma_api.models.user_account import UserAccount
from zeromerma_api.schemas.payment import PaymentCreate, PaymentOut
from zeromerma_api.schemas.sale import SaleDetailOut
from zeromerma_api.services.payment_service import add_payment, get_sale_detail

router = APIRouter(prefix="/sales", tags=["pos"])  # paths: /pos/sales/{id}/...


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI DB dependency: open a session, yield it, always close it.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _sale_branch_id(db: Session, *, sale_id: int) -> int | None:
    """
    Fetch the branch_id for a sale, or None if the sale does not exist.
    """
    return db.execute(
        text("SELECT branch_id FROM sale WHERE id = :id"),
        {"id": int(sale_id)},
    ).scalar_one_or_none()


def _enforce_sale_branch_scope(
    db: Session, *, sale_id: int, current_user: UserAccount
) -> None:
    """
    Enforce that the requested sale belongs to current_user.branch_id.

    Raises:
      - 404 if sale not found
      - 403 if sale belongs to a different branch
    """
    branch_id = _sale_branch_id(db, sale_id=sale_id)
    if branch_id is None:
        raise HTTPException(status_code=404, detail=f"Sale {sale_id} not found.")

    if int(branch_id) != int(current_user.branch_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: sale belongs to a different branch.",
        )


@router.post("/{sale_id}/payments", response_model=PaymentOut)
def api_add_payment(
    sale_id: int,
    payload: PaymentCreate,
    db: Session = Depends(get_db),
    current_user: UserAccount = Depends(get_current_active_user),
):
    """
    Append a payment to a sale.

    Authorization:
      - Sale must belong to current_user.branch_id.
    """
    _enforce_sale_branch_scope(db, sale_id=sale_id, current_user=current_user)

    try:
        p = add_payment(
            db,
            sale_id=sale_id,
            method=payload.method,
            amount=payload.amount,
            reference=payload.reference,
        )
        db.commit()
        db.refresh(p)
        return p

    except LookupError as e:
        db.rollback()
        raise HTTPException(status_code=404, detail=str(e)) from e

    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(e)) from e

    except Exception:
        db.rollback()
        raise


@router.get("/{sale_id}", response_model=SaleDetailOut)
def api_get_sale_detail(
    sale_id: int,
    db: Session = Depends(get_db),
    current_user: UserAccount = Depends(get_current_active_user),
):
    """
    Return a sale with items, payments, and computed paid/balance.

    Authorization:
      - Sale must belong to current_user.branch_id.
    """
    _enforce_sale_branch_scope(db, sale_id=sale_id, current_user=current_user)

    try:
        return get_sale_detail(db, sale_id)
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
