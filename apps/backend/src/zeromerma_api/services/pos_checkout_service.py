from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

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
from zeromerma_api.models.branch import Branch
from zeromerma_api.models.product import Product
from zeromerma_api.models.product_category import ProductCategory
from zeromerma_api.models.product_price import ProductPrice
from zeromerma_api.models.sale import Sale
from zeromerma_api.services.payment_service import add_payment
from zeromerma_api.services.sale_service import create_sale

MONEY_PLACES = Decimal("0.01")
QTY_PLACES = Decimal("0.001")


@dataclass(frozen=True)
class ResolvedCheckoutLine:
    """
    One fully resolved checkout line, ready for create_sale() and receipt rendering.
    """

    product_id: int
    sku: str | None
    name: str
    quick_name: str | None
    uom: str
    qty: Decimal
    unit_price: Decimal
    line_total: Decimal


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


def _resolve_checkout_lines(
    db: Session,
    *,
    branch_id: int,
    items: list[dict],
) -> list[ResolvedCheckoutLine]:
    """
    Resolve all checkout lines against the current sellable catalog.

    Rules:
    - products must exist
    - products must be active
    - products must belong to an active POS-visible category
    - products must be visible in POS
    - products must be explicitly sellable in POS
    - products must not be inputs/raw materials
    - effective price = COALESCE(product_price.price, product.sale_price)
    """
    if not items:
        raise DomainValidationError(
            message="Checkout must contain at least one item.",
            details={"items": []},
        )

    requested_product_ids = [int(item["product_id"]) for item in items]

    stmt = (
        select(
            Product.id.label("product_id"),
            Product.sku.label("sku"),
            Product.name.label("name"),
            Product.quick_name.label("quick_name"),
            Product.uom.label("uom"),
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

    resolved: list[ResolvedCheckoutLine] = []

    for item in items:
        product_id = int(item["product_id"])
        raw_qty = qty(to_decimal(item["qty"]))
        row = row_map[product_id]

        if raw_qty <= 0:
            raise DomainValidationError(
                message="Checkout item quantity must be greater than zero.",
                details={
                    "product_id": product_id,
                    "qty": str(raw_qty),
                },
            )

        if not bool(row.product_is_active):
            raise DomainValidationError(
                message="Product is inactive and cannot be sold.",
                details={"product_id": product_id},
            )

        if bool(row.is_input):
            raise DomainValidationError(
                message="Input/raw-material products cannot be sold via POS.",
                details={"product_id": product_id},
            )

        if row.category_id is None:
            raise DomainValidationError(
                message="Product must belong to a POS-visible category.",
                details={"product_id": product_id},
            )

        if not bool(row.category_is_active):
            raise DomainValidationError(
                message="Product category is inactive and cannot be used in POS.",
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
                message="Product is not sellable in POS.",
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

        unit_price = money(to_decimal(row.effective_price))
        line_total = money(raw_qty * unit_price)

        resolved.append(
            ResolvedCheckoutLine(
                product_id=product_id,
                sku=row.sku,
                name=str(row.name),
                quick_name=row.quick_name,
                uom=str(row.uom),
                qty=raw_qty,
                unit_price=unit_price,
                line_total=line_total,
            )
        )

    return resolved


def _build_sale_input_lines(lines: list[ResolvedCheckoutLine]) -> list[dict]:
    """
    Convert resolved lines into the exact structure expected by create_sale().
    """
    return [
        {
            "product_id": int(line.product_id),
            "qty": line.qty,
            "unit_price": line.unit_price,
        }
        for line in lines
    ]


def _build_receipt_payload(
    *,
    sale: Sale,
    lines: list[ResolvedCheckoutLine],
    payment_method: str,
    amount_tendered: Decimal | None,
    change_due: Decimal,
) -> dict[str, Any]:
    """
    Build the receipt payload returned by checkout.

    Printing remains a non-blocking concern. This payload is intended for the
    frontend or a printer adapter to render after commit.
    """
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
        "items": [
            {
                "product_id": int(line.product_id),
                "sku": line.sku,
                "name": line.name,
                "quick_name": line.quick_name,
                "qty": line.qty,
                "unit_price": line.unit_price,
                "line_total": line.line_total,
            }
            for line in lines
        ],
    }


def _freeze_receipt_snapshot(value: Any) -> Any:
    """
    Convert the printable receipt payload into a JSON-serializable structure
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
    Persist one frozen receipt snapshot on the sale row.

    This allows future reprints to use the original printable payload instead
    of reconstructing from current catalog/pricing state.
    """
    sale.receipt_snapshot = _freeze_receipt_snapshot(receipt)


def checkout_pos_sale(
    db: Session,
    *,
    branch_id: int,
    cash_session_id: int,
    created_by_id: int,
    items: list[dict],
    payment: dict,
    print_ticket: bool,
) -> dict[str, Any]:
    """
    Execute one atomic POS checkout flow.

    Flow:
    1. validate branch
    2. resolve sellable products + effective prices
    3. create sale using canonical sale_service
    4. register one payment using canonical payment_service
    5. compute change (cash only)
    6. persist receipt_snapshot
    7. mark sale as PAID
    8. return receipt payload

    v1 constraints:
    - exactly one payment block
    - no split tender
    - CASH supports change
    - CARD/TRANSFER/OTHER behave as fully authorized methods for now
    """
    _require_branch(db, branch_id=int(branch_id))

    method = normalize_payment_method(payment["method"])
    if method not in PAYMENT_METHOD_VALUES:
        raise DomainValidationError(
            message=f"Unsupported checkout payment method '{method}'.",
            details={
                "method": method,
                "allowed_methods": list(PAYMENT_METHOD_VALUES),
            },
        )

    resolved_lines = _resolve_checkout_lines(
        db,
        branch_id=int(branch_id),
        items=items,
    )

    sale = create_sale(
        db=db,
        branch_id=int(branch_id),
        cash_session_id=int(cash_session_id),
        created_by_id=int(created_by_id),
        items=_build_sale_input_lines(resolved_lines),
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
        change_due = Decimal("0.00")

    reference = payment.get("reference") or payment.get("external_auth_code")

    payment_row = add_payment(
        db=db,
        sale_id=int(sale.id),
        method=method,
        amount=total,
        reference=reference,
    )
    db.flush()

    receipt = _build_receipt_payload(
        sale=sale,
        lines=resolved_lines,
        payment_method=method,
        amount_tendered=amount_tendered,
        change_due=change_due,
    )

    _persist_receipt_snapshot(sale=sale, receipt=receipt)

    sale.status = "PAID"
    db.flush()

    paid_amount = total
    balance_due = Decimal("0.00")

    return {
        "sale_id": int(sale.id),
        "payment_id": int(payment_row.id),
        "sale_status": "PAID",
        "payment_status": "AUTHORIZED",
        "subtotal": money(to_decimal(sale.subtotal)),
        "tax": money(to_decimal(sale.tax)),
        "total": total,
        "paid_amount": paid_amount,
        "change_due": change_due,
        "balance_due": balance_due,
        "print_ticket": bool(print_ticket),
        "receipt": receipt,
    }
