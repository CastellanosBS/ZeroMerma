from __future__ import annotations

from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import select

from zeromerma_api.bootstrap.seed_local import (
    SEED_PRODUCT_CAFE_AMERICANO_CODE,
    SEED_PRODUCT_CLASS_BEBIDAS_CODE,
    SEED_PRODUCT_CLASS_BOLILLO_CODE,
    SEED_PRODUCT_CLASS_PAN_DULCE_CODE,
    SEED_PRODUCT_CLASS_PASTELES_CODE,
    SEED_PRODUCT_CLASS_TELERA_CODE,
    SEED_PRODUCT_COCA_355_CODE,
    SEED_PRODUCT_REBANADA_TRES_LECHES_CODE,
    SEED_USER_EMAIL,
    SEED_USER_PASSWORD,
    SEED_WORKSTATION_CODE,
)
from zeromerma_api.db.session import SessionLocal
from zeromerma_api.modules.audit.infrastructure.models import AuditLog
from zeromerma_api.modules.catalog.infrastructure.models import Product, ProductClass
from zeromerma_api.modules.outbox.infrastructure.models import OutboxEvent
from zeromerma_api.modules.sales.infrastructure.models import CashMovement, Sale, SalePayment


def _login(client: TestClient) -> str:
    response = client.post(
        "/v1/auth/login",
        json={"email": SEED_USER_EMAIL, "password": SEED_USER_PASSWORD},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["user"]["email"] == SEED_USER_EMAIL
    return str(payload["access_token"])


def _authorization_header(client: TestClient) -> dict[str, str]:
    return {"Authorization": f"Bearer {_login(client)}"}


def _open_cash_session(client: TestClient) -> None:
    response = client.post(
        "/v1/cash-sessions/open",
        headers=_authorization_header(client),
        json={
            "workstation_code": SEED_WORKSTATION_CODE,
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


def _get_product_id(code: str) -> str:
    with SessionLocal() as session:
        product = session.execute(select(Product).where(Product.code == code)).scalar_one()
    return str(product.id)


def test_pos_catalog_supports_class_and_product_search_for_main_pos_flow(
    client: TestClient,
) -> None:
    headers = _authorization_header(client)

    catalog_response = client.get(
        f"/v1/pos/catalog?workstation_code={SEED_WORKSTATION_CODE}&query=coca",
        headers=headers,
    )

    assert catalog_response.status_code == 200
    catalog_payload = catalog_response.json()
    assert catalog_payload["workstation_code"] == SEED_WORKSTATION_CODE
    bebidas_entry = next(
        item
        for item in catalog_payload["classes"]
        if item["code"] == SEED_PRODUCT_CLASS_BEBIDAS_CODE
    )
    assert bebidas_entry["capture_mode_default"] == "PRODUCT_DIRECT"
    assert bebidas_entry["product_count"] == 2

    class_products_response = client.get(
        f"/v1/pos/classes/{_get_product_class_id(SEED_PRODUCT_CLASS_BEBIDAS_CODE)}/products"
        f"?workstation_code={SEED_WORKSTATION_CODE}&query=americano",
        headers=headers,
    )

    assert class_products_response.status_code == 200
    class_products_payload = class_products_response.json()
    assert class_products_payload["class_code"] == SEED_PRODUCT_CLASS_BEBIDAS_CODE
    assert [product["code"] for product in class_products_payload["products"]] == [
        SEED_PRODUCT_CAFE_AMERICANO_CODE
    ]


def test_pos_catalog_orders_classes_by_capture_mode_and_display_order(client: TestClient) -> None:
    response = client.get(
        f"/v1/pos/catalog?workstation_code={SEED_WORKSTATION_CODE}",
        headers=_authorization_header(client),
    )

    assert response.status_code == 200
    assert [entry["code"] for entry in response.json()["classes"]] == [
        SEED_PRODUCT_CLASS_PAN_DULCE_CODE,
        SEED_PRODUCT_CLASS_BOLILLO_CODE,
        SEED_PRODUCT_CLASS_TELERA_CODE,
        SEED_PRODUCT_CLASS_BEBIDAS_CODE,
        SEED_PRODUCT_CLASS_PASTELES_CODE,
    ]


def test_class_capture_sale_confirmation_writes_sale_payment_cash_movement_audit_and_outbox(
    client: TestClient,
) -> None:
    _open_cash_session(client)
    headers = {
        **_authorization_header(client),
        "X-Request-ID": "phase-2a-class-capture",
    }

    response = client.post(
        "/v1/sales/confirm",
        headers=headers,
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
    payload = response.json()
    assert Decimal(str(payload["total_amount"])) == Decimal("24.00")
    assert Decimal(str(payload["paid_amount"])) == Decimal("24.00")
    assert Decimal(str(payload["change_amount"])) == Decimal("26.00")
    assert payload["lines"][0]["product_class_code"] == SEED_PRODUCT_CLASS_PAN_DULCE_CODE
    assert payload["lines"][0]["product_id"] is None
    assert payload["lines"][0]["physical_attribution_status"] == "PENDING_RECONCILIATION"
    assert payload["payments"][0]["payment_method_code"] == "CASH"

    sale_lookup_response = client.get(
        f"/v1/sales/{payload['id']}",
        headers=_authorization_header(client),
    )
    assert sale_lookup_response.status_code == 200
    assert sale_lookup_response.json()["id"] == payload["id"]

    with SessionLocal() as session:
        sale_record = session.execute(select(Sale).where(Sale.id == payload["id"])).scalar_one()
        payment_record = session.execute(
            select(SalePayment).where(SalePayment.sale_id == sale_record.id)
        ).scalar_one()
        cash_movement_record = session.execute(
            select(CashMovement).where(CashMovement.sale_id == sale_record.id)
        ).scalar_one()
        audit_record = session.execute(
            select(AuditLog).where(AuditLog.action == "sale.confirmed")
        ).scalar_one()
        outbox_event = session.execute(
            select(OutboxEvent).where(OutboxEvent.event_name == "sale.confirmed.v1")
        ).scalar_one()

    assert Decimal(str(payment_record.applied_amount)) == Decimal("24.00")
    assert Decimal(str(cash_movement_record.amount)) == Decimal("24.00")
    assert audit_record.request_id == "phase-2a-class-capture"
    assert audit_record.resource_id == payload["id"]
    assert outbox_event.payload["sale_id"] == payload["id"]


def test_product_direct_sale_confirmation_uses_product_reference_and_direct_assignment(
    client: TestClient,
) -> None:
    _open_cash_session(client)

    response = client.post(
        "/v1/sales/confirm",
        headers=_authorization_header(client),
        json={
            "workstation_code": SEED_WORKSTATION_CODE,
            "lines": [
                {
                    "capture_mode": "PRODUCT_DIRECT",
                    "product_id": _get_product_id(SEED_PRODUCT_COCA_355_CODE),
                    "quantity": "1",
                }
            ],
            "payments": [
                {
                    "payment_method_code": "CASH",
                    "tendered_amount": "20.00",
                }
            ],
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert Decimal(str(payload["total_amount"])) == Decimal("18.00")
    assert payload["lines"][0]["product_code"] == SEED_PRODUCT_COCA_355_CODE
    assert payload["lines"][0]["physical_attribution_status"] == "DIRECT_ASSIGNED"


def test_mixed_sale_confirmation_supports_class_capture_and_product_direct_lines(
    client: TestClient,
) -> None:
    _open_cash_session(client)

    response = client.post(
        "/v1/sales/confirm",
        headers=_authorization_header(client),
        json={
            "workstation_code": SEED_WORKSTATION_CODE,
            "lines": [
                {
                    "capture_mode": "CLASS_CAPTURE",
                    "product_class_id": _get_product_class_id(SEED_PRODUCT_CLASS_PAN_DULCE_CODE),
                    "quantity": "2",
                },
                {
                    "capture_mode": "PRODUCT_DIRECT",
                    "product_id": _get_product_id(SEED_PRODUCT_REBANADA_TRES_LECHES_CODE),
                    "quantity": "1",
                },
            ],
            "payments": [
                {
                    "payment_method_code": "CASH",
                    "tendered_amount": "100.00",
                }
            ],
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert Decimal(str(payload["total_amount"])) == Decimal("62.00")
    assert Decimal(str(payload["change_amount"])) == Decimal("38.00")
    assert {line["capture_mode"] for line in payload["lines"]} == {
        "CLASS_CAPTURE",
        "PRODUCT_DIRECT",
    }


def test_sale_confirmation_supports_card_payment_without_cash_movement(
    client: TestClient,
) -> None:
    _open_cash_session(client)

    response = client.post(
        "/v1/sales/confirm",
        headers=_authorization_header(client),
        json={
            "workstation_code": SEED_WORKSTATION_CODE,
            "lines": [
                {
                    "capture_mode": "PRODUCT_DIRECT",
                    "product_id": _get_product_id(SEED_PRODUCT_COCA_355_CODE),
                    "quantity": "1",
                }
            ],
            "payments": [
                {
                    "payment_method_code": "CARD",
                    "tendered_amount": "18.00",
                }
            ],
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert Decimal(str(payload["paid_amount"])) == Decimal("18.00")
    assert Decimal(str(payload["change_amount"])) == Decimal("0.00")
    assert payload["payments"][0]["payment_method_code"] == "CARD"

    with SessionLocal() as session:
        sale_record = session.execute(select(Sale).where(Sale.id == payload["id"])).scalar_one()
        payment_record = session.execute(
            select(SalePayment).where(SalePayment.sale_id == sale_record.id)
        ).scalar_one()
        cash_movement_records = (
            session.execute(select(CashMovement).where(CashMovement.sale_id == sale_record.id))
            .scalars()
            .all()
        )

    assert payment_record.payment_method_code == "CARD"
    assert cash_movement_records == []


def test_sale_confirmation_supports_mixed_cash_and_card_payment(
    client: TestClient,
) -> None:
    _open_cash_session(client)

    response = client.post(
        "/v1/sales/confirm",
        headers=_authorization_header(client),
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
                    "payment_method_code": "CARD",
                    "tendered_amount": "10.00",
                },
                {
                    "payment_method_code": "CASH",
                    "tendered_amount": "20.00",
                },
            ],
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert Decimal(str(payload["total_amount"])) == Decimal("24.00")
    assert Decimal(str(payload["change_amount"])) == Decimal("6.00")
    assert [payment["payment_method_code"] for payment in payload["payments"]] == [
        "CARD",
        "CASH",
    ]

    with SessionLocal() as session:
        sale_record = session.execute(select(Sale).where(Sale.id == payload["id"])).scalar_one()
        payment_records = (
            session.execute(
                select(SalePayment)
                .where(SalePayment.sale_id == sale_record.id)
                .order_by(SalePayment.sequence.asc())
            )
            .scalars()
            .all()
        )
        cash_movement_record = session.execute(
            select(CashMovement).where(CashMovement.sale_id == sale_record.id)
        ).scalar_one()

    assert [record.payment_method_code for record in payment_records] == ["CARD", "CASH"]
    assert [Decimal(str(record.applied_amount)) for record in payment_records] == [
        Decimal("10.00"),
        Decimal("14.00"),
    ]
    assert Decimal(str(payment_records[1].change_amount)) == Decimal("6.00")
    assert Decimal(str(cash_movement_record.amount)) == Decimal("14.00")


def test_sale_confirmation_rejects_removed_other_payment_method(
    client: TestClient,
) -> None:
    _open_cash_session(client)

    response = client.post(
        "/v1/sales/confirm",
        headers=_authorization_header(client),
        json={
            "workstation_code": SEED_WORKSTATION_CODE,
            "lines": [
                {
                    "capture_mode": "CLASS_CAPTURE",
                    "product_class_id": _get_product_class_id(SEED_PRODUCT_CLASS_BOLILLO_CODE),
                    "quantity": "2",
                }
            ],
            "payments": [
                {
                    "payment_method_code": "OTHER",
                    "tendered_amount": "6.00",
                }
            ],
        },
    )

    assert response.status_code == 409
    assert response.json()["message"] == "El metodo de pago OTHER no esta disponible."


def test_sale_confirmation_rejects_insufficient_cash(client: TestClient) -> None:
    _open_cash_session(client)

    response = client.post(
        "/v1/sales/confirm",
        headers=_authorization_header(client),
        json={
            "workstation_code": SEED_WORKSTATION_CODE,
            "lines": [
                {
                    "capture_mode": "CLASS_CAPTURE",
                    "product_class_id": _get_product_class_id(SEED_PRODUCT_CLASS_PAN_DULCE_CODE),
                    "quantity": "1",
                }
            ],
            "payments": [
                {
                    "payment_method_code": "CASH",
                    "tendered_amount": "10.00",
                }
            ],
        },
    )

    assert response.status_code == 409
    assert response.json()["message"] == "El efectivo registrado no cubre el total pendiente."


def test_sale_confirmation_requires_open_cash_session(client: TestClient) -> None:
    response = client.post(
        "/v1/sales/confirm",
        headers=_authorization_header(client),
        json={
            "workstation_code": SEED_WORKSTATION_CODE,
            "lines": [
                {
                    "capture_mode": "PRODUCT_DIRECT",
                    "product_id": _get_product_id(SEED_PRODUCT_COCA_355_CODE),
                    "quantity": "1",
                }
            ],
            "payments": [
                {
                    "payment_method_code": "CASH",
                    "tendered_amount": "20.00",
                }
            ],
        },
    )

    assert response.status_code == 409
    assert "requires an OPEN cash session" in response.json()["message"]
