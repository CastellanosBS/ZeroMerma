from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy import select

from zeromerma_api.bootstrap.seed_local import (
    SEED_ADMIN_EMAIL,
    SEED_ADMIN_PASSWORD,
    SEED_BRANCH_CODE,
    SEED_USER_EMAIL,
    SEED_USER_PASSWORD,
)
from zeromerma_api.db.session import SessionLocal
from zeromerma_api.modules.audit.infrastructure.models import AuditLog
from zeromerma_api.modules.branches.infrastructure.models import Branch


def _login(client: TestClient, *, email: str, password: str) -> str:
    response = client.post("/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    return str(response.json()["access_token"])


def _admin_headers(client: TestClient) -> dict[str, str]:
    token = _login(client, email=SEED_ADMIN_EMAIL, password=SEED_ADMIN_PASSWORD)
    return {"Authorization": f"Bearer {token}"}


def _cashier_headers(client: TestClient) -> dict[str, str]:
    token = _login(client, email=SEED_USER_EMAIL, password=SEED_USER_PASSWORD)
    return {"Authorization": f"Bearer {token}"}


def _branch_id() -> str:
    with SessionLocal() as session:
        branch = session.execute(select(Branch).where(Branch.code == SEED_BRANCH_CODE)).scalar_one()
        return str(branch.id)


def test_admin_reports_list_definitions_metrics_and_filters(client: TestClient) -> None:
    response = client.get("/v1/admin/reports", headers=_admin_headers(client))

    assert response.status_code == 200
    payload = response.json()
    codes = {definition["code"] for definition in payload["definitions"]}
    assert "sales_summary_by_branch" in codes
    assert "user_access_summary" in codes
    assert "purchase_supplier_activity" in codes
    assert payload["backend_contract"]["preview_endpoint"] == (
        "POST /v1/admin/reports/{report_code}/preview"
    )
    assert payload["metrics"]["available_reports"] >= 8
    assert payload["metrics"]["pending_backend_reports"] >= 1
    assert payload["filter_options"]["categories"]

    filtered = client.get("/v1/admin/reports?category=control", headers=_admin_headers(client))
    assert filtered.status_code == 200
    assert all(definition["category"] == "control" for definition in filtered.json()["definitions"])


def test_admin_reports_rejects_pos_only_user(client: TestClient) -> None:
    response = client.get("/v1/admin/reports", headers=_cashier_headers(client))

    assert response.status_code == 403


def test_admin_report_preview_uses_backend_data_and_filters_branch(
    client: TestClient,
) -> None:
    branch_id = _branch_id()
    response = client.post(
        "/v1/admin/reports/user_access_summary/preview",
        headers=_admin_headers(client),
        json={"filters": {"branch_id": branch_id, "app_access": "POS"}},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["report_code"] == "user_access_summary"
    assert payload["summary_cards"]
    assert payload["columns"]
    assert payload["rows"]
    assert all("email" in row["cells"] for row in payload["rows"])
    assert payload["filters_applied"]["branch_id"] == branch_id


def test_admin_report_preview_validates_required_filters_and_unknown_code(
    client: TestClient,
) -> None:
    missing_filters = client.post(
        "/v1/admin/reports/sales_summary_by_branch/preview",
        headers=_admin_headers(client),
        json={"filters": {}},
    )
    assert missing_filters.status_code == 400

    unknown = client.post(
        "/v1/admin/reports/not_real/preview",
        headers=_admin_headers(client),
        json={"filters": {}},
    )
    assert unknown.status_code == 404

    unavailable = client.post(
        "/v1/admin/reports/purchase_supplier_activity/preview",
        headers=_admin_headers(client),
        json={"filters": {"date_from": "2026-05-01", "date_to": "2026-05-22"}},
    )
    assert unavailable.status_code == 409


def test_admin_report_export_returns_rows_and_audits_sensitive_export(
    client: TestClient,
) -> None:
    response = client.post(
        "/v1/admin/reports/user_access_summary/export",
        headers={**_admin_headers(client), "X-Request-ID": "report-export-test"},
        json={"format": "json", "filters": {"app_access": "BACKOFFICE"}},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["format"] == "json"
    assert payload["report_code"] == "user_access_summary"
    assert payload["total_rows"] == len(payload["rows"])

    with SessionLocal() as session:
        audit_event = session.execute(
            select(AuditLog).where(
                AuditLog.action == "admin.report.exported",
                AuditLog.resource_id == "user_access_summary",
            )
        ).scalar_one()

    assert audit_event.request_id == "report-export-test"
    assert audit_event.metadata_["is_sensitive"] is True
    assert audit_event.metadata_["row_count"] == payload["total_rows"]


def test_admin_report_export_rejects_unsupported_format(client: TestClient) -> None:
    response = client.post(
        "/v1/admin/reports/user_access_summary/export",
        headers=_admin_headers(client),
        json={"format": "pdf", "filters": {}},
    )

    assert response.status_code == 400
