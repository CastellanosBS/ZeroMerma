import sqlite3
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from threading import Event
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from zeromerma_api.local_hardware.runtime import LocalHardwareBridge, PairedDevice
from zeromerma_api.local_hardware.server import create_bridge_app
from zeromerma_api.modules.hardware.domain.commands import (
    DeviceCommand,
    DeviceCommandResult,
    sign_device_command,
)
from zeromerma_api.modules.tickets.application.receipt_schemas import OperationalReceiptView

KEY = b"test-only-local-hardware-pairing-key-256bits"
ORIGIN = "https://pos.example.test"


class Adapter:
    def __init__(self):
        self.calls = []
        self.fail = False
        self.entered = None
        self.release = None

    def execute(self, command, *, timeout_seconds):
        assert timeout_seconds == 5
        self.calls.append(command.id)
        if self.entered is not None:
            self.entered.set()
            assert self.release.wait(5)
        if self.fail:
            raise TimeoutError("PRIVATE_DRIVER_RESPONSE")
        return DeviceCommandResult(
            command_id=command.id, state="OPENED", evidence_reference="pulse-1"
        )


@pytest.fixture
def environment(tmp_path):
    adapter = Adapter()
    device = PairedDevice(
        device_id=uuid4(),
        branch_id=uuid4(),
        workstation_id=uuid4(),
        binding_version=1,
        environment="SANDBOX",
        origin=ORIGIN,
        capabilities=frozenset({"OPEN_DRAWER"}),
        adapter=adapter,
    )
    path = tmp_path / "spool.sqlite3"
    bridge = LocalHardwareBridge(path, KEY, [device])
    command = DeviceCommand(
        id=uuid4(),
        kind="OPEN_DRAWER",
        branch_id=device.branch_id,
        workstation_id=device.workstation_id,
        device_id=device.device_id,
        binding_version=1,
        environment="SANDBOX",
        origin=ORIGIN,
        cash_entry_id=uuid4(),
    )
    yield bridge, device, adapter, command, path
    bridge.close()


def test_replay_and_changed_payload_never_repeat_the_physical_cause(environment):
    bridge, _, adapter, command, _ = environment
    grant = sign_device_command(command, KEY)
    result = bridge.submit(grant, origin=ORIGIN)
    assert result.state == "OPENED"
    assert bridge.submit(grant, origin=ORIGIN) == result
    assert adapter.calls == [command.id]
    changed = command.model_copy(update={"cash_entry_id": uuid4()})
    with pytest.raises(ValueError, match="identity"):
        bridge.submit(sign_device_command(changed, KEY), origin=ORIGIN)
    assert len(adapter.calls) == 1


def test_status_never_submits_an_unknown_command_or_repeats_a_completed_one(environment):
    bridge, _, adapter, command, path = environment
    grant = sign_device_command(command, KEY)
    assert bridge.status(grant, origin=ORIGIN).state == "UNKNOWN"
    with sqlite3.connect(path) as connection:
        assert connection.execute("SELECT count(*) FROM device_jobs").fetchone()[0] == 0
    assert adapter.calls == []
    assert bridge.submit(grant, origin=ORIGIN).state == "OPENED"
    assert bridge.status(grant, origin=ORIGIN).state == "OPENED"
    assert adapter.calls == [command.id]


@pytest.mark.parametrize(
    "reported,evidence,expected",
    [
        ("PRINTED", None, "UNKNOWN"),
        ("PRINTED", "proof-1", "PRINTED"),
        ("ACKNOWLEDGED", None, "ACKNOWLEDGED"),
        ("UNAVAILABLE", None, "UNAVAILABLE"),
    ],
)
def test_print_requires_device_evidence_and_spool_never_contains_receipt_data(
    environment, tmp_path, reported, evidence, expected
):
    _, device, _, original, _ = environment

    class Printer:
        def execute(self, command, *, timeout_seconds):
            return DeviceCommandResult(
                command_id=command.id, state=reported, evidence_reference=evidence
            )

    printer = replace(device, capabilities=frozenset({"PRINT"}), adapter=Printer())
    receipt = OperationalReceiptView.model_validate(
        {
            "source_kind": "SALE",
            "source_id": uuid4(),
            "folio": "TCK-UNIQUE",
            "occurred_at": datetime.now(UTC),
            "context": {
                "branch_id": device.branch_id,
                "branch_code": "MAIN",
                "branch_name": "PRIVATE_BRANCH",
                "timezone": "America/Hermosillo",
                "workstation_id": device.workstation_id,
                "workstation_code": "POS-01",
                "workstation_name": "PRIVATE_STATION",
                "actor_id": uuid4(),
                "actor_name": "PRIVATE_PERSON",
                "cash_session_id": uuid4(),
            },
            "subtotal_amount": "1.00",
            "discount_amount": "0.00",
            "total_amount": "1.00",
            "change_amount": "0.00",
            "lines": [],
            "payments": [],
        }
    )
    command = DeviceCommand.model_validate(
        {**original.model_dump(), "kind": "PRINT", "cash_entry_id": None, "receipt": receipt}
    )
    path = tmp_path / "printer.sqlite3"
    bridge = LocalHardwareBridge(path, KEY, [printer])
    try:
        grant = sign_device_command(command, KEY)
        assert bridge.submit(grant, origin=ORIGIN).state == expected
        assert bridge.status(grant, origin=ORIGIN).state == expected
        assert b"PRIVATE_" not in path.read_bytes()
    finally:
        bridge.close()


@pytest.mark.parametrize(
    "field,value",
    [
        ("workstation_id", uuid4()),
        ("branch_id", uuid4()),
        ("binding_version", 2),
        ("device_id", uuid4()),
        ("environment", "PRODUCTION"),
        ("origin", "https://evil.test"),
    ],
)
def test_signed_commands_still_require_exact_pairing(environment, field, value):
    bridge, _, adapter, command, _ = environment
    grant = sign_device_command(command.model_copy(update={field: value}), KEY)
    with pytest.raises(ValueError, match="pairing"):
        bridge.submit(grant, origin=ORIGIN)
    assert adapter.calls == []


def test_signature_expiry_and_origin_are_checked_before_claim(environment):
    bridge, _, adapter, command, _ = environment
    grant = sign_device_command(command, KEY)
    for value in [
        grant.model_copy(update={"signature": "0" * 64}),
        grant.model_copy(update={"expires_at": datetime.now(UTC) - timedelta(seconds=1)}),
    ]:
        with pytest.raises(ValueError, match="authorization"):
            bridge.submit(value, origin=ORIGIN)
    with pytest.raises(ValueError, match="pairing"):
        bridge.submit(grant, origin="https://evil.test")
    assert adapter.calls == []


def test_timeout_and_process_restart_preserve_unknown_without_resending(environment):
    bridge, device, adapter, command, path = environment
    adapter.fail = True
    grant = sign_device_command(command, KEY)
    assert bridge.submit(grant, origin=ORIGIN).state == "UNKNOWN"
    assert bridge.submit(grant, origin=ORIGIN).state == "UNKNOWN"
    assert adapter.calls == [command.id]
    bridge.close()
    with sqlite3.connect(path) as connection:
        connection.execute("UPDATE device_jobs SET state='PROCESSING'")
    restarted = LocalHardwareBridge(path, KEY, [device])
    try:
        assert restarted.submit(grant, origin=ORIGIN).state == "UNKNOWN"
        assert adapter.calls == [command.id]
        assert b"PRIVATE_DRIVER_RESPONSE" not in path.read_bytes()
    finally:
        restarted.close()


def test_one_process_owns_each_durable_spool(environment):
    _, device, _, _, path = environment
    with pytest.raises(ValueError, match="Another bridge"):
        LocalHardwareBridge(path, KEY, [device])


def test_fifo_is_per_device_and_does_not_block_another_device(environment, tmp_path):
    first, device, adapter, command, _ = environment
    first.close()
    second_adapter = Adapter()
    second_device = replace(device, device_id=uuid4(), adapter=second_adapter)
    bridge = LocalHardwareBridge(tmp_path / "two.sqlite3", KEY, [device, second_device])
    adapter.entered, adapter.release = Event(), Event()
    next_command = command.model_copy(update={"id": uuid4(), "cash_entry_id": uuid4()})
    last_command = command.model_copy(update={"id": uuid4(), "cash_entry_id": uuid4()})
    try:
        with ThreadPoolExecutor() as executor:
            pending = executor.submit(
                bridge.submit, sign_device_command(command, KEY), origin=ORIGIN
            )
            assert adapter.entered.wait(5)
            assert (
                bridge.submit(sign_device_command(command, KEY), origin=ORIGIN).state
                == "PROCESSING"
            )
            assert (
                bridge.submit(sign_device_command(next_command, KEY), origin=ORIGIN).state
                == "QUEUED"
            )
            independent = command.model_copy(
                update={"id": uuid4(), "device_id": second_device.device_id}
            )
            assert (
                bridge.submit(sign_device_command(independent, KEY), origin=ORIGIN).state
                == "OPENED"
            )
            adapter.release.set()
            assert pending.result(timeout=5).state == "OPENED"
        assert (
            bridge.submit(sign_device_command(last_command, KEY), origin=ORIGIN).state == "QUEUED"
        )
        assert (
            bridge.submit(sign_device_command(next_command, KEY), origin=ORIGIN).state == "OPENED"
        )
        assert (
            bridge.submit(sign_device_command(last_command, KEY), origin=ORIGIN).state == "OPENED"
        )
        assert adapter.calls == [command.id, next_command.id, last_command.id]
    finally:
        adapter.release.set()
        bridge.close()


def test_transport_rejects_other_origins_and_malformed_commands_without_echoing_them(environment):
    bridge, _, adapter, command, _ = environment
    with TestClient(
        create_bridge_app(bridge, [ORIGIN]),
        base_url="http://127.0.0.1",
        client=("127.0.0.1", 12345),
    ) as client:
        assert client.get("/health").status_code == 403
        assert (
            client.get("/health", headers={"Origin": ORIGIN}).json()["physical_action_performed"]
            is False
        )
        denied = client.post(
            "/commands",
            headers={"Origin": "https://evil.test"},
            json=sign_device_command(command, KEY).model_dump(mode="json"),
        )
        assert denied.status_code == 403
        malformed = client.post("/commands", headers={"Origin": ORIGIN}, json={"secret": "PRIVATE"})
        assert malformed.status_code == 422
        assert "PRIVATE" not in malformed.text
        assert adapter.calls == []
