# apps/backend/src/zeromerma_api/scripts/dev_seed.py
from __future__ import annotations

import logging
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from typing import Iterable, Sequence

from sqlalchemy import text
from sqlalchemy.orm import Session

from zeromerma_api.core.security import hash_password
from zeromerma_api.core.settings import get_settings
from zeromerma_api.db.engine import SessionLocal
from zeromerma_api.services.inventory_balance_service import (
    bootstrap_inventory_balance_from_ledger,
)

log = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# Seed configuration (deterministic inputs)
# -----------------------------------------------------------------------------

DEFAULT_BRANCH_CODE = "MAIN"
DEFAULT_BRANCH_NAME = "Main Branch"

DEFAULT_ROLES: list[tuple[str, str]] = [
    ("ADMIN", "Administrator"),
    ("CASHIER", "Cashier"),
]

DEFAULT_ADMIN_EMAIL = "admin@zeromerma.local"
DEFAULT_ADMIN_NAME = "ZeroMerma Admin"

# Deterministic dev password (acceptable for dev seed only).
DEFAULT_ADMIN_PASSWORD = "admin1234"

# Deterministic marker used to identify a seeded sample transaction.
SEED_SAMPLE_PAYMENT_REF = "DEV_SEED_SAMPLE_SALE_V1"

QTY_PLACES = Decimal("0.001")
MONEY_PLACES = Decimal("0.01")


@dataclass(frozen=True)
class SeedProduct:
    sku: str
    name: str
    opening_qty: Decimal


DEFAULT_PRODUCTS: list[SeedProduct] = [
    SeedProduct(sku="DON-GLZ", name="Glazed donut", opening_qty=Decimal("50.000")),
    SeedProduct(sku="DON-CHC", name="Chocolate donut", opening_qty=Decimal("50.000")),
    SeedProduct(sku="COF-AMR", name="Americano coffee", opening_qty=Decimal("30.000")),
    SeedProduct(sku="BUN-TRD", name="Traditional bread", opening_qty=Decimal("40.000")),
]


# -----------------------------------------------------------------------------
# Small numeric helpers
# -----------------------------------------------------------------------------


def qty(value: Decimal) -> Decimal:
    """
    Quantize quantities to 3 decimals to match NUMERIC(18,3).
    """
    return value.quantize(QTY_PLACES, rounding=ROUND_HALF_UP)


def money(value: Decimal) -> Decimal:
    """
    Quantize money values to 2 decimals to match NUMERIC(18,2).
    """
    return value.quantize(MONEY_PLACES, rounding=ROUND_HALF_UP)


# -----------------------------------------------------------------------------
# DB helpers (idempotent + convergent behavior)
# -----------------------------------------------------------------------------


def get_or_create_branch(db: Session, *, code: str, name: str) -> int:
    """
    Upsert by branch.code.

    Convergent behavior:
    - If exists, update name/is_active to expected seed values.
    - If missing, insert.

    Returns:
      branch_id
    """
    row = (
        db.execute(
            text("SELECT id, name, is_active FROM branch WHERE code = :code"),
            {"code": code},
        )
        .mappings()
        .first()
    )

    if row:
        # Converge to expected state
        if row["name"] != name or row["is_active"] is not True:
            db.execute(
                text(
                    """
                    UPDATE branch
                    SET name = :name,
                        is_active = true,
                        updated_at = now()
                    WHERE id = :id
                    """
                ),
                {"id": int(row["id"]), "name": name},
            )
        return int(row["id"])

    new_id = db.execute(
        text(
            """
            INSERT INTO branch (code, name, is_active, created_at, updated_at)
            VALUES (:code, :name, true, now(), now())
            RETURNING id
            """
        ),
        {"code": code, "name": name},
    ).scalar_one()

    return int(new_id)


def get_or_create_role(db: Session, *, code: str, name: str) -> int:
    """
    Upsert by role.code; converge role.name.

    Returns:
      role_id
    """
    row = (
        db.execute(
            text("SELECT id, name FROM role WHERE code = :code"),
            {"code": code},
        )
        .mappings()
        .first()
    )

    if row:
        if row["name"] != name:
            db.execute(
                text(
                    """
                    UPDATE role
                    SET name = :name,
                        updated_at = now()
                    WHERE id = :id
                    """
                ),
                {"id": int(row["id"]), "name": name},
            )
        return int(row["id"])

    new_id = db.execute(
        text(
            """
            INSERT INTO role (code, name, created_at, updated_at)
            VALUES (:code, :name, now(), now())
            RETURNING id
            """
        ),
        {"code": code, "name": name},
    ).scalar_one()

    return int(new_id)


def get_or_create_admin_user(
    db: Session,
    *,
    email: str,
    full_name: str,
    branch_id: int,
    role_id: int,
    plain_password: str,
) -> int:
    """
    Upsert by user_account.email; converge identity fields and password_hash.

    DEV SEED POLICY:
    - We ensure the seeded admin account always has a deterministic password hash.
    - This is acceptable for local development.
    - In production, password resets must be explicit and audited.

    Returns:
      user_id
    """
    seeded_hash = hash_password(plain_password)

    row = (
        db.execute(
            text(
                """
            SELECT id, full_name, branch_id, role_id, is_active, password_hash
            FROM user_account
            WHERE email = :email
            """
            ),
            {"email": email},
        )
        .mappings()
        .first()
    )

    if row:
        changed = False
        updates: dict[str, object] = {
            "id": int(row["id"]),
            "full_name": full_name,
            "branch_id": int(branch_id),
            "role_id": int(role_id),
            "password_hash": seeded_hash,
        }

        if row["full_name"] != full_name:
            changed = True
        if int(row["branch_id"]) != int(branch_id):
            changed = True
        if int(row["role_id"]) != int(role_id):
            changed = True
        if row["is_active"] is not True:
            changed = True
        if (row["password_hash"] or "") != seeded_hash:
            changed = True

        if changed:
            db.execute(
                text(
                    """
                    UPDATE user_account
                    SET full_name = :full_name,
                        branch_id = :branch_id,
                        role_id = :role_id,
                        is_active = true,
                        password_hash = :password_hash,
                        updated_at = now()
                    WHERE id = :id
                    """
                ),
                updates,
            )

        return int(row["id"])

    new_id = db.execute(
        text(
            """
            INSERT INTO user_account
              (branch_id, role_id, email, full_name, password_hash, is_active, created_at, updated_at)
            VALUES
              (:branch_id, :role_id, :email, :full_name, :password_hash, true, now(), now())
            RETURNING id
            """
        ),
        {
            "branch_id": int(branch_id),
            "role_id": int(role_id),
            "email": email,
            "full_name": full_name,
            "password_hash": seeded_hash,
        },
    ).scalar_one()

    return int(new_id)


def get_or_create_product(db: Session, *, sku: str, name: str) -> int:
    """
    Upsert by product.sku; converge product.name and is_active.

    Returns:
      product_id
    """
    row = (
        db.execute(
            text("SELECT id, name, is_active FROM product WHERE sku = :sku"),
            {"sku": sku},
        )
        .mappings()
        .first()
    )

    if row:
        if row["name"] != name or row["is_active"] is not True:
            db.execute(
                text(
                    """
                    UPDATE product
                    SET name = :name,
                        is_active = true,
                        updated_at = now()
                    WHERE id = :id
                    """
                ),
                {"id": int(row["id"]), "name": name},
            )
        return int(row["id"])

    new_id = db.execute(
        text(
            """
            INSERT INTO product (sku, name, is_active, created_at, updated_at)
            VALUES (:sku, :name, true, now(), now())
            RETURNING id
            """
        ),
        {"sku": sku, "name": name},
    ).scalar_one()

    return int(new_id)


def ensure_opening_balance_movements(
    db: Session,
    *,
    branch_id: int,
    created_by_id: int,
    products: Iterable[tuple[int, Decimal]],
) -> int:
    """
    Ensure at most one OPENING_BALANCE per (branch_id, product_id).

    Idempotency rule:
    - If an opening balance movement exists, do nothing.
    - Otherwise, insert one movement.

    Returns:
      count_created
    """
    created = 0

    for product_id, opening_qty in products:
        exists = db.execute(
            text(
                """
                SELECT 1
                FROM inventory_movement
                WHERE branch_id = :b
                  AND product_id = :p
                  AND reason = 'OPENING_BALANCE'
                LIMIT 1
                """
            ),
            {"b": int(branch_id), "p": int(product_id)},
        ).first()

        if exists:
            continue

        db.execute(
            text(
                """
                INSERT INTO inventory_movement
                  (branch_id, product_id, qty, reason, ref_type, ref_id, note, created_by_id, created_at, updated_at)
                VALUES
                  (:b, :p, :q, 'OPENING_BALANCE', 'DEV_SEED', NULL, 'Dev seed opening balance', :u, now(), now())
                """
            ),
            {
                "b": int(branch_id),
                "p": int(product_id),
                "q": float(qty(opening_qty)),
                "u": int(created_by_id),
            },
        )
        created += 1

    return created


def get_or_create_open_cash_session(
    db: Session,
    *,
    branch_id: int,
    opened_by_id: int,
    opening_amount: Decimal,
) -> int:
    """
    Ensure exactly one OPEN cash session per branch.

    Returns:
      cash_session_id
    """
    row = db.execute(
        text(
            """
            SELECT id
            FROM cash_session
            WHERE branch_id = :b
              AND status = 'OPEN'
            LIMIT 1
            """
        ),
        {"b": int(branch_id)},
    ).first()

    if row:
        return int(row[0])

    new_id = db.execute(
        text(
            """
            INSERT INTO cash_session
              (branch_id, opened_by_id, opening_amount, status, created_at, updated_at, opened_at)
            VALUES
              (:b, :u, :amt, 'OPEN', now(), now(), now())
            RETURNING id
            """
        ),
        {
            "b": int(branch_id),
            "u": int(opened_by_id),
            "amt": float(money(opening_amount)),
        },
    ).scalar_one()

    return int(new_id)


def sample_sale_already_seeded(db: Session) -> bool:
    """
    Determine whether the deterministic sample sale is already present.

    We key idempotency off payment.reference because sale has no reference column.
    """
    row = db.execute(
        text("SELECT 1 FROM payment WHERE reference = :ref LIMIT 1"),
        {"ref": SEED_SAMPLE_PAYMENT_REF},
    ).first()
    return row is not None


def create_sample_sale_payment_and_inventory(
    db: Session,
    *,
    branch_id: int,
    cash_session_id: int,
    created_by_id: int,
    products: Sequence[tuple[str, int]],
) -> int:
    """
    Create a deterministic sample sale (one-time, idempotent marker lives in payment.reference).

    What we insert:
    - sale
    - 2 sale_item rows
    - payment (method=CASH, reference=SEED_SAMPLE_PAYMENT_REF)
    - inventory_movement rows with reason=SALE (negative qty) referencing the sale

    Returns:
      sale_id
    """
    if len(products) < 2:
        raise ValueError("Need at least 2 products to create a sample sale.")

    # Deterministically pick two products by SKU order
    prods_sorted = sorted(products, key=lambda x: x[0])
    sku1, p1 = prods_sorted[0]
    sku2, p2 = prods_sorted[1]

    qty1 = qty(Decimal("2.000"))
    qty2 = qty(Decimal("1.000"))
    unit1 = money(Decimal("25.00"))
    unit2 = money(Decimal("30.00"))

    line1 = money(qty1 * unit1)
    line2 = money(qty2 * unit2)

    subtotal = money(line1 + line2)
    tax = money(Decimal("0.00"))
    total = money(subtotal + tax)

    sale_id = db.execute(
        text(
            """
            INSERT INTO sale
              (branch_id, cash_session_id, created_by_id, created_at, subtotal, tax, total, status, updated_at)
            VALUES
              (:b, :cs, :u, now(), :subtotal, :tax, :total, 'OPEN', now())
            RETURNING id
            """
        ),
        {
            "b": int(branch_id),
            "cs": int(cash_session_id),
            "u": int(created_by_id),
            "subtotal": float(subtotal),
            "tax": float(tax),
            "total": float(total),
        },
    ).scalar_one()
    sale_id = int(sale_id)

    db.execute(
        text(
            """
            INSERT INTO sale_item (sale_id, product_id, qty, unit_price, line_total)
            VALUES (:sale_id, :p, :q, :unit, :line)
            """
        ),
        {
            "sale_id": sale_id,
            "p": int(p1),
            "q": float(qty1),
            "unit": float(unit1),
            "line": float(line1),
        },
    )

    db.execute(
        text(
            """
            INSERT INTO sale_item (sale_id, product_id, qty, unit_price, line_total)
            VALUES (:sale_id, :p, :q, :unit, :line)
            """
        ),
        {
            "sale_id": sale_id,
            "p": int(p2),
            "q": float(qty2),
            "unit": float(unit2),
            "line": float(line2),
        },
    )

    # Deterministic payment marker
    db.execute(
        text(
            """
            INSERT INTO payment (sale_id, method, amount, reference, created_at)
            VALUES (:sale_id, 'CASH', :amount, :ref, now())
            """
        ),
        {"sale_id": sale_id, "amount": float(total), "ref": SEED_SAMPLE_PAYMENT_REF},
    )

    # Inventory coupling via ledger movements (negative quantities)
    db.execute(
        text(
            """
            INSERT INTO inventory_movement
              (branch_id, product_id, qty, reason, ref_type, ref_id, note, created_by_id, created_at, updated_at)
            VALUES
              (:b, :p, :q, 'SALE', 'sale', :sale_id, 'Dev seed sample sale', :u, now(), now())
            """
        ),
        {
            "b": int(branch_id),
            "p": int(p1),
            "q": float(qty(Decimal("-1") * qty1)),
            "sale_id": sale_id,
            "u": int(created_by_id),
        },
    )

    db.execute(
        text(
            """
            INSERT INTO inventory_movement
              (branch_id, product_id, qty, reason, ref_type, ref_id, note, created_by_id, created_at, updated_at)
            VALUES
              (:b, :p, :q, 'SALE', 'sale', :sale_id, 'Dev seed sample sale', :u, now(), now())
            """
        ),
        {
            "b": int(branch_id),
            "p": int(p2),
            "q": float(qty(Decimal("-1") * qty2)),
            "sale_id": sale_id,
            "u": int(created_by_id),
        },
    )

    # Mark sale as paid (simple deterministic state for dev)
    db.execute(
        text("UPDATE sale SET status = 'PAID', updated_at = now() WHERE id = :id"),
        {"id": sale_id},
    )

    log.info("Seeded sample sale: id=%s, items=[%s,%s]", sale_id, sku1, sku2)
    return sale_id


def find_negative_ledger_balances(
    db: Session, *, branch_id: int
) -> list[dict[str, object]]:
    """
    Scan the inventory ledger for negative net on_hand (per product) for a branch.

    Why:
    - inventory_balance has a non-negative check constraint.
    - bootstrapping snapshot from ledger will fail if ledger sums are negative.

    Returns:
      A list of rows with negative balances:
        [{"product_id": ..., "on_hand": ...}, ...]
    """
    rows = (
        db.execute(
            text(
                """
            SELECT product_id, COALESCE(SUM(qty), 0) AS on_hand
            FROM inventory_movement
            WHERE branch_id = :b
            GROUP BY product_id
            HAVING COALESCE(SUM(qty), 0) < 0
            ORDER BY product_id
            """
            ),
            {"b": int(branch_id)},
        )
        .mappings()
        .all()
    )

    return [dict(r) for r in rows]


def main() -> None:
    """
    Deterministic dev seed entrypoint.

    Goals:
    - Create a minimal baseline dataset (branch, roles, admin, products).
    - Create deterministic opening inventory movements (idempotent).
    - Ensure one OPEN cash session exists (idempotent).
    - Optionally seed a deterministic sample sale/payment (idempotent marker).
    - Bootstrap inventory_balance ONLY if this seed run introduced new ledger rows.
      Also, guard against negative ledger sums to avoid constraint violations.
    """
    _ = get_settings()

    db: Session = SessionLocal()
    try:
        # ---------------------------------------------------------------------
        # 1) Core reference entities
        # ---------------------------------------------------------------------
        branch_id = get_or_create_branch(
            db, code=DEFAULT_BRANCH_CODE, name=DEFAULT_BRANCH_NAME
        )

        role_ids: dict[str, int] = {}
        for code, name in DEFAULT_ROLES:
            role_ids[code] = get_or_create_role(db, code=code, name=name)

        admin_user_id = get_or_create_admin_user(
            db,
            email=DEFAULT_ADMIN_EMAIL,
            full_name=DEFAULT_ADMIN_NAME,
            branch_id=branch_id,
            role_id=role_ids["ADMIN"],
            plain_password=DEFAULT_ADMIN_PASSWORD,
        )

        cash_session_id = get_or_create_open_cash_session(
            db,
            branch_id=branch_id,
            opened_by_id=admin_user_id,
            opening_amount=Decimal("1000.00"),
        )

        # ---------------------------------------------------------------------
        # 2) Products
        # ---------------------------------------------------------------------
        product_pairs: list[tuple[str, int]] = []
        opening_pairs: list[tuple[int, Decimal]] = []

        for p in DEFAULT_PRODUCTS:
            pid = get_or_create_product(db, sku=p.sku, name=p.name)
            product_pairs.append((p.sku, pid))
            opening_pairs.append((pid, p.opening_qty))

        # ---------------------------------------------------------------------
        # 3) Ledger: opening balance movements (idempotent)
        # ---------------------------------------------------------------------
        created_opening_movements = ensure_opening_balance_movements(
            db,
            branch_id=branch_id,
            created_by_id=admin_user_id,
            products=opening_pairs,
        )

        # ---------------------------------------------------------------------
        # 4) Optional sample sale + payment + ledger SALE movements (idempotent)
        # ---------------------------------------------------------------------
        sample_sale_created = False
        if not sample_sale_already_seeded(db):
            _ = create_sample_sale_payment_and_inventory(
                db,
                branch_id=branch_id,
                cash_session_id=cash_session_id,
                created_by_id=admin_user_id,
                products=product_pairs,
            )
            sample_sale_created = True
        else:
            log.info("sample_sale_already_seeded=True")

        # Commit all writes (reference entities + ledger inserts)
        db.commit()

        # ---------------------------------------------------------------------
        # 5) Snapshot bootstrap (guarded)
        # ---------------------------------------------------------------------
        should_bootstrap_snapshot = (
            created_opening_movements > 0
        ) or sample_sale_created

        if should_bootstrap_snapshot:
            negatives = find_negative_ledger_balances(db, branch_id=branch_id)
            if negatives:
                # Do not attempt snapshot bootstrap if ledger sums are negative,
                # because inventory_balance has a non-negative check constraint.
                log.error(
                    "inventory_balance bootstrap skipped due to negative ledger balances: %s",
                    negatives,
                )
                log.error(
                    "Fix ledger inconsistencies (e.g., missing OPENING_BALANCE) before bootstrapping snapshot."
                )
            else:
                bootstrap_inventory_balance_from_ledger(db, branch_id=branch_id)
                db.commit()
                log.info("inventory_balance bootstrap completed.")
        else:
            log.info(
                "inventory_balance bootstrap skipped (no new ledger movements created)."
            )

        # ---------------------------------------------------------------------
        # 6) Summary
        # ---------------------------------------------------------------------
        log.info("Dev seed done.")
        log.info("branch=%s (%s)", DEFAULT_BRANCH_CODE, branch_id)
        log.info("admin=%s (%s)", DEFAULT_ADMIN_EMAIL, admin_user_id)
        log.info("cash_session_open_id=%s", cash_session_id)
        log.info("products=%s", len(DEFAULT_PRODUCTS))
        log.info("opening movements created=%s", created_opening_movements)

    finally:
        db.close()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    main()
