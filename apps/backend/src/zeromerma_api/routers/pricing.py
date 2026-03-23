from __future__ import annotations

from fastapi import APIRouter, Query

from zeromerma_api.core.authz import ROLE_ADMIN, ROLE_CASHIER, require_ctx_role
from zeromerma_api.core.dependency_aliases import ActiveAuthContextDep, DbSessionDep
from zeromerma_api.core.domain_errors import (
    DomainAuthorizationError,
    DomainConflictError,
    DomainNotFoundError,
)
from zeromerma_api.schemas.pricing import (
    EffectivePriceRow,
    PriceOverrideOut,
    PriceOverrideUpsert,
)
from zeromerma_api.services.pricing_service import (
    delete_price_override,
    get_effective_price,
    list_effective_prices,
    upsert_price_override,
)

router = APIRouter(prefix="/pricing", tags=["pricing"])


def _enforce_same_branch_only(*, branch_id: int, ctx: ActiveAuthContextDep) -> None:
    """
    Pricing v1 policy:
      - users may only access/manage pricing for their own branch
      - ADMIN does not bypass this yet (no SUPERADMIN concept)
    """
    if int(ctx.user.branch_id) != int(branch_id):
        raise DomainAuthorizationError(
            message="Cross-branch pricing access is not allowed.",
            details={
                "requested_branch_id": int(branch_id),
                "user_branch_id": int(ctx.user.branch_id),
            },
        )


@router.get("/branches/{branch_id}/products", response_model=list[EffectivePriceRow])
def api_list_effective_prices(
    branch_id: int,
    db: DbSessionDep,
    ctx: ActiveAuthContextDep,
    include_inactive: bool = Query(False),
    category_id: int | None = Query(None, ge=1),
    is_input: bool | None = Query(None),
    q: str | None = Query(None, min_length=1, max_length=200),
    limit: int = Query(200, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> list[EffectivePriceRow]:
    """
    List effective prices for a branch.
    """
    require_ctx_role(ctx=ctx, allowed_roles={ROLE_ADMIN, ROLE_CASHIER})
    _enforce_same_branch_only(branch_id=branch_id, ctx=ctx)

    rows = list_effective_prices(
        db,
        branch_id=branch_id,
        include_inactive=include_inactive,
        category_id=category_id,
        is_input=is_input,
        q=q,
        limit=limit,
        offset=offset,
    )
    return [EffectivePriceRow.model_validate(r) for r in rows]


@router.get("/branches/{branch_id}/products/{product_id}", response_model=EffectivePriceRow)
def api_get_effective_price(
    branch_id: int,
    product_id: int,
    db: DbSessionDep,
    ctx: ActiveAuthContextDep,
) -> EffectivePriceRow:
    """
    Get effective price for one product at a branch.
    """
    require_ctx_role(ctx=ctx, allowed_roles={ROLE_ADMIN, ROLE_CASHIER})
    _enforce_same_branch_only(branch_id=branch_id, ctx=ctx)

    try:
        row = get_effective_price(db, branch_id=branch_id, product_id=product_id)
        return EffectivePriceRow.model_validate(row)
    except LookupError as e:
        raise DomainNotFoundError(message=str(e)) from e


@router.put("/branches/{branch_id}/products/{product_id}", response_model=PriceOverrideOut)
def api_upsert_price_override(
    branch_id: int,
    product_id: int,
    payload: PriceOverrideUpsert,
    db: DbSessionDep,
    ctx: ActiveAuthContextDep,
) -> PriceOverrideOut:
    """
    Upsert a branch override price (ADMIN only).
    """
    require_ctx_role(ctx=ctx, allowed_roles={ROLE_ADMIN})
    _enforce_same_branch_only(branch_id=branch_id, ctx=ctx)

    try:
        row = upsert_price_override(
            db,
            branch_id=branch_id,
            product_id=product_id,
            price=payload.price,
            currency=payload.currency,
            created_by_id=int(ctx.user.id),
        )
        db.commit()
        return PriceOverrideOut.model_validate(row)
    except LookupError as e:
        db.rollback()
        raise DomainNotFoundError(message=str(e)) from e
    except ValueError as e:
        db.rollback()
        raise DomainConflictError(message=str(e)) from e
    except Exception:
        db.rollback()
        raise


@router.delete("/branches/{branch_id}/products/{product_id}")
def api_delete_price_override(
    branch_id: int,
    product_id: int,
    db: DbSessionDep,
    ctx: ActiveAuthContextDep,
) -> dict[str, bool]:
    """
    Delete an override (ADMIN only).
    """
    require_ctx_role(ctx=ctx, allowed_roles={ROLE_ADMIN})
    _enforce_same_branch_only(branch_id=branch_id, ctx=ctx)

    deleted = delete_price_override(db, branch_id=branch_id, product_id=product_id)
    db.commit()
    return {"deleted": bool(deleted)}
