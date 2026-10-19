from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from zeromerma_api.modules.idempotency.application.context import execution
from zeromerma_api.modules.idempotency.domain.exceptions import IdempotencyBoundaryError
from zeromerma_api.modules.operations.infrastructure.models import (
    OperationDocument,
    OperationDocumentLine,
)
from zeromerma_api.modules.transfers.application.schemas import (
    TransferCommandLineView,
    TransferCommandResultView,
)
from zeromerma_api.modules.transfers.domain.exceptions import (
    TransferNotFoundError,
    TransferValidationError,
)


def lock_shipment(session: Session, transfer_id: UUID) -> OperationDocument:
    shipment = session.scalar(
        select(OperationDocument)
        .where(
            OperationDocument.id == transfer_id,
            OperationDocument.document_type == "BRANCH_TRANSFER_SHIPMENT",
        )
        .with_for_update(of=OperationDocument, key_share=True)
        .execution_options(populate_existing=True)
    )
    if shipment is None:
        raise TransferNotFoundError("Transfer shipment was not found.")
    owner = execution(session)
    if owner is None or owner.record is None:
        raise IdempotencyBoundaryError("A transfer command requires its reservation.")
    allowed = {
        owner.record.branch_id,
        *(UUID(value) for value in owner.record.context_data.get("related_branch_ids", [])),
    }
    if shipment.source_branch_id not in allowed or shipment.destination_branch_id not in allowed:
        raise TransferValidationError(
            "The transfer branches changed before the command acquired its lock."
        )
    return shipment


def receipts(session: Session, shipment_id: UUID) -> list[OperationDocument]:
    return list(
        session.scalars(
            select(OperationDocument)
            .where(
                OperationDocument.reference_document_id == shipment_id,
                OperationDocument.document_type == "BRANCH_TRANSFER_RECEIPT",
            )
            .order_by(OperationDocument.created_at_utc, OperationDocument.id)
        )
    )


def receipt_lines(session: Session, shipment_id: UUID) -> list[OperationDocumentLine]:
    return list(
        session.scalars(
            select(OperationDocumentLine)
            .join(
                OperationDocument,
                OperationDocument.id == OperationDocumentLine.operation_document_id,
            )
            .where(
                OperationDocument.reference_document_id == shipment_id,
                OperationDocument.document_type == "BRANCH_TRANSFER_RECEIPT",
            )
            .order_by(
                OperationDocument.created_at_utc,
                OperationDocument.id,
                OperationDocumentLine.line_number,
            )
        )
    )


def received_quantities(session: Session, shipment_id: UUID) -> dict[int, Decimal]:
    quantities: dict[int, Decimal] = {}
    for line in receipt_lines(session, shipment_id):
        quantities[line.line_number] = quantities.get(line.line_number, Decimal(0)) + (
            line.received_quantity or Decimal(0)
        )
    return quantities


def progress(session: Session, shipment_id: UUID) -> list[TransferCommandLineView]:
    received = received_quantities(session, shipment_id)
    lines = session.scalars(
        select(OperationDocumentLine)
        .where(OperationDocumentLine.operation_document_id == shipment_id)
        .order_by(OperationDocumentLine.line_number)
    ).all()
    return [
        TransferCommandLineView(
            shipment_line_id=line.id,
            product_id=line.product_id,
            sent_quantity=line.quantity,
            received_quantity=received.get(line.line_number, Decimal(0)),
            pending_quantity=line.quantity - received.get(line.line_number, Decimal(0)),
        )
        for line in lines
    ]


def command_snapshot(
    session: Session, shipment: OperationDocument, *, receipt_id: UUID | None = None
) -> TransferCommandResultView:
    session.flush()
    if shipment.destination_branch_id is None:
        raise TransferValidationError("Destination branch is required.")
    owner = execution(session)
    if owner is None or owner.record is None:
        raise IdempotencyBoundaryError("A transfer command requires its reservation.")
    return TransferCommandResultView(
        id=shipment.id,
        folio=f"ENV-{str(shipment.id).split('-')[0].upper()}",
        status=shipment.status,
        origin_branch_id=shipment.source_branch_id,
        destination_branch_id=shipment.destination_branch_id,
        receipt_id=receipt_id,
        cash_session_id=owner.record.cash_session_id,
        committed_at_utc=shipment.committed_at_utc,
        lines=progress(session, shipment.id),
    )


def command_trace(session: Session) -> dict[str, str]:
    owner = execution(session)
    if owner is None or owner.record is None:
        raise IdempotencyBoundaryError("A transfer command requires its reservation.")
    return {
        "idempotency_key": str(owner.record.idempotency_key),
        "operation_id": str(owner.record.id),
        "operation_code": owner.record.operation_code,
    }
