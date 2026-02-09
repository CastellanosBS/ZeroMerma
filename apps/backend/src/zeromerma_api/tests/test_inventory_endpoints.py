# apps/backend/tests/test_inventory_endpoints.py
# PURPOSE: Prove /inventory/stock and /inventory/movements behave correctly on real data.

from __future__ import annotations

import os
from typing import Any

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from zeromerma_api.db.engine import SessionLocal
from zeromerma_api.main import create_app
from zeromerma_api.models.branch import Branch
from zeromerma_api.models.inventory_movement import InventoryMovement, MovementReason
from zeromerma_api.models.product import Product


def _alembic_upgrade_head() -> None:
    """Apply all migrations to head using Alembic's programmatic API."""
    cfg = Config("alembic.ini")
    command.upgrade(cfg, "head")


@pytest.mark.skipif(
    not os.getenv("DATABASE_URL"),
    reason="DATABASE_URL not set; skipping inventory endpoint tests",
)
def test_stock_and_movements_endpoints():
    # 1) Bring schema up
    _alembic_upgrade_head()

    # 2) Build a test client
    app = create_app()
    client = TestClient(app)

    # 3) Create minimal fixture: ensure MAIN branch exists (from seeds or create if missing),
    #    create one product, and two movements: +10 OPENING_BALANCE, -3 SALE.
    s: Session = SessionLocal()
    try:
        # MAIN branch (create if missing)
        main = s.scalar(select(Branch).where(Branch.code == "MAIN"))
        if main is None:
            main = Branch(code="MAIN", name="Main Branch")
            s.add(main)
            s.flush()

        # Product
        prod = s.scalar(select(Product).where(Product.sku == "DONUT-GLA"))
        if prod is None:
            prod = Product(sku="DONUT-GLA", name="Donut Glazed")
            s.add(prod)
            s.flush()

        # Clear any prior movements for deterministic assertions (dev DB only).
        # NOTE: In production tests you'd use an isolated DB/schema; this keeps test stable locally.
        s.query(InventoryMovement).filter(
            InventoryMovement.branch_id == main.id,
            InventoryMovement.product_id == prod.id,
        ).delete()
        s.flush()

        # +10 opening balance
        s.add(
            InventoryMovement(
                branch_id=main.id,
                product_id=prod.id,
                qty=10.000,
                reason=MovementReason.OPENING_BALANCE.value,
            )
        )
        # -3 sale
        s.add(
            InventoryMovement(
                branch_id=main.id,
                product_id=prod.id,
                qty=-3.000,
                reason=MovementReason.SALE.value,
            )
        )
        s.commit()
    finally:
        s.close()

    # 4) Call /inventory/stock: expect a single row with qty=7
    r = client.get(
        "/inventory/stock", params={"branch_id": main.id, "product_id": prod.id}
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert isinstance(data, list)
    assert len(data) == 1
    row: dict[str, Any] = data[0]
    assert row["branch_id"] == main.id
    assert row["product_id"] == prod.id
    assert row["sku"] == "DONUT-GLA"
    assert row["product_name"] == "Donut Glazed"
    assert abs(row["qty"] - 7.0) < 1e-6  # 10 - 3 = 7

    # 5) Call /inventory/movements: expect two rows, newest first
    r2 = client.get(
        "/inventory/movements",
        params={"branch_id": main.id, "product_id": prod.id, "limit": 10},
    )
    assert r2.status_code == 200, r2.text
    items = r2.json()
    assert len(items) == 2
    # newest first should be the SALE (the second insert)
    assert items[0]["reason"] in ("SALE", MovementReason.SALE.value)
    assert items[0]["qty"] == -3.0
    assert items[1]["reason"] in (
        "OPENING_BALANCE",
        MovementReason.OPENING_BALANCE.value,
    )
    assert items[1]["qty"] == 10.0
