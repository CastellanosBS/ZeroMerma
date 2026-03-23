# apps/backend/src/zeromerma_api/tests/test_pricing_endpoints.py
# PURPOSE:
#   Validate Pricing Policy endpoints:
#     - list effective prices
#     - admin can upsert/delete override
#     - effective_price resolves override -> base fallback

from __future__ import annotations

import os
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from zeromerma_api.core.security import create_access_token
from zeromerma_api.db.engine import SessionLocal
from zeromerma_api.main import create_app


def make_alembic_config() -> Config:
    backend_dir = Path(__file__).resolve().parents[3]
    cfg = Config(str(backend_dir / "alembic.ini"))
    cfg.set_main_option("script_location", str(backend_dir / "migrations"))
    if os.getenv("DATABASE_URL"):
        cfg.set_main_option("sqlalchemy.url", os.environ["DATABASE_URL"])
    return cfg


def alembic_upgrade_head() -> None:
    command.upgrade(make_alembic_config(), "head")


def auth_headers(*, user_id: int, role_code: str, branch_id: int) -> dict[str, str]:
    token = create_access_token(
        subject=str(int(user_id)),
        extra_claims={"role_code": str(role_code), "branch_id": int(branch_id)},
    )
    return {"Authorization": f"Bearer {token}"}


def reset_db(s: Session) -> None:
    s.execute(
        text(
            """
            TRUNCATE TABLE
                product_price,
                production_run,
                payment,
                sale_item,
                sale,
                inventory_movement,
                inventory_balance,
                cash_session,
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


@pytest.mark.skipif(
    not os.getenv("DATABASE_URL"), reason="DATABASE_URL not set; skipping pricing tests"
)
def test_pricing_override_and_effective_resolution():
    alembic_upgrade_head()

    s: Session = SessionLocal()
    try:
        reset_db(s)

        branch_id = s.execute(
            text(
                "INSERT INTO branch (code, name, is_active, created_at, updated_at) VALUES ('MAIN','Main',TRUE,now(),now()) RETURNING id"
            )
        ).scalar_one()

        role_id = s.execute(
            text(
                "INSERT INTO role (code, name, created_at, updated_at) VALUES ('ADMIN','Admin',now(),now()) RETURNING id"
            )
        ).scalar_one()

        user_id = s.execute(
            text(
                """
                INSERT INTO user_account (branch_id, role_id, email, full_name, password_hash, is_active, created_at, updated_at)
                VALUES (:b, :r, 'admin@example.com', 'Admin', NULL, TRUE, now(), now())
                RETURNING id
                """
            ),
            {"b": int(branch_id), "r": int(role_id)},
        ).scalar_one()

        cat_id = s.execute(
            text(
                "INSERT INTO product_category (code, name, is_active, created_at, updated_at) VALUES ('FIN','Finished',TRUE,now(),now()) RETURNING id"
            )
        ).scalar_one()

        # Base price = 50.00
        product_id = s.execute(
            text(
                """
                INSERT INTO product (sku, name, category_id, is_input, sale_price, is_active, created_at, updated_at)
                VALUES ('DONUT','Donut',:c,FALSE,50.00,TRUE,now(),now())
                RETURNING id
                """
            ),
            {"c": int(cat_id)},
        ).scalar_one()

        s.commit()
        branch_id = int(branch_id)
        user_id = int(user_id)
        product_id = int(product_id)
    finally:
        s.close()

    app = create_app()
    client = TestClient(app)
    h = auth_headers(user_id=user_id, role_code="ADMIN", branch_id=branch_id)

    # Effective list (no override) => effective == base
    r0 = client.get(f"/pricing/branches/{branch_id}/products", headers=h)
    assert r0.status_code == 200, r0.text
    row = next(x for x in r0.json() if x["product_id"] == product_id)
    assert float(row["base_price"]) == pytest.approx(50.0)
    assert row["override_price"] is None
    assert float(row["effective_price"]) == pytest.approx(50.0)

    # Upsert override => effective == override
    r1 = client.put(
        f"/pricing/branches/{branch_id}/products/{product_id}",
        json={"price": 60.0, "currency": "MXN"},
        headers=h,
    )
    assert r1.status_code == 200, r1.text

    r2 = client.get(f"/pricing/branches/{branch_id}/products/{product_id}", headers=h)
    assert r2.status_code == 200, r2.text
    assert float(r2.json()["override_price"]) == pytest.approx(60.0)
    assert float(r2.json()["effective_price"]) == pytest.approx(60.0)

    # Delete override => fallback to base
    r3 = client.delete(f"/pricing/branches/{branch_id}/products/{product_id}", headers=h)
    assert r3.status_code == 200, r3.text
    assert r3.json()["deleted"] is True

    r4 = client.get(f"/pricing/branches/{branch_id}/products/{product_id}", headers=h)
    assert r4.status_code == 200, r4.text
    assert r4.json()["override_price"] is None
    assert float(r4.json()["effective_price"]) == pytest.approx(50.0)
