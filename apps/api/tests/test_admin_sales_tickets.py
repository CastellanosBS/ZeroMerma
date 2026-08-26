from __future__ import annotations

from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import select

from zeromerma_api.bootstrap.seed_local import (
    SEED_ADMIN_EMAIL,
    SEED_ADMIN_PASSWORD,
    SEED_PRODUCT_CLASS_PAN_DULCE_CODE,
    SEED_PRODUCT_COCA_355_CODE,
    SEED_USER_EMAIL,
    SEED_USER_PASSWORD,
    SEED_WORKSTATION_CODE,
)
from zeromerma_api.db.session import SessionLocal
from zeromerma_api.modules.audit.infrastructure.models import AuditLog
from zeromerma_api.modules.catalog.infrastructure.models import Product, ProductClass


def _login(client: TestClient, *, email: str, password: str) -> str:
    response = client.post("/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    return str(response.json()["access_token"])


def _admin_headers(client: TestClient) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {_login(client, email=SEED_ADMIN_EMAIL, password=SEED_ADMIN_PASSWORD)}"
    }


def _cashier_headers(client: TestClient) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {_login(client, email=SEED_USER_EMAIL, password=SEED_USER_PASSWORD)}"
    }


def _open_cash_session(client: TestClient) -> None:
    response = client.post(
        "/v1/cash-sessions/open",
        headers=_cashier_headers(client),
        json={"workstation_code": SEED_WORKSTATION_CODE, "opening_amount": "150.00"},
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


def _confirm_sale(client: TestClient, *, payment_method_code: str = "CASH") -> dict[str, object]:
    tendered_amount = "100.00" if payment_method_code == "CASH" else "42.00"
    response = client.post(
        "/v1/sales/confirm",
        headers=_cashier_headers(client),
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
                    "payment_method_code": payment_method_code,
                    "tendered_amount": tendered_amount,
                }
            ],
        },
    )
    assert response.status_code == 201
    return response.json()


def test_admin_sales_tickets_list_supports_filters_and_metrics(client: TestClient) -> None:
    _open_cash_session(client)
    sale_payload = _confirm_sale(client)
    headers = _admin_headers(client)

    list_response = client.get(
        "/v1/admin/sales/tickets",
        headers=headers,
        params={
            "branch_id": sale_payload["branch_id"],
            "cashier_id": sale_payload["operator_id"],
            "payment_method": "CASH",
            "status": "CONFIRMED",
            "date_from": "2020-01-01T00:00:00Z",
            "date_to": "2999-01-01T00:00:00Z",
        },
    )

    assert list_response.status_code == 200
    payload = list_response.json()
    assert payload["is_backend_connected"] is True
    assert payload["total"] >= 1
    assert Decimal(str(payload["metrics"]["total_sales_amount"])) >= Decimal("42.00")
    assert Decimal(str(payload["metrics"]["cash_amount"])) >= Decimal("42.00")
    assert payload["metrics"]["ticket_count"] >= 1
    assert payload["filter_options"]["branches"]
    assert payload["filter_options"]["workstations"]
    assert payload["filter_options"]["cashiers"]

    ticket = next(item for item in payload["items"] if item["id"] == sale_payload["id"])
    assert ticket["folio"].startswith("TCK-")
    assert ticket["branch_name"] == sale_payload["branch_name"]
    assert ticket["cashier_name"] == sale_payload["operator_full_name"]
    assert ticket["payment_methods_label"] == "CASH"
    assert ticket["status"] == "CONFIRMED"

    search_response = client.get(
        "/v1/admin/sales/tickets",
        headers=headers,
        params={"search": ticket["folio"]},
    )
    assert search_response.status_code == 200
    assert any(item["id"] == sale_payload["id"] for item in search_response.json()["items"])


def test_admin_sales_ticket_detail_reprint_and_related_returns(client: TestClient) -> None:
    _open_cash_session(client)
    sale_payload = _confirm_sale(client)
    cashier_headers = _cashier_headers(client)
    admin_headers = {**_admin_headers(client), "X-Request-ID": "admin-ticket-reprint"}

    sale_return_source_response = client.get(
        f"/v1/returns/sales/{sale_payload['id']}",
        params={"workstation_code": SEED_WORKSTATION_CODE},
        headers=cashier_headers,
    )
    assert sale_return_source_response.status_code == 200
    product_direct_line_id = sale_return_source_response.json()["lines"][1]["id"]

    return_response = client.post(
        "/v1/returns/commit",
        headers=cashier_headers,
        json={
            "workstation_code": SEED_WORKSTATION_CODE,
            "original_sale_id": sale_payload["id"],
            "reason_code": "WRONG_ITEM",
            "refund_method_code": "CASH",
            "lines": [
                {
                    "original_sale_line_id": product_direct_line_id,
                    "returned_quantity": "1.000",
                    "disposition_code": "RESTOCK_COUNTER",
                }
            ],
        },
    )
    assert return_response.status_code == 201

    detail_response = client.get(
        f"/v1/admin/sales/tickets/{sale_payload['id']}",
        headers=admin_headers,
    )

    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert detail["overview"]["folio"].startswith("TCK-")
    assert detail["overview"]["status"] == "PARTIALLY_RETURNED"
    assert detail["overview"]["return_count"] == 1
    assert len(detail["lines"]) == 2
    assert detail["lines"][0]["capture_mode"] == "CLASS_CAPTURE"
    assert len(detail["payments"]) == 1
    assert detail["payments"][0]["payment_method_code"] == "CASH"
    assert detail["related_documents"][0]["document_type"] == "return"
    assert detail["printable_ticket"]["can_reprint"] is True

    reprint_response = client.post(
        f"/v1/admin/sales/tickets/{sale_payload['id']}/reprint",
        headers=admin_headers,
    )
    assert reprint_response.status_code == 200

    with SessionLocal() as session:
        audit_record = session.execute(
            select(AuditLog).where(
                AuditLog.action == "ticket.reprinted",
                AuditLog.resource_id == sale_payload["id"],
                AuditLog.request_id == "admin-ticket-reprint",
            )
        ).scalar_one()

    assert audit_record.metadata_["source"] == "backoffice"
    assert audit_record.metadata_["folio"].startswith("TCK-")


def test_admin_sales_tickets_require_backoffice_surface(client: TestClient) -> None:
    response = client.get("/v1/admin/sales/tickets", headers=_cashier_headers(client))

    assert response.status_code == 403
    assert response.json()["detail"] == "Backoffice access is required."
