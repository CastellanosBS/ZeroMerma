from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from zeromerma_api.core.security import create_access_token
from zeromerma_api.db.engine import SessionLocal
from zeromerma_api.main import create_app
from zeromerma_api.tests.alembic_utils import alembic_upgrade_head


def auth_headers(user_id: int) -> dict[str, str]:
    token = create_access_token(subject=str(user_id))
    return {"Authorization": f"Bearer {token}"}


def reset_db(s: Session) -> None:
    s.execute(
        text(
            """
            TRUNCATE TABLE
                customer_order_item,
                customer_order,
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


def seed_role(s: Session, code: str, name: str) -> int:
    role_id = s.execute(
        text(
            """
            INSERT INTO role (code, name, created_at, updated_at)
            VALUES (:code, :name, now(), now())
            RETURNING id
            """
        ),
        {"code": code, "name": name},
    ).scalar_one()
    s.commit()
    return int(role_id)


def seed_branch(s: Session, code: str, name: str) -> int:
    branch_id = s.execute(
        text(
            """
            INSERT INTO branch (code, name, is_active, created_at, updated_at)
            VALUES (:code, :name, TRUE, now(), now())
            RETURNING id
            """
        ),
        {"code": code, "name": name},
    ).scalar_one()
    s.commit()
    return int(branch_id)


def seed_user(
    s: Session,
    *,
    branch_id: int,
    role_id: int,
    email: str,
    full_name: str,
) -> int:
    user_id = s.execute(
        text(
            """
            INSERT INTO user_account
                (branch_id, role_id, email, full_name, password_hash, is_active, created_at, updated_at)
            VALUES
                (:branch_id, :role_id, :email, :full_name, NULL, TRUE, now(), now())
            RETURNING id
            """
        ),
        {
            "branch_id": int(branch_id),
            "role_id": int(role_id),
            "email": email,
            "full_name": full_name,
        },
    ).scalar_one()
    s.commit()
    return int(user_id)


def seed_category(
    s: Session,
    *,
    code: str,
    name: str,
    quick_name: str,
) -> int:
    category_id = s.execute(
        text(
            """
            INSERT INTO product_category
                (code, name, quick_name, show_in_pos, default_pos_order, is_active, created_at, updated_at)
            VALUES
                (:code, :name, :quick_name, TRUE, 10, TRUE, now(), now())
            RETURNING id
            """
        ),
        {"code": code, "name": name, "quick_name": quick_name},
    ).scalar_one()
    s.commit()
    return int(category_id)


def seed_product(
    s: Session,
    *,
    category_id: int,
    branch_id: int,
    sku: str,
    name: str,
    quick_name: str,
    sale_price: Decimal,
) -> int:
    product_id = s.execute(
        text(
            """
            INSERT INTO product
                (
                    sku, name, quick_name, category_id, uom, is_input,
                    show_in_pos, is_sellable_in_pos, default_pos_order,
                    sale_price, is_active, created_at, updated_at
                )
            VALUES
                (
                    :sku, :name, :quick_name, :category_id, 'PCS', FALSE,
                    TRUE, TRUE, 10,
                    :sale_price, TRUE, now(), now()
                )
            RETURNING id
            """
        ),
        {
            "sku": sku,
            "name": name,
            "quick_name": quick_name,
            "category_id": int(category_id),
            "sale_price": sale_price,
        },
    ).scalar_one()

    s.execute(
        text(
            """
            INSERT INTO inventory_balance
                (branch_id, product_id, on_hand, reserved, created_at, updated_at)
            VALUES
                (:branch_id, :product_id, 100.000, 0.000, now(), now())
            """
        ),
        {"branch_id": int(branch_id), "product_id": int(product_id)},
    )
    s.commit()
    return int(product_id)


def create_order(
    client: TestClient,
    *,
    branch_id: int,
    user_id: int,
    product_id: int,
    qty: str,
    customer_name: str,
    requested_for_at: str | None,
) -> int:
    resp = client.post(
        "/pos/orders",
        json={
            "branch_id": branch_id,
            "customer_name": customer_name,
            "requested_for_at": requested_for_at,
            "items": [{"product_id": product_id, "qty": qty}],
        },
        headers=auth_headers(user_id),
    )
    assert resp.status_code == 200, resp.text
    return int(resp.json()["id"])


@pytest.mark.skipif(
    not os.getenv("DATABASE_URL"),
    reason="DATABASE_URL not set; skipping POS order queue tests",
)
def test_order_queue_groups_active_statuses_and_counts():
    alembic_upgrade_head()

    s: Session = SessionLocal()
    try:
        reset_db(s)

        admin_role_id = seed_role(s, "ADMIN", "Administrator")
        cashier_role_id = seed_role(s, "CASHIER", "Cashier")
        baker_role_id = seed_role(s, "BAKER", "Baker")

        branch_id = seed_branch(s, "MAIN", "Main Branch")

        admin_user_id = seed_user(
            s,
            branch_id=branch_id,
            role_id=admin_role_id,
            email="admin@example.com",
            full_name="Admin User",
        )
        cashier_user_id = seed_user(
            s,
            branch_id=branch_id,
            role_id=cashier_role_id,
            email="cashier@example.com",
            full_name="Cashier User",
        )
        baker_user_id = seed_user(
            s,
            branch_id=branch_id,
            role_id=baker_role_id,
            email="baker@example.com",
            full_name="Baker User",
        )

        category_id = seed_category(
            s,
            code="BREAD",
            name="Bread",
            quick_name="Bread",
        )
        product_id = seed_product(
            s,
            category_id=category_id,
            branch_id=branch_id,
            sku="BREAD-BOL",
            name="Bolillo",
            quick_name="Bolillo",
            sale_price=Decimal("8.00"),
        )
    finally:
        s.close()

    app = create_app()
    client = TestClient(app)

    now_utc = datetime.now(timezone.utc)

    created_order_id = create_order(
        client,
        branch_id=branch_id,
        user_id=cashier_user_id,
        product_id=product_id,
        qty="2.000",
        customer_name="Created Order",
        requested_for_at=(now_utc + timedelta(hours=3)).isoformat(),
    )

    sent_order_id = create_order(
        client,
        branch_id=branch_id,
        user_id=cashier_user_id,
        product_id=product_id,
        qty="3.000",
        customer_name="Sent Order",
        requested_for_at=(now_utc - timedelta(hours=2)).isoformat(),
    )

    ready_order_id = create_order(
        client,
        branch_id=branch_id,
        user_id=cashier_user_id,
        product_id=product_id,
        qty="1.000",
        customer_name="Ready Order",
        requested_for_at=None,
    )

    cancel_order_id = create_order(
        client,
        branch_id=branch_id,
        user_id=cashier_user_id,
        product_id=product_id,
        qty="1.000",
        customer_name="Canceled Order",
        requested_for_at=(now_utc + timedelta(days=1)).isoformat(),
    )

    client.post(
        f"/pos/orders/{sent_order_id}/send-to-bakery",
        headers=auth_headers(admin_user_id),
    )
    client.post(
        f"/pos/orders/{ready_order_id}/send-to-bakery",
        headers=auth_headers(admin_user_id),
    )
    client.post(
        f"/pos/orders/{ready_order_id}/ready",
        headers=auth_headers(baker_user_id),
    )
    client.post(
        f"/pos/orders/{cancel_order_id}/cancel",
        headers=auth_headers(cashier_user_id),
    )

    resp = client.get(
        "/pos/orders/queue",
        params={"branch_id": branch_id},
        headers=auth_headers(admin_user_id),
    )
    assert resp.status_code == 200, resp.text
    payload = resp.json()

    assert payload["branch_id"] == branch_id
    assert payload["generated_at"] is not None

    counts = payload["counts"]
    assert counts["created"] == 1
    assert counts["sent_to_bakery"] == 1
    assert counts["ready"] == 1
    assert counts["delivered"] == 0
    assert counts["canceled"] == 1
    assert counts["active_total"] == 3

    assert len(payload["pending_intake"]) == 1
    assert len(payload["bakery_work"]) == 1
    assert len(payload["ready_for_pickup"]) == 1

    pending = payload["pending_intake"][0]
    assert pending["id"] == created_order_id
    assert pending["status"] == "CREATED"
    assert pending["customer_name"] == "Created Order"
    assert pending["due_bucket"] in {"TODAY", "FUTURE"}
    assert pending["lines_count"] == 1
    assert Decimal(pending["total_units"]) == Decimal("2.000")
    assert len(pending["items_preview"]) == 1
    assert pending["items_preview"][0]["sku"] == "BREAD-BOL"

    bakery = payload["bakery_work"][0]
    assert bakery["id"] == sent_order_id
    assert bakery["status"] == "SENT_TO_BAKERY"
    assert bakery["customer_name"] == "Sent Order"
    assert bakery["due_bucket"] == "OVERDUE"

    ready = payload["ready_for_pickup"][0]
    assert ready["id"] == ready_order_id
    assert ready["status"] == "READY"
    assert ready["customer_name"] == "Ready Order"
    assert ready["due_bucket"] == "UNSCHEDULED"


@pytest.mark.skipif(
    not os.getenv("DATABASE_URL"),
    reason="DATABASE_URL not set; skipping POS order queue tests",
)
def test_order_queue_respects_branch_scope():
    alembic_upgrade_head()

    s: Session = SessionLocal()
    try:
        reset_db(s)

        admin_role_id = seed_role(s, "ADMIN", "Administrator")
        cashier_role_id = seed_role(s, "CASHIER", "Cashier")

        branch_1_id = seed_branch(s, "MAIN", "Main Branch")
        branch_2_id = seed_branch(s, "AUX", "Aux Branch")

        admin_user_id = seed_user(
            s,
            branch_id=branch_1_id,
            role_id=admin_role_id,
            email="admin@example.com",
            full_name="Admin User",
        )
        other_branch_cashier_id = seed_user(
            s,
            branch_id=branch_2_id,
            role_id=cashier_role_id,
            email="cashier.other@example.com",
            full_name="Other Branch Cashier",
        )

        category_id = seed_category(
            s,
            code="BREAD",
            name="Bread",
            quick_name="Bread",
        )
        product_id = seed_product(
            s,
            category_id=category_id,
            branch_id=branch_1_id,
            sku="BREAD-BOL",
            name="Bolillo",
            quick_name="Bolillo",
            sale_price=Decimal("8.00"),
        )
    finally:
        s.close()

    app = create_app()
    client = TestClient(app)

    _order_id = create_order(
        client,
        branch_id=branch_1_id,
        user_id=admin_user_id,
        product_id=product_id,
        qty="2.000",
        customer_name="Main Branch Order",
        requested_for_at=None,
    )

    resp = client.get(
        "/pos/orders/queue",
        params={"branch_id": branch_1_id},
        headers=auth_headers(other_branch_cashier_id),
    )
    assert resp.status_code == 403, resp.text
