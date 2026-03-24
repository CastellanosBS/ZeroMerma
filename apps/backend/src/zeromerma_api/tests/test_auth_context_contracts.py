from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from zeromerma_api.core.security import create_access_token
from zeromerma_api.db.engine import SessionLocal
from zeromerma_api.main import create_app
from zeromerma_api.tests.alembic_utils import alembic_upgrade_head
from zeromerma_api.tests.auth_helpers import build_auth_headers


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
                (
                    branch_id,
                    role_id,
                    email,
                    full_name,
                    password_hash,
                    is_active,
                    created_at,
                    updated_at
                )
            VALUES
                (
                    :branch_id,
                    :role_id,
                    :email,
                    :full_name,
                    NULL,
                    TRUE,
                    now(),
                    now()
                )
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


@pytest.mark.skipif(
    not os.getenv("DATABASE_URL"),
    reason="DATABASE_URL not set; skipping auth context contract tests",
)
def test_claimful_token_can_access_pos_route():
    alembic_upgrade_head()

    s: Session = SessionLocal()
    try:
        reset_db(s)
        cashier_role_id = seed_role(s, "CASHIER", "Cashier")
        branch_id = seed_branch(s, "MAIN", "Main Branch")
        cashier_user_id = seed_user(
            s,
            branch_id=branch_id,
            role_id=cashier_role_id,
            email="cashier@example.com",
            full_name="Cashier User",
        )
    finally:
        s.close()

    client = TestClient(create_app())

    resp = client.get(
        f"/pos/orders/queue?branch_id={branch_id}",
        headers=build_auth_headers(
            user_id=cashier_user_id,
            role_code="CASHIER",
            branch_id=branch_id,
        ),
    )
    assert resp.status_code == 200, resp.text

    payload = resp.json()
    assert payload["branch_id"] == branch_id
    assert payload["counts"]["active_total"] == 0
    assert payload["pending_intake"] == []
    assert payload["bakery_work"] == []
    assert payload["ready_for_pickup"] == []


@pytest.mark.skipif(
    not os.getenv("DATABASE_URL"),
    reason="DATABASE_URL not set; skipping auth context contract tests",
)
def test_subject_only_token_remains_backward_compatible():
    alembic_upgrade_head()

    s: Session = SessionLocal()
    try:
        reset_db(s)
        cashier_role_id = seed_role(s, "CASHIER", "Cashier")
        branch_id = seed_branch(s, "MAIN", "Main Branch")
        cashier_user_id = seed_user(
            s,
            branch_id=branch_id,
            role_id=cashier_role_id,
            email="cashier@example.com",
            full_name="Cashier User",
        )
    finally:
        s.close()

    client = TestClient(create_app())

    legacy_token = create_access_token(subject=str(cashier_user_id))
    resp = client.get(
        f"/pos/orders/queue?branch_id={branch_id}",
        headers={"Authorization": f"Bearer {legacy_token}"},
    )
    assert resp.status_code == 200, resp.text

    payload = resp.json()
    assert payload["branch_id"] == branch_id
    assert payload["counts"]["active_total"] == 0


@pytest.mark.skipif(
    not os.getenv("DATABASE_URL"),
    reason="DATABASE_URL not set; skipping auth context contract tests",
)
def test_invalid_branch_claim_is_rejected_as_malformed_token():
    alembic_upgrade_head()

    s: Session = SessionLocal()
    try:
        reset_db(s)
        cashier_role_id = seed_role(s, "CASHIER", "Cashier")
        branch_id = seed_branch(s, "MAIN", "Main Branch")
        cashier_user_id = seed_user(
            s,
            branch_id=branch_id,
            role_id=cashier_role_id,
            email="cashier@example.com",
            full_name="Cashier User",
        )
    finally:
        s.close()

    client = TestClient(create_app())

    malformed_token = create_access_token(
        subject=str(cashier_user_id),
        extra_claims={"role_code": "CASHIER", "branch_id": "not-a-number"},
    )

    resp = client.get(
        f"/pos/orders/queue?branch_id={branch_id}",
        headers={"Authorization": f"Bearer {malformed_token}"},
    )
    assert resp.status_code == 401, resp.text

    payload = resp.json()
    assert payload["error"]["code"] == "UNAUTHORIZED"
    assert payload["error"]["message"] == "Invalid token branch_id claim."
