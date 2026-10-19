"""Explicit planning policy, quotations and immutable commercial commitment evidence."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta
from decimal import ROUND_UP, Decimal
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from zeromerma_api.modules.audit.application.service import AuditRecorder
from zeromerma_api.modules.branches.infrastructure.models import Branch
from zeromerma_api.modules.orders.application.schemas import (
    OrderQuoteLineView,
    OrderQuoteRequest,
    OrderQuoteView,
)
from zeromerma_api.modules.orders.domain.exceptions import OrderStateConflictError
from zeromerma_api.modules.orders.infrastructure.models import (
    CustomerOrder,
    CustomerOrderItem,
    OrderCommitmentPolicy,
    OrderProductionCommitment,
    OrderRevision,
)
from zeromerma_api.modules.outbox.application.service import OutboxWriter


def current_order_time(session: Session) -> datetime:
    """Use the database wall clock after locks; transaction-start time can be stale."""
    now = session.scalar(select(func.clock_timestamp()))
    assert isinstance(now, datetime) and now.tzinfo is not None
    return now.astimezone(UTC)


def quote_order(session: Session, *, branch_id: UUID, request: OrderQuoteRequest) -> OrderQuoteView:
    from zeromerma_api.modules.orders.application.services import (
        _prepare_order_items,
        _resolve_order_currency,
    )

    # Policy configuration locks the same branch row exclusively. Hold a shared lock
    # until this quotation/confirmation transaction ends.
    branch = session.scalar(select(Branch).where(Branch.id == branch_id).with_for_update(read=True))
    assert branch is not None
    policy = session.scalar(
        select(OrderCommitmentPolicy)
        .where(OrderCommitmentPolicy.branch_id == branch_id)
        .order_by(OrderCommitmentPolicy.version.desc())
        .limit(1)
    )
    if policy is None:
        raise OrderStateConflictError("ORDER_POLICY_REQUIRED: Configura la política de pedidos.")
    requested = request.requested_for_at.astimezone(UTC)
    cutoff = requested - timedelta(minutes=policy.lead_time_minutes)
    if cutoff <= current_order_time(session):
        raise OrderStateConflictError(
            "ORDER_COMMITMENT_IN_PAST: La fecha no permite confirmar antes del compromiso."
        )
    items = _prepare_order_items(session, request.items)
    total = sum((item.line_total_amount for item in items), Decimal("0.00"))
    if total <= 0:
        raise OrderStateConflictError("El pedido debe tener un importe positivo.")
    quote = OrderQuoteView(
        quote_fingerprint="",
        policy_id=policy.id,
        policy_version=policy.version,
        lead_time_minutes=policy.lead_time_minutes,
        branch_id=branch_id,
        branch_timezone=branch.timezone,
        requested_for_at=requested,
        production_commit_at=cutoff,
        currency_code=_resolve_order_currency(items),
        total_amount=total,
        minimum_advance_amount=(total / 2).quantize(Decimal("0.01"), rounding=ROUND_UP),
        items=[
            OrderQuoteLineView(
                product_id=item.product_id,
                quantity=item.quantity,
                unit_price=item.unit_price,
                line_total_amount=item.line_total_amount,
            )
            for item in items
        ],
    )
    canonical = json.dumps(quote.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
    return quote.model_copy(
        update={"quote_fingerprint": hashlib.sha256(canonical.encode()).hexdigest()}
    )


def validate_quote(quote: OrderQuoteView, fingerprint: str) -> None:
    if quote.quote_fingerprint != fingerprint:
        raise OrderStateConflictError(
            "ORDER_QUOTE_CHANGED: El precio o la política cambió. Revisa otra cotización."
        )


def save_revision(
    session: Session, *, order: CustomerOrder, quote: OrderQuoteView, actor_id: UUID, reason: str
) -> None:
    now = current_order_time(session)
    if quote.production_commit_at <= now:
        raise OrderStateConflictError("ORDER_COMMITMENT_IN_PAST: Vuelve a cotizar el pedido.")
    order.version += 1
    order.production_commit_at = quote.production_commit_at
    order.production_committed_at = None
    session.flush()
    items = session.scalars(
        select(CustomerOrderItem)
        .where(CustomerOrderItem.customer_order_id == order.id)
        .order_by(CustomerOrderItem.line_number)
    ).all()
    local_cutoff = quote.production_commit_at.astimezone(ZoneInfo(quote.branch_timezone))
    offset = local_cutoff.utcoffset()
    assert offset is not None
    snapshot = {
        **quote.model_dump(mode="json"),
        "minimum_advance_percent": "50",
        "customer_cancel_before_commitment": "FULL_REFUND",
        "customer_cancel_after_commitment": "NO_REFUND",
        "merchant_cancel": "FULL_REFUND",
        "calculation_version": "elapsed_minutes_v1",
        "cutoff_local": local_cutoff.isoformat(),
        "timezone_offset_seconds": int(offset.total_seconds()),
        "reason": reason,
        "customer_name": order.customer_name,
        "customer_phone": order.customer_phone,
        "notes": order.notes,
        "item_snapshots": [
            {
                "id": str(item.id),
                "product_id": str(item.product_id),
                "product_code": item.product_code_snapshot,
                "product_name": item.product_name_snapshot,
                "quantity": str(item.quantity),
                "unit_price": str(item.unit_price),
                "line_total_amount": str(item.line_total_amount),
            }
            for item in items
        ],
    }
    session.add(
        OrderRevision(
            branch_id=order.branch_id,
            order_id=order.id,
            version=order.version,
            policy_id=quote.policy_id,
            quote_fingerprint=quote.quote_fingerprint,
            snapshot=snapshot,
            confirmed_at=now,
            confirmed_by_user_id=actor_id,
        )
    )
    session.flush()


def materialize_commitment(
    session: Session,
    *,
    order: CustomerOrder,
    actor_id: UUID,
    request_id: str | None,
    decision_at: datetime | None = None,
) -> bool:
    if order.production_commit_at is None or order.version < 1:
        raise OrderStateConflictError(
            "ORDER_POLICY_EVIDENCE_REQUIRED: El pedido carece de política histórica verificable."
        )
    if order.production_committed_at is not None:
        return True
    now = decision_at if decision_at is not None else current_order_time(session)
    if now < order.production_commit_at:
        return False
    revision = session.scalar(
        select(OrderRevision).where(
            OrderRevision.order_id == order.id, OrderRevision.version == order.version
        )
    )
    if revision is None:
        raise OrderStateConflictError(
            "ORDER_POLICY_EVIDENCE_REQUIRED: Falta la versión del pedido."
        )
    milestone = OrderProductionCommitment(
        branch_id=order.branch_id,
        order_id=order.id,
        revision_id=revision.id,
        effective_at=order.production_commit_at,
        recorded_at=now,
        actor_id=actor_id,
    )
    session.add(milestone)
    order.production_committed_at = order.production_commit_at
    session.flush()
    payload = {
        "order_id": str(order.id),
        "branch_id": str(order.branch_id),
        "version": order.version,
        "revision_id": str(revision.id),
        "commitment_id": str(milestone.id),
        "effective_at": order.production_commit_at.isoformat(),
        "recorded_at": now.isoformat(),
        "policy_id": str(revision.policy_id),
        "policy_version": revision.snapshot["policy_version"],
        "causal_effect_code": "PRODUCTION_COMMITTED",
    }
    AuditRecorder().record(
        session,
        actor_id=actor_id,
        action="order.production_committed",
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
        event_name="order.production_committed.v1",
        payload=payload,
        headers={"request_id": request_id},
    )
    return True
