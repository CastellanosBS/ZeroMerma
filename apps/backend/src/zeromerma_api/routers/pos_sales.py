from __future__ import annotations

from fastapi import APIRouter, Query

from zeromerma_api.core.authz import (
    POS_ALLOWED_ROLES,
    enforce_branch_access,
    require_ctx_role,
)
from zeromerma_api.core.dependency_aliases import ActiveAuthContextDep, DbSessionDep
from zeromerma_api.schemas.sale import SaleCreate, SaleOut
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

    Authorization:
      - POS role required
      - branch scope enforced only when branch_id is explicit
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
