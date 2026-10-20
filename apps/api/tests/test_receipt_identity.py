"""Branch-owned merchant identity is frozen at issuance, including durable print recovery."""

import hashlib
import json
from uuid import UUID

import pytest
from sqlalchemy import select
from test_admin_returns_corrections import _commit_return
from test_hardware_commands import KEY, hardware  # noqa: F401
from test_order_lifecycle import _create, _setup
from test_tickets_module import _authorization_header, _confirm_sale, _open_cash_session

from zeromerma_api.bootstrap.seed_local import SEED_BRANCH_CODE, SEED_WORKSTATION_CODE
from zeromerma_api.db.session import SessionLocal
from zeromerma_api.local_hardware.runtime import LocalHardwareBridge, PairedDevice
from zeromerma_api.modules.branches.infrastructure.models import Branch
from zeromerma_api.modules.hardware.application.services import HardwareService
from zeromerma_api.modules.hardware.domain.commands import (
    DeviceCommandResult,
    SignedDeviceCommand,
    command_digest,
    verify_device_command,
)
from zeromerma_api.modules.hardware.presentation.router import hardware_service
from zeromerma_api.modules.orders.infrastructure.models import CustomerOrderPayment
from zeromerma_api.modules.tickets.application import receipts
from zeromerma_api.modules.tickets.application.receipt_seller import snapshot_receipt_seller
from zeromerma_api.modules.tickets.infrastructure.models import ReceiptSnapshot
from zeromerma_api.testing.authorization import owner_headers
from zeromerma_api.testing.idempotency import new_idempotency_key

PROFILE = {
    "receipt_commercial_name": "Synthetic Bakery",
    "receipt_business_descriptor": "Bread and pastries",
    "address_line": "Synthetic Plaza 10",
    "city": "Hermosillo",
    "state": "Sonora",
    "postal_code": "83249",
    "country": "Mexico",
}
ADDRESS = "Synthetic Plaza 10, Hermosillo, Sonora, 83249, Mexico"


def _configure(client, *, branch_id=None, **changes):
    if branch_id is None:
        with SessionLocal() as session:
            branch_id = session.scalar(select(Branch.id).where(Branch.code == SEED_BRANCH_CODE))
    result = client.patch(
        f"/v1/admin/branches/{branch_id}", headers=owner_headers(), json={**PROFILE, **changes}
    )
    assert result.status_code == 200, result.text
    return branch_id


def _stored_receipt(source_kind, source_id):
    with SessionLocal() as session:
        row = session.scalars(
            select(ReceiptSnapshot).where(
                ReceiptSnapshot.source_kind == source_kind,
                ReceiptSnapshot.source_id == UUID(str(source_id)),
            )
        ).one()
        document = receipts.read_receipt(session, source_kind, UUID(str(source_id)))
        assert document is not None
        return row.document, row.document_sha256, document.model_dump(mode="json")


@pytest.mark.parametrize("source_kind", ["SALE", "ORDER_PAYMENT", "RETURN"])
def test_each_economic_producer_freezes_branch_profile_without_inventing_fiscal_identity(
    client, source_kind
):
    _configure(client)
    if source_kind == "ORDER_PAYMENT":
        headers, context, payload = _setup(client)
        order, _ = _create(client, headers, context, payload)
        with SessionLocal() as session:
            source_id = session.scalars(
                select(CustomerOrderPayment.id).where(
                    CustomerOrderPayment.customer_order_id == UUID(order["id"])
                )
            ).one()
    else:
        _open_cash_session(client)
        sale = _confirm_sale(client)
        source_id = sale["id"]
        if source_kind == "RETURN":
            source_id = _commit_return(client, str(source_id))["id"]

    before = _stored_receipt(source_kind, source_id)
    seller = before[0]["seller"]
    assert seller == {
        "commercial_name": "Synthetic Bakery",
        "business_descriptor": "Bread and pastries",
        "address": ADDRESS,
        "legal_name": None,
        "tax_identifier": None,
        "fiscal_regime": None,
        "configuration_status": "UNCONFIGURED",
    }
    assert before[0]["fiscal_document"] is False
    _configure(
        client, receipt_commercial_name="Renamed Synthetic Bakery", address_line="New Plaza 20"
    )
    assert _stored_receipt(source_kind, source_id) == before
    if source_kind == "ORDER_PAYMENT":
        response = client.post(
            f"/v1/orders/{order['id']}/payments",
            headers={**headers, "Idempotency-Key": new_idempotency_key()},
            json={**context, "payments": [{"payment_method_code": "CASH", "amount": "1.00"}]},
        )
        assert response.status_code == 200, response.text
        with SessionLocal() as session:
            next_id = session.scalars(
                select(CustomerOrderPayment.id).where(
                    CustomerOrderPayment.customer_order_id == UUID(order["id"]),
                    CustomerOrderPayment.id != source_id,
                )
            ).one()
    else:
        next_sale = _confirm_sale(client)
        next_id = next_sale["id"]
        if source_kind == "RETURN":
            next_id = _commit_return(client, str(next_id))["id"]
    latest = _stored_receipt(source_kind, next_id)[0]
    assert latest["seller"]["commercial_name"] == "Renamed Synthetic Bakery"
    assert latest["seller"]["address"] == "New Plaza 20, Hermosillo, Sonora, 83249, Mexico"


def test_profile_is_explicit_per_branch_and_never_inherited_from_another_branch(client):
    branch_id = _configure(client)
    with SessionLocal() as session:
        other_id = session.scalars(select(Branch.id).where(Branch.id != branch_id)).first()
        assert snapshot_receipt_seller(session, other_id).commercial_name is None
        assert snapshot_receipt_seller(session, other_id).business_descriptor is None
    _configure(client, branch_id=other_id, receipt_commercial_name="Other Synthetic Bakery")
    with SessionLocal() as session:
        assert snapshot_receipt_seller(session, branch_id).commercial_name == "Synthetic Bakery"
        assert (
            snapshot_receipt_seller(session, other_id).commercial_name == "Other Synthetic Bakery"
        )


@pytest.mark.parametrize("tampered", [False, True])
def test_historical_raw_snapshot_hash_is_checked_before_optional_defaults_and_print_recovery(
    client, monkeypatch, tampered
):
    def insert_historical_document(session, document):
        raw = document.model_dump(mode="json")
        # This optional schema-1 field may be absent in persisted source documents.
        raw.pop("related_document_folio")
        assert "commercial_name" not in raw["seller"]
        assert "business_descriptor" not in raw["seller"]
        digest = hashlib.sha256(
            json.dumps(raw, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        if tampered:
            raw["seller"]["address"] = "Unauthorized replacement"
        session.add(
            ReceiptSnapshot(
                branch_id=document.context.branch_id,
                workstation_id=document.context.workstation_id,
                source_kind=document.source_kind,
                source_id=document.source_id,
                document=raw,
                document_sha256=digest,
            )
        )
        session.flush()

    monkeypatch.setattr(receipts, "persist_receipt", insert_historical_document)
    _open_cash_session(client)
    sale = _confirm_sale(client)
    if tampered:
        rejected = client.get(
            f"/v1/tickets/{sale['id']}",
            params={"workstation_code": SEED_WORKSTATION_CODE},
            headers=_authorization_header(client),
        )
        assert rejected.status_code == 409, rejected.text
        assert "integrity check failed" in rejected.text
        return
    before = _stored_receipt("SALE", sale["id"])
    assert "related_document_folio" not in before[0]
    assert before[2]["related_document_folio"] is None
    headers = {**_authorization_header(client), "Idempotency-Key": new_idempotency_key()}
    path = f"/v1/tickets/receipts/SALE/{sale['id']}/print-request"
    payload = {"workstation_code": SEED_WORKSTATION_CODE, "reason": "Historical document copy"}
    first = client.post(path, headers=headers, json=payload)
    assert first.status_code == 200, first.text
    _configure(client)
    replay = client.post(path, headers=headers, json=payload)
    assert replay.status_code == 200, replay.text
    assert replay.headers["Idempotency-Replayed"] == "true"
    assert replay.json() == first.json()
    recovered = client.get(
        f"/v1/tickets/receipts/SALE/{sale['id']}/print-requests/{headers['Idempotency-Key']}",
        params={"workstation_code": SEED_WORKSTATION_CODE},
        headers=headers,
    )
    assert recovered.status_code == 200, recovered.text
    assert recovered.json() == first.json()
    assert _stored_receipt("SALE", sale["id"]) == before


def test_historical_device_command_keeps_its_digest_and_never_prints_twice_after_recovery(
    client, request, tmp_path
):
    sale, bindings, registrations, _, headers = request.getfixturevalue("hardware")
    client.app.dependency_overrides[hardware_service] = lambda: HardwareService(registrations)
    key = new_idempotency_key()
    issued = client.post(
        "/v1/hardware/commands",
        headers={**headers, "Idempotency-Key": key},
        json={
            "workstation_code": SEED_WORKSTATION_CODE,
            "binding_id": str(bindings["PRINTER"]),
            "kind": "PRINT",
            "receipt_source_kind": "SALE",
            "receipt_source_id": sale["id"],
        },
    )
    assert issued.status_code == 200, issued.text
    raw = issued.json()["grant"]["command"]
    assert "commercial_name" not in raw["receipt"]["seller"]
    assert "business_descriptor" not in raw["receipt"]["seller"]
    original_digest = hashlib.sha256(
        json.dumps(raw, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    grant = SignedDeviceCommand.model_validate(issued.json()["grant"])
    assert command_digest(grant.command) == original_digest
    verify_device_command(grant, KEY)
    calls = []

    class TestOnlyPrinter:
        def execute(self, command, *, timeout_seconds):
            calls.append(command.id)
            return DeviceCommandResult(
                command_id=command.id, state="PRINTED", evidence_reference="test-proof"
            )

    device = PairedDevice(
        device_id=grant.command.device_id,
        branch_id=grant.command.branch_id,
        workstation_id=grant.command.workstation_id,
        binding_version=1,
        environment="SANDBOX",
        origin=grant.command.origin,
        capabilities=frozenset({"PRINT"}),
        adapter=TestOnlyPrinter(),
    )
    path = tmp_path / "historical-jobs.sqlite3"
    bridge = LocalHardwareBridge(path, KEY, [device])
    try:
        assert bridge.submit(grant, origin=device.origin).state == "PRINTED"
    finally:
        bridge.close()
    _configure(client)
    recovered = client.get(
        f"/v1/hardware/commands/by-key/{key}",
        params={"workstation_code": SEED_WORKSTATION_CODE},
        headers=headers,
    )
    assert recovered.status_code == 200, recovered.text
    assert recovered.json()["grant"]["command"] == raw
    renewed = SignedDeviceCommand.model_validate(recovered.json()["grant"])
    assert command_digest(renewed.command) == original_digest
    bridge = LocalHardwareBridge(path, KEY, [device])
    try:
        assert bridge.status(renewed, origin=device.origin).state == "PRINTED"
        assert bridge.submit(renewed, origin=device.origin).state == "PRINTED"
        assert calls == [grant.command.id]
    finally:
        bridge.close()
