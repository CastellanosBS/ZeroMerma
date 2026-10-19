"""Canonical physical effects shared by POS and administrative operations."""

from __future__ import annotations

from typing import TypedDict
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from zeromerma_api.modules.catalog.infrastructure.models import Product
from zeromerma_api.modules.inventory.application.mutations import (
    InventoryBalanceKey,
    LockedInventoryBalances,
    lock_inventory_balances,
)
from zeromerma_api.modules.inventory.domain.quantities import InventoryLotQuantity
from zeromerma_api.modules.operations.infrastructure.models import (
    OperationDocument,
    OperationDocumentLine,
)


class OperationMovementCause(TypedDict):
    movement_type: str
    unit_of_measure: str
    source_document_type: str
    source_document_id: UUID
    source_line_id: UUID
    operator_user_id: UUID
    reason: str | None
    notes: str | None


def apply_operation_inventory(
    session: Session,
    document: OperationDocument,
    *,
    balances: LockedInventoryBalances | None = None,
    explicit_lots: dict[UUID, list[InventoryLotQuantity]] | None = None,
    line_lots: dict[int, UUID] | None = None,
) -> list[UUID]:
    # Session autoflush is disabled; every pending line must exist before querying effects.
    session.flush()
    lines = session.scalars(
        select(OperationDocumentLine)
        .where(OperationDocumentLine.operation_document_id == document.id)
        .order_by(OperationDocumentLine.line_number)
    ).all()
    products = {
        p.id: p
        for p in session.scalars(
            select(Product).where(Product.id.in_([line.product_id for line in lines]))
        )
    }
    surplus = document.document_type == "CLOSE_COUNTER_ADJUSTMENT"
    if document.document_type not in {
        "COUNTER_TRANSFER",
        "WASTE_RECORD",
        "CLOSE_COUNTER_ADJUSTMENT",
        "CLOSE_WASTE_ADJUSTMENT",
    }:
        raise ValueError("This document has a different physical workflow.")
    source = None if surplus else document.source_bucket_code
    destination = document.destination_bucket_code
    keys = [
        InventoryBalanceKey(document.source_branch_id, line.product_id, location)
        for line in lines
        for location in (source, destination)
        if location
    ]
    balances = balances or lock_inventory_balances(session, keys)
    movement_ids: list[UUID] = []
    for line in lines:
        product = products[line.product_id]
        selected_lots = explicit_lots.get(product.id) if explicit_lots else None
        if line_lots and line.line_number in line_lots:
            selected_lots = [InventoryLotQuantity(line_lots[line.line_number], line.quantity)]
        if (
            document.document_type == "WASTE_RECORD"
            and product.lot_tracking_enabled
            and not selected_lots
        ):
            raise HTTPException(
                409,
                detail={
                    "code": "WASTE_LOT_REQUIRED",
                    "message": "Identify the physical lot being discarded before confirming waste.",
                },
            )
        if not product.is_inventory_tracked:
            raise HTTPException(
                409,
                detail={
                    "code": "INVENTORY_PRODUCT_NOT_TRACKED",
                    "message": "Physical operations require an inventory-tracked product.",
                },
            )
        # These documents capture base units; the snapshot is never a made-up EACH alias.
        line.unit_of_measure_code = product.unit_of_measure
        outbound = None
        common: OperationMovementCause = dict(
            movement_type=document.document_type,
            unit_of_measure=product.unit_of_measure,
            source_document_type="OPERATION_DOCUMENT",
            source_document_id=document.id,
            source_line_id=line.id,
            operator_user_id=document.created_by_user_id,
            reason=document.reason_code or ("PHYSICAL_COUNT_SURPLUS" if surplus else None),
            notes=document.notes,
        )
        if source:
            outbound = balances.apply_delta(
                key=InventoryBalanceKey(document.source_branch_id, line.product_id, source),
                delta=-line.quantity,
                causal_effect_code=f"operation:{line.id}:out",
                lot_allocations=selected_lots,
                **common,
            )
            movement_ids.append(outbound.id)
        if destination:
            inbound = balances.apply_delta(
                key=InventoryBalanceKey(document.source_branch_id, line.product_id, destination),
                delta=line.quantity,
                causal_effect_code=f"operation:{line.id}:in",
                unit_cost=outbound.unit_cost if outbound else None,
                total_cost=outbound.total_cost if outbound else None,
                lot_allocations=[
                    InventoryLotQuantity(row.lot_id, row.quantity)
                    for row in outbound.lot_allocations
                ]
                if outbound
                else selected_lots,
                cost_evidence_reference=str(outbound.id)
                if outbound and outbound.total_cost is not None
                else None,
                **common,
            )
            movement_ids.append(inbound.id)
    return movement_ids
