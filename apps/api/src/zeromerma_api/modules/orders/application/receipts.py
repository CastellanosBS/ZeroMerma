"""Freeze an operational receipt for each actual order collection."""

from decimal import Decimal
from typing import Literal, cast

from sqlalchemy.orm import Session

from zeromerma_api.modules.branches.infrastructure.models import Branch, Workstation
from zeromerma_api.modules.identity.infrastructure.models import User
from zeromerma_api.modules.orders.infrastructure.models import CustomerOrderPayment
from zeromerma_api.modules.tickets.application.receipt_schemas import (
    OperationalReceiptView,
    ReceiptContextView,
    ReceiptLineView,
    ReceiptPaymentView,
)
from zeromerma_api.modules.tickets.application.receipts import persist_receipt


def persist_order_payment_receipt(session: Session, payment: CustomerOrderPayment) -> None:
    workstation = session.get(Workstation, payment.workstation_id)
    assert workstation is not None
    branch = session.get(Branch, workstation.branch_id)
    actor = session.get(User, payment.recorded_by_user_id)
    assert branch is not None and actor is not None
    order_folio = f"PED-{payment.customer_order_id.hex.upper()}"
    collection_label = "Liquidación" if payment.payment_type == "SETTLEMENT" else "Abono"
    persist_receipt(
        session,
        OperationalReceiptView(
            source_kind="ORDER_PAYMENT",
            source_id=payment.id,
            folio=f"OPR-{payment.id.hex.upper()}",
            currency_code=payment.currency_code,
            occurred_at=payment.recorded_at_utc,
            context=ReceiptContextView(
                branch_id=branch.id,
                branch_code=branch.code,
                branch_name=branch.name,
                timezone=branch.timezone,
                workstation_id=workstation.id,
                workstation_code=workstation.code,
                workstation_name=workstation.name,
                actor_id=actor.id,
                actor_name=actor.full_name,
                cash_session_id=payment.cash_session_id,
            ),
            subtotal_amount=payment.amount,
            discount_amount=Decimal("0.00"),
            total_amount=payment.amount,
            change_amount=Decimal("0.00"),
            related_document_folio=order_folio,
            lines=[
                ReceiptLineView(
                    sequence=1,
                    name=f"{collection_label} a pedido {order_folio}",
                    quantity=Decimal("1"),
                    unit_price=payment.amount,
                    total_amount=payment.amount,
                )
            ],
            payments=[
                ReceiptPaymentView(
                    method=cast(Literal["CASH", "CARD"], payment.payment_method_code),
                    execution_mode="LOCAL"
                    if payment.payment_method_code == "CASH"
                    else "ACCOUNTING_ONLY",
                    amount=payment.amount,
                    tendered_amount=payment.amount,
                    change_amount=Decimal("0.00"),
                )
            ],
        ),
    )
