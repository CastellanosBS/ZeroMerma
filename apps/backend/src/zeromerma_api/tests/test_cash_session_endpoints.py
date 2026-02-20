from __future__ import annotations

import os

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from zeromerma_api.db.engine import SessionLocal
from zeromerma_api.main import create_app
from zeromerma_api.models.branch import Branch
from zeromerma_api.models.role import Role
from zeromerma_api.models.user_account import UserAccount


def _alembic_upgrade_head() -> None:
    cfg = Config("alembic.ini")
    command.upgrade(cfg, "head")


@pytest.mark.skipif(
    not os.getenv("DATABASE_URL"), reason="DATABASE_URL not set; skipping POS tests"
)
def test_cash_session_open_close_flow():
    _alembic_upgrade_head()

    app = create_app()
    client = TestClient(app)

    s: Session = SessionLocal()
    try:
        # Ensure minimal admin core data exists
        b = s.scalar(select(Branch).where(Branch.code == "MAIN"))
        if b is None:
            b = Branch(code="MAIN", name="Main Branch")
            s.add(b)
            s.flush()

        r = s.scalar(select(Role).where(Role.code == "ADMIN"))
        if r is None:
            r = Role(code="ADMIN", name="Admin")
            s.add(r)
            s.flush()

        u = s.scalar(
            select(UserAccount).where(UserAccount.email == "admin@example.com")
        )
        if u is None:
            u = UserAccount(
                branch_id=b.id,
                role_id=r.id,
                email="admin@example.com",
                full_name="Admin User",
                password_hash=None,
                is_active=True,
            )
            s.add(u)
            s.flush()

        s.commit()
        branch_id = b.id
        user_id = u.id
    finally:
        s.close()

    # Open
    resp = client.post(
        "/pos/cash-sessions/open",
        json={
            "branch_id": branch_id,
            "opened_by_id": user_id,
            "opening_amount": 100.00,
        },
    )
    assert resp.status_code == 200, resp.text
    opened = resp.json()
    session_id = opened["id"]
    assert opened["status"] == "OPEN"

    # Open again should fail
    resp2 = client.post(
        "/pos/cash-sessions/open",
        json={"branch_id": branch_id, "opened_by_id": user_id, "opening_amount": 50.00},
    )
    assert resp2.status_code == 409, resp2.text

    # Current should return the open session
    resp3 = client.get("/pos/cash-sessions/current", params={"branch_id": branch_id})
    assert resp3.status_code == 200
    current = resp3.json()
    assert current["id"] == session_id
    assert current["status"] == "OPEN"

    # Close
    resp4 = client.post(
        f"/pos/cash-sessions/{session_id}/close",
        json={"closed_by_id": user_id, "closing_amount": 150.00},
    )
    assert resp4.status_code == 200, resp4.text
    closed = resp4.json()
    assert closed["status"] == "CLOSED"
    assert closed["closed_by_id"] == user_id

    # Now open again should succeed
    resp5 = client.post(
        "/pos/cash-sessions/open",
        json={"branch_id": branch_id, "opened_by_id": user_id, "opening_amount": 0.00},
    )
    assert resp5.status_code == 200, resp5.text
    assert resp5.json()["status"] == "OPEN"
