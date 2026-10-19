"""Device authorization uses real PostgreSQL and a test-only paired adapter registration."""

from dataclasses import replace
from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, select
from test_tickets_module import _authorization_header, _confirm_sale, _open_cash_session

from zeromerma_api.bootstrap.seed_local import SEED_WORKSTATION_CODE
from zeromerma_api.db.session import SessionLocal
from zeromerma_api.modules.audit.infrastructure.models import AuditLog
from zeromerma_api.modules.financial_ledger.infrastructure.models import (
    FinancialEntry,
    FinancialOperation,
)
from zeromerma_api.modules.hardware.application.services import (
    HardwareService,
    VerifiedHardwareRegistration,
)
from zeromerma_api.modules.hardware.domain.commands import (
    SignedDeviceCommand,
    verify_device_command,
)
from zeromerma_api.modules.hardware.infrastructure.models import (
    HardwareCommandIntent,
    HardwareDeviceBinding,
)
from zeromerma_api.modules.hardware.presentation.router import hardware_service
from zeromerma_api.testing.idempotency import new_idempotency_key

KEY = b"test-only-hardware-api-pairing-key-256bits"


@pytest.fixture
def hardware(client):
    _open_cash_session(client)
    sale = _confirm_sale(client)
    bindings = {}
    registrations = {}
    with SessionLocal.begin() as session:
        for kind in ("PRINTER", "DRAWER"):
            binding = HardwareDeviceBinding(
                id=uuid4(),
                branch_id=UUID(sale["branch_id"]),
                workstation_id=UUID(sale["workstation_id"]),
                kind=kind,
                adapter_code="TEST_ONLY",
                adapter_version="1",
                environment="SANDBOX",
                origin="https://pos.example.test",
                certification_evidence_id=uuid4(),
                version=1,
                is_active=True,
            )
            session.add(binding)
            registrations[binding.id] = VerifiedHardwareRegistration(
                adapter_code=binding.adapter_code,
                adapter_version=binding.adapter_version,
                certification_evidence_id=binding.certification_evidence_id,
                environment=binding.environment,
                origin=binding.origin,
                pairing_key=KEY,
            )
            bindings[kind] = binding.id
        entry_id = session.scalar(
            select(FinancialEntry.id)
            .join(FinancialOperation)
            .where(
                FinancialOperation.source_id == UUID(sale["id"]),
                FinancialOperation.kind == "SALE_COLLECTION",
                FinancialEntry.payment_method_code == "CASH",
            )
        )
    headers = _authorization_header(client)
    yield sale, bindings, registrations, entry_id, headers
    client.app.dependency_overrides.pop(hardware_service, None)


def _request(client, headers, body, key=None):
    return client.post(
        "/v1/hardware/commands",
        json=body,
        headers={**headers, "Idempotency-Key": key or new_idempotency_key()},
    )


def test_default_runtime_never_claims_certified_hardware_or_issues_a_grant(client, hardware):
    sale, bindings, _, _, headers = hardware
    response = client.get(
        f"/v1/hardware/bootstrap?workstation_code={SEED_WORKSTATION_CODE}", headers=headers
    )
    assert response.status_code == 200, response.text
    assert response.json()["manual_drawer_opening_enabled"] is False
    assert response.json()["browser_print_fallback"] == "UNCERTIFIED"
    assert all(not item["enabled"] for item in response.json()["devices"])
    denied = _request(
        client,
        headers,
        {
            "workstation_code": SEED_WORKSTATION_CODE,
            "binding_id": str(bindings["PRINTER"]),
            "kind": "PRINT",
            "receipt_source_kind": "SALE",
            "receipt_source_id": sale["id"],
        },
    )
    assert denied.status_code == 503, denied.text
    with SessionLocal() as session:
        assert session.scalar(select(func.count(HardwareCommandIntent.id))) == 0


def test_print_authorization_replays_without_economics_and_renews_same_causal_job(client, hardware):
    sale, bindings, registrations, _, headers = hardware
    client.app.dependency_overrides[hardware_service] = lambda: HardwareService(registrations)
    body = {
        "workstation_code": SEED_WORKSTATION_CODE,
        "binding_id": str(bindings["PRINTER"]),
        "kind": "PRINT",
        "receipt_source_kind": "SALE",
        "receipt_source_id": sale["id"],
    }
    key = new_idempotency_key()
    first = _request(client, headers, body, key)
    assert first.status_code == 200, first.text
    replay = _request(client, headers, body, key)
    assert replay.status_code == 200, replay.text
    assert replay.json() == first.json()
    assert replay.headers["Idempotency-Replayed"] == "true"
    verify_device_command(SignedDeviceCommand.model_validate(first.json()["grant"]), KEY)
    assert first.json()["physical_outcome"] == "NOT_CONFIRMED"
    assert first.json()["grant"]["command"]["cash_entry_id"] is None
    recovered = client.get(
        f"/v1/hardware/commands/by-key/{key}?workstation_code={SEED_WORKSTATION_CODE}",
        headers=headers,
    )
    assert recovered.status_code == 200, recovered.text
    assert recovered.headers["Idempotency-Replayed"] == "true"
    assert recovered.json()["command_id"] == first.json()["command_id"]
    assert recovered.json()["grant"]["command"] == first.json()["grant"]["command"]
    verify_device_command(SignedDeviceCommand.model_validate(recovered.json()["grant"]), KEY)
    unknown = client.get(
        f"/v1/hardware/commands/by-key/{new_idempotency_key()}?workstation_code={SEED_WORKSTATION_CODE}",
        headers=headers,
    )
    assert unknown.status_code == 409, unknown.text
    renewed = client.get(
        f"/v1/hardware/commands/{first.json()['command_id']}/authorization"
        f"?workstation_code={SEED_WORKSTATION_CODE}",
        headers=headers,
    )
    assert renewed.status_code == 200, renewed.text
    assert renewed.json()["grant"]["command"] == first.json()["grant"]["command"]
    with SessionLocal() as session:
        assert session.scalar(select(func.count(HardwareCommandIntent.id))) == 1
        assert (
            session.scalar(
                select(func.count(AuditLog.id)).where(
                    AuditLog.action == "hardware.command_requested"
                )
            )
            == 1
        )
    with SessionLocal.begin() as session:
        session.get(HardwareDeviceBinding, bindings["PRINTER"]).version = 2
    denied = client.get(
        f"/v1/hardware/commands/{first.json()['command_id']}/authorization"
        f"?workstation_code={SEED_WORKSTATION_CODE}",
        headers=headers,
    )
    assert denied.status_code == 409, denied.text


def test_drawer_identity_is_unique_per_confirmed_cash_effect_even_with_new_keys(client, hardware):
    _, bindings, registrations, entry_id, headers = hardware
    client.app.dependency_overrides[hardware_service] = lambda: HardwareService(registrations)
    body = {
        "workstation_code": SEED_WORKSTATION_CODE,
        "binding_id": str(bindings["DRAWER"]),
        "kind": "OPEN_DRAWER",
        "cash_entry_id": str(entry_id),
    }
    first = _request(client, headers, body)
    assert first.status_code == 200, first.text
    second = _request(client, headers, body)
    assert second.status_code == 200, second.text
    assert second.json()["command_id"] == first.json()["command_id"]
    assert second.json()["grant"]["command"]["receipt"] is None
    with SessionLocal() as session:
        assert session.scalar(select(func.count(HardwareCommandIntent.id))) == 1
    missing = _request(client, headers, {**body, "cash_entry_id": None})
    assert missing.status_code == 422
    cannot_mix = _request(
        client, headers, {**body, "receipt_source_kind": "SALE", "receipt_source_id": str(uuid4())}
    )
    assert cannot_mix.status_code == 422


def test_gate_evidence_cannot_be_replaced_by_an_active_database_binding(client, hardware):
    sale, bindings, registrations, _, headers = hardware
    registrations[bindings["PRINTER"]] = replace(
        registrations[bindings["PRINTER"]], certification_evidence_id=uuid4()
    )
    client.app.dependency_overrides[hardware_service] = lambda: HardwareService(registrations)
    result = _request(
        client,
        headers,
        {
            "workstation_code": SEED_WORKSTATION_CODE,
            "binding_id": str(bindings["PRINTER"]),
            "kind": "PRINT",
            "receipt_source_kind": "SALE",
            "receipt_source_id": sale["id"],
        },
    )
    assert result.status_code == 503, result.text
