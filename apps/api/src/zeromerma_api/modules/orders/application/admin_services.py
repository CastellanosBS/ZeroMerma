from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import UTC, datetime, time
from decimal import Decimal

from sqlalchemy import String, and_, case, cast, func, or_, select
from sqlalchemy.engine import RowMapping
from sqlalchemy.orm import Session
from sqlalchemy.sql.elements import ColumnElement
from sqlalchemy.sql.selectable import Subquery

from zeromerma_api.modules.audit.application.service import AuditRecorder
from zeromerma_api.modules.branches.infrastructure.models import Branch, Workstation
from zeromerma_api.modules.identity.infrastructure.models import User
from zeromerma_api.modules.orders.application.admin_schemas import (
    AdminOrderAvailableActionsView,
    AdminOrderCustomerView,
    AdminOrderDetailView,
    AdminOrderFilterOptionsView,
    AdminOrderFilterOptionView,
    AdminOrderLineView,
    AdminOrderListItemView,
    AdminOrderMetricsView,
    AdminOrderOverviewView,
    AdminOrderPaymentView,
    AdminOrdersBackendContractView,
    AdminOrdersListResponse,
    AdminOrderTimelineEventView,
)
from zeromerma_api.modules.orders.application.services import (
    ORDER_STATUS_SEQUENCE,
    ZERO_MONEY,
    _build_order_folio,
    _get_cancellation_refund_amount,
    _quantize_money,
    _quantize_quantity,
)
from zeromerma_api.modules.orders.domain.constants import (
    ORDER_PAYMENT_TYPE_ADVANCE,
    ORDER_PAYMENT_TYPE_REFUND,
    ORDER_PAYMENT_TYPE_SETTLEMENT,
    ORDER_STATUS_CANCELED,
    ORDER_STATUS_DELIVERED,
    ORDER_STATUS_PENDING,
    ORDER_STATUS_READY,
    OUTBOX_EVENT_ORDER_CANCELED_V1,
    OUTBOX_EVENT_ORDER_DELIVERED_V1,
    OUTBOX_EVENT_ORDER_READY_V1,
    VALID_ORDER_STATUSES,
)
from zeromerma_api.modules.orders.domain.exceptions import (
    OrderNotFoundError,
    OrderStateConflictError,
    OrderValidationError,
)
from zeromerma_api.modules.orders.infrastructure.models import (
    CustomerOrder,
    CustomerOrderItem,
    CustomerOrderPayment,
)
from zeromerma_api.modules.outbox.application.service import OutboxWriter

PAYMENT_STATE_NO_DEPOSIT = "NO_DEPOSIT"
PAYMENT_STATE_PARTIAL_DEPOSIT = "PARTIAL_DEPOSIT"
PAYMENT_STATE_PAID = "PAID"
PAYMENT_STATE_BALANCE_PENDING = "BALANCE_PENDING"
PAYMENT_STATE_CANCELED = "CANCELED"

VALID_PAYMENT_STATES = {
    PAYMENT_STATE_NO_DEPOSIT,
    PAYMENT_STATE_PARTIAL_DEPOSIT,
    PAYMENT_STATE_PAID,
    PAYMENT_STATE_BALANCE_PENDING,
    PAYMENT_STATE_CANCELED,
}


class AdminOrdersService:
    def __init__(
        self,
        audit_recorder: AuditRecorder | None = None,
        outbox_writer: OutboxWriter | None = None,
    ) -> None:
        self._audit_recorder = audit_recorder or AuditRecorder()
        self._outbox_writer = outbox_writer or OutboxWriter()

    def list_orders(
        self,
        session: Session,
        *,
        branch_id: uuid.UUID | None,
        cashier_id: uuid.UUID | None,
        date_from: datetime | None,
        date_to: datetime | None,
        page: int,
        page_size: int,
        payment_state: str | None,
        search: str | None,
        status_filter: str | None,
        workstation_id: uuid.UUID | None,
    ) -> AdminOrdersListResponse:
        normalized_page = max(page, 1)
        normalized_page_size = min(max(page_size, 1), 100)
        conditions = _build_order_conditions(
            branch_id=branch_id,
            cashier_id=cashier_id,
            date_from=date_from,
            date_to=date_to,
            payment_state=payment_state,
            search=search,
            status_filter=status_filter,
            workstation_id=workstation_id,
        )
        item_stats = _order_item_stats_subquery()
        base_statement = (
            select(
                CustomerOrder.id,
                CustomerOrder.status,
                CustomerOrder.customer_name,
                CustomerOrder.customer_phone,
                CustomerOrder.requested_for_at,
                CustomerOrder.total_amount,
                CustomerOrder.advance_amount,
                CustomerOrder.remaining_balance_amount,
                CustomerOrder.currency_code,
                CustomerOrder.created_at_utc,
                CustomerOrder.updated_at_utc,
                Branch.id.label("branch_id"),
                Branch.name.label("branch_name"),
                Workstation.id.label("workstation_id"),
                Workstation.name.label("workstation_name"),
                Workstation.code.label("workstation_code"),
                User.id.label("created_by_user_id"),
                User.full_name.label("created_by_user_full_name"),
                func.coalesce(item_stats.c.line_count, 0).label("line_count"),
                func.coalesce(item_stats.c.total_units, Decimal("0.000")).label("total_units"),
            )
            .select_from(CustomerOrder)
            .join(Branch, Branch.id == CustomerOrder.branch_id)
            .join(Workstation, Workstation.id == CustomerOrder.workstation_id_created)
            .join(User, User.id == CustomerOrder.created_by_user_id)
            .outerjoin(item_stats, item_stats.c.customer_order_id == CustomerOrder.id)
            .where(*conditions)
        )
        total = int(
            session.execute(
                select(func.count()).select_from(base_statement.order_by(None).subquery())
            ).scalar_one()
        )
        records = session.execute(
            base_statement.order_by(
                CustomerOrder.requested_for_at.asc().nulls_last(),
                CustomerOrder.updated_at_utc.desc(),
            )
            .offset((normalized_page - 1) * normalized_page_size)
            .limit(normalized_page_size)
        ).mappings()
        metrics = self._build_metrics(session, conditions)
        now = datetime.now(tz=UTC)

        return AdminOrdersListResponse(
            backend_contract=_backend_contract(),
            filter_options=_build_filter_options(session),
            is_backend_connected=True,
            items=[_map_order_list_item(record, effective_at=now) for record in records],
            metrics=metrics,
            page=normalized_page,
            page_size=normalized_page_size,
            total=total,
        )

    def get_order_detail(self, session: Session, *, order_id: uuid.UUID) -> AdminOrderDetailView:
        order = _get_order(session, order_id=order_id)
        return _build_order_detail(session, order)

    def mark_ready(
        self,
        session: Session,
        *,
        actor_id: uuid.UUID,
        order_id: uuid.UUID,
        request_id: str | None,
    ) -> AdminOrderDetailView:
        order = _get_order(session, order_id=order_id)
        if order.status != ORDER_STATUS_PENDING:
            raise OrderStateConflictError(
                "Solo los pedidos pendientes se pueden marcar como listos para entrega."
            )
        now = datetime.now(tz=UTC)
        order.status = ORDER_STATUS_READY
        order.updated_at_utc = now
        resolved_request_id = request_id or str(uuid.uuid4())
        session.flush()

        self._audit_recorder.record(
            session,
            actor_id=actor_id,
            action="order.ready",
            resource_type="customer_order",
            resource_id=str(order.id),
            branch_id=order.branch_id,
            request_id=resolved_request_id,
            metadata={
                "folio": _build_order_folio(order.id),
                "source": "backoffice",
                "status": ORDER_STATUS_READY,
            },
        )
        self._outbox_writer.append(
            session,
            aggregate_type="customer_order",
            aggregate_id=str(order.id),
            event_name=OUTBOX_EVENT_ORDER_READY_V1,
            payload={
                "order_id": str(order.id),
                "folio": _build_order_folio(order.id),
                "source": "backoffice",
                "status": ORDER_STATUS_READY,
                "branch_id": str(order.branch_id),
                "marked_ready_by_user_id": str(actor_id),
                "marked_ready_at_utc": now.isoformat(),
            },
            headers={"request_id": resolved_request_id},
        )
        session.commit()
        return _build_order_detail(session, order)

    def deliver_order(
        self,
        session: Session,
        *,
        actor_id: uuid.UUID,
        order_id: uuid.UUID,
        request_id: str | None,
    ) -> AdminOrderDetailView:
        order = _get_order(session, order_id=order_id)
        if order.status != ORDER_STATUS_READY:
            raise OrderStateConflictError(
                "Solo los pedidos listos para entrega se pueden entregar."
            )
        if _quantize_money(order.remaining_balance_amount) > ZERO_MONEY:
            raise OrderStateConflictError(
                "Este pedido tiene saldo pendiente. Cobra el saldo desde una caja abierta "
                "antes de entregarlo."
            )
        now = datetime.now(tz=UTC)
        order.status = ORDER_STATUS_DELIVERED
        order.delivered_at = now
        order.delivered_by_user_id = actor_id
        order.updated_at_utc = now
        resolved_request_id = request_id or str(uuid.uuid4())
        session.flush()

        self._audit_recorder.record(
            session,
            actor_id=actor_id,
            action="order.delivered",
            resource_type="customer_order",
            resource_id=str(order.id),
            branch_id=order.branch_id,
            request_id=resolved_request_id,
            metadata={
                "folio": _build_order_folio(order.id),
                "source": "backoffice",
                "status": ORDER_STATUS_DELIVERED,
                "settlement_amount": "0.00",
            },
        )
        self._outbox_writer.append(
            session,
            aggregate_type="customer_order",
            aggregate_id=str(order.id),
            event_name=OUTBOX_EVENT_ORDER_DELIVERED_V1,
            payload={
                "order_id": str(order.id),
                "folio": _build_order_folio(order.id),
                "source": "backoffice",
                "status": ORDER_STATUS_DELIVERED,
                "branch_id": str(order.branch_id),
                "delivered_by_user_id": str(actor_id),
                "settlement_amount": "0.00",
                "delivered_at_utc": now.isoformat(),
            },
            headers={"request_id": resolved_request_id},
        )
        session.commit()
        return _build_order_detail(session, order)

    def cancel_order(
        self,
        session: Session,
        *,
        actor_id: uuid.UUID,
        order_id: uuid.UUID,
        request_id: str | None,
    ) -> AdminOrderDetailView:
        order = _get_order(session, order_id=order_id)
        if order.status == ORDER_STATUS_DELIVERED:
            raise OrderStateConflictError("No se puede cancelar un pedido que ya fue entregado.")
        if order.status == ORDER_STATUS_CANCELED:
            raise OrderStateConflictError("Este pedido ya fue cancelado.")
        now = datetime.now(tz=UTC)
        refund_amount = _get_cancellation_refund_amount(order, effective_at=now)
        if refund_amount > ZERO_MONEY:
            raise OrderStateConflictError(
                "La cancelacion requiere reembolso de anticipo. "
                "Procesa el reembolso desde una caja abierta."
            )
        order.status = ORDER_STATUS_CANCELED
        order.remaining_balance_amount = ZERO_MONEY
        order.canceled_at = now
        order.canceled_by_user_id = actor_id
        order.cancellation_reason = "Cancelado desde Backoffice."
        order.updated_at_utc = now
        resolved_request_id = request_id or str(uuid.uuid4())
        session.flush()

        self._audit_recorder.record(
            session,
            actor_id=actor_id,
            action="order.canceled",
            resource_type="customer_order",
            resource_id=str(order.id),
            branch_id=order.branch_id,
            request_id=resolved_request_id,
            metadata={
                "folio": _build_order_folio(order.id),
                "source": "backoffice",
                "status": ORDER_STATUS_CANCELED,
                "cancellation_refund_eligible": False,
                "cancellation_refund_amount": "0.00",
            },
        )
        self._outbox_writer.append(
            session,
            aggregate_type="customer_order",
            aggregate_id=str(order.id),
            event_name=OUTBOX_EVENT_ORDER_CANCELED_V1,
            payload={
                "order_id": str(order.id),
                "folio": _build_order_folio(order.id),
                "source": "backoffice",
                "status": ORDER_STATUS_CANCELED,
                "branch_id": str(order.branch_id),
                "canceled_by_user_id": str(actor_id),
                "cancellation_refund_eligible": False,
                "cancellation_refund_amount": "0.00",
                "refund_payments": [],
                "canceled_at_utc": now.isoformat(),
            },
            headers={"request_id": resolved_request_id},
        )
        session.commit()
        return _build_order_detail(session, order)

    def _build_metrics(
        self,
        session: Session,
        conditions: list[ColumnElement[bool]],
    ) -> AdminOrderMetricsView:
        now = datetime.now(tz=UTC)
        today_start = datetime.combine(now.date(), time.min, tzinfo=UTC)
        today_end = datetime.combine(now.date(), time.max, tzinfo=UTC)
        record = (
            session.execute(
                select(
                    func.count(
                        case(
                            (
                                CustomerOrder.status.in_(
                                    [ORDER_STATUS_PENDING, ORDER_STATUS_READY]
                                ),
                                1,
                            )
                        )
                    ).label("active_orders"),
                    func.count(case((CustomerOrder.status == ORDER_STATUS_READY, 1))).label(
                        "ready_orders"
                    ),
                    func.count(
                        case(
                            (
                                and_(
                                    CustomerOrder.requested_for_at >= today_start,
                                    CustomerOrder.requested_for_at <= today_end,
                                ),
                                1,
                            )
                        )
                    ).label("due_today"),
                    func.coalesce(func.sum(CustomerOrder.advance_amount), ZERO_MONEY).label(
                        "deposits_received_amount"
                    ),
                    func.coalesce(
                        func.sum(
                            case(
                                (
                                    CustomerOrder.status.in_(
                                        [ORDER_STATUS_PENDING, ORDER_STATUS_READY]
                                    ),
                                    CustomerOrder.remaining_balance_amount,
                                ),
                                else_=ZERO_MONEY,
                            )
                        ),
                        ZERO_MONEY,
                    ).label("outstanding_balance_amount"),
                    func.count(case((CustomerOrder.status == ORDER_STATUS_CANCELED, 1))).label(
                        "canceled_orders"
                    ),
                ).where(*conditions)
            )
            .mappings()
            .one()
        )
        return AdminOrderMetricsView(
            active_orders=int(record["active_orders"] or 0),
            ready_orders=int(record["ready_orders"] or 0),
            due_today=int(record["due_today"] or 0),
            deposits_received_amount=_quantize_money(record["deposits_received_amount"]),
            outstanding_balance_amount=_quantize_money(record["outstanding_balance_amount"]),
            canceled_orders=int(record["canceled_orders"] or 0),
        )


def _backend_contract() -> AdminOrdersBackendContractView:
    return AdminOrdersBackendContractView(
        list_endpoint="GET /v1/admin/orders",
        detail_endpoint="GET /v1/admin/orders/{order_id}",
        mark_ready_endpoint="POST /v1/admin/orders/{order_id}/mark-ready",
        deliver_endpoint="POST /v1/admin/orders/{order_id}/deliver",
        cancel_endpoint="POST /v1/admin/orders/{order_id}/cancel",
        create_endpoint=None,
        financial_capture_endpoint=None,
    )


def _order_item_stats_subquery() -> Subquery:
    return (
        select(
            CustomerOrderItem.customer_order_id.label("customer_order_id"),
            func.count(CustomerOrderItem.id).label("line_count"),
            func.coalesce(func.sum(CustomerOrderItem.quantity), Decimal("0.000")).label(
                "total_units"
            ),
        )
        .group_by(CustomerOrderItem.customer_order_id)
        .subquery()
    )


def _build_order_conditions(
    *,
    branch_id: uuid.UUID | None,
    cashier_id: uuid.UUID | None,
    date_from: datetime | None,
    date_to: datetime | None,
    payment_state: str | None,
    search: str | None,
    status_filter: str | None,
    workstation_id: uuid.UUID | None,
) -> list[ColumnElement[bool]]:
    conditions: list[ColumnElement[bool]] = []
    if branch_id is not None:
        conditions.append(CustomerOrder.branch_id == branch_id)
    if cashier_id is not None:
        conditions.append(CustomerOrder.created_by_user_id == cashier_id)
    if workstation_id is not None:
        conditions.append(CustomerOrder.workstation_id_created == workstation_id)
    if date_from is not None:
        conditions.append(CustomerOrder.requested_for_at >= date_from)
    if date_to is not None:
        conditions.append(CustomerOrder.requested_for_at <= date_to)
    normalized_status = _normalize_status_filter(status_filter)
    if normalized_status is not None:
        conditions.append(CustomerOrder.status == normalized_status)
    normalized_payment_state = _normalize_payment_state(payment_state)
    if normalized_payment_state is not None:
        conditions.append(_payment_state_condition(normalized_payment_state))
    normalized_search = _normalize_search(search)
    if normalized_search is not None:
        order_id_prefix = normalized_search.removeprefix("ped-")
        conditions.append(
            or_(
                func.lower(cast(CustomerOrder.id, String)).like(f"{order_id_prefix}%"),
                func.lower(cast(CustomerOrder.id, String)).contains(normalized_search),
                func.lower(CustomerOrder.customer_name).contains(normalized_search),
                func.lower(CustomerOrder.customer_phone).contains(normalized_search),
            )
        )
    return conditions


def _payment_state_condition(payment_state: str) -> ColumnElement[bool]:
    if payment_state == PAYMENT_STATE_NO_DEPOSIT:
        return and_(
            CustomerOrder.status != ORDER_STATUS_CANCELED,
            CustomerOrder.advance_amount == ZERO_MONEY,
            CustomerOrder.remaining_balance_amount > ZERO_MONEY,
        )
    if payment_state == PAYMENT_STATE_PARTIAL_DEPOSIT:
        return and_(
            CustomerOrder.status != ORDER_STATUS_CANCELED,
            CustomerOrder.advance_amount > ZERO_MONEY,
            CustomerOrder.remaining_balance_amount > ZERO_MONEY,
        )
    if payment_state == PAYMENT_STATE_PAID:
        return and_(
            CustomerOrder.status != ORDER_STATUS_CANCELED,
            CustomerOrder.remaining_balance_amount == ZERO_MONEY,
        )
    if payment_state == PAYMENT_STATE_BALANCE_PENDING:
        return and_(
            CustomerOrder.status.in_([ORDER_STATUS_PENDING, ORDER_STATUS_READY]),
            CustomerOrder.remaining_balance_amount > ZERO_MONEY,
        )
    return CustomerOrder.status == ORDER_STATUS_CANCELED


def _build_filter_options(session: Session) -> AdminOrderFilterOptionsView:
    branches = session.execute(
        select(Branch.id, Branch.name).order_by(Branch.name.asc())
    ).mappings()
    workstations = session.execute(
        select(Workstation.id, Workstation.name, Workstation.code).order_by(Workstation.name.asc())
    ).mappings()
    cashiers = session.execute(
        select(User.id, User.full_name)
        .join(CustomerOrder, CustomerOrder.created_by_user_id == User.id)
        .group_by(User.id, User.full_name)
        .order_by(User.full_name.asc())
    ).mappings()
    return AdminOrderFilterOptionsView(
        branches=[
            AdminOrderFilterOptionView(id=str(record["id"]), label=record["name"])
            for record in branches
        ],
        cashiers=[
            AdminOrderFilterOptionView(id=str(record["id"]), label=record["full_name"])
            for record in cashiers
        ],
        payment_states=[
            AdminOrderFilterOptionView(id=PAYMENT_STATE_NO_DEPOSIT, label="Sin anticipo"),
            AdminOrderFilterOptionView(id=PAYMENT_STATE_PARTIAL_DEPOSIT, label="Anticipo parcial"),
            AdminOrderFilterOptionView(id=PAYMENT_STATE_PAID, label="Pagado"),
            AdminOrderFilterOptionView(id=PAYMENT_STATE_BALANCE_PENDING, label="Con saldo"),
            AdminOrderFilterOptionView(id=PAYMENT_STATE_CANCELED, label="Cancelado"),
        ],
        statuses=[
            AdminOrderFilterOptionView(id=status, label=_status_label(status))
            for status in ORDER_STATUS_SEQUENCE
        ],
        workstations=[
            AdminOrderFilterOptionView(
                id=str(record["id"]), label=f"{record['name']} ({record['code']})"
            )
            for record in workstations
        ],
    )


def _map_order_list_item(
    record: RowMapping,
    *,
    effective_at: datetime,
) -> AdminOrderListItemView:
    refund_amount = _get_record_cancellation_refund_amount(record, effective_at=effective_at)
    status = str(record["status"])
    payment_state = _derive_payment_state(
        status=status,
        advance_amount=Decimal(record["advance_amount"]),
        remaining_balance_amount=Decimal(record["remaining_balance_amount"]),
    )
    return AdminOrderListItemView(
        id=record["id"],
        folio=_build_order_folio(record["id"]),
        customer_name=str(record["customer_name"]),
        customer_phone=record["customer_phone"],
        requested_for_at=record["requested_for_at"],
        status=status,
        payment_state=payment_state,
        total_amount=_quantize_money(record["total_amount"]),
        advance_amount=_quantize_money(record["advance_amount"]),
        remaining_balance_amount=_quantize_money(record["remaining_balance_amount"]),
        currency_code=str(record["currency_code"]),
        branch_id=record["branch_id"],
        branch_name=str(record["branch_name"]),
        workstation_id=record["workstation_id"],
        workstation_name=str(record["workstation_name"]),
        workstation_code=str(record["workstation_code"]),
        created_by_user_id=record["created_by_user_id"],
        created_by_user_full_name=str(record["created_by_user_full_name"]),
        line_count=int(record["line_count"]),
        total_units=_quantize_quantity(record["total_units"]),
        cancellation_refund_eligible=(
            status in {ORDER_STATUS_PENDING, ORDER_STATUS_READY} and refund_amount > ZERO_MONEY
        ),
        cancellation_refund_amount=refund_amount,
        warning_state=_derive_warning_state(status=status, payment_state=payment_state),
        created_at_utc=record["created_at_utc"],
        updated_at_utc=record["updated_at_utc"],
    )


def _get_record_cancellation_refund_amount(
    record: RowMapping,
    *,
    effective_at: datetime,
) -> Decimal:
    pseudo_order = CustomerOrder(
        id=record["id"],
        branch_id=record["branch_id"],
        workstation_id_created=record["workstation_id"],
        created_by_user_id=record["created_by_user_id"],
        active_cash_session_id=uuid.uuid4(),
        status=str(record["status"]),
        customer_name=str(record["customer_name"]),
        customer_phone=record["customer_phone"],
        requested_for_at=record["requested_for_at"],
        notes=None,
        currency_code=str(record["currency_code"]),
        subtotal_amount=record["total_amount"],
        total_amount=record["total_amount"],
        advance_amount=record["advance_amount"],
        remaining_balance_amount=record["remaining_balance_amount"],
        created_at_utc=record["created_at_utc"],
        updated_at_utc=record["updated_at_utc"],
    )
    return _get_cancellation_refund_amount(pseudo_order, effective_at=effective_at)


def _build_order_detail(session: Session, order: CustomerOrder) -> AdminOrderDetailView:
    branch = session.get(Branch, order.branch_id)
    workstation = session.get(Workstation, order.workstation_id_created)
    created_by = session.get(User, order.created_by_user_id)
    delivered_by = (
        session.get(User, order.delivered_by_user_id) if order.delivered_by_user_id else None
    )
    canceled_by = (
        session.get(User, order.canceled_by_user_id) if order.canceled_by_user_id else None
    )
    if branch is None or workstation is None or created_by is None:
        raise OrderStateConflictError("No fue posible reconstruir el pedido.")
    lines = session.execute(
        select(CustomerOrderItem)
        .where(CustomerOrderItem.customer_order_id == order.id)
        .order_by(CustomerOrderItem.line_number.asc())
    ).scalars()
    payment_records = (
        session.execute(
            select(CustomerOrderPayment, User.full_name)
            .join(User, User.id == CustomerOrderPayment.recorded_by_user_id)
            .where(CustomerOrderPayment.customer_order_id == order.id)
            .order_by(CustomerOrderPayment.sequence.asc())
        )
        .tuples()
        .all()
    )
    now = datetime.now(tz=UTC)
    refund_amount = _get_cancellation_refund_amount(order, effective_at=now)
    payment_state = _derive_payment_state(
        status=order.status,
        advance_amount=_quantize_money(order.advance_amount),
        remaining_balance_amount=_quantize_money(order.remaining_balance_amount),
    )
    return AdminOrderDetailView(
        available_actions=_build_available_actions(order, refund_amount=refund_amount),
        backend_contract=_backend_contract(),
        customer=AdminOrderCustomerView(
            name=order.customer_name,
            phone=order.customer_phone,
            notes=order.notes,
        ),
        lines=[
            AdminOrderLineView(
                id=line.id,
                line_number=line.line_number,
                product_id=line.product_id,
                product_code=line.product_code_snapshot,
                product_name=line.product_name_snapshot,
                product_class_id=line.product_class_id,
                product_class_code=line.product_class_code_snapshot,
                product_class_name=line.product_class_name_snapshot,
                quantity=_quantize_quantity(line.quantity),
                unit_price=_quantize_money(line.unit_price),
                line_total_amount=_quantize_money(line.line_total_amount),
            )
            for line in lines
        ],
        operational_context={
            "branch_id": branch.id,
            "branch_name": branch.name,
            "workstation_id": workstation.id,
            "workstation_name": workstation.name,
            "workstation_code": workstation.code,
            "created_by_user_id": created_by.id,
            "created_by_user_full_name": created_by.full_name,
            "delivered_by_user_full_name": delivered_by.full_name if delivered_by else None,
            "canceled_by_user_full_name": canceled_by.full_name if canceled_by else None,
            "active_cash_session_id": order.active_cash_session_id,
        },
        overview=AdminOrderOverviewView(
            id=order.id,
            folio=_build_order_folio(order.id),
            status=order.status,
            payment_state=payment_state,
            customer_name=order.customer_name,
            customer_phone=order.customer_phone,
            requested_for_at=order.requested_for_at,
            branch_id=branch.id,
            branch_name=branch.name,
            total_amount=_quantize_money(order.total_amount),
            advance_amount=_quantize_money(order.advance_amount),
            remaining_balance_amount=_quantize_money(order.remaining_balance_amount),
            currency_code=order.currency_code,
            cancellation_refund_eligible=(
                order.status in {ORDER_STATUS_PENDING, ORDER_STATUS_READY}
                and refund_amount > ZERO_MONEY
            ),
            cancellation_refund_amount=refund_amount,
            created_at_utc=order.created_at_utc,
            updated_at_utc=order.updated_at_utc,
            delivered_at=order.delivered_at,
            canceled_at=order.canceled_at,
            cancellation_reason=order.cancellation_reason,
        ),
        payments=[
            AdminOrderPaymentView(
                id=payment.id,
                sequence=payment.sequence,
                payment_type=payment.payment_type,
                payment_method_code=payment.payment_method_code,
                amount=_quantize_money(payment.amount),
                currency_code=payment.currency_code,
                recorded_at_utc=payment.recorded_at_utc,
                recorded_by_user_id=payment.recorded_by_user_id,
                recorded_by_user_full_name=recorded_by_full_name,
            )
            for payment, recorded_by_full_name in payment_records
        ],
        related_documents=[],
        timeline=_build_timeline(order, payment_records),
    )


def _build_available_actions(
    order: CustomerOrder,
    *,
    refund_amount: Decimal,
) -> AdminOrderAvailableActionsView:
    has_balance_due = _quantize_money(order.remaining_balance_amount) > ZERO_MONEY
    can_deliver_without_payment = order.status == ORDER_STATUS_READY and not has_balance_due
    requires_financial_action = (order.status == ORDER_STATUS_READY and has_balance_due) or (
        order.status in {ORDER_STATUS_PENDING, ORDER_STATUS_READY} and refund_amount > ZERO_MONEY
    )
    financial_note = None
    if order.status == ORDER_STATUS_READY and has_balance_due:
        financial_note = "El saldo pendiente debe cobrarse desde una caja abierta."
    elif refund_amount > ZERO_MONEY:
        financial_note = "El reembolso del anticipo debe procesarse desde una caja abierta."
    return AdminOrderAvailableActionsView(
        can_mark_ready=order.status == ORDER_STATUS_PENDING,
        can_deliver=can_deliver_without_payment,
        can_cancel=(
            order.status in {ORDER_STATUS_PENDING, ORDER_STATUS_READY}
            and refund_amount == ZERO_MONEY
        ),
        can_capture_balance=False,
        can_create_from_backoffice=False,
        requires_settlement_on_delivery=order.status == ORDER_STATUS_READY and has_balance_due,
        requires_cash_session_for_financial_action=requires_financial_action,
        financial_action_note=financial_note,
    )


def _build_timeline(
    order: CustomerOrder,
    payment_records: Sequence[tuple[CustomerOrderPayment, str]],
) -> list[AdminOrderTimelineEventView]:
    events = [
        AdminOrderTimelineEventView(
            key="created",
            label="Pedido creado",
            occurred_at=order.created_at_utc,
            description=_build_order_folio(order.id),
        )
    ]
    for payment, _recorded_by_full_name in payment_records:
        payment_label = {
            ORDER_PAYMENT_TYPE_ADVANCE: "Anticipo registrado",
            ORDER_PAYMENT_TYPE_SETTLEMENT: "Saldo liquidado",
            ORDER_PAYMENT_TYPE_REFUND: "Anticipo reembolsado",
        }.get(payment.payment_type, payment.payment_type)
        events.append(
            AdminOrderTimelineEventView(
                key=f"payment-{payment.sequence}",
                label=payment_label,
                occurred_at=payment.recorded_at_utc,
                description=f"{payment.payment_method_code} {payment.amount}",
            )
        )
    if order.delivered_at is not None:
        events.append(
            AdminOrderTimelineEventView(
                key="delivered",
                label="Pedido entregado",
                occurred_at=order.delivered_at,
            )
        )
    if order.canceled_at is not None:
        events.append(
            AdminOrderTimelineEventView(
                key="canceled",
                label="Pedido cancelado",
                occurred_at=order.canceled_at,
                description=order.cancellation_reason,
            )
        )
    return sorted(events, key=lambda event: event.occurred_at)


def _get_order(session: Session, *, order_id: uuid.UUID) -> CustomerOrder:
    order = session.get(CustomerOrder, order_id)
    if order is None:
        raise OrderNotFoundError("Order was not found.")
    return order


def _normalize_search(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip().casefold()
    return normalized or None


def _normalize_status_filter(value: str | None) -> str | None:
    if value is None or value.strip() == "":
        return None
    normalized = value.strip().upper()
    if normalized not in VALID_ORDER_STATUSES:
        raise OrderValidationError("El estado solicitado no es valido para pedidos.")
    return normalized


def _normalize_payment_state(value: str | None) -> str | None:
    if value is None or value.strip() == "":
        return None
    normalized = value.strip().upper()
    if normalized not in VALID_PAYMENT_STATES:
        raise OrderValidationError("El estado de pago solicitado no es valido para pedidos.")
    return normalized


def _derive_payment_state(
    *,
    status: str,
    advance_amount: Decimal,
    remaining_balance_amount: Decimal,
) -> str:
    if status == ORDER_STATUS_CANCELED:
        return PAYMENT_STATE_CANCELED
    if remaining_balance_amount == ZERO_MONEY:
        return PAYMENT_STATE_PAID
    if advance_amount == ZERO_MONEY:
        return PAYMENT_STATE_NO_DEPOSIT
    if remaining_balance_amount > ZERO_MONEY:
        return PAYMENT_STATE_PARTIAL_DEPOSIT
    return PAYMENT_STATE_BALANCE_PENDING


def _derive_warning_state(*, status: str, payment_state: str) -> str | None:
    if status == ORDER_STATUS_READY and payment_state in {
        PAYMENT_STATE_PARTIAL_DEPOSIT,
        PAYMENT_STATE_NO_DEPOSIT,
        PAYMENT_STATE_BALANCE_PENDING,
    }:
        return "BALANCE_DUE_BEFORE_DELIVERY"
    return None


def _status_label(status: str) -> str:
    return {
        ORDER_STATUS_PENDING: "Pendiente",
        ORDER_STATUS_READY: "Listo",
        ORDER_STATUS_DELIVERED: "Entregado",
        ORDER_STATUS_CANCELED: "Cancelado",
    }.get(status, status)
