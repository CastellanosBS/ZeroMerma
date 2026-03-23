from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from zeromerma_api.core.domain_errors import DomainNotFoundError
from zeromerma_api.models.payment import Payment
from zeromerma_api.models.product import Product
from zeromerma_api.models.sale import Sale

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


def _require_sale(db: Session, *, sale_id: int) -> Sale:
    """
    Load one sale with its items and payments or fail clearly.
    """
    stmt = (
        select(Sale)
        .where(Sale.id == int(sale_id))
        .options(
            selectinload(Sale.items),
            selectinload(Sale.payments),
        )
    )
    sale = db.scalar(stmt)

    if sale is None:
        raise DomainNotFoundError(
            message=f"Sale {sale_id} not found.",
            details={"sale_id": int(sale_id)},
        )

    return sale


def _normalize_snapshot(value: Any) -> Any:
    """
    Convert a stored JSON snapshot back into a response-friendly structure.

    We intentionally preserve stringified decimals as-is, since that is the
    canonical JSON-safe representation already used elsewhere in the API.
    """
    if isinstance(value, list):
        return [_normalize_snapshot(item) for item in value]

    if isinstance(value, dict):
        return {str(key): _normalize_snapshot(item) for key, item in value.items()}

    return value


def _resolve_product_projection(
    db: Session, *, product_ids: list[int]
) -> dict[int, dict[str, Any]]:
    """
    Load current product projection for fallback reprint reconstruction.

    This is only used when a historic receipt snapshot does not exist.
    """
    if not product_ids:
        return {}

    stmt = select(
        Product.id,
        Product.sku,
        Product.name,
        Product.quick_name,
    ).where(Product.id.in_(product_ids))

    rows = db.execute(stmt).all()

    return {
        int(row.id): {
            "sku": row.sku,
            "name": str(row.name),
            "quick_name": row.quick_name,
        }
        for row in rows
    }


def _reconstruct_receipt(db: Session, *, sale: Sale) -> dict[str, Any]:
    """
    Reconstruct a printable receipt payload from persisted sale/items/payments.

    This path is intentionally marked as reconstructed because it may rely on
    current product labels if the sale has no persisted snapshot.
    """
    product_map = _resolve_product_projection(
        db,
        product_ids=[int(item.product_id) for item in sale.items],
    )

    items_payload: list[dict[str, Any]] = []
    for item in sale.items:
        product_view = product_map.get(int(item.product_id), {})

        items_payload.append(
            {
                "product_id": int(item.product_id),
                "sku": product_view.get("sku"),
                "name": product_view.get("name", f"Product {int(item.product_id)}"),
                "quick_name": product_view.get("quick_name"),
                "qty": qty(to_decimal(item.qty)),
                "unit_price": money(to_decimal(item.unit_price)),
                "line_total": money(to_decimal(item.line_total)),
            }
        )

    payments: list[Payment] = list(sale.payments)
    payment_method = str(payments[0].method) if payments else "OTHER"

    # Fallback semantics:
    # - if there is no original receipt snapshot, we can reliably reconstruct
    #   totals/items, but not the exact historical amount_tendered/change_due
    #   for cash beyond the persisted payment amount.
    if payment_method == "CASH":
        amount_tendered: Decimal | None = money(to_decimal(sale.total))
        change_due = Decimal("0.00")
    else:
        amount_tendered = None
        change_due = Decimal("0.00")

    return {
        "sale_id": int(sale.id),
        "branch_id": int(sale.branch_id),
        "cash_session_id": int(sale.cash_session_id),
        "created_at": sale.created_at,
        "payment_method": payment_method,
        "amount_tendered": amount_tendered,
        "change_due": change_due,
        "subtotal": money(to_decimal(sale.subtotal)),
        "tax": money(to_decimal(sale.tax)),
        "total": money(to_decimal(sale.total)),
        "items": items_payload,
    }


def get_reprint_payload(db: Session, *, sale_id: int) -> dict[str, Any]:
    """
    Return the canonical reprint payload for one sale.

    Preferred source:
    - persisted receipt_snapshot captured at checkout time

    Fallback source:
    - reconstructed receipt from sale/items/payments/current product projection

    Returns:
        {
          "sale_id": int,
          "source": "SNAPSHOT" | "RECONSTRUCTED",
          "reprint_count": int,
          "receipt": {...}
        }
    """
    sale = _require_sale(db, sale_id=int(sale_id))

    if sale.receipt_snapshot is not None:
        receipt = _normalize_snapshot(sale.receipt_snapshot)
        source = "SNAPSHOT"
    else:
        receipt = _reconstruct_receipt(db, sale=sale)
        source = "RECONSTRUCTED"

    return {
        "sale_id": int(sale.id),
        "source": source,
        "reprint_count": 1,
        "receipt": receipt,
    }
