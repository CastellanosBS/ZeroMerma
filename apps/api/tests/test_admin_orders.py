from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from fastapi.testclient import TestClient
from order_fixtures import seed_order_stock
from sqlalchemy import select

from zeromerma_api.bootstrap.seed_local import (
    SEED_PRODUCT_BOLILLO_STD_CODE,
    SEED_PRODUCT_CAFE_AMERICANO_CODE,
    SEED_USER_EMAIL,
    SEED_USER_PASSWORD,
    SEED_WORKSTATION_CODE,
)
from zeromerma_api.db.session import SessionLocal
from zeromerma_api.modules.audit.infrastructure.models import AuditLog
from zeromerma_api.modules.catalog.infrastructure.models import Product
from zeromerma_api.modules.outbox.infrastructure.models import OutboxEvent
from zeromerma_api.testing.authorization import owner_headers
from zeromerma_api.testing.idempotency import current_cash_session_id, new_idempotency_key
from zeromerma_api.testing.sessions import login_headers


def _login(client: TestClient, *, email: str, password: str) -> dict[str, str]:
    return login_headers(client, email=email, password=password, audience="POS")


def _admin_headers(client: TestClient) -> dict[str, str]:
    return owner_headers()


def _cashier_headers(client: TestClient) -> dict[str, str]:
    return _login(client, email=SEED_USER_EMAIL, password=SEED_USER_PASSWORD)


def _open_cash_session(client: TestClient) -> None:
    seed_order_stock()
    response = client.post(
        "/v1/cash-sessions/open",
        headers={**_cashier_headers(client), "Idempotency-Key": new_idempotency_key()},
        json={
            "workstation_code": SEED_WORKSTATION_CODE,
            "opening_amount": "200.00",
        },
    )
    assert response.status_code == 201


def _get_product_id(code: str) -> str:
    with SessionLocal() as session:
        product = session.execute(select(Product).where(Product.code == code)).scalar_one()
    return str(product.id)


def _create_order(
    client: TestClient,
    *,
    advance_amount: str = "0.00",
    advance_payment_method_code: str | None = None,
    customer_name: str = "Cliente Backoffice",
    requested_for_at: str | None = None,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "workstation_code": SEED_WORKSTATION_CODE,
        "customer_name": customer_name,
        "customer_phone": "6621234567",
        "requested_for_at": requested_for_at
        or (datetime.now(tz=UTC) + timedelta(days=2)).isoformat(),
        "notes": "Pedido para backoffice",
        "items": [
            {"product_id": _get_product_id(SEED_PRODUCT_BOLILLO_STD_CODE), "quantity": "4"},
            {"product_id": _get_product_id(SEED_PRODUCT_CAFE_AMERICANO_CODE), "quantity": "1"},
        ],
        "advance_amount": advance_amount,
    }
    if advance_payment_method_code is not None:
        payload["advance_payment_method_code"] = advance_payment_method_code
    command_headers = _cashier_headers(client)
    cash_session_id = current_cash_session_id(
        client, headers=command_headers, workstation_code=SEED_WORKSTATION_CODE
    )
    response = client.post(
        "/v1/orders",
        headers={**command_headers, "Idempotency-Key": new_idempotency_key()},
        json={**payload, "cash_session_id": cash_session_id},
    )
    assert response.status_code == 201
    return response.json()


def test_admin_orders_list_filters_and_metrics_use_real_orders(client: TestClient) -> None:
    _open_cash_session(client)
    order = _create_order(
        client,
        advance_amount="10.00",
        advance_payment_method_code="CASH",
        customer_name="Cliente Consulta Admin",
    )

    response = client.get(
        "/v1/admin/orders",
        params={
            "search": "Consulta Admin",
            "status": "PENDING",
            "payment_state": "PARTIAL_DEPOSIT",
        },
        headers=_admin_headers(client),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["items"][0]["id"] == order["id"]
    assert payload["items"][0]["payment_state"] == "PARTIAL_DEPOSIT"
    assert Decimal(str(payload["metrics"]["deposits_received_amount"])) == Decimal("10.00")
    assert payload["filter_options"]["branches"]
    assert payload["filter_options"]["statuses"]


def test_admin_order_detail_includes_lines_payments_timeline_and_actions(
    client: TestClient,
) -> None:
    _open_cash_session(client)
    order = _create_order(
        client,
        advance_amount="10.00",
        advance_payment_method_code="CARD",
        customer_name="Cliente Detalle Admin",
    )

    response = client.get(f"/v1/admin/orders/{order['id']}", headers=_admin_headers(client))

    assert response.status_code == 200
    payload = response.json()
    assert payload["overview"]["folio"] == order["folio"]
    assert payload["customer"]["name"] == "Cliente Detalle Admin"
    assert len(payload["lines"]) == 2
    assert payload["payments"][0]["payment_type"] == "ADVANCE"
    assert payload["timeline"][0]["key"] == "created"
    assert payload["available_actions"]["can_mark_ready"] is True
    assert payload["available_actions"]["can_capture_balance"] is False


def test_admin_order_can_mark_ready_and_deliver_when_paid_without_mutating_pos_flow(
    client: TestClient,
) -> None:
    _open_cash_session(client)
    order = _create_order(
        client,
        advance_amount="34.00",
        advance_payment_method_code="CASH",
        customer_name="Cliente Pagado Admin",
    )

    ready_response = client.post(
        f"/v1/admin/orders/{order['id']}/mark-ready",
        headers={
            "Idempotency-Key": new_idempotency_key(),
            **_admin_headers(client),
            "X-Request-ID": "d08a9ce4-78e2-5240-94db-db68e14e4b47",
        },
        json={},
    )
    assert ready_response.status_code == 200
    assert ready_response.json()["status"] == "READY"

    deliver_response = client.post(
        f"/v1/admin/orders/{order['id']}/deliver",
        headers={
            "Idempotency-Key": new_idempotency_key(),
            **_admin_headers(client),
            "X-Request-ID": "f4ab3402-0115-50ce-80a5-649b3a29727b",
        },
        json={},
    )

    assert deliver_response.status_code == 200
    assert deliver_response.json()["status"] == "DELIVERED"

    with SessionLocal() as session:
        audit_actions = [
            record.action
            for record in session.execute(
                select(AuditLog).where(AuditLog.resource_id == str(order["id"]))
            ).scalars()
        ]
        outbox_events = [
            record.event_name
            for record in session.execute(
                select(OutboxEvent).where(OutboxEvent.aggregate_id == str(order["id"]))
            ).scalars()
        ]

    assert "order.ready" in audit_actions
    assert "order.delivered" in audit_actions
    assert "order.ready.v1" in outbox_events
    assert "order.delivered.v1" in outbox_events


def test_admin_order_blocks_financial_actions_and_cancels_non_refundable_order(
    client: TestClient,
) -> None:
    _open_cash_session(client)
    balance_order = _create_order(
        client,
        advance_amount="5.00",
        advance_payment_method_code="CASH",
        customer_name="Cliente Saldo Admin",
    )
    ready_response = client.post(
        f"/v1/admin/orders/{balance_order['id']}/mark-ready",
        headers={**_admin_headers(client), "Idempotency-Key": new_idempotency_key()},
        json={},
    )
    assert ready_response.status_code == 200

    deliver_response = client.post(
        f"/v1/admin/orders/{balance_order['id']}/deliver",
        headers={**_admin_headers(client), "Idempotency-Key": new_idempotency_key()},
        json={},
    )
    assert deliver_response.status_code == 409
    assert "saldo pendiente" in deliver_response.json()["message"]

    refundable_cancel_response = client.post(
        f"/v1/admin/orders/{balance_order['id']}/cancel",
        headers={**_admin_headers(client), "Idempotency-Key": new_idempotency_key()},
        json={},
    )
    assert refundable_cancel_response.status_code == 409
    assert "reembolso" in refundable_cancel_response.json()["message"]

    non_refundable_order = _create_order(
        client,
        advance_amount="5.00",
        advance_payment_method_code="CARD",
        customer_name="Cliente Cancelacion Admin",
        requested_for_at=(datetime.now(tz=UTC) + timedelta(hours=8)).isoformat(),
    )
    cancel_response = client.post(
        f"/v1/admin/orders/{non_refundable_order['id']}/cancel",
        headers={
            "Idempotency-Key": new_idempotency_key(),
            **_admin_headers(client),
            "X-Request-ID": "367e3602-8f8c-57a5-a3a8-d80c98398241",
        },
        json={},
    )

    assert cancel_response.status_code == 200
    payload = cancel_response.json()
    assert payload["status"] == "CANCELED"
    assert Decimal(str(payload["advance_amount"])) == Decimal("5.00")
    assert Decimal(str(payload["remaining_balance_amount"])) == Decimal("0.00")
