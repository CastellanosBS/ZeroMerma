# apps/backend/src/zeromerma_api/tests/test_inventory_endpoints.py
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

from zeromerma_api.core.security import create_access_token
from zeromerma_api.db.engine import SessionLocal
from zeromerma_api.main import create_app
from zeromerma_api.models.branch import Branch
from zeromerma_api.models.inventory_movement import InventoryMovement, MovementReason
from zeromerma_api.models.product import Product
from zeromerma_api.models.role import Role
from zeromerma_api.models.user_account import UserAccount


def auth_headers(user_id: int) -> dict[str, str]:
    """
    Build Authorization headers for protected endpoints.
    """
    token = create_access_token(subject=str(user_id))
    return {"Authorization": f"Bearer {token}"}


def _alembic_upgrade_head() -> None:
    backend_dir = Path(__file__).resolve().parents[3]
    cfg = Config(str(backend_dir / "alembic.ini"))
    cfg.set_main_option("script_location", str(backend_dir / "migrations"))
    cfg.set_main_option("sqlalchemy.url", os.environ["DATABASE_URL"])
    command.upgrade(cfg, "head")


@pytest.mark.skipif(
    not os.getenv("DATABASE_URL"),
    reason="DATABASE_URL not set; skipping inventory endpoint tests",
)
def test_stock_and_movements_endpoints():
    _alembic_upgrade_head()

    app = create_app()
    client = TestClient(app)

    s: Session = SessionLocal()
    try:
        # Ensure MAIN branch exists
        main = s.scalar(select(Branch).where(Branch.code == "MAIN"))
        if main is None:
            main = Branch(code="MAIN", name="Main Branch")
            s.add(main)
            s.flush()

        # Ensure ADMIN role exists
        role = s.scalar(select(Role).where(Role.code == "ADMIN"))
        if role is None:
            role = Role(code="ADMIN", name="Admin")
            s.add(role)
            s.flush()

        # Ensure user exists (needed only if /inventory/* is protected)
        user = s.scalar(
            select(UserAccount).where(UserAccount.email == "admin@example.com")
        )
        if user is None:
            user = UserAccount(
                branch_id=main.id,
                role_id=role.id,
                email="admin@example.com",
                full_name="Admin User",
                password_hash=None,
                is_active=True,
            )
            s.add(user)
            s.flush()

        # Ensure product exists
        prod = s.scalar(select(Product).where(Product.sku == "DONUT-GLA"))
        if prod is None:
            prod = Product(sku="DONUT-GLA", name="Donut Glazed", is_active=True)
            s.add(prod)
            s.flush()

        # Clear any prior movements for deterministic assertions
        s.query(InventoryMovement).filter(
            InventoryMovement.branch_id == main.id,
            InventoryMovement.product_id == prod.id,
        ).delete()
        s.flush()

        # Insert movements: +10, -3
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

        branch_id = int(main.id)
        product_id = int(prod.id)
        user_id = int(user.id)
    finally:
        s.close()

    # /inventory/stock
    r = client.get(
        "/inventory/stock",
        params={"branch_id": branch_id, "product_id": product_id},
        headers=auth_headers(user_id),
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

    # /inventory/movements
    r2 = client.get(
        "/inventory/movements",
        params={"branch_id": branch_id, "product_id": product_id, "limit": 10},
        headers=auth_headers(user_id),
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
