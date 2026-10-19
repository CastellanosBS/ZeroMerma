"""Purchase command acceptance against disposable PostgreSQL."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from decimal import Decimal
from threading import Barrier, Event
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from test_admin_purchases import _create_supplier, _purchase_payload

from zeromerma_api.db.access_scope import bind_authorization_scope
from zeromerma_api.db.session import SessionLocal
from zeromerma_api.modules.audit.infrastructure.models import AuditLog
from zeromerma_api.modules.idempotency.domain.exceptions import IdempotencyInProgress
from zeromerma_api.modules.idempotency.infrastructure.models import IdempotencyRecord
from zeromerma_api.modules.identity.application.authorization import resolve_authorization
from zeromerma_api.modules.identity.application.session_services import auth_error
from zeromerma_api.modules.identity.infrastructure.models import User
from zeromerma_api.modules.inventory.infrastructure.models import (
    InventoryBalance,
    InventoryMovement,
)
from zeromerma_api.modules.outbox.application.service import OutboxWriter
from zeromerma_api.modules.outbox.infrastructure.models import OutboxEvent
from zeromerma_api.modules.purchases.application.admin_schemas import (
    AdminPurchaseCancelRequest,
    AdminPurchaseCreateRequest,
    AdminPurchaseDirectEntryRequest,
    AdminPurchaseReceiveRequest,
    AdminPurchaseUpdateRequest,
)
from zeromerma_api.modules.purchases.application.idempotency import (
    PurchaseCommandService,
    _capability,
)
from zeromerma_api.modules.purchases.infrastructure.models import (
    PurchaseDocument,
    PurchaseDocumentLine,
    PurchaseReceipt,
    PurchaseReceiptLine,
)
from zeromerma_api.modules.suppliers.infrastructure.models import SupplierProduct
from zeromerma_api.testing.authorization import TEST_OWNER_EMAIL, owner_headers
from zeromerma_api.testing.idempotency import new_idempotency_key

CODES = ["create", "update", "direct-entry", "confirm", "receive", "cancel"]
SCHEMAS = {
    "create": AdminPurchaseCreateRequest,
    "update": AdminPurchaseUpdateRequest,
    "direct-entry": AdminPurchaseDirectEntryRequest,
    "receive": AdminPurchaseReceiveRequest,
    "cancel": AdminPurchaseCancelRequest,
}


def _post(
    client: TestClient,
    code: str,
    headers: dict,
    body: dict | None,
    key: str,
    purchase_id: str | None = None,
):
    path = "/v1/admin/purchases"
    if code == "direct-entry":
        path += "/direct-entry"
    elif code not in {"create"}:
        path += f"/{purchase_id}"
        if code != "update":
            path += f"/{code}"
    return client.request(
        "PATCH" if code == "update" else "POST",
        path,
        headers={**headers, "Idempotency-Key": key},
        json=body,
    )


def _setup(client: TestClient, code: str):
    headers = owner_headers()
    supplier = _create_supplier(client)
    body = _purchase_payload(supplier_id=supplier["overview"]["id"])
    branch = body["branch_id"]
    if code == "create":
        return headers, body, None, branch
    if code == "direct-entry":
        body.pop("confirm_now")
        for line in body["lines"]:
            line["received_quantity"] = line.pop("ordered_quantity")
        return headers, body, None, branch
    created = _post(client, "create", headers, body, new_idempotency_key())
    assert created.status_code == 201
    purchase_id = created.json()["id"]
    if code == "update":
        body = {"notes": "Private revised supplier note"}
    elif code == "receive":
        body = {
            "lines": [
                {
                    "purchase_line_id": created.json()["lines"][0]["purchase_line_id"],
                    "received_quantity": "5.000",
                }
            ]
        }
    elif code == "cancel":
        body = {"reason": "Private cancellation note"}
    else:
        body = None
    return headers, body, purchase_id, branch


def _effects() -> tuple:
    with SessionLocal() as session:
        return tuple(
            session.scalar(select(func.count(model.id)))
            for model in (
                PurchaseDocument,
                PurchaseDocumentLine,
                PurchaseReceipt,
                PurchaseReceiptLine,
                InventoryBalance,
                InventoryMovement,
            )
        ) + (
            session.scalar(
                select(func.count(AuditLog.id)).where(AuditLog.action.like("admin.purchase.%"))
            ),
            session.scalar(
                select(func.count(OutboxEvent.id)).where(
                    OutboxEvent.event_name.like("admin.purchase.%")
                )
            ),
            session.scalar(
                select(func.count(IdempotencyRecord.id)).where(
                    IdempotencyRecord.operation_code.like("purchase.%")
                )
            ),
        )


def _recover(client: TestClient, code: str, headers: dict, key: str, branch: str):
    return client.get(
        f"/v1/admin/purchases/commands/{code}/{key}", params={"branch_id": branch}, headers=headers
    )


@pytest.mark.parametrize("code", CODES)
def test_purchase_replay_recovery_and_private_snapshot(client: TestClient, code: str) -> None:
    headers, body, purchase_id, branch = _setup(client, code)
    key = new_idempotency_key()
    result = _post(client, code, headers, body, key, purchase_id)
    assert result.status_code == (201 if code in {"create", "direct-entry"} else 200)
    assert result.headers["Idempotency-Replayed"] == "false"
    effects = _effects()
    replay = _post(
        client,
        code,
        {**headers, "X-Request-ID": "69c557b2-ba73-5788-ae47-6c728571a809"},
        body,
        key,
        purchase_id,
    )
    assert replay.status_code == result.status_code
    assert replay.json() == result.json()
    assert replay.headers["Idempotency-Replayed"] == "true"
    recovered = _recover(client, code, headers, key, branch)
    assert recovered.json() == result.json()
    assert _effects() == effects
    forbidden = {
        "notes",
        "reason",
        "supplier_name",
        "supplier_context",
        "created_by_user_name",
        "available_actions",
        "external_document_number",
    }

    def check(value):
        if isinstance(value, dict):
            assert not forbidden.intersection(value)
            for child in value.values():
                check(child)
        elif isinstance(value, list):
            for child in value:
                check(child)

    check(result.json())
    with SessionLocal() as session:
        record = session.scalar(
            select(IdempotencyRecord).where(IdempotencyRecord.idempotency_key == UUID(key))
        )
        audits = list(
            session.scalars(
                select(AuditLog).where(
                    AuditLog.resource_id == result.json()["id"],
                    AuditLog.action.like("admin.purchase.%"),
                )
            )
        )
        assert any(audit.metadata_.get("operation_id") == str(record.id) for audit in audits)


@pytest.mark.parametrize("code", CODES)
def test_purchase_missing_key_and_changed_payload_fail_closed(
    client: TestClient, code: str
) -> None:
    headers, body, purchase_id, branch = _setup(client, code)
    before = _effects()
    bad_key = _post(client, code, headers, body, "invalid", purchase_id)
    assert bad_key.status_code == 422
    assert _effects() == before
    key = new_idempotency_key()
    first = _post(client, code, headers, body, key, purchase_id)
    assert first.status_code in {200, 201}
    changed = deepcopy(body)
    if changed is not None:
        field = "reason" if code == "cancel" else "notes"
        changed[field] = "Changed intention"
        mismatch = _post(client, code, headers, changed, key, purchase_id)
    else:
        mismatch = _post(client, "cancel", headers, {"reason": None}, key, purchase_id)
    assert mismatch.status_code == 409
    assert mismatch.json()["code"] == "IDEMPOTENCY_KEY_REUSED"
    assert (
        _recover(client, code, headers, new_idempotency_key(), branch).json()["code"]
        == "IDEMPOTENCY_RESULT_UNKNOWN"
    )


def test_partial_receipts_preserve_original_result_and_rejection(client: TestClient) -> None:
    headers, body, purchase_id, branch = _setup(client, "receive")
    body["lines"][0].update(received_quantity="2.000", discrepancy_reason="Pending shipment")
    key = new_idempotency_key()
    first = _post(client, "receive", headers, body, key, purchase_id)
    assert first.status_code == 200
    assert first.json()["status"] == "PARTIALLY_RECEIVED"
    excess = deepcopy(body)
    excess["lines"][0]["received_quantity"] = "4.000"
    rejected_key = new_idempotency_key()
    rejected = _post(client, "receive", headers, excess, rejected_key, purchase_id)
    assert rejected.status_code == 409
    assert rejected.json()["code"] == "PURCHASE_COMMAND_REJECTED"
    remaining = deepcopy(body)
    remaining["lines"][0]["received_quantity"] = "3.000"
    assert (
        _post(client, "receive", headers, remaining, new_idempotency_key(), purchase_id).json()[
            "status"
        ]
        == "RECEIVED"
    )
    assert _recover(client, "receive", headers, key, branch).json() == first.json()
    recovered_rejection = _recover(client, "receive", headers, rejected_key, branch)
    assert recovered_rejection.status_code == 409
    assert recovered_rejection.headers["Idempotency-Replayed"] == "true"
    with SessionLocal() as session:
        assert session.scalar(select(InventoryBalance.quantity_on_hand)) == Decimal("5")
        assert session.scalar(select(func.count(PurchaseReceipt.id))) == 2


def test_patch_omission_and_null_are_different_intentions(client: TestClient) -> None:
    headers, _, purchase_id, _ = _setup(client, "update")
    key = new_idempotency_key()
    assert _post(client, "update", headers, {}, key, purchase_id).status_code == 200
    assert _post(client, "update", headers, {"notes": None}, key, purchase_id).status_code == 409


def test_confirmed_creation_rechecks_confirmation_permission_on_replay_and_recovery(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    from zeromerma_api.modules.purchases.application import idempotency

    headers, body, _, branch = _setup(client, "create")
    body["confirm_now"] = True
    key = new_idempotency_key()
    require = idempotency.require_branches

    def deny_confirmation(user, capability, branches):
        if capability == "purchases.confirm":
            raise auth_error(403, "FORBIDDEN", "Confirmation permission was revoked.")
        return require(user, capability, branches)

    before = _effects()
    with monkeypatch.context() as patch:
        patch.setattr(idempotency, "require_branches", deny_confirmation)
        assert _post(client, "create", headers, body, key).status_code == 403
    assert _effects() == before
    created = _post(client, "create", headers, body, key)
    assert created.status_code == 201 and created.json()["status"] == "ORDERED"
    committed = _effects()
    with monkeypatch.context() as patch:
        patch.setattr(idempotency, "require_branches", deny_confirmation)
        assert _post(client, "create", headers, body, key).status_code == 403
        assert _recover(client, "create", headers, key, branch).status_code == 403
    assert _effects() == committed
    assert _recover(client, "create", headers, key, branch).json() == created.json()


def test_draft_creation_recovery_does_not_infer_permission_from_mutated_document(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    from zeromerma_api.modules.purchases.application import idempotency

    headers, body, _, branch = _setup(client, "create")
    key = new_idempotency_key()
    created = _post(client, "create", headers, body, key)
    assert created.status_code == 201 and created.json()["status"] == "DRAFT"
    assert (
        _post(
            client, "confirm", headers, None, new_idempotency_key(), created.json()["id"]
        ).status_code
        == 200
    )
    require = idempotency.require_branches

    def deny_confirmation(user, capability, branches):
        if capability == "purchases.confirm":
            raise auth_error(403, "FORBIDDEN", "Confirmation permission was revoked.")
        return require(user, capability, branches)

    with monkeypatch.context() as patch:
        patch.setattr(idempotency, "require_branches", deny_confirmation)
        assert _recover(client, "create", headers, key, branch).json() == created.json()


def test_duplicate_receipt_lines_do_not_change_inventory(client: TestClient) -> None:
    headers, body, purchase_id, _ = _setup(client, "receive")
    body["lines"] *= 2
    before = _effects()
    response = _post(client, "receive", headers, body, new_idempotency_key(), purchase_id)
    assert response.status_code in {409, 422}
    assert _effects()[:8] == before[:8]


@pytest.mark.parametrize("code", ["create", "direct-entry", "update"])
def test_missing_purchase_branch_is_rejected_before_reserving_identity(
    client: TestClient, code: str
) -> None:
    headers, body, purchase_id, _ = _setup(client, code)
    body["branch_id"] = str(uuid4())
    before = _effects()
    response = _post(client, code, headers, body, new_idempotency_key(), purchase_id)
    assert response.status_code == 404
    assert _effects() == before


def _domain(code: str, body: dict | None, key: str, purchase_id: str | None):
    with SessionLocal() as session:
        user = resolve_authorization(
            session,
            session.scalar(select(User).where(User.email == TEST_OWNER_EMAIL)),
            surface="BACKOFFICE",
        )
        bind_authorization_scope(
            session,
            user=user,
            capabilities=(_capability(code),),
            mutation=True,
            surface="BACKOFFICE",
        )
        return PurchaseCommandService().execute(
            session,
            current_user=user,
            command_code=code,
            command=SCHEMAS[code].model_validate(body) if body is not None else None,
            key=UUID(key),
            purchase_id=UUID(purchase_id) if purchase_id else None,
            request_id="purchase-concurrency",
        )


def test_concurrent_receipts_cannot_receive_the_same_remainder_twice(client: TestClient) -> None:
    _, body, purchase_id, _ = _setup(client, "receive")
    barrier = Barrier(2)

    def run():
        barrier.wait(timeout=15)
        return _domain("receive", body, new_idempotency_key(), purchase_id)

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(run) for _ in range(2)]
        results = [future.result(timeout=20) for future in futures]
    assert sorted(result.status_code for result in results) == [200, 409]
    with SessionLocal() as session:
        assert session.scalar(select(InventoryBalance.quantity_on_hand)) == Decimal("5")
        assert session.scalar(select(func.count(PurchaseReceipt.id))) == 1


def test_purchase_same_key_contention_is_bounded(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    _, body, purchase_id, _ = _setup(client, "receive")
    held, release = Event(), Event()
    append = OutboxWriter.append

    def hold(self, session, **kwargs):
        result = append(self, session, **kwargs)
        if kwargs["event_name"] == "admin.purchase.received.v1" and not held.is_set():
            held.set()
            assert release.wait(timeout=20)
        return result

    key = new_idempotency_key()
    with monkeypatch.context() as patch, ThreadPoolExecutor(max_workers=2) as pool:
        patch.setattr(OutboxWriter, "append", hold)
        first = pool.submit(_domain, "receive", body, key, purchase_id)
        try:
            assert held.wait(timeout=15)
            with pytest.raises(IdempotencyInProgress):
                _domain("receive", body, key, purchase_id)
        finally:
            release.set()
        committed = first.result(timeout=15)
    replay = _domain("receive", body, key, purchase_id)
    assert replay.replayed and replay.payload == committed.payload


@pytest.mark.parametrize(
    "code", ["create", "direct-entry", "update", "confirm", "receive", "cancel"]
)
def test_purchase_crash_rolls_back_document_effects_and_reservation(
    client: TestClient, code: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    _, body, purchase_id, _ = _setup(client, code)
    before = _effects()
    key = new_idempotency_key()
    append = OutboxWriter.append

    def crash(self, session, **kwargs):
        append(self, session, **kwargs)
        session.flush()
        raise RuntimeError("Injected purchase failure after effects were flushed")

    with monkeypatch.context() as patch:
        patch.setattr(OutboxWriter, "append", crash)
        with pytest.raises(RuntimeError, match="Injected purchase failure"):
            _domain(code, body, key, purchase_id)
    assert _effects() == before
    assert _domain(code, body, key, purchase_id).status_code in {200, 201}


@pytest.mark.parametrize("code", ["direct-entry", "receive"])
@pytest.mark.parametrize("existing_supplier_product", [True, False])
def test_receipt_lines_for_same_product_accumulate_stock_before_replay(
    client: TestClient, code: str, existing_supplier_product: bool
) -> None:
    headers, body, _, branch = _setup(client, "create")
    product_id = body["lines"][0]["product_id"]
    supplier_id = body["supplier_id"]
    body["lines"] = [
        {**body["lines"][0], "ordered_quantity": "2.000", "unit_cost": "12.5000"},
        {**body["lines"][0], "ordered_quantity": "3.000", "unit_cost": "17.5000"},
    ]
    initial_stock = client.post(
        "/v1/admin/inventory/adjustments",
        headers={**headers, "Idempotency-Key": new_idempotency_key()},
        json={
            "adjustment_type": "INCREASE",
            "branch_id": branch,
            "location_code": "BACKROOM",
            "product_id": product_id,
            "quantity": "10.000",
            "reason": "Opening stock for repeated product receipt",
        },
    )
    assert initial_stock.status_code == 201, initial_stock.text
    if not existing_supplier_product:
        with SessionLocal() as session:
            relation = session.scalars(
                select(SupplierProduct).where(
                    SupplierProduct.supplier_id == UUID(supplier_id),
                    SupplierProduct.product_id == UUID(product_id),
                )
            ).one()
            session.delete(relation)
            session.commit()
    purchase_id = None
    if code == "direct-entry":
        body.pop("confirm_now")
        for line in body["lines"]:
            line["received_quantity"] = line.pop("ordered_quantity")
    else:
        created = _post(client, "create", headers, body, new_idempotency_key())
        assert created.status_code == 201, created.text
        purchase_id = created.json()["id"]
        assert len({line["purchase_line_id"] for line in created.json()["lines"]}) == 2
        body = {
            "lines": [
                {
                    "purchase_line_id": line["purchase_line_id"],
                    "received_quantity": line["ordered_quantity"],
                }
                for line in created.json()["lines"]
            ]
        }
    key = new_idempotency_key()
    committed = _post(client, code, headers, body, key, purchase_id)
    assert committed.status_code == (201 if code == "direct-entry" else 200), committed.text
    result = committed.json()
    assert result["status"] == "RECEIVED"
    assert len({line["purchase_line_id"] for line in result["lines"]}) == 2
    assert {line["product_id"] for line in result["lines"]} == {product_id}
    assert sorted(Decimal(line["received_quantity"]) for line in result["lines"]) == [
        Decimal("2"),
        Decimal("3"),
    ]
    with SessionLocal() as session:
        assert session.scalar(
            select(InventoryBalance.quantity_on_hand).where(
                InventoryBalance.product_id == UUID(product_id),
                InventoryBalance.branch_id == UUID(branch),
                InventoryBalance.location_code == "BACKROOM",
            )
        ) == Decimal("15")
        movements = session.execute(
            select(InventoryMovement.quantity, InventoryMovement.balance_after)
            .where(
                InventoryMovement.id.in_([UUID(item) for item in result["inventory_movement_ids"]])
            )
            .order_by(InventoryMovement.balance_after)
        ).all()
        assert movements == [(Decimal("2"), Decimal("12")), (Decimal("3"), Decimal("15"))]
        relation = session.scalars(
            select(SupplierProduct).where(
                SupplierProduct.supplier_id == UUID(supplier_id),
                SupplierProduct.product_id == UUID(product_id),
            )
        ).one()
        assert relation.last_known_price == Decimal("17.5000")
    effects = _effects()
    replay = _post(client, code, headers, body, key, purchase_id)
    recovered = _recover(client, code, headers, key, branch)
    assert replay.status_code == committed.status_code
    assert recovered.status_code == 200
    assert replay.json() == recovered.json() == result
    assert replay.headers["Idempotency-Replayed"] == "true"
    assert recovered.headers["Idempotency-Replayed"] == "true"
    assert _effects() == effects
