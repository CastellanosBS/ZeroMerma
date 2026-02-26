# apps/backend/src/zeromerma_api/services/sale_service.py

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal
from typing import Iterable

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from zeromerma_api.models.cash_session import CashSession, CashSessionStatus
from zeromerma_api.models.inventory_movement import InventoryMovement
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
    qty as qty_dec,
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


def require_open_cash_session(
    db: Session, cash_session_id: int, branch_id: int
) -> CashSession:
    cs = db.get(CashSession, cash_session_id)
    if cs is None:
        raise LookupError(f"Cash session {cash_session_id} not found.")
    if cs.branch_id != branch_id:
        raise ValueError(
            f"Cash session {cash_session_id} belongs to branch {cs.branch_id}, not {branch_id}."
        )
    if cs.status != CashSessionStatus.OPEN.value:
        raise ValueError(
            f"Cash session {cash_session_id} is not OPEN (status={cs.status})."
        )
    return cs


def require_user(db: Session, user_id: int) -> UserAccount:
    u = db.get(UserAccount, user_id)
    if u is None:
        raise LookupError(f"User {user_id} not found.")
    return u


def require_products(db: Session, product_ids: list[int]) -> None:
    if not product_ids:
        raise ValueError("No items provided (product list is empty).")

    stmt = select(Product.id).where(Product.id.in_(product_ids))
    rows = db.execute(stmt).all()
    found = {r[0] for r in rows}
    missing = set(product_ids) - found
    if missing:
        raise LookupError(f"Missing products: {sorted(missing)}")


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

    Inventory rule (B3.5):
      - Use inventory_balance for operational stock.
      - Atomically decrement on_hand per item with guard (on_hand >= qty).
      - Append ledger movements in inventory_movement for audit trail.
    """
    # 1) Validate context
    require_open_cash_session(db, cash_session_id=cash_session_id, branch_id=branch_id)
    require_user(db, created_by_id)

    # 2) Normalize items
    item_list = list(items)
    if len(item_list) == 0:
        raise ValueError("Sale must have at least one item.")

    # 3) Validate products exist
    product_ids = [int(it["product_id"]) for it in item_list]
    require_products(db, product_ids)

    # 4) Compute items + totals
    computed_items: list[SaleItem] = []
    subtotal_dec = Decimal("0.00")

    for it in item_list:
        product_id = int(it["product_id"])
        q_dec = qty(to_decimal(it["qty"]))
        unit_price_dec = money(to_decimal(it["unit_price"]))

        if q_dec <= 0:
            raise ValueError(f"qty must be > 0 for product_id={product_id}")
        if unit_price_dec < 0:
            raise ValueError(f"unit_price must be >= 0 for product_id={product_id}")

        line_total_dec = money(q_dec * unit_price_dec)
        subtotal_dec += line_total_dec

        computed_items.append(
            SaleItem(
                product_id=product_id,
                qty=float(q_dec),
                unit_price=float(unit_price_dec),
                line_total=float(line_total_dec),
            )
        )

    tax_dec = Decimal("0.00")
    total_dec = money(subtotal_dec + tax_dec)

    # 5) Create sale header + attach items
    sale = Sale(
        branch_id=branch_id,
        cash_session_id=cash_session_id,
        created_by_id=created_by_id,
        subtotal=float(money(subtotal_dec)),
        tax=float(money(tax_dec)),
        total=float(total_dec),
        status=SaleStatus.OPEN.value,
    )
    sale.items = computed_items

    db.add(sale)
    db.flush()  # sale.id exists now

    # 6) Inventory effects (B3.5): atomic decrement + ledger append
    #
    # IMPORTANT:
    # - We do snapshot decrement first, then ledger append, for each line.
    # - Any failure raises ValueError -> router rollback -> all changes revert.
    for si in computed_items:
        required = qty_dec(to_decimal(si.qty))  # use shared quantizer (NUMERIC(18,3))

        # Ensure snapshot row exists (safe no-op if exists)
        ensure_balance_row(db, branch_id=branch_id, product_id=si.product_id)

        # Atomic decrement prevents oversell under concurrency
        _new_on_hand = atomic_decrement_on_hand(
            db,
            branch_id=branch_id,
            product_id=si.product_id,
            amount=required,
        )

        # Append ledger movement for audit trail (qty negative for SALE)
        db.add(
            InventoryMovement(
                branch_id=branch_id,
                product_id=si.product_id,
                qty=float(Decimal("0.000") - required),
                reason="SALE",
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
    stmt = select(Sale).order_by(desc(Sale.created_at), desc(Sale.id))

    if branch_id is not None:
        stmt = stmt.where(Sale.branch_id == branch_id)
    if cash_session_id is not None:
        stmt = stmt.where(Sale.cash_session_id == cash_session_id)

    stmt = stmt.offset(offset).limit(limit)
    return list(db.execute(stmt).scalars().all())
