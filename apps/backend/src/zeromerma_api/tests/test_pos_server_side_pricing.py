from __future__ import annotations

import os
from decimal import Decimal
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from zeromerma_api.core.security import create_access_token
from zeromerma_api.db.engine import SessionLocal
from zeromerma_api.main import create_app
from zeromerma_api.tests.alembic_utils import alembic_upgrade_head


def auth_headers(*, user_id: int, role_code: str, branch_id: int) -> dict[str, str]:
    """
    Build Authorization headers with explicit role/branch claims for POS tests.
    """
    token = create_access_token(
        subject=str(int(user_id)),
        extra_claims={"role_code": str(role_code), "branch_id": int(branch_id)},
    )
    return {"Authorization": f"Bearer {token}"}


def reset_db(s: Session) -> None:
    """
    Hard reset all tables touched by pricing and POS sale tests.
    """
    s.execute(
        text(
            """
            TRUNCATE TABLE
                product_price,
                payment,
                sale_item,
                sale,
                inventory_movement,
                inventory_balance,
                cash_session,
                production_run,
                user_account,
                role,
                branch,
                product,
                product_category
            RESTART IDENTITY CASCADE
            """
        )
    )
    s.commit()


def seed_admin_branch_and_open_session(s: Session) -> dict[str, int]:
    """
    Create:
      - branch MAIN
      - role ADMIN
      - admin user
      - one OPEN cash session
    """
    branch_id = s.execute(
        text(
            """
            INSERT INTO branch (code, name, is_active, created_at, updated_at)
            VALUES ('MAIN','Main',TRUE,now(),now())
            RETURNING id
            """
        )
    ).scalar_one()

    role_id = s.execute(
        text(
            """
            INSERT INTO role (code, name, created_at, updated_at)
            VALUES ('ADMIN','Admin',now(),now())
            RETURNING id
            """
        )
    ).scalar_one()

    user_id = s.execute(
        text(
            """
            INSERT INTO user_account
                (branch_id, role_id, email, full_name, password_hash, is_active, created_at, updated_at)
            VALUES
                (:b,:r,'admin@example.com','Admin',NULL,TRUE,now(),now())
            RETURNING id
            """
        ),
        {"b": int(branch_id), "r": int(role_id)},
    ).scalar_one()

    cash_session_id = s.execute(
        text(
            """
            INSERT INTO cash_session
                (branch_id, opened_by_id, opened_at, opening_amount, status, created_at, updated_at)
            VALUES
                (:b, :u, now(), 0.00, 'OPEN', now(), now())
            RETURNING id
            """
        ),
        {"b": int(branch_id), "u": int(user_id)},
    ).scalar_one()

    s.commit()
    return {
        "branch_id": int(branch_id),
        "user_id": int(user_id),
        "cash_session_id": int(cash_session_id),
    }


def seed_category(s: Session) -> int:
    cat_id = s.execute(
        text(
            """
            INSERT INTO product_category (code, name, is_active, created_at, updated_at)
            VALUES ('FIN','Finished',TRUE,now(),now())
            RETURNING id
            """
        )
    ).scalar_one()
    s.commit()
    return int(cat_id)


def seed_product(
    s: Session,
    *,
    cat_id: int,
    sku: str,
    name: str,
    sale_price: Decimal | None,
) -> int:
    """
    Insert one finished product with optional catalog base sale_price.
    """
    if sale_price is None:
        pid = s.execute(
            text(
                """
                INSERT INTO product
                    (sku, name, category_id, uom, is_input, sale_price, is_active, created_at, updated_at)
                VALUES
                    (:sku, :name, :c, 'PCS', FALSE, NULL, TRUE, now(), now())
                RETURNING id
                """
            ),
            {"sku": sku, "name": name, "c": int(cat_id)},
        ).scalar_one()
    else:
        pid = s.execute(
            text(
                """
                INSERT INTO product
                    (sku, name, category_id, uom, is_input, sale_price, is_active, created_at, updated_at)
                VALUES
                    (:sku, :name, :c, 'PCS', FALSE, :price, TRUE, now(), now())
                RETURNING id
                """
            ),
            {"sku": sku, "name": name, "c": int(cat_id), "price": str(sale_price)},
        ).scalar_one()

    s.commit()
    return int(pid)


def seed_inventory_balance(
    s: Session,
    *,
    branch_id: int,
    product_id: int,
    on_hand: Decimal,
) -> None:
    """
    Ensure enough stock so pricing tests do not fail on inventory.
    """
    s.execute(
        text(
            """
            INSERT INTO inventory_balance (branch_id, product_id, on_hand, reserved, created_at, updated_at)
            VALUES (:b,:p,:oh,0,now(),now())
            ON CONFLICT (branch_id, product_id)
            DO UPDATE SET on_hand = EXCLUDED.on_hand, updated_at = now()
            """
        ),
        {"b": int(branch_id), "p": int(product_id), "oh": str(on_hand)},
    )
    s.commit()


def seed_price_override(
    s: Session,
    *,
    branch_id: int,
    product_id: int,
    price: Decimal,
    created_by_id: int,
) -> None:
    s.execute(
        text(
            """
            INSERT INTO product_price (branch_id, product_id, price, currency, created_by_id, created_at, updated_at)
            VALUES (:b,:p,:price,'MXN',:u,now(),now())
            ON CONFLICT (branch_id, product_id)
            DO UPDATE SET price = EXCLUDED.price, updated_at = now()
            """
        ),
        {"b": int(branch_id), "p": int(product_id), "price": str(price), "u": int(created_by_id)},
    )
    s.commit()


def count_rows(s: Session, table: str) -> int:
    return int(s.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar_one())


@pytest.mark.skipif(
    not os.getenv("DATABASE_URL"),
    reason="DATABASE_URL not set; skipping server-side pricing tests",
)
def test_pos_sale_uses_base_price_when_unit_price_missing():
    alembic_upgrade_head()

    s: Session = SessionLocal()
    try:
        reset_db(s)
        ids = seed_admin_branch_and_open_session(s)
        cat_id = seed_category(s)

        product_id = seed_product(
            s,
            cat_id=cat_id,
            sku="DONUT-BASE",
            name="Donut Base Price",
            sale_price=Decimal("50.00"),
        )
        seed_inventory_balance(
            s,
            branch_id=ids["branch_id"],
            product_id=product_id,
            on_hand=Decimal("100.000"),
        )
    finally:
        s.close()

    app = create_app()
    client = TestClient(app)
    headers = auth_headers(
        user_id=ids["user_id"],
        role_code="ADMIN",
        branch_id=ids["branch_id"],
    )

    resp = client.post(
        "/pos/sales",
        json={
            "branch_id": ids["branch_id"],
            "cash_session_id": ids["cash_session_id"],
            "items": [{"product_id": product_id, "qty": "2.000"}],
        },
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    sale: dict[str, Any] = resp.json()

    assert sale["status"] == "OPEN"
    assert Decimal(sale["subtotal"]) == Decimal("100.00")
    assert Decimal(sale["total"]) == Decimal("100.00")

    assert len(sale["items"]) == 1
    assert Decimal(sale["items"][0]["unit_price"]) == Decimal("50.00")
    assert Decimal(sale["items"][0]["line_total"]) == Decimal("100.00")


@pytest.mark.skipif(
    not os.getenv("DATABASE_URL"),
    reason="DATABASE_URL not set; skipping server-side pricing tests",
)
def test_pos_sale_uses_branch_override_when_unit_price_missing():
    alembic_upgrade_head()

    s: Session = SessionLocal()
    try:
        reset_db(s)
        ids = seed_admin_branch_and_open_session(s)
        cat_id = seed_category(s)

        product_id = seed_product(
            s,
            cat_id=cat_id,
            sku="DONUT-OVR",
            name="Donut Override Price",
            sale_price=Decimal("50.00"),
        )
        seed_inventory_balance(
            s,
            branch_id=ids["branch_id"],
            product_id=product_id,
            on_hand=Decimal("100.000"),
        )

        seed_price_override(
            s,
            branch_id=ids["branch_id"],
            product_id=product_id,
            price=Decimal("60.00"),
            created_by_id=ids["user_id"],
        )
    finally:
        s.close()

    app = create_app()
    client = TestClient(app)
    headers = auth_headers(
        user_id=ids["user_id"],
        role_code="ADMIN",
        branch_id=ids["branch_id"],
    )

    resp = client.post(
        "/pos/sales",
        json={
            "branch_id": ids["branch_id"],
            "cash_session_id": ids["cash_session_id"],
            "items": [{"product_id": product_id, "qty": "2.000"}],
        },
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    sale: dict[str, Any] = resp.json()

    assert Decimal(sale["subtotal"]) == Decimal("120.00")
    assert Decimal(sale["total"]) == Decimal("120.00")
    assert Decimal(sale["items"][0]["unit_price"]) == Decimal("60.00")
    assert Decimal(sale["items"][0]["line_total"]) == Decimal("120.00")


@pytest.mark.skipif(
    not os.getenv("DATABASE_URL"),
    reason="DATABASE_URL not set; skipping server-side pricing tests",
)
def test_pos_sale_without_any_price_returns_409_and_rolls_back():
    alembic_upgrade_head()

    s: Session = SessionLocal()
    try:
        reset_db(s)
        ids = seed_admin_branch_and_open_session(s)
        cat_id = seed_category(s)

        product_id = seed_product(
            s,
            cat_id=cat_id,
            sku="DONUT-NOPRICE",
            name="Donut No Price",
            sale_price=None,
        )
        seed_inventory_balance(
            s,
            branch_id=ids["branch_id"],
            product_id=product_id,
            on_hand=Decimal("100.000"),
        )
    finally:
        s.close()

    app = create_app()
    client = TestClient(app)
    headers = auth_headers(
        user_id=ids["user_id"],
        role_code="ADMIN",
        branch_id=ids["branch_id"],
    )

    resp = client.post(
        "/pos/sales",
        json={
            "branch_id": ids["branch_id"],
            "cash_session_id": ids["cash_session_id"],
            "items": [{"product_id": product_id, "qty": "1.000"}],
        },
        headers=headers,
    )

    assert resp.status_code == 409, resp.text

    s2: Session = SessionLocal()
    try:
        assert count_rows(s2, "sale") == 0
        assert count_rows(s2, "sale_item") == 0
        assert (
            int(
                s2.execute(
                    text("SELECT COUNT(*) FROM inventory_movement WHERE reason='SALE'")
                ).scalar_one()
            )
            == 0
        )
    finally:
        s2.close()
