# apps/backend/src/zeromerma_api/routers/pos_payments.py
# PURPOSE:
#   Payments endpoints under POS.
#
# AUTHORIZATION:
#   - Only POS roles (ADMIN, CASHIER) can add/view payments.
#   - Sale scoping:
#       * ADMIN -> can access any sale
#       * CASHIER -> sale must belong to their branch

from __future__ import annotations

from typing import Generator

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from zeromerma_api.core.authz import (
    POS_ALLOWED_ROLES,
    enforce_sale_access,
    require_role,
)
from zeromerma_api.core.deps_auth import get_current_active_user
from zeromerma_api.db.engine import SessionLocal
from zeromerma_api.models.user_account import UserAccount
from zeromerma_api.schemas.payment import PaymentCreate, PaymentOut
from zeromerma_api.schemas.sale import SaleDetailOut
from zeromerma_api.services.payment_service import add_payment, get_sale_detail

router = APIRouter(prefix="/sales", tags=["pos"])  # paths: /pos/sales/{id}/...


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/{sale_id}/payments", response_model=PaymentOut)
def api_add_payment(
    sale_id: int,
    payload: PaymentCreate,
    db: Session = Depends(get_db),
    current_user: UserAccount = Depends(get_current_active_user),
):
    """
    Append a payment to a sale.
    """
    role_code = require_role(
        db, current_user=current_user, allowed_roles=POS_ALLOWED_ROLES
    )
    enforce_sale_access(
        db, current_user=current_user, role_code=role_code, sale_id=sale_id
    )

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
    """
    role_code = require_role(
        db, current_user=current_user, allowed_roles=POS_ALLOWED_ROLES
    )
    enforce_sale_access(
        db, current_user=current_user, role_code=role_code, sale_id=sale_id
    )

    try:
        return get_sale_detail(db, sale_id)
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
