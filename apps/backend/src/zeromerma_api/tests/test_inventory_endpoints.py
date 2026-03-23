from __future__ import annotations

import os
from decimal import Decimal
from typing import Any
from uuid import uuid4

import pytest
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
from zeromerma_api.tests.alembic_utils import alembic_upgrade_head as _alembic_upgrade_head


def auth_headers(user_id: int) -> dict[str, str]:
    """
    Build Authorization headers for protected inventory endpoints.
    """
    token = create_access_token(subject=str(user_id))
    return {"Authorization": f"Bearer {token}"}


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

        # Ensure user exists (needed if /inventory/* is protected)
        user = s.scalar(select(UserAccount).where(UserAccount.email == "admin@example.com"))
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

        # Create an isolated product for deterministic assertions
        test_sku = f"DONUT-GLA-{uuid4().hex[:8].upper()}"

        prod = Product(
            sku=test_sku,
            name="Donut Glazed",
            is_active=True,
            uom="PCS",
            is_input=False,
        )
        s.add(prod)
        s.flush()

        # Clear any prior movements for this exact (branch, product)
        s.query(InventoryMovement).filter(
            InventoryMovement.branch_id == main.id,
            InventoryMovement.product_id == prod.id,
        ).delete()
        s.flush()

        # Insert deterministic ledger movements: +10, -3 => net 7
        s.add(
            InventoryMovement(
                branch_id=main.id,
                product_id=prod.id,
                qty=Decimal("10.000"),
                reason=MovementReason.OPENING_BALANCE.value,
            )
        )
        s.add(
            InventoryMovement(
                branch_id=main.id,
                product_id=prod.id,
                qty=Decimal("-3.000"),
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
    assert row["sku"] == test_sku
    assert row["product_name"] == "Donut Glazed"
    assert Decimal(row["qty"]) == Decimal("7.000")

    # /inventory/movements
    r2 = client.get(
        "/inventory/movements",
        params={"branch_id": branch_id, "product_id": product_id, "limit": 50},
        headers=auth_headers(user_id),
    )
    assert r2.status_code == 200, r2.text
    moves = r2.json()

    assert isinstance(moves, list)
    assert len(moves) == 2

    # Newest first (service orders by id desc), so SALE should typically come first
    reasons = {m["reason"] for m in moves}
    assert MovementReason.OPENING_BALANCE.value in reasons
    assert MovementReason.SALE.value in reasons

    qtys = sorted(Decimal(m["qty"]) for m in moves)
    assert qtys == [Decimal("-3.000"), Decimal("10.000")]
