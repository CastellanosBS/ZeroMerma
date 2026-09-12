from __future__ import annotations

from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import select

from zeromerma_api.bootstrap.seed_local import (
    SEED_ADMIN_EMAIL,
    SEED_ADMIN_PASSWORD,
    SEED_PRODUCT_COCA_355_CODE,
    SEED_USER_EMAIL,
    SEED_USER_PASSWORD,
    SEED_WORKSTATION_CODE,
)
from zeromerma_api.db.session import SessionLocal
from zeromerma_api.modules.catalog.infrastructure.models import Product
from zeromerma_api.modules.payments.infrastructure.models import OperationalPaymentCategory


def _login(client: TestClient, *, email: str, password: str) -> str:
    response = client.post("/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.json()
    return str(response.json()["access_token"])


def _admin_headers(client: TestClient) -> dict[str, str]:
    token = _login(client, email=SEED_ADMIN_EMAIL, password=SEED_ADMIN_PASSWORD)
    return {"Authorization": f"Bearer {token}"}


def _cashier_headers(client: TestClient) -> dict[str, str]:
    token = _login(client, email=SEED_USER_EMAIL, password=SEED_USER_PASSWORD)
    return {"Authorization": f"Bearer {token}"}


def _open_cash_session(client: TestClient, *, opening_amount: str = "150.00") -> dict[str, object]:
    response = client.post(
        "/v1/cash-sessions/open",
        headers=_cashier_headers(client),
        json={"workstation_code": SEED_WORKSTATION_CODE, "opening_amount": opening_amount},
    )
    assert response.status_code == 201
    return response.json()


def _get_product_id(code: str) -> str:
    with SessionLocal() as session:
        product = session.execute(select(Product).where(Product.code == code)).scalar_one()
    return str(product.id)


def _get_category_code(code: str) -> str:
    with SessionLocal() as session:
        category = session.execute(
            select(OperationalPaymentCategory).where(OperationalPaymentCategory.code == code)
        ).scalar_one()
    return str(category.code)


def _confirm_direct_sale(client: TestClient) -> dict[str, object]:
    response = client.post(
        "/v1/sales/confirm",
        headers=_cashier_headers(client),
        json={
            "workstation_code": SEED_WORKSTATION_CODE,
            "lines": [
                {
                    "capture_mode": "PRODUCT_DIRECT",
                    "product_id": _get_product_id(SEED_PRODUCT_COCA_355_CODE),
                    "quantity": "1",
                }
            ],
            "payments": [{"payment_method_code": "CASH", "tendered_amount": "100.00"}],
        },
    )
    assert response.status_code == 201
    return response.json()


def _commit_return(client: TestClient, *, sale_id: str) -> dict[str, object]:
    source_response = client.get(
        f"/v1/returns/sales/{sale_id}",
        params={"workstation_code": SEED_WORKSTATION_CODE},
        headers=_cashier_headers(client),
    )
    assert source_response.status_code == 200
    line_id = source_response.json()["lines"][0]["id"]

    response = client.post(
        "/v1/returns/commit",
        headers=_cashier_headers(client),
        json={
            "workstation_code": SEED_WORKSTATION_CODE,
            "original_sale_id": sale_id,
            "reason_code": "WRONG_ITEM",
            "refund_method_code": "CASH",
            "lines": [
                {
                    "original_sale_line_id": line_id,
                    "returned_quantity": "1.000",
                    "disposition_code": "RESTOCK_COUNTER",
                }
            ],
        },
    )
    assert response.status_code == 201
    return response.json()


def _create_operational_payment(client: TestClient) -> dict[str, object]:
    response = client.post(
        "/v1/payments",
        headers=_cashier_headers(client),
        json={
            "workstation_code": SEED_WORKSTATION_CODE,
            "payee_name": "Proveedor de turno",
            "concept": "Compra menor",
            "category_code": _get_category_code("SUPPLIER"),
            "payment_method_code": "CASH",
            "total_amount": "25.00",
            "notes": "Salida auditada del turno",
        },
    )
    assert response.status_code == 201
    return response.json()


def _commit_cash_close_with_difference(client: TestClient) -> dict[str, object]:
    summary_response = client.get(
        "/v1/cash-close/summary",
        params={"workstation_code": SEED_WORKSTATION_CODE},
        headers=_cashier_headers(client),
    )
    assert summary_response.status_code == 200
    expected_cash = Decimal(str(summary_response.json()["expected_cash_amount"]))
    counted_cash = expected_cash + Decimal("5.00")
    response = client.post(
        "/v1/cash-close/commit",
        headers=_cashier_headers(client),
        json={
            "workstation_code": SEED_WORKSTATION_CODE,
            "counter_empty_confirmed": True,
            "counted_payment_methods": [
                {"payment_method_code": "CASH", "counted_amount": str(counted_cash)}
            ],
        },
    )
    assert response.status_code == 200, response.json()
    return response.json()


def _prepare_closed_cash_cut(client: TestClient) -> dict[str, object]:
    _open_cash_session(client)
    sale_payload = _confirm_direct_sale(client)
    payment_payload = _create_operational_payment(client)
    return_payload = _commit_return(client, sale_id=str(sale_payload["id"]))
    close_payload = _commit_cash_close_with_difference(client)
    return {
        "close": close_payload,
        "payment": payment_payload,
        "return": return_payload,
        "sale": sale_payload,
    }


def test_admin_cash_cuts_list_supports_filters_metrics_and_open_sessions(
    client: TestClient,
) -> None:
    prepared = _prepare_closed_cash_cut(client)
    close_payload = prepared["close"]
    sale_payload = prepared["sale"]
    headers = _admin_headers(client)

    list_response = client.get(
        "/v1/admin/cash-cuts",
        headers=headers,
        params={
            "branch_id": sale_payload["branch_id"],
            "cashier_id": sale_payload["operator_id"],
            "difference_state": "WITH_DIFFERENCE",
            "payment_method": "CASH",
            "status": "CLOSED_WITH_DIFFERENCE",
            "date_from": "2020-01-01T00:00:00Z",
            "date_to": "2999-01-01T00:00:00Z",
        },
    )

    assert list_response.status_code == 200
    payload = list_response.json()
    assert payload["is_backend_connected"] is True
    assert payload["total"] >= 1
    assert payload["metrics"]["closed_cuts_count"] >= 1
    assert Decimal(str(payload["metrics"]["net_difference_amount"])) >= Decimal("5.00")
    assert payload["metrics"]["cuts_with_difference_count"] >= 1
    assert Decimal(str(payload["metrics"]["operational_payments_amount"])) >= Decimal("25.00")
    assert payload["filter_options"]["branches"]
    assert payload["filter_options"]["workstations"]
    assert payload["filter_options"]["cashiers"]

    cash_session_id = close_payload["cash_session"]["id"]
    item = next(entry for entry in payload["items"] if entry["cash_session_id"] == cash_session_id)
    assert item["folio"].startswith("CC-")
    assert item["status"] == "CLOSED_WITH_DIFFERENCE"
    assert item["difference_state"] == "OVER"
    assert item["has_refunds"] is True
    assert item["has_operational_payments"] is True
    assert item["payment_methods_summary"] == "CASH"

    search_response = client.get(
        "/v1/admin/cash-cuts",
        headers=headers,
        params={"search": item["folio"]},
    )
    assert search_response.status_code == 200
    assert any(
        entry["cash_session_id"] == cash_session_id for entry in search_response.json()["items"]
    )

    _open_cash_session(client)
    open_response = client.get(
        "/v1/admin/cash-cuts",
        headers=headers,
        params={"status": "OPEN"},
    )
    assert open_response.status_code == 200
    assert any(entry["status"] == "OPEN" for entry in open_response.json()["items"])


def test_admin_cash_cut_detail_exposes_financial_and_related_context(
    client: TestClient,
) -> None:
    prepared = _prepare_closed_cash_cut(client)
    close_payload = prepared["close"]
    headers = _admin_headers(client)
    cash_session_id = close_payload["cash_session"]["id"]

    detail_response = client.get(f"/v1/admin/cash-cuts/{cash_session_id}", headers=headers)

    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert detail["overview"]["folio"].startswith("CC-")
    assert detail["overview"]["status"] == "CLOSED_WITH_DIFFERENCE"
    assert detail["overview"]["cash_session_id"] == cash_session_id
    assert detail["expected_vs_counted"]["difference_state"] == "OVER"
    assert Decimal(str(detail["expected_vs_counted"]["difference_amount"])) == Decimal("5.00")
    assert detail["payment_breakdown"][0]["payment_method_code"] == "CASH"
    assert detail["included_tickets"][0]["folio"].startswith("TCK-")
    assert detail["returns_refunds"][0]["folio"].startswith("DEV-")
    assert detail["operational_payments"][0]["folio"].startswith("PAG-")
    assert detail["denomination_count"]["is_supported"] is False
    assert detail["available_actions"]["can_remote_close"] is False
    assert detail["available_actions"]["can_export_report"] is False
    assert any(document["document_type"] == "ticket" for document in detail["related_documents"])
    assert any(event["event_code"] == "CASH_SESSION_CLOSED" for event in detail["audit_timeline"])


def test_admin_cash_cuts_require_backoffice_surface(client: TestClient) -> None:
    response = client.get("/v1/admin/cash-cuts", headers=_cashier_headers(client))

    assert response.status_code == 403
    assert response.json()["message"] == "Backoffice access is required."
