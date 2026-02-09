# apps/backend/scripts/dev_seed_inventory.py
# PURPOSE: Dev-only fixture to create one product and two ledger movements
#          so /inventory endpoints have something to show.

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from zeromerma_api.db.engine import SessionLocal
from zeromerma_api.models.branch import Branch
from zeromerma_api.models.inventory_movement import InventoryMovement, MovementReason
from zeromerma_api.models.product import Product


def ensure_main_branch(s: Session) -> Branch:
    """Get-or-create the canonical MAIN branch."""
    b = s.scalar(select(Branch).where(Branch.code == "MAIN"))
    if b is None:
        b = Branch(code="MAIN", name="Main Branch")
        s.add(b)
        s.flush()  # obtain b.id before commit
    return b


def ensure_product(s: Session, sku: str, name: str) -> Product:
    """Get-or-create a product by SKU."""
    p = s.scalar(select(Product).where(Product.sku == sku))
    if p is None:
        p = Product(sku=sku, name=name)
        s.add(p)
        s.flush()  # obtain p.id
    return p


def recreate_fixture_movements(s: Session, branch_id: int, product_id: int) -> None:
    """
    Clear prior movements for this (branch, product) pair and recreate:
      +10 OPENING_BALANCE, -3 SALE
    """
    # wipe old rows so the result is deterministic in dev
    s.query(InventoryMovement).filter(
        InventoryMovement.branch_id == branch_id,
        InventoryMovement.product_id == product_id,
    ).delete()
    s.flush()

    # +10 opening
    s.add(
        InventoryMovement(
            branch_id=branch_id,
            product_id=product_id,
            qty=10.000,
            reason=MovementReason.OPENING_BALANCE.value,
        )
    )
    # -3 sale
    s.add(
        InventoryMovement(
            branch_id=branch_id,
            product_id=product_id,
            qty=-3.000,
            reason=MovementReason.SALE.value,
        )
    )


def main() -> None:
    s = SessionLocal()
    try:
        branch = ensure_main_branch(s)
        prod = ensure_product(s, "DONUT-GLA", "Donut Glazed")
        recreate_fixture_movements(s, branch.id, prod.id)
        s.commit()
        print(
            f"[dev-seed] OK — branch_id={branch.id}, product_id={prod.id}, sku={prod.sku}"
        )
    finally:
        s.close()


if __name__ == "__main__":
    main()
