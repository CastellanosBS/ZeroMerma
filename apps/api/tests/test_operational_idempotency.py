"""Physical document command acceptance against disposable PostgreSQL."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from decimal import Decimal
from threading import Barrier
from typing import Any
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from zeromerma_api.bootstrap.seed_local import (
    SEED_ALT_DESTINATION_BRANCH_CODE,
    SEED_DESTINATION_BRANCH_CODE,
    SEED_PRODUCT_CONCHA_VAN_CODE,
    SEED_USER_EMAIL,
    SEED_USER_PASSWORD,
    SEED_WORKSTATION_CODE,
)
from zeromerma_api.db.session import SessionLocal
from zeromerma_api.main import create_app
from zeromerma_api.modules.audit.infrastructure.models import AuditLog
from zeromerma_api.modules.branches.infrastructure.models import Branch, Workstation
from zeromerma_api.modules.catalog.infrastructure.models import Product
from zeromerma_api.modules.corrections.infrastructure.models import (
    CorrectionDocument,
    CorrectionDocumentLine,
)
from zeromerma_api.modules.idempotency.infrastructure.models import IdempotencyRecord
from zeromerma_api.modules.identity.infrastructure.models import User, UserBranchAssignment
from zeromerma_api.modules.inventory.infrastructure.models import (
    InventoryAdjustment,
    InventoryBalance,
    InventoryMovement,
)
from zeromerma_api.modules.operations.infrastructure.models import OperationDocument
from zeromerma_api.modules.outbox.application.service import OutboxWriter
from zeromerma_api.modules.outbox.infrastructure.models import OutboxEvent
from zeromerma_api.testing.authorization import owner_headers
from zeromerma_api.testing.idempotency import new_idempotency_key
from zeromerma_api.testing.sessions import login_headers
from zeromerma_api.testing.transfer_operators import transfer_cashier_email

PATHS = {
    "counter": (
        "/v1/operations/counter-transfer/commit",
        "/v1/operations/counter-transfer",
        "counter_transfer.commit",
    ),
    "pos-waste": ("/v1/operations/waste/commit", "/v1/operations/waste", "waste.commit"),
    "correction": ("/v1/corrections/commit", "/v1/corrections", "correction.commit"),
    "admin-waste": ("/v1/admin/waste", "/v1/admin/waste", "waste.commit"),
    "adjustment": (
        "/v1/admin/inventory/adjustments",
        "/v1/admin/inventory/adjustments",
        "inventory.adjust",
    ),
}


def _post(
    client: TestClient, kind: str, headers: dict[str, str], body: dict[str, Any], key: str
) -> Any:
    return client.post(PATHS[kind][0], headers={**headers, "Idempotency-Key": key}, json=body)


def _setup(client: TestClient, kind: str) -> tuple[dict[str, str], dict[str, Any]]:
    with SessionLocal() as session:
        product = str(
            session.scalars(
                select(Product.id).where(Product.code == SEED_PRODUCT_CONCHA_VAN_CODE)
            ).one()
        )
        branch = str(session.scalars(select(Branch.id).where(Branch.code == "MAIN")).one())
    if kind in {"adjustment", "admin-waste"}:
        headers = owner_headers()
        body = {
            "branch_id": branch,
            "product_id": product,
            "location_code": "BACKROOM",
            "quantity": "2.000",
            "notes": "Private physical command notes",
        }
        if kind == "adjustment":
            return headers, {**body, "adjustment_type": "INCREASE", "reason": "Physical count"}
        stock = _post(
            client,
            "adjustment",
            headers,
            {
                **body,
                "quantity": "10.000",
                "adjustment_type": "INCREASE",
                "reason": "Opening stock",
            },
            new_idempotency_key(),
        )
        assert stock.status_code == 201, stock.text
        return headers, {**body, "reason_code": "DAMAGED"}
    headers = login_headers(
        client,
        email=SEED_USER_EMAIL,
        password=SEED_USER_PASSWORD,
        audience="POS",
        workstation_code=SEED_WORKSTATION_CODE,
    )
    opened = client.post(
        "/v1/cash-sessions/open",
        headers={**headers, "Idempotency-Key": new_idempotency_key()},
        json={"workstation_code": SEED_WORKSTATION_CODE, "opening_amount": "0"},
    )
    assert opened.status_code == 201, opened.text
    body = {
        "workstation_code": SEED_WORKSTATION_CODE,
        "cash_session_id": opened.json()["id"],
        "notes": "Private physical command notes",
        "lines": [{"product_id": product, "quantity": "4.000"}],
    }
    if kind == "counter":
        return headers, body
    if kind == "pos-waste":
        return headers, {**body, "source_bucket_code": "BACKROOM", "reason_code": "DAMAGED"}
    target = _post(client, "counter", headers, body, new_idempotency_key())
    assert target.status_code == 201, target.text
    return headers, {
        **body,
        "target_document_id": target.json()["id"],
        "reason_code": "WRONG_QUANTITY",
        "lines": [
            {
                "product_id": product,
                "target_line_id": target.json()["lines"][0]["id"],
                "delta_quantity": "-2.000",
            }
        ],
    }


def _recover(
    client: TestClient, kind: str, headers: dict[str, str], body: dict[str, Any], key: str
) -> Any:
    query = {
        name: body[name]
        for name in ("branch_id", "workstation_code", "cash_session_id")
        if name in body
    }
    return client.get(f"{PATHS[kind][1]}/confirmations/{key}", headers=headers, params=query)


def _counts() -> dict[str, Any]:
    with SessionLocal() as session:
        counts: dict[str, Any] = {
            model.__tablename__: int(session.scalar(select(func.count()).select_from(model)) or 0)
            for model in (
                OperationDocument,
                CorrectionDocument,
                CorrectionDocumentLine,
                InventoryAdjustment,
                InventoryMovement,
                InventoryBalance,
                AuditLog,
                OutboxEvent,
                IdempotencyRecord,
            )
        }
        counts["stock"] = sorted(
            (str(row.id), str(row.quantity_on_hand))
            for row in session.scalars(select(InventoryBalance)).all()
        )
        return counts


@pytest.mark.parametrize("kind", PATHS)
def test_physical_command_replays_minimal_snapshot_and_recovers_without_effects(
    client: TestClient, kind: str
) -> None:
    headers, body = _setup(client, kind)
    key = new_idempotency_key()
    result = _post(client, kind, headers, body, key)
    assert result.status_code == 201, result.text
    baseline = _counts()
    replay = _post(client, kind, headers, body, key)
    recovered = _recover(client, kind, headers, body, key)
    assert replay.status_code == 201, replay.text
    assert recovered.status_code == 200, recovered.text
    assert result.json() == replay.json() == recovered.json()
    assert (
        replay.headers["Idempotency-Replayed"]
        == recovered.headers["Idempotency-Replayed"]
        == "true"
    )
    assert _counts() == baseline
    assert "Private physical command notes" not in result.text
    assert "operator_email" not in result.text and "created_by_user" not in result.text
    with SessionLocal() as session:
        record = session.scalars(
            select(IdempotencyRecord).where(IdempotencyRecord.idempotency_key == UUID(key))
        ).one()
        audit = session.scalars(
            select(AuditLog).where(
                AuditLog.resource_id == result.json().get("balance_id", result.json()["id"])
            )
        ).one()
        event = session.scalars(
            select(OutboxEvent).where(
                OutboxEvent.aggregate_id == result.json().get("balance_id", result.json()["id"])
            )
        ).one()
        assert record.status == "COMPLETED"
        assert audit.metadata_["operation_id"] == event.payload["operation_id"] == str(record.id)
        assert event.payload["idempotency_key"] == key
        if kind == "admin-waste":
            movement_id = result.json()["inventory_movement_ids"][0]
            assert (
                event.payload["inventory_movement_id"]
                == audit.metadata_["inventory_movement_id"]
                == movement_id
            )
            assert session.get(InventoryMovement, UUID(movement_id)) is not None
        if kind in {"counter", "pos-waste", "correction"}:
            assert session.scalar(select(func.count()).select_from(InventoryMovement)) == 0
    changed = deepcopy(body)
    changed["notes"] = "Different command"
    conflict = _post(client, kind, headers, changed, key)
    assert conflict.status_code == 409
    assert conflict.json()["code"] == "IDEMPOTENCY_KEY_REUSED"
    assert _counts() == baseline


@pytest.mark.parametrize("kind", PATHS)
def test_physical_command_unknown_is_nonterminal_and_requires_uuid7(
    client: TestClient, kind: str
) -> None:
    headers, body = _setup(client, kind)
    baseline = _counts()
    key = new_idempotency_key()
    unknown = _recover(client, kind, headers, body, key)
    assert unknown.status_code == 409 and unknown.json()["code"] == "IDEMPOTENCY_RESULT_UNKNOWN"
    missing = client.post(PATHS[kind][0], headers=headers, json=body)
    assert missing.status_code == 422
    assert _counts() == baseline


@pytest.mark.parametrize("kind", PATHS)
@pytest.mark.parametrize("integrity_failure", [False, True])
def test_physical_command_rollback_after_domain_flush_leaves_no_partial_effect(
    client: TestClient, kind: str, integrity_failure: bool, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers, body = _setup(client, kind)
    baseline = _counts()
    key = new_idempotency_key()
    original = OutboxWriter.append

    def fail(self: OutboxWriter, session: Any, **kwargs: Any) -> Any:
        original(self, session, **kwargs)
        session.flush()
        if integrity_failure:
            raise IntegrityError(
                "Injected after domain flush", {}, RuntimeError("Injected failure")
            )
        raise RuntimeError("Injected after domain flush")

    with monkeypatch.context() as patch:
        patch.setattr(OutboxWriter, "append", fail)
        with pytest.raises(
            IntegrityError if integrity_failure else RuntimeError,
            match="Injected after domain flush",
        ):
            _post(client, kind, headers, body, key)
    assert _counts() == baseline
    assert _recover(client, kind, headers, body, key).status_code == 409
    committed = _post(client, kind, headers, body, key)
    assert committed.status_code == 201, committed.text


@pytest.mark.parametrize("kind", PATHS)
def test_physical_command_concurrent_same_key_has_one_effect(client: TestClient, kind: str) -> None:
    headers, body = _setup(client, kind)
    key = new_idempotency_key()
    barrier = Barrier(2)

    def send() -> Any:
        with TestClient(create_app()) as other:
            barrier.wait(timeout=10)
            return _post(other, kind, headers, body, key)

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(send) for _ in range(2)]
        responses = [future.result(timeout=30) for future in futures]
    assert [r.status_code for r in responses] == [201, 201], [r.text for r in responses]
    assert responses[0].json() == responses[1].json()
    with SessionLocal() as session:
        assert (
            session.scalar(
                select(func.count())
                .select_from(AuditLog)
                .where(
                    AuditLog.resource_id
                    == responses[0].json().get("balance_id", responses[0].json()["id"])
                )
            )
            == 1
        )


def test_correction_competing_keys_cannot_exceed_original_remainder(client: TestClient) -> None:
    headers, body = _setup(client, "correction")
    body["lines"][0]["delta_quantity"] = "-3.000"
    with SessionLocal() as session:
        branch_id = session.scalar(select(Branch.id).where(Branch.code == "MAIN"))
        session.add(
            Workstation(
                branch_id=branch_id, code="POS-CORRECTION-02", name="Correction concurrency fixture"
            )
        )
        session.commit()
    with TestClient(create_app()) as second:
        other_headers = login_headers(
            second,
            email=transfer_cashier_email("POS-CORRECTION-02"),
            password=SEED_USER_PASSWORD,
            audience="POS",
            workstation_code="POS-CORRECTION-02",
        )
        opening = second.post(
            "/v1/cash-sessions/open",
            headers={**other_headers, "Idempotency-Key": new_idempotency_key()},
            json={"workstation_code": "POS-CORRECTION-02", "opening_amount": "0"},
        )
        assert opening.status_code == 201, opening.text
    other_body = {
        **body,
        "workstation_code": "POS-CORRECTION-02",
        "cash_session_id": opening.json()["id"],
    }
    barrier = Barrier(2)

    def send(current_headers: dict[str, str], current_body: dict[str, Any]) -> Any:
        with TestClient(create_app()) as other:
            barrier.wait(timeout=10)
            return _post(other, "correction", current_headers, current_body, new_idempotency_key())

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(send, headers, body), pool.submit(send, other_headers, other_body)]
        responses = [future.result(timeout=30) for future in futures]
    assert sorted(response.status_code for response in responses) == [201, 400], [
        response.text for response in responses
    ]
    with SessionLocal() as session:
        assert session.scalar(select(func.sum(CorrectionDocumentLine.delta_quantity))) == Decimal(
            "-3.000"
        )
        assert session.scalar(select(func.count()).select_from(CorrectionDocument)) == 1


def test_correction_aggregates_duplicate_request_lines_and_rejects_changed_units(
    client: TestClient,
) -> None:
    headers, body = _setup(client, "correction")
    line = body["lines"][0]
    body["lines"] = [{**line, "delta_quantity": "-3"}, {**line, "delta_quantity": "-2"}]
    rejected = _post(client, "correction", headers, body, new_idempotency_key())
    assert rejected.status_code == 400, rejected.text
    with SessionLocal() as session:
        product = session.get(Product, UUID(line["product_id"]))
        assert product is not None
        product.unit_of_measure = "KG"
        session.commit()
    body["lines"] = [line]
    rejected = _post(client, "correction", headers, body, new_idempotency_key())
    assert rejected.status_code == 400, rejected.text


@pytest.mark.parametrize("kind", ["admin-waste", "adjustment"])
def test_physical_command_unknown_branch_is_rejected_before_reservation(
    client: TestClient, kind: str
) -> None:
    headers, body = _setup(client, kind)
    body["branch_id"] = "00000000-0000-0000-0000-000000000000"
    before = _counts()
    response = _post(client, kind, headers, body, new_idempotency_key())
    assert response.status_code == 404, response.text
    assert _counts() == before


@pytest.mark.parametrize("revoked_branch", ["original", "corrected"])
def test_correction_replay_and_recovery_revalidate_original_related_branches(
    client: TestClient, revoked_branch: str
) -> None:
    headers, opening_body = _setup(client, "counter")
    with SessionLocal() as session:
        original = session.scalars(
            select(Branch.id).where(Branch.code == SEED_DESTINATION_BRANCH_CODE)
        ).one()
        corrected = session.scalars(
            select(Branch.id).where(Branch.code == SEED_ALT_DESTINATION_BRANCH_CODE)
        ).one()
    dispatched = client.post(
        "/v1/transfers/dispatch/commit",
        headers={**headers, "Idempotency-Key": new_idempotency_key()},
        json={**opening_body, "destination_branch_id": str(original)},
    )
    assert dispatched.status_code == 201, dispatched.text
    body = {
        "workstation_code": opening_body["workstation_code"],
        "cash_session_id": opening_body["cash_session_id"],
        "target_document_id": dispatched.json()["id"],
        "reason_code": "WRONG_DESTINATION",
        "corrected_destination_branch_id": str(corrected),
        "lines": [],
    }
    key = new_idempotency_key()
    committed = _post(client, "correction", headers, body, key)
    assert committed.status_code == 201, committed.text
    with SessionLocal() as session:
        record = session.scalars(
            select(IdempotencyRecord).where(IdempotencyRecord.idempotency_key == UUID(key))
        ).one()
        assert set(record.context_data["related_branch_ids"]) == {str(original), str(corrected)}
        # Recovery must use the admitted scope even after the original workflow changes state.
        document = session.get(OperationDocument, UUID(body["target_document_id"]))
        assert document is not None
        document.status = "CANCELLED"
        session.commit()
    replay = _post(client, "correction", headers, body, key)
    assert replay.status_code == 201 and replay.json() == committed.json()
    recovered = _recover(client, "correction", headers, body, key)
    assert recovered.status_code == 200 and recovered.json() == committed.json()
    with SessionLocal() as session:
        actor = session.scalars(select(User).where(User.email == SEED_USER_EMAIL)).one()
        membership = session.scalars(
            select(UserBranchAssignment).where(
                UserBranchAssignment.user_id == actor.id,
                UserBranchAssignment.branch_id
                == (original if revoked_branch == "original" else corrected),
            )
        ).one()
        membership.is_active = False
        session.commit()
    headers = login_headers(
        client,
        email=SEED_USER_EMAIL,
        password=SEED_USER_PASSWORD,
        audience="POS",
        workstation_code=SEED_WORKSTATION_CODE,
    )
    before = _counts()
    for response in (
        _post(client, "correction", headers, body, key),
        _recover(client, "correction", headers, body, key),
    ):
        assert response.status_code == 403, response.text
        assert response.json()["code"] == "FORBIDDEN"
    assert _counts() == {**before, "audit_log": before["audit_log"] + 2}
    with SessionLocal() as session:
        denials = session.scalars(
            select(AuditLog).where(
                AuditLog.actor_id == actor.id, AuditLog.action == "authorization.denied"
            )
        ).all()
        assert len(denials) == 2
        assert {record.metadata_["method"] for record in denials} == {"GET", "POST"}
        assert all(record.metadata_["result"] == "denied" for record in denials)
