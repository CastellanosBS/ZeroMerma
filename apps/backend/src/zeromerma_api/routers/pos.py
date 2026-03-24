from __future__ import annotations

from fastapi import APIRouter, Query

from zeromerma_api.core.authz import (
    POS_ALLOWED_ROLES,
    POS_CASH_SESSION_CLOSE_ALLOWED_ROLES,
    POS_CASH_SESSION_OPEN_ALLOWED_ROLES,
    enforce_branch_access,
    enforce_cash_session_close_access,
    enforce_sale_access,
    require_ctx_role,
)
from zeromerma_api.core.dependency_aliases import ActiveAuthContextDep, DbSessionDep
from zeromerma_api.routers.pos_orders import router as orders_router
from zeromerma_api.routers.pos_payments import router as payments_router
from zeromerma_api.routers.pos_sales import router as sales_router
from zeromerma_api.schemas.cash_session import (
    CashSessionCloseIn,
    CashSessionOpenIn,
    CashSessionOut,
)
from zeromerma_api.schemas.pos_bootstrap import PosBootstrapOut
from zeromerma_api.schemas.pos_checkout import PosCheckoutIn, PosCheckoutOut
from zeromerma_api.schemas.pos_reprint import PosReprintOut
from zeromerma_api.services.cash_session_service import (
    close_cash_session,
    get_current_open_session,
    open_cash_session,
)
from zeromerma_api.services.pos_bootstrap_service import get_pos_bootstrap
from zeromerma_api.services.pos_checkout_service import checkout_pos_sale
from zeromerma_api.services.pos_reprint_service import get_reprint_payload

router = APIRouter(prefix="/pos", tags=["pos"])


@router.get("/bootstrap", response_model=PosBootstrapOut)
def api_get_pos_bootstrap(
    db: DbSessionDep,
    ctx: ActiveAuthContextDep,
    branch_id: int = Query(..., ge=1),
) -> PosBootstrapOut:
    """
    Return the POS bootstrap payload for one branch.
    """
    role_code = require_ctx_role(ctx=ctx, allowed_roles=POS_ALLOWED_ROLES)
    enforce_branch_access(
        current_user=ctx.user,
        role_code=role_code,
        branch_id=int(branch_id),
    )

    payload = get_pos_bootstrap(db, branch_id=int(branch_id))
    return PosBootstrapOut.model_validate(payload)


@router.post("/checkout", response_model=PosCheckoutOut)
def api_checkout_pos_sale(
    payload: PosCheckoutIn,
    db: DbSessionDep,
    ctx: ActiveAuthContextDep,
) -> PosCheckoutOut:
    """
    Execute one atomic POS checkout.
    """
    role_code = require_ctx_role(ctx=ctx, allowed_roles=POS_ALLOWED_ROLES)
    enforce_branch_access(
        current_user=ctx.user,
        role_code=role_code,
        branch_id=int(payload.branch_id),
    )

    try:
        result = checkout_pos_sale(
            db=db,
            branch_id=int(payload.branch_id),
            cash_session_id=int(payload.cash_session_id),
            created_by_id=int(ctx.user.id),
            items=[item.model_dump(exclude_none=True) for item in payload.items],
            payment=payload.payment.model_dump(exclude_none=True),
            print_ticket=bool(payload.print_ticket),
        )
        db.commit()
        return PosCheckoutOut.model_validate(result)
    except Exception:
        db.rollback()
        raise


@router.post("/sales/{sale_id}/reprint", response_model=PosReprintOut)
def api_reprint_sale_receipt(
    sale_id: int,
    db: DbSessionDep,
    ctx: ActiveAuthContextDep,
) -> PosReprintOut:
    """
    Return the canonical printable receipt payload for one sale.
    """
    role_code = require_ctx_role(ctx=ctx, allowed_roles=POS_ALLOWED_ROLES)
    enforce_sale_access(
        db=db,
        current_user=ctx.user,
        role_code=role_code,
        sale_id=int(sale_id),
    )

    payload = get_reprint_payload(db, sale_id=int(sale_id))
    return PosReprintOut.model_validate(payload)


@router.post("/cash-sessions/open", response_model=CashSessionOut)
def api_open_cash_session(
    payload: CashSessionOpenIn,
    db: DbSessionDep,
    ctx: ActiveAuthContextDep,
) -> CashSessionOut:
    """
    Open a new cash session.

    Policy:
    - ADMIN and CASHIER may open sessions
    - non-admins remain branch-scoped
    """
    role_code = require_ctx_role(
        ctx=ctx,
        allowed_roles=POS_CASH_SESSION_OPEN_ALLOWED_ROLES,
    )
    enforce_branch_access(
        current_user=ctx.user,
        role_code=role_code,
        branch_id=int(payload.branch_id),
    )

    try:
        cs = open_cash_session(
            db=db,
            branch_id=int(payload.branch_id),
            opened_by_id=int(ctx.user.id),
            opening_amount=payload.opening_amount,
        )
        db.commit()
        db.refresh(cs)
        return CashSessionOut.model_validate(cs)
    except Exception:
        db.rollback()
        raise


@router.post("/cash-sessions/{session_id}/close", response_model=CashSessionOut)
def api_close_cash_session(
    session_id: int,
    payload: CashSessionCloseIn,
    db: DbSessionDep,
    ctx: ActiveAuthContextDep,
) -> CashSessionOut:
    """
    Close an OPEN cash session.

    Fine-grained policy:
    - ADMIN may close any accessible session
    - CASHIER may close only the session they opened
    """
    role_code = require_ctx_role(
        ctx=ctx,
        allowed_roles=POS_CASH_SESSION_CLOSE_ALLOWED_ROLES,
    )
    enforce_cash_session_close_access(
        db=db,
        current_user=ctx.user,
        role_code=role_code,
        session_id=int(session_id),
    )

    try:
        updated = close_cash_session(
            db=db,
            session_id=int(session_id),
            closed_by_id=int(ctx.user.id),
            closing_amount=payload.closing_amount,
            counted_card_total=payload.counted_card_total,
            counted_transfer_total=payload.counted_transfer_total,
            counted_other_total=payload.counted_other_total,
            note=payload.note,
        )
        db.commit()
        db.refresh(updated)
        return CashSessionOut.model_validate(updated)
    except Exception:
        db.rollback()
        raise


@router.get("/cash-sessions/current", response_model=CashSessionOut | None)
def api_current_cash_session(
    db: DbSessionDep,
    ctx: ActiveAuthContextDep,
    branch_id: int = Query(..., ge=1),
) -> CashSessionOut | None:
    """
    Return the current OPEN cash session for a branch, or null if none exists.
    """
    role_code = require_ctx_role(ctx=ctx, allowed_roles=POS_ALLOWED_ROLES)
    enforce_branch_access(
        current_user=ctx.user,
        role_code=role_code,
        branch_id=int(branch_id),
    )

    cs = get_current_open_session(db, branch_id=int(branch_id))
    return CashSessionOut.model_validate(cs) if cs is not None else None


router.include_router(sales_router)
router.include_router(payments_router)
router.include_router(orders_router)
