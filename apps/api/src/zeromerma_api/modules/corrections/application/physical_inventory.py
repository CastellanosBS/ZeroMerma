"""Compensating physical facts for counter transfers and waste corrections."""

from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from zeromerma_api.modules.catalog.infrastructure.models import Product
from zeromerma_api.modules.corrections.domain.exceptions import CorrectionValidationError
from zeromerma_api.modules.corrections.infrastructure.models import (
    CorrectionDocument,
    CorrectionDocumentLine,
)
from zeromerma_api.modules.inventory.application.mutations import (
    InventoryBalanceKey,
    lock_inventory_balances,
)
from zeromerma_api.modules.inventory.domain.quantities import InventoryLotQuantity
from zeromerma_api.modules.inventory.infrastructure.lot_models import (
    InventoryMovementLotAllocation,
)
from zeromerma_api.modules.inventory.infrastructure.models import InventoryMovement
from zeromerma_api.modules.operations.application.physical_inventory import OperationMovementCause
from zeromerma_api.modules.operations.infrastructure.models import OperationDocument


def remaining_movement_lots(
    session: Session, original: InventoryMovement, quantity: Decimal
) -> list[InventoryLotQuantity] | None:
    originals = list(
        session.scalars(
            select(InventoryMovementLotAllocation)
            .where(InventoryMovementLotAllocation.movement_id == original.id)
            .order_by(InventoryMovementLotAllocation.lot_id)
        )
    )
    if not originals:
        return None
    previous = session.execute(
        select(InventoryMovementLotAllocation.lot_id, InventoryMovementLotAllocation.quantity)
        .join(InventoryMovement, InventoryMovement.id == InventoryMovementLotAllocation.movement_id)
        .where(InventoryMovement.reversal_of_movement_id == original.id)
    ).all()
    consumed: dict[UUID, Decimal] = {}
    for lot_id, taken in previous:
        consumed[lot_id] = consumed.get(lot_id, Decimal(0)) + taken
    selected = []
    pending = quantity
    for row in originals:
        take = min(pending, row.quantity - consumed.get(row.lot_id, Decimal(0)))
        if take > 0:
            selected.append(InventoryLotQuantity(row.lot_id, take))
            pending -= take
    if pending:
        raise CorrectionValidationError("The original lot quantity is already compensated.")
    return selected


def apply_correction_inventory(
    session: Session, document: CorrectionDocument, target: OperationDocument
) -> list[UUID]:
    lines = list(
        session.scalars(
            select(CorrectionDocumentLine)
            .where(CorrectionDocumentLine.correction_document_id == document.id)
            .order_by(CorrectionDocumentLine.line_number)
        )
    )
    if len({line.product_id for line in lines}) != len(lines):
        raise CorrectionValidationError("Use one correction line per product.")
    source = target.source_bucket_code
    destination = target.destination_bucket_code
    if source is None or destination is None:
        raise CorrectionValidationError("The original physical locations are missing.")
    balances = lock_inventory_balances(
        session,
        [
            InventoryBalanceKey(document.source_branch_id, line.product_id, location)
            for line in lines
            for location in {source, destination, "QUARANTINE"}
        ],
    )
    ids: list[UUID] = []
    for line in lines:
        product = session.get(Product, line.product_id)
        if product is None or not product.is_inventory_tracked:
            raise CorrectionValidationError("Physical corrections require a tracked product.")
        line.unit_of_measure_code = product.unit_of_measure
        cause: OperationMovementCause = dict(
            movement_type="INVENTORY_COMPENSATION",
            unit_of_measure=product.unit_of_measure,
            source_document_type="CORRECTION_DOCUMENT",
            source_document_id=document.id,
            source_line_id=line.id,
            operator_user_id=document.created_by_user_id,
            reason=document.reason_code,
            notes=line.notes or document.notes,
        )

        def key(location: str, product_id: UUID = line.product_id) -> InventoryBalanceKey:
            return InventoryBalanceKey(document.source_branch_id, product_id, location)

        if line.delta_quantity > 0:
            lots = None
            if product.lot_tracking_enabled:
                original_lots = (
                    session.scalars(
                        select(InventoryMovementLotAllocation.lot_id)
                        .join(
                            InventoryMovement,
                            InventoryMovement.id == InventoryMovementLotAllocation.movement_id,
                        )
                        .where(
                            InventoryMovement.source_document_type == "OPERATION_DOCUMENT",
                            InventoryMovement.source_document_id == target.id,
                            InventoryMovement.source_line_id == line.target_line_id,
                            InventoryMovement.product_id == product.id,
                            InventoryMovement.location_code == source,
                            InventoryMovement.direction == "OUT",
                        )
                        .distinct()
                    ).all()
                    if line.target_line_id
                    else []
                )
                if len(original_lots) != 1:
                    raise CorrectionValidationError(
                        "The additional quantity requires one identified original lot. "
                        "Record a new physical document when the original lot is ambiguous."
                    )
                lots = [InventoryLotQuantity(original_lots[0], line.delta_quantity)]
            if target.document_type == "WASTE_RECORD":
                cause["movement_type"] = "WASTE_RECORD"
            outbound = balances.apply_delta(
                key(source),
                delta=-line.delta_quantity,
                causal_effect_code=f"correction:{line.id}:out",
                lot_allocations=lots,
                **cause,
            )
            inbound = balances.apply_delta(
                key(destination),
                delta=line.delta_quantity,
                causal_effect_code=f"correction:{line.id}:in",
                unit_cost=outbound.unit_cost,
                total_cost=outbound.total_cost,
                cost_evidence_reference=str(outbound.id)
                if outbound.total_cost is not None
                else None,
                lot_allocations=[
                    InventoryLotQuantity(a.lot_id, a.quantity) for a in outbound.lot_allocations
                ]
                or None,
                **cause,
            )
            ids.extend([outbound.id, inbound.id])
            continue
        correction_lines = (
            select(CorrectionDocumentLine.id)
            .join(CorrectionDocument)
            .where(
                CorrectionDocument.target_document_id == target.id,
                CorrectionDocument.id != document.id,
                CorrectionDocumentLine.delta_quantity > 0,
                CorrectionDocumentLine.product_id == line.product_id,
            )
        )
        if line.target_line_id:
            correction_lines = correction_lines.where(
                CorrectionDocumentLine.target_line_id == line.target_line_id
            )
        originals = (
            select(InventoryMovement)
            .where(
                InventoryMovement.branch_id == document.source_branch_id,
                InventoryMovement.product_id == line.product_id,
                InventoryMovement.location_code == destination,
                InventoryMovement.direction == "IN",
                InventoryMovement.reversal_of_movement_id.is_(None),
                or_(
                    (InventoryMovement.source_document_type == "OPERATION_DOCUMENT")
                    & (InventoryMovement.source_document_id == target.id)
                    & (
                        (InventoryMovement.source_line_id == line.target_line_id)
                        if line.target_line_id
                        else True
                    ),
                    (InventoryMovement.source_document_type == "CORRECTION_DOCUMENT")
                    & InventoryMovement.source_line_id.in_(correction_lines),
                ),
            )
            .order_by(InventoryMovement.occurred_at, InventoryMovement.id)
        )
        pending = -line.delta_quantity
        for original in session.scalars(originals):
            already = sum(
                session.scalars(
                    select(InventoryMovement.quantity).where(
                        InventoryMovement.reversal_of_movement_id == original.id
                    )
                ),
                Decimal(0),
            )
            take = min(pending, original.quantity - already)
            if take <= 0:
                continue
            lots = remaining_movement_lots(session, original, take)
            outbound = balances.apply_delta(
                key(destination),
                delta=-take,
                lot_allocations=lots,
                reversal_of_movement_id=original.id,
                causal_effect_code=f"correction:{line.id}:{original.id}:out",
                **cause,
            )
            source_original = None
            if target.document_type == "COUNTER_TRANSFER":
                source_original = session.scalar(
                    select(InventoryMovement).where(
                        InventoryMovement.source_document_type == original.source_document_type,
                        InventoryMovement.source_document_id == original.source_document_id,
                        InventoryMovement.source_line_id == original.source_line_id,
                        InventoryMovement.product_id == line.product_id,
                        InventoryMovement.branch_id == document.source_branch_id,
                        InventoryMovement.location_code == source,
                        InventoryMovement.direction == "OUT",
                        InventoryMovement.reversal_of_movement_id.is_(None),
                    )
                )
                if source_original is None:
                    raise CorrectionValidationError("Original physical evidence is incomplete.")
            inbound = balances.apply_delta(
                key(source if source_original else "QUARANTINE"),
                delta=take,
                lot_allocations=lots,
                reversal_of_movement_id=source_original.id if source_original else None,
                unit_cost=outbound.unit_cost,
                total_cost=outbound.total_cost,
                cost_evidence_reference=str(outbound.id)
                if outbound.total_cost is not None
                else None,
                causal_effect_code=f"correction:{line.id}:{original.id}:in",
                **cause,
            )
            ids.extend([outbound.id, inbound.id])
            pending -= take
            session.flush()
            if not pending:
                break
        if pending:
            raise CorrectionValidationError("The quantity lacks uncompensated physical evidence.")
    return ids
