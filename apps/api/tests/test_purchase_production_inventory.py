from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from threading import Barrier
from typing import Any
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from test_admin_inputs_supplies import _input_payload
from test_admin_production import _create_active_recipe, _create_production, _create_raw_material
from test_admin_purchases import _create_supplier, _get_branch_id

from zeromerma_api.db.session import SessionLocal
from zeromerma_api.modules.catalog.infrastructure.models import Product, Recipe
from zeromerma_api.modules.idempotency.application.service import IdempotencyExecutor
from zeromerma_api.modules.identity.application.authorization import resolve_authorization
from zeromerma_api.modules.identity.infrastructure.models import User
from zeromerma_api.modules.inventory.infrastructure.lot_models import (
    InventoryLot,
    InventoryLotBalance,
    InventoryMovementLotAllocation,
)
from zeromerma_api.modules.inventory.infrastructure.models import (
    InventoryBalance,
    InventoryMovement,
)
from zeromerma_api.modules.production.application.admin_schemas import AdminProductionReleaseRequest
from zeromerma_api.modules.production.application.idempotency import ProductionIdempotencyService
from zeromerma_api.modules.purchases.infrastructure.models import PurchaseReceiptReversal
from zeromerma_api.testing.authorization import TEST_OWNER_EMAIL, owner_headers
from zeromerma_api.testing.idempotency import new_idempotency_key


def _post(client: TestClient, path: str, body: dict[str, Any], *, key: str | None = None) -> Any:
    return client.post(
        path,
        headers={**owner_headers(), "Idempotency-Key": key or new_idempotency_key()},
        json=body,
    )


def _detail(client: TestClient, family: str, identity: str) -> dict[str, Any]:
    response = client.get(f"/v1/admin/{family}/{identity}", headers=owner_headers())
    assert response.status_code == 200
    return dict(response.json())


def _purchase(
    client: TestClient, product_id: str, quantity: str, cost: str, **line_fields: Any
) -> Any:
    supplier = _create_supplier(client)
    return _post(
        client,
        "/v1/admin/purchases/direct-entry",
        {
            "branch_id": _get_branch_id(),
            "supplier_id": supplier["overview"]["id"],
            "lines": [
                {
                    "product_id": product_id,
                    "received_quantity": quantity,
                    "unit_cost": cost,
                    **line_fields,
                }
            ],
        },
    )


def _stock(product_id: str, location: str = "BACKROOM") -> tuple[Decimal, Decimal, Decimal | None]:
    with SessionLocal() as session:
        balance = session.scalar(
            select(InventoryBalance).where(
                InventoryBalance.product_id == UUID(product_id),
                InventoryBalance.branch_id == UUID(_get_branch_id()),
                InventoryBalance.location_code == location,
            )
        )
        assert balance is not None
        return balance.quantity_on_hand, balance.quantity_reserved, balance.inventory_value


def _released(client: TestClient, *, product_id: str, quantity: str = "20.000") -> dict[str, Any]:
    recipe_id = _create_active_recipe(raw_material_id=product_id)
    plan = _create_production(client, recipe_id=recipe_id, planned_output_qty=quantity)
    response = _post(client, f"/v1/admin/production/{plan['overview']['id']}/release", {})
    assert response.status_code == 200, response.text
    return _detail(client, "production", response.json()["id"])


def test_purchase_source_conversion_cost_history_reversal_and_replay(client: TestClient) -> None:
    raw = _create_raw_material("PURCHASE-BOX")
    with SessionLocal() as session:
        product = session.get(Product, UUID(raw))
        assert product
        product.purchase_unit_of_measure, product.purchase_conversion_factor = "BOX", Decimal(5)
        session.commit()
    supplier = _create_supplier(client)
    created = _post(
        client,
        "/v1/admin/purchases",
        {
            "branch_id": _get_branch_id(),
            "supplier_id": supplier["overview"]["id"],
            "confirm_now": True,
            "lines": [
                {
                    "product_id": raw,
                    "ordered_quantity": "2.000",
                    "source_unit_of_measure": "BOX",
                    "unit_cost": "10.0000",
                }
            ],
        },
    )
    assert created.status_code == 201, created.text
    purchase_id = created.json()["id"]
    line_id = created.json()["lines"][0]["purchase_line_id"]
    # Catalog changes cannot reinterpret a confirmed purchase's conversion evidence.
    with SessionLocal() as session:
        product = session.get(Product, UUID(raw))
        assert product
        product.purchase_conversion_factor = Decimal(8)
        session.commit()
    for cost in ("10.0000", "20.0000"):
        response = _post(
            client,
            f"/v1/admin/purchases/{purchase_id}/receive",
            {
                "lines": [
                    {
                        "purchase_line_id": line_id,
                        "received_quantity": "1.000",
                        "unit_cost": cost,
                        "discrepancy_reason": "Partial delivery",
                    }
                ],
            },
        )
        assert response.status_code == 200, response.text
    detail = _detail(client, "purchases", purchase_id)
    assert Decimal(detail["cost_summary"]["received_total"]) == Decimal(30)
    assert Decimal(detail["lines"][0]["unit_cost"]) == Decimal(10)
    assert _stock(raw) == (Decimal(10), Decimal(0), Decimal(30))
    key = new_idempotency_key()
    body = {"receipt_id": detail["receipts"][1]["id"], "reason": "Incorrect second delivery"}
    first = _post(client, f"/v1/admin/purchases/{purchase_id}/reverse-receipt", body, key=key)
    assert first.status_code == 200, first.text
    replay = _post(client, f"/v1/admin/purchases/{purchase_id}/reverse-receipt", body, key=key)
    assert replay.status_code == 200 and replay.json() == first.json()
    assert replay.headers["Idempotency-Replayed"] == "true"
    assert _stock(raw) == (Decimal(5), Decimal(0), Decimal(10))
    final = _detail(client, "purchases", purchase_id)
    assert final["overview"]["status"] == "PARTIALLY_RECEIVED"
    assert Decimal(final["cost_summary"]["received_total"]) == Decimal(10)
    with SessionLocal() as session:
        assert len(list(session.scalars(select(PurchaseReceiptReversal)))) == 1
        effects = list(
            session.scalars(
                select(InventoryMovement).where(InventoryMovement.product_id == UUID(raw))
            )
        )
        assert len(effects) == 3
        assert sum(effect.reversal_of_movement_id is not None for effect in effects) == 1


def test_purchase_invoice_normalization_rejects_duplicate_without_stock(client: TestClient) -> None:
    raw = _create_raw_material("PURCHASE-INVOICE")
    supplier = _create_supplier(client)
    body = {
        "branch_id": _get_branch_id(),
        "supplier_id": supplier["overview"]["id"],
        "external_document_type": "INVOICE",
        "external_document_number": " INV-42 ",
        "lines": [{"product_id": raw, "ordered_quantity": "1", "unit_cost": "0.0000"}],
    }
    assert _post(client, "/v1/admin/purchases", body).status_code == 201
    body["external_document_number"] = "inv-42"
    duplicate = _post(client, "/v1/admin/purchases", body)
    assert duplicate.status_code == 409, duplicate.text
    with SessionLocal() as session:
        assert (
            session.scalar(
                select(InventoryMovement.id).where(InventoryMovement.product_id == UUID(raw))
            )
            is None
        )


def test_production_release_reserves_then_manual_reconciliation_moves_exact_effects(
    client: TestClient,
) -> None:
    raw = _create_raw_material("PROD-RECONCILE")
    receipt = _purchase(client, raw, "10.000", "2.0000")
    assert receipt.status_code == 201, receipt.text
    plan = _released(client, product_id=raw)
    identity = plan["overview"]["id"]
    assert plan["overview"]["plan_status"] == "RELEASED"
    assert plan["overview"]["run_status"] == "OPEN"
    assert _stock(raw) == (Decimal(10), Decimal(4), Decimal(20))
    response = _post(
        client,
        f"/v1/admin/production/{identity}/complete",
        {
            "actual_output_qty": "18.000",
            "variance_reason": "Observed output after baking",
            "inputs": [
                {
                    "input_product_id": raw,
                    "consumed_qty": "3.000",
                    "returned_qty": "0.500",
                    "waste_qty": "0.500",
                    "remainder_qty": "0.000",
                    "reason": "Supervisor counted consumption and spillage",
                }
            ],
        },
    )
    assert response.status_code == 200, response.text
    assert _stock(raw) == (Decimal("6.500"), Decimal(0), Decimal(13))
    assert _stock(raw, "WASTE") == (Decimal("0.500"), Decimal(0), Decimal(1))
    output = plan["product_recipe"]["product_id"]
    assert _stock(output) == (Decimal(18), Decimal(0), Decimal(6))
    detail = _detail(client, "production", identity)
    assert detail["overview"]["reconciliation_evidence"] == "MANUAL_CONFIRMED"
    assert Decimal(detail["actual_consumption"][0]["waste_qty"]) == Decimal("0.500")
    assert len(detail["inventory_impact"]["movements"]) == 4


def test_production_cancel_requires_no_effects_or_keeps_reservation_pending(
    client: TestClient,
) -> None:
    raw = _create_raw_material("PROD-CANCEL-RESERVE")
    assert _purchase(client, raw, "4", "1").status_code == 201
    plan = _released(client, product_id=raw)
    identity = plan["overview"]["id"]
    pending = _post(
        client, f"/v1/admin/production/{identity}/cancel", {"reason": "Supervisor must reconcile"}
    )
    assert pending.status_code == 200 and pending.json()["status"] == "PENDING_RECONCILIATION"
    assert _stock(raw)[1] == Decimal(4)
    cancelled = _post(
        client,
        f"/v1/admin/production/{identity}/cancel",
        {
            "reason": "Materials never left storage",
            "no_physical_effects_confirmed": True,
        },
    )
    assert cancelled.status_code == 200 and cancelled.json()["status"] == "CANCELLED"
    assert _stock(raw) == (Decimal(4), Decimal(0), Decimal(4))


def test_released_recipe_and_input_snapshots_are_immutable_but_deactivation_is_allowed(
    client: TestClient,
) -> None:
    raw = _create_raw_material("PROD-FROZEN")
    assert _purchase(client, raw, "4", "1").status_code == 201
    plan = _released(client, product_id=raw)
    recipe_id = UUID(plan["product_recipe"]["recipe_id"])
    with SessionLocal() as session:
        recipe = session.get(Recipe, recipe_id)
        assert recipe
        recipe.yield_qty = Decimal(30)
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()
        recipe = session.get(Recipe, recipe_id)
        assert recipe
        recipe.is_active = False
        session.commit()
    response = _post(
        client,
        f"/v1/admin/production/{plan['overview']['id']}/complete",
        {
            "actual_output_qty": "20",
            "confirm_without_differences": True,
        },
    )
    assert response.status_code == 200, response.text
    detail = _detail(client, "production", response.json()["id"])
    assert Decimal(detail["product_recipe"]["recipe_yield_qty"]) == Decimal(10)


def test_two_releases_contend_for_last_input_reservation(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    raw = _create_raw_material("PROD-LAST-INPUT")
    assert _purchase(client, raw, "4", "1").status_code == 201
    recipe_id = _create_active_recipe(raw_material_id=raw)
    identities = [
        _create_production(client, recipe_id=recipe_id)["overview"]["id"] for _ in range(2)
    ]
    barrier = Barrier(2, timeout=15)
    reserve = IdempotencyExecutor._reserve

    def paused(self: Any, *args: Any, **kwargs: Any) -> Any:
        result = reserve(self, *args, **kwargs)
        barrier.wait()
        return result

    def release(identity: str) -> Any:
        with SessionLocal() as session:
            user = session.scalar(select(User).where(User.email == TEST_OWNER_EMAIL))
            assert user
            return ProductionIdempotencyService().execute(
                session,
                current_user=resolve_authorization(session, user, surface="BACKOFFICE"),
                command_code="release",
                command=AdminProductionReleaseRequest(),
                key=UUID(new_idempotency_key()),
                production_id=UUID(identity),
                request_id=None,
            )

    with monkeypatch.context() as patch, ThreadPoolExecutor(max_workers=2) as pool:
        patch.setattr(IdempotencyExecutor, "_reserve", paused)
        futures = [pool.submit(release, identity) for identity in identities]
        assert sorted(future.result(timeout=25).status_code for future in futures) == [200, 409]
    assert _stock(raw) == (Decimal(4), Decimal(4), Decimal(4))


def test_pending_reconciliation_preserves_claims_and_additional_consumption_is_costed(
    client: TestClient,
) -> None:
    raw = _create_raw_material("PROD-ADDITIONAL")
    assert _purchase(client, raw, "10", "2").status_code == 201
    plan = _released(client, product_id=raw)
    path = f"/v1/admin/production/{plan['overview']['id']}/complete"
    body = {
        "actual_output_qty": "18",
        "variance_reason": "Manual measured yield",
        "output_lot_code": "PENDING-OUTPUT",
        "output_expires_at": "2030-01-02T18:30:00Z",
        "finish_as": "CANCELLED",
        "inputs": [
            {
                "input_product_id": raw,
                "consumed_qty": "3",
                "returned_qty": "0",
                "waste_qty": "0",
                "remainder_qty": "1",
                "reason": "Unresolved material",
            }
        ],
    }
    pending = _post(client, path, body)
    assert pending.status_code == 200, pending.text
    assert pending.json()["status"] == "PENDING_RECONCILIATION"
    detail = _detail(client, "production", plan["overview"]["id"])
    assert Decimal(detail["actual_consumption"][0]["consumed_qty"]) == Decimal(3)
    assert Decimal(detail["overview"]["actual_output_qty"]) == Decimal(18)
    assert detail["overview"]["variance_reason"] == body["variance_reason"]
    assert detail["overview"]["output_lot_code"] == body["output_lot_code"]
    assert detail["overview"]["output_expires_at"] == body["output_expires_at"]
    assert detail["overview"]["reconciliation_finish_as"] == "CANCELLED"
    assert _stock(raw) == (Decimal(10), Decimal(4), Decimal(20))
    body["inputs"] = [
        {
            "input_product_id": raw,
            "consumed_qty": "5",
            "returned_qty": "0",
            "waste_qty": "0",
            "remainder_qty": "0",
            "reason": "Additional measured input",
        }
    ]
    body["finish_as"] = "COMPLETED"
    key = new_idempotency_key()
    completed = _post(client, path, body, key=key)
    assert completed.status_code == 200, completed.text
    replay = _post(client, path, body, key=key)
    assert replay.status_code == 200 and replay.json() == completed.json()
    assert _stock(raw) == (Decimal(5), Decimal(0), Decimal(10))
    assert _stock(plan["product_recipe"]["product_id"]) == (Decimal(18), Decimal(0), Decimal(10))


def test_purchase_lots_reserve_fefo_and_production_preserves_weighted_average_cost(
    client: TestClient,
) -> None:
    raw = _create_raw_material("PROD-LOT-RAW")
    with SessionLocal() as session:
        product = session.get(Product, UUID(raw))
        assert product
        product.lot_tracking_enabled = product.expiry_required = True
        session.commit()
    supplier = _create_supplier(client)
    now = datetime.now(UTC)
    for lot, quantity, cost, days in (("LATER", "4", "3", 20), ("EARLIER", "2", "1", 10)):
        receipt = _post(
            client,
            "/v1/admin/purchases/direct-entry",
            {
                "branch_id": _get_branch_id(),
                "supplier_id": supplier["overview"]["id"],
                "lines": [
                    {
                        "product_id": raw,
                        "received_quantity": quantity,
                        "unit_cost": cost,
                        "lot_code": lot,
                        "expires_at": (now + timedelta(days=days)).isoformat(),
                    }
                ],
            },
        )
        assert receipt.status_code == 201, receipt.text
    plan = _released(client, product_id=raw)
    with SessionLocal() as session:
        allocations = session.execute(
            select(InventoryLot.lot_code, InventoryLotBalance.quantity_reserved)
            .join(InventoryLotBalance, InventoryLotBalance.lot_id == InventoryLot.id)
            .where(InventoryLot.product_id == UUID(raw))
        ).all()
        assert dict(allocations) == {"EARLIER": Decimal(2), "LATER": Decimal(2)}
    completed = _post(
        client,
        f"/v1/admin/production/{plan['overview']['id']}/complete",
        {
            "actual_output_qty": "20",
            "confirm_without_differences": True,
        },
    )
    assert completed.status_code == 200, completed.text
    # Physical FEFO does not change the independently maintained weighted average valuation.
    assert _stock(raw) == (Decimal(2), Decimal(0), Decimal("4.66666667"))
    assert _stock(plan["product_recipe"]["product_id"])[2] == Decimal("9.33333333")
    with SessionLocal() as session:
        quantities = session.execute(
            select(InventoryLot.lot_code, InventoryLotBalance.quantity_on_hand)
            .join(InventoryLotBalance, InventoryLotBalance.lot_id == InventoryLot.id)
            .where(InventoryLot.product_id == UUID(raw))
        ).all()
        assert dict(quantities) == {"EARLIER": Decimal(0), "LATER": Decimal(2)}


def test_purchase_conversion_preserves_total_cost_when_base_unit_cost_repeats(
    client: TestClient,
) -> None:
    raw = _create_raw_material("PURCHASE-THIRDS")
    with SessionLocal() as session:
        product = session.get(Product, UUID(raw))
        assert product is not None
        product.purchase_unit_of_measure = "BOX"
        product.purchase_conversion_factor = Decimal(3)
        session.commit()
    response = _purchase(client, raw, "1", "10", source_unit_of_measure="BOX")
    assert response.status_code == 201, response.text
    assert _stock(raw) == (Decimal(3), Decimal(0), Decimal(10))
    detail = _detail(client, "purchases", response.json()["id"])
    receipt = detail["receipts"][0]["lines"][0]
    assert Decimal(receipt["base_unit_cost"]) == Decimal("3.33333333")
    assert Decimal(detail["inventory_impact"]["movements"][0]["total_cost"]) == Decimal(10)


def test_production_output_requires_explicit_expiry_and_records_its_lot(client: TestClient) -> None:
    raw = _create_raw_material("PROD-OUTPUT-LOT")
    assert _purchase(client, raw, "10", "2").status_code == 201
    recipe = _create_active_recipe(raw_material_id=raw)
    with SessionLocal() as session:
        recipe_row = session.get(Recipe, UUID(recipe))
        assert recipe_row is not None
        output = session.get(Product, recipe_row.product_id)
        assert output is not None
        output.lot_tracking_enabled = output.expiry_required = True
        session.commit()
    plan = _create_production(client, recipe_id=recipe)
    identity = plan["overview"]["id"]
    assert _post(client, f"/v1/admin/production/{identity}/release", {}).status_code == 200
    body = {
        "actual_output_qty": "20",
        "confirm_without_differences": True,
        "output_lot_code": "BREAD-EXPLICIT",
    }
    rejected = _post(client, f"/v1/admin/production/{identity}/complete", body)
    assert rejected.status_code == 409, rejected.text
    assert _stock(raw) == (Decimal(10), Decimal(4), Decimal(20))
    with SessionLocal() as session:
        assert not list(
            session.scalars(
                select(InventoryMovement).where(
                    InventoryMovement.source_document_id == UUID(identity)
                )
            )
        )
    expires_at = datetime.now(UTC).replace(microsecond=0) + timedelta(days=2)
    body["output_expires_at"] = expires_at.isoformat()
    completed = _post(client, f"/v1/admin/production/{identity}/complete", body)
    assert completed.status_code == 200, completed.text
    assert _stock(plan["product_recipe"]["product_id"])[2] == Decimal(8)
    with SessionLocal() as session:
        lot = session.scalar(select(InventoryLot).where(InventoryLot.lot_code == "BREAD-EXPLICIT"))
        assert lot is not None and lot.expires_at == expires_at
        assert session.scalar(
            select(InventoryLotBalance.quantity_on_hand).where(InventoryLotBalance.lot_id == lot.id)
        ) == Decimal(20)


def test_input_sale_and_usage_flags_are_independent_and_stock_policy_is_preserved(
    client: TestClient,
) -> None:
    body = {
        **_input_payload(code="DUAL-USE-INPUT"),
        "is_sellable": True,
        "is_usable_as_input": True,
    }
    headers = owner_headers()
    created = client.post("/v1/admin/inputs-supplies", headers=headers, json=body)
    assert created.status_code == 201, created.text
    identity = created.json()["overview"]["id"]
    body["is_active"] = False
    updated = client.patch(f"/v1/admin/inputs-supplies/{identity}", headers=headers, json=body)
    assert updated.status_code == 200, updated.text
    with SessionLocal() as session:
        product = session.get(Product, UUID(identity))
        assert product is not None
        assert not product.is_active and product.is_sellable and product.is_usable_as_input
    body["is_active"] = True
    assert (
        client.patch(
            f"/v1/admin/inputs-supplies/{identity}", headers=headers, json=body
        ).status_code
        == 200
    )
    body["is_sellable"] = False
    assert (
        client.patch(
            f"/v1/admin/inputs-supplies/{identity}", headers=headers, json=body
        ).status_code
        == 200
    )
    class_response = client.get(
        f"/v1/admin/product-classes/{body['product_class_id']}", headers=headers
    )
    assert class_response.status_code == 200
    class_detail = class_response.json()
    with SessionLocal() as session:
        products = session.scalars(
            select(Product).where(Product.product_class_id == UUID(str(body["product_class_id"])))
        ).all()
        assert class_detail["active_product_count"] == sum(
            product.is_active for product in products
        )
        assert class_detail["inactive_product_count"] == sum(
            not product.is_active for product in products
        )
    assert class_detail["product_count"] == (
        class_detail["active_product_count"] + class_detail["inactive_product_count"]
    )
    assert _purchase(client, identity, "1", "2").status_code == 201
    changed = {**body, "lot_tracking_enabled": True, "expiry_required": True}
    rejected = client.patch(f"/v1/admin/inputs-supplies/{identity}", headers=headers, json=changed)
    assert rejected.status_code == 409, rejected.text
    assert "explicit reconciliation" in rejected.json()["message"]
    with SessionLocal() as session:
        product = session.get(Product, UUID(identity))
        assert product is not None
        assert not product.lot_tracking_enabled and not product.expiry_required


def test_reserved_input_expiring_after_release_can_only_be_reconciled_as_explicit_waste(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    from zeromerma_api.modules.inventory.application import lots

    raw = _create_raw_material("PROD-EXPIRED-RESERVATION")
    with SessionLocal() as session:
        product = session.get(Product, UUID(raw))
        assert product is not None
        product.lot_tracking_enabled = product.expiry_required = True
        session.commit()
    expiry = datetime.now(UTC).replace(microsecond=0) + timedelta(days=1)
    for code, expires_at in (
        ("RESERVED-EARLY", expiry),
        ("FRESH-LATER", expiry + timedelta(days=7)),
    ):
        purchased = _purchase(
            client, raw, "4", "2", lot_code=code, expires_at=expires_at.isoformat()
        )
        assert purchased.status_code == 201, purchased.text
    plan = _released(client, product_id=raw)
    identity = plan["overview"]["id"]
    assert _stock(raw) == (Decimal(8), Decimal(4), Decimal(16))

    class ExpiredClock(datetime):
        @classmethod
        def now(cls, tz: Any = None) -> datetime:
            instant = expiry + timedelta(seconds=1)
            return instant.astimezone(tz) if tz is not None else instant.replace(tzinfo=None)

    # Advance the decision clock without mutating the immutable admitted lot expiry.
    monkeypatch.setattr(lots, "datetime", ExpiredClock)
    rejected = _post(
        client,
        f"/v1/admin/production/{identity}/complete",
        {"actual_output_qty": "20", "confirm_without_differences": True},
    )
    assert rejected.status_code == 409, rejected.text
    assert "expired" in rejected.json()["message"].lower()
    assert _stock(raw) == (Decimal(8), Decimal(4), Decimal(16))
    key = new_idempotency_key()
    body = {
        "actual_output_qty": "0",
        "finish_as": "CANCELLED",
        "variance_reason": "The reserved physical input expired before production.",
        "inputs": [
            {
                "input_product_id": raw,
                "consumed_qty": "0",
                "returned_qty": "0",
                "waste_qty": "4",
                "remainder_qty": "0",
                "reason": "Observed expired reserved input discarded.",
            }
        ],
    }
    completed = _post(client, f"/v1/admin/production/{identity}/complete", body, key=key)
    assert completed.status_code == 200, completed.text
    assert completed.json()["status"] == "CANCELLED"
    assert _stock(raw) == (Decimal(4), Decimal(0), Decimal(8))
    assert _stock(raw, "WASTE") == (Decimal(4), Decimal(0), Decimal(8))
    with SessionLocal() as session:
        physical = session.execute(
            select(
                InventoryLot.lot_code,
                InventoryLotBalance.location_code,
                InventoryLotBalance.quantity_on_hand,
            )
            .join(InventoryLotBalance, InventoryLotBalance.lot_id == InventoryLot.id)
            .where(InventoryLot.product_id == UUID(raw))
        ).all()
        assert set(physical) == {
            ("RESERVED-EARLY", "BACKROOM", Decimal(0)),
            ("RESERVED-EARLY", "WASTE", Decimal(4)),
            ("FRESH-LATER", "BACKROOM", Decimal(4)),
        }
        movements = session.execute(
            select(
                InventoryMovement.id,
                InventoryMovementLotAllocation.lot_id,
                InventoryMovementLotAllocation.quantity,
            )
            .join(
                InventoryMovementLotAllocation,
                InventoryMovementLotAllocation.movement_id == InventoryMovement.id,
            )
            .where(InventoryMovement.source_document_id == UUID(identity))
        ).all()
        assert len(movements) == 2
    replay = _post(client, f"/v1/admin/production/{identity}/complete", body, key=key)
    assert replay.json() == completed.json()
    assert _stock(raw) == (Decimal(4), Decimal(0), Decimal(8))
    assert _stock(raw, "WASTE") == (Decimal(4), Decimal(0), Decimal(8))
