from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from fastapi.testclient import TestClient
from sqlalchemy import select

from zeromerma_api.bootstrap.seed_local import (
    SEED_BRANCH_TIMEZONE,
    SEED_PRODUCT_BOLILLO_STD_CODE,
    SEED_PRODUCT_CAFE_AMERICANO_CODE,
    SEED_PRODUCT_CLASS_BEBIDAS_CODE,
    SEED_USER_EMAIL,
    SEED_USER_PASSWORD,
    SEED_WORKSTATION_CODE,
)
from zeromerma_api.db.session import SessionLocal
from zeromerma_api.modules.audit.infrastructure.models import AuditLog
from zeromerma_api.modules.catalog.infrastructure.models import Product, ProductClass
from zeromerma_api.modules.orders.infrastructure.models import (
    CustomerOrder,
    CustomerOrderPayment,
)
from zeromerma_api.modules.outbox.infrastructure.models import OutboxEvent


def _login(client: TestClient) -> str:
    response = client.post(
        "/v1/auth/login",
        json={"email": SEED_USER_EMAIL, "password": SEED_USER_PASSWORD},
    )
    assert response.status_code == 200
    return str(response.json()["access_token"])


def _authorization_header(client: TestClient) -> dict[str, str]:
    return {"Authorization": f"Bearer {_login(client)}"}


def _open_cash_session(client: TestClient) -> None:
    response = client.post(
        "/v1/cash-sessions/open",
        headers=_authorization_header(client),
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


def _get_product_class_id(code: str) -> str:
    with SessionLocal() as session:
        product_class = session.execute(
            select(ProductClass).where(ProductClass.code == code)
        ).scalar_one()
    return str(product_class.id)


def _create_order(
    client: TestClient,
    *,
    customer_name: str = "Cliente Pedidos",
    advance_amount: str = "0.00",
    advance_payment_method_code: str | None = None,
    advance_payments: list[dict[str, str]] | None = None,
    requested_for_at: str | None = None,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "workstation_code": SEED_WORKSTATION_CODE,
        "customer_name": customer_name,
        "customer_phone": "6621234567",
        "requested_for_at": requested_for_at
        or (datetime.now(tz=UTC) + timedelta(days=2)).isoformat(),
        "notes": "Pedido de prueba",
        "items": [
            {
                "product_id": _get_product_id(SEED_PRODUCT_BOLILLO_STD_CODE),
                "quantity": "4",
            },
            {
                "product_id": _get_product_id(SEED_PRODUCT_CAFE_AMERICANO_CODE),
                "quantity": "1",
            },
        ],
        "advance_amount": advance_amount,
    }
    if advance_payment_method_code is not None:
        payload["advance_payment_method_code"] = advance_payment_method_code
    if advance_payments is not None:
        payload["advance_payments"] = advance_payments

    response = client.post(
        "/v1/orders",
        headers={
            **_authorization_header(client),
            "X-Request-ID": f"orders-create-{customer_name}",
        },
        json=payload,
    )
    assert response.status_code == 201
    return response.json()


def test_orders_bootstrap_catalog_and_class_products_follow_current_branch_context(
    client: TestClient,
) -> None:
    headers = _authorization_header(client)

    bootstrap_response = client.get(
        "/v1/orders/bootstrap",
        params={"workstation_code": SEED_WORKSTATION_CODE},
        headers=headers,
    )
    assert bootstrap_response.status_code == 200
    bootstrap_payload = bootstrap_response.json()
    assert bootstrap_payload["branch"]["code"] == "MAIN"
    assert bootstrap_payload["branch_brand_key"] == "EL_MEJOR_PAN"
    assert bootstrap_payload["current_open_cash_session"] is None
    assert bootstrap_payload["can_create_order"] is False
    assert [entry["count"] for entry in bootstrap_payload["status_counters"]] == [0, 0, 0, 0]

    catalog_response = client.get(
        "/v1/orders/catalog",
        params={"workstation_code": SEED_WORKSTATION_CODE, "query": "bebidas"},
        headers=headers,
    )
    assert catalog_response.status_code == 200
    catalog_payload = catalog_response.json()
    assert [entry["code"] for entry in catalog_payload["classes"]] == [
        SEED_PRODUCT_CLASS_BEBIDAS_CODE
    ]

    products_response = client.get(
        f"/v1/orders/classes/{_get_product_class_id(SEED_PRODUCT_CLASS_BEBIDAS_CODE)}/products",
        params={"workstation_code": SEED_WORKSTATION_CODE, "query": "americano"},
        headers=headers,
    )
    assert products_response.status_code == 200
    assert [entry["code"] for entry in products_response.json()["products"]] == [
        SEED_PRODUCT_CAFE_AMERICANO_CODE
    ]


def test_create_order_lists_and_details_with_advance_payment_audit_and_outbox(
    client: TestClient,
) -> None:
    _open_cash_session(client)

    payload = _create_order(
        client,
        customer_name="Cliente Anticipo",
        advance_amount="20.00",
        advance_payment_method_code="CASH",
    )

    assert payload["status"] == "PENDING"
    assert payload["customer_name"] == "Cliente Anticipo"
    assert Decimal(str(payload["subtotal_amount"])) == Decimal("34.00")
    assert Decimal(str(payload["total_amount"])) == Decimal("34.00")
    assert Decimal(str(payload["advance_amount"])) == Decimal("20.00")
    assert Decimal(str(payload["remaining_balance_amount"])) == Decimal("14.00")
    assert payload["payments"][0]["payment_type"] == "ADVANCE"
    assert payload["payments"][0]["payment_method_code"] == "CASH"
    assert payload["can_mark_ready"] is True
    assert payload["can_deliver"] is False
    assert payload["can_cancel"] is True
    assert payload["cancellation_refund_eligible"] is True
    assert Decimal(str(payload["cancellation_refund_amount"])) == Decimal("20.00")

    list_response = client.get(
        "/v1/orders",
        params={
            "workstation_code": SEED_WORKSTATION_CODE,
            "status": "PENDING",
            "query": "Cliente Anticipo",
        },
        headers=_authorization_header(client),
    )
    assert list_response.status_code == 200
    list_payload = list_response.json()
    assert list_payload["orders"][0]["id"] == payload["id"]
    assert Decimal(str(list_payload["orders"][0]["remaining_balance_amount"])) == Decimal("14.00")

    requested_date = (
        datetime.fromisoformat(payload["requested_for_at"])
        .astimezone(ZoneInfo(SEED_BRANCH_TIMEZONE))
        .date()
        .isoformat()
    )
    folio_list_response = client.get(
        "/v1/orders",
        params={
            "workstation_code": SEED_WORKSTATION_CODE,
            "status": "PENDING",
            "query": payload["folio"],
            "date_from": requested_date,
            "date_to": requested_date,
        },
        headers=_authorization_header(client),
    )
    assert folio_list_response.status_code == 200
    folio_list_payload = folio_list_response.json()
    assert folio_list_payload["orders"][0]["id"] == payload["id"]
    assert folio_list_payload["date_from"] == requested_date
    assert folio_list_payload["date_to"] == requested_date

    detail_response = client.get(
        f"/v1/orders/{payload['id']}",
        params={"workstation_code": SEED_WORKSTATION_CODE},
        headers=_authorization_header(client),
    )
    assert detail_response.status_code == 200
    assert detail_response.json()["folio"] == payload["folio"]

    with SessionLocal() as session:
        order_record = session.execute(
            select(CustomerOrder).where(CustomerOrder.id == payload["id"])
        ).scalar_one()
        payment_record = session.execute(
            select(CustomerOrderPayment).where(
                CustomerOrderPayment.customer_order_id == order_record.id
            )
        ).scalar_one()
        audit_record = session.execute(
            select(AuditLog).where(
                AuditLog.action == "order.created",
                AuditLog.resource_id == str(order_record.id),
            )
        ).scalar_one()
        outbox_event = session.execute(
            select(OutboxEvent).where(
                OutboxEvent.aggregate_id == str(order_record.id),
                OutboxEvent.event_name == "order.created.v1",
            )
        ).scalar_one()

    assert payment_record.payment_type == "ADVANCE"
    assert Decimal(str(payment_record.amount)) == Decimal("20.00")
    assert audit_record.request_id == "orders-create-Cliente Anticipo"
    assert outbox_event.payload["customer_name"] == "Cliente Anticipo"


def test_create_order_records_mixed_advance_as_cash_and_card_payments(client: TestClient) -> None:
    _open_cash_session(client)

    payload = _create_order(
        client,
        customer_name="Cliente Mixto",
        advance_amount="20.00",
        advance_payment_method_code="MIXED",
        advance_payments=[
            {"payment_method_code": "CASH", "amount": "8.00"},
            {"payment_method_code": "CARD", "amount": "12.00"},
        ],
    )

    assert Decimal(str(payload["advance_amount"])) == Decimal("20.00")
    assert [payment["payment_method_code"] for payment in payload["payments"]] == ["CASH", "CARD"]
    assert [Decimal(str(payment["amount"])) for payment in payload["payments"]] == [
        Decimal("8.00"),
        Decimal("12.00"),
    ]

    with SessionLocal() as session:
        payment_records = (
            session.execute(
                select(CustomerOrderPayment)
                .where(CustomerOrderPayment.customer_order_id == payload["id"])
                .order_by(CustomerOrderPayment.sequence)
            )
            .scalars()
            .all()
        )
        outbox_event = session.execute(
            select(OutboxEvent).where(
                OutboxEvent.aggregate_id == str(payload["id"]),
                OutboxEvent.event_name == "order.created.v1",
            )
        ).scalar_one()

    assert [payment.payment_method_code for payment in payment_records] == ["CASH", "CARD"]
    assert [Decimal(str(payment.amount)) for payment in payment_records] == [
        Decimal("8.00"),
        Decimal("12.00"),
    ]
    assert [payment["payment_method_code"] for payment in outbox_event.payload["payments"]] == [
        "CASH",
        "CARD",
    ]


def test_order_lifecycle_marks_ready_and_delivers_with_final_settlement(client: TestClient) -> None:
    _open_cash_session(client)
    created_order = _create_order(
        client,
        customer_name="Cliente Entrega",
        advance_amount="10.00",
        advance_payment_method_code="CARD",
    )

    ready_response = client.post(
        f"/v1/orders/{created_order['id']}/mark-ready",
        headers={
            **_authorization_header(client),
            "X-Request-ID": "orders-ready-cliente-entrega",
        },
        json={"workstation_code": SEED_WORKSTATION_CODE},
    )
    assert ready_response.status_code == 200
    ready_payload = ready_response.json()
    assert ready_payload["status"] == "READY"
    assert ready_payload["can_deliver"] is True
    assert ready_payload["requires_settlement_on_delivery"] is True

    deliver_response = client.post(
        f"/v1/orders/{created_order['id']}/deliver",
        headers={
            **_authorization_header(client),
            "X-Request-ID": "orders-deliver-cliente-entrega",
        },
        json={
            "workstation_code": SEED_WORKSTATION_CODE,
            "settlement_amount": "24.00",
            "settlement_payment_method_code": "CASH",
        },
    )
    assert deliver_response.status_code == 200
    delivered_payload = deliver_response.json()
    assert delivered_payload["status"] == "DELIVERED"
    assert Decimal(str(delivered_payload["remaining_balance_amount"])) == Decimal("0.00")
    assert delivered_payload["can_mark_ready"] is False
    assert delivered_payload["can_deliver"] is False
    assert delivered_payload["can_cancel"] is False
    assert [entry["payment_type"] for entry in delivered_payload["payments"]] == [
        "ADVANCE",
        "SETTLEMENT",
    ]

    with SessionLocal() as session:
        payment_records = (
            session.execute(
                select(CustomerOrderPayment)
                .where(CustomerOrderPayment.customer_order_id == delivered_payload["id"])
                .order_by(CustomerOrderPayment.sequence)
            )
            .scalars()
            .all()
        )
        outbox_events = (
            session.execute(
                select(OutboxEvent)
                .where(OutboxEvent.aggregate_id == str(delivered_payload["id"]))
                .order_by(OutboxEvent.occurred_at)
            )
            .scalars()
            .all()
        )

    assert [payment.payment_method_code for payment in payment_records] == ["CARD", "CASH"]
    assert [event.event_name for event in outbox_events] == [
        "order.created.v1",
        "order.ready.v1",
        "order.delivered.v1",
    ]


def test_order_delivery_records_mixed_final_settlement_as_cash_and_card(client: TestClient) -> None:
    _open_cash_session(client)
    created_order = _create_order(
        client,
        customer_name="Cliente Entrega Mixta",
        advance_amount="10.00",
        advance_payment_method_code="CARD",
    )

    ready_response = client.post(
        f"/v1/orders/{created_order['id']}/mark-ready",
        headers=_authorization_header(client),
        json={"workstation_code": SEED_WORKSTATION_CODE},
    )
    assert ready_response.status_code == 200

    deliver_response = client.post(
        f"/v1/orders/{created_order['id']}/deliver",
        headers={
            **_authorization_header(client),
            "X-Request-ID": "orders-deliver-cliente-entrega-mixta",
        },
        json={
            "workstation_code": SEED_WORKSTATION_CODE,
            "settlement_amount": "24.00",
            "settlement_payment_method_code": "MIXED",
            "settlement_payments": [
                {"payment_method_code": "CASH", "amount": "9.00"},
                {"payment_method_code": "CARD", "amount": "15.00"},
            ],
        },
    )
    assert deliver_response.status_code == 200
    delivered_payload = deliver_response.json()
    assert delivered_payload["status"] == "DELIVERED"
    assert [entry["payment_method_code"] for entry in delivered_payload["payments"]] == [
        "CARD",
        "CASH",
        "CARD",
    ]
    assert [Decimal(str(entry["amount"])) for entry in delivered_payload["payments"]] == [
        Decimal("10.00"),
        Decimal("9.00"),
        Decimal("15.00"),
    ]

    with SessionLocal() as session:
        payment_records = (
            session.execute(
                select(CustomerOrderPayment)
                .where(CustomerOrderPayment.customer_order_id == delivered_payload["id"])
                .order_by(CustomerOrderPayment.sequence)
            )
            .scalars()
            .all()
        )
        outbox_event = session.execute(
            select(OutboxEvent).where(
                OutboxEvent.aggregate_id == str(delivered_payload["id"]),
                OutboxEvent.event_name == "order.delivered.v1",
            )
        ).scalar_one()

    assert [payment.payment_method_code for payment in payment_records] == ["CARD", "CASH", "CARD"]
    assert outbox_event.payload["settlement_payment_method_code"] == "MIXED"
    assert [
        payment["payment_method_code"] for payment in outbox_event.payload["settlement_payments"]
    ] == ["CASH", "CARD"]


def test_order_delivery_rejects_mixed_settlement_without_cash_and_card_breakdown(
    client: TestClient,
) -> None:
    _open_cash_session(client)
    created_order = _create_order(
        client,
        customer_name="Cliente Entrega Mixta Invalida",
        advance_amount="10.00",
        advance_payment_method_code="CARD",
    )

    ready_response = client.post(
        f"/v1/orders/{created_order['id']}/mark-ready",
        headers=_authorization_header(client),
        json={"workstation_code": SEED_WORKSTATION_CODE},
    )
    assert ready_response.status_code == 200

    deliver_response = client.post(
        f"/v1/orders/{created_order['id']}/deliver",
        headers=_authorization_header(client),
        json={
            "workstation_code": SEED_WORKSTATION_CODE,
            "settlement_amount": "24.00",
            "settlement_payment_method_code": "MIXED",
            "settlement_payments": [{"payment_method_code": "CASH", "amount": "24.00"}],
        },
    )
    assert deliver_response.status_code == 400
    assert (
        deliver_response.json()["message"]
        == "El cobro mixto de la liquidacion final requiere efectivo y tarjeta."
    )


def test_order_creation_rejects_removed_other_payment_method(client: TestClient) -> None:
    _open_cash_session(client)

    response = client.post(
        "/v1/orders",
        headers=_authorization_header(client),
        json={
            "workstation_code": SEED_WORKSTATION_CODE,
            "customer_name": "Cliente Metodo Invalido",
            "customer_phone": "6621234567",
            "requested_for_at": "2026-04-11T18:30:00-07:00",
            "items": [
                {
                    "product_id": _get_product_id(SEED_PRODUCT_BOLILLO_STD_CODE),
                    "quantity": "2",
                }
            ],
            "advance_amount": "2.00",
            "advance_payment_method_code": "OTHER",
        },
    )

    assert response.status_code == 400
    assert response.json()["message"] == "Selecciona un metodo de pago valido."


def test_order_creation_rejects_mixed_advance_without_cash_and_card_breakdown(
    client: TestClient,
) -> None:
    _open_cash_session(client)

    response = client.post(
        "/v1/orders",
        headers=_authorization_header(client),
        json={
            "workstation_code": SEED_WORKSTATION_CODE,
            "customer_name": "Cliente Mixto Invalido",
            "customer_phone": "6621234567",
            "requested_for_at": "2026-04-11T18:30:00-07:00",
            "items": [
                {
                    "product_id": _get_product_id(SEED_PRODUCT_BOLILLO_STD_CODE),
                    "quantity": "2",
                }
            ],
            "advance_amount": "2.00",
            "advance_payment_method_code": "MIXED",
            "advance_payments": [{"payment_method_code": "CASH", "amount": "2.00"}],
        },
    )

    assert response.status_code == 400
    assert response.json()["message"] == "El cobro mixto del anticipo requiere efectivo y tarjeta."


def test_cancel_refunds_advance_when_order_is_canceled_before_cutoff(client: TestClient) -> None:
    _open_cash_session(client)

    refundable_order = _create_order(
        client,
        customer_name="Cliente Reembolso Anticipado",
        advance_amount="5.00",
        advance_payment_method_code="CASH",
        requested_for_at=(datetime.now(tz=UTC) + timedelta(days=2)).isoformat(),
    )
    ready_response = client.post(
        f"/v1/orders/{refundable_order['id']}/mark-ready",
        headers=_authorization_header(client),
        json={"workstation_code": SEED_WORKSTATION_CODE},
    )
    assert ready_response.status_code == 200
    cancel_response = client.post(
        f"/v1/orders/{refundable_order['id']}/cancel",
        headers={
            **_authorization_header(client),
            "X-Request-ID": "orders-cancel-advance-refund",
        },
        json={
            "workstation_code": SEED_WORKSTATION_CODE,
            "cancellation_reason": "Cliente cancelo con anticipacion.",
        },
    )
    assert cancel_response.status_code == 200
    canceled_payload = cancel_response.json()
    assert canceled_payload["status"] == "CANCELED"
    assert Decimal(str(canceled_payload["advance_amount"])) == Decimal("0.00")
    assert Decimal(str(canceled_payload["remaining_balance_amount"])) == Decimal("0.00")

    with SessionLocal() as session:
        payment_records = (
            session.execute(
                select(CustomerOrderPayment)
                .where(CustomerOrderPayment.customer_order_id == refundable_order["id"])
                .order_by(CustomerOrderPayment.sequence)
            )
            .scalars()
            .all()
        )
        audit_record = session.execute(
            select(AuditLog).where(
                AuditLog.action == "order.canceled",
                AuditLog.resource_id == str(refundable_order["id"]),
            )
        ).scalar_one()
        outbox_event = session.execute(
            select(OutboxEvent).where(
                OutboxEvent.aggregate_id == str(refundable_order["id"]),
                OutboxEvent.event_name == "order.canceled.v1",
            )
        ).scalar_one()

    assert [(record.payment_type, Decimal(str(record.amount))) for record in payment_records] == [
        ("ADVANCE", Decimal("5.00")),
        ("REFUND", Decimal("5.00")),
    ]
    assert audit_record.request_id == "orders-cancel-advance-refund"
    assert audit_record.metadata_["cancellation_reason"] == "Cliente cancelo con anticipacion."
    assert audit_record.metadata_["cancellation_refund_eligible"] is True
    assert audit_record.metadata_["cancellation_refund_amount"] == "5.00"
    assert outbox_event.payload["cancellation_reason"] == "Cliente cancelo con anticipacion."
    assert outbox_event.payload["cancellation_refund_eligible"] is True
    assert outbox_event.payload["cancellation_refund_amount"] == "5.00"
    assert outbox_event.payload["refund_payments"] == [
        {"payment_method_code": "CASH", "amount": "5.00"}
    ]


def test_cancel_keeps_advance_when_order_is_canceled_after_cutoff(client: TestClient) -> None:
    _open_cash_session(client)

    late_cancel_order = _create_order(
        client,
        customer_name="Cliente Cancelacion Tardia",
        advance_amount="5.00",
        advance_payment_method_code="CASH",
        requested_for_at=(datetime.now(tz=UTC) + timedelta(hours=8)).isoformat(),
    )
    cancel_response = client.post(
        f"/v1/orders/{late_cancel_order['id']}/cancel",
        headers=_authorization_header(client),
        json={
            "workstation_code": SEED_WORKSTATION_CODE,
            "cancellation_reason": "Cancelacion fuera de plazo.",
        },
    )
    assert cancel_response.status_code == 200
    canceled_payload = cancel_response.json()
    assert canceled_payload["status"] == "CANCELED"
    assert Decimal(str(canceled_payload["advance_amount"])) == Decimal("5.00")
    assert Decimal(str(canceled_payload["remaining_balance_amount"])) == Decimal("0.00")
    assert canceled_payload["cancellation_reason"] == "Cancelacion fuera de plazo."

    with SessionLocal() as session:
        payment_records = (
            session.execute(
                select(CustomerOrderPayment)
                .where(CustomerOrderPayment.customer_order_id == late_cancel_order["id"])
                .order_by(CustomerOrderPayment.sequence)
            )
            .scalars()
            .all()
        )

    assert [(record.payment_type, Decimal(str(record.amount))) for record in payment_records] == [
        ("ADVANCE", Decimal("5.00"))
    ]


def test_cancel_rules_still_block_delivered_orders_and_allow_safe_cancel(
    client: TestClient,
) -> None:
    _open_cash_session(client)

    safe_order = _create_order(client, customer_name="Cliente Cancelable")
    cancel_response = client.post(
        f"/v1/orders/{safe_order['id']}/cancel",
        headers={
            **_authorization_header(client),
            "X-Request-ID": "orders-cancel-cliente-cancelable",
        },
        json={
            "workstation_code": SEED_WORKSTATION_CODE,
            "cancellation_reason": "Cliente ya no requiere el pedido.",
        },
    )
    assert cancel_response.status_code == 200
    canceled_payload = cancel_response.json()
    assert canceled_payload["status"] == "CANCELED"
    assert canceled_payload["can_cancel"] is False

    delivered_order = _create_order(client, customer_name="Cliente Ya Entregado")
    ready_response = client.post(
        f"/v1/orders/{delivered_order['id']}/mark-ready",
        headers=_authorization_header(client),
        json={"workstation_code": SEED_WORKSTATION_CODE},
    )
    assert ready_response.status_code == 200
    deliver_response = client.post(
        f"/v1/orders/{delivered_order['id']}/deliver",
        headers=_authorization_header(client),
        json={
            "workstation_code": SEED_WORKSTATION_CODE,
            "settlement_amount": "34.00",
            "settlement_payment_method_code": "CARD",
        },
    )
    assert deliver_response.status_code == 200

    delivered_cancel_response = client.post(
        f"/v1/orders/{delivered_order['id']}/cancel",
        headers=_authorization_header(client),
        json={
            "workstation_code": SEED_WORKSTATION_CODE,
            "cancellation_reason": "Intento invalido tras entrega.",
        },
    )
    assert delivered_cancel_response.status_code == 409
    assert "ya fue entregado" in delivered_cancel_response.json()["message"]

    with SessionLocal() as session:
        audit_record = session.execute(
            select(AuditLog).where(
                AuditLog.action == "order.canceled",
                AuditLog.resource_id == str(safe_order["id"]),
            )
        ).scalar_one()
        outbox_event = session.execute(
            select(OutboxEvent).where(
                OutboxEvent.aggregate_id == str(safe_order["id"]),
                OutboxEvent.event_name == "order.canceled.v1",
            )
        ).scalar_one()

    assert audit_record.request_id == "orders-cancel-cliente-cancelable"
    assert audit_record.metadata_["cancellation_reason"] == "Cliente ya no requiere el pedido."
    assert outbox_event.payload["status"] == "CANCELED"


def test_cancel_requires_reason_and_rejects_invalid_date_range_filter(client: TestClient) -> None:
    _open_cash_session(client)

    created_order = _create_order(client, customer_name="Cliente Validacion Cancelacion")

    cancel_response = client.post(
        f"/v1/orders/{created_order['id']}/cancel",
        headers=_authorization_header(client),
        json={"workstation_code": SEED_WORKSTATION_CODE},
    )
    assert cancel_response.status_code == 422

    invalid_date_response = client.get(
        "/v1/orders",
        params={
            "workstation_code": SEED_WORKSTATION_CODE,
            "date_from": "2026-04-22",
            "date_to": "2026-04-21",
        },
        headers=_authorization_header(client),
    )
    assert invalid_date_response.status_code == 400
    assert "fecha inicial" in invalid_date_response.json()["message"]
