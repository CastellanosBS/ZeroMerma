from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from zeromerma_api.modules.audit.application.service import AuditRecorder
from zeromerma_api.modules.branches.infrastructure.models import Branch
from zeromerma_api.modules.catalog.infrastructure.models import Product
from zeromerma_api.modules.idempotency.application.context import execution
from zeromerma_api.modules.idempotency.domain.exceptions import IdempotencyBoundaryError
from zeromerma_api.modules.identity.application.schemas import AuthenticatedUser
from zeromerma_api.modules.inventory.application.mutations import (
    InventoryBalanceKey,
    LockedInventoryBalances,
    lock_inventory_balances,
)
from zeromerma_api.modules.inventory.domain.costs import COST_QUANTUM
from zeromerma_api.modules.inventory.domain.exceptions import InventoryValidationError
from zeromerma_api.modules.inventory.domain.quantities import (
    InventoryLotQuantity,
    inventory_calculation,
    normalize_uom,
)
from zeromerma_api.modules.inventory.infrastructure.models import InventoryMovement
from zeromerma_api.modules.operations.infrastructure.models import (
    OperationDocument,
    OperationDocumentLine,
)
from zeromerma_api.modules.outbox.application.service import OutboxWriter
from zeromerma_api.modules.transfers.application.admin_schemas import AdminTransferReceiptLineInput
from zeromerma_api.modules.transfers.application.lot_queries import shipment_lot_progress
from zeromerma_api.modules.transfers.application.schemas import (
    AdminTransferResolveRequest,
    TransferCommandResultView,
    TransferLotAllocationRequest,
    TransferReceiptLineRequest,
)
from zeromerma_api.modules.transfers.application.workflow import (
    command_snapshot,
    command_trace,
    lock_shipment,
    progress,
)
from zeromerma_api.modules.transfers.domain.exceptions import (
    TransferAlreadyReceivedError,
    TransferValidationError,
)
from zeromerma_api.modules.transfers.infrastructure.models import (
    TransferTransitResolution,
    TransferTransitResolutionLine,
)


def _lines(session: Session, shipment: OperationDocument) -> list[OperationDocumentLine]:
    return list(
        session.scalars(
            select(OperationDocumentLine)
            .where(OperationDocumentLine.operation_document_id == shipment.id)
            .order_by(OperationDocumentLine.line_number)
        )
    )


def _destination(session: Session, shipment: OperationDocument) -> UUID:
    if (
        shipment.destination_branch_id is None
        or shipment.destination_branch_id == shipment.source_branch_id
    ):
        raise TransferValidationError("Origin and destination branches must differ.")
    for branch_id in (shipment.source_branch_id, shipment.destination_branch_id):
        branch = session.get(Branch, branch_id)
        if branch is None or not branch.is_active:
            raise TransferValidationError("Transfer branches must be active.")
    return shipment.destination_branch_id


def _record(
    session: Session,
    shipment: OperationDocument,
    user: AuthenticatedUser,
    action: str,
    request_id: str | None,
    **metadata: object,
) -> None:
    payload = {
        "transfer_id": str(shipment.id),
        "document_type": shipment.document_type,
        "origin_branch_id": str(shipment.source_branch_id),
        "destination_branch_id": str(shipment.destination_branch_id),
        "status": shipment.status,
        **metadata,
        **command_trace(session),
    }
    AuditRecorder().record(
        session,
        actor_id=user.id,
        action=f"transfer.{action}",
        resource_type="operation_document",
        resource_id=str(shipment.id),
        branch_id=shipment.source_branch_id,
        request_id=request_id,
        metadata=payload,
    )
    OutboxWriter().append(
        session,
        aggregate_type="transfer",
        aggregate_id=str(shipment.id),
        event_name=f"transfer.{action}.v1",
        payload=payload,
        headers={"request_id": request_id, **command_trace(session)},
    )


def _move(
    balances: LockedInventoryBalances,
    *,
    branch: UUID,
    line: OperationDocumentLine,
    location: str,
    quantity: Decimal,
    movement_type: str,
    document_type: str,
    document_id: UUID,
    source_line_id: UUID,
    actor: UUID,
    reason: str,
    leg: str,
    unit_cost: Decimal | None = None,
    total_cost: Decimal | None = None,
    cost_evidence_reference: str | None = None,
    lot_allocations: Sequence[InventoryLotQuantity] | None = None,
) -> InventoryMovement:
    try:
        return balances.apply_delta(
            InventoryBalanceKey(branch, line.product_id, location),
            delta=quantity,
            movement_type=movement_type,
            unit_of_measure=line.unit_of_measure_code,
            source_document_type=document_type,
            source_document_id=document_id,
            source_line_id=source_line_id,
            causal_effect_code=f"{source_line_id}:{leg}",
            source_quantity=abs(quantity),
            source_uom=line.unit_of_measure_code,
            conversion_factor=Decimal(1),
            operator_user_id=actor,
            reason=reason,
            notes=line.notes,
            unit_cost=unit_cost,
            total_cost=total_cost,
            cost_evidence_reference=cost_evidence_reference,
            lot_allocations=lot_allocations,
        )
    except InventoryValidationError as error:
        raise TransferValidationError(str(error)) from error


@inventory_calculation
def _transit_cost(
    session: Session,
    shipment: OperationDocument,
    line: OperationDocumentLine,
    quantity: Decimal,
    pending: Decimal,
) -> tuple[Decimal | None, Decimal | None, str | None]:
    original = session.scalar(
        select(InventoryMovement).where(
            InventoryMovement.source_document_id == shipment.id,
            InventoryMovement.source_line_id == line.id,
            InventoryMovement.causal_effect_code == f"{line.id}:dispatch_transit",
            InventoryMovement.branch_id == shipment.destination_branch_id,
            InventoryMovement.location_code == "IN_TRANSIT",
            InventoryMovement.direction == "IN",
        )
    )
    if (
        original is None
        or original.quantity != line.quantity
        or original.unit_of_measure != normalize_uom(line.unit_of_measure_code)
    ):
        raise TransferValidationError(
            "The shipment has no canonical physical dispatch evidence; reconcile it before receipt."
        )
    if original.total_cost is None:
        return None, None, None
    evidence = f"transfer-dispatch:{original.id}"
    consumed = session.scalar(
        select(func.coalesce(func.sum(InventoryMovement.total_cost), 0)).where(
            InventoryMovement.cost_evidence_reference == evidence,
            InventoryMovement.location_code == "IN_TRANSIT",
            InventoryMovement.direction == "OUT",
        )
    ) or Decimal(0)
    total = (
        original.total_cost - consumed
        if quantity == pending
        else (original.total_cost * quantity / original.quantity).quantize(COST_QUANTUM)
    )
    return (total / quantity).quantize(COST_QUANTUM), total, evidence


def dispatch(
    session: Session,
    *,
    shipment: OperationDocument,
    user: AuthenticatedUser,
    notes: str | None,
    request_id: str | None,
) -> TransferCommandResultView:
    """The only physical dispatch implementation, called by both surfaces."""
    if shipment.status != "DRAFT":
        raise TransferValidationError("Only draft transfers can be dispatched.")
    destination = _destination(session, shipment)
    lines = _lines(session, shipment)
    if not lines:
        raise TransferValidationError("Transfer must contain at least one line.")
    balances = lock_inventory_balances(
        session,
        (
            key
            for line in lines
            for key in (
                InventoryBalanceKey(shipment.source_branch_id, line.product_id, "BACKROOM"),
                InventoryBalanceKey(destination, line.product_id, "IN_TRANSIT"),
            )
        ),
    )
    for line in lines:
        outgoing: InventoryMovement | None = None
        for branch, location, quantity, leg in (
            (shipment.source_branch_id, "BACKROOM", -line.quantity, "dispatch_source"),
            (destination, "IN_TRANSIT", line.quantity, "dispatch_transit"),
        ):
            movement = _move(
                balances,
                branch=branch,
                line=line,
                location=location,
                quantity=quantity,
                movement_type="TRANSFER_DISPATCH",
                document_type="BRANCH_TRANSFER_SHIPMENT",
                document_id=shipment.id,
                source_line_id=line.id,
                actor=user.id,
                reason="Transfer dispatch",
                leg=leg,
                lot_allocations=(
                    [
                        InventoryLotQuantity(item.lot_id, item.quantity)
                        for item in outgoing.lot_allocations
                    ]
                    if outgoing is not None
                    else None
                ),
                unit_cost=outgoing.unit_cost if outgoing is not None else None,
                total_cost=outgoing.total_cost if outgoing is not None else None,
                cost_evidence_reference=(
                    f"movement:{outgoing.id}"
                    if outgoing is not None and outgoing.total_cost is not None
                    else None
                ),
            )
            if outgoing is None:
                outgoing = movement
    shipment.status = "IN_TRANSIT"
    shipment.destination_bucket_code = "IN_TRANSIT"
    shipment.committed_at_utc = datetime.now(UTC)
    if notes is not None:
        shipment.notes = notes
    _record(session, shipment, user, "dispatched", request_id, line_count=len(lines))
    return command_snapshot(session, shipment)


def _finish_status(session: Session, shipment: OperationDocument) -> None:
    session.flush()
    items = progress(session, shipment.id)
    if any(line.pending_quantity > 0 for line in items):
        status = "IN_TRANSIT"
    elif all(line.returned_quantity == line.sent_quantity for line in items):
        status = "CANCELLED"
    elif any(line.returned_quantity > 0 or line.waste_quantity > 0 for line in items):
        status = "RECEIVED_WITH_VARIANCE"
    else:
        status = "RECEIVED"
    # A partial receipt at destination does not mutate the origin's shipment.
    # Even assigning its existing status marks it dirty for branch authorization.
    if shipment.status != status:
        shipment.status = status


def receive(
    session: Session,
    *,
    transfer_id: UUID,
    user: AuthenticatedUser,
    lines: Sequence[AdminTransferReceiptLineInput | TransferReceiptLineRequest],
    notes: str | None,
    request_id: str | None,
) -> TransferCommandResultView:
    shipment = lock_shipment(session, transfer_id)
    if shipment.status != "IN_TRANSIT":
        raise TransferAlreadyReceivedError("Transfer shipment is no longer pending receipt.")
    destination = _destination(session, shipment)
    owner = execution(session)
    if owner is None or owner.record is None:
        raise IdempotencyBoundaryError("A transfer command requires its reservation.")
    if owner.record.context_data.get("surface") == "POS" and owner.record.branch_id != destination:
        raise TransferValidationError("Transfer shipment is not destined to the current branch.")
    shipment_lines = {line.id: line for line in _lines(session, shipment)}
    pending = {
        line.shipment_line_id: line.pending_quantity for line in progress(session, shipment.id)
    }
    if not {line.shipment_line_id for line in lines}.issubset(shipment_lines):
        raise TransferValidationError(
            "Transfer receipt lines must match the pending shipment lines exactly."
        )
    if not any(line.received_quantity > 0 for line in lines):
        raise TransferValidationError("Receipt must include a positive quantity.")
    for line in lines:
        remaining = pending[line.shipment_line_id]
        if remaining <= 0 or line.received_quantity > remaining:
            raise TransferValidationError("Received quantity cannot exceed pending quantity.")
        if isinstance(line, TransferReceiptLineRequest) and line.expected_quantity != remaining:
            raise TransferValidationError(
                "Transfer receipt expected quantities must match the pending shipment."
            )
        if line.received_quantity != remaining and not (line.variance_reason or "").strip():
            raise TransferValidationError(
                "Variance reason is required when the received quantity differs from the shipment."
            )
    balances = lock_inventory_balances(
        session,
        (
            InventoryBalanceKey(
                destination, shipment_lines[line.shipment_line_id].product_id, location
            )
            for line in lines
            if line.received_quantity > 0
            for location in ("IN_TRANSIT", "BACKROOM")
        ),
    )
    receipt = OperationDocument(
        document_type="BRANCH_TRANSFER_RECEIPT",
        status="RECEIVED",
        source_branch_id=shipment.source_branch_id,
        destination_branch_id=destination,
        source_bucket_code="IN_TRANSIT",
        destination_bucket_code="BACKROOM",
        workstation_id=owner.record.workstation_id,
        created_by_user_id=user.id,
        reference_document_id=shipment.id,
        notes=notes,
        committed_at_utc=datetime.now(UTC),
    )
    session.add(receipt)
    session.flush()
    for line in lines:
        original = shipment_lines[line.shipment_line_id]
        detail = OperationDocumentLine(
            operation_document_id=receipt.id,
            line_number=original.line_number,
            product_id=original.product_id,
            product_code_snapshot=original.product_code_snapshot,
            product_name_snapshot=original.product_name_snapshot,
            product_class_id=original.product_class_id,
            product_class_code_snapshot=original.product_class_code_snapshot,
            product_class_name_snapshot=original.product_class_name_snapshot,
            quantity=original.quantity,
            expected_quantity=pending[original.id],
            received_quantity=line.received_quantity,
            unit_of_measure_code=original.unit_of_measure_code,
            variance_reason=line.variance_reason,
            notes=line.notes,
        )
        session.add(detail)
        session.flush()
        if line.received_quantity != pending[original.id]:
            receipt.status = "RECEIVED_WITH_VARIANCE"
        if line.received_quantity == 0:
            continue
        unit_cost, total_cost, evidence = _transit_cost(
            session, shipment, original, line.received_quantity, pending[original.id]
        )
        selected_lots = _transit_lots(
            session, shipment.id, original.id, line.received_quantity, line.lot_allocations
        )
        for location, quantity, leg in (
            ("IN_TRANSIT", -line.received_quantity, "receipt_transit"),
            ("BACKROOM", line.received_quantity, "receipt_destination"),
        ):
            _move(
                balances,
                branch=destination,
                line=original,
                location=location,
                quantity=quantity,
                movement_type="TRANSFER_RECEIPT",
                document_type="BRANCH_TRANSFER_RECEIPT",
                document_id=receipt.id,
                source_line_id=detail.id,
                actor=user.id,
                reason=line.variance_reason or "Transfer receipt",
                leg=leg,
                unit_cost=unit_cost,
                total_cost=total_cost,
                cost_evidence_reference=evidence,
                lot_allocations=selected_lots,
            )
    _finish_status(session, shipment)
    _record(
        session,
        shipment,
        user,
        "received",
        request_id,
        receipt_id=str(receipt.id),
        line_count=len(lines),
    )
    return command_snapshot(session, shipment, receipt_id=receipt.id)


def resolve(
    session: Session,
    *,
    transfer_id: UUID,
    user: AuthenticatedUser,
    command: AdminTransferResolveRequest,
    request_id: str | None,
) -> TransferCommandResultView:
    shipment = lock_shipment(session, transfer_id)
    if shipment.status != "IN_TRANSIT":
        raise TransferValidationError("Only outstanding transit stock can be resolved.")
    destination = _destination(session, shipment)
    owner = execution(session)
    if owner is None or owner.record is None:
        raise IdempotencyBoundaryError("A transfer command requires its reservation.")
    returning = command.kind == "RETURN_TO_ORIGIN"
    branch = shipment.source_branch_id if returning else destination
    if owner.record.context_data.get("surface") == "POS" and owner.record.branch_id != branch:
        raise TransferValidationError("The resolution must be confirmed at its physical branch.")
    shipment_lines = {line.id: line for line in _lines(session, shipment)}
    pending = {
        line.shipment_line_id: line.pending_quantity for line in progress(session, shipment.id)
    }
    if not {line.shipment_line_id for line in command.lines}.issubset(shipment_lines):
        raise TransferValidationError("Resolution lines must belong to this shipment.")
    for line in command.lines:
        if line.quantity > pending[line.shipment_line_id]:
            raise TransferValidationError("Resolved quantity cannot exceed pending quantity.")
    location = command.destination_location if returning else "WASTE"
    balances = lock_inventory_balances(
        session,
        (
            key
            for line in command.lines
            for key in (
                InventoryBalanceKey(
                    destination, shipment_lines[line.shipment_line_id].product_id, "IN_TRANSIT"
                ),
                InventoryBalanceKey(
                    branch, shipment_lines[line.shipment_line_id].product_id, location
                ),
            )
        ),
    )
    resolution = TransferTransitResolution(
        shipment_id=shipment.id,
        branch_id=branch,
        origin_branch_id=shipment.source_branch_id,
        destination_branch_id=destination,
        idempotency_record_id=owner.record.id,
        kind=command.kind,
        destination_location=location,
        reason=command.reason,
        actor_id=user.id,
        workstation_id=owner.record.workstation_id,
        cash_session_id=owner.record.cash_session_id,
        occurred_at=datetime.now(UTC),
    )
    session.add(resolution)
    session.flush()
    for line in command.lines:
        original = shipment_lines[line.shipment_line_id]
        unit_cost, total_cost, evidence = _transit_cost(
            session, shipment, original, line.quantity, pending[original.id]
        )
        detail = TransferTransitResolutionLine(
            resolution_id=resolution.id,
            shipment_line_id=original.id,
            product_id=original.product_id,
            quantity=line.quantity,
            unit_of_measure=original.unit_of_measure_code,
        )
        session.add(detail)
        session.flush()
        selected_lots = _transit_lots(
            session, shipment.id, original.id, line.quantity, line.lot_allocations
        )
        for target_branch, target_location, quantity, leg in (
            (destination, "IN_TRANSIT", -line.quantity, "resolution_transit"),
            (branch, location, line.quantity, "resolution_destination"),
        ):
            _move(
                balances,
                branch=target_branch,
                line=original,
                location=target_location,
                quantity=quantity,
                movement_type=(
                    "TRANSFER_DISPOSITION"
                    if location == "QUARANTINE"
                    else "TRANSFER_RETURN"
                    if returning
                    else "WASTE_RECORD"
                ),
                document_type="TRANSFER_RESOLUTION",
                document_id=resolution.id,
                source_line_id=detail.id,
                actor=user.id,
                reason=command.reason,
                leg=leg,
                unit_cost=unit_cost,
                total_cost=total_cost,
                cost_evidence_reference=evidence,
                lot_allocations=selected_lots,
            )
    _finish_status(session, shipment)
    _record(
        session,
        shipment,
        user,
        "resolved",
        request_id,
        resolution_id=str(resolution.id),
        kind=command.kind,
        destination_location=location,
        reason=command.reason,
        lines=[
            {"shipment_line_id": str(line.shipment_line_id), "quantity": str(line.quantity)}
            for line in command.lines
        ],
    )
    return command_snapshot(session, shipment, resolution_id=resolution.id)


def _transit_lots(
    session: Session,
    shipment_id: UUID,
    line_id: UUID,
    quantity: Decimal,
    requested: list[TransferLotAllocationRequest] | None,
) -> list[InventoryLotQuantity] | None:
    remaining = {
        item.lot_id: item.pending_quantity
        for item in shipment_lot_progress(session, shipment_id).get(line_id, [])
        if item.pending_quantity > 0
    }
    if not remaining:
        shipment_line = session.get(OperationDocumentLine, line_id)
        product = session.get(Product, shipment_line.product_id) if shipment_line else None
        if requested or (product is not None and product.lot_tracking_enabled):
            raise TransferValidationError("The shipment has no remaining evidence for these lots.")
        return None
    if requested is None:
        if len(remaining) == 1:
            lot_id = next(iter(remaining))
            selected = [InventoryLotQuantity(lot_id, quantity)]
        elif quantity == sum(remaining.values(), Decimal(0)):
            selected = [
                InventoryLotQuantity(lot_id, amount) for lot_id, amount in remaining.items()
            ]
        else:
            raise TransferValidationError(
                "Select the actual arriving lots for this partial quantity."
            )
    else:
        selected = [InventoryLotQuantity(item.lot_id, item.quantity) for item in requested]
    if (
        len({item.lot_id for item in selected}) != len(selected)
        or sum((item.quantity for item in selected), Decimal(0)) != quantity
    ):
        raise TransferValidationError("Transfer lot quantities must equal the physical quantity.")
    if any(item.quantity > remaining.get(item.lot_id, Decimal(0)) for item in selected):
        raise TransferValidationError(
            "The selected lot exceeds this shipment's remaining quantity."
        )
    return selected
