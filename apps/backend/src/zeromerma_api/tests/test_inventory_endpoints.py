# apps/backend/tests/test_inventory_endpoints.py
# PURPOSE: Prove /inventory/stock and /inventory/movements behave correctly on real data.

from __future__ import annotations

import os
from pathlib import Path
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


def make_alembic_config() -> Config:
    backend_dir = Path(__file__).resolve().parents[1]  # apps/backend
    alembic_ini = backend_dir / "alembic.ini"
    migrations_dir = backend_dir / "migrations"

    cfg = Config(str(alembic_ini))
    cfg.set_main_option("script_location", str(migrations_dir))
    return cfg


def _alembic_upgrade_head() -> None:
    # __file__ = .../apps/backend/src/zeromerma_api/tests/test_xxx.py
    # parents[0]=tests, [1]=zeromerma_api, [2]=src, [3]=backend
    backend_dir = Path(__file__).resolve().parents[3]

    cfg = Config(str(backend_dir / "alembic.ini"))

    # IMPORTANT: point to the real migrations folder
    cfg.set_main_option("script_location", str(backend_dir / "migrations"))

    # Make sure we use the DB from env var (the tests skip otherwise)
    cfg.set_main_option("sqlalchemy.url", os.environ["DATABASE_URL"])

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

    # 3) Create minimal fixture: ensure MAIN branch exists, create a product, and movements: +10, -3
    s: Session = SessionLocal()
    try:
        main = s.scalar(select(Branch).where(Branch.code == "MAIN"))
        if main is None:
            main = Branch(code="MAIN", name="Main Branch")
            s.add(main)
            s.flush()

        prod = s.scalar(select(Product).where(Product.sku == "DONUT-GLA"))
        if prod is None:
            prod = Product(sku="DONUT-GLA", name="Donut Glazed")
            s.add(prod)
            s.flush()

        # Clear any prior movements for deterministic assertions
        s.query(InventoryMovement).filter(
            InventoryMovement.branch_id == main.id,
            InventoryMovement.product_id == prod.id,
        ).delete()
        s.flush()

        s.add(
            InventoryMovement(
                branch_id=main.id,
                product_id=prod.id,
                qty=10.000,
                reason=MovementReason.OPENING_BALANCE.value,
            )
        )
        s.add(
            InventoryMovement(
                branch_id=main.id,
                product_id=prod.id,
                qty=-3.000,
                reason=MovementReason.SALE.value,
            )
        )
        s.commit()

        # IMPORTANT: keep ids outside the session scope for later asserts
        branch_id = int(main.id)
        product_id = int(prod.id)
    finally:
        s.close()

    # 4) Call /inventory/stock: expect qty=7
    r = client.get(
        "/inventory/stock", params={"branch_id": branch_id, "product_id": product_id}
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert isinstance(data, list)
    assert len(data) == 1
    row: dict[str, Any] = data[0]
    assert row["branch_id"] == branch_id
    assert row["product_id"] == product_id
    assert row["sku"] == "DONUT-GLA"
    assert row["product_name"] == "Donut Glazed"
    assert abs(row["qty"] - 7.0) < 1e-6  # 10 - 3 = 7

    # 5) Call /inventory/movements: expect two rows, newest first
    r2 = client.get(
        "/inventory/movements",
        params={"branch_id": branch_id, "product_id": product_id, "limit": 10},
    )
    assert r2.status_code == 200, r2.text
    items = r2.json()
    assert len(items) == 2
    assert items[0]["reason"] in ("SALE", MovementReason.SALE.value)
    assert items[0]["qty"] == -3.0
    assert items[1]["reason"] in (
        "OPENING_BALANCE",
        MovementReason.OPENING_BALANCE.value,
    )
    assert items[1]["qty"] == 10.0
