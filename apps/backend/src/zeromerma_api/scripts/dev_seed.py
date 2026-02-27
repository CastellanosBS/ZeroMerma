"""
zeromerma_api/scripts/dev_seed.py

GOAL
----
Create a deterministic, idempotent "dev baseline" dataset.

"Deterministic" means:
- Same input -> same rows (same unique keys)
- Safe to run multiple times (no duplicates)
- After it finishes, API is immediately usable for dev/testing.

HOW TO RUN (from apps/backend)
------------------------------
poetry run python -m zeromerma_api.scripts.dev_seed
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from decimal import Decimal
from typing import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

# Settings/engine/session come from your app (single source of truth)
from zeromerma_api.core.settings import get_settings
from zeromerma_api.db.engine import SessionLocal

# Import ORM models (adjust imports if your module names differ)
from zeromerma_api.models.branch import Branch
from zeromerma_api.models.inventory_movement import InventoryMovement
from zeromerma_api.models.product import Product
from zeromerma_api.models.role import Role
from zeromerma_api.models.user_account import UserAccount

# We reuse your existing bootstrap logic for snapshot creation
from zeromerma_api.services.inventory_balance_service import (
    bootstrap_inventory_balance_from_ledger,
)

log = logging.getLogger(__name__)


# ----------------------------
# Seed "inputs" (deterministic)
# ----------------------------


@dataclass(frozen=True)
class SeedProduct:
    sku: str
    name: str
    opening_qty: Decimal


DEFAULT_BRANCH_CODE = "MAIN"
DEFAULT_BRANCH_NAME = "Main Branch"

DEFAULT_ROLES = [
    ("ADMIN", "Administrator"),
    ("CASHIER", "Cashier"),
]

DEFAULT_ADMIN_EMAIL = "admin@zeromerma.local"
DEFAULT_ADMIN_NAME = "ZeroMerma Admin"

DEFAULT_PRODUCTS: list[SeedProduct] = [
    SeedProduct(sku="DON-GLZ", name="Glazed donut", opening_qty=Decimal("50")),
    SeedProduct(sku="DON-CHC", name="Chocolate donut", opening_qty=Decimal("50")),
    SeedProduct(sku="COF-AMR", name="Americano coffee", opening_qty=Decimal("30")),
    SeedProduct(sku="BUN-TRD", name="Traditional bread", opening_qty=Decimal("40")),
]


# ----------------------------
# Small DB helpers (idempotent)
# ----------------------------
def get_or_create_branch(session: Session, *, code: str, name: str) -> Branch:
    """
    Upsert by Branch.code.

    Convergent behavior:
    - If the branch exists, we update stable fields to match the seed config.
    - If it doesn't exist, we insert it.

    Why update on existing?
    - If you tweak DEFAULT_BRANCH_NAME later, rerunning seed should converge.
    """
    existing = session.execute(
        select(Branch).where(Branch.code == code)
    ).scalar_one_or_none()
    if existing:
        # Keep seed deterministic: bring DB row to expected state.
        if existing.name != name:
            existing.name = name
        if getattr(existing, "is_active", None) is not True:
            existing.is_active = True
        session.flush()
        return existing

    obj = Branch(code=code, name=name, is_active=True)
    session.add(obj)
    session.flush()
    return obj


def get_or_create_role(session: Session, *, code: str, name: str) -> Role:
    """
    Upsert by Role.code with convergent updates.
    """
    existing = session.execute(
        select(Role).where(Role.code == code)
    ).scalar_one_or_none()
    if existing:
        if existing.name != name:
            existing.name = name
            session.flush()
        return existing

    obj = Role(code=code, name=name)
    session.add(obj)
    session.flush()
    return obj


def get_or_create_user(
    session: Session,
    *,
    email: str,
    full_name: str,
    branch_id: int,
    role_id: int,
) -> UserAccount:
    """
    Upsert by UserAccount.email with convergent updates.
    """
    existing = session.execute(
        select(UserAccount).where(UserAccount.email == email)
    ).scalar_one_or_none()
    if existing:
        changed = False
        if existing.full_name != full_name:
            existing.full_name = full_name
            changed = True
        if existing.branch_id != branch_id:
            existing.branch_id = branch_id
            changed = True
        if existing.role_id != role_id:
            existing.role_id = role_id
            changed = True
        if getattr(existing, "is_active", None) is not True:
            existing.is_active = True
            changed = True
        if changed:
            session.flush()
        return existing

    obj = UserAccount(
        email=email,
        full_name=full_name,
        branch_id=branch_id,
        role_id=role_id,
        is_active=True,
        password_hash=None,
    )
    session.add(obj)
    session.flush()
    return obj


def get_or_create_product(session: Session, *, sku: str, name: str) -> Product:
    """
    Upsert by Product.sku with convergent updates.
    """
    existing = session.execute(
        select(Product).where(Product.sku == sku)
    ).scalar_one_or_none()
    if existing:
        if existing.name != name:
            existing.name = name
        if getattr(existing, "is_active", None) is not True:
            existing.is_active = True
        session.flush()
        return existing

    obj = Product(sku=sku, name=name, is_active=True)
    session.add(obj)
    session.flush()
    return obj


def ensure_opening_balance_movements(
    session: Session,
    *,
    branch_id: int,
    created_by_id: int,
    products: Iterable[tuple[Product, Decimal]],
) -> int:
    """
    Create OPENING_BALANCE movements only if they do not exist.

    Determinism rule:
    - For each (branch_id, product_id), we create at most ONE opening balance movement.
    - If it already exists, we do nothing (idempotent).
    """
    created = 0

    for product, qty in products:
        # Is there already an OPENING_BALANCE for this branch+product?
        exists = session.execute(
            select(InventoryMovement.id).where(
                InventoryMovement.branch_id == branch_id,
                InventoryMovement.product_id == product.id,
                InventoryMovement.reason == "OPENING_BALANCE",
            )
        ).first()

        if exists:
            continue

        mv = InventoryMovement(
            branch_id=branch_id,
            product_id=product.id,
            qty=qty,
            reason="OPENING_BALANCE",
            ref_type="DEV_SEED",
            ref_id=None,
            note="Dev seed opening balance",
            created_by_id=created_by_id,
        )
        session.add(mv)
        created += 1

    session.flush()
    return created


def main() -> None:
    # 1) Ensure settings are loaded (DATABASE_URL, etc.)
    _ = get_settings()

    # 2) Create a DB session
    session = SessionLocal()
    try:
        # 3) Branch
        branch = get_or_create_branch(
            session, code=DEFAULT_BRANCH_CODE, name=DEFAULT_BRANCH_NAME
        )

        # 4) Roles
        roles: dict[str, Role] = {}
        for code, name in DEFAULT_ROLES:
            roles[code] = get_or_create_role(session, code=code, name=name)

        # 5) Admin user
        admin = get_or_create_user(
            session,
            email=DEFAULT_ADMIN_EMAIL,
            full_name=DEFAULT_ADMIN_NAME,
            branch_id=branch.id,
            role_id=roles["ADMIN"].id,
        )

        # 6) Products
        products_with_qty: list[tuple[Product, Decimal]] = []
        for p in DEFAULT_PRODUCTS:
            prod = get_or_create_product(session, sku=p.sku, name=p.name)
            products_with_qty.append((prod, p.opening_qty))

        # 7) Opening movements (ledger)
        created_movements = ensure_opening_balance_movements(
            session,
            branch_id=branch.id,
            created_by_id=admin.id,
            products=products_with_qty,
        )

        # 8) Commit ledger first (so bootstrap reads consistent data)
        session.commit()

        # 9) Bootstrap snapshot from ledger (inventory_balance)
        #    This function should internally open its own session or accept one.
        #    If it accepts a session, we can pass it; if not, it will use SessionLocal.
        bootstrap_inventory_balance_from_ledger(session, branch_id=branch.id)
        session.commit()

        log.info("Dev seed done.")
        log.info("branch=%s (%s)", branch.code, branch.id)
        log.info("admin=%s (%s)", admin.email, admin.id)
        log.info("products=%s", len(products_with_qty))
        log.info("opening movements created=%s", created_movements)

    finally:
        session.close()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    main()
