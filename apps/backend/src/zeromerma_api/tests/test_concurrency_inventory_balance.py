from __future__ import annotations

import os
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

# We ONLY depend on these, because you've already used them in your probes/scripts.
from zeromerma_api.db.engine import SessionLocal

# App import that works regardless of whether you expose create_app() or app
try:
    from zeromerma_api.main import create_app  # type: ignore
except Exception:  # pragma: no cover
    create_app = None  # type: ignore

try:
    from zeromerma_api.main import app as fastapi_app  # type: ignore
except Exception:  # pragma: no cover
    fastapi_app = None  # type: ignore


def get_app():
    """
    Compatibility:
    - If you have create_app(), use it.
    - Else fall back to `app`.
    """
    if create_app is not None:
        return create_app()
    if fastapi_app is not None:
        return fastapi_app
    raise RuntimeError(
        "Could not import FastAPI app. Expected create_app() or app in zeromerma_api.main"
    )


def reset_tables() -> None:
    """
    Deterministic state: TRUNCATE all relevant tables.
    Order doesn't matter much with CASCADE, but we keep it explicit.
    """
    with SessionLocal() as s:
        s.execute(text("TRUNCATE TABLE payment RESTART IDENTITY CASCADE;"))
        s.execute(text("TRUNCATE TABLE sale_item RESTART IDENTITY CASCADE;"))
        s.execute(text("TRUNCATE TABLE sale RESTART IDENTITY CASCADE;"))
        s.execute(text("TRUNCATE TABLE cash_session RESTART IDENTITY CASCADE;"))
        s.execute(text("TRUNCATE TABLE inventory_movement RESTART IDENTITY CASCADE;"))
        s.execute(text("TRUNCATE TABLE inventory_balance RESTART IDENTITY CASCADE;"))
        s.execute(text("TRUNCATE TABLE product RESTART IDENTITY CASCADE;"))
        s.execute(text("TRUNCATE TABLE user_account RESTART IDENTITY CASCADE;"))
        s.execute(text("TRUNCATE TABLE role RESTART IDENTITY CASCADE;"))
        s.execute(text("TRUNCATE TABLE branch RESTART IDENTITY CASCADE;"))
        s.commit()


def seed_base_state() -> dict[str, int]:
    """
    Seed minimal required entities using raw SQL with RETURNING:
    - branch
    - role
    - user_account
    - product
    - cash_session (OPEN)
    - inventory_balance (on_hand=1)

    Returns IDs for later use.
    """
    with SessionLocal() as s:
        branch_id = s.execute(
            text(
                """
                INSERT INTO branch (code, name, is_active, created_at, updated_at)
                VALUES ('MAIN', 'Main Branch', true, now(), now())
                RETURNING id
                """
            )
        ).scalar_one()

        role_id = s.execute(
            text(
                """
                INSERT INTO role (code, name, created_at, updated_at)
                VALUES ('ADMIN', 'Admin', now(), now())
                RETURNING id
                """
            )
        ).scalar_one()

        user_id = s.execute(
            text(
                """
                INSERT INTO user_account (branch_id, role_id, email, full_name, password_hash, is_active, created_at, updated_at)
                VALUES (:branch_id, :role_id, 'admin@example.com', 'Admin User', NULL, true, now(), now())
                RETURNING id
                """
            ),
            {"branch_id": branch_id, "role_id": role_id},
        ).scalar_one()

        product_id = s.execute(
            text(
                """
                INSERT INTO product (sku, name, is_active, created_at, updated_at)
                VALUES ('SKU-001', 'Test Product', true, now(), now())
                RETURNING id
                """
            )
        ).scalar_one()

        cash_session_id = s.execute(
            text(
                """
                INSERT INTO cash_session
                  (branch_id, opened_by_id, opened_at, opening_amount, status, created_at, updated_at)
                VALUES
                  (:branch_id, :opened_by_id, now(), 0, 'OPEN', now(), now())
                RETURNING id
                """
            ),
            {"branch_id": branch_id, "opened_by_id": user_id},
        ).scalar_one()

        # Snapshot row: THIS is the operational truth (atomic decrement uses this)
        s.execute(
            text(
                """
                INSERT INTO inventory_balance (branch_id, product_id, on_hand, reserved, created_at, updated_at)
                VALUES (:branch_id, :product_id, 1.000, 0.000, now(), now())
                """
            ),
            {"branch_id": branch_id, "product_id": product_id},
        )

        # Optional: seed ledger too (audit). Not required for atomic decrement, but useful consistency check.
        s.execute(
            text(
                """
                INSERT INTO inventory_movement
                  (branch_id, product_id, qty, reason, ref_type, ref_id, note, created_by_id, created_at, updated_at)
                VALUES
                  (:branch_id, :product_id, 1.000, 'OPENING_BALANCE', NULL, NULL, 'seed', :user_id, now(), now())
                """
            ),
            {"branch_id": branch_id, "product_id": product_id, "user_id": user_id},
        )

        s.commit()

        return {
            "branch_id": int(branch_id),
            "user_id": int(user_id),
            "product_id": int(product_id),
            "cash_session_id": int(cash_session_id),
        }


def snapshot_on_hand(branch_id: int, product_id: int) -> float:
    with SessionLocal() as s:
        val = s.execute(
            text(
                """
                SELECT COALESCE(on_hand, 0)
                FROM inventory_balance
                WHERE branch_id = :b AND product_id = :p
                """
            ),
            {"b": branch_id, "p": product_id},
        ).scalar_one_or_none()
        return float(val or 0)


@pytest.mark.skipif(
    not os.getenv("DATABASE_URL"),
    reason="DATABASE_URL not set; skipping concurrency tests",
)
def test_concurrent_sales_do_not_oversell_inventory_balance():
    """
    Stock=1 in inventory_balance.
    Run N concurrent sale attempts of qty=1.
    Expect exactly one 200 and N-1 conflicts (409).
    """

    reset_tables()
    ids = seed_base_state()

    app = get_app()

    workers = 8
    barrier = threading.Barrier(workers)

    def worker_attempt_sale() -> int:
        """
        Each thread uses its own TestClient (avoid shared-client thread-safety issues).
        """
        client = TestClient(app)
        barrier.wait()

        resp = client.post(
            "/pos/sales",
            json={
                "branch_id": ids["branch_id"],
                "cash_session_id": ids["cash_session_id"],
                "created_by_id": ids["user_id"],
                "items": [
                    {"product_id": ids["product_id"], "qty": 1.0, "unit_price": 10.00}
                ],
            },
        )
        return resp.status_code

    statuses: list[int] = []
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futures = [ex.submit(worker_attempt_sale) for _ in range(workers)]
        for f in as_completed(futures):
            statuses.append(f.result())

    ok = sum(1 for s in statuses if s == 200)
    conflict = sum(1 for s in statuses if s == 409)

    assert ok == 1, f"Expected exactly 1 success (200). Got statuses={statuses}"
    assert (
        conflict == workers - 1
    ), f"Expected {workers-1} conflicts (409). Got statuses={statuses}"

    # DB truth: snapshot must be exactly 0.000 after one success
    assert abs(snapshot_on_hand(ids["branch_id"], ids["product_id"]) - 0.0) < 1e-9
