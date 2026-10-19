"""Read-only diagnosis and owner-authorized opening/rebuild from immutable evidence."""

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.orm import Session

from zeromerma_api.db.access_scope import bind_authorization_scope
from zeromerma_api.modules.audit.application.service import AuditRecorder
from zeromerma_api.modules.branches.infrastructure.models import Branch
from zeromerma_api.modules.cash.infrastructure.models import CashSession
from zeromerma_api.modules.catalog.infrastructure.models import Product
from zeromerma_api.modules.idempotency.application.context import execution
from zeromerma_api.modules.idempotency.application.schemas import (
    CommandContext,
    CommandResult,
    IdempotencyResult,
    ResponsePolicy,
)
from zeromerma_api.modules.idempotency.application.service import IdempotencyExecutor
from zeromerma_api.modules.identity.application.authorization import (
    require_branches,
    resolve_authorization,
)
from zeromerma_api.modules.identity.application.schemas import AuthenticatedUser
from zeromerma_api.modules.inventory.application.mutations import (
    InventoryBalanceKey,
    create_inventory_lot,
    lock_inventory_balances,
)
from zeromerma_api.modules.inventory.domain.exceptions import InventoryValidationError
from zeromerma_api.modules.inventory.domain.quantities import (
    InventoryLotQuantity,
    inventory_calculation,
    normalize_uom,
)
from zeromerma_api.modules.inventory.domain.reconciliation import (
    InventoryReconciliationItem,
    InventoryReconciliationManifest,
    evidence_digest,
)
from zeromerma_api.modules.inventory.infrastructure.lot_models import (
    InventoryLotBalance,
    InventoryMovementLotAllocation,
    InventoryReservationEventLotAllocation,
)
from zeromerma_api.modules.inventory.infrastructure.models import (
    InventoryBalance,
    InventoryMovement,
    InventoryReservation,
    InventoryReservationEvent,
)
from zeromerma_api.modules.inventory.infrastructure.reconciliation_models import (
    InventoryReconciliationManifest as ManifestRecord,
)
from zeromerma_api.modules.inventory.infrastructure.reconciliation_models import (
    InventoryReconciliationRow,
)
from zeromerma_api.modules.outbox.application.service import OutboxWriter


class ReconciliationResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    manifest_id: UUID
    row_key: str
    action: str
    inventory_movement_id: UUID | None
    before_sha256: str
    after_sha256: str


@inventory_calculation
def _key_state(session: Session, key: InventoryBalanceKey) -> dict[str, Any]:
    product = session.get(Product, key.product_id)
    if product is None:
        raise InventoryValidationError("The manifest product does not exist.")
    criteria = dict(
        branch_id=key.branch_id, product_id=key.product_id, location_code=key.location_code
    )
    balance = session.scalar(select(InventoryBalance).filter_by(**criteria))
    movements = list(
        session.scalars(
            select(InventoryMovement)
            .filter_by(**criteria)
            .order_by(InventoryMovement.recorded_at, InventoryMovement.id)
        )
    )
    reservations = list(session.scalars(select(InventoryReservation).filter_by(**criteria)))
    events = list(
        session.scalars(
            select(InventoryReservationEvent)
            .where(InventoryReservationEvent.reservation_id.in_([item.id for item in reservations]))
            .order_by(InventoryReservationEvent.id)
        )
    )
    movement_lots = list(
        session.scalars(
            select(InventoryMovementLotAllocation)
            .where(InventoryMovementLotAllocation.movement_id.in_([item.id for item in movements]))
            .order_by(InventoryMovementLotAllocation.id)
        )
    )
    event_lots = list(
        session.scalars(
            select(InventoryReservationEventLotAllocation)
            .where(
                InventoryReservationEventLotAllocation.reservation_event_id.in_(
                    [item.id for item in events]
                )
            )
            .order_by(InventoryReservationEventLotAllocation.id)
        )
    )
    lot_balances = list(session.scalars(select(InventoryLotBalance).filter_by(**criteria)))
    anomalies: list[str] = []
    quantity = Decimal(0)
    value: Decimal | None = Decimal(0)
    for movement in movements:
        direction = Decimal(1) if movement.direction == "IN" else Decimal(-1)
        quantity += direction * movement.quantity
        if movement.context_version != 1:
            anomalies.append("UNCLASSIFIED_LEGACY_CAUSE")
        if normalize_uom(movement.unit_of_measure) != normalize_uom(product.unit_of_measure):
            anomalies.append("INCOMPATIBLE_UOM")
        if movement.balance_after != quantity:
            anomalies.append("UNEXPLAINED_HISTORY_BALANCE")
        value = (
            None
            if value is None or movement.total_cost is None
            else value + direction * movement.total_cost
        )
        if quantity == 0:
            value = Decimal(0)
        if quantity < 0:
            value = None
    reserved = sum(
        (event.quantity if event.event_type == "RESERVE" else -event.quantity for event in events),
        Decimal(0),
    )
    if reserved < 0:
        anomalies.append("NEGATIVE_RESERVED_EVIDENCE")
    if quantity < 0:
        anomalies.append("NEGATIVE_STOCK_REQUIRES_RECONCILIATION")
    if value is not None and value < 0:
        anomalies.append("NEGATIVE_VALUATION_EVIDENCE")
    lots: dict[str, dict[str, str]] = {}
    directions = {
        item.id: Decimal(1) if item.direction == "IN" else Decimal(-1) for item in movements
    }
    event_directions = {
        item.id: Decimal(1) if item.event_type == "RESERVE" else Decimal(-1) for item in events
    }
    for allocation in movement_lots:
        item = lots.setdefault(str(allocation.lot_id), {"quantity": "0", "reserved": "0"})
        item["quantity"] = str(
            Decimal(item["quantity"]) + directions[allocation.movement_id] * allocation.quantity
        )
    for event_allocation in event_lots:
        item = lots.setdefault(str(event_allocation.lot_id), {"quantity": "0", "reserved": "0"})
        item["reserved"] = str(
            Decimal(item["reserved"])
            + event_directions[event_allocation.reservation_event_id] * event_allocation.quantity
        )
    if product.lot_tracking_enabled and (
        sum((Decimal(item["quantity"]) for item in lots.values()), Decimal(0)) != quantity
        or sum((Decimal(item["reserved"]) for item in lots.values()), Decimal(0)) != reserved
        or any(
            Decimal(item["quantity"]) < Decimal(item["reserved"]) or Decimal(item["reserved"]) < 0
            for item in lots.values()
        )
    ):
        anomalies.append("LOT_EVIDENCE_DOES_NOT_RECONCILE")
    history = {
        "movements": [
            (
                str(item.id),
                item.context_version,
                item.direction,
                str(item.quantity),
                item.unit_of_measure,
                str(item.total_cost),
                str(item.balance_after),
                str(item.idempotency_record_id),
                item.causal_effect_code,
            )
            for item in movements
        ],
        "events": [
            (str(item.id), str(item.reservation_id), item.event_type, str(item.quantity))
            for item in events
        ],
        "movement_lots": [
            (str(item.movement_id), str(item.lot_id), str(item.quantity)) for item in movement_lots
        ],
        "event_lots": [
            (str(item.reservation_event_id), str(item.lot_id), str(item.quantity))
            for item in event_lots
        ],
    }
    actual = {
        "quantity": str(balance.quantity_on_hand if balance else Decimal(0)),
        "reserved": str(balance.quantity_reserved if balance else Decimal(0)),
        "inventory_value": str(balance.inventory_value)
        if balance and balance.inventory_value is not None
        else None,
        "lots": {
            str(item.lot_id): {
                "quantity": str(item.quantity_on_hand),
                "reserved": str(item.quantity_reserved),
            }
            for item in lot_balances
        },
    }
    expected = {
        "quantity": str(quantity),
        "reserved": str(reserved),
        "inventory_value": str(value) if value is not None else None,
        "lots": dict(sorted(lots.items())),
    }

    def normalized(projection: dict[str, Any]) -> dict[str, Any]:
        return {
            "quantity": Decimal(projection["quantity"]),
            "reserved": Decimal(projection["reserved"]),
            "inventory_value": Decimal(projection["inventory_value"])
            if projection["inventory_value"] is not None
            else None,
            "lots": {
                lot: (Decimal(amounts["quantity"]), Decimal(amounts["reserved"]))
                for lot, amounts in projection["lots"].items()
                if Decimal(amounts["quantity"]) or Decimal(amounts["reserved"])
            },
        }

    return {
        "product_id": str(key.product_id),
        "location_code": key.location_code,
        "unit_of_measure": product.unit_of_measure,
        "movement_count": len(movements),
        "reservation_event_count": len(events),
        "ledger_sha256": evidence_digest(history),
        "projection_sha256": evidence_digest(actual),
        "actual": actual,
        "expected": expected,
        "matches": normalized(actual) == normalized(expected),
        "anomalies": sorted(set(anomalies)),
        "rebuildable": bool(movements or events) and not anomalies,
        "valuation_status": "KNOWN" if value is not None else "UNAVAILABLE",
        "available_quantity": str(quantity - reserved),
        "materialized_available_quantity": str(
            balance.quantity_on_hand - balance.quantity_reserved if balance else Decimal(0)
        ),
    }


def diagnose_inventory_state(session: Session, *, branch_id: UUID) -> dict[str, Any]:
    """May run inside a PostgreSQL READ ONLY transaction; never flush or infer authority."""
    with session.no_autoflush:
        keys: set[InventoryBalanceKey] = set()
        for model in (
            InventoryBalance,
            InventoryMovement,
            InventoryReservation,
            InventoryLotBalance,
        ):
            keys.update(
                InventoryBalanceKey(branch_id, product, location)
                for product, location in session.execute(
                    select(model.product_id, model.location_code).where(
                        model.branch_id == branch_id
                    )
                )
            )
        rows = [_key_state(session, key) for key in sorted(keys)]
    return {
        "read_only": True,
        "branch_id": str(branch_id),
        "keys": rows,
        "difference_count": sum(not row["matches"] for row in rows),
        "unrebuildable_count": sum(not row["rebuildable"] for row in rows),
        "production_reconciliation_signed": False,
    }


def _validate_row(
    session: Session,
    manifest: InventoryReconciliationManifest,
    row: InventoryReconciliationItem,
    state: dict[str, Any],
) -> None:
    manifest.require_productive_source()
    manifest.require_cutover(datetime.now(UTC))
    product = session.get(Product, row.product_id)
    if product is None or not product.is_inventory_tracked:
        raise InventoryValidationError("The opening/rebuild product must be inventory tracked.")
    if normalize_uom(row.unit_of_measure) != normalize_uom(product.unit_of_measure):
        raise InventoryValidationError("The manifest base unit differs from the product.")
    if row.action == "REBUILD":
        if not state["rebuildable"] or row.expected_ledger_sha256 != state["ledger_sha256"]:
            raise InventoryValidationError("Rebuild requires unchanged, complete causal history.")
        return
    actual = state["actual"]
    if (
        state["movement_count"]
        or state["reservation_event_count"]
        or Decimal(actual["quantity"])
        or Decimal(actual["reserved"])
        or actual["lots"]
        or actual["inventory_value"] not in (None, "0", "0.00000000")
    ):
        raise InventoryValidationError(
            "Opening requires an empty stock key, never a legacy balance authority."
        )
    if row.quantity and product.lot_tracking_enabled != bool(row.lots):
        raise InventoryValidationError(
            "Opening lot evidence must match the product tracking policy."
        )
    for lot in row.lots:
        if product.expiry_required and lot.expires_at is None:
            raise InventoryValidationError(
                "Opening requires the actual expiry for every controlled lot."
            )
        if (
            lot.expires_at is not None
            and lot.expires_at <= datetime.now(UTC)
            and row.location_code not in {"QUARANTINE", "WASTE"}
        ):
            raise InventoryValidationError("Expired opening stock must be quarantined or disposed.")


def dry_run_inventory_reconciliation(
    session: Session, *, manifest: InventoryReconciliationManifest
) -> dict[str, Any]:
    with session.no_autoflush:
        stored = session.get(ManifestRecord, manifest.manifest_id)
        conflict = stored is not None and stored.manifest_sha256 != manifest.digest()
        rows = []
        for row in manifest.rows:
            applied = session.scalar(
                select(InventoryReconciliationRow).where(
                    InventoryReconciliationRow.manifest_id == manifest.manifest_id,
                    InventoryReconciliationRow.row_key == row.row_key,
                )
            )
            state = _key_state(
                session, InventoryBalanceKey(manifest.branch_id, row.product_id, row.location_code)
            )
            error = "The admitted manifest cannot change." if conflict else None
            try:
                manifest.require_productive_source()
                if applied is None:
                    _validate_row(session, manifest, row, state)
                elif applied.row_sha256 != row.digest():
                    raise InventoryValidationError("An applied row cannot change.")
            except InventoryValidationError as issue:
                error = str(issue)
            rows.append(
                {
                    "row_key": row.row_key,
                    "row_sha256": row.digest(),
                    "status": "REJECTED" if error else "APPLIED" if applied else "READY",
                    "reason": error,
                    "before": state,
                    "action": row.action,
                }
            )
    return {
        "read_only": True,
        "manifest_sha256": manifest.digest(),
        "rows": rows,
        "can_apply": all(row["status"] in {"READY", "APPLIED"} for row in rows),
        "approval_authenticity_verified": False,
        "production_reconciliation_signed": False,
    }


@inventory_calculation
def apply_inventory_reconciliation_row(
    session: Session,
    *,
    current_user: AuthenticatedUser,
    manifest: InventoryReconciliationManifest,
    row_key: str,
    expected_manifest_sha256: str,
    controlled_window_confirmed: bool,
) -> IdempotencyResult:
    manifest.require_productive_source()
    if not controlled_window_confirmed or expected_manifest_sha256 != manifest.digest():
        raise InventoryValidationError(
            "Apply requires the reviewed exact hash and controlled window."
        )
    row = next((item for item in manifest.rows if item.row_key == row_key), None)
    if row is None:
        raise InventoryValidationError("The row is not in the reviewed manifest.")
    if current_user.authorization_surface != "BACKOFFICE":
        raise HTTPException(
            403, "Inventory reconciliation requires authenticated Backoffice authority."
        )
    bind_authorization_scope(
        session,
        user=current_user,
        capabilities=("inventory.adjust",),
        mutation=True,
        global_only=True,
        surface="BACKOFFICE",
    )

    def authorize(current: Session, context: CommandContext) -> None:
        refreshed = resolve_authorization(current, current_user, surface="BACKOFFICE")
        require_branches(refreshed, "inventory.adjust", [manifest.branch_id], global_only=True)
        if not refreshed.is_superadministrator or refreshed.password_reset_required:
            raise HTTPException(
                403, "Only the designated owner may apply inventory reconciliation."
            )

    def action(current: Session) -> CommandResult:
        owner = execution(current)
        assert owner is not None and owner.record is not None
        branch = current.scalar(
            select(Branch).where(Branch.id == manifest.branch_id).with_for_update(key_share=True)
        )
        if branch is None or not branch.is_active:
            raise InventoryValidationError("The approved branch must be active.")
        if (
            current.scalar(
                select(CashSession.id)
                .where(
                    CashSession.branch_id == manifest.branch_id,
                    CashSession.status.in_(("OPEN", "CLOSING")),
                )
                .limit(1)
            )
            is not None
        ):
            raise InventoryValidationError(
                "Reconciliation requires a window without open cash sessions."
            )
        stored = current.get(ManifestRecord, manifest.manifest_id)
        if stored is not None and stored.manifest_sha256 != manifest.digest():
            raise InventoryValidationError("The admitted manifest is immutable.")
        key = InventoryBalanceKey(manifest.branch_id, row.product_id, row.location_code)
        locked = lock_inventory_balances(current, [key])
        before = _key_state(current, key)
        _validate_row(current, manifest, row, before)
        if stored is None:
            current.add(
                ManifestRecord(
                    id=manifest.manifest_id,
                    branch_id=manifest.branch_id,
                    manifest_sha256=manifest.digest(),
                    evidence=manifest.model_dump(mode="json"),
                    admitted_by_user_id=current_user.id,
                )
            )
            current.flush()
        movement_id = None
        if row.action == "OPENING" and row.quantity:
            allocations = []
            for lot in row.lots:
                identity = create_inventory_lot(
                    current,
                    product_id=row.product_id,
                    lot_code=lot.lot_code,
                    expires_at=lot.expires_at,
                    source_document_type="INVENTORY_OPENING",
                    source_document_id=manifest.manifest_id,
                    source_line_id=None,
                    branch_id=manifest.branch_id,
                    operator_user_id=current_user.id,
                )
                allocations.append(InventoryLotQuantity(identity.id, lot.quantity))
            movement = locked.apply_delta(
                key,
                delta=row.quantity,
                movement_type="OPENING_ADJUSTMENT",
                unit_of_measure=row.unit_of_measure,
                source_document_type="INVENTORY_OPENING",
                source_document_id=manifest.manifest_id,
                operator_user_id=current_user.id,
                causal_effect_code=f"opening:{row.row_key}",
                reason=row.reason,
                notes=None,
                total_cost=row.inventory_value,
                cost_evidence_reference=f"opening:{manifest.manifest_id}:{row.row_key}"
                if row.inventory_value is not None
                else None,
                lot_allocations=allocations or None,
            )
            movement_id = movement.id
        elif row.action == "REBUILD":
            expected = before["expected"]
            balance = locked.balance(key)
            balance.quantity_on_hand = Decimal(expected["quantity"])
            balance.quantity_reserved = Decimal(expected["reserved"])
            balance.inventory_value = (
                Decimal(expected["inventory_value"])
                if expected["inventory_value"] is not None
                else None
            )
            existing = {
                str(item.lot_id): item
                for item in current.scalars(
                    select(InventoryLotBalance).filter_by(
                        branch_id=key.branch_id,
                        product_id=key.product_id,
                        location_code=key.location_code,
                    )
                )
            }
            for lot_id in sorted(set(existing) | set(expected["lots"])):
                lot_balance = existing.get(lot_id)
                if lot_balance is None:
                    lot_balance = InventoryLotBalance(
                        id=uuid4(),
                        branch_id=key.branch_id,
                        product_id=key.product_id,
                        location_code=key.location_code,
                        lot_id=UUID(lot_id),
                    )
                    current.add(lot_balance)
                amounts = expected["lots"].get(lot_id, {"quantity": "0", "reserved": "0"})
                lot_balance.quantity_on_hand = Decimal(amounts["quantity"])
                lot_balance.quantity_reserved = Decimal(amounts["reserved"])
        current.flush()
        after = _key_state(current, key)
        if not after["matches"]:
            raise InventoryValidationError(
                "The resulting projections do not reconcile with immutable evidence."
            )
        trace = {
            "manifest_id": str(manifest.manifest_id),
            "manifest_sha256": manifest.digest(),
            "row_key": row.row_key,
            "row_sha256": row.digest(),
            "action": row.action,
            "approval_reference": manifest.approval_reference,
            "approval_evidence_sha256": manifest.approval_evidence_sha256,
            "approval_authenticity_verified": False,
            "source_evidence_sha256": row.evidence_sha256,
            "before": before,
            "after": after,
        }
        current.add(
            InventoryReconciliationRow(
                id=uuid4(),
                manifest_id=manifest.manifest_id,
                branch_id=manifest.branch_id,
                row_key=row.row_key,
                row_sha256=row.digest(),
                action=row.action,
                idempotency_record_id=owner.record.id,
                inventory_movement_id=movement_id,
                reconciliation=trace,
            )
        )
        AuditRecorder().record(
            current,
            actor_id=current_user.id,
            action="inventory_reconciliation.row_applied",
            resource_type="inventory_reconciliation",
            resource_id=str(manifest.manifest_id),
            branch_id=manifest.branch_id,
            request_id=None,
            metadata=trace,
        )
        OutboxWriter().append(
            current,
            aggregate_type="inventory_reconciliation",
            aggregate_id=str(manifest.manifest_id),
            event_name="inventory_reconciliation.row_applied.v1",
            payload=trace,
        )
        return CommandResult(
            status_code=201,
            snapshot=ReconciliationResult(
                manifest_id=manifest.manifest_id,
                row_key=row.row_key,
                action=row.action,
                inventory_movement_id=movement_id,
                before_sha256=before["projection_sha256"],
                after_sha256=after["projection_sha256"],
            ),
        )

    return IdempotencyExecutor().execute(
        session,
        key=row.idempotency_key,
        operation_code="inventory_reconciliation.apply_row",
        payload={
            "manifest_sha256": manifest.digest(),
            "row_key": row.row_key,
            "row_sha256": row.digest(),
        },
        resolve_context=lambda current, saved: CommandContext(
            actor_user_id=current_user.id, surface="BACKOFFICE", branch_id=manifest.branch_id
        ),
        authorize=authorize,
        action=action,
        response_policy=ResponsePolicy(snapshot_model=ReconciliationResult),
    )
