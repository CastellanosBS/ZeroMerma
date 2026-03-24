from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session, selectinload

from zeromerma_api.core.domain_errors import (
    DomainConflictError,
    DomainNotFoundError,
    DomainValidationError,
)
from zeromerma_api.models.branch import Branch
from zeromerma_api.models.customer_order import CustomerOrder, CustomerOrderStatus
from zeromerma_api.models.customer_order_item import CustomerOrderItem
from zeromerma_api.models.product import Product
from zeromerma_api.models.product_category import ProductCategory
from zeromerma_api.models.product_price import ProductPrice
from zeromerma_api.models.user_account import UserAccount

MONEY_PLACES = Decimal("0.01")
QTY_PLACES = Decimal("0.001")

ACTIVE_ORDER_STATUSES = {
    CustomerOrderStatus.CREATED.value,
    CustomerOrderStatus.SENT_TO_BAKERY.value,
    CustomerOrderStatus.READY.value,
}


@dataclass(frozen=True)
class ResolvedOrderLine:
    """
    One fully resolved order line with frozen commercial data.
    """

    product_id: int
    sku: str | None
    name: str
    quick_name: str | None
    qty: Decimal
    unit_price_snapshot: Decimal
    line_total_snapshot: Decimal


def utcnow() -> datetime:
    """
    Return a timezone-aware UTC timestamp.
    """
    return datetime.now(timezone.utc)


def money(value: Decimal) -> Decimal:
    """
    Normalize money to 2 decimal places.
    """
    return value.quantize(MONEY_PLACES, rounding=ROUND_HALF_UP)


def qty(value: Decimal) -> Decimal:
    """
    Normalize quantity to 3 decimal places.
    """
    return value.quantize(QTY_PLACES, rounding=ROUND_HALF_UP)


def to_decimal(value: Decimal | float | int | str) -> Decimal:
    """
    Convert numeric-like input to Decimal safely.
    """
    return Decimal(str(value))


def _require_branch(db: Session, *, branch_id: int) -> Branch:
    """
    Ensure target branch exists and is active.
    """
    branch = db.get(Branch, int(branch_id))
    if branch is None:
        raise DomainNotFoundError(
            message=f"Branch {branch_id} not found.",
            details={"branch_id": int(branch_id)},
        )

    if not bool(branch.is_active):
        raise DomainConflictError(
            message=f"Branch {branch_id} is inactive.",
            details={"branch_id": int(branch_id)},
        )

    return branch


def _require_actor_user(db: Session, *, user_id: int) -> UserAccount:
    """
    Ensure actor user exists and is active.
    """
    user = db.get(UserAccount, int(user_id))
    if user is None:
        raise DomainNotFoundError(
            message=f"User {user_id} not found.",
            details={"user_id": int(user_id)},
        )

    if not bool(user.is_active):
        raise DomainConflictError(
            message=f"User {user_id} is inactive.",
            details={"user_id": int(user_id)},
        )

    return user


def get_customer_order_branch_id(db: Session, *, order_id: int) -> int | None:
    """
    Resolve one order's branch_id for router-level branch scope checks.
    """
    value = db.scalar(select(CustomerOrder.branch_id).where(CustomerOrder.id == int(order_id)))
    return int(value) if value is not None else None


def _require_order(db: Session, *, order_id: int) -> CustomerOrder:
    """
    Load one order with items and current product projection.
    """
    stmt = (
        select(CustomerOrder)
        .where(CustomerOrder.id == int(order_id))
        .options(selectinload(CustomerOrder.items).selectinload(CustomerOrderItem.product))
    )
    order = db.scalar(stmt)

    if order is None:
        raise DomainNotFoundError(
            message=f"Customer order {order_id} not found.",
            details={"order_id": int(order_id)},
        )

    return order


def _resolve_order_lines(
    db: Session,
    *,
    branch_id: int,
    items: list[dict],
) -> list[ResolvedOrderLine]:
    """
    Resolve items against the current POS-visible finished-goods catalog.

    Current 2B.1 rule:
    orders can only be created for products that are:
    - existing
    - active
    - non-input (finished goods)
    - POS-visible
    - POS-sellable
    - in an active POS-visible category
    """
    if not items:
        raise DomainValidationError(
            message="Order must contain at least one item.",
            details={"items": []},
        )

    requested_product_ids = [int(item["product_id"]) for item in items]

    stmt = (
        select(
            Product.id.label("product_id"),
            Product.sku.label("sku"),
            Product.name.label("name"),
            Product.quick_name.label("quick_name"),
            Product.is_active.label("product_is_active"),
            Product.is_input.label("is_input"),
            Product.show_in_pos.label("product_show_in_pos"),
            Product.is_sellable_in_pos.label("is_sellable_in_pos"),
            ProductCategory.id.label("category_id"),
            ProductCategory.is_active.label("category_is_active"),
            ProductCategory.show_in_pos.label("category_show_in_pos"),
            func.coalesce(ProductPrice.price, Product.sale_price).label("effective_price"),
        )
        .outerjoin(ProductCategory, Product.category_id == ProductCategory.id)
        .outerjoin(
            ProductPrice,
            and_(
                ProductPrice.branch_id == int(branch_id),
                ProductPrice.product_id == Product.id,
            ),
        )
        .where(Product.id.in_(requested_product_ids))
    )

    rows = db.execute(stmt).all()
    row_map = {int(row.product_id): row for row in rows}

    missing_ids = sorted(set(requested_product_ids) - set(row_map.keys()))
    if missing_ids:
        raise DomainNotFoundError(
            message="Some products do not exist.",
            details={"missing_product_ids": missing_ids},
        )

    resolved: list[ResolvedOrderLine] = []

    for item in items:
        product_id = int(item["product_id"])
        requested_qty = qty(to_decimal(item["qty"]))
        row = row_map[product_id]

        if requested_qty <= 0:
            raise DomainValidationError(
                message="Order item quantity must be greater than zero.",
                details={"product_id": product_id, "qty": str(requested_qty)},
            )

        if not bool(row.product_is_active):
            raise DomainValidationError(
                message="Product is inactive and cannot be ordered.",
                details={"product_id": product_id},
            )

        if bool(row.is_input):
            raise DomainValidationError(
                message="Input/raw-material products cannot be ordered.",
                details={"product_id": product_id},
            )

        if row.category_id is None:
            raise DomainValidationError(
                message="Product must belong to a valid category.",
                details={"product_id": product_id},
            )

        if not bool(row.category_is_active):
            raise DomainValidationError(
                message="Product category is inactive and cannot be used.",
                details={"product_id": product_id, "category_id": int(row.category_id)},
            )

        if not bool(row.category_show_in_pos):
            raise DomainValidationError(
                message="Product category is hidden from POS.",
                details={"product_id": product_id, "category_id": int(row.category_id)},
            )

        if not bool(row.product_show_in_pos):
            raise DomainValidationError(
                message="Product is hidden from POS.",
                details={"product_id": product_id},
            )

        if not bool(row.is_sellable_in_pos):
            raise DomainValidationError(
                message="Product is not orderable from POS.",
                details={"product_id": product_id},
            )

        if row.effective_price is None:
            raise DomainConflictError(
                message="No effective price configured for product.",
                details={
                    "branch_id": int(branch_id),
                    "product_id": product_id,
                },
            )

        unit_price_snapshot = money(to_decimal(row.effective_price))
        line_total_snapshot = money(requested_qty * unit_price_snapshot)

        resolved.append(
            ResolvedOrderLine(
                product_id=product_id,
                sku=row.sku,
                name=str(row.name),
                quick_name=row.quick_name,
                qty=requested_qty,
                unit_price_snapshot=unit_price_snapshot,
                line_total_snapshot=line_total_snapshot,
            )
        )

    return resolved


def _serialize_order_item(item: CustomerOrderItem) -> dict[str, Any]:
    """
    Serialize one order item using current product labels and frozen price snapshots.
    """
    product = item.product

    if product is not None:
        sku = product.sku
        name = str(product.name)
        quick_name = product.quick_name
    else:
        sku = None
        name = f"Product {int(item.product_id)}"
        quick_name = None

    return {
        "product_id": int(item.product_id),
        "sku": sku,
        "name": name,
        "quick_name": quick_name,
        "qty": qty(to_decimal(item.qty)),
        "unit_price_snapshot": money(to_decimal(item.unit_price_snapshot)),
        "line_total_snapshot": money(to_decimal(item.line_total_snapshot)),
    }


def _serialize_order_summary(order: CustomerOrder) -> dict[str, Any]:
    """
    Serialize one order for list screens.
    """
    return {
        "id": int(order.id),
        "branch_id": int(order.branch_id),
        "created_by_id": int(order.created_by_id),
        "delivered_sale_id": (
            int(order.delivered_sale_id) if order.delivered_sale_id is not None else None
        ),
        "status": str(order.status),
        "customer_name": order.customer_name,
        "customer_phone": order.customer_phone,
        "note": order.note,
        "requested_for_at": order.requested_for_at,
        "sent_to_bakery_at": order.sent_to_bakery_at,
        "ready_at": order.ready_at,
        "delivered_at": order.delivered_at,
        "canceled_at": order.canceled_at,
        "subtotal": money(to_decimal(order.subtotal)),
        "tax": money(to_decimal(order.tax)),
        "total": money(to_decimal(order.total)),
        "created_at": order.created_at,
        "updated_at": order.updated_at,
    }


def _serialize_order_detail(order: CustomerOrder) -> dict[str, Any]:
    """
    Serialize one full order with items and transition actors.
    """
    payload = _serialize_order_summary(order)
    payload.update(
        {
            "sent_to_bakery_by_id": (
                int(order.sent_to_bakery_by_id) if order.sent_to_bakery_by_id is not None else None
            ),
            "ready_by_id": int(order.ready_by_id) if order.ready_by_id is not None else None,
            "delivered_by_id": (
                int(order.delivered_by_id) if order.delivered_by_id is not None else None
            ),
            "canceled_by_id": (
                int(order.canceled_by_id) if order.canceled_by_id is not None else None
            ),
            "items": [_serialize_order_item(item) for item in order.items],
        }
    )
    return payload


def _compute_due_bucket(*, requested_for_at: datetime | None, now_utc: datetime) -> str:
    """
    Compute one operational due bucket for queue screens.

    Semantics:
    - UNSCHEDULED: no requested_for_at
    - OVERDUE: requested_for_at earlier than now
    - TODAY: same UTC calendar day and not overdue
    - FUTURE: later than today
    """
    if requested_for_at is None:
        return "UNSCHEDULED"

    if requested_for_at < now_utc:
        return "OVERDUE"

    if requested_for_at.date() == now_utc.date():
        return "TODAY"

    return "FUTURE"


def _serialize_queue_item(
    order: CustomerOrder,
    *,
    now_utc: datetime,
) -> dict[str, Any]:
    """
    Serialize one customer order into a compact operational queue projection.
    """
    items_preview = []
    total_units = Decimal("0.000")

    for item in order.items:
        product = item.product
        items_preview.append(
            {
                "product_id": int(item.product_id),
                "sku": product.sku if product is not None else None,
                "name": (
                    str(product.name) if product is not None else f"Product {int(item.product_id)}"
                ),
                "quick_name": product.quick_name if product is not None else None,
                "qty": qty(to_decimal(item.qty)),
            }
        )
        total_units += qty(to_decimal(item.qty))

    return {
        "id": int(order.id),
        "branch_id": int(order.branch_id),
        "status": str(order.status),
        "customer_name": order.customer_name,
        "customer_phone": order.customer_phone,
        "note": order.note,
        "requested_for_at": order.requested_for_at,
        "created_at": order.created_at,
        "subtotal": money(to_decimal(order.subtotal)),
        "tax": money(to_decimal(order.tax)),
        "total": money(to_decimal(order.total)),
        "lines_count": len(order.items),
        "total_units": qty(total_units),
        "due_bucket": _compute_due_bucket(
            requested_for_at=order.requested_for_at,
            now_utc=now_utc,
        ),
        "items_preview": items_preview,
    }


def create_customer_order(
    db: Session,
    *,
    branch_id: int,
    created_by_id: int,
    customer_name: str | None,
    customer_phone: str | None,
    note: str | None,
    requested_for_at: datetime | None,
    items: list[dict],
) -> dict[str, Any]:
    """
    Create one customer order for existing finished goods.

    Important 2B.1 rule:
    this operation does NOT affect inventory.
    """
    _require_branch(db, branch_id=int(branch_id))
    _require_actor_user(db, user_id=int(created_by_id))

    resolved_lines = _resolve_order_lines(
        db,
        branch_id=int(branch_id),
        items=items,
    )

    subtotal = money(sum((line.line_total_snapshot for line in resolved_lines), Decimal("0.00")))
    tax = Decimal("0.00")
    total = money(subtotal + tax)

    order = CustomerOrder(
        branch_id=int(branch_id),
        created_by_id=int(created_by_id),
        status=CustomerOrderStatus.CREATED.value,
        customer_name=customer_name,
        customer_phone=customer_phone,
        note=note,
        requested_for_at=requested_for_at,
        subtotal=subtotal,
        tax=tax,
        total=total,
    )

    order.items = [
        CustomerOrderItem(
            product_id=int(line.product_id),
            qty=line.qty,
            unit_price_snapshot=line.unit_price_snapshot,
            line_total_snapshot=line.line_total_snapshot,
        )
        for line in resolved_lines
    ]

    db.add(order)
    db.flush()

    return _serialize_order_detail(_require_order(db, order_id=int(order.id)))


def list_customer_orders(
    db: Session,
    *,
    branch_id: int,
    status: str | None = None,
    requested_from: datetime | None = None,
    requested_to: datetime | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[dict[str, Any]]:
    """
    List customer orders for one branch.
    """
    _require_branch(db, branch_id=int(branch_id))

    stmt = (
        select(CustomerOrder)
        .where(CustomerOrder.branch_id == int(branch_id))
        .order_by(
            CustomerOrder.requested_for_at.asc().nullslast(),
            CustomerOrder.created_at.desc(),
            CustomerOrder.id.desc(),
        )
    )

    if status is not None:
        stmt = stmt.where(CustomerOrder.status == str(status))
    if requested_from is not None:
        stmt = stmt.where(CustomerOrder.requested_for_at >= requested_from)
    if requested_to is not None:
        stmt = stmt.where(CustomerOrder.requested_for_at <= requested_to)

    stmt = stmt.offset(int(offset)).limit(int(limit))
    rows = db.execute(stmt).scalars().all()

    return [_serialize_order_summary(order) for order in rows]


def get_customer_order_detail(
    db: Session,
    *,
    order_id: int,
) -> dict[str, Any]:
    """
    Return one customer order detail projection.
    """
    order = _require_order(db, order_id=int(order_id))
    return _serialize_order_detail(order)


def get_customer_order_queue(
    db: Session,
    *,
    branch_id: int,
) -> dict[str, Any]:
    """
    Build the operational customer-order queue for one branch.

    Buckets:
    - pending_intake: CREATED
    - bakery_work: SENT_TO_BAKERY
    - ready_for_pickup: READY

    2B.2/2B.3 purpose:
    - admin sees newly captured orders
    - bakers see released work
    - POS/cashier sees ready orders to deliver
    """
    _require_branch(db, branch_id=int(branch_id))

    now_utc = utcnow()

    counts_stmt = select(
        func.count()
        .filter(CustomerOrder.status == CustomerOrderStatus.CREATED.value)
        .label("created_count"),
        func.count()
        .filter(CustomerOrder.status == CustomerOrderStatus.SENT_TO_BAKERY.value)
        .label("sent_count"),
        func.count()
        .filter(CustomerOrder.status == CustomerOrderStatus.READY.value)
        .label("ready_count"),
        func.count()
        .filter(CustomerOrder.status == CustomerOrderStatus.DELIVERED.value)
        .label("delivered_count"),
        func.count()
        .filter(CustomerOrder.status == CustomerOrderStatus.CANCELED.value)
        .label("canceled_count"),
    ).where(CustomerOrder.branch_id == int(branch_id))
    counts_row = db.execute(counts_stmt).one()

    orders_stmt = (
        select(CustomerOrder)
        .where(
            CustomerOrder.branch_id == int(branch_id),
            CustomerOrder.status.in_(ACTIVE_ORDER_STATUSES),
        )
        .options(selectinload(CustomerOrder.items).selectinload(CustomerOrderItem.product))
        .order_by(
            CustomerOrder.requested_for_at.asc().nullslast(),
            CustomerOrder.created_at.asc(),
            CustomerOrder.id.asc(),
        )
    )
    active_orders = db.execute(orders_stmt).scalars().all()

    pending_intake: list[dict[str, Any]] = []
    bakery_work: list[dict[str, Any]] = []
    ready_for_pickup: list[dict[str, Any]] = []

    for order in active_orders:
        row = _serialize_queue_item(order, now_utc=now_utc)

        if order.status == CustomerOrderStatus.CREATED.value:
            pending_intake.append(row)
        elif order.status == CustomerOrderStatus.SENT_TO_BAKERY.value:
            bakery_work.append(row)
        elif order.status == CustomerOrderStatus.READY.value:
            ready_for_pickup.append(row)

    return {
        "branch_id": int(branch_id),
        "generated_at": now_utc,
        "counts": {
            "created": int(counts_row.created_count or 0),
            "sent_to_bakery": int(counts_row.sent_count or 0),
            "ready": int(counts_row.ready_count or 0),
            "delivered": int(counts_row.delivered_count or 0),
            "canceled": int(counts_row.canceled_count or 0),
            "active_total": (
                int(counts_row.created_count or 0)
                + int(counts_row.sent_count or 0)
                + int(counts_row.ready_count or 0)
            ),
        },
        "pending_intake": pending_intake,
        "bakery_work": bakery_work,
        "ready_for_pickup": ready_for_pickup,
    }


def _assert_transition(
    *,
    current_status: str,
    allowed_from: set[str],
    target_status: str,
    order_id: int,
) -> None:
    """
    Enforce valid state transitions.
    """
    if current_status not in allowed_from:
        raise DomainConflictError(
            message=(
                f"Customer order {order_id} cannot transition from "
                f"{current_status} to {target_status}."
            ),
            details={
                "order_id": int(order_id),
                "current_status": current_status,
                "target_status": target_status,
                "allowed_from": sorted(allowed_from),
            },
        )


def _build_manual_delivery_audit_note(
    *,
    reason: str,
    actor_user_id: int,
    delivered_at: datetime,
) -> str:
    """
    Build a compact audit marker for exceptional manual delivery without sale.

    This project does not yet have a dedicated structured audit table/columns
    for manual delivery exceptions, so the current transitional strategy is to
    append an explicit system-generated marker into `customer_order.note`.

    This keeps the decision visible in existing read models without requiring a
    schema migration in this block.
    """
    normalized_reason = str(reason).strip()
    if not normalized_reason:
        raise DomainValidationError(
            message="Manual delivery reason must not be blank.",
            details={"reason": normalized_reason},
        )

    return (
        "[MANUAL_DELIVERY_WITHOUT_SALE] "
        f"delivered_at={delivered_at.isoformat()} "
        f"delivered_by_id={int(actor_user_id)} "
        f"reason={normalized_reason}"
    )


def send_customer_order_to_bakery(
    db: Session,
    *,
    order_id: int,
    actor_user_id: int,
) -> dict[str, Any]:
    """
    Transition CREATED -> SENT_TO_BAKERY.
    """
    _require_actor_user(db, user_id=int(actor_user_id))
    order = _require_order(db, order_id=int(order_id))

    _assert_transition(
        current_status=str(order.status),
        allowed_from={CustomerOrderStatus.CREATED.value},
        target_status=CustomerOrderStatus.SENT_TO_BAKERY.value,
        order_id=int(order.id),
    )

    order.status = CustomerOrderStatus.SENT_TO_BAKERY.value
    order.sent_to_bakery_by_id = int(actor_user_id)
    order.sent_to_bakery_at = utcnow()

    db.flush()
    return _serialize_order_detail(_require_order(db, order_id=int(order.id)))


def mark_customer_order_ready(
    db: Session,
    *,
    order_id: int,
    actor_user_id: int,
) -> dict[str, Any]:
    """
    Transition SENT_TO_BAKERY -> READY.
    """
    _require_actor_user(db, user_id=int(actor_user_id))
    order = _require_order(db, order_id=int(order_id))

    _assert_transition(
        current_status=str(order.status),
        allowed_from={CustomerOrderStatus.SENT_TO_BAKERY.value},
        target_status=CustomerOrderStatus.READY.value,
        order_id=int(order.id),
    )

    order.status = CustomerOrderStatus.READY.value
    order.ready_by_id = int(actor_user_id)
    order.ready_at = utcnow()

    db.flush()
    return _serialize_order_detail(_require_order(db, order_id=int(order.id)))


def deliver_customer_order_manually(
    db: Session,
    *,
    order_id: int,
    actor_user_id: int,
    reason: str,
) -> dict[str, Any]:
    """
    Exceptional manual transition READY -> DELIVERED without creating a sale.

    This function intentionally preserves `/deliver` only as a controlled
    operational escape hatch. It must not compete with the canonical commercial
    flow implemented by `deliver_order_via_checkout()`.

    Guarantees:
    - order must currently be READY
    - delivered_sale_id remains NULL
    - the actor is recorded
    - an explicit audit marker is appended to `note`
    """
    _require_actor_user(db, user_id=int(actor_user_id))
    order = _require_order(db, order_id=int(order_id))

    _assert_transition(
        current_status=str(order.status),
        allowed_from={CustomerOrderStatus.READY.value},
        target_status=CustomerOrderStatus.DELIVERED.value,
        order_id=int(order.id),
    )

    if order.delivered_sale_id is not None:
        raise DomainConflictError(
            message=(
                f"Customer order {order_id} is already linked to sale "
                f"{int(order.delivered_sale_id)}."
            ),
            details={
                "order_id": int(order.id),
                "delivered_sale_id": int(order.delivered_sale_id),
            },
        )

    delivered_at = utcnow()
    audit_note = _build_manual_delivery_audit_note(
        reason=reason,
        actor_user_id=int(actor_user_id),
        delivered_at=delivered_at,
    )

    order.status = CustomerOrderStatus.DELIVERED.value
    order.delivered_by_id = int(actor_user_id)
    order.delivered_at = delivered_at

    existing_note = (order.note or "").rstrip()
    order.note = f"{existing_note}\n{audit_note}" if existing_note else audit_note

    db.flush()
    return _serialize_order_detail(_require_order(db, order_id=int(order.id)))


def cancel_customer_order(
    db: Session,
    *,
    order_id: int,
    actor_user_id: int,
) -> dict[str, Any]:
    """
    Transition CREATED/SENT_TO_BAKERY/READY -> CANCELED.
    """
    _require_actor_user(db, user_id=int(actor_user_id))
    order = _require_order(db, order_id=int(order_id))

    _assert_transition(
        current_status=str(order.status),
        allowed_from={
            CustomerOrderStatus.CREATED.value,
            CustomerOrderStatus.SENT_TO_BAKERY.value,
            CustomerOrderStatus.READY.value,
        },
        target_status=CustomerOrderStatus.CANCELED.value,
        order_id=int(order.id),
    )

    order.status = CustomerOrderStatus.CANCELED.value
    order.canceled_by_id = int(actor_user_id)
    order.canceled_at = utcnow()

    db.flush()
    return _serialize_order_detail(_require_order(db, order_id=int(order.id)))
