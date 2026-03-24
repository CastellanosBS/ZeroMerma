from __future__ import annotations

from datetime import datetime, timezone
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from zeromerma_api.core.domain_errors import (
    DomainConflictError,
    DomainNotFoundError,
    DomainValidationError,
)
from zeromerma_api.core.payment_method import (
    CASH_PAYMENT_METHOD,
    PAYMENT_METHOD_VALUES,
    is_cash_payment_method,
    normalize_payment_method,
)
from zeromerma_api.models.customer_order import CustomerOrder, CustomerOrderStatus
from zeromerma_api.models.customer_order_item import CustomerOrderItem
from zeromerma_api.models.payment import Payment
from zeromerma_api.models.sale import Sale
from zeromerma_api.models.user_account import UserAccount
from zeromerma_api.services.payment_service import add_payment
from zeromerma_api.services.pos_audit_service import record_pos_audit_event
from zeromerma_api.services.sale_service import create_sale

MONEY_PLACES = Decimal("0.01")
QTY_PLACES = Decimal("0.001")


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


def _require_actor_user(db: Session, *, user_id: int) -> UserAccount:
    """
    Ensure actor exists and is active.
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


def _require_ready_order(db: Session, *, order_id: int) -> CustomerOrder:
    """
    Load one customer order and ensure it is READY and not yet delivered.
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

    if str(order.status) != CustomerOrderStatus.READY.value:
        raise DomainConflictError(
            message=(f"Customer order {order_id} must be READY to enter delivery checkout."),
            details={
                "order_id": int(order_id),
                "current_status": str(order.status),
                "required_status": CustomerOrderStatus.READY.value,
            },
        )

    if order.delivered_sale_id is not None:
        raise DomainConflictError(
            message=f"Customer order {order_id} is already linked to a sale.",
            details={
                "order_id": int(order_id),
                "delivered_sale_id": int(order.delivered_sale_id),
            },
        )

    if not order.items:
        raise DomainConflictError(
            message=f"Customer order {order_id} has no items.",
            details={"order_id": int(order_id)},
        )

    return order


def _serialize_preview_line(item: CustomerOrderItem) -> dict[str, Any]:
    """
    Build one checkout-preview line from frozen order snapshots.
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


def get_order_checkout_preview(db: Session, *, order_id: int) -> dict[str, Any]:
    """
    Return the POS checkout preview for one READY customer order.

    Important:
    - uses frozen monetary snapshots from the order
    - does not touch inventory
    - does not create a sale
    """
    order = _require_ready_order(db, order_id=int(order_id))

    return {
        "order_id": int(order.id),
        "branch_id": int(order.branch_id),
        "status": str(order.status),
        "customer_name": order.customer_name,
        "customer_phone": order.customer_phone,
        "note": order.note,
        "requested_for_at": order.requested_for_at,
        "subtotal": money(to_decimal(order.subtotal)),
        "tax": money(to_decimal(order.tax)),
        "total": money(to_decimal(order.total)),
        "items": [_serialize_preview_line(item) for item in order.items],
    }


def _build_sale_input_lines_from_order(
    order: CustomerOrder,
) -> list[dict[str, Any]]:
    """
    Transform frozen order items into canonical create_sale() lines.

    Important:
    - unit_price comes from order snapshot
    - inventory deduction occurs only now, at delivery checkout time
    """
    return [
        {
            "product_id": int(item.product_id),
            "qty": qty(to_decimal(item.qty)),
            "unit_price": money(to_decimal(item.unit_price_snapshot)),
        }
        for item in order.items
    ]


def _build_receipt_payload_from_order_sale(
    *,
    order: CustomerOrder,
    sale: Sale,
    payment_method: str,
    amount_tendered: Decimal | None,
    change_due: Decimal,
) -> dict[str, Any]:
    """
    Build the printable receipt payload for order delivery checkout.

    Prices are frozen from order snapshots; product labels come from current
    product projection, which is acceptable because the commercial commitment
    is preserved in the monetary snapshots.
    """
    items_payload: list[dict[str, Any]] = []

    for item in order.items:
        product = item.product
        if product is not None:
            sku = product.sku
            name = str(product.name)
            quick_name = product.quick_name
        else:
            sku = None
            name = f"Product {int(item.product_id)}"
            quick_name = None

        items_payload.append(
            {
                "product_id": int(item.product_id),
                "sku": sku,
                "name": name,
                "quick_name": quick_name,
                "qty": qty(to_decimal(item.qty)),
                "unit_price": money(to_decimal(item.unit_price_snapshot)),
                "line_total": money(to_decimal(item.line_total_snapshot)),
            }
        )

    return {
        "sale_id": int(sale.id),
        "branch_id": int(sale.branch_id),
        "cash_session_id": int(sale.cash_session_id),
        "created_at": sale.created_at,
        "payment_method": str(payment_method),
        "amount_tendered": amount_tendered,
        "change_due": change_due,
        "subtotal": money(to_decimal(sale.subtotal)),
        "tax": money(to_decimal(sale.tax)),
        "total": money(to_decimal(sale.total)),
        "items": items_payload,
    }


def _freeze_receipt_snapshot(value: Any) -> Any:
    """
    Convert a printable receipt payload into a JSON-serializable structure
    suitable for persistence in sale.receipt_snapshot.

    Rules:
    - Decimal -> string
    - datetime -> ISO 8601 string
    - dict/list -> recursive conversion
    """
    if isinstance(value, Decimal):
        return str(value)

    if isinstance(value, datetime):
        return value.isoformat()

    if isinstance(value, list):
        return [_freeze_receipt_snapshot(item) for item in value]

    if isinstance(value, dict):
        return {str(key): _freeze_receipt_snapshot(item) for key, item in value.items()}

    return value


def _persist_receipt_snapshot(*, sale: Sale, receipt: dict[str, Any]) -> None:
    """
    Persist the frozen printable receipt payload on the final sale row.
    """
    sale.receipt_snapshot = _freeze_receipt_snapshot(receipt)


def deliver_order_via_checkout(
    db: Session,
    *,
    order_id: int,
    cash_session_id: int,
    actor_user_id: int,
    payment: dict[str, Any],
    print_ticket: bool,
) -> dict[str, Any]:
    """
    Atomically deliver one READY customer order through the POS checkout flow.

    Flow:
    1. load READY order
    2. create sale from frozen order snapshots
    3. register payment
    4. compute change (cash only)
    5. persist sale receipt_snapshot
    6. mark sale as PAID
    7. mark order as DELIVERED and link delivered_sale_id

    Important:
    - this is the moment where inventory is actually affected, because a sale
      is created
    - prices are taken from frozen order snapshots, not current catalog prices
    """
    _require_actor_user(db, user_id=int(actor_user_id))
    order = _require_ready_order(db, order_id=int(order_id))

    method = normalize_payment_method(payment["method"])
    if method not in PAYMENT_METHOD_VALUES:
        raise DomainValidationError(
            message=f"Unsupported payment method '{method}'.",
            details={
                "method": method,
                "allowed_methods": list(PAYMENT_METHOD_VALUES),
            },
        )

    sale = create_sale(
        db=db,
        branch_id=int(order.branch_id),
        cash_session_id=int(cash_session_id),
        created_by_id=int(actor_user_id),
        items=_build_sale_input_lines_from_order(order),
    )
    db.flush()

    total = money(to_decimal(sale.total))

    amount_tendered: Decimal | None = None
    change_due = Decimal("0.00")

    if is_cash_payment_method(method):
        raw_amount_tendered = payment.get("amount_tendered")
        if raw_amount_tendered is None:
            raise DomainValidationError(
                message="amount_tendered is required for cash checkout.",
                details={"method": CASH_PAYMENT_METHOD},
            )

        amount_tendered = money(to_decimal(raw_amount_tendered))
        if amount_tendered < total:
            raise DomainValidationError(
                message="Cash amount_tendered must be greater than or equal to total.",
                details={
                    "amount_tendered": str(amount_tendered),
                    "total": str(total),
                },
            )

        change_due = money(amount_tendered - total)

    else:
        if payment.get("amount_tendered") is not None:
            raise DomainValidationError(
                message="amount_tendered is only allowed for cash checkout.",
                details={"method": method},
            )

    reference = payment.get("reference") or payment.get("external_auth_code")

    payment_row: Payment = add_payment(
        db=db,
        sale_id=int(sale.id),
        method=method,
        amount=total,
        reference=reference,
    )
    db.flush()

    receipt = _build_receipt_payload_from_order_sale(
        order=order,
        sale=sale,
        payment_method=method,
        amount_tendered=amount_tendered,
        change_due=change_due,
    )
    _persist_receipt_snapshot(sale=sale, receipt=receipt)

    sale.status = "PAID"

    order.status = CustomerOrderStatus.DELIVERED.value
    order.delivered_by_id = int(actor_user_id)
    order.delivered_at = datetime.now(timezone.utc)
    order.delivered_sale_id = int(sale.id)

    db.flush()

    record_pos_audit_event(
        db,
        branch_id=int(order.branch_id),
        actor_user_id=int(actor_user_id),
        entity_type="CUSTOMER_ORDER",
        entity_id=int(order.id),
        event_type="ORDER_DELIVERED_VIA_CHECKOUT",
        payload={
            "order_id": int(order.id),
            "sale_id": int(sale.id),
            "payment_id": int(payment_row.id),
            "cash_session_id": int(cash_session_id),
            "payment_method": method,
            "subtotal": money(to_decimal(sale.subtotal)),
            "tax": money(to_decimal(sale.tax)),
            "total": total,
            "paid_amount": total,
            "change_due": change_due,
            "print_ticket": bool(print_ticket),
        },
    )

    return {
        "order_id": int(order.id),
        "sale_id": int(sale.id),
        "payment_id": int(payment_row.id),
        "order_status": CustomerOrderStatus.DELIVERED.value,
        "sale_status": "PAID",
        "payment_status": "AUTHORIZED",
        "subtotal": money(to_decimal(sale.subtotal)),
        "tax": money(to_decimal(sale.tax)),
        "total": total,
        "paid_amount": total,
        "change_due": change_due,
        "balance_due": Decimal("0.00"),
        "print_ticket": bool(print_ticket),
        "receipt": receipt,
    }
