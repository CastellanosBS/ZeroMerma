"""Opt-in synthetic stock with real command/ledger evidence in guarded disposable databases."""

import os
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from zeromerma_api.modules.audit.application.service import AuditRecorder
from zeromerma_api.modules.catalog.infrastructure.models import Product
from zeromerma_api.modules.idempotency.application.schemas import (
    CommandContext,
    CommandResult,
    ResponsePolicy,
)
from zeromerma_api.modules.idempotency.application.service import IdempotencyExecutor
from zeromerma_api.modules.inventory.application.mutations import (
    InventoryBalanceKey,
    create_inventory_lot,
    lock_inventory_balances,
)
from zeromerma_api.modules.inventory.domain.quantities import InventoryLotQuantity
from zeromerma_api.modules.outbox.application.service import OutboxWriter
from zeromerma_api.testing.database_safety import (
    assert_authorized_destructive_connection,
    load_destructive_test_database_config,
)
from zeromerma_api.testing.idempotency import new_idempotency_key


class TestInventoryResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    movement_ids: list[UUID]


def seed_test_inventory(
    session: Session,
    *,
    branch_id: UUID,
    actor_user_id: UUID,
    product_quantities: Mapping[UUID, Decimal],
    location_code: str,
    fixture_reference: str,
    unit_cost: Decimal | None = None,
) -> list[UUID]:
    """Call only where a test explicitly needs stock; never autoseed ordinary business fixtures."""
    config = load_destructive_test_database_config(os.environ)
    assert_authorized_destructive_connection(session.connection(), config)
    if not fixture_reference.strip() or len(fixture_reference) > 160:
        raise ValueError("An explicit bounded synthetic fixture reference is required.")
    source_id = uuid4()

    def action(current: Session) -> CommandResult:
        keys = [
            InventoryBalanceKey(branch_id, product_id, location_code)
            for product_id in product_quantities
        ]
        locked = lock_inventory_balances(current, keys)
        movements = []
        for key in sorted(keys):
            product = current.get(Product, key.product_id)
            assert product is not None
            quantity = product_quantities[key.product_id]
            if quantity <= 0:
                raise ValueError("Synthetic opening stock must be positive.")
            allocations = None
            if product.lot_tracking_enabled:
                lot = create_inventory_lot(
                    current,
                    product_id=product.id,
                    lot_code=f"TEST:{source_id}:{product.id}",
                    expires_at=datetime.now(UTC) + timedelta(days=30)
                    if product.expiry_required
                    else None,
                    source_document_type="TEST_INVENTORY_OPENING",
                    source_document_id=source_id,
                    source_line_id=product.id,
                    branch_id=branch_id,
                    operator_user_id=actor_user_id,
                )
                allocations = [InventoryLotQuantity(lot.id, quantity)]
            movement = locked.apply_delta(
                key,
                delta=quantity,
                movement_type="OPENING_ADJUSTMENT",
                unit_of_measure=product.unit_of_measure,
                source_document_type="TEST_INVENTORY_OPENING",
                source_document_id=source_id,
                source_line_id=product.id,
                operator_user_id=actor_user_id,
                reason=fixture_reference,
                notes="SYNTHETIC_TEST_ONLY",
                causal_effect_code=f"fixture:{product.id}",
                unit_cost=unit_cost,
                cost_evidence_reference=f"synthetic:{source_id}" if unit_cost is not None else None,
                lot_allocations=allocations,
            )
            movements.append(movement)
        trace = {
            "fixture_reference": fixture_reference,
            "classification": "DEVELOPMENT_DEMO_TEST",
            "movement_ids": [str(item.id) for item in movements],
        }
        AuditRecorder().record(
            current,
            actor_id=actor_user_id,
            action="inventory.test_opening.recorded",
            resource_type="test_inventory_opening",
            resource_id=str(source_id),
            branch_id=branch_id,
            request_id=None,
            metadata=trace,
        )
        OutboxWriter().append(
            current,
            aggregate_type="test_inventory_opening",
            aggregate_id=str(source_id),
            event_name="inventory.test_opening.recorded.v1",
            payload=trace,
        )
        return CommandResult(
            status_code=201,
            snapshot=TestInventoryResult(movement_ids=[item.id for item in movements]),
        )

    result = IdempotencyExecutor().execute(
        session,
        key=new_idempotency_key(),
        operation_code="inventory.test_opening",
        payload={"source_id": str(source_id)},
        resolve_context=lambda current, saved: CommandContext(
            actor_user_id=actor_user_id, surface="BACKOFFICE", branch_id=branch_id
        ),
        authorize=lambda current, context: None,
        action=action,
        response_policy=ResponsePolicy(snapshot_model=TestInventoryResult),
    )
    return [UUID(value) for value in result.payload["movement_ids"]]
