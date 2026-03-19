# apps/backend/src/zeromerma_api/routers/pos_payments.py
# PURPOSE:
#   Payments endpoints under POS.
#   Mounted under /pos via routers/pos.py.
#
# AUTHORIZATION (role-based + sale scoping):
#   - Allowed roles: ADMIN, CASHIER
#   - Sale scope:
#       * ADMIN -> can access any sale
#       * CASHIER -> sale must belong to their branch
#
# FAST-PATH (role-coded JWT):
#   - role_code is read from JWT claims via AuthContext.
#   - No per-request DB lookup to resolve role.code.

from __future__ import annotations

from typing import Generator

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from zeromerma_api.core.auth_context import AuthContext
from zeromerma_api.core.authz import (
    POS_ALLOWED_ROLES,
    enforce_sale_access,
    require_ctx_role,
)
from zeromerma_api.core.deps_auth import get_current_active_auth_context
from zeromerma_api.db.engine import SessionLocal
from zeromerma_api.schemas.payment import PaymentCreate, PaymentOut
from zeromerma_api.schemas.sale import SaleDetailOut
from zeromerma_api.services.payment_service import add_payment, get_sale_detail

router = APIRouter(prefix="/sales", tags=["pos"])  # paths: /pos/sales/{id}/...


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


@router.post("/{sale_id}/payments", response_model=PaymentOut)
def api_add_payment(
    sale_id: int,
    payload: PaymentCreate,
    db: Session = Depends(get_db),
    ctx: AuthContext = Depends(get_current_active_auth_context),
):
    """
    Append a payment to a sale.

    Security:
      - Role check via ctx.role_code.
      - Sale scoping enforced (cashier can't pay other branch sales).
    """
    role_code = require_ctx_role(ctx=ctx, allowed_roles=POS_ALLOWED_ROLES)
    enforce_sale_access(
        db, current_user=ctx.user, role_code=role_code, sale_id=int(sale_id)
    )

    try:
        p = add_payment(
            db,
            sale_id=int(sale_id),
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
    ctx: AuthContext = Depends(get_current_active_auth_context),
):
    """
    Return a sale with items, payments, and computed paid/balance.

    Security:
      - Role check via ctx.role_code.
      - Sale scoping enforced.
    """
    role_code = require_ctx_role(ctx=ctx, allowed_roles=POS_ALLOWED_ROLES)
    enforce_sale_access(
        db, current_user=ctx.user, role_code=role_code, sale_id=int(sale_id)
    )

    try:
        return get_sale_detail(db, int(sale_id))
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
