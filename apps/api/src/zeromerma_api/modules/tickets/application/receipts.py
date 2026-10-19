"""Freeze documents inside the economic transaction; reads never fabricate history."""

import hashlib
import json
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from zeromerma_api.modules.branches.infrastructure.models import Branch
from zeromerma_api.modules.sales.application.schemas import SaleDetailView
from zeromerma_api.modules.tickets.application.receipt_schemas import (
    OperationalReceiptView,
    ReceiptContextView,
    ReceiptLineView,
    ReceiptPaymentView,
)
from zeromerma_api.modules.tickets.domain.exceptions import TicketConflictError
from zeromerma_api.modules.tickets.infrastructure.models import ReceiptSnapshot


def receipt_digest(document: OperationalReceiptView) -> str:
    serialized = json.dumps(document.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode()).hexdigest()


def persist_receipt(session: Session, document: OperationalReceiptView) -> None:
    """Caller owns commit/rollback and has already authorized the document's branch."""
    existing = session.scalar(
        select(ReceiptSnapshot).where(
            ReceiptSnapshot.source_kind == document.source_kind,
            ReceiptSnapshot.source_id == document.source_id,
        )
    )
    digest = receipt_digest(document)
    if existing is not None:
        if existing.document_sha256 != digest:
            raise TicketConflictError("The committed receipt cannot be replaced.")
        return
    session.add(
        ReceiptSnapshot(
            branch_id=document.context.branch_id,
            workstation_id=document.context.workstation_id,
            source_kind=document.source_kind,
            source_id=document.source_id,
            document=document.model_dump(mode="json"),
            document_sha256=digest,
        )
    )
    session.flush()


def read_receipt(
    session: Session, source_kind: str, source_id: UUID
) -> OperationalReceiptView | None:
    row = session.scalar(
        select(ReceiptSnapshot).where(
            ReceiptSnapshot.source_kind == source_kind, ReceiptSnapshot.source_id == source_id
        )
    )
    if row is None:
        return None
    document = OperationalReceiptView.model_validate(row.document)
    if receipt_digest(document) != row.document_sha256:
        raise TicketConflictError("The receipt integrity check failed.")
    return document


def snapshot_sale(session: Session, detail: SaleDetailView) -> None:
    branch = session.get(Branch, detail.branch_id)
    assert branch is not None
    persist_receipt(
        session,
        OperationalReceiptView(
            source_kind="SALE",
            source_id=detail.id,
            folio=f"TCK-{detail.id.hex.upper()}",
            currency_code=detail.currency_code,
            occurred_at=detail.confirmed_at,
            context=ReceiptContextView(
                branch_id=detail.branch_id,
                branch_code=detail.branch_code,
                branch_name=detail.branch_name,
                timezone=branch.timezone,
                workstation_id=detail.workstation_id,
                workstation_code=detail.workstation_code,
                workstation_name=detail.workstation_name,
                actor_id=detail.operator_id,
                actor_name=detail.operator_full_name,
                cash_session_id=detail.cash_session_id,
            ),
            subtotal_amount=detail.subtotal_amount,
            discount_amount=detail.subtotal_amount - detail.total_amount,
            total_amount=detail.total_amount,
            change_amount=detail.change_amount,
            lines=[
                ReceiptLineView(
                    sequence=line.sequence,
                    name=line.catalog_name_snapshot,
                    quantity=line.quantity,
                    unit_price=line.unit_price,
                    total_amount=line.line_total_amount,
                )
                for line in detail.lines
            ],
            payments=[
                ReceiptPaymentView.model_validate(
                    {
                        "method": payment.payment_method_code,
                        "execution_mode": "LOCAL"
                        if payment.payment_method_code == "CASH"
                        else "ACCOUNTING_ONLY",
                        "amount": payment.applied_amount,
                        "tendered_amount": payment.tendered_amount,
                        "change_amount": payment.change_amount,
                    }
                )
                for payment in detail.payments
            ],
        ),
    )
