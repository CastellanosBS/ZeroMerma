"""Read the explicitly configured branch identity for a new operational receipt."""

from uuid import UUID

from sqlalchemy.orm import Session

from zeromerma_api.modules.branches.infrastructure.models import Branch
from zeromerma_api.modules.tickets.application.receipt_schemas import ReceiptSellerView


def snapshot_receipt_seller(session: Session, branch_id: UUID) -> ReceiptSellerView:
    branch = session.get(Branch, branch_id)
    assert branch is not None
    address = ", ".join(
        value.strip()
        for value in (
            branch.address_line,
            branch.city,
            branch.state,
            branch.postal_code,
            branch.country,
        )
        if value and value.strip()
    )
    return ReceiptSellerView(
        commercial_name=branch.receipt_commercial_name,
        business_descriptor=branch.receipt_business_descriptor,
        address=address or None,
    )
