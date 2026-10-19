"""Explicit physical dispositions never change refund or return entitlement facts."""

from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from zeromerma_api.db.access_scope import bind_authorization_scope
from zeromerma_api.modules.audit.application.service import AuditRecorder
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
from zeromerma_api.modules.identity.application.schemas import AuthenticatedUser, CapabilityCode
from zeromerma_api.modules.inventory.application.disposition_schemas import (
    InventoryDispositionRequest,
    InventoryDispositionResult,
)
from zeromerma_api.modules.inventory.application.mutations import (
    InventoryBalanceKey,
    lock_inventory_balances,
)
from zeromerma_api.modules.inventory.domain.quantities import InventoryLotQuantity
from zeromerma_api.modules.inventory.infrastructure.models import InventoryMovement
from zeromerma_api.modules.operations.application.physical_inventory import OperationMovementCause
from zeromerma_api.modules.outbox.application.service import OutboxWriter
from zeromerma_api.modules.returns.infrastructure.models import (
    ReturnDispositionAllocation,
    SaleReturn,
    SaleReturnLine,
)

POLICY = ResponsePolicy(snapshot_model=InventoryDispositionResult)
OPERATIONS = {
    "RETURN_CORRECTION": "inventory.return_compensate",
    "QUARANTINE_RELEASE": "inventory.quarantine_release",
}


def disposition_capability(kind: str) -> CapabilityCode:
    return "returns_corrections.manage" if kind == "RETURN_CORRECTION" else "inventory.adjust"


def bind_disposition(
    session: Session, user: AuthenticatedUser, kind: str, *, mutation: bool
) -> None:
    if user.authorization_surface != "BACKOFFICE":
        raise HTTPException(403, "Backoffice authority is required.")
    bind_authorization_scope(
        session,
        user=user,
        capabilities=(disposition_capability(kind),),
        mutation=mutation,
        surface="BACKOFFICE",
    )


def authorize_disposition(
    session: Session, user: AuthenticatedUser, context: CommandContext, kind: str
) -> None:
    if user.authorization_surface != "BACKOFFICE" or context.branch_id is None:
        raise HTTPException(403, "Backoffice branch authority is required.")
    require_branches(
        resolve_authorization(session, user, surface="BACKOFFICE"),
        disposition_capability(kind),
        [context.branch_id],
    )


def commit_disposition(
    session: Session,
    *,
    current_user: AuthenticatedUser,
    command: InventoryDispositionRequest,
    key: UUID,
    request_id: str | None,
) -> IdempotencyResult:
    bind_disposition(session, current_user, command.kind, mutation=True)

    def action(current: Session) -> CommandResult:
        owner = execution(current)
        if owner is None or owner.record is None:
            raise RuntimeError("Disposition requires its command owner.")
        product = current.get(Product, command.product_id)
        if product is None or not product.is_inventory_tracked:
            raise HTTPException(409, "Physical disposition requires an inventory-tracked product.")
        if command.destination == "COUNTER" and not (product.is_active and product.is_sellable):
            raise HTTPException(409, "Only an active sellable product can return to the counter.")
        original = None
        lot_id = command.lot_id
        source = "QUARANTINE"
        if command.return_allocation_id is not None:
            record = current.execute(
                select(ReturnDispositionAllocation, SaleReturn)
                .join(
                    SaleReturnLine,
                    SaleReturnLine.id == ReturnDispositionAllocation.sale_return_line_id,
                )
                .join(SaleReturn, SaleReturn.id == SaleReturnLine.sale_return_id)
                .where(
                    ReturnDispositionAllocation.id == command.return_allocation_id,
                    SaleReturn.branch_id == command.branch_id,
                )
                .with_for_update(of=SaleReturn)
            ).first()
            if record is None:
                raise HTTPException(404, "Return allocation was not found in this branch.")
            allocation = record.ReturnDispositionAllocation
            if allocation.returned_product_id != command.product_id:
                raise HTTPException(409, "The original allocation belongs to a different product.")
            original = (
                current.get(InventoryMovement, allocation.inventory_movement_id)
                if allocation.inventory_movement_id
                else None
            )
            if original is None or original.direction != "IN":
                raise HTTPException(409, "The original return lacks physical inbound evidence.")
            source = original.location_code
            lot_id = allocation.lot_id
        if source == command.destination:
            raise HTTPException(409, "The stock is already in the requested physical location.")
        if product.lot_tracking_enabled and lot_id is None:
            raise HTTPException(409, "Select the exact physical lot to inspect or dispose.")
        balances = lock_inventory_balances(
            current,
            [
                InventoryBalanceKey(command.branch_id, command.product_id, location)
                for location in {source, command.destination}
            ],
        )
        lots = [InventoryLotQuantity(lot_id, command.quantity)] if lot_id else None
        cause: OperationMovementCause = dict(
            movement_type="INVENTORY_COMPENSATION" if original else "QUARANTINE_RELEASE",
            unit_of_measure=product.unit_of_measure,
            source_document_type="INVENTORY_DISPOSITION",
            source_document_id=owner.record.id,
            source_line_id=command.return_allocation_id or owner.record.id,
            operator_user_id=current_user.id,
            reason=command.reason,
            notes=command.notes,
        )
        outbound = balances.apply_delta(
            InventoryBalanceKey(command.branch_id, command.product_id, source),
            delta=-command.quantity,
            reversal_of_movement_id=original.id if original else None,
            causal_effect_code="disposition:out",
            lot_allocations=lots,
            **cause,
        )
        inbound = balances.apply_delta(
            InventoryBalanceKey(command.branch_id, command.product_id, command.destination),
            delta=command.quantity,
            causal_effect_code="disposition:in",
            lot_allocations=lots,
            unit_cost=outbound.unit_cost,
            total_cost=outbound.total_cost,
            cost_evidence_reference=str(outbound.id) if outbound.total_cost is not None else None,
            **cause,
        )
        result = InventoryDispositionResult(
            operation_id=owner.record.id,
            branch_id=command.branch_id,
            product_id=command.product_id,
            kind=command.kind,
            source=source,
            destination=command.destination,
            quantity=command.quantity,
            return_allocation_id=command.return_allocation_id,
            lot_id=lot_id,
            movement_ids=[outbound.id, inbound.id],
        )
        facts = {
            **result.model_dump(mode="json"),
            "reason": command.reason,
            "inspection_passed": command.inspection_passed,
            "notes": command.notes,
        }
        AuditRecorder().record(
            current,
            actor_id=current_user.id,
            action="inventory.disposition",
            resource_type="inventory_disposition",
            resource_id=str(owner.record.id),
            branch_id=command.branch_id,
            request_id=request_id,
            metadata=facts,
        )
        OutboxWriter().append(
            current,
            aggregate_type="inventory_disposition",
            aggregate_id=str(owner.record.id),
            event_name="inventory.disposition.v1",
            payload=facts,
            headers={"request_id": request_id} if request_id else {},
        )
        return CommandResult(
            status_code=201,
            snapshot=result,
            resource_type="inventory_disposition",
            resource_id=str(owner.record.id),
        )

    return IdempotencyExecutor().execute(
        session,
        key=key,
        operation_code=OPERATIONS[command.kind],
        payload=command,
        resolve_context=lambda _current, _saved: CommandContext(
            actor_user_id=current_user.id, surface="BACKOFFICE", branch_id=command.branch_id
        ),
        authorize=lambda current, context: authorize_disposition(
            current, current_user, context, command.kind
        ),
        action=action,
        response_policy=POLICY,
        request_id=request_id,
    )
