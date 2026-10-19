from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from zeromerma_api.modules.inventory.domain.quantities import inventory_calculation
from zeromerma_api.modules.inventory.infrastructure.lot_models import (
    InventoryLot,
    InventoryMovementLotAllocation,
)
from zeromerma_api.modules.inventory.infrastructure.models import InventoryMovement
from zeromerma_api.modules.operations.infrastructure.models import (
    OperationDocument,
    OperationDocumentLine,
)
from zeromerma_api.modules.transfers.application.schemas import (
    TransferLotProgressView,
    TransferLotQuantityView,
)
from zeromerma_api.modules.transfers.infrastructure.models import (
    TransferTransitResolution,
    TransferTransitResolutionLine,
)


@inventory_calculation
def shipment_lot_progress(
    session: Session, shipment_id: UUID
) -> dict[UUID, list[TransferLotProgressView]]:
    """Derive exact outstanding lots from the immutable shipment and subsequent physical effects."""
    by_number = {
        line.line_number: line.id
        for line in session.scalars(
            select(OperationDocumentLine).where(
                OperationDocumentLine.operation_document_id == shipment_id
            )
        )
    }
    receipt_sources = {
        line.id: by_number[line.line_number]
        for line in session.scalars(
            select(OperationDocumentLine)
            .join(
                OperationDocument,
                OperationDocument.id == OperationDocumentLine.operation_document_id,
            )
            .where(
                OperationDocument.reference_document_id == shipment_id,
                OperationDocument.document_type == "BRANCH_TRANSFER_RECEIPT",
            )
        )
    }
    resolutions = {
        line.id: (line.shipment_line_id, resolution.kind)
        for line, resolution in session.execute(
            select(TransferTransitResolutionLine, TransferTransitResolution)
            .join(
                TransferTransitResolution,
                TransferTransitResolution.id == TransferTransitResolutionLine.resolution_id,
            )
            .where(TransferTransitResolution.shipment_id == shipment_id)
        )
    }
    source_ids = [*by_number.values(), *receipt_sources, *resolutions]
    rows = session.execute(
        select(InventoryMovement, InventoryMovementLotAllocation, InventoryLot)
        .join(
            InventoryMovementLotAllocation,
            InventoryMovementLotAllocation.movement_id == InventoryMovement.id,
        )
        .join(InventoryLot, InventoryLot.id == InventoryMovementLotAllocation.lot_id)
        .where(
            InventoryMovement.source_line_id.in_(source_ids),
            InventoryMovement.location_code == "IN_TRANSIT",
        )
        .order_by(InventoryMovement.occurred_at, InventoryMovement.id)
    ).all()
    result: dict[tuple[UUID, UUID], TransferLotProgressView] = {}
    for movement, allocation, lot in rows:
        source_id = movement.source_line_id
        kind = "dispatch"
        if source_id in receipt_sources:
            line_id, kind = receipt_sources[source_id], "receive"
        elif source_id in resolutions:
            line_id, kind = resolutions[source_id]
        elif source_id in by_number.values():
            line_id = source_id
        else:
            continue
        key = (line_id, lot.id)
        item = result.setdefault(
            key,
            TransferLotProgressView(
                lot_id=lot.id,
                lot_code=lot.lot_code,
                expires_at=lot.expires_at,
                sent_quantity=Decimal(0),
                received_quantity=Decimal(0),
                returned_quantity=Decimal(0),
                waste_quantity=Decimal(0),
                pending_quantity=Decimal(0),
            ),
        )
        if kind == "dispatch" and movement.direction == "IN":
            item.sent_quantity += allocation.quantity
            item.pending_quantity += allocation.quantity
        elif movement.direction == "OUT":
            item.pending_quantity -= allocation.quantity
            if kind == "receive":
                item.received_quantity += allocation.quantity
            elif kind == "RETURN_TO_ORIGIN":
                item.returned_quantity += allocation.quantity
            elif kind == "SEND_TO_WASTE":
                item.waste_quantity += allocation.quantity
    grouped: dict[UUID, list[TransferLotProgressView]] = {}
    for (line_id, _), item in result.items():
        grouped.setdefault(line_id, []).append(item)
    return grouped


def resolution_line_lots(session: Session, line_id: UUID) -> list[TransferLotQuantityView]:
    rows = session.execute(
        select(InventoryLot, InventoryMovementLotAllocation.quantity)
        .join(
            InventoryMovementLotAllocation, InventoryMovementLotAllocation.lot_id == InventoryLot.id
        )
        .join(InventoryMovement, InventoryMovement.id == InventoryMovementLotAllocation.movement_id)
        .where(InventoryMovement.source_line_id == line_id, InventoryMovement.direction == "IN")
    )
    return [
        TransferLotQuantityView(
            lot_id=lot.id, lot_code=lot.lot_code, expires_at=lot.expires_at, quantity=quantity
        )
        for lot, quantity in rows
    ]
