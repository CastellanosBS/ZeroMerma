# apps/backend/src/zeromerma_api/services/sale_service.py
#
# PURPOSE:
#   POS sale orchestration:
#     - Validate context (open cash session, user exists, products exist)
#     - Guardrails (inputs cannot be sold via POS)
#     - Resolve effective prices when unit_price is omitted
#     - Compute totals and persist sale + items
#     - Apply inventory effects:
#         * snapshot decrement via inventory_balance (atomic to prevent oversell)
#         * ledger append via inventory_movement (auditable history)

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal
from typing import Iterable

from sqlalchemy import desc, select, text
from sqlalchemy.orm import Session

from zeromerma_api.core.domain_errors import (
    DomainConflictError,
    DomainInvariantError,
    DomainNotFoundError,
    DomainValidationError,
)
from zeromerma_api.models.cash_session import CashSession, CashSessionStatus
from zeromerma_api.models.inventory_movement import InventoryMovement, MovementReason
from zeromerma_api.models.product import Product
from zeromerma_api.models.sale import Sale, SaleStatus
from zeromerma_api.models.sale_item import SaleItem
from zeromerma_api.models.user_account import UserAccount
from zeromerma_api.services.inventory_balance_service import (
    atomic_decrement_on_hand,
    ensure_balance_row,
    to_decimal,
)
from zeromerma_api.services.inventory_balance_service import (
    qty as inv_qty,
)

MONEY_PLACES = Decimal("0.01")
QTY_PLACES = Decimal("0.001")


def money(value: Decimal) -> Decimal:
    """
    Round money to cents using POS-friendly rounding.
    """
    return value.quantize(MONEY_PLACES, rounding=ROUND_HALF_UP)


def qty(value: Decimal) -> Decimal:
    """
    Round quantity to 3 decimals.
    """
    return value.quantize(QTY_PLACES, rounding=ROUND_HALF_UP)


def assert_products_are_sellable(db: Session, *, product_ids: list[int]) -> None:
    """
    Guardrail: prevent selling inputs (ingredients/raw materials) via POS.

    Business rule:
      - product.is_input = TRUE  -> NOT sellable in POS
      - product.is_input = FALSE -> sellable
    """
    if not product_ids:
        raise DomainValidationError(
            message="Sale must contain at least one product.",
            details={"product_ids": []},
        )

    rows = db.execute(
        text(
            """
            SELECT id, is_input
            FROM product
            WHERE id = ANY(CAST(:ids AS BIGINT[]))
            """
        ),
        {"ids": [int(x) for x in product_ids]},
    ).fetchall()

    found_ids = {int(r[0]) for r in rows}
    missing = sorted(set(int(x) for x in product_ids) - found_ids)
    if missing:
        raise DomainNotFoundError(
            message="Some products do not exist.",
            details={"missing_product_ids": missing},
        )

    input_ids = sorted(int(r[0]) for r in rows if bool(r[1]) is True)
    if input_ids:
        raise DomainValidationError(
            message="Cannot sell input/ingredient products via POS.",
            details={"input_product_ids": input_ids},
        )


def require_open_cash_session(
    db: Session,
    *,
    cash_session_id: int,
    branch_id: int,
) -> CashSession:
    """
    Ensure the given cash session exists, belongs to the requested branch, and is OPEN.
    """
    cs = db.get(CashSession, cash_session_id)
    if cs is None:
        raise DomainNotFoundError(
            message=f"Cash session {cash_session_id} not found.",
            details={"cash_session_id": int(cash_session_id)},
        )

    if cs.branch_id != branch_id:
        raise DomainConflictError(
            message="Cash session does not belong to the requested branch.",
            details={
                "cash_session_id": int(cash_session_id),
                "expected_branch_id": int(branch_id),
                "actual_branch_id": int(cs.branch_id),
            },
        )

    if cs.status != CashSessionStatus.OPEN.value:
        raise DomainConflictError(
            message=f"Cash session {cash_session_id} is not OPEN.",
            details={
                "cash_session_id": int(cash_session_id),
                "status": str(cs.status),
            },
        )

    return cs


def require_user(db: Session, user_id: int) -> UserAccount:
    """
    Ensure the actor user exists.
    """
    user = db.get(UserAccount, user_id)
    if user is None:
        raise DomainNotFoundError(
            message=f"User {user_id} not found.",
            details={"user_id": int(user_id)},
        )
    return user


def require_products(db: Session, product_ids: list[int]) -> None:
    """
    Ensure all requested product IDs exist.
    """
    if not product_ids:
        raise DomainValidationError(
            message="Sale must have at least one item.",
            details={"product_ids": []},
        )

    stmt = select(Product.id).where(Product.id.in_(product_ids))
    rows = db.execute(stmt).all()
    found = {int(r[0]) for r in rows}
    missing = sorted(set(int(x) for x in product_ids) - found)

    if missing:
        raise DomainNotFoundError(
            message="Some products do not exist.",
            details={"missing_product_ids": missing},
        )


def _resolve_missing_unit_prices(
    db: Session,
    *,
    branch_id: int,
    item_list: list[dict],
) -> None:
    """
    Resolve missing unit prices server-side.

    Effective pricing policy:
      effective_price = COALESCE(product_price.price, product.sale_price)

    Mutates item_list in place by injecting Decimal-valued unit_price.
    """
    missing_ids = sorted(
        {int(it["product_id"]) for it in item_list if it.get("unit_price") is None}
    )
    if not missing_ids:
        return

    rows = db.execute(
        text(
            """
            SELECT
                p.id AS product_id,
                COALESCE(pp.price, p.sale_price) AS effective_price
            FROM product p
            LEFT JOIN product_price pp
                ON pp.branch_id = CAST(:branch_id AS BIGINT)
               AND pp.product_id = p.id
            WHERE p.id = ANY(CAST(:ids AS BIGINT[]))
            """
        ),
        {"branch_id": int(branch_id), "ids": missing_ids},
    ).fetchall()

    price_map: dict[int, Decimal | None] = {pid: None for pid in missing_ids}
    for row in rows:
        pid = int(row[0])
        eff = row[1]
        price_map[pid] = Decimal(str(eff)) if eff is not None else None

    for item in item_list:
        if item.get("unit_price") is None:
            pid = int(item["product_id"])
            eff = price_map.get(pid)
            if eff is None:
                raise DomainConflictError(
                    message="No effective price configured for product.",
                    details={
                        "branch_id": int(branch_id),
                        "product_id": pid,
                    },
                )
            item["unit_price"] = eff


def create_sale(
    db: Session,
    *,
    branch_id: int,
    cash_session_id: int,
    created_by_id: int,
    items: Iterable[dict],
) -> Sale:
    """
    Create a sale + items + inventory effects in a single transaction.

    Inventory rule:
      - Use inventory_balance for operational stock.
      - Atomically decrement on_hand per item with guard (on_hand >= qty).
      - Append ledger movements in inventory_movement for audit trail.

    Pricing rule:
      - unit_price may be omitted per item.
      - Missing unit_price is resolved server-side via effective pricing policy.
    """
    require_open_cash_session(
        db,
        cash_session_id=cash_session_id,
        branch_id=branch_id,
    )
    require_user(db, created_by_id)

    item_list = list(items)
    if len(item_list) == 0:
        raise DomainValidationError(
            message="Sale must contain at least one item.",
            details={"items": []},
        )

    product_ids = [int(it["product_id"]) for it in item_list]
    require_products(db, product_ids)
    assert_products_are_sellable(db, product_ids=product_ids)
    _resolve_missing_unit_prices(db, branch_id=branch_id, item_list=item_list)

    computed_items: list[SaleItem] = []
    subtotal_dec = Decimal("0.00")

    for item in item_list:
        product_id = int(item["product_id"])
        q_dec = qty(to_decimal(item["qty"]))

        unit_price_raw = item.get("unit_price")
        if unit_price_raw is None:
            raise DomainInvariantError(
                message="unit_price is still missing after pricing resolution.",
                details={"product_id": product_id},
            )

        unit_price_dec = money(to_decimal(unit_price_raw))

        if q_dec <= 0:
            raise DomainValidationError(
                message="Item quantity must be greater than zero.",
                details={
                    "product_id": product_id,
                    "qty": str(q_dec),
                },
            )

        if unit_price_dec < 0:
            raise DomainValidationError(
                message="Item unit_price must be greater than or equal to zero.",
                details={
                    "product_id": product_id,
                    "unit_price": str(unit_price_dec),
                },
            )

        line_total_dec = money(q_dec * unit_price_dec)
        subtotal_dec += line_total_dec

        computed_items.append(
            SaleItem(
                product_id=product_id,
                qty=q_dec,
                unit_price=unit_price_dec,
                line_total=line_total_dec,
            )
        )

    tax_dec = Decimal("0.00")
    total_dec = money(subtotal_dec + tax_dec)

    sale = Sale(
        branch_id=branch_id,
        cash_session_id=cash_session_id,
        created_by_id=created_by_id,
        subtotal=money(subtotal_dec),
        tax=money(tax_dec),
        total=total_dec,
        status=SaleStatus.OPEN.value,
    )
    sale.items = computed_items

    db.add(sale)
    db.flush()

    for sale_item in computed_items:
        required = inv_qty(to_decimal(sale_item.qty))

        ensure_balance_row(
            db,
            branch_id=branch_id,
            product_id=sale_item.product_id,
        )

        try:
            atomic_decrement_on_hand(
                db,
                branch_id=branch_id,
                product_id=sale_item.product_id,
                amount=required,
            )
        except ValueError as e:
            raise DomainConflictError(
                message="Insufficient stock to complete sale.",
                details={
                    "branch_id": int(branch_id),
                    "product_id": int(sale_item.product_id),
                    "required_qty": str(required),
                },
            ) from e

        db.add(
            InventoryMovement(
                branch_id=branch_id,
                product_id=sale_item.product_id,
                qty=Decimal("0.000") - required,
                reason=MovementReason.SALE.value,
                ref_type="SALE",
                ref_id=sale.id,
                note=None,
                created_by_id=created_by_id,
            )
        )

    db.flush()
    return sale


def list_sales(
    db: Session,
    *,
    branch_id: int | None = None,
    cash_session_id: int | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[Sale]:
    """
    List sale headers using the current canonical filters.
    """
    stmt = select(Sale).order_by(desc(Sale.created_at), desc(Sale.id))

    if branch_id is not None:
        stmt = stmt.where(Sale.branch_id == branch_id)

    if cash_session_id is not None:
        stmt = stmt.where(Sale.cash_session_id == cash_session_id)

    stmt = stmt.offset(offset).limit(limit)
    return list(db.execute(stmt).scalars().all())
