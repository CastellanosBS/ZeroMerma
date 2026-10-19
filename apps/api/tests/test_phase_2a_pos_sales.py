from __future__ import annotations

from decimal import Decimal

from fastapi.testclient import TestClient
from inventory_fixtures import stock_for_codes
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
from zeromerma_api.modules.financial_ledger.infrastructure.models import (
    FinancialEntry,
    FinancialOperation,
)
from zeromerma_api.modules.outbox.infrastructure.models import OutboxEvent
from zeromerma_api.modules.sales.infrastructure.models import CashMovement, Sale, SalePayment
from zeromerma_api.testing.idempotency import current_cash_session_id, new_idempotency_key
from zeromerma_api.testing.sessions import login_headers


def _login(client: TestClient) -> dict[str, str]:
    return login_headers(client, email=SEED_USER_EMAIL, password=SEED_USER_PASSWORD, audience="POS")


def _authorization_header(client: TestClient) -> dict[str, str]:
    return _login(client)


def _open_cash_session(client: TestClient) -> None:
    stock_for_codes(
        workstation_code=SEED_WORKSTATION_CODE,
        quantities={
            SEED_PRODUCT_COCA_355_CODE: Decimal(10),
            SEED_PRODUCT_REBANADA_TRES_LECHES_CODE: Decimal(10),
        },
        location="COUNTER",
        reference="sale-contract-physical-input",
    )
    response = client.post(
        "/v1/cash-sessions/open",
        headers={**_authorization_header(client), "Idempotency-Key": new_idempotency_key()},
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


def test_class_capture_sale_confirmation_writes_financial_fact_audit_and_outbox_without_mirror(
    client: TestClient,
) -> None:
    _open_cash_session(client)
    headers = {
        **_authorization_header(client),
        "X-Request-ID": "e820f01b-c850-5472-889c-4e6570b14467",
    }

    cash_session_id = current_cash_session_id(
        client, headers=headers, workstation_code=SEED_WORKSTATION_CODE
    )
    headers["Idempotency-Key"] = new_idempotency_key()

    response = client.post(
        "/v1/sales/confirm",
        headers=headers,
        json={
            "cash_session_id": cash_session_id,
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
        assert (
            session.scalar(select(CashMovement).where(CashMovement.sale_id == sale_record.id))
            is None
        )
        operation = session.scalars(
            select(FinancialOperation).where(FinancialOperation.source_id == sale_record.id)
        ).one()
        entry = session.scalars(
            select(FinancialEntry).where(FinancialEntry.financial_operation_id == operation.id)
        ).one()
        audit_record = session.execute(
            select(AuditLog).where(AuditLog.action == "sale.confirmed")
        ).scalar_one()
        outbox_event = session.execute(
            select(OutboxEvent).where(OutboxEvent.event_name == "sale.confirmed.v1")
        ).scalar_one()

    assert Decimal(str(payment_record.applied_amount)) == Decimal("24.00")
    assert operation.kind == "SALE_COLLECTION"
    assert operation.source_type == operation.subject_type == "SALE"
    assert operation.subject_id == sale_record.id
    assert operation.amount_due == entry.amount == Decimal("24.00")
    assert entry.payment_method_code == "CASH" and entry.direction == "IN"
    assert entry.state == "CONFIRMED" and entry.execution_mode == "LOCAL"
    assert entry.tendered_amount == Decimal("50.00")
    assert entry.change_amount == Decimal("26.00")
    assert entry.leg_key == str(payment_record.id)
    assert operation.branch_id == entry.branch_id == sale_record.branch_id
    assert operation.workstation_id == entry.workstation_id == sale_record.workstation_id
    assert operation.cash_session_id == entry.cash_session_id == sale_record.cash_session_id
    assert operation.actor_id == entry.actor_id == sale_record.operator_id
    assert audit_record.request_id == "e820f01b-c850-5472-889c-4e6570b14467"
    assert audit_record.resource_id == payload["id"]
    assert outbox_event.payload["sale_id"] == payload["id"]
    for trace in (audit_record.metadata_, outbox_event.payload, outbox_event.headers):
        assert trace["financial_operation_id"] == str(operation.id)
        assert trace["financial_entry_ids"] == [str(entry.id)]
    assert operation.operation_id == entry.operation_id == audit_record.operation_id
    assert operation.operation_id == outbox_event.operation_id


def test_product_direct_sale_confirmation_uses_product_reference_and_direct_assignment(
    client: TestClient,
) -> None:
    _open_cash_session(client)

    headers = _authorization_header(client)
    cash_session_id = current_cash_session_id(
        client, headers=headers, workstation_code=SEED_WORKSTATION_CODE
    )
    headers["Idempotency-Key"] = new_idempotency_key()

    response = client.post(
        "/v1/sales/confirm",
        headers=headers,
        json={
            "cash_session_id": cash_session_id,
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

    headers = _authorization_header(client)
    cash_session_id = current_cash_session_id(
        client, headers=headers, workstation_code=SEED_WORKSTATION_CODE
    )
    headers["Idempotency-Key"] = new_idempotency_key()

    response = client.post(
        "/v1/sales/confirm",
        headers=headers,
        json={
            "cash_session_id": cash_session_id,
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

    headers = _authorization_header(client)
    cash_session_id = current_cash_session_id(
        client, headers=headers, workstation_code=SEED_WORKSTATION_CODE
    )
    headers["Idempotency-Key"] = new_idempotency_key()

    response = client.post(
        "/v1/sales/confirm",
        headers=headers,
        json={
            "cash_session_id": cash_session_id,
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
        operation = session.scalars(
            select(FinancialOperation).where(FinancialOperation.source_id == sale_record.id)
        ).one()
        entry = session.scalars(
            select(FinancialEntry).where(FinancialEntry.financial_operation_id == operation.id)
        ).one()

    assert payment_record.payment_method_code == "CARD"
    assert cash_movement_records == []
    assert operation.kind == "SALE_COLLECTION"
    assert operation.amount_due == entry.amount == Decimal("18.00")
    assert entry.payment_method_code == "CARD" and entry.direction == "IN"
    assert entry.state == "CONFIRMED" and entry.execution_mode == "ACCOUNTING_ONLY"
    assert entry.resolution_kind == "EXTERNAL_RECORDING"
    assert entry.resolution_reference == payment_record.id
    assert entry.cash_session_id == sale_record.cash_session_id


def test_sale_confirmation_supports_mixed_cash_and_card_payment(
    client: TestClient,
) -> None:
    _open_cash_session(client)

    headers = _authorization_header(client)
    cash_session_id = current_cash_session_id(
        client, headers=headers, workstation_code=SEED_WORKSTATION_CODE
    )
    headers["Idempotency-Key"] = new_idempotency_key()

    response = client.post(
        "/v1/sales/confirm",
        headers=headers,
        json={
            "cash_session_id": cash_session_id,
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
        assert (
            session.scalar(select(CashMovement).where(CashMovement.sale_id == sale_record.id))
            is None
        )
        operation = session.scalars(
            select(FinancialOperation).where(FinancialOperation.source_id == sale_record.id)
        ).one()
        entries = session.scalars(
            select(FinancialEntry).where(FinancialEntry.financial_operation_id == operation.id)
        ).all()

    assert [record.payment_method_code for record in payment_records] == ["CARD", "CASH"]
    assert [Decimal(str(record.applied_amount)) for record in payment_records] == [
        Decimal("10.00"),
        Decimal("14.00"),
    ]
    assert Decimal(str(payment_records[1].change_amount)) == Decimal("6.00")
    assert operation.kind == "SALE_COLLECTION" and operation.amount_due == Decimal("24.00")
    assert len(entries) == 2
    by_method = {entry.payment_method_code: entry for entry in entries}
    assert set(by_method) == {"CASH", "CARD"}
    assert by_method["CASH"].amount == Decimal("14.00")
    assert by_method["CASH"].tendered_amount == Decimal("20.00")
    assert by_method["CASH"].change_amount == Decimal("6.00")
    assert by_method["CASH"].execution_mode == "LOCAL"
    assert by_method["CARD"].amount == Decimal("10.00")
    assert by_method["CARD"].execution_mode == "ACCOUNTING_ONLY"
    assert by_method["CARD"].resolution_reference == payment_records[0].id
    assert sum(entry.amount for entry in entries) == operation.amount_due
    for entry in entries:
        assert entry.state == "CONFIRMED" and entry.direction == "IN"
        assert entry.cash_session_id == sale_record.cash_session_id
        assert entry.branch_id == sale_record.branch_id
        assert entry.workstation_id == sale_record.workstation_id


def test_sale_confirmation_rejects_removed_other_payment_method(
    client: TestClient,
) -> None:
    _open_cash_session(client)

    headers = _authorization_header(client)
    cash_session_id = current_cash_session_id(
        client, headers=headers, workstation_code=SEED_WORKSTATION_CODE
    )
    headers["Idempotency-Key"] = new_idempotency_key()

    response = client.post(
        "/v1/sales/confirm",
        headers=headers,
        json={
            "cash_session_id": cash_session_id,
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
    assert response.json()["message"] == "Envía componentes reales de efectivo o tarjeta."
    with SessionLocal() as session:
        assert session.scalar(select(Sale.id)) is None
        assert session.scalar(select(SalePayment.id)) is None
        assert session.scalar(select(CashMovement.id)) is None
        assert (
            session.scalar(
                select(FinancialOperation.id).where(FinancialOperation.kind == "SALE_COLLECTION")
            )
            is None
        )


def test_sale_confirmation_rejects_insufficient_cash(client: TestClient) -> None:
    _open_cash_session(client)

    headers = _authorization_header(client)
    cash_session_id = current_cash_session_id(
        client, headers=headers, workstation_code=SEED_WORKSTATION_CODE
    )
    headers["Idempotency-Key"] = new_idempotency_key()

    response = client.post(
        "/v1/sales/confirm",
        headers=headers,
        json={
            "cash_session_id": cash_session_id,
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
    headers = _authorization_header(client)
    cash_session_id = "10000000-0000-4000-8000-000000000001"
    headers["Idempotency-Key"] = new_idempotency_key()

    response = client.post(
        "/v1/sales/confirm",
        headers=headers,
        json={
            "cash_session_id": cash_session_id,
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
