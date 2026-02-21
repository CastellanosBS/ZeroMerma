# apps/backend/src/zeromerma_api/services/sale_service.py
# =============================================================================
# PURPOSE
# =============================================================================
# This module contains the business logic for POS Sales:
#   1) Create a Sale (header) + SaleItem (lines)
#   2) Compute totals on the backend (never trust client totals)
#   3) B3.4 Inventory coupling: write one InventoryMovement per SaleItem
#   4) Prevent oversell (MVP): reject sale if stock would go negative
#
# WHY SERVICE LAYER?
# - Keeps routers thin (HTTP concerns stay in routers)
# - Centralizes rules (easy to test and audit)
# - Defines a single place to change logic when you harden later
#
# =============================================================================
# MVP ASSUMPTIONS
# =============================================================================
# - There is no authoritative pricing model yet (Product has no "price" field).
#   Therefore, the client provides unit_price per line item.
# - Backend computes:
#     line_total = qty * unit_price
#     subtotal = sum(line_total)
#     tax = 0
#     total = subtotal
#
# - Inventory is a ledger:
#   on_hand(branch, product) = SUM(inventory_movement.qty)
#   and a sale writes a negative movement per line:
#     qty = -sale_item.qty
#     reason = "SALE"
#     ref_type = "SALE"
#     ref_id = sale.id
#
# =============================================================================

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
from zeromerma_api.services.inventory_service import get_on_hand

# -----------------------------------------------------------------------------
# Decimal quantization constants
# -----------------------------------------------------------------------------
# MONEY_PLACES:
#   - Used to round monetary values to 2 decimals (cents).
# QTY_PLACES:
#   - Used to round quantities to 3 decimals (common for weight-based units).
MONEY_PLACES = Decimal("0.01")
QTY_PLACES = Decimal("0.001")


# -----------------------------------------------------------------------------
# Helpers: safe Decimal conversion and rounding
# -----------------------------------------------------------------------------
def to_decimal(value: float | int | str) -> Decimal:
    """
    Convert value to Decimal safely.

    Why we do this:
    - floats are binary approximations and can produce artifacts like:
        0.1 + 0.2 = 0.30000000000000004
    - Decimal(str(value)) preserves what the user "meant" numerically
    """
    return Decimal(str(value))


def money(value: Decimal) -> Decimal:
    """
    Round a Decimal to cents using typical POS rounding.

    ROUND_HALF_UP:
    - 1.005 -> 1.01
    - this matches common financial expectations in retail/POS.
    """
    return value.quantize(MONEY_PLACES, rounding=ROUND_HALF_UP)


def qty(value: Decimal) -> Decimal:
    """
    Round quantity to 3 decimal places.
    """
    return value.quantize(QTY_PLACES, rounding=ROUND_HALF_UP)


# -----------------------------------------------------------------------------
# Validation helpers
# -----------------------------------------------------------------------------
def require_open_cash_session(
    db: Session, cash_session_id: int, branch_id: int
) -> CashSession:
    """
    Ensure the cash session exists, belongs to the branch, and is OPEN.
    """
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
    """
    Ensure the user exists.
    """
    u = db.get(UserAccount, user_id)
    if u is None:
        raise LookupError(f"User {user_id} not found.")
    return u


def require_products(db: Session, product_ids: list[int]) -> None:
    """
    Ensure all products exist.

    Implementation detail:
    - fetch all existing ids in one query
    - compare sets to find missing ids (fast, deterministic)
    """
    if not product_ids:
        raise ValueError("No items provided (product list is empty).")

    stmt = select(Product.id).where(Product.id.in_(product_ids))
    rows = db.execute(stmt).all()
    found = {r[0] for r in rows}

    missing = set(product_ids) - found
    if missing:
        raise LookupError(f"Missing products: {sorted(missing)}")


# -----------------------------------------------------------------------------
# Core: Create sale + items + inventory movements
# -----------------------------------------------------------------------------
def create_sale(
    db: Session,
    *,
    branch_id: int,
    cash_session_id: int,
    created_by_id: int,
    items: Iterable[dict],
) -> Sale:
    """
    Create a sale transactionally.

    Parameters
    ----------
    branch_id:
      - Branch where sale is registered.
    cash_session_id:
      - Must exist, must belong to branch_id, must be OPEN.
    created_by_id:
      - User who created the sale.
    items:
      - Iterable of dict with keys:
          product_id (int)
          qty (float)
          unit_price (float)

    Returns
    -------
    Sale ORM object (with items attached).
    Router is responsible for commit/rollback.
    """

    # 1) Validate required context (cash session + user)
    require_open_cash_session(db, cash_session_id=cash_session_id, branch_id=branch_id)
    require_user(db, created_by_id)

    # 2) Normalize items into list so we can read twice and compute totals
    item_list = list(items)
    if len(item_list) == 0:
        raise ValueError("Sale must have at least one item.")

    # 3) Validate products exist (single query)
    product_ids = [int(it["product_id"]) for it in item_list]
    require_products(db, product_ids)

    # 4) Compute line totals and aggregate subtotal using Decimal
    computed_items: list[SaleItem] = []
    subtotal_dec = Decimal("0.00")

    for it in item_list:
        # Extract and normalize types
        product_id = int(it["product_id"])
        qty_dec = qty(to_decimal(it["qty"]))
        unit_price_dec = money(to_decimal(it["unit_price"]))

        # Domain validation (beyond Pydantic)
        if qty_dec <= 0:
            raise ValueError(f"qty must be > 0 for product_id={product_id}")
        if unit_price_dec < 0:
            raise ValueError(f"unit_price must be >= 0 for product_id={product_id}")

        # Compute line total with rounding to cents
        line_total_dec = money(qty_dec * unit_price_dec)

        subtotal_dec += line_total_dec

        # Build the SaleItem ORM object (not yet attached to any Sale)
        computed_items.append(
            SaleItem(
                product_id=product_id,
                qty=float(qty_dec),  # DB NUMERIC(18,3)
                unit_price=float(unit_price_dec),  # DB NUMERIC(18,2)
                line_total=float(line_total_dec),  # DB NUMERIC(18,2)
            )
        )

    # 5) Compute tax/total (MVP: tax=0)
    tax_dec = Decimal("0.00")
    total_dec = money(subtotal_dec + tax_dec)

    # 6) Create sale header
    sale = Sale(
        branch_id=branch_id,
        cash_session_id=cash_session_id,
        created_by_id=created_by_id,
        subtotal=float(money(subtotal_dec)),
        tax=float(money(tax_dec)),
        total=float(total_dec),
        status=SaleStatus.OPEN.value,
    )

    # 7) Attach items via relationship (cascade inserts them when the sale is added)
    sale.items = computed_items

    # 8) Add and flush to materialize IDs and enforce FK constraints early
    db.add(sale)
    db.flush()  # sale.id exists after this, sale_item rows will also be staged/inserted

    # -------------------------------------------------------------------------
    # 9) B3.4 INVENTORY COUPLING (MVP)
    # -------------------------------------------------------------------------
    # For each sale item, append a ledger movement:
    #   qty = -sale_item.qty
    #
    # Oversell guardrail:
    #   on_hand - required_qty >= 0
    #
    # Important subtlety:
    # - We compute on_hand BEFORE inserting the SALE movements, so it represents
    #   stock prior to this sale. (The sale movements are not yet written.)
    #
    # Concurrency note:
    # - In production, two concurrent sales can both pass the check and oversell.
    #   We'll harden later using locks/advisory locks or serializable transactions.
    # -------------------------------------------------------------------------
    for si in computed_items:
        required_qty = qty(to_decimal(si.qty))

        on_hand = get_on_hand(db, branch_id=branch_id, product_id=si.product_id)

        if on_hand - required_qty < 0:
            raise ValueError(
                f"Insufficient stock for product_id={si.product_id}: "
                f"on_hand={on_hand}, required={required_qty}."
            )

        movement = InventoryMovement(
            branch_id=branch_id,
            product_id=si.product_id,
            qty=float(qty(Decimal("0.000") - required_qty)),  # negative quantity
            reason="SALE",
            ref_type="SALE",
            ref_id=sale.id,
            note=None,
            created_by_id=created_by_id,
        )
        db.add(movement)

    # Flush again so inventory movements are inserted and FKs checked now.
    db.flush()

    # 10) Return the Sale ORM (router will commit and refresh)
    return sale


# -----------------------------------------------------------------------------
# Listing sales (MVP)
# -----------------------------------------------------------------------------
def list_sales(
    db: Session,
    *,
    branch_id: int | None = None,
    cash_session_id: int | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[Sale]:
    """
    Minimal listing:
    - optional filters
    - newest first
    - basic paging
    """
    stmt = select(Sale).order_by(desc(Sale.created_at), desc(Sale.id))

    if branch_id is not None:
        stmt = stmt.where(Sale.branch_id == branch_id)

    if cash_session_id is not None:
        stmt = stmt.where(Sale.cash_session_id == cash_session_id)

    stmt = stmt.offset(offset).limit(limit)

    # scalars() returns Sale objects; .all() resolves list.

    return list(db.execute(stmt).scalars().all())
