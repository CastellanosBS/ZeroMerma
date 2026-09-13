from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy import select

from zeromerma_api.bootstrap.seed_local import (
    SEED_PRODUCT_COCA_355_CODE,
    SEED_USER_EMAIL,
    SEED_USER_PASSWORD,
    SEED_WORKSTATION_CODE,
)
from zeromerma_api.db.session import SessionLocal
from zeromerma_api.modules.audit.infrastructure.models import AuditLog
from zeromerma_api.modules.cash_close.infrastructure.models import (
    CashSessionClose,
    FinancialReconciliation,
)
from zeromerma_api.modules.catalog.infrastructure.models import Product
from zeromerma_api.modules.outbox.infrastructure.models import OutboxEvent
from zeromerma_api.testing.authorization import owner_headers


def _login(client: TestClient, *, email: str, password: str) -> str:
    response = client.post("/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.json()
    return str(response.json()["access_token"])


def _admin_headers(client: TestClient) -> dict[str, str]:
    return owner_headers()


def _cashier_headers(client: TestClient) -> dict[str, str]:
    token = _login(client, email=SEED_USER_EMAIL, password=SEED_USER_PASSWORD)
    return {"Authorization": f"Bearer {token}"}


def _get_product_id(code: str) -> str:
    with SessionLocal() as session:
        product = session.execute(select(Product).where(Product.code == code)).scalar_one()
    return str(product.id)


def _open_cash_session(client: TestClient, *, opening_amount: str = "150.00") -> None:
    response = client.post(
        "/v1/cash-sessions/open",
        headers=_cashier_headers(client),
        json={
            "opening_amount": opening_amount,
            "workstation_code": SEED_WORKSTATION_CODE,
        },
    )
    assert response.status_code == 201, response.json()


def _confirm_direct_sale(client: TestClient) -> dict[str, object]:
    response = client.post(
        "/v1/sales/confirm",
        headers=_cashier_headers(client),
        json={
            "lines": [
                {
                    "capture_mode": "PRODUCT_DIRECT",
                    "product_id": _get_product_id(SEED_PRODUCT_COCA_355_CODE),
                    "quantity": "1",
                }
            ],
            "payments": [{"payment_method_code": "CASH", "tendered_amount": "100.00"}],
            "workstation_code": SEED_WORKSTATION_CODE,
        },
    )
    assert response.status_code == 201, response.json()
    return response.json()


def _commit_return(client: TestClient, *, sale_id: str) -> dict[str, object]:
    source_response = client.get(
        f"/v1/returns/sales/{sale_id}",
        params={"workstation_code": SEED_WORKSTATION_CODE},
        headers=_cashier_headers(client),
    )
    assert source_response.status_code == 200, source_response.json()
    line_id = source_response.json()["lines"][0]["id"]

    response = client.post(
        "/v1/returns/commit",
        headers=_cashier_headers(client),
        json={
            "lines": [
                {
                    "disposition_code": "RESTOCK_COUNTER",
                    "original_sale_line_id": line_id,
                    "returned_quantity": "1.000",
                }
            ],
            "original_sale_id": sale_id,
            "reason_code": "WRONG_ITEM",
            "refund_method_code": "CASH",
            "workstation_code": SEED_WORKSTATION_CODE,
        },
    )
    assert response.status_code == 201, response.json()
    return response.json()


def _commit_cash_close_with_difference(
    client: TestClient,
    *,
    difference: Decimal = Decimal("5.00"),
) -> dict[str, object]:
    summary_response = client.get(
        "/v1/cash-close/summary",
        params={"workstation_code": SEED_WORKSTATION_CODE},
        headers=_cashier_headers(client),
    )
    assert summary_response.status_code == 200, summary_response.json()
    expected_cash = Decimal(str(summary_response.json()["expected_cash_amount"]))
    counted_cash = expected_cash + difference
    response = client.post(
        "/v1/cash-close/commit",
        headers=_cashier_headers(client),
        json={
            "counter_empty_confirmed": True,
            "counted_payment_methods": [
                {"payment_method_code": "CASH", "counted_amount": str(counted_cash)}
            ],
            "workstation_code": SEED_WORKSTATION_CODE,
        },
    )
    assert response.status_code == 200, response.json()
    return response.json()


def _prepare_closed_cash_cut(client: TestClient) -> dict[str, object]:
    _open_cash_session(client)
    sale_payload = _confirm_direct_sale(client)
    return_payload = _commit_return(client, sale_id=str(sale_payload["id"]))
    close_payload = _commit_cash_close_with_difference(client)
    return {"close": close_payload, "return": return_payload, "sale": sale_payload}


def test_admin_reconciliation_lists_pending_cash_cut_discrepancies(
    client: TestClient,
) -> None:
    prepared = _prepare_closed_cash_cut(client)
    close_payload = prepared["close"]
    sale_payload = prepared["sale"]
    headers = _admin_headers(client)

    response = client.get(
        "/v1/admin/reconciliation",
        headers=headers,
        params={
            "branch_id": sale_payload["branch_id"],
            "cashier_id": sale_payload["operator_id"],
            "date_from": "2020-01-01T00:00:00Z",
            "date_to": "2999-01-01T00:00:00Z",
            "discrepancy_type": "OVERAGE",
            "payment_method": "CASH",
            "source_type": "CASH_CUT",
        },
    )

    assert response.status_code == 200, response.json()
    payload = response.json()
    assert payload["is_backend_connected"] is True
    assert payload["items"] == []
    assert payload["metrics"]["pending_count"] == 1
    assert Decimal(str(payload["metrics"]["net_difference_amount"])) == Decimal("5.00")
    assert payload["metrics"]["cash_pending_count"] == 1
    assert payload["filter_options"]["reason_codes"]
    assert payload["backend_contract"]["pending_endpoint"] == (
        "GET /v1/admin/reconciliation/pending"
    )

    pending = payload["pending_discrepancies"][0]
    assert pending["source_document_id"] == close_payload["id"]
    assert pending["source_reference"].startswith("CC-")
    assert pending["source_type"] == "CASH_CUT"
    assert pending["difference_direction"] == "OVERAGE"

    pending_response = client.get("/v1/admin/reconciliation/pending", headers=headers)
    assert pending_response.status_code == 200
    assert pending_response.json()["total"] == 1


def test_admin_reconciliation_can_create_review_resolve_and_keep_cut_immutable(
    client: TestClient,
) -> None:
    prepared = _prepare_closed_cash_cut(client)
    close_payload = prepared["close"]
    close_id = str(close_payload["id"])
    headers = _admin_headers(client)

    create_response = client.post(
        "/v1/admin/reconciliation",
        headers={**headers, "X-Request-ID": "reconciliation-test-create"},
        json={
            "evidence_note": "Foto de conteo en caja.",
            "final_status": "IN_REVIEW",
            "notes": "Diferencia identificada durante revision administrativa.",
            "reason_code": "COUNTING_ERROR",
            "source_document_id": close_id,
            "source_type": "CASH_CUT",
        },
    )

    assert create_response.status_code == 200, create_response.json()
    created = create_response.json()
    reconciliation_id = created["overview"]["id"]
    assert created["overview"]["folio"].startswith("CON-")
    assert created["overview"]["status"] == "IN_REVIEW"
    assert created["difference_breakdown"]["direction"] == "OVERAGE"
    assert created["source_document_context"]["source_route_hint"].startswith("/admin/cortes-caja")
    assert created["resolution"]["can_resolve"] is True
    assert created["available_actions"]["can_resolve"] is True
    assert created["evidence"]["has_evidence"] is True
    assert any(document["document_type"] == "TICKET" for document in created["related_documents"])

    duplicate_response = client.post(
        "/v1/admin/reconciliation",
        headers=headers,
        json={
            "final_status": "RECONCILED",
            "notes": "Intento duplicado.",
            "reason_code": "COUNTING_ERROR",
            "source_document_id": close_id,
            "source_type": "CASH_CUT",
        },
    )
    assert duplicate_response.status_code == 400

    resolve_response = client.post(
        f"/v1/admin/reconciliation/{reconciliation_id}/resolve",
        headers={**headers, "X-Request-ID": "reconciliation-test-resolve"},
        json={
            "evidence_note": "Conteo validado contra reporte impreso.",
            "notes": "Se documenta como sobrante aceptado.",
            "reason_code": "CASH_OVER",
        },
    )
    assert resolve_response.status_code == 200, resolve_response.json()
    resolved = resolve_response.json()
    assert resolved["overview"]["status"] == "RECONCILED"
    assert resolved["resolution"]["can_resolve"] is False
    assert resolved["resolution"]["resolution_reason"] == "Sobrante de efectivo"

    second_resolve_response = client.post(
        f"/v1/admin/reconciliation/{reconciliation_id}/resolve",
        headers=headers,
        json={
            "notes": "No debe permitir segunda resolucion.",
            "reason_code": "COUNTING_ERROR",
        },
    )
    assert second_resolve_response.status_code == 400

    list_response = client.get("/v1/admin/reconciliation", headers=headers)
    assert list_response.status_code == 200
    list_payload = list_response.json()
    assert list_payload["pending_discrepancies"] == []
    assert list_payload["metrics"]["reconciled_count"] == 1
    assert list_payload["metrics"]["with_evidence_count"] == 1

    cut_response = client.get(
        f"/v1/admin/cash-cuts/{close_payload['cash_session']['id']}",
        headers=headers,
    )
    assert cut_response.status_code == 200
    assert Decimal(str(cut_response.json()["expected_vs_counted"]["difference_amount"])) == Decimal(
        "5.00"
    )

    with SessionLocal() as session:
        close = session.get(CashSessionClose, UUID(close_id))
        reconciliation = session.get(FinancialReconciliation, UUID(reconciliation_id))
        audit_actions = set(session.execute(select(AuditLog.action)).scalars().all())
        outbox_events = set(session.execute(select(OutboxEvent.event_name)).scalars().all())

    assert close is not None
    assert close.cash_variance_amount == Decimal("5.00")
    assert reconciliation is not None
    assert reconciliation.status == "RECONCILED"
    assert "admin.financial_reconciliation.created" in audit_actions
    assert "admin.financial_reconciliation.resolved" in audit_actions
    assert "financial_reconciliation.created.v1" in outbox_events
    assert "financial_reconciliation.resolved.v1" in outbox_events


def test_admin_reconciliation_requires_reason_notes_and_backoffice_surface(
    client: TestClient,
) -> None:
    prepared = _prepare_closed_cash_cut(client)
    close_id = str(prepared["close"]["id"])

    cashier_response = client.get(
        "/v1/admin/reconciliation",
        headers=_cashier_headers(client),
    )
    assert cashier_response.status_code == 403
    assert cashier_response.json()["message"] == "This application surface is not authorized."

    other_without_note_response = client.post(
        "/v1/admin/reconciliation",
        headers=_admin_headers(client),
        json={
            "final_status": "RECONCILED",
            "reason_code": "OTHER",
            "source_document_id": close_id,
            "source_type": "CASH_CUT",
        },
    )
    assert other_without_note_response.status_code == 400
    assert "Notes are required" in other_without_note_response.json()["message"]
