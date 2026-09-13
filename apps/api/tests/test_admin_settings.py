from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy import select

from zeromerma_api.bootstrap.seed_local import (
    SEED_USER_EMAIL,
    SEED_USER_PASSWORD,
)
from zeromerma_api.db.session import SessionLocal
from zeromerma_api.modules.audit.infrastructure.models import AuditLog
from zeromerma_api.modules.configuration.infrastructure.models import (
    SystemSetting,
    SystemSettingHistory,
)
from zeromerma_api.testing.authorization import owner_headers


def _login(client: TestClient, *, email: str, password: str) -> str:
    response = client.post("/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    return str(response.json()["access_token"])


def _admin_headers(client: TestClient) -> dict[str, str]:
    return owner_headers()


def _cashier_headers(client: TestClient) -> dict[str, str]:
    token = _login(client, email=SEED_USER_EMAIL, password=SEED_USER_PASSWORD)
    return {"Authorization": f"Bearer {token}"}


def test_admin_settings_list_registry_metrics_and_filters(client: TestClient) -> None:
    response = client.get("/v1/admin/settings", headers=_admin_headers(client))

    assert response.status_code == 200
    payload = response.json()
    keys = {item["definition"]["key"] for item in payload["items"]}
    assert "general.business_name" in keys
    assert "cash.cash_opening_required" in keys
    assert "integrations.payment_terminal_status" in keys
    assert payload["backend_contract"]["scoped_overrides_supported"] is False
    assert payload["metrics"]["active_settings"] >= 20
    assert payload["metrics"]["sensitive_settings"] >= 1
    assert payload["filter_options"]["categories"]

    filtered = client.get("/v1/admin/settings?category=cash", headers=_admin_headers(client))
    assert filtered.status_code == 200
    assert all(item["definition"]["category"] == "cash" for item in filtered.json()["items"])


def test_admin_settings_rejects_pos_only_user(client: TestClient) -> None:
    response = client.get("/v1/admin/settings", headers=_cashier_headers(client))

    assert response.status_code == 403


def test_admin_setting_detail_shows_definition_value_and_empty_history(
    client: TestClient,
) -> None:
    response = client.get(
        "/v1/admin/settings/general.business_name",
        headers=_admin_headers(client),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["definition"]["key"] == "general.business_name"
    assert payload["value"]["effective_value"] == "ZeroMerma"
    assert payload["history"] == []
    assert "edit" in payload["available_actions"]


def test_admin_setting_update_validates_persists_history_and_audit(
    client: TestClient,
) -> None:
    response = client.patch(
        "/v1/admin/settings/general.business_name",
        headers={**_admin_headers(client), "X-Request-ID": "settings-update-test"},
        json={"value": "Panaderia Central", "change_note": "Brand default update"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["value"]["effective_value"] == "Panaderia Central"
    assert payload["history"][0]["old_value_masked"] == "ZeroMerma"
    assert payload["history"][0]["new_value_masked"] == "Panaderia Central"

    with SessionLocal() as session:
        setting = session.execute(
            select(SystemSetting).where(SystemSetting.key == "general.business_name")
        ).scalar_one()
        history = session.execute(
            select(SystemSettingHistory).where(
                SystemSettingHistory.setting_key == "general.business_name"
            )
        ).scalar_one()
        audit_event = session.execute(
            select(AuditLog).where(
                AuditLog.action == "admin.setting.updated",
                AuditLog.resource_id == "general.business_name",
            )
        ).scalar_one()

    assert setting.value == "Panaderia Central"
    assert history.change_note == "Brand default update"
    assert audit_event.request_id == "settings-update-test"
    assert audit_event.metadata_["module"] == "configuration"


def test_admin_setting_update_rejects_invalid_values_and_readonly(
    client: TestClient,
) -> None:
    invalid_enum = client.patch(
        "/v1/admin/settings/localization.default_currency",
        headers=_admin_headers(client),
        json={"value": "EUR"},
    )
    assert invalid_enum.status_code == 400

    invalid_range = client.patch(
        "/v1/admin/settings/pos.product_search_min_length",
        headers=_admin_headers(client),
        json={"value": 0},
    )
    assert invalid_range.status_code == 400

    readonly = client.patch(
        "/v1/admin/settings/cash.cash_opening_required",
        headers=_admin_headers(client),
        json={"value": False, "confirm_sensitive": True},
    )
    assert readonly.status_code == 409


def test_admin_setting_sensitive_update_requires_confirmation_and_masks(
    client: TestClient,
) -> None:
    missing_confirmation = client.patch(
        "/v1/admin/settings/cash.cash_difference_tolerance",
        headers=_admin_headers(client),
        json={"value": "75"},
    )
    assert missing_confirmation.status_code == 409

    response = client.patch(
        "/v1/admin/settings/cash.cash_difference_tolerance",
        headers=_admin_headers(client),
        json={"value": "75", "confirm_sensitive": True},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["definition"]["is_sensitive"] is True
    assert payload["value"]["effective_value"] == "valor sensible"
    assert payload["history"][0]["new_value_masked"] == "valor sensible"


def test_admin_setting_reset_restores_default_and_audits(client: TestClient) -> None:
    headers = _admin_headers(client)
    update = client.patch(
        "/v1/admin/settings/tickets.receipt_footer_text",
        headers=headers,
        json={"value": "Vuelve pronto"},
    )
    assert update.status_code == 200

    reset = client.post(
        "/v1/admin/settings/tickets.receipt_footer_text/reset",
        headers={**headers, "X-Request-ID": "settings-reset-test"},
        json={"change_note": "Back to default"},
    )

    assert reset.status_code == 200
    payload = reset.json()
    assert payload["value"]["effective_value"] == "Gracias por su compra."

    with SessionLocal() as session:
        setting = session.execute(
            select(SystemSetting).where(SystemSetting.key == "tickets.receipt_footer_text")
        ).scalar_one_or_none()
        audit_event = session.execute(
            select(AuditLog).where(
                AuditLog.action == "admin.setting.reset",
                AuditLog.resource_id == "tickets.receipt_footer_text",
            )
        ).scalar_one()

    assert setting is None
    assert audit_event.request_id == "settings-reset-test"
