from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import select

from zeromerma_api.bootstrap.seed_local import (
    SEED_PRODUCT_CLASS_PAN_DULCE_CODE,
    SEED_PRODUCT_COCA_355_CODE,
    SEED_PRODUCT_CONCHA_VAN_CODE,
    SEED_USER_EMAIL,
    SEED_USER_PASSWORD,
    SEED_WORKSTATION_CODE,
)
from zeromerma_api.db.session import SessionLocal
from zeromerma_api.modules.audit.infrastructure.models import AuditLog
from zeromerma_api.modules.catalog.infrastructure.models import Product, ProductClass
from zeromerma_api.modules.outbox.infrastructure.models import OutboxEvent
from zeromerma_api.modules.returns.infrastructure.models import SaleReturn, SaleReturnLine
from zeromerma_api.modules.sales.infrastructure.models import CashMovement, Sale


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


def _confirm_sale(client: TestClient) -> dict[str, object]:
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
                    "product_id": _get_product_id(SEED_PRODUCT_COCA_355_CODE),
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
    return response.json()


def _get_sale_detail(client: TestClient, sale_id: str) -> dict[str, object]:
    response = client.get(
        f"/v1/returns/sales/{sale_id}",
        params={"workstation_code": SEED_WORKSTATION_CODE},
        headers=_authorization_header(client),
    )
    assert response.status_code == 200
    return response.json()


def test_returns_bootstrap_search_and_sale_detail_show_returnable_quantities(
    client: TestClient,
) -> None:
    _open_cash_session(client)
    sale_payload = _confirm_sale(client)
    headers = _authorization_header(client)

    bootstrap_response = client.get(
        "/v1/returns/bootstrap",
        params={"workstation_code": SEED_WORKSTATION_CODE},
        headers=headers,
    )
    assert bootstrap_response.status_code == 200
    bootstrap_payload = bootstrap_response.json()
    assert bootstrap_payload["return_operations_allowed"] is True
    assert bootstrap_payload["default_scope"] == "CURRENT_SHIFT"
    assert bootstrap_payload["return_reasons"][0]["code"] == "CUSTOMER_REGRET"
    assert bootstrap_payload["refund_methods"][0]["code"] == "CASH"
    assert bootstrap_payload["refund_methods"][1]["is_enabled"] is False
    assert bootstrap_payload["return_controls"]["high_risk_requires_acknowledgement"] is True

    search_response = client.get(
        "/v1/returns/search-sales",
        params={
            "workstation_code": SEED_WORKSTATION_CODE,
            "scope": "CURRENT_SHIFT",
            "query": "TCK-",
        },
        headers=headers,
    )
    assert search_response.status_code == 200
    search_payload = search_response.json()
    assert len(search_payload["sales"]) == 1
    assert search_payload["sales"][0]["id"] == sale_payload["id"]
    assert search_payload["sales"][0]["has_returnable_quantity"] is True

    sale_detail = _get_sale_detail(client, str(sale_payload["id"]))
    assert sale_detail["folio"].startswith("TCK-")
    assert sale_detail["has_returnable_lines"] is True
    assert len(sale_detail["lines"]) == 2
    assert all(
        Decimal(str(line["already_returned_quantity"])) == Decimal("0.000")
        for line in sale_detail["lines"]
    )


def test_returns_search_sales_supports_date_range_filters(client: TestClient) -> None:
    _open_cash_session(client)
    sale_payload = _confirm_sale(client)
    headers = _authorization_header(client)
    with SessionLocal() as session:
        sale = session.execute(select(Sale).where(Sale.id == sale_payload["id"])).scalar_one()
        sale.confirmed_at = datetime(2026, 4, 10, 18, 0, tzinfo=UTC)
        session.commit()

    excluded_response = client.get(
        "/v1/returns/search-sales",
        params={
            "workstation_code": SEED_WORKSTATION_CODE,
            "scope": "RECENT",
            "date_from": "2026-04-11",
            "date_to": "2026-04-12",
        },
        headers=headers,
    )
    assert excluded_response.status_code == 200
    assert excluded_response.json()["sales"] == []

    included_response = client.get(
        "/v1/returns/search-sales",
        params={
            "workstation_code": SEED_WORKSTATION_CODE,
            "scope": "CURRENT_SHIFT",
            "date_from": "2026-04-10",
            "date_to": "2026-04-10",
        },
        headers=headers,
    )
    assert included_response.status_code == 200
    assert len(included_response.json()["sales"]) == 1
    assert included_response.json()["sales"][0]["id"] == sale_payload["id"]


def test_product_direct_return_commits_refund_and_writes_audit_and_outbox(
    client: TestClient,
) -> None:
    _open_cash_session(client)
    sale_payload = _confirm_sale(client)
    sale_detail = _get_sale_detail(client, str(sale_payload["id"]))
    product_direct_line = next(
        line for line in sale_detail["lines"] if line["capture_mode"] == "PRODUCT_DIRECT"
    )

    response = client.post(
        "/v1/returns/commit",
        headers={
            **_authorization_header(client),
            "X-Request-ID": "returns-product-direct",
        },
        json={
            "workstation_code": SEED_WORKSTATION_CODE,
            "original_sale_id": sale_payload["id"],
            "reason_code": "WRONG_ITEM",
            "refund_method_code": "CASH",
            "notes": "Cliente devolvio refresco",
            "lines": [
                {
                    "original_sale_line_id": product_direct_line["id"],
                    "returned_quantity": "1.000",
                    "disposition_code": "RESTOCK_COUNTER",
                }
            ],
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["folio"].startswith("DEV-")
    assert Decimal(str(payload["total_refund_amount"])) == Decimal("18.00")
    assert payload["lines"][0]["disposition_code"] == "RESTOCK_COUNTER"

    reread_response = client.get(
        f"/v1/returns/{payload['id']}",
        params={"workstation_code": SEED_WORKSTATION_CODE},
        headers=_authorization_header(client),
    )
    assert reread_response.status_code == 200
    assert reread_response.json()["id"] == payload["id"]

    updated_sale_detail = _get_sale_detail(client, str(sale_payload["id"]))
    updated_direct_line = next(
        line for line in updated_sale_detail["lines"] if line["id"] == product_direct_line["id"]
    )
    assert Decimal(str(updated_direct_line["already_returned_quantity"])) == Decimal("1.000")
    assert Decimal(str(updated_direct_line["remaining_returnable_quantity"])) == Decimal("0.000")

    with SessionLocal() as session:
        return_record = session.execute(
            select(SaleReturn).where(SaleReturn.id == payload["id"])
        ).scalar_one()
        return_line = session.execute(
            select(SaleReturnLine).where(SaleReturnLine.sale_return_id == return_record.id)
        ).scalar_one()
        cash_movement = session.execute(
            select(CashMovement).where(
                CashMovement.sale_id == sale_payload["id"],
                CashMovement.movement_type == "SALE_RETURN_REFUND",
            )
        ).scalar_one()
        audit_record = session.execute(
            select(AuditLog).where(
                AuditLog.action == "sale_return.committed",
                AuditLog.resource_id == str(return_record.id),
            )
        ).scalar_one()
        outbox_event = session.execute(
            select(OutboxEvent).where(
                OutboxEvent.aggregate_id == str(return_record.id),
                OutboxEvent.event_name == "sale_return.committed.v1",
            )
        ).scalar_one()

    assert Decimal(str(return_line.refund_line_total_amount)) == Decimal("18.00")
    assert cash_movement.direction == "OUT"
    assert Decimal(str(cash_movement.amount)) == Decimal("18.00")
    assert audit_record.request_id == "returns-product-direct"
    assert outbox_event.payload["original_sale_id"] == str(sale_payload["id"])
    assert return_record.reason_code == "WRONG_ITEM"
    assert payload["reason_code"] == "WRONG_ITEM"


def test_class_capture_return_requires_exact_product_and_blocks_over_return(
    client: TestClient,
) -> None:
    _open_cash_session(client)
    sale_payload = _confirm_sale(client)
    sale_detail = _get_sale_detail(client, str(sale_payload["id"]))
    class_capture_line = next(
        line for line in sale_detail["lines"] if line["capture_mode"] == "CLASS_CAPTURE"
    )

    missing_product_response = client.post(
        "/v1/returns/commit",
        headers=_authorization_header(client),
        json={
            "workstation_code": SEED_WORKSTATION_CODE,
            "original_sale_id": sale_payload["id"],
            "reason_code": "QUALITY_ISSUE",
            "refund_method_code": "CASH",
            "lines": [
                {
                    "original_sale_line_id": class_capture_line["id"],
                    "returned_quantity": "1.000",
                    "disposition_code": "SEND_TO_WASTE",
                }
            ],
        },
    )
    assert missing_product_response.status_code == 400
    assert "producto exacto" in missing_product_response.json()["detail"]

    valid_response = client.post(
        "/v1/returns/commit",
        headers=_authorization_header(client),
        json={
            "workstation_code": SEED_WORKSTATION_CODE,
            "original_sale_id": sale_payload["id"],
            "reason_code": "QUALITY_ISSUE",
            "refund_method_code": "CASH",
            "lines": [
                {
                    "original_sale_line_id": class_capture_line["id"],
                    "returned_quantity": "1.000",
                    "disposition_code": "RESTOCK_BACKROOM",
                    "exact_product_id": _get_product_id(SEED_PRODUCT_CONCHA_VAN_CODE),
                }
            ],
        },
    )
    assert valid_response.status_code == 201

    over_return_response = client.post(
        "/v1/returns/commit",
        headers=_authorization_header(client),
        json={
            "workstation_code": SEED_WORKSTATION_CODE,
            "original_sale_id": sale_payload["id"],
            "reason_code": "QUALITY_ISSUE",
            "refund_method_code": "CASH",
            "lines": [
                {
                    "original_sale_line_id": class_capture_line["id"],
                    "returned_quantity": "2.000",
                    "disposition_code": "RESTOCK_COUNTER",
                    "exact_product_id": _get_product_id(SEED_PRODUCT_CONCHA_VAN_CODE),
                }
            ],
        },
    )
    assert over_return_response.status_code == 400
    assert "supera" in over_return_response.json()["detail"]


def test_class_capture_line_allows_returning_only_remaining_quantity(
    client: TestClient,
) -> None:
    _open_cash_session(client)
    sale_payload = _confirm_sale(client)
    sale_detail = _get_sale_detail(client, str(sale_payload["id"]))
    class_capture_line = next(
        line for line in sale_detail["lines"] if line["capture_mode"] == "CLASS_CAPTURE"
    )
    exact_product_id = _get_product_id(SEED_PRODUCT_CONCHA_VAN_CODE)

    first_response = client.post(
        "/v1/returns/commit",
        headers=_authorization_header(client),
        json={
            "workstation_code": SEED_WORKSTATION_CODE,
            "original_sale_id": sale_payload["id"],
            "reason_code": "DAMAGED_ON_DELIVERY",
            "refund_method_code": "CASH",
            "lines": [
                {
                    "original_sale_line_id": class_capture_line["id"],
                    "returned_quantity": "1.000",
                    "disposition_code": "RESTOCK_COUNTER",
                    "exact_product_id": exact_product_id,
                }
            ],
        },
    )
    assert first_response.status_code == 201

    second_response = client.post(
        "/v1/returns/commit",
        headers=_authorization_header(client),
        json={
            "workstation_code": SEED_WORKSTATION_CODE,
            "original_sale_id": sale_payload["id"],
            "reason_code": "DAMAGED_ON_DELIVERY",
            "refund_method_code": "CASH",
            "lines": [
                {
                    "original_sale_line_id": class_capture_line["id"],
                    "returned_quantity": "1.000",
                    "disposition_code": "RESTOCK_COUNTER",
                    "exact_product_id": exact_product_id,
                }
            ],
        },
    )
    assert second_response.status_code == 201

    updated_sale_detail = _get_sale_detail(client, str(sale_payload["id"]))
    updated_class_line = next(
        line for line in updated_sale_detail["lines"] if line["id"] == class_capture_line["id"]
    )
    assert Decimal(str(updated_class_line["already_returned_quantity"])) == Decimal("2.000")
    assert Decimal(str(updated_class_line["remaining_returnable_quantity"])) == Decimal("0.000")


def test_return_requires_reason_and_valid_refund_method(client: TestClient) -> None:
    _open_cash_session(client)
    sale_payload = _confirm_sale(client)
    sale_detail = _get_sale_detail(client, str(sale_payload["id"]))
    product_direct_line = next(
        line for line in sale_detail["lines"] if line["capture_mode"] == "PRODUCT_DIRECT"
    )

    missing_reason_response = client.post(
        "/v1/returns/commit",
        headers=_authorization_header(client),
        json={
            "workstation_code": SEED_WORKSTATION_CODE,
            "original_sale_id": sale_payload["id"],
            "reason_code": " ",
            "refund_method_code": "CASH",
            "lines": [
                {
                    "original_sale_line_id": product_direct_line["id"],
                    "returned_quantity": "1.000",
                    "disposition_code": "RESTOCK_COUNTER",
                }
            ],
        },
    )
    assert missing_reason_response.status_code == 400
    assert "motivo" in missing_reason_response.json()["detail"].lower()

    invalid_refund_method_response = client.post(
        "/v1/returns/commit",
        headers=_authorization_header(client),
        json={
            "workstation_code": SEED_WORKSTATION_CODE,
            "original_sale_id": sale_payload["id"],
            "reason_code": "WRONG_ITEM",
            "refund_method_code": "CARD",
            "lines": [
                {
                    "original_sale_line_id": product_direct_line["id"],
                    "returned_quantity": "1.000",
                    "disposition_code": "RESTOCK_COUNTER",
                }
            ],
        },
    )
    assert invalid_refund_method_response.status_code == 400
    assert "tarjeta" in invalid_refund_method_response.json()["detail"].lower()


def test_old_sale_return_requires_acknowledgement_and_prepares_backoffice_review(
    client: TestClient,
) -> None:
    _open_cash_session(client)
    sale_payload = _confirm_sale(client)
    sale_detail = _get_sale_detail(client, str(sale_payload["id"]))
    product_direct_line = next(
        line for line in sale_detail["lines"] if line["capture_mode"] == "PRODUCT_DIRECT"
    )

    with SessionLocal() as session:
        sale = session.execute(select(Sale).where(Sale.id == sale_payload["id"])).scalar_one()
        sale.confirmed_at = datetime.now(tz=UTC) - timedelta(days=10)
        session.commit()

    blocked_response = client.post(
        "/v1/returns/commit",
        headers={
            **_authorization_header(client),
            "X-Request-ID": "returns-high-risk-blocked",
        },
        json={
            "workstation_code": SEED_WORKSTATION_CODE,
            "original_sale_id": sale_payload["id"],
            "reason_code": "QUALITY_ISSUE",
            "refund_method_code": "CASH",
            "high_risk_acknowledged": False,
            "lines": [
                {
                    "original_sale_line_id": product_direct_line["id"],
                    "returned_quantity": "1.000",
                    "disposition_code": "RESTOCK_COUNTER",
                }
            ],
        },
    )
    assert blocked_response.status_code == 400
    assert "alto riesgo" in blocked_response.json()["detail"].lower()

    allowed_response = client.post(
        "/v1/returns/commit",
        headers={
            **_authorization_header(client),
            "X-Request-ID": "returns-high-risk-confirmed",
        },
        json={
            "workstation_code": SEED_WORKSTATION_CODE,
            "original_sale_id": sale_payload["id"],
            "reason_code": "QUALITY_ISSUE",
            "refund_method_code": "CASH",
            "high_risk_acknowledged": True,
            "lines": [
                {
                    "original_sale_line_id": product_direct_line["id"],
                    "returned_quantity": "1.000",
                    "disposition_code": "RESTOCK_COUNTER",
                }
            ],
        },
    )
    assert allowed_response.status_code == 201

    with SessionLocal() as session:
        sale_return = session.execute(
            select(SaleReturn).where(SaleReturn.id == allowed_response.json()["id"])
        ).scalar_one()
        alert_audit = session.execute(
            select(AuditLog).where(
                AuditLog.action == "sale_return.backoffice_review_requested",
                AuditLog.resource_id == str(sale_return.id),
            )
        ).scalar_one()
        alert_outbox = session.execute(
            select(OutboxEvent).where(
                OutboxEvent.aggregate_id == str(sale_return.id),
                OutboxEvent.event_name == "sale_return.backoffice_review_requested.v1",
            )
        ).scalar_one()

    assert alert_audit.request_id == "returns-high-risk-confirmed"
    assert alert_outbox.payload["notification_target"] == "backoffice"

    detail_response = client.get(
        f"/v1/returns/{allowed_response.json()['id']}",
        params={"workstation_code": SEED_WORKSTATION_CODE},
        headers=_authorization_header(client),
    )
    assert detail_response.status_code == 200
    detail_payload = detail_response.json()
    assert detail_payload["audit_summary"]["backoffice_notification"]["status"] == "PENDING"
    assert detail_payload["audit_summary"]["backoffice_notification"]["label"] == (
        "Revision de backoffice"
    )


def test_returns_history_and_detail_expose_safe_audit_summary(client: TestClient) -> None:
    _open_cash_session(client)
    sale_payload = _confirm_sale(client)
    sale_detail = _get_sale_detail(client, str(sale_payload["id"]))
    product_direct_line = next(
        line for line in sale_detail["lines"] if line["capture_mode"] == "PRODUCT_DIRECT"
    )

    create_response = client.post(
        "/v1/returns/commit",
        headers={
            **_authorization_header(client),
            "X-Request-ID": "returns-history-audit",
        },
        json={
            "workstation_code": SEED_WORKSTATION_CODE,
            "original_sale_id": sale_payload["id"],
            "reason_code": "WRONG_ITEM",
            "refund_method_code": "CASH",
            "notes": "Cliente devolvio refresco",
            "lines": [
                {
                    "original_sale_line_id": product_direct_line["id"],
                    "returned_quantity": "1.000",
                    "disposition_code": "RESTOCK_COUNTER",
                }
            ],
        },
    )
    assert create_response.status_code == 201
    created_payload = create_response.json()

    history_response = client.get(
        "/v1/returns/history",
        params={
            "workstation_code": SEED_WORKSTATION_CODE,
            "scope": "CURRENT_SHIFT",
            "query": created_payload["folio"],
            "reason_code": "WRONG_ITEM",
        },
        headers=_authorization_header(client),
    )
    assert history_response.status_code == 200
    history_payload = history_response.json()
    assert history_payload["scope"] == "CURRENT_SHIFT"
    assert history_payload["available_users"][0]["value"]
    assert history_payload["available_reasons"][0]["value"]
    assert len(history_payload["records"]) == 1
    assert history_payload["records"][0]["id"] == created_payload["id"]
    assert history_payload["records"][0]["branch_code"] == "MAIN"
    assert history_payload["records"][0]["workstation_code"] == SEED_WORKSTATION_CODE
    assert history_payload["records"][0]["reason_code"] == "WRONG_ITEM"

    detail_response = client.get(
        f"/v1/returns/{created_payload['id']}",
        params={"workstation_code": SEED_WORKSTATION_CODE},
        headers=_authorization_header(client),
    )
    assert detail_response.status_code == 200
    detail_payload = detail_response.json()
    assert detail_payload["audit_summary"]["created_by"]["email"] == SEED_USER_EMAIL
    assert detail_payload["audit_summary"]["confirmed_by"]["full_name"] == "Main Branch Cashier"
    assert detail_payload["audit_summary"]["reason_label"] == "Producto incorrecto"
    assert detail_payload["audit_summary"]["notes"] == "Cliente devolvio refresco"
    assert detail_payload["audit_summary"]["backoffice_notification"] is None
