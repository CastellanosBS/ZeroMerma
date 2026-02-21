# apps/backend/src/zeromerma_api/services/sale_service.py
# PURPOSE:
#   Business logic for POS sales creation and basic listing.
#   We keep this out of routers to:
#     - centralize rules
#     - keep endpoints thin
#     - make behavior testable and reusable
#
# MVP assumptions:
#   - Product has no official price table yet.
#   - Therefore client provides unit_price; backend persists it as a price snapshot.
#   - Backend still computes totals (never trust the client for totals).

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal  # Decimal is critical for money correctness.
from typing import Iterable, Sequence

from sqlalchemy import desc, select  # SQL query construction.
from sqlalchemy.orm import Session  # The DB session transaction context.

from zeromerma_api.models.cash_session import CashSession, CashSessionStatus
from zeromerma_api.models.product import Product
from zeromerma_api.models.sale import Sale, SaleStatus
from zeromerma_api.models.sale_item import SaleItem
from zeromerma_api.models.user_account import UserAccount

# --- Money helpers ------------------------------------------------------------

MONEY_PLACES = Decimal("0.01")  # 2 decimal places (cents)
QTY_PLACES = Decimal("0.001")  # 3 decimals for quantity


def to_decimal(value: float | int | str) -> Decimal:
    """
    Convert common numeric inputs to Decimal safely.
    Using str(value) avoids float binary artifacts like 0.30000000004.
    """
    return Decimal(str(value))


def money(value: Decimal) -> Decimal:
    """
    Quantize a Decimal to 2 decimal places using bankers-friendly rounding.
    ROUND_HALF_UP matches typical POS rounding.
    """
    return value.quantize(MONEY_PLACES, rounding=ROUND_HALF_UP)


def qty(value: Decimal) -> Decimal:
    """
    Quantize quantity to 3 decimals.
    """
    return value.quantize(QTY_PLACES, rounding=ROUND_HALF_UP)


# --- Core queries / validation ------------------------------------------------


def require_open_cash_session(
    db: Session, cash_session_id: int, branch_id: int
) -> CashSession:
    """
    Load a cash session and ensure it is OPEN and belongs to the given branch.
    Raises:
      - LookupError if it doesn't exist
      - ValueError if not OPEN or wrong branch
    """
    cs = db.get(CashSession, cash_session_id)  # Efficient PK lookup.
    if cs is None:
        raise LookupError(f"Cash session {cash_session_id} not found.")

    if cs.branch_id != branch_id:
        # Prevent creating sales in a session belonging to a different branch.
        raise ValueError(
            f"Cash session {cash_session_id} belongs to branch {cs.branch_id}, not {branch_id}."
        )

    if cs.status != CashSessionStatus.OPEN.value:
        raise ValueError(
            f"Cash session {cash_session_id} is not OPEN (status={cs.status})."
        )

    return cs


def require_user(db: Session, user_id: int) -> UserAccount:
    """
    Ensure the user exists.
    """
    u = db.get(UserAccount, user_id)
    if u is None:
        raise LookupError(f"User {user_id} not found.")
    return u


def require_products(db: Session, product_ids: Sequence[int]) -> None:
    """
    Ensure all products exist.
    This uses one query for all ids, then checks set difference.
    """
    if not product_ids:
        raise ValueError("No items provided (product list is empty).")

    stmt = select(Product.id).where(Product.id.in_(product_ids))
    rows = db.execute(stmt).all()
    found_ids = {r[0] for r in rows}

    missing = set(product_ids) - found_ids
    if missing:
        raise LookupError(f"Missing products: {sorted(missing)}")


# --- Sale creation ------------------------------------------------------------


def create_sale(
    db: Session,
    *,
    branch_id: int,
    cash_session_id: int,
    created_by_id: int,
    items: Iterable[dict],
) -> Sale:
    """
    Create a sale and its items in a single transaction (router will commit/rollback).

    `items` is an iterable of dicts like:
      {"product_id": int, "qty": float, "unit_price": float}

    Returns:
      The created Sale ORM object (with items attached).
    """
    # 1) Validate session + user exist and are consistent.
    require_open_cash_session(db, cash_session_id=cash_session_id, branch_id=branch_id)
    require_user(db, created_by_id)

    # 2) Normalize items to a list so we can iterate multiple times.
    item_list = list(items)
    if len(item_list) == 0:
        raise ValueError("Sale must have at least one item.")

    # 3) Validate that all referenced products exist (single query).
    product_ids = [int(it["product_id"]) for it in item_list]
    require_products(db, product_ids)

    # 4) Compute line totals and sale totals using Decimal for correctness.
    computed_items: list[SaleItem] = []
    subtotal_dec = Decimal("0.00")

    for it in item_list:
        # Convert inputs to Decimal using safe conversion.
        product_id = int(it["product_id"])
        qty_dec = qty(to_decimal(it["qty"]))
        unit_price_dec = money(to_decimal(it["unit_price"]))

        # Basic business validation (beyond Pydantic):
        if qty_dec <= 0:
            raise ValueError(f"qty must be > 0 for product_id={product_id}")
        if unit_price_dec < 0:
            raise ValueError(f"unit_price must be >= 0 for product_id={product_id}")

        # line_total = qty * unit_price, then quantize to cents.
        line_total_dec = money(qty_dec * unit_price_dec)

        subtotal_dec += line_total_dec

        computed_items.append(
            SaleItem(
                product_id=product_id,
                qty=float(qty_dec),  # store numeric; DB column is NUMERIC(18,3)
                unit_price=float(
                    unit_price_dec
                ),  # store numeric; DB column is NUMERIC(18,2)
                line_total=float(
                    line_total_dec
                ),  # store numeric; DB column is NUMERIC(18,2)
            )
        )

    # 5) Compute tax/total (MVP: tax=0).
    tax_dec = Decimal("0.00")
    total_dec = money(subtotal_dec + tax_dec)

    # 6) Create sale header ORM object.
    sale = Sale(
        branch_id=branch_id,
        cash_session_id=cash_session_id,
        created_by_id=created_by_id,
        subtotal=float(money(subtotal_dec)),
        tax=float(money(tax_dec)),
        total=float(total_dec),
        status=SaleStatus.OPEN.value,
    )

    # 7) Attach items to sale (relationship cascade will insert them).
    sale.items = computed_items

    # 8) Add and flush now so:
    #    - sale gets an id
    #    - DB FK constraints trigger immediately
    db.add(sale)
    db.flush()

    # 9) Return the ORM object; router will commit and refresh.
    return sale


# --- Listing sales (minimal for MVP) -----------------------------------------


def list_sales(
    db: Session,
    *,
    branch_id: int | None = None,
    cash_session_id: int | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[Sale]:
    """
    Minimal list for MVP:
      - optional filters
      - newest first
      - basic paging

    For now we return Sale objects; router controls response shape.
    """
    stmt = select(Sale).order_by(desc(Sale.created_at), desc(Sale.id))

    if branch_id is not None:
        stmt = stmt.where(Sale.branch_id == branch_id)
    if cash_session_id is not None:
        stmt = stmt.where(Sale.cash_session_id == cash_session_id)

    stmt = stmt.offset(offset).limit(limit)

    # scalars() returns Sale objects; .all() resolves list.
    return list(db.execute(stmt).scalars().all())
