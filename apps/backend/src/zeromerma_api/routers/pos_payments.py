# apps/backend/src/zeromerma_api/routers/pos_payments.py
from __future__ import annotations

from fastapi import APIRouter

from zeromerma_api.core.authz import (
    POS_ALLOWED_ROLES,
    enforce_sale_access,
    require_ctx_role,
)
from zeromerma_api.core.dependency_aliases import ActiveAuthContextDep, DbSessionDep
from zeromerma_api.schemas.payment import PaymentCreate, PaymentOut
from zeromerma_api.schemas.sale import SaleDetailOut
from zeromerma_api.services.payment_service import add_payment, get_sale_detail

router = APIRouter(prefix="/sales", tags=["pos"])


@router.post("/{sale_id}/payments", response_model=PaymentOut)
def api_add_payment(
    sale_id: int,
    payload: PaymentCreate,
    db: DbSessionDep,
    ctx: ActiveAuthContextDep,
) -> PaymentOut:
    """
    Append a payment to a sale.

    Authorization:
      - POS role required
      - sale scope enforced
    """
    role_code = require_ctx_role(ctx=ctx, allowed_roles=POS_ALLOWED_ROLES)
    enforce_sale_access(
        db=db,
        current_user=ctx.user,
        role_code=role_code,
        sale_id=int(sale_id),
    )

    try:
        payment = add_payment(
            db=db,
            sale_id=int(sale_id),
            method=payload.method,
            amount=payload.amount,
            reference=payload.reference,
        )
        db.commit()
        db.refresh(payment)
        return PaymentOut.model_validate(payment)
    except Exception:
        db.rollback()
        raise


@router.get("/{sale_id}", response_model=SaleDetailOut)
def api_get_sale_detail(
    sale_id: int,
    db: DbSessionDep,
    ctx: ActiveAuthContextDep,
) -> SaleDetailOut:
    """
    Return a sale with items, payments, and computed paid/balance.
    """
    role_code = require_ctx_role(ctx=ctx, allowed_roles=POS_ALLOWED_ROLES)
    enforce_sale_access(
        db=db,
        current_user=ctx.user,
        role_code=role_code,
        sale_id=int(sale_id),
    )

    detail = get_sale_detail(db, int(sale_id))
    return SaleDetailOut.model_validate(detail)
