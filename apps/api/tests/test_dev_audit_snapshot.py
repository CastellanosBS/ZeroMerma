from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import select

from zeromerma_api.bootstrap.seed_local import (
    SEED_PRODUCT_CLASS_PAN_DULCE_CODE,
    SEED_USER_EMAIL,
    SEED_USER_PASSWORD,
    SEED_WORKSTATION_CODE,
)
from zeromerma_api.core.config import get_settings
from zeromerma_api.db.session import SessionLocal
from zeromerma_api.main import create_app
from zeromerma_api.modules.branches.infrastructure.models import Branch, Workstation
from zeromerma_api.modules.cash.infrastructure.models import CashSession
from zeromerma_api.modules.catalog.infrastructure.models import ProductClass
from zeromerma_api.modules.identity.infrastructure.models import User
from zeromerma_api.modules.sales.infrastructure.models import Sale

DEV_AUDIT_TOKEN = "change-me-dev-audit-token"


def _login(client: TestClient) -> str:
    response = client.post(
        "/v1/auth/login",
        json={"email": SEED_USER_EMAIL, "password": SEED_USER_PASSWORD},
    )
    assert response.status_code == 200
    return str(response.json()["access_token"])


def _authorization_header(client: TestClient) -> dict[str, str]:
    return {"Authorization": f"Bearer {_login(client)}"}


def _open_cash_session(client: TestClient, workstation_code: str = SEED_WORKSTATION_CODE) -> None:
    response = client.post(
        "/v1/cash-sessions/open",
        headers=_authorization_header(client),
        json={
            "workstation_code": workstation_code,
            "opening_amount": "150.00",
        },
    )
    assert response.status_code == 201


def _get_product_class_id(code: str) -> str:
    with SessionLocal() as session:
        product_class = session.execute(
            select(ProductClass).where(ProductClass.code == code)
        ).scalar_one()
    return str(product_class.id)


def _confirm_sale(client: TestClient) -> str:
    response = client.post(
        "/v1/sales/confirm",
        headers={
            **_authorization_header(client),
            "X-Request-ID": "dev-audit-sale-confirmation",
        },
        json={
            "workstation_code": SEED_WORKSTATION_CODE,
            "lines": [
                {
                    "capture_mode": "CLASS_CAPTURE",
                    "product_class_id": _get_product_class_id(SEED_PRODUCT_CLASS_PAN_DULCE_CODE),
                    "quantity": "2",
                }
            ],
            "payments": [
                {
                    "payment_method_code": "CASH",
                    "tendered_amount": "50.00",
                }
            ],
        },
    )
    assert response.status_code == 201
    return str(response.json()["id"])


@contextmanager
def _dev_audit_client(
    monkeypatch,
    *,
    enabled: bool,
    token: str | None = DEV_AUDIT_TOKEN,
) -> Iterator[TestClient]:
    monkeypatch.setenv(
        "ZEROMERMA_API_ENABLE_DEV_AUDIT_ENDPOINT",
        "true" if enabled else "false",
    )
    if token is None:
        monkeypatch.delenv("ZEROMERMA_API_DEV_AUDIT_TOKEN", raising=False)
    else:
        monkeypatch.setenv("ZEROMERMA_API_DEV_AUDIT_TOKEN", token)

    get_settings.cache_clear()
    try:
        with TestClient(create_app()) as client:
            yield client
    finally:
        get_settings.cache_clear()


def _audit_headers(token: str = DEV_AUDIT_TOKEN) -> dict[str, str]:
    return {"X-Audit-Token": token}


def _snapshot_table(payload: dict, table_name: str) -> dict:
    return next(table for table in payload["tables"] if table["table_name"] == table_name)


def _seed_cross_branch_sale() -> str:
    with SessionLocal() as session:
        north_branch = session.execute(select(Branch).where(Branch.code == "NORTE")).scalar_one()
        north_workstation = session.execute(
            select(Workstation).where(Workstation.code == "POS-NORTE-01")
        ).scalar_one()
        other_user = User(
            email="dev-audit-north@example.com",
            full_name="Dev Audit North Cashier",
            password_hash="dev-audit-password-hash",
            is_active=True,
        )
        session.add(other_user)
        session.flush()

        north_cash_session = CashSession(
            branch_id=north_branch.id,
            workstation_id=north_workstation.id,
            user_id=other_user.id,
            status="OPEN",
            opening_amount=Decimal("200.00"),
        )
        session.add(north_cash_session)
        session.flush()

        north_sale = Sale(
            branch_id=north_branch.id,
            workstation_id=north_workstation.id,
            cash_session_id=north_cash_session.id,
            operator_id=other_user.id,
            status="CONFIRMED",
            currency_code="MXN",
            subtotal_amount=Decimal("18.00"),
            total_amount=Decimal("18.00"),
            paid_amount=Decimal("18.00"),
            change_amount=Decimal("0.00"),
        )
        session.add(north_sale)
        session.commit()
        return str(north_sale.id)


def test_dev_audit_snapshot_returns_404_when_feature_is_disabled(monkeypatch) -> None:
    with _dev_audit_client(monkeypatch, enabled=False) as client:
        response = client.get("/dev/audit/snapshot", headers=_audit_headers())

    assert response.status_code == 404


def test_dev_audit_snapshot_rejects_missing_token(monkeypatch) -> None:
    with _dev_audit_client(monkeypatch, enabled=True) as client:
        response = client.get("/dev/audit/snapshot")

    assert response.status_code == 403


def test_dev_audit_snapshot_rejects_invalid_token(monkeypatch) -> None:
    with _dev_audit_client(monkeypatch, enabled=True) as client:
        response = client.get("/dev/audit/snapshot", headers=_audit_headers("wrong-token"))

    assert response.status_code == 403


def test_dev_audit_snapshot_returns_200_with_valid_token_when_enabled(monkeypatch) -> None:
    with _dev_audit_client(monkeypatch, enabled=True) as client:
        response = client.get("/dev/audit/snapshot", headers=_audit_headers())

    assert response.status_code == 200


def test_dev_audit_snapshot_returns_top_level_keys_with_valid_token(monkeypatch) -> None:
    with _dev_audit_client(monkeypatch, enabled=True) as client:
        response = client.get(
            "/dev/audit/snapshot?workstation_code=POS-01",
            headers=_audit_headers(),
        )

    assert response.status_code == 200
    payload = response.json()
    assert {
        "generated_at",
        "environment",
        "snapshot_version",
        "database_overview",
        "filters_applied",
        "tables",
    }.issubset(payload.keys())
    assert payload["database_overview"]["total_tracked_tables"] == 19


def test_dev_audit_snapshot_reflects_newly_opened_cash_session(monkeypatch) -> None:
    with _dev_audit_client(monkeypatch, enabled=True) as client:
        before_response = client.get("/dev/audit/snapshot", headers=_audit_headers())
        assert before_response.status_code == 200
        before_payload = before_response.json()
        before_cash_sessions = _snapshot_table(before_payload, "cash_sessions")["row_count"]

        _open_cash_session(client)

        after_response = client.get(
            "/dev/audit/snapshot?workstation_code=POS-01",
            headers=_audit_headers(),
        )

    assert after_response.status_code == 200
    after_payload = after_response.json()
    cash_sessions_table = _snapshot_table(after_payload, "cash_sessions")
    assert cash_sessions_table["row_count"] == before_cash_sessions + 1
    assert cash_sessions_table["scoped_row_count"] == 1
    assert cash_sessions_table["recent_rows"][0]["workstation_code"] == "POS-01"
    assert cash_sessions_table["recent_rows"][0]["status"] == "OPEN"


def test_dev_audit_snapshot_reflects_confirmed_sale_after_opening_cash_session(monkeypatch) -> None:
    with _dev_audit_client(monkeypatch, enabled=True) as client:
        before_response = client.get(
            "/dev/audit/snapshot?workstation_code=POS-01",
            headers=_audit_headers(),
        )
        assert before_response.status_code == 200
        before_payload = before_response.json()
        before_sales = _snapshot_table(before_payload, "sales")["scoped_row_count"]

        _open_cash_session(client)
        sale_id = _confirm_sale(client)

        after_response = client.get(
            "/dev/audit/snapshot?workstation_code=POS-01",
            headers=_audit_headers(),
        )

    assert after_response.status_code == 200
    after_payload = after_response.json()

    sales_table = _snapshot_table(after_payload, "sales")
    assert sales_table["scoped_row_count"] == before_sales + 1
    assert any(row["id"] == sale_id for row in sales_table["recent_rows"])


def test_dev_audit_snapshot_reflects_audit_log_and_outbox_after_critical_operations(
    monkeypatch,
) -> None:
    with _dev_audit_client(monkeypatch, enabled=True) as client:
        before_response = client.get(
            "/dev/audit/snapshot?workstation_code=POS-01",
            headers=_audit_headers(),
        )
        assert before_response.status_code == 200
        before_payload = before_response.json()
        before_audit = _snapshot_table(before_payload, "audit_log")["row_count"]
        before_outbox = _snapshot_table(before_payload, "outbox_events")["row_count"]

        _open_cash_session(client)
        _confirm_sale(client)

        after_response = client.get(
            "/dev/audit/snapshot?workstation_code=POS-01",
            headers=_audit_headers(),
        )

    assert after_response.status_code == 200
    after_payload = after_response.json()

    audit_log_table = _snapshot_table(after_payload, "audit_log")
    assert audit_log_table["row_count"] >= before_audit + 2
    assert any(row["action"] == "cash_session.opened" for row in audit_log_table["recent_rows"])
    assert any(row["action"] == "sale.confirmed" for row in audit_log_table["recent_rows"])

    outbox_table = _snapshot_table(after_payload, "outbox_events")
    assert outbox_table["row_count"] >= before_outbox + 2
    assert any(row["event_name"] == "cash.session.opened.v1" for row in outbox_table["recent_rows"])
    assert any(row["event_name"] == "sale.confirmed.v1" for row in outbox_table["recent_rows"])


def test_dev_audit_snapshot_scopes_sales_and_cash_sessions_by_workstation(monkeypatch) -> None:
    with _dev_audit_client(monkeypatch, enabled=True) as client:
        _open_cash_session(client, workstation_code="POS-01")
        _confirm_sale(client)
        _seed_cross_branch_sale()

        response = client.get(
            "/dev/audit/snapshot?workstation_code=POS-01",
            headers=_audit_headers(),
        )

    assert response.status_code == 200
    payload = response.json()
    sales_table = _snapshot_table(payload, "sales")
    cash_sessions_table = _snapshot_table(payload, "cash_sessions")
    assert sales_table["row_count"] >= 2
    assert sales_table["scoped_row_count"] == 1
    assert cash_sessions_table["row_count"] >= 2
    assert cash_sessions_table["scoped_row_count"] == 1


def test_dev_audit_snapshot_rejects_mismatched_branch_and_workstation_scope(monkeypatch) -> None:
    with _dev_audit_client(monkeypatch, enabled=True) as client:
        response = client.get(
            "/dev/audit/snapshot?branch_code=NORTE&workstation_code=POS-01",
            headers=_audit_headers(),
        )

    assert response.status_code == 400
