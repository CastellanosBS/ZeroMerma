from __future__ import annotations

from fastapi import APIRouter, Query

from zeromerma_api.core.authz import (
    POS_ALLOWED_ROLES,
    enforce_branch_access,
    enforce_sale_access,
    require_ctx_role,
)
from zeromerma_api.core.dependency_aliases import ActiveAuthContextDep, DbSessionDep
from zeromerma_api.schemas.sale import SaleCreate, SaleOut
from zeromerma_api.schemas.sale_reversal import (
    SaleRefundIn,
    SaleReversalOut,
    SaleVoidIn,
)
from zeromerma_api.services.sale_reversal_service import refund_sale, void_sale
from zeromerma_api.services.sale_service import create_sale, list_sales

router = APIRouter(prefix="/sales", tags=["pos"])


@router.post("", response_model=SaleOut, summary="Create a sale")
def api_create_sale(
    payload: SaleCreate,
    db: DbSessionDep,
    ctx: ActiveAuthContextDep,
) -> SaleOut:
    """
    Create a sale transactionally.

    The authenticated user is always the creator of the sale.
    """
    role_code = require_ctx_role(ctx=ctx, allowed_roles=POS_ALLOWED_ROLES)
    enforce_branch_access(
        current_user=ctx.user,
        role_code=role_code,
        branch_id=int(payload.branch_id),
    )

    try:
        sale = create_sale(
            db=db,
            branch_id=int(payload.branch_id),
            cash_session_id=int(payload.cash_session_id),
            created_by_id=int(ctx.user.id),
            items=[item.model_dump(exclude_none=True) for item in payload.items],
        )
        db.commit()
        db.refresh(sale)
        return SaleOut.model_validate(sale)
    except Exception:
        db.rollback()
        raise


@router.get("", response_model=list[SaleOut], summary="List sales")
def api_list_sales(
    db: DbSessionDep,
    ctx: ActiveAuthContextDep,
    branch_id: int | None = Query(None, ge=1),
    cash_session_id: int | None = Query(None, ge=1),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> list[SaleOut]:
    """
    List sales with optional filters.
    """
    role_code = require_ctx_role(ctx=ctx, allowed_roles=POS_ALLOWED_ROLES)

    if branch_id is not None:
        enforce_branch_access(
            current_user=ctx.user,
            role_code=role_code,
            branch_id=int(branch_id),
        )

    sales = list_sales(
        db=db,
        branch_id=branch_id,
        cash_session_id=cash_session_id,
        limit=limit,
        offset=offset,
    )
    return [SaleOut.model_validate(s) for s in sales]


@router.post("/{sale_id}/void", response_model=SaleReversalOut, summary="Void an unpaid open sale")
def api_void_sale(
    sale_id: int,
    payload: SaleVoidIn,
    db: DbSessionDep,
    ctx: ActiveAuthContextDep,
) -> SaleReversalOut:
    """
    Void one OPEN unpaid sale.

    This route is for operational cancellation before money collection has been
    finalized. It restores inventory and preserves a reversal audit snapshot.
    """
    role_code = require_ctx_role(ctx=ctx, allowed_roles=POS_ALLOWED_ROLES)
    enforce_sale_access(
        db=db,
        current_user=ctx.user,
        role_code=role_code,
        sale_id=int(sale_id),
    )

    try:
        result = void_sale(
            db=db,
            sale_id=int(sale_id),
            actor_user_id=int(ctx.user.id),
            reason=payload.reason,
        )
        db.commit()
        return SaleReversalOut.model_validate(result)
    except Exception:
        db.rollback()
        raise


@router.post(
    "/{sale_id}/refund", response_model=SaleReversalOut, summary="Fully refund a paid sale"
)
def api_refund_sale(
    sale_id: int,
    payload: SaleRefundIn,
    db: DbSessionDep,
    ctx: ActiveAuthContextDep,
) -> SaleReversalOut:
    """
    Fully refund one PAID sale.

    This block implements only full refunds. It mirrors original payment lines
    as negative payments, restores inventory, and preserves a reversal audit
    snapshot.
    """
    role_code = require_ctx_role(ctx=ctx, allowed_roles=POS_ALLOWED_ROLES)
    enforce_sale_access(
        db=db,
        current_user=ctx.user,
        role_code=role_code,
        sale_id=int(sale_id),
    )

    try:
        result = refund_sale(
            db=db,
            sale_id=int(sale_id),
            actor_user_id=int(ctx.user.id),
            reason=payload.reason,
        )
        db.commit()
        return SaleReversalOut.model_validate(result)
    except Exception:
        db.rollback()
        raise
