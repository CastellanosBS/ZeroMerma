"""Additional order collections and versioned amendments under the order lock."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from zeromerma_api.modules.audit.application.service import AuditRecorder
from zeromerma_api.modules.branches.application.access import WorkstationAccessService
from zeromerma_api.modules.identity.application.schemas import AuthenticatedUser
from zeromerma_api.modules.orders.application.commitment import (
    materialize_commitment,
    quote_order,
    save_revision,
    validate_quote,
)
from zeromerma_api.modules.orders.application.financial_services import record_order_payment
from zeromerma_api.modules.orders.application.schemas import (
    AmendCustomerOrderRequest,
    OrderCommandResultView,
    OrderQuoteRequest,
    PayCustomerOrderRequest,
)
from zeromerma_api.modules.orders.application.services import (
    OrderCommandTrace,
    _build_command_result,
    _get_order_for_branch,
    _prepare_order_items,
    _resolve_context_and_open_session,
)
from zeromerma_api.modules.orders.domain.exceptions import (
    OrderStateConflictError,
    OrderValidationError,
)
from zeromerma_api.modules.orders.infrastructure.models import (
    CustomerOrderItem,
    CustomerOrderPayment,
)
from zeromerma_api.modules.outbox.application.service import OutboxWriter


def execute_lifecycle(
    session: Session,
    *,
    current_user: AuthenticatedUser,
    order_id: uuid.UUID,
    command: PayCustomerOrderRequest | AmendCustomerOrderRequest,
    trace: OrderCommandTrace,
    request_id: str | None,
) -> OrderCommandResultView:
    context, cash = _resolve_context_and_open_session(
        session,
        workstation_access=WorkstationAccessService(),
        current_user=current_user,
        workstation_code=command.workstation_code,
        cash_session_id=command.cash_session_id,
    )
    order = _get_order_for_branch(
        session, order_id=order_id, branch_id=context.branch_id, for_update=True
    )
    if order.status not in {"PENDING", "READY"}:
        raise OrderStateConflictError("El pedido ya tiene un estado terminal.")
    committed = materialize_commitment(
        session, order=order, actor_id=current_user.id, request_id=request_id
    )
    payments = (
        command.payments
        if isinstance(command, PayCustomerOrderRequest)
        else command.additional_payments
    )
    additional = sum((payment.amount for payment in payments), Decimal("0.00"))
    if any(payment.payment_method_code not in {"CASH", "CARD"} for payment in payments):
        raise OrderValidationError("Cada pago debe identificar efectivo o tarjeta.")
    if len({payment.payment_method_code for payment in payments}) != len(payments):
        raise OrderValidationError("No repitas el mismo medio de pago.")
    paid = order.advance_amount + additional
    if isinstance(command, AmendCustomerOrderRequest):
        if order.status != "PENDING" or committed:
            raise OrderStateConflictError("ORDER_AMENDMENT_AFTER_PRODUCTION_COMMITMENT")
        if command.expected_version != order.version:
            raise OrderStateConflictError("ORDER_VERSION_CHANGED: Consulta la versión vigente.")
        quote = quote_order(
            session,
            branch_id=order.branch_id,
            request=OrderQuoteRequest(
                workstation_code=command.workstation_code,
                requested_for_at=command.requested_for_at,
                items=command.items,
            ),
        )
        validate_quote(quote, command.quote_fingerprint)
        if quote.currency_code != order.currency_code:
            raise OrderValidationError(
                "La modificación debe conservar la moneda del pedido pagado."
            )
        if paid < quote.minimum_advance_amount or paid > quote.total_amount:
            raise OrderValidationError(
                "El pago acumulado debe cubrir el 50% sin exceder el nuevo total."
            )
        prepared_items = _prepare_order_items(session, command.items)
        for old in session.scalars(
            select(CustomerOrderItem).where(CustomerOrderItem.customer_order_id == order.id)
        ):
            session.delete(old)
        session.flush()
        for sequence, item in enumerate(prepared_items, 1):
            session.add(
                CustomerOrderItem(
                    customer_order_id=order.id,
                    line_number=sequence,
                    product_id=item.product_id,
                    product_code_snapshot=item.product_code,
                    product_name_snapshot=item.product_name,
                    product_class_id=item.product_class_id,
                    product_class_code_snapshot=item.product_class_code,
                    product_class_name_snapshot=item.product_class_name,
                    quantity=item.quantity,
                    unit_price=item.unit_price,
                    line_total_amount=item.line_total_amount,
                )
            )
        order.total_amount = quote.total_amount
        order.subtotal_amount = quote.total_amount
        order.requested_for_at = quote.requested_for_at
        save_revision(
            session, order=order, quote=quote, actor_id=current_user.id, reason=command.reason
        )
        action = "order.amended"
    else:
        if additional <= 0 or paid > order.total_amount:
            raise OrderValidationError(
                "El abono debe ser positivo y no exceder el saldo pendiente."
            )
        action = "order.payment_recorded"
    sequence = int(
        session.scalar(
            select(func.coalesce(func.max(CustomerOrderPayment.sequence), 0)).where(
                CustomerOrderPayment.customer_order_id == order.id
            )
        )
        or 0
    )
    references = []
    for index, payment in enumerate(payments, 1):
        references.append(
            record_order_payment(
                session,
                branch_id=order.branch_id,
                payment=CustomerOrderPayment(
                    id=uuid.uuid4(),
                    customer_order_id=order.id,
                    sequence=sequence + index,
                    payment_type="ADVANCE",
                    payment_method_code=payment.payment_method_code,
                    amount=payment.amount,
                    currency_code=order.currency_code,
                    workstation_id=context.workstation_id,
                    cash_session_id=cash.id,
                    recorded_by_user_id=current_user.id,
                    recorded_at_utc=datetime.now(UTC),
                ),
            )
        )
    order.advance_amount = paid
    order.remaining_balance_amount = order.total_amount - paid
    order.updated_at_utc = datetime.now(UTC)
    payload = {
        **trace.metadata,
        "order_id": str(order.id),
        "branch_id": str(order.branch_id),
        "version": order.version,
        "paid_amount": str(additional),
        "total_amount": str(order.total_amount),
        "remaining_balance_amount": str(order.remaining_balance_amount),
        "financial_records": [reference.trace_fields() for reference in references],
    }
    AuditRecorder().record(
        session,
        actor_id=current_user.id,
        action=action,
        resource_type="customer_order",
        resource_id=str(order.id),
        branch_id=order.branch_id,
        request_id=request_id,
        metadata=payload,
    )
    OutboxWriter().append(
        session,
        aggregate_type="customer_order",
        aggregate_id=str(order.id),
        event_name=f"{action}.v1",
        payload=payload,
        headers={"request_id": request_id, **trace.metadata},
    )
    session.flush()
    return _build_command_result(session, order)
