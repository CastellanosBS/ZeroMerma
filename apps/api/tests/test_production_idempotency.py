"""Production command acceptance on guarded disposable PostgreSQL."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from threading import Barrier
from typing import Any
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from zeromerma_api.bootstrap.seed_local import SEED_BRANCH_CODE, SEED_PRODUCT_CONCHA_VAN_CODE
from zeromerma_api.db.session import SessionLocal
from zeromerma_api.modules.audit.infrastructure.models import AuditLog
from zeromerma_api.modules.branches.infrastructure.models import Branch
from zeromerma_api.modules.catalog.infrastructure.models import Product, Recipe, RecipeInput
from zeromerma_api.modules.idempotency.application.service import IdempotencyExecutor
from zeromerma_api.modules.idempotency.infrastructure.models import IdempotencyRecord
from zeromerma_api.modules.identity.application.authorization import resolve_authorization
from zeromerma_api.modules.identity.infrastructure.models import User
from zeromerma_api.modules.inventory.infrastructure.models import (
    InventoryBalance,
    InventoryMovement,
)
from zeromerma_api.modules.outbox.infrastructure.models import OutboxEvent
from zeromerma_api.modules.production.application.admin_schemas import (
    AdminProductionCancelRequest,
    AdminProductionCompleteRequest,
    AdminProductionCreateRequest,
    AdminProductionReleaseRequest,
    AdminProductionUpdateRequest,
)
from zeromerma_api.modules.production.application.admin_services import AdminProductionService
from zeromerma_api.modules.production.application.idempotency import ProductionIdempotencyService
from zeromerma_api.modules.production.infrastructure.models import ProductionBatch
from zeromerma_api.testing.authorization import TEST_OWNER_EMAIL, owner_headers
from zeromerma_api.testing.idempotency import new_idempotency_key
from zeromerma_api.testing.inventory import seed_test_inventory

COMMANDS = ("create", "update", "release", "complete", "cancel")


def _fixture(*, initial_stock: Decimal = Decimal(100)) -> tuple[dict[str, str], dict[str, Any]]:
    headers = owner_headers()
    with SessionLocal() as session:
        branch = session.scalars(select(Branch).where(Branch.code == SEED_BRANCH_CODE)).one()
        output = session.scalars(
            select(Product).where(Product.code == SEED_PRODUCT_CONCHA_VAN_CODE)
        ).one()
        raw = Product(
            code="IDEM-RAW",
            name="Production acceptance raw",
            quick_name="Raw",
            product_class_id=output.product_class_id,
            product_kind="RAW_MATERIAL",
            is_active=True,
            is_sellable=False,
            is_usable_as_input=True,
            unit_of_measure="kg",
            unit_price=Decimal(0),
            currency_code="MXN",
            display_order=800,
        )
        session.add(raw)
        session.flush()
        for old in session.scalars(select(Recipe).where(Recipe.product_id == output.id)):
            old.is_active = False
        recipe = Recipe(
            product_id=output.id,
            version_name="Idempotency acceptance",
            yield_qty=Decimal(20),
            yield_uom=output.unit_of_measure,
            is_active=True,
        )
        session.add(recipe)
        session.flush()
        session.add(RecipeInput(recipe_id=recipe.id, input_product_id=raw.id, quantity=Decimal(2)))
        body = {
            "branch_id": str(branch.id),
            "product_id": str(output.id),
            "recipe_id": str(recipe.id),
            "planned_output_qty": "20.000",
            "notes": "Private production memo not retained in the replay snapshot",
        }
        session.commit()
        actor = session.scalar(select(User).where(User.email == TEST_OWNER_EMAIL))
        assert actor is not None
        if initial_stock > 0:
            seed_test_inventory(
                session,
                branch_id=branch.id,
                actor_user_id=actor.id,
                product_quantities={raw.id: initial_stock},
                location_code="BACKROOM",
                fixture_reference="Production idempotency acceptance",
            )
    return headers, body


def _send(
    client: TestClient,
    code: str,
    headers: dict[str, str],
    body: dict[str, Any],
    key: str | None,
    batch_id: str | None = None,
) -> Any:
    path = "/v1/admin/production"
    if batch_id is not None:
        path += f"/{batch_id}"
        if code != "update":
            path += f"/{code}"
    return client.request(
        "PATCH" if code == "update" else "POST",
        path,
        headers={**headers, **({"Idempotency-Key": key} if key is not None else {})},
        json=body,
    )


def _setup(
    client: TestClient, code: str, *, initial_stock: Decimal = Decimal(100)
) -> tuple[dict[str, str], dict[str, Any], str | None, str]:
    headers, create_body = _fixture(initial_stock=initial_stock)
    branch_id = create_body["branch_id"]
    if code == "create":
        return headers, create_body, None, branch_id
    created = _send(client, "create", headers, create_body, new_idempotency_key())
    assert created.status_code == 201
    batch_id = created.json()["id"]
    if code == "complete":
        started = _send(client, "release", headers, {}, new_idempotency_key(), batch_id)
        assert started.status_code == 200
        body = {"actual_output_qty": "20.000", "confirm_without_differences": True}
    elif code == "update":
        body = {"planned_output_qty": "30.000"}
    else:
        body = {}
    return headers, body, batch_id, branch_id


def _state() -> dict[str, Any]:
    with SessionLocal() as session:
        return {
            "batches": session.execute(
                select(
                    ProductionBatch.id, ProductionBatch.status, ProductionBatch.actual_output_qty
                ).order_by(ProductionBatch.id)
            ).all(),
            "balances": session.execute(
                select(InventoryBalance.id, InventoryBalance.quantity_on_hand).order_by(
                    InventoryBalance.id
                )
            ).all(),
            "movements": session.scalar(select(func.count()).select_from(InventoryMovement)),
            "audit": session.scalar(
                select(func.count())
                .select_from(AuditLog)
                .where(AuditLog.action.like("admin.production.%"))
            ),
            "outbox": session.scalar(
                select(func.count())
                .select_from(OutboxEvent)
                .where(OutboxEvent.aggregate_type == "production")
            ),
            "identities": session.scalar(select(func.count()).select_from(IdempotencyRecord)),
        }


@pytest.mark.parametrize("code", COMMANDS)
def test_production_replay_recovery_and_snapshot_privacy(client: TestClient, code: str) -> None:
    headers, body, batch_id, branch_id = _setup(client, code)
    key = new_idempotency_key()
    first = _send(client, code, headers, body, key, batch_id)
    assert first.status_code == (201 if code == "create" else 200)
    state = _state()
    replay = _send(
        client,
        code,
        {**headers, "X-Request-ID": "9719fe08-9a79-59fe-a5eb-a84656b6519c"},
        body,
        key,
        batch_id,
    )
    recovery = client.get(
        f"/v1/admin/production/commands/{code}/{key}?branch_id={branch_id}", headers=headers
    )
    assert recovery.status_code == 200
    assert replay.json() == recovery.json() == first.json()
    assert first.headers["Idempotency-Replayed"] == "false"
    assert (
        replay.headers["Idempotency-Replayed"] == recovery.headers["Idempotency-Replayed"] == "true"
    )
    assert recovery.headers["Cache-Control"] == "no-store"
    assert set(first.json()) == {
        "id",
        "folio",
        "branch_id",
        "product_id",
        "recipe_id",
        "status",
        "planned_output_qty",
        "actual_output_qty",
        "variance_qty",
        "variance_percent",
        "created_at",
        "updated_at",
    }
    assert _state() == state


@pytest.mark.parametrize("code", COMMANDS)
def test_production_changed_payload_conflicts_without_effects(
    client: TestClient, code: str
) -> None:
    headers, body, batch_id, _ = _setup(client, code)
    key = new_idempotency_key()
    assert _send(client, code, headers, body, key, batch_id).status_code < 300
    state = _state()
    changed = {**body, "reason" if code == "cancel" else "notes": "another intention"}
    response = _send(client, code, headers, changed, key, batch_id)
    assert response.status_code == 409
    assert response.json()["code"] == "IDEMPOTENCY_KEY_REUSED"
    assert _state() == state


@pytest.mark.parametrize("code", COMMANDS)
def test_production_failure_after_flush_rolls_back_and_allows_same_key(
    client: TestClient,
    code: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    headers, body, batch_id, _ = _setup(client, code)
    key = new_idempotency_key()
    before = _state()
    original = AdminProductionService._command_result

    def crash(session: Any, batch: Any) -> Any:
        original(session, batch)
        raise RuntimeError("controlled failure after production effects were flushed")

    with monkeypatch.context() as patch:
        patch.setattr(AdminProductionService, "_command_result", staticmethod(crash))
        with pytest.raises(RuntimeError, match="controlled failure"):
            _send(client, code, headers, body, key, batch_id)
    assert _state() == before
    assert _send(client, code, headers, body, key, batch_id).status_code < 300


@pytest.mark.parametrize("code", COMMANDS)
def test_production_committed_result_survives_lost_response(
    client: TestClient,
    code: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    headers, body, batch_id, _ = _setup(client, code)
    key = new_idempotency_key()

    def lost(*_args: Any, **_kwargs: Any) -> Any:
        raise RuntimeError("controlled response loss after commit")

    with monkeypatch.context() as patch:
        patch.setattr(
            "zeromerma_api.modules.production.presentation.router.idempotency_response", lost
        )
        with pytest.raises(RuntimeError, match="controlled response loss"):
            _send(client, code, headers, body, key, batch_id)
    before = _state()
    replay = _send(client, code, headers, body, key, batch_id)
    assert replay.status_code < 300 and replay.headers["Idempotency-Replayed"] == "true"
    assert _state() == before


def test_production_shortage_rejection_is_durable_and_retry_needs_new_intention(
    client: TestClient,
) -> None:
    headers, body, batch_id, branch_id = _setup(client, "release", initial_stock=Decimal(0))
    key = new_idempotency_key()
    rejected = _send(client, "release", headers, body, key, batch_id)
    assert rejected.status_code == 409 and rejected.json()["code"] == "PRODUCTION_CONFLICT"
    with SessionLocal() as session:
        raw = session.scalar(select(Product).where(Product.code == "IDEM-RAW"))
        actor = session.scalar(select(User).where(User.email == TEST_OWNER_EMAIL))
        assert raw is not None and actor is not None
        seed_test_inventory(
            session,
            branch_id=UUID(branch_id),
            actor_user_id=actor.id,
            product_quantities={raw.id: Decimal(100)},
            location_code="BACKROOM",
            fixture_reference="Stock received after a rejected production release",
        )
    replay = _send(client, "release", headers, body, key, batch_id)
    assert replay.status_code == 409 and replay.headers["Idempotency-Replayed"] == "true"
    recovered = client.get(
        f"/v1/admin/production/commands/release/{key}?branch_id={branch_id}", headers=headers
    )
    assert recovered.status_code == 409 and recovered.json()["code"] == "PRODUCTION_CONFLICT"
    assert (
        _send(client, "release", headers, body, new_idempotency_key(), batch_id).status_code == 200
    )


def test_production_update_distinguishes_absent_from_null(client: TestClient) -> None:
    headers, _, batch_id, _ = _setup(client, "update")
    key = new_idempotency_key()
    assert _send(client, "update", headers, {}, key, batch_id).status_code == 200
    conflict = _send(client, "update", headers, {"notes": None}, key, batch_id)
    assert conflict.status_code == 409 and conflict.json()["code"] == "IDEMPOTENCY_KEY_REUSED"


def test_production_recovery_unknown_context_and_current_authorization(client: TestClient) -> None:
    headers, body, batch_id, branch_id = _setup(client, "cancel")
    key = new_idempotency_key()
    unknown = client.get(
        f"/v1/admin/production/commands/cancel/{key}?branch_id={branch_id}", headers=headers
    )
    assert unknown.status_code == 409 and unknown.json()["code"] == "IDEMPOTENCY_RESULT_UNKNOWN"
    assert _send(client, "cancel", headers, body, key, batch_id).status_code == 200
    wrong = client.get(
        f"/v1/admin/production/commands/cancel/{key}?branch_id={uuid4()}", headers=headers
    )
    assert wrong.status_code == 409 and wrong.json()["code"] == "IDEMPOTENCY_KEY_REUSED"
    with SessionLocal() as session:
        user = session.scalars(select(User).where(User.email == TEST_OWNER_EMAIL)).one()
        user.is_active = False
        session.commit()
    denied = client.get(
        f"/v1/admin/production/commands/cancel/{key}?branch_id={branch_id}", headers=headers
    )
    assert denied.status_code in {401, 403}


@pytest.mark.parametrize(
    "pair", [("complete", "cancel"), ("complete", "complete"), ("release", "cancel")]
)
def test_production_different_keys_serialize_incompatible_transitions(
    client: TestClient,
    pair: tuple[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, _, batch_id, _ = _setup(client, "complete" if pair[0] == "complete" else "release")
    barrier = Barrier(2, timeout=15)
    reserve = IdempotencyExecutor._reserve

    def paused(self: Any, *args: Any, **kwargs: Any) -> Any:
        result = reserve(self, *args, **kwargs)
        barrier.wait()
        return result

    def execute(code: str) -> Any:
        with SessionLocal() as session:
            user = session.scalars(select(User).where(User.email == TEST_OWNER_EMAIL)).one()
            actor = resolve_authorization(session, user, surface="BACKOFFICE")
            command = (
                AdminProductionCompleteRequest(
                    actual_output_qty=Decimal(20), confirm_without_differences=True
                )
                if code == "complete"
                else AdminProductionCancelRequest(
                    no_physical_effects_confirmed=True, reason="No physical effects"
                )
                if code == "cancel"
                else AdminProductionReleaseRequest()
            )
            return ProductionIdempotencyService().execute(
                session,
                current_user=actor,
                command_code=code,
                command=command,
                key=UUID(new_idempotency_key()),
                production_id=UUID(batch_id),
                request_id="parallel",
            )

    with monkeypatch.context() as patch, ThreadPoolExecutor(max_workers=2) as pool:
        patch.setattr(IdempotencyExecutor, "_reserve", paused)
        futures = [pool.submit(execute, code) for code in pair]
        results = [future.result(timeout=25) for future in futures]
    codes = sorted(result.status_code for result in results)
    assert codes == ([200, 200] if pair[0] == "release" and codes == [200, 200] else [200, 409])
    with SessionLocal() as session:
        batch = session.get(ProductionBatch, UUID(batch_id))
        count = session.scalar(
            select(func.count())
            .select_from(InventoryMovement)
            .where(InventoryMovement.source_document_id == UUID(batch_id))
        )
        assert count == (2 if batch.status == "COMPLETED" else 0)
        assert batch.status in {"COMPLETED", "CANCELLED"}


def test_production_two_lots_create_one_output_balance_without_lost_updates(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    headers, body = _fixture()
    ids = []
    for _ in range(2):
        created = _send(client, "create", headers, body, new_idempotency_key())
        identity = created.json()["id"]
        assert (
            _send(client, "release", headers, {}, new_idempotency_key(), identity).status_code
            == 200
        )
        ids.append(identity)
    barrier = Barrier(2, timeout=15)
    reserve = IdempotencyExecutor._reserve

    def paused(self: Any, *args: Any, **kwargs: Any) -> Any:
        result = reserve(self, *args, **kwargs)
        barrier.wait()
        return result

    def complete(identity: str) -> Any:
        with SessionLocal() as session:
            user = session.scalars(select(User).where(User.email == TEST_OWNER_EMAIL)).one()
            return ProductionIdempotencyService().execute(
                session,
                current_user=resolve_authorization(session, user, surface="BACKOFFICE"),
                command_code="complete",
                command=AdminProductionCompleteRequest(
                    actual_output_qty=Decimal(20), confirm_without_differences=True
                ),
                key=UUID(new_idempotency_key()),
                production_id=UUID(identity),
                request_id="two-lots",
            )

    with monkeypatch.context() as patch, ThreadPoolExecutor(max_workers=2) as pool:
        patch.setattr(IdempotencyExecutor, "_reserve", paused)
        futures = [pool.submit(complete, identity) for identity in ids]
        assert all(future.result(timeout=25).status_code == 200 for future in futures)
    with SessionLocal() as session:
        balances = session.scalars(
            select(InventoryBalance).where(
                InventoryBalance.product_id == UUID(body["product_id"]),
                InventoryBalance.branch_id == UUID(body["branch_id"]),
                InventoryBalance.location_code == "BACKROOM",
            )
        ).all()
        assert len(balances) == 1 and balances[0].quantity_on_hand == Decimal(40)


@pytest.mark.parametrize("code", COMMANDS)
def test_production_same_key_concurrency_has_one_action(client: TestClient, code: str) -> None:
    _, body, batch_id, _ = _setup(client, code)
    before = _state()
    key = UUID(new_idempotency_key())
    barrier = Barrier(2, timeout=15)
    model = {
        "create": AdminProductionCreateRequest,
        "update": AdminProductionUpdateRequest,
        "release": AdminProductionReleaseRequest,
        "complete": AdminProductionCompleteRequest,
        "cancel": AdminProductionCancelRequest,
    }[code]

    def execute() -> Any:
        with SessionLocal() as session:
            user = session.scalars(select(User).where(User.email == TEST_OWNER_EMAIL)).one()
            actor = resolve_authorization(session, user, surface="BACKOFFICE")
            barrier.wait()
            return ProductionIdempotencyService().execute(
                session,
                current_user=actor,
                command_code=code,
                command=model.model_validate(body),
                key=key,
                production_id=UUID(batch_id) if batch_id else None,
                request_id="same-key",
            )

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(execute) for _ in range(2)]
        results = [future.result(timeout=25) for future in futures]
    assert results[0].payload == results[1].payload
    assert sorted(result.replayed for result in results) == [False, True]
    after = _state()
    assert after["audit"] == before["audit"] + 1
    assert after["outbox"] == before["outbox"] + 1
    assert after["identities"] == before["identities"] + 1
    assert after["movements"] == before["movements"] + (2 if code == "complete" else 0)


@pytest.mark.parametrize("code", COMMANDS)
def test_production_missing_and_invalid_keys_are_rejected_before_mutation(
    client: TestClient, code: str
) -> None:
    headers, body, batch_id, _ = _setup(client, code)
    before = _state()
    for value in (None, "", str(uuid4()), "invalid"):
        response = _send(client, code, headers, body, value, batch_id)
        assert response.status_code == 422
        assert _state() == before


@pytest.mark.parametrize("output", ["0.000", "12.000"])
def test_production_zero_and_partial_output_have_exact_existing_effects(
    client: TestClient, output: str
) -> None:
    headers, _, batch_id, _ = _setup(client, "complete")
    key = new_idempotency_key()
    detail = client.get(f"/v1/admin/production/{batch_id}", headers=headers)
    assert detail.status_code == 200
    body = {
        "actual_output_qty": output,
        "variance_reason": "Confirmed yield variance",
        "inputs": [
            {
                "input_product_id": item["input_product_id"],
                "consumed_qty": item["required_qty"],
                "returned_qty": "0",
                "waste_qty": "0",
                "remainder_qty": "0",
            }
            for item in detail.json()["planned_inputs"]
        ],
    }
    result = _send(client, "complete", headers, body, key, batch_id)
    assert result.status_code == 200
    state = _state()
    assert _send(client, "complete", headers, body, key, batch_id).json() == result.json()
    assert _state() == state
    with SessionLocal() as session:
        movements = session.scalars(
            select(InventoryMovement).where(InventoryMovement.source_document_id == UUID(batch_id))
        ).all()
        assert len(movements) == (1 if Decimal(output) == 0 else 2)
        assert sum((m.quantity for m in movements if m.direction == "OUT"), Decimal(0)) == Decimal(
            2
        )
        assert sum((m.quantity for m in movements if m.direction == "IN"), Decimal(0)) == Decimal(
            output
        )


def test_production_inactive_recipe_rejects_release(client: TestClient) -> None:
    headers, body, batch_id, _ = _setup(client, "release")
    with SessionLocal() as session:
        batch = session.get(ProductionBatch, UUID(batch_id))
        session.get(Recipe, batch.recipe_id).is_active = False
        session.commit()
    assert (
        _send(client, "release", headers, body, new_idempotency_key(), batch_id).status_code == 409
    )


def test_production_update_replay_keeps_draft_snapshot_after_later_release(
    client: TestClient,
) -> None:
    headers, body, batch_id, _ = _setup(client, "update")
    key = new_idempotency_key()
    updated = _send(client, "update", headers, body, key, batch_id)
    assert updated.status_code == 200 and updated.json()["status"] == "DRAFT"
    assert _send(client, "release", headers, {}, new_idempotency_key(), batch_id).status_code == 200
    state = _state()
    assert _send(client, "update", headers, body, key, batch_id).json() == updated.json()
    assert _state() == state


def test_production_unknown_branch_rejects_before_idempotency_reservation(
    client: TestClient,
) -> None:
    headers, body = _fixture()
    body["branch_id"] = str(uuid4())
    before = _state()
    result = _send(client, "create", headers, body, new_idempotency_key())
    assert result.status_code == 404
    assert _state() == before
