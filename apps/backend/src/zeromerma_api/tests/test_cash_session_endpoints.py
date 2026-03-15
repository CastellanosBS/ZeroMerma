# apps/backend/src/zeromerma_api/tests/test_cash_session_endpoints.py
from __future__ import annotations

import os
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from zeromerma_api.core.security import create_access_token
from zeromerma_api.db.engine import SessionLocal
from zeromerma_api.main import create_app
from zeromerma_api.models.branch import Branch
from zeromerma_api.models.role import Role
from zeromerma_api.models.user_account import UserAccount


def auth_headers(user_id: int) -> dict[str, str]:
    """
    Build Authorization headers for protected endpoints.

    We generate a JWT directly in tests so we don't depend on /auth/login.
    """
    token = create_access_token(subject=str(user_id))
    return {"Authorization": f"Bearer {token}"}


def make_alembic_config() -> Config:
    """
    Tests live at:
      .../apps/backend/src/zeromerma_api/tests/test_cash_session_endpoints.py

    So:
      parents[0]=tests
      parents[1]=zeromerma_api
      parents[2]=src
      parents[3]=backend ✅
    """
    backend_dir = Path(__file__).resolve().parents[3]
    cfg = Config(str(backend_dir / "alembic.ini"))
    cfg.set_main_option("script_location", str(backend_dir / "migrations"))

    # Optional but recommended: force URL for programmatic runs
    if os.getenv("DATABASE_URL"):
        cfg.set_main_option("sqlalchemy.url", os.environ["DATABASE_URL"])

    return cfg


def _alembic_upgrade_head() -> None:
    cfg = make_alembic_config()
    command.upgrade(cfg, "head")


def _close_open_cash_sessions_for_branch(branch_id: int, *, closed_by_id: int) -> None:
    """
    IMPORTANT:
      We do NOT delete cash_session rows because sales reference them (FK).
      Instead, we close any OPEN sessions so the test can open a new one.
    """
    with SessionLocal() as s:
        s.execute(
            text(
                """
                UPDATE cash_session
                SET status = 'CLOSED',
                    closed_by_id = :u,
                    closed_at = now(),
                    closing_amount = COALESCE(closing_amount, opening_amount, 0),
                    updated_at = now()
                WHERE branch_id = :b
                  AND status = 'OPEN'
                """
            ),
            {"b": branch_id, "u": closed_by_id},
        )
        s.commit()


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
        branch_id = int(b.id)
        user_id = int(u.id)
    finally:
        s.close()

    # Ensure test isolation: if there is an OPEN session already, close it (don't delete).
    _close_open_cash_sessions_for_branch(branch_id, closed_by_id=user_id)

    # Open
    resp = client.post(
        "/pos/cash-sessions/open",
        json={"branch_id": branch_id, "opening_amount": 100.00},
        headers=auth_headers(user_id),
    )
    assert resp.status_code == 200, resp.text
    opened = resp.json()
    session_id = opened["id"]
    assert opened["status"] == "OPEN"

    # Open again should fail
    resp2 = client.post(
        "/pos/cash-sessions/open",
        json={"branch_id": branch_id, "opening_amount": 50.00},
        headers=auth_headers(user_id),
    )
    assert resp2.status_code == 409, resp2.text

    # Current should return the open session (AUTH REQUIRED)
    resp3 = client.get(
        "/pos/cash-sessions/current",
        params={"branch_id": branch_id},
        headers=auth_headers(user_id),
    )
    assert resp3.status_code == 200, resp3.text
    current = resp3.json()
    assert current["id"] == session_id
    assert current["status"] == "OPEN"

    # Close
    resp4 = client.post(
        f"/pos/cash-sessions/{session_id}/close",
        json={"closing_amount": 150.00},
        headers=auth_headers(user_id),
    )
    assert resp4.status_code == 200, resp4.text
    closed = resp4.json()
    assert closed["status"] == "CLOSED"
    assert closed["closed_by_id"] == user_id

    # Now open again should succeed
    resp5 = client.post(
        "/pos/cash-sessions/open",
        json={"branch_id": branch_id, "opening_amount": 0.00},
        headers=auth_headers(user_id),
    )
    assert resp5.status_code == 200, resp5.text
    assert resp5.json()["status"] == "OPEN"
