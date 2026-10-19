from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from zeromerma_api.modules.idempotency.domain.exceptions import IdempotencyBoundaryError
from zeromerma_api.modules.operations.application.schemas import (
    OperationCommitLineResultView,
    OperationCommitResultView,
)
from zeromerma_api.modules.operations.infrastructure.models import (
    OperationDocument,
    OperationDocumentLine,
)


def build_operation_result(
    session: Session,
    document: OperationDocument,
    *,
    cash_session_id: UUID | None,
    inventory_movement_ids: list[UUID] | None = None,
) -> OperationCommitResultView:
    if document.committed_at_utc is None:
        raise IdempotencyBoundaryError(
            "An operation acknowledgement requires a committed document."
        )
    prefixes = {"COUNTER_TRANSFER": "CTR", "WASTE_RECORD": "WST"}
    return OperationCommitResultView(
        id=document.id,
        folio=f"{prefixes[document.document_type]}-{str(document.id).split('-')[0].upper()}",
        document_type=document.document_type,
        status=document.status,
        branch_id=document.source_branch_id,
        workstation_id=document.workstation_id,
        cash_session_id=cash_session_id,
        source_bucket_code=document.source_bucket_code,
        destination_bucket_code=document.destination_bucket_code,
        committed_at_utc=document.committed_at_utc,
        inventory_movement_ids=inventory_movement_ids or [],
        lines=[
            OperationCommitLineResultView(
                id=line.id,
                line_number=line.line_number,
                product_id=line.product_id,
                quantity=line.quantity,
                unit_of_measure_code=line.unit_of_measure_code,
            )
            for line in session.scalars(
                select(OperationDocumentLine)
                .where(OperationDocumentLine.operation_document_id == document.id)
                .order_by(OperationDocumentLine.line_number)
            )
        ],
    )
