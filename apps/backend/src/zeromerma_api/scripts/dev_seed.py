# apps/backend/src/zeromerma_api/scripts/dev_seed.py
# PURPOSE:
#   Deterministic development seeding for ZeroMerma.
#
# WHAT THIS SCRIPT DOES (HIGH-LEVEL):
#   1) Ensures admin core entities exist (branch, roles, users).
#   2) Seeds catalog foundations:
#        - product_category
#        - product with v2 fields (category_id, uom, is_input, sale_price, standard_cost)
#   3) Seeds opening inventory ledger movements (OPENING_BALANCE) for deterministic stock.
#   4) Bootstraps inventory_balance snapshot from the ledger (so operational stock is consistent).
#
# DESIGN PRINCIPLES:
#   - Idempotent: running multiple times should not duplicate records.
#   - Backward-compatible: does not assume new fields are NOT NULL (except uom/is_input defaults).
#   - Safe: avoids creating negative stock in inventory_balance.

from __future__ import annotations

import logging
from dataclasses import dataclass
from decimal import Decimal
from typing import Iterable

from sqlalchemy import text
from sqlalchemy.orm import Session

from zeromerma_api.core.security import hash_password
from zeromerma_api.core.settings import get_settings
from zeromerma_api.db.engine import SessionLocal
from zeromerma_api.services.inventory_balance_service import (
    bootstrap_inventory_balance_from_ledger,
)

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Seed constants (edit these if you want different defaults)
# ---------------------------------------------------------------------------

DEFAULT_BRANCH_CODE = "MAIN"
DEFAULT_BRANCH_NAME = "Main Branch"

DEFAULT_ADMIN_EMAIL = "admin@zeromerma.local"
DEFAULT_ADMIN_NAME = "Admin User"
DEFAULT_ADMIN_PASSWORD = "admin1234"

DEFAULT_CASHIER_EMAIL = "cashier@zeromerma.local"
DEFAULT_CASHIER_NAME = "Cashier User"
DEFAULT_CASHIER_PASSWORD = "cashier1234"

# A stable marker used to make ledger movements idempotent.
SEED_REF_TYPE = "SEED"
SEED_REF_ID = 1
OPENING_NOTE = "DEV_SEED_OPENING_BALANCE"

# A stable marker used to detect whether we already created the optional sample sale/payment.
SAMPLE_PAYMENT_REFERENCE = "DEV_SEED_SAMPLE_V1"

# ---------------------------------------------------------------------------
# Catalog definitions
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CategoryDef:
    code: str
    name: str


@dataclass(frozen=True)
class ProductDef:
    sku: str
    name: str
    category_code: str
    uom: str  # Must satisfy the CHECK constraint (PCS/KG/G/L/ML)
    is_input: bool
    sale_price: Decimal | None
    standard_cost: Decimal | None
    opening_qty: Decimal  # Opening inventory (ledger)


DEFAULT_CATEGORIES: list[CategoryDef] = [
    CategoryDef(code="DONUTS", name="Donuts"),
    CategoryDef(code="PASTRY", name="Pastry"),
    CategoryDef(code="BREAD", name="Bread"),
    CategoryDef(code="DRINKS", name="Drinks"),
    CategoryDef(code="INGREDIENTS", name="Ingredients"),
]

# NOTE:
# - Keep at least one sellable product with enough opening_qty so the sample sale can succeed.
# - Keep all opening_qty >= 0 to avoid inventory_balance negative check violations.
DEFAULT_PRODUCTS: list[ProductDef] = [
    # Sellable products
    ProductDef(
        sku="DONUT-GLA",
        name="Donut Glazed",
        category_code="DONUTS",
        uom="PCS",
        is_input=False,
        sale_price=Decimal("18.00"),
        standard_cost=Decimal("6.00"),
        opening_qty=Decimal("50.000"),
    ),
    ProductDef(
        sku="DONUT-CHO",
        name="Donut Chocolate",
        category_code="DONUTS",
        uom="PCS",
        is_input=False,
        sale_price=Decimal("20.00"),
        standard_cost=Decimal("7.00"),
        opening_qty=Decimal("40.000"),
    ),
    ProductDef(
        sku="COFFEE-AM",
        name="Coffee Americano",
        category_code="DRINKS",
        uom="PCS",
        is_input=False,
        sale_price=Decimal("35.00"),
        standard_cost=Decimal("10.00"),
        opening_qty=Decimal("30.000"),
    ),
    # Inputs / ingredients (not sold directly)
    ProductDef(
        sku="FLOUR",
        name="Wheat Flour",
        category_code="INGREDIENTS",
        uom="KG",
        is_input=True,
        sale_price=None,
        standard_cost=Decimal("18.00"),
        opening_qty=Decimal("25.000"),
    ),
]


# ---------------------------------------------------------------------------
# DB helpers (idempotent "get or create")
# ---------------------------------------------------------------------------


def get_or_create_branch(db: Session, *, code: str, name: str) -> int:
    """
    Get or create a branch by code.

    Returns:
      branch_id
    """
    row = db.execute(
        text("SELECT id FROM branch WHERE code = :code"),
        {"code": code},
    ).fetchone()

    if row:
        return int(row[0])

    branch_id = db.execute(
        text(
            """
            INSERT INTO branch (code, name, is_active, created_at, updated_at)
            VALUES (:code, :name, true, now(), now())
            RETURNING id
            """
        ),
        {"code": code, "name": name},
    ).scalar_one()

    return int(branch_id)


def get_or_create_role(db: Session, *, code: str, name: str) -> int:
    """
    Get or create a role by code.

    Returns:
      role_id
    """
    row = db.execute(
        text("SELECT id FROM role WHERE code = :code"),
        {"code": code},
    ).fetchone()

    if row:
        return int(row[0])

    role_id = db.execute(
        text(
            """
            INSERT INTO role (code, name, created_at, updated_at)
            VALUES (:code, :name, now(), now())
            RETURNING id
            """
        ),
        {"code": code, "name": name},
    ).scalar_one()

    return int(role_id)


def get_or_create_user(
    db: Session,
    *,
    email: str,
    full_name: str,
    branch_id: int,
    role_id: int,
    password: str,
) -> int:
    """
    Get or create a user by email.

    Behavior:
      - If user exists but password_hash is NULL, we set it (so login works).
      - We also ensure branch_id/role_id and is_active are aligned with seed defaults
        (safe for dev; for prod you would not do this blindly).

    Returns:
      user_id
    """
    email_norm = email.strip().lower()

    row = db.execute(
        text("SELECT id, password_hash FROM user_account WHERE email = :email"),
        {"email": email_norm},
    ).fetchone()

    if row:
        user_id = int(row[0])
        password_hash = row[1]

        # Ensure password exists for login in dev.
        if password_hash is None:
            db.execute(
                text(
                    """
                    UPDATE user_account
                    SET password_hash = :ph, updated_at = now()
                    WHERE id = :id
                    """
                ),
                {"ph": hash_password(password), "id": user_id},
            )

        # Keep dev users aligned (role/branch/active/name)
        db.execute(
            text(
                """
                UPDATE user_account
                SET branch_id = :b,
                    role_id = :r,
                    full_name = :n,
                    is_active = true,
                    updated_at = now()
                WHERE id = :id
                """
            ),
            {"b": int(branch_id), "r": int(role_id), "n": full_name, "id": user_id},
        )

        return user_id

    user_id = db.execute(
        text(
            """
            INSERT INTO user_account (branch_id, role_id, email, full_name, password_hash, is_active, created_at, updated_at)
            VALUES (:b, :r, :email, :name, :ph, true, now(), now())
            RETURNING id
            """
        ),
        {
            "b": int(branch_id),
            "r": int(role_id),
            "email": email_norm,
            "name": full_name,
            "ph": hash_password(password),
        },
    ).scalar_one()

    return int(user_id)


def get_or_create_category(db: Session, *, code: str, name: str) -> int:
    """
    Get or create a product category by code.

    Returns:
      category_id
    """
    row = db.execute(
        text("SELECT id FROM product_category WHERE code = :code"),
        {"code": code},
    ).fetchone()

    if row:
        category_id = int(row[0])
        # Keep name aligned in dev.
        db.execute(
            text(
                "UPDATE product_category SET name = :name, updated_at = now() WHERE id = :id"
            ),
            {"name": name, "id": category_id},
        )
        return category_id

    category_id = db.execute(
        text(
            """
            INSERT INTO product_category (code, name, is_active, created_at, updated_at)
            VALUES (:code, :name, true, now(), now())
            RETURNING id
            """
        ),
        {"code": code, "name": name},
    ).scalar_one()

    return int(category_id)


def get_or_create_product(
    db: Session,
    *,
    sku: str,
    name: str,
    category_id: int | None,
    uom: str,
    is_input: bool,
    sale_price: Decimal | None,
    standard_cost: Decimal | None,
    is_active: bool = True,
) -> int:
    """
    Get or create a product by sku.

    Behavior:
      - If exists: update name + v2 fields (category/uom/is_input/sale_price/standard_cost/is_active).
      - If missing: insert with v2 fields.
    """
    sku_norm = sku.strip().upper()

    row = db.execute(
        text("SELECT id FROM product WHERE sku = :sku"),
        {"sku": sku_norm},
    ).fetchone()

    if row:
        product_id = int(row[0])
        db.execute(
            text(
                """
                UPDATE product
                SET name = :name,
                    category_id = :category_id,
                    uom = :uom,
                    is_input = :is_input,
                    sale_price = :sale_price,
                    standard_cost = :standard_cost,
                    is_active = :is_active,
                    updated_at = now()
                WHERE id = :id
                """
            ),
            {
                "name": name,
                "category_id": int(category_id) if category_id is not None else None,
                "uom": uom,
                "is_input": bool(is_input),
                "sale_price": sale_price,
                "standard_cost": standard_cost,
                "is_active": bool(is_active),
                "id": product_id,
            },
        )
        return product_id

    product_id = db.execute(
        text(
            """
            INSERT INTO product (sku, name, category_id, uom, is_input, sale_price, standard_cost, is_active, created_at, updated_at)
            VALUES (:sku, :name, :category_id, :uom, :is_input, :sale_price, :standard_cost, :is_active, now(), now())
            RETURNING id
            """
        ),
        {
            "sku": sku_norm,
            "name": name,
            "category_id": int(category_id) if category_id is not None else None,
            "uom": uom,
            "is_input": bool(is_input),
            "sale_price": sale_price,
            "standard_cost": standard_cost,
            "is_active": bool(is_active),
        },
    ).scalar_one()

    return int(product_id)


def ensure_opening_balance_movements(
    db: Session,
    *,
    branch_id: int,
    created_by_id: int,
    products: Iterable[tuple[int, Decimal]],
) -> int:
    """
    Ensure deterministic OPENING_BALANCE movements exist for (branch, product).

    Idempotency rule:
      A movement is considered the "seed opening balance" if:
        - reason = 'OPENING_BALANCE'
        - ref_type = 'SEED'
        - ref_id = 1
        - note = OPENING_NOTE

    Returns:
      number_of_movements_created
    """
    created = 0

    for product_id, opening_qty in products:
        qty = Decimal(opening_qty)

        # Never create negative opening quantities (would break snapshot non-negative checks).
        if qty < 0:
            raise ValueError(
                f"Invalid opening_qty for product_id={product_id}: {qty}. Must be >= 0."
            )

        # If qty is zero, we skip creating the movement.
        if qty == 0:
            continue

        exists = db.execute(
            text(
                """
                SELECT 1
                FROM inventory_movement
                WHERE branch_id = :b
                  AND product_id = :p
                  AND reason = 'OPENING_BALANCE'
                  AND ref_type = :rt
                  AND ref_id = :rid
                  AND note = :note
                LIMIT 1
                """
            ),
            {
                "b": int(branch_id),
                "p": int(product_id),
                "rt": SEED_REF_TYPE,
                "rid": SEED_REF_ID,
                "note": OPENING_NOTE,
            },
        ).fetchone()

        if exists:
            continue

        db.execute(
            text(
                """
                INSERT INTO inventory_movement
                  (branch_id, product_id, qty, reason, ref_type, ref_id, note, created_by_id, created_at, updated_at)
                VALUES
                  (:b, :p, :q, 'OPENING_BALANCE', :rt, :rid, :note, :u, now(), now())
                """
            ),
            {
                "b": int(branch_id),
                "p": int(product_id),
                "q": float(qty),
                "rt": SEED_REF_TYPE,
                "rid": SEED_REF_ID,
                "note": OPENING_NOTE,
                "u": int(created_by_id),
            },
        )
        created += 1

    return created


def assert_ledger_non_negative(db: Session, *, branch_id: int) -> None:
    """
    Safety check before bootstrapping snapshot:

    inventory_balance enforces on_hand >= 0.
    Since bootstrap computes on_hand = SUM(inventory_movement.qty),
    we must ensure no product has net negative qty in the ledger.
    """
    rows = db.execute(
        text(
            """
            SELECT product_id, SUM(qty) AS sum_qty
            FROM inventory_movement
            WHERE branch_id = :b
            GROUP BY product_id
            HAVING SUM(qty) < 0
            ORDER BY SUM(qty) ASC
            """
        ),
        {"b": int(branch_id)},
    ).fetchall()

    if rows:
        details = ", ".join([f"(product_id={r[0]}, sum_qty={r[1]})" for r in rows])
        raise RuntimeError(
            "Ledger has negative net stock for some products in this branch. "
            "Fix the ledger before bootstrapping inventory_balance. "
            f"branch_id={branch_id} negatives: {details}"
        )


def sample_sale_already_seeded(db: Session) -> bool:
    """
    Detect if we already created the sample transaction.

    We use payment.reference as a stable marker.
    """
    row = db.execute(
        text(
            """
            SELECT 1
            FROM payment
            WHERE reference = :ref
            LIMIT 1
            """
        ),
        {"ref": SAMPLE_PAYMENT_REFERENCE},
    ).fetchone()

    return bool(row)


def main() -> None:
    # 1) Ensure settings are loaded (.env, DATABASE_URL, etc.)
    _ = get_settings()

    # 2) Create a DB session
    session = SessionLocal()

    try:
        # -------------------------------------------------------------------
        # (A) Admin core entities
        # -------------------------------------------------------------------
        branch_id = get_or_create_branch(
            session, code=DEFAULT_BRANCH_CODE, name=DEFAULT_BRANCH_NAME
        )

        admin_role_id = get_or_create_role(session, code="ADMIN", name="Admin")
        cashier_role_id = get_or_create_role(session, code="CASHIER", name="Cashier")

        admin_user_id = get_or_create_user(
            session,
            email=DEFAULT_ADMIN_EMAIL,
            full_name=DEFAULT_ADMIN_NAME,
            branch_id=branch_id,
            role_id=admin_role_id,
            password=DEFAULT_ADMIN_PASSWORD,
        )

        _ = get_or_create_user(
            session,
            email=DEFAULT_CASHIER_EMAIL,
            full_name=DEFAULT_CASHIER_NAME,
            branch_id=branch_id,
            role_id=cashier_role_id,
            password=DEFAULT_CASHIER_PASSWORD,
        )

        # -------------------------------------------------------------------
        # (B) Catalog: categories + products (ProductCategory + Product v2)
        # -------------------------------------------------------------------
        category_ids: dict[str, int] = {}
        for c in DEFAULT_CATEGORIES:
            category_ids[c.code] = get_or_create_category(
                session, code=c.code, name=c.name
            )

        products_with_qty: list[tuple[int, Decimal]] = []
        for p in DEFAULT_PRODUCTS:
            cat_id = category_ids.get(p.category_code)
            product_id = get_or_create_product(
                session,
                sku=p.sku,
                name=p.name,
                category_id=cat_id,
                uom=p.uom,
                is_input=p.is_input,
                sale_price=p.sale_price,
                standard_cost=p.standard_cost,
                is_active=True,
            )
            products_with_qty.append((product_id, p.opening_qty))

        session.commit()

        # -------------------------------------------------------------------
        # (C) Ledger: deterministic opening balance movements
        # -------------------------------------------------------------------
        created_movements = ensure_opening_balance_movements(
            session,
            branch_id=branch_id,
            created_by_id=admin_user_id,
            products=products_with_qty,
        )

        session.commit()

        # -------------------------------------------------------------------
        # (D) Snapshot: bootstrap inventory_balance from ledger
        # -------------------------------------------------------------------
        assert_ledger_non_negative(session, branch_id=branch_id)
        bootstrap_inventory_balance_from_ledger(session, branch_id=branch_id)
        session.commit()

        # -------------------------------------------------------------------
        # (E) Optional: sample sale/payment (kept minimal & deterministic)
        # -------------------------------------------------------------------
        # NOTE:
        # We keep this optional flow because it validates end-to-end POS + inventory coupling.
        # It must never create negative ledger totals.
        if not sample_sale_already_seeded(session):
            # Choose a sellable product with sufficient opening stock
            sellable = [
                p
                for p in DEFAULT_PRODUCTS
                if not p.is_input and p.opening_qty >= Decimal("5.000")
            ]
            if not sellable:
                log.warning(
                    "No sellable products with enough stock for sample sale; skipping."
                )
            else:
                # We do not import services here to keep the seed decoupled.
                # Instead, we rely on your API flow/tests for sale creation.
                # If you want, we can wire in create_sale/add_payment here in Phase 6.1-C.
                log.info("sample_sale_skipped=True (kept for next step Phase 6.1-C)")
        else:
            log.info("sample_sale_already_seeded=True")

        # -------------------------------------------------------------------
        # Summary logs (helpful when running dev-seed.ps1)
        # -------------------------------------------------------------------
        log.info("Dev seed done.")
        log.info("branch_id=%s", branch_id)
        log.info("admin_user_id=%s email=%s", admin_user_id, DEFAULT_ADMIN_EMAIL)
        log.info("categories=%s", len(DEFAULT_CATEGORIES))
        log.info("products=%s", len(DEFAULT_PRODUCTS))
        log.info("opening movements created=%s", created_movements)

    finally:
        session.close()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    main()
