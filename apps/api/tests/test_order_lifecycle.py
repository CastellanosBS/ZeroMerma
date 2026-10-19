"""Approved commercial order policies, payments and terminal financial outcomes."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import patch
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from order_fixtures import order_clock, seed_order_stock
from sqlalchemy import func, select, update
from sqlalchemy.exc import DBAPIError

from zeromerma_api.bootstrap.seed_local import (
    SEED_PRODUCT_BOLILLO_STD_CODE,
    SEED_USER_EMAIL,
    SEED_USER_PASSWORD,
    SEED_WORKSTATION_CODE,
)
from zeromerma_api.db.session import SessionLocal
from zeromerma_api.modules.branches.infrastructure.models import Workstation
from zeromerma_api.modules.catalog.infrastructure.models import Product
from zeromerma_api.modules.orders.infrastructure.models import (
    CustomerOrder,
    CustomerOrderPayment,
    OrderCommitmentPolicy,
    OrderProductionCommitment,
    OrderRevision,
)
from zeromerma_api.modules.outbox.infrastructure.models import OutboxEvent
from zeromerma_api.testing.authorization import owner_headers
from zeromerma_api.testing.idempotency import new_idempotency_key
from zeromerma_api.testing.sessions import login_headers


def _setup(client: TestClient, *, policy: bool = True):
    seed_order_stock()
    with SessionLocal() as session:
        station = session.scalar(
            select(Workstation).where(Workstation.code == SEED_WORKSTATION_CODE)
        )
        product = session.scalar(
            select(Product).where(Product.code == SEED_PRODUCT_BOLILLO_STD_CODE)
        )
        branch_id, product_id = str(station.branch_id), str(product.id)
    if policy:
        configured = client.post(
            f"/v1/admin/orders/commitment-policies/{branch_id}",
            headers={**owner_headers(), "Idempotency-Key": new_idempotency_key()},
            json={"lead_time_minutes": 60, "reason": "Explicit synthetic test policy"},
        )
        assert configured.status_code == 201, configured.text
    headers = login_headers(
        client, email=SEED_USER_EMAIL, password=SEED_USER_PASSWORD, audience="POS"
    )
    opened = client.post(
        "/v1/cash-sessions/open",
        headers={**headers, "Idempotency-Key": new_idempotency_key()},
        json={"workstation_code": SEED_WORKSTATION_CODE, "opening_amount": "100"},
    )
    assert opened.status_code == 201, opened.text
    context = {"workstation_code": SEED_WORKSTATION_CODE, "cash_session_id": opened.json()["id"]}
    quote_payload = {
        "workstation_code": SEED_WORKSTATION_CODE,
        "requested_for_at": (datetime.now(UTC) + timedelta(days=2)).isoformat(),
        "items": [{"product_id": product_id, "quantity": "4"}],
    }
    return headers, context, quote_payload


def _quote(client, headers, payload):
    response = client.post("/v1/orders/quote", headers=headers, json=payload)
    assert response.status_code == 200, response.text
    return response.json()


def _create(client, headers, context, quote_payload, *, amount=None):
    quote = _quote(client, headers, quote_payload)
    payload = {
        **context,
        **quote_payload,
        "customer_name": "Synthetic order client",
        "quote_fingerprint": quote["quote_fingerprint"],
        "advance_amount": amount or quote["minimum_advance_amount"],
        "advance_payment_method_code": "CASH",
    }
    response = client.post(
        "/v1/orders", headers={**headers, "Idempotency-Key": new_idempotency_key()}, json=payload
    )
    assert response.status_code == 201, response.text
    return response.json(), quote


def _post(client, headers, path, body, key=None):
    return client.post(
        path, headers={**headers, "Idempotency-Key": key or new_idempotency_key()}, json=body
    )


def test_missing_policy_fails_closed_without_order_or_payment(client: TestClient):
    headers, context, payload = _setup(client, policy=False)
    quote = client.post("/v1/orders/quote", headers=headers, json=payload)
    assert quote.status_code == 409
    assert "ORDER_POLICY_REQUIRED" in quote.text
    with SessionLocal() as session:
        assert session.scalar(select(func.count()).select_from(CustomerOrder)) == 0
        assert session.scalar(select(func.count()).select_from(CustomerOrderPayment)) == 0


def test_quote_minimum_advance_and_changed_price_reject_before_any_effect(client: TestClient):
    headers, context, payload = _setup(client)
    quote = _quote(client, headers, payload)
    body = {
        **context,
        **payload,
        "customer_name": "Synthetic client",
        "quote_fingerprint": quote["quote_fingerprint"],
        "advance_amount": "0",
        "advance_payment_method_code": "CASH",
    }
    assert _post(client, headers, "/v1/orders", body).status_code == 400
    changed = {
        **body,
        "advance_amount": quote["minimum_advance_amount"],
        "quote_fingerprint": "f" * 64,
    }
    assert _post(client, headers, "/v1/orders", changed).status_code == 409
    with SessionLocal() as session:
        assert session.scalar(select(func.count()).select_from(CustomerOrder)) == 0


def test_interim_payment_replay_amendment_versions_and_merchant_refund(client: TestClient):
    headers, context, payload = _setup(client)
    created, quote = _create(client, headers, context, payload)
    order_id = created["id"]
    key = new_idempotency_key()
    payment = {**context, "payments": [{"payment_method_code": "CASH", "amount": "1.00"}]}
    paid = _post(client, headers, f"/v1/orders/{order_id}/payments", payment, key)
    assert paid.status_code == 200, paid.text
    assert (
        _post(client, headers, f"/v1/orders/{order_id}/payments", payment, key).json()
        == paid.json()
    )
    revision_payload = {**payload, "items": [{**payload["items"][0], "quantity": "5"}]}
    new_quote = _quote(client, headers, revision_payload)
    revised = _post(
        client,
        headers,
        f"/v1/orders/{order_id}/amend",
        {
            **context,
            **revision_payload,
            "expected_version": 1,
            "quote_fingerprint": new_quote["quote_fingerprint"],
            "reason": "Customer increased the quantity",
            "additional_payments": [{"payment_method_code": "CASH", "amount": "2.00"}],
        },
    )
    assert revised.status_code == 200, revised.text
    with SessionLocal() as session:
        revisions = session.scalars(
            select(OrderRevision)
            .where(OrderRevision.order_id == UUID(order_id))
            .order_by(OrderRevision.version)
        ).all()
        assert [version.version for version in revisions] == [1, 2]
        assert revisions[0].snapshot["items"][0]["quantity"] == "4.000"
        assert revisions[1].snapshot["items"][0]["quantity"] == "5.000"
    canceled = _post(
        client,
        headers,
        f"/v1/orders/{order_id}/cancel",
        {
            **context,
            "cancellation_reason": "Merchant cannot fulfill order",
            "cancellation_responsibility": "MERCHANT",
        },
    )
    assert canceled.status_code == 200, canceled.text
    assert (
        Decimal(canceled.json()["financial_refund"]["amount_due"])
        == Decimal(quote["minimum_advance_amount"]) + 3
    )
    assert _post(client, headers, f"/v1/orders/{order_id}/payments", payment).status_code == 409


def test_commitment_is_explicit_and_ready_delivery_consumes_once(client: TestClient):
    headers, context, payload = _setup(client)
    created, quote = _create(client, headers, context, payload)
    order_id = created["id"]
    assert _post(client, headers, f"/v1/orders/{order_id}/mark-ready", context).status_code == 409
    effective = datetime.fromisoformat(quote["production_commit_at"].replace("Z", "+00:00"))

    with order_clock(effective + timedelta(seconds=1)):
        ready = _post(client, headers, f"/v1/orders/{order_id}/mark-ready", context)
    assert ready.status_code == 200, ready.text
    settlement = {
        **context,
        "settlement_amount": created["remaining_balance_amount"],
        "settlement_payment_method_code": "CASH",
    }
    delivered = _post(client, headers, f"/v1/orders/{order_id}/deliver", settlement)
    assert delivered.status_code == 200, delivered.text
    assert _post(client, headers, f"/v1/orders/{order_id}/deliver", settlement).status_code == 409
    detail = client.get(
        f"/v1/orders/{order_id}",
        headers=headers,
        params={"workstation_code": SEED_WORKSTATION_CODE},
    ).json()
    assert detail["recognized_revenue_amount"] == created["total_amount"]
    assert len(detail["payments"]) == 2
    assert all(payment["receipt"] for payment in detail["payments"])
    with SessionLocal() as session:
        assert session.scalar(select(func.count()).select_from(OrderProductionCommitment)) == 1
        delivered_event = session.scalar(
            select(OutboxEvent).where(OutboxEvent.event_name == "order.delivered.v1")
        )
        assert delivered_event.payload["recognized_revenue_amount"] == created["total_amount"]
        assert delivered_event.payload["order_version"] == 1


def test_explicit_no_show_retains_customer_payment_after_commitment(client: TestClient):
    headers, context, payload = _setup(client)
    created, quote = _create(client, headers, context, payload)
    effective = datetime.fromisoformat(quote["production_commit_at"].replace("Z", "+00:00"))

    with order_clock(effective + timedelta(seconds=1)):
        result = _post(
            client,
            headers,
            f"/v1/orders/{created['id']}/cancel",
            {
                **context,
                "terminal_status": "NO_SHOW",
                "cancellation_responsibility": "CUSTOMER",
                "cancellation_reason": "Customer explicitly did not collect the order",
            },
        )
    assert result.status_code == 200, result.text
    assert result.json()["status"] == "NO_SHOW"
    assert result.json()["financial_refund"] is None
    listing = client.get(
        "/v1/orders",
        headers=headers,
        params={
            "workstation_code": context["workstation_code"],
            "status": "NO_SHOW",
            "query": created["folio"],
        },
    )
    assert listing.status_code == 200 and [row["id"] for row in listing.json()["orders"]] == [
        created["id"]
    ]
    administrative = client.get(
        "/v1/admin/orders", headers=owner_headers(), params={"search": created["folio"]}
    )
    assert administrative.status_code == 200, administrative.text
    assert administrative.json()["items"][0]["payment_state"] == "CANCELED"


def test_policy_recovery_keeps_exact_version_and_existing_cutoff_is_immutable(client: TestClient):
    headers, context, payload = _setup(client)
    created, quote = _create(client, headers, context, payload)
    branch_id = quote["branch_id"]
    admin, key = owner_headers(), new_idempotency_key()
    path = f"/v1/admin/orders/commitment-policies/{branch_id}"
    configured = _post(
        client,
        admin,
        path,
        {"lead_time_minutes": 120, "reason": "Explicit second test policy"},
        key,
    )
    assert configured.status_code == 201, configured.text
    assert configured.json()["version"] == 2
    assert (
        _post(
            client, admin, path, {"lead_time_minutes": 180, "reason": "Explicit third test policy"}
        ).status_code
        == 201
    )
    recovered = client.get(f"{path}/confirmations/{key}", headers=admin)
    assert recovered.status_code == 200, recovered.text
    assert recovered.json() == configured.json()
    assert client.get(path, headers=admin).json()["version"] == 3
    with SessionLocal() as session:
        order = session.get(CustomerOrder, UUID(created["id"]))
        assert (
            order.production_commit_at.isoformat()
            == datetime.fromisoformat(
                quote["production_commit_at"].replace("Z", "+00:00")
            ).isoformat()
        )
    for model, field, value in (
        (OrderCommitmentPolicy, "lead_time_minutes", 1),
        (OrderRevision, "snapshot", {}),
    ):
        with SessionLocal() as session, pytest.raises(DBAPIError, match="immutable"):
            session.execute(update(model).values({field: value}))
            session.commit()


def test_amendment_is_atomic_for_stale_versions_minimum_money_and_exact_cutoff(client: TestClient):
    headers, context, payload = _setup(client)
    created, quote = _create(client, headers, context, payload)
    order_id = created["id"]
    revised_payload = {**payload, "items": [{**payload["items"][0], "quantity": "8"}]}
    revised_quote = _quote(client, headers, revised_payload)
    body = {
        **context,
        **revised_payload,
        "expected_version": 1,
        "quote_fingerprint": revised_quote["quote_fingerprint"],
        "reason": "Explicit synthetic quantity increase",
        "additional_payments": [],
    }
    assert _post(client, headers, f"/v1/orders/{order_id}/amend", body).status_code == 400
    body["additional_payments"] = [{"payment_method_code": "CARD", "amount": "6.00"}]
    key = new_idempotency_key()
    accepted = _post(client, headers, f"/v1/orders/{order_id}/amend", body, key)
    assert accepted.status_code == 200, accepted.text
    assert (
        _post(client, headers, f"/v1/orders/{order_id}/amend", body, key).json() == accepted.json()
    )
    assert _post(client, headers, f"/v1/orders/{order_id}/amend", body).status_code == 409
    current = {**body, "expected_version": 2, "additional_payments": []}
    cutoff = datetime.fromisoformat(quote["production_commit_at"].replace("Z", "+00:00"))
    with order_clock(cutoff):
        rejected = _post(client, headers, f"/v1/orders/{order_id}/amend", current)
    assert rejected.status_code == 409 and "AFTER_PRODUCTION_COMMITMENT" in rejected.text
    with SessionLocal() as session:
        assert session.get(CustomerOrder, UUID(order_id)).version == 2
        assert session.scalar(select(func.count()).select_from(OrderRevision)) == 2
        assert session.scalar(select(func.count()).select_from(CustomerOrderPayment)) == 2
        assert session.scalar(select(func.count()).select_from(OrderProductionCommitment)) == 0


def test_a_real_catalog_price_change_invalidates_quote_without_repricing_paid_order(
    client: TestClient,
):
    headers, context, payload = _setup(client)
    created, original = _create(client, headers, context, payload)
    with SessionLocal() as session:
        product = session.get(Product, UUID(payload["items"][0]["product_id"]))
        product.unit_price += Decimal("1.00")
        session.commit()
    body = {
        **context,
        **payload,
        "customer_name": "Synthetic stale quote",
        "quote_fingerprint": original["quote_fingerprint"],
        "advance_amount": "8.00",
        "advance_payment_method_code": "CASH",
    }
    result = _post(client, headers, "/v1/orders", body)
    assert result.status_code == 409 and "ORDER_QUOTE_CHANGED" in result.text
    detail = client.get(
        f"/v1/orders/{created['id']}",
        headers=headers,
        params={"workstation_code": context["workstation_code"]},
    ).json()
    assert detail["total_amount"] == original["total_amount"]
    assert detail["items"][0]["unit_price"] == original["items"][0]["unit_price"]


def test_cancellation_uses_database_clock_instead_of_a_fast_application_clock(client: TestClient):
    headers, context, payload = _setup(client)
    created, quote = _create(client, headers, context, payload)

    class FastApplicationClock(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime.now(UTC) + timedelta(days=30)

    with patch("zeromerma_api.modules.orders.application.services.datetime", FastApplicationClock):
        canceled = _post(
            client,
            headers,
            f"/v1/orders/{created['id']}/cancel",
            {
                **context,
                "cancellation_responsibility": "CUSTOMER",
                "cancellation_reason": "Cancel before the actual database cutoff",
            },
        )
    assert canceled.status_code == 200, canceled.text
    assert canceled.json()["financial_refund"]["amount_due"] == quote["minimum_advance_amount"]
    with SessionLocal() as session:
        assert session.scalar(select(func.count()).select_from(OrderProductionCommitment)) == 0
        order = session.get(CustomerOrder, UUID(created["id"]))
        assert order.canceled_at < order.production_commit_at
