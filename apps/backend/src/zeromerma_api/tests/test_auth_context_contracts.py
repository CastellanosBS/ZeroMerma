from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from zeromerma_api.core.security import create_access_token
from zeromerma_api.tests.auth_helpers import build_auth_headers
from zeromerma_api.tests.support.db import reset_pos_core_tables
from zeromerma_api.tests.support.seeders import (
    seed_branch,
    seed_role,
    seed_user,
)


def test_claimful_token_can_access_pos_route(
    db_session: Session,
    client: TestClient,
) -> None:
    reset_pos_core_tables(db_session)

    cashier_role_id = seed_role(db_session, code="CASHIER", name="Cashier")
    branch_id = seed_branch(db_session, code="MAIN", name="Main Branch")
    cashier_user_id = seed_user(
        db_session,
        branch_id=branch_id,
        role_id=cashier_role_id,
        email="cashier@example.com",
        full_name="Cashier User",
    )

    response = client.get(
        f"/pos/orders/queue?branch_id={branch_id}",
        headers=build_auth_headers(
            user_id=cashier_user_id,
            role_code="CASHIER",
            branch_id=branch_id,
        ),
    )
    assert response.status_code == 200, response.text

    payload = response.json()
    assert payload["branch_id"] == branch_id
    assert payload["counts"]["active_total"] == 0
    assert payload["pending_intake"] == []
    assert payload["bakery_work"] == []
    assert payload["ready_for_pickup"] == []


def test_subject_only_token_remains_backward_compatible(
    db_session: Session,
    client: TestClient,
) -> None:
    reset_pos_core_tables(db_session)

    cashier_role_id = seed_role(db_session, code="CASHIER", name="Cashier")
    branch_id = seed_branch(db_session, code="MAIN", name="Main Branch")
    cashier_user_id = seed_user(
        db_session,
        branch_id=branch_id,
        role_id=cashier_role_id,
        email="cashier@example.com",
        full_name="Cashier User",
    )

    legacy_token = create_access_token(subject=str(cashier_user_id))
    response = client.get(
        f"/pos/orders/queue?branch_id={branch_id}",
        headers={"Authorization": f"Bearer {legacy_token}"},
    )
    assert response.status_code == 200, response.text

    payload = response.json()
    assert payload["branch_id"] == branch_id
    assert payload["counts"]["active_total"] == 0


def test_invalid_branch_claim_is_rejected_as_malformed_token(
    db_session: Session,
    client: TestClient,
) -> None:
    reset_pos_core_tables(db_session)

    cashier_role_id = seed_role(db_session, code="CASHIER", name="Cashier")
    branch_id = seed_branch(db_session, code="MAIN", name="Main Branch")
    cashier_user_id = seed_user(
        db_session,
        branch_id=branch_id,
        role_id=cashier_role_id,
        email="cashier@example.com",
        full_name="Cashier User",
    )

    malformed_token = create_access_token(
        subject=str(cashier_user_id),
        extra_claims={"role_code": "CASHIER", "branch_id": "not-a-number"},
    )

    response = client.get(
        f"/pos/orders/queue?branch_id={branch_id}",
        headers={"Authorization": f"Bearer {malformed_token}"},
    )
    assert response.status_code == 401, response.text

    payload = response.json()
    assert payload["error"]["code"] == "UNAUTHORIZED"
    assert payload["error"]["message"] == "Invalid token branch_id claim."
