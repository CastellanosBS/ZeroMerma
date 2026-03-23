from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Query

from zeromerma_api.core.authz import (
    ROLE_ADMIN,
    ROLE_CASHIER,
    enforce_branch_access,
    require_ctx_role,
)
from zeromerma_api.core.dependency_aliases import ActiveAuthContextDep, DbSessionDep
from zeromerma_api.core.domain_errors import DomainNotFoundError
from zeromerma_api.models.customer_order import CustomerOrder
from zeromerma_api.schemas.pos_order import (
    PosOrderCreateIn,
    PosOrderDetailOut,
    PosOrderSummaryOut,
)
from zeromerma_api.schemas.pos_order_queue import PosOrderQueueOut
from zeromerma_api.services.pos_order_service import (
    cancel_customer_order,
    create_customer_order,
    deliver_customer_order,
    get_customer_order_detail,
    get_customer_order_queue,
    list_customer_orders,
    mark_customer_order_ready,
    send_customer_order_to_bakery,
)

ROLE_BAKER = "BAKER"

ORDER_CREATE_ALLOWED_ROLES = {ROLE_ADMIN, ROLE_CASHIER}
ORDER_READ_ALLOWED_ROLES = {ROLE_ADMIN, ROLE_CASHIER, ROLE_BAKER}
ORDER_SEND_ALLOWED_ROLES = {ROLE_ADMIN}
ORDER_READY_ALLOWED_ROLES = {ROLE_ADMIN, ROLE_BAKER}
ORDER_DELIVER_ALLOWED_ROLES = {ROLE_ADMIN, ROLE_CASHIER}
ORDER_CANCEL_ALLOWED_ROLES = {ROLE_ADMIN, ROLE_CASHIER}

router = APIRouter(prefix="/orders", tags=["pos"])


def _require_customer_order(db, *, order_id: int) -> CustomerOrder:
    """
    Load one customer order for branch scope checks.
    """
    order = db.get(CustomerOrder, int(order_id))
    if order is None:
        raise DomainNotFoundError(
            message=f"Customer order {order_id} not found.",
            details={"order_id": int(order_id)},
        )
    return order


@router.post("", response_model=PosOrderDetailOut)
def api_create_customer_order(
    payload: PosOrderCreateIn,
    db: DbSessionDep,
    ctx: ActiveAuthContextDep,
) -> PosOrderDetailOut:
    """
    Create one customer order for existing finished goods.

    2B.1:
    - does not affect inventory
    - freezes price snapshots
    - creates an operational order to be later sent to bakers
    """
    role_code = require_ctx_role(ctx=ctx, allowed_roles=ORDER_CREATE_ALLOWED_ROLES)
    enforce_branch_access(
        current_user=ctx.user,
        role_code=role_code,
        branch_id=int(payload.branch_id),
    )

    try:
        result = create_customer_order(
            db=db,
            branch_id=int(payload.branch_id),
            created_by_id=int(ctx.user.id),
            customer_name=payload.customer_name,
            customer_phone=payload.customer_phone,
            note=payload.note,
            requested_for_at=payload.requested_for_at,
            items=[item.model_dump(exclude_none=True) for item in payload.items],
        )
        db.commit()
        return PosOrderDetailOut.model_validate(result)
    except Exception:
        db.rollback()
        raise


@router.get("/queue", response_model=PosOrderQueueOut)
def api_get_customer_order_queue(
    db: DbSessionDep,
    ctx: ActiveAuthContextDep,
    branch_id: int | None = Query(None, ge=1),
) -> PosOrderQueueOut:
    """
    Return the operational queue for orders in one branch.

    If branch_id is omitted, the caller's own branch is used.
    """
    role_code = require_ctx_role(ctx=ctx, allowed_roles=ORDER_READ_ALLOWED_ROLES)

    effective_branch_id = int(branch_id) if branch_id is not None else int(ctx.user.branch_id)

    enforce_branch_access(
        current_user=ctx.user,
        role_code=role_code,
        branch_id=effective_branch_id,
    )

    payload = get_customer_order_queue(
        db=db,
        branch_id=effective_branch_id,
    )
    return PosOrderQueueOut.model_validate(payload)


@router.get("", response_model=list[PosOrderSummaryOut])
def api_list_customer_orders(
    db: DbSessionDep,
    ctx: ActiveAuthContextDep,
    branch_id: int | None = Query(None, ge=1),
    status: str | None = Query(None),
    requested_from: datetime | None = Query(None),
    requested_to: datetime | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> list[PosOrderSummaryOut]:
    """
    List customer orders for one branch.

    If branch_id is omitted, the caller's own branch is used.
    """
    role_code = require_ctx_role(ctx=ctx, allowed_roles=ORDER_READ_ALLOWED_ROLES)

    effective_branch_id = int(branch_id) if branch_id is not None else int(ctx.user.branch_id)

    enforce_branch_access(
        current_user=ctx.user,
        role_code=role_code,
        branch_id=effective_branch_id,
    )

    rows = list_customer_orders(
        db=db,
        branch_id=effective_branch_id,
        status=status,
        requested_from=requested_from,
        requested_to=requested_to,
        limit=limit,
        offset=offset,
    )
    return [PosOrderSummaryOut.model_validate(row) for row in rows]


@router.get("/{order_id}", response_model=PosOrderDetailOut)
def api_get_customer_order_detail(
    order_id: int,
    db: DbSessionDep,
    ctx: ActiveAuthContextDep,
) -> PosOrderDetailOut:
    """
    Return one full customer order detail.
    """
    role_code = require_ctx_role(ctx=ctx, allowed_roles=ORDER_READ_ALLOWED_ROLES)
    order = _require_customer_order(db, order_id=int(order_id))

    enforce_branch_access(
        current_user=ctx.user,
        role_code=role_code,
        branch_id=int(order.branch_id),
    )

    payload = get_customer_order_detail(db, order_id=int(order_id))
    return PosOrderDetailOut.model_validate(payload)


@router.post("/{order_id}/send-to-bakery", response_model=PosOrderDetailOut)
def api_send_customer_order_to_bakery(
    order_id: int,
    db: DbSessionDep,
    ctx: ActiveAuthContextDep,
) -> PosOrderDetailOut:
    """
    Transition one order from CREATED to SENT_TO_BAKERY.
    """
    role_code = require_ctx_role(ctx=ctx, allowed_roles=ORDER_SEND_ALLOWED_ROLES)
    order = _require_customer_order(db, order_id=int(order_id))

    enforce_branch_access(
        current_user=ctx.user,
        role_code=role_code,
        branch_id=int(order.branch_id),
    )

    try:
        payload = send_customer_order_to_bakery(
            db=db,
            order_id=int(order_id),
            actor_user_id=int(ctx.user.id),
        )
        db.commit()
        return PosOrderDetailOut.model_validate(payload)
    except Exception:
        db.rollback()
        raise


@router.post("/{order_id}/ready", response_model=PosOrderDetailOut)
def api_mark_customer_order_ready(
    order_id: int,
    db: DbSessionDep,
    ctx: ActiveAuthContextDep,
) -> PosOrderDetailOut:
    """
    Transition one order from SENT_TO_BAKERY to READY.
    """
    role_code = require_ctx_role(ctx=ctx, allowed_roles=ORDER_READY_ALLOWED_ROLES)
    order = _require_customer_order(db, order_id=int(order_id))

    enforce_branch_access(
        current_user=ctx.user,
        role_code=role_code,
        branch_id=int(order.branch_id),
    )

    try:
        payload = mark_customer_order_ready(
            db=db,
            order_id=int(order_id),
            actor_user_id=int(ctx.user.id),
        )
        db.commit()
        return PosOrderDetailOut.model_validate(payload)
    except Exception:
        db.rollback()
        raise


@router.post("/{order_id}/deliver", response_model=PosOrderDetailOut)
def api_deliver_customer_order(
    order_id: int,
    db: DbSessionDep,
    ctx: ActiveAuthContextDep,
) -> PosOrderDetailOut:
    """
    Transition one order from READY to DELIVERED.

    In 2B.1/2B.2 this only marks operational delivery; it does not yet create/link a sale.
    """
    role_code = require_ctx_role(ctx=ctx, allowed_roles=ORDER_DELIVER_ALLOWED_ROLES)
    order = _require_customer_order(db, order_id=int(order_id))

    enforce_branch_access(
        current_user=ctx.user,
        role_code=role_code,
        branch_id=int(order.branch_id),
    )

    try:
        payload = deliver_customer_order(
            db=db,
            order_id=int(order_id),
            actor_user_id=int(ctx.user.id),
        )
        db.commit()
        return PosOrderDetailOut.model_validate(payload)
    except Exception:
        db.rollback()
        raise


@router.post("/{order_id}/cancel", response_model=PosOrderDetailOut)
def api_cancel_customer_order(
    order_id: int,
    db: DbSessionDep,
    ctx: ActiveAuthContextDep,
) -> PosOrderDetailOut:
    """
    Transition one order into CANCELED from an allowed pre-terminal state.
    """
    role_code = require_ctx_role(ctx=ctx, allowed_roles=ORDER_CANCEL_ALLOWED_ROLES)
    order = _require_customer_order(db, order_id=int(order_id))

    enforce_branch_access(
        current_user=ctx.user,
        role_code=role_code,
        branch_id=int(order.branch_id),
    )

    try:
        payload = cancel_customer_order(
            db=db,
            order_id=int(order_id),
            actor_user_id=int(ctx.user.id),
        )
        db.commit()
        return PosOrderDetailOut.model_validate(payload)
    except Exception:
        db.rollback()
        raise
