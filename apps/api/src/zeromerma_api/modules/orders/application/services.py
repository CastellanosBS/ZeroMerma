from __future__ import annotations

import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from decimal import ROUND_HALF_UP, Decimal
from zoneinfo import ZoneInfo

from sqlalchemy import Select, String, cast, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from zeromerma_api.modules.audit.application.service import AuditRecorder
from zeromerma_api.modules.branches.application.access import (
    WorkstationAccessService,
    WorkstationContext,
)
from zeromerma_api.modules.branches.application.schemas import BranchSummary, WorkstationSummary
from zeromerma_api.modules.branches.infrastructure.models import Branch, Workstation
from zeromerma_api.modules.cash.application.services import CashSessionQueryService
from zeromerma_api.modules.cash.domain.constants import CASH_SESSION_STATUS_OPEN
from zeromerma_api.modules.cash.infrastructure.models import CashSession
from zeromerma_api.modules.catalog.domain.exceptions import (
    ProductClassNotFoundError,
    ProductNotFoundError,
)
from zeromerma_api.modules.catalog.infrastructure.models import Product, ProductClass
from zeromerma_api.modules.identity.application.schemas import AuthenticatedUser
from zeromerma_api.modules.identity.infrastructure.models import User
from zeromerma_api.modules.operations.domain.constants import BRANCH_BRAND_MAPPING
from zeromerma_api.modules.orders.application.schemas import (
    CancelCustomerOrderRequest,
    CreateCustomerOrderAdvancePaymentRequest,
    CreateCustomerOrderItemRequest,
    CreateCustomerOrderRequest,
    CustomerOrderDetailResponse,
    CustomerOrderItemView,
    CustomerOrderListItemView,
    CustomerOrderPaymentView,
    DeliverCustomerOrderRequest,
    DeliverCustomerOrderSettlementPaymentRequest,
    OrderActionRequest,
    OrdersBootstrapResponse,
    OrdersCatalogClassView,
    OrdersCatalogProductView,
    OrdersCatalogResponse,
    OrdersClassProductsResponse,
    OrdersListResponse,
    OrderStatusCounterView,
)
from zeromerma_api.modules.orders.domain.constants import (
    ORDER_PAYMENT_METHOD_CARD,
    ORDER_PAYMENT_METHOD_CASH,
    ORDER_PAYMENT_METHOD_MIXED,
    ORDER_PAYMENT_TYPE_ADVANCE,
    ORDER_PAYMENT_TYPE_REFUND,
    ORDER_PAYMENT_TYPE_SETTLEMENT,
    ORDER_STATUS_CANCELED,
    ORDER_STATUS_DELIVERED,
    ORDER_STATUS_PENDING,
    ORDER_STATUS_READY,
    OUTBOX_EVENT_ORDER_CANCELED_V1,
    OUTBOX_EVENT_ORDER_CREATED_V1,
    OUTBOX_EVENT_ORDER_DELIVERED_V1,
    OUTBOX_EVENT_ORDER_READY_V1,
    VALID_ORDER_PAYMENT_METHOD_CODES,
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

MONEY_QUANTIZER = Decimal("0.01")
ZERO_MONEY = Decimal("0.00")
ORDER_STATUS_SEQUENCE = [
    ORDER_STATUS_PENDING,
    ORDER_STATUS_READY,
    ORDER_STATUS_DELIVERED,
    ORDER_STATUS_CANCELED,
]


@dataclass(frozen=True)
class PreparedOrderItem:
    product_id: uuid.UUID
    product_code: str
    product_name: str
    product_class_id: uuid.UUID
    product_class_code: str
    product_class_name: str
    quantity: Decimal
    unit_price: Decimal
    line_total_amount: Decimal
    currency_code: str


@dataclass(frozen=True)
class PreparedOrderAdvancePayment:
    payment_method_code: str
    amount: Decimal


class OrdersQueryService:
    def __init__(
        self,
        workstation_access: WorkstationAccessService | None = None,
        cash_session_query: CashSessionQueryService | None = None,
    ) -> None:
        self._workstation_access = workstation_access or WorkstationAccessService()
        self._cash_session_query = cash_session_query or CashSessionQueryService()

    def get_bootstrap(
        self,
        session: Session,
        *,
        current_user: AuthenticatedUser,
        workstation_code: str,
    ) -> OrdersBootstrapResponse:
        context = self._workstation_access.resolve_context(
            session,
            user_id=current_user.id,
            workstation_code=workstation_code,
        )
        local_timestamp = datetime.now(tz=UTC).astimezone(ZoneInfo(context.branch_timezone))
        current_open_cash_session = self._cash_session_query.get_open_session_for_workstation_code(
            session,
            workstation_code=workstation_code,
        )
        grouped_counts = {
            record["status"]: int(record["count"])
            for record in session.execute(
                select(CustomerOrder.status, func.count(CustomerOrder.id).label("count"))
                .where(CustomerOrder.branch_id == context.branch_id)
                .group_by(CustomerOrder.status)
            ).mappings()
        }

        return OrdersBootstrapResponse(
            user=current_user,
            branch=BranchSummary(
                id=context.branch_id,
                code=context.branch_code,
                name=context.branch_name,
                timezone=context.branch_timezone,
                is_active=context.branch_is_active,
            ),
            workstation=WorkstationSummary(
                id=context.workstation_id,
                code=context.workstation_code,
                name=context.workstation_name,
                is_active=context.workstation_is_active,
            ),
            local_timestamp=local_timestamp,
            current_open_cash_session=current_open_cash_session,
            branch_brand_key=_get_branch_brand_key(context.branch_code),
            status_counters=[
                OrderStatusCounterView(status=status_code, count=grouped_counts.get(status_code, 0))
                for status_code in ORDER_STATUS_SEQUENCE
            ],
            can_create_order=(
                current_open_cash_session is not None
                and current_open_cash_session.user_id == current_user.id
            ),
        )

    def list_orders(
        self,
        session: Session,
        *,
        current_user: AuthenticatedUser,
        workstation_code: str,
        status_filter: str | None,
        query: str | None,
        date_from: date | None,
        date_to: date | None,
    ) -> OrdersListResponse:
        context = self._workstation_access.resolve_context(
            session,
            user_id=current_user.id,
            workstation_code=workstation_code,
        )
        normalized_status = _validate_status_filter(status_filter)
        normalized_query = _normalize_query(query)
        item_stats_subquery = (
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
        statement = (
            select(
                CustomerOrder.id,
                CustomerOrder.status,
                CustomerOrder.customer_name,
                CustomerOrder.customer_phone,
                CustomerOrder.requested_for_at,
                CustomerOrder.created_at_utc,
                CustomerOrder.total_amount,
                CustomerOrder.advance_amount,
                CustomerOrder.remaining_balance_amount,
                CustomerOrder.currency_code,
                func.coalesce(item_stats_subquery.c.line_count, 0).label("line_count"),
                func.coalesce(item_stats_subquery.c.total_units, Decimal("0.000")).label(
                    "total_units"
                ),
            )
            .select_from(CustomerOrder)
            .outerjoin(
                item_stats_subquery, item_stats_subquery.c.customer_order_id == CustomerOrder.id
            )
            .where(CustomerOrder.branch_id == context.branch_id)
            .order_by(CustomerOrder.created_at_utc.desc())
            .limit(60)
        )
        if normalized_status is not None:
            statement = statement.where(CustomerOrder.status == normalized_status)
        statement = _apply_requested_for_date_filters(
            statement,
            branch_timezone=context.branch_timezone,
            date_from=date_from,
            date_to=date_to,
        )
        if normalized_query is not None:
            order_id_prefix = normalized_query.removeprefix("ped-")
            statement = statement.where(
                or_(
                    func.lower(cast(CustomerOrder.id, String)).like(f"{order_id_prefix}%"),
                    func.lower(cast(CustomerOrder.id, String)).contains(normalized_query),
                    func.lower(CustomerOrder.customer_name).contains(normalized_query),
                    func.lower(CustomerOrder.customer_phone).contains(normalized_query),
                )
            )
        records = session.execute(statement).mappings().all()
        return OrdersListResponse(
            workstation_code=workstation_code,
            status=normalized_status,
            query=normalized_query,
            date_from=date_from,
            date_to=date_to,
            orders=[
                CustomerOrderListItemView(
                    id=record["id"],
                    folio=_build_order_folio(record["id"]),
                    status=record["status"],
                    customer_name=record["customer_name"],
                    customer_phone=record["customer_phone"],
                    requested_for_at=record["requested_for_at"],
                    created_at_utc=record["created_at_utc"],
                    line_count=int(record["line_count"]),
                    total_units=record["total_units"],
                    total_amount=record["total_amount"],
                    advance_amount=record["advance_amount"],
                    remaining_balance_amount=record["remaining_balance_amount"],
                    currency_code=record["currency_code"],
                )
                for record in records
            ],
        )

    def get_catalog(
        self,
        session: Session,
        *,
        current_user: AuthenticatedUser,
        workstation_code: str,
        query: str | None,
    ) -> OrdersCatalogResponse:
        self._workstation_access.resolve_context(
            session,
            user_id=current_user.id,
            workstation_code=workstation_code,
        )
        normalized_query = _normalize_query(query)
        product_count_subquery = (
            select(func.count(Product.id))
            .where(
                Product.product_class_id == ProductClass.id,
                Product.is_active.is_(True),
                Product.is_sellable.is_(True),
            )
            .correlate(ProductClass)
            .scalar_subquery()
        )
        statement = (
            select(
                ProductClass.id,
                ProductClass.code,
                ProductClass.name,
                ProductClass.quick_name,
                ProductClass.display_order,
                product_count_subquery.label("product_count"),
            )
            .where(
                ProductClass.is_active.is_(True),
                ProductClass.is_sellable.is_(True),
                product_count_subquery > 0,
            )
            .order_by(ProductClass.display_order.asc(), ProductClass.name.asc())
        )
        if normalized_query is not None:
            pattern = f"%{normalized_query}%"
            matching_products = (
                select(Product.id)
                .where(
                    Product.product_class_id == ProductClass.id,
                    Product.is_active.is_(True),
                    Product.is_sellable.is_(True),
                    or_(
                        Product.code.ilike(pattern),
                        Product.name.ilike(pattern),
                        Product.quick_name.ilike(pattern),
                        Product.search_aliases.ilike(pattern),
                    ),
                )
                .exists()
            )
            statement = statement.where(
                or_(
                    ProductClass.code.ilike(pattern),
                    ProductClass.name.ilike(pattern),
                    ProductClass.quick_name.ilike(pattern),
                    ProductClass.search_aliases.ilike(pattern),
                    matching_products,
                )
            )
        records = session.execute(statement).mappings().all()
        return OrdersCatalogResponse(
            workstation_code=workstation_code,
            query=normalized_query,
            classes=[
                OrdersCatalogClassView(
                    id=record["id"],
                    code=record["code"],
                    name=record["name"],
                    quick_name=record["quick_name"],
                    display_order=record["display_order"],
                    product_count=int(record["product_count"]),
                )
                for record in records
            ],
        )

    def get_class_products(
        self,
        session: Session,
        *,
        current_user: AuthenticatedUser,
        workstation_code: str,
        class_id: uuid.UUID,
        query: str | None,
    ) -> OrdersClassProductsResponse:
        self._workstation_access.resolve_context(
            session,
            user_id=current_user.id,
            workstation_code=workstation_code,
        )
        normalized_query = _normalize_query(query)
        product_class = session.execute(
            select(ProductClass).where(
                ProductClass.id == class_id,
                ProductClass.is_active.is_(True),
                ProductClass.is_sellable.is_(True),
            )
        ).scalar_one_or_none()
        if product_class is None:
            raise ProductClassNotFoundError("Product class was not found.")
        statement = (
            select(
                Product.id,
                Product.code,
                Product.name,
                Product.quick_name,
                Product.display_order,
                Product.unit_price,
                Product.currency_code,
            )
            .where(
                Product.product_class_id == class_id,
                Product.is_active.is_(True),
                Product.is_sellable.is_(True),
            )
            .order_by(Product.display_order.asc(), Product.name.asc())
        )
        if normalized_query is not None:
            pattern = f"%{normalized_query}%"
            statement = statement.where(
                or_(
                    Product.code.ilike(pattern),
                    Product.name.ilike(pattern),
                    Product.quick_name.ilike(pattern),
                    Product.search_aliases.ilike(pattern),
                )
            )
        product_records = session.execute(statement).mappings().all()
        return OrdersClassProductsResponse(
            class_id=product_class.id,
            class_code=product_class.code,
            class_name=product_class.name,
            query=normalized_query,
            products=[
                OrdersCatalogProductView(
                    id=record["id"],
                    code=record["code"],
                    name=record["name"],
                    quick_name=record["quick_name"],
                    display_order=record["display_order"],
                    unit_price=record["unit_price"],
                    currency_code=record["currency_code"],
                )
                for record in product_records
            ],
        )

    def get_order_detail(
        self,
        session: Session,
        *,
        current_user: AuthenticatedUser,
        workstation_code: str,
        order_id: uuid.UUID,
    ) -> CustomerOrderDetailResponse:
        context = self._workstation_access.resolve_context(
            session,
            user_id=current_user.id,
            workstation_code=workstation_code,
        )
        order = _get_order_for_branch(session, order_id=order_id, branch_id=context.branch_id)
        return _build_order_detail(session, order)


class OrdersCommandService:
    def __init__(
        self,
        workstation_access: WorkstationAccessService | None = None,
        cash_session_query: CashSessionQueryService | None = None,
        audit_recorder: AuditRecorder | None = None,
        outbox_writer: OutboxWriter | None = None,
        query_service: OrdersQueryService | None = None,
    ) -> None:
        self._workstation_access = workstation_access or WorkstationAccessService()
        self._cash_session_query = cash_session_query or CashSessionQueryService()
        self._audit_recorder = audit_recorder or AuditRecorder()
        self._outbox_writer = outbox_writer or OutboxWriter()
        self._query_service = query_service or OrdersQueryService(
            workstation_access=self._workstation_access,
            cash_session_query=self._cash_session_query,
        )

    def create_order(
        self,
        session: Session,
        *,
        current_user: AuthenticatedUser,
        command: CreateCustomerOrderRequest,
        request_id: str | None,
    ) -> CustomerOrderDetailResponse:
        context, cash_session = _resolve_context_and_open_session(
            session,
            workstation_access=self._workstation_access,
            current_user=current_user,
            workstation_code=command.workstation_code,
        )
        prepared_items = _prepare_order_items(session, command.items)
        currency_code = _resolve_order_currency(prepared_items)
        subtotal_amount = _quantize_money(
            sum((item.line_total_amount for item in prepared_items), ZERO_MONEY)
        )
        total_amount = subtotal_amount
        advance_amount = _quantize_money(command.advance_amount)
        if advance_amount > total_amount:
            raise OrderValidationError("El anticipo no puede ser mayor al total del pedido.")
        if advance_amount > ZERO_MONEY:
            advance_payment_method_code = _validate_payment_method_code(
                command.advance_payment_method_code
            )
            prepared_advance_payments = _prepare_advance_payments(
                advance_amount=advance_amount,
                advance_payment_method_code=advance_payment_method_code,
                advance_payments=command.advance_payments,
            )
        else:
            if _normalize_optional_string(command.advance_payment_method_code) is not None:
                raise OrderValidationError(
                    "No captures un metodo de anticipo si el pedido no lleva anticipo."
                )
            if command.advance_payments:
                raise OrderValidationError(
                    "No captures pagos de anticipo si el pedido no lleva anticipo."
                )
            advance_payment_method_code = None
            prepared_advance_payments = []
        remaining_balance_amount = _quantize_money(total_amount - advance_amount)
        created_at = datetime.now(tz=UTC)
        resolved_request_id = request_id or str(uuid.uuid4())

        order = CustomerOrder(
            branch_id=context.branch_id,
            workstation_id_created=context.workstation_id,
            created_by_user_id=current_user.id,
            active_cash_session_id=cash_session.id,
            status=ORDER_STATUS_PENDING,
            customer_name=command.customer_name.strip(),
            customer_phone=_normalize_optional_string(command.customer_phone),
            requested_for_at=command.requested_for_at,
            notes=_normalize_optional_string(command.notes),
            currency_code=currency_code,
            subtotal_amount=subtotal_amount,
            total_amount=total_amount,
            advance_amount=advance_amount,
            remaining_balance_amount=remaining_balance_amount,
            created_at_utc=created_at,
            updated_at_utc=created_at,
        )

        try:
            session.add(order)
            session.flush()

            for line_number, item in enumerate(prepared_items, start=1):
                session.add(
                    CustomerOrderItem(
                        customer_order_id=order.id,
                        line_number=line_number,
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

            for sequence, payment in enumerate(prepared_advance_payments, start=1):
                session.add(
                    CustomerOrderPayment(
                        customer_order_id=order.id,
                        sequence=sequence,
                        payment_type=ORDER_PAYMENT_TYPE_ADVANCE,
                        payment_method_code=payment.payment_method_code,
                        amount=payment.amount,
                        currency_code=currency_code,
                        workstation_id=context.workstation_id,
                        cash_session_id=cash_session.id,
                        recorded_by_user_id=current_user.id,
                        recorded_at_utc=created_at,
                    )
                )

            self._audit_recorder.record(
                session,
                actor_id=current_user.id,
                action="order.created",
                resource_type="customer_order",
                resource_id=str(order.id),
                branch_id=context.branch_id,
                request_id=resolved_request_id,
                metadata={
                    "folio": _build_order_folio(order.id),
                    "branch_code": context.branch_code,
                    "workstation_code": context.workstation_code,
                    "cash_session_id": str(cash_session.id),
                    "customer_name": order.customer_name,
                    "line_count": len(prepared_items),
                    "total_amount": str(total_amount),
                    "advance_amount": str(advance_amount),
                    "advance_payment_method_code": advance_payment_method_code,
                    "advance_payment_count": len(prepared_advance_payments),
                    "remaining_balance_amount": str(remaining_balance_amount),
                },
            )
            self._outbox_writer.append(
                session,
                aggregate_type="customer_order",
                aggregate_id=str(order.id),
                event_name=OUTBOX_EVENT_ORDER_CREATED_V1,
                payload={
                    "order_id": str(order.id),
                    "folio": _build_order_folio(order.id),
                    "branch_id": str(context.branch_id),
                    "branch_code": context.branch_code,
                    "workstation_id": str(context.workstation_id),
                    "workstation_code": context.workstation_code,
                    "cash_session_id": str(cash_session.id),
                    "created_by_user_id": str(current_user.id),
                    "created_by_user_email": current_user.email,
                    "status": ORDER_STATUS_PENDING,
                    "customer_name": order.customer_name,
                    "customer_phone": order.customer_phone,
                    "requested_for_at": order.requested_for_at.isoformat()
                    if order.requested_for_at
                    else None,
                    "notes": order.notes,
                    "currency_code": currency_code,
                    "subtotal_amount": str(subtotal_amount),
                    "total_amount": str(total_amount),
                    "advance_amount": str(advance_amount),
                    "remaining_balance_amount": str(remaining_balance_amount),
                    "items": [
                        {
                            "product_id": str(item.product_id),
                            "product_code_snapshot": item.product_code,
                            "product_name_snapshot": item.product_name,
                            "product_class_id": str(item.product_class_id),
                            "product_class_code_snapshot": item.product_class_code,
                            "product_class_name_snapshot": item.product_class_name,
                            "quantity": str(item.quantity),
                            "unit_price": str(item.unit_price),
                            "line_total_amount": str(item.line_total_amount),
                        }
                        for item in prepared_items
                    ],
                    "payments": [
                        {
                            "payment_type": ORDER_PAYMENT_TYPE_ADVANCE,
                            "payment_method_code": payment.payment_method_code,
                            "amount": str(payment.amount),
                        }
                        for payment in prepared_advance_payments
                    ],
                    "created_at_utc": created_at.isoformat(),
                },
                headers={"request_id": resolved_request_id},
            )
            session.commit()
        except IntegrityError as error:
            session.rollback()
            raise OrderStateConflictError(
                "La captura del pedido entro en conflicto con otra solicitud concurrente."
            ) from error

        return self._query_service.get_order_detail(
            session,
            current_user=current_user,
            workstation_code=command.workstation_code,
            order_id=order.id,
        )

    def mark_ready(
        self,
        session: Session,
        *,
        current_user: AuthenticatedUser,
        order_id: uuid.UUID,
        command: OrderActionRequest,
        request_id: str | None,
    ) -> CustomerOrderDetailResponse:
        context, cash_session = _resolve_context_and_open_session(
            session,
            workstation_access=self._workstation_access,
            current_user=current_user,
            workstation_code=command.workstation_code,
        )
        order = _get_order_for_branch(session, order_id=order_id, branch_id=context.branch_id)
        if order.status != ORDER_STATUS_PENDING:
            raise OrderStateConflictError(
                "Solo los pedidos pendientes se pueden marcar como listos para entrega."
            )

        order.status = ORDER_STATUS_READY
        order.updated_at_utc = datetime.now(tz=UTC)
        resolved_request_id = request_id or str(uuid.uuid4())
        session.flush()

        self._audit_recorder.record(
            session,
            actor_id=current_user.id,
            action="order.ready",
            resource_type="customer_order",
            resource_id=str(order.id),
            branch_id=context.branch_id,
            request_id=resolved_request_id,
            metadata={
                "folio": _build_order_folio(order.id),
                "branch_code": context.branch_code,
                "workstation_code": context.workstation_code,
                "cash_session_id": str(cash_session.id),
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
                "status": ORDER_STATUS_READY,
                "branch_id": str(context.branch_id),
                "branch_code": context.branch_code,
                "workstation_id": str(context.workstation_id),
                "workstation_code": context.workstation_code,
                "cash_session_id": str(cash_session.id),
                "marked_ready_by_user_id": str(current_user.id),
                "marked_ready_at_utc": order.updated_at_utc.isoformat(),
            },
            headers={"request_id": resolved_request_id},
        )
        session.commit()

        return self._query_service.get_order_detail(
            session,
            current_user=current_user,
            workstation_code=command.workstation_code,
            order_id=order.id,
        )

    def deliver_order(
        self,
        session: Session,
        *,
        current_user: AuthenticatedUser,
        order_id: uuid.UUID,
        command: DeliverCustomerOrderRequest,
        request_id: str | None,
    ) -> CustomerOrderDetailResponse:
        context, cash_session = _resolve_context_and_open_session(
            session,
            workstation_access=self._workstation_access,
            current_user=current_user,
            workstation_code=command.workstation_code,
        )
        order = _get_order_for_branch(session, order_id=order_id, branch_id=context.branch_id)
        if order.status != ORDER_STATUS_READY:
            raise OrderStateConflictError(
                "Solo los pedidos listos para entrega se pueden entregar."
            )

        remaining_balance_amount = _quantize_money(order.remaining_balance_amount)
        settlement_amount = _quantize_money(command.settlement_amount or ZERO_MONEY)
        settlement_payment_method = _normalize_optional_string(
            command.settlement_payment_method_code
        )
        prepared_settlement_payments: list[PreparedOrderAdvancePayment] = []
        next_sequence = (
            int(
                session.execute(
                    select(func.coalesce(func.max(CustomerOrderPayment.sequence), 0)).where(
                        CustomerOrderPayment.customer_order_id == order.id
                    )
                ).scalar_one()
            )
            + 1
        )

        if remaining_balance_amount > ZERO_MONEY:
            if settlement_amount != remaining_balance_amount:
                raise OrderValidationError(
                    "La liquidacion final debe cubrir exactamente el faltante del pedido."
                )
            settlement_payment_method = _validate_payment_method_code(settlement_payment_method)
            prepared_settlement_payments = _prepare_settlement_payments(
                settlement_amount=settlement_amount,
                settlement_payment_method_code=settlement_payment_method,
                settlement_payments=command.settlement_payments,
            )
            for sequence_offset, payment in enumerate(prepared_settlement_payments):
                session.add(
                    CustomerOrderPayment(
                        customer_order_id=order.id,
                        sequence=next_sequence + sequence_offset,
                        payment_type=ORDER_PAYMENT_TYPE_SETTLEMENT,
                        payment_method_code=payment.payment_method_code,
                        amount=payment.amount,
                        currency_code=order.currency_code,
                        workstation_id=context.workstation_id,
                        cash_session_id=cash_session.id,
                        recorded_by_user_id=current_user.id,
                        recorded_at_utc=datetime.now(tz=UTC),
                    )
                )
        elif (
            settlement_amount > ZERO_MONEY
            or settlement_payment_method is not None
            or command.settlement_payments
        ):
            raise OrderValidationError("Este pedido ya no tiene saldo pendiente por liquidar.")

        delivered_at = datetime.now(tz=UTC)
        order.status = ORDER_STATUS_DELIVERED
        order.remaining_balance_amount = ZERO_MONEY
        order.delivered_at = delivered_at
        order.delivered_by_user_id = current_user.id
        order.updated_at_utc = delivered_at
        resolved_request_id = request_id or str(uuid.uuid4())
        session.flush()

        self._audit_recorder.record(
            session,
            actor_id=current_user.id,
            action="order.delivered",
            resource_type="customer_order",
            resource_id=str(order.id),
            branch_id=context.branch_id,
            request_id=resolved_request_id,
            metadata={
                "folio": _build_order_folio(order.id),
                "branch_code": context.branch_code,
                "workstation_code": context.workstation_code,
                "cash_session_id": str(cash_session.id),
                "status": ORDER_STATUS_DELIVERED,
                "settlement_amount": str(settlement_amount),
                "settlement_payment_method_code": settlement_payment_method,
                "settlement_payment_count": len(prepared_settlement_payments),
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
                "status": ORDER_STATUS_DELIVERED,
                "branch_id": str(context.branch_id),
                "branch_code": context.branch_code,
                "workstation_id": str(context.workstation_id),
                "workstation_code": context.workstation_code,
                "cash_session_id": str(cash_session.id),
                "delivered_by_user_id": str(current_user.id),
                "settlement_amount": str(settlement_amount),
                "settlement_payment_method_code": settlement_payment_method,
                "settlement_payments": [
                    {
                        "payment_method_code": payment.payment_method_code,
                        "amount": str(payment.amount),
                    }
                    for payment in prepared_settlement_payments
                ],
                "delivered_at_utc": delivered_at.isoformat(),
            },
            headers={"request_id": resolved_request_id},
        )
        session.commit()

        return self._query_service.get_order_detail(
            session,
            current_user=current_user,
            workstation_code=command.workstation_code,
            order_id=order.id,
        )

    def cancel_order(
        self,
        session: Session,
        *,
        current_user: AuthenticatedUser,
        order_id: uuid.UUID,
        command: CancelCustomerOrderRequest,
        request_id: str | None,
    ) -> CustomerOrderDetailResponse:
        context, cash_session = _resolve_context_and_open_session(
            session,
            workstation_access=self._workstation_access,
            current_user=current_user,
            workstation_code=command.workstation_code,
        )
        order = _get_order_for_branch(session, order_id=order_id, branch_id=context.branch_id)
        if order.status == ORDER_STATUS_DELIVERED:
            raise OrderStateConflictError("No se puede cancelar un pedido que ya fue entregado.")
        if order.status == ORDER_STATUS_CANCELED:
            raise OrderStateConflictError("Este pedido ya fue cancelado.")
        canceled_at = datetime.now(tz=UTC)
        cancellation_refund_amount = _get_cancellation_refund_amount(
            order,
            effective_at=canceled_at,
        )
        cancellation_refund_eligible = cancellation_refund_amount > ZERO_MONEY
        refund_payments = _prepare_cancellation_refund_payments(
            session,
            order=order,
            refund_amount=cancellation_refund_amount,
        )
        next_sequence = (
            int(
                session.execute(
                    select(func.coalesce(func.max(CustomerOrderPayment.sequence), 0)).where(
                        CustomerOrderPayment.customer_order_id == order.id
                    )
                ).scalar_one()
            )
            + 1
        )
        for sequence_offset, payment in enumerate(refund_payments):
            session.add(
                CustomerOrderPayment(
                    customer_order_id=order.id,
                    sequence=next_sequence + sequence_offset,
                    payment_type=ORDER_PAYMENT_TYPE_REFUND,
                    payment_method_code=payment.payment_method_code,
                    amount=payment.amount,
                    currency_code=order.currency_code,
                    workstation_id=context.workstation_id,
                    cash_session_id=cash_session.id,
                    recorded_by_user_id=current_user.id,
                    recorded_at_utc=canceled_at,
                )
            )

        order.status = ORDER_STATUS_CANCELED
        if cancellation_refund_eligible:
            order.advance_amount = ZERO_MONEY
        order.remaining_balance_amount = ZERO_MONEY
        order.canceled_at = canceled_at
        order.canceled_by_user_id = current_user.id
        order.cancellation_reason = command.cancellation_reason.strip()
        order.updated_at_utc = canceled_at
        resolved_request_id = request_id or str(uuid.uuid4())
        session.flush()

        self._audit_recorder.record(
            session,
            actor_id=current_user.id,
            action="order.canceled",
            resource_type="customer_order",
            resource_id=str(order.id),
            branch_id=context.branch_id,
            request_id=resolved_request_id,
            metadata={
                "folio": _build_order_folio(order.id),
                "branch_code": context.branch_code,
                "workstation_code": context.workstation_code,
                "cash_session_id": str(cash_session.id),
                "status": ORDER_STATUS_CANCELED,
                "cancellation_reason": order.cancellation_reason,
                "cancellation_refund_eligible": cancellation_refund_eligible,
                "cancellation_refund_amount": str(cancellation_refund_amount),
                "refund_payment_count": len(refund_payments),
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
                "status": ORDER_STATUS_CANCELED,
                "branch_id": str(context.branch_id),
                "branch_code": context.branch_code,
                "workstation_id": str(context.workstation_id),
                "workstation_code": context.workstation_code,
                "cash_session_id": str(cash_session.id),
                "canceled_by_user_id": str(current_user.id),
                "cancellation_reason": order.cancellation_reason,
                "cancellation_refund_eligible": cancellation_refund_eligible,
                "cancellation_refund_amount": str(cancellation_refund_amount),
                "refund_payments": [
                    {
                        "payment_method_code": payment.payment_method_code,
                        "amount": str(payment.amount),
                    }
                    for payment in refund_payments
                ],
                "canceled_at_utc": canceled_at.isoformat(),
            },
            headers={"request_id": resolved_request_id},
        )
        session.commit()

        return self._query_service.get_order_detail(
            session,
            current_user=current_user,
            workstation_code=command.workstation_code,
            order_id=order.id,
        )


def _resolve_context_and_open_session(
    session: Session,
    *,
    workstation_access: WorkstationAccessService,
    current_user: AuthenticatedUser,
    workstation_code: str,
) -> tuple[WorkstationContext, CashSession]:
    context = workstation_access.resolve_context(
        session,
        user_id=current_user.id,
        workstation_code=workstation_code,
    )
    cash_session = session.execute(
        select(CashSession).where(
            CashSession.workstation_id == context.workstation_id,
            CashSession.status == CASH_SESSION_STATUS_OPEN,
        )
    ).scalar_one_or_none()
    if cash_session is None:
        raise OrderStateConflictError(
            "Necesitas una caja abierta en esta estacion para operar pedidos."
        )
    if cash_session.user_id != current_user.id:
        raise OrderStateConflictError("La caja abierta en esta estacion pertenece a otro cajero.")
    return context, cash_session


def _prepare_order_items(
    session: Session,
    items: Sequence[CreateCustomerOrderItemRequest],
) -> list[PreparedOrderItem]:
    aggregated_quantities: dict[uuid.UUID, Decimal] = {}
    for item in items:
        quantity = _quantize_quantity(item.quantity)
        aggregated_quantities[item.product_id] = (
            aggregated_quantities.get(item.product_id, Decimal("0.000")) + quantity
        )

    product_records = session.execute(
        select(
            Product.id,
            Product.code,
            Product.name,
            Product.unit_price,
            Product.currency_code,
            ProductClass.id.label("product_class_id"),
            ProductClass.code.label("product_class_code"),
            ProductClass.name.label("product_class_name"),
        )
        .select_from(Product)
        .join(ProductClass, ProductClass.id == Product.product_class_id)
        .where(
            Product.id.in_(tuple(aggregated_quantities.keys())),
            Product.is_active.is_(True),
            Product.is_sellable.is_(True),
            ProductClass.is_active.is_(True),
            ProductClass.is_sellable.is_(True),
        )
    ).mappings()
    products_by_id = {record["id"]: record for record in product_records}

    missing_product_ids = [
        product_id for product_id in aggregated_quantities if product_id not in products_by_id
    ]
    if missing_product_ids:
        missing_product_id = missing_product_ids[0]
        raise ProductNotFoundError(f"Product {missing_product_id} was not found.")

    prepared_items: list[PreparedOrderItem] = []
    for product_id, quantity in aggregated_quantities.items():
        record = products_by_id[product_id]
        unit_price = _quantize_money(record["unit_price"])
        line_total_amount = _quantize_money(unit_price * quantity)
        prepared_items.append(
            PreparedOrderItem(
                product_id=record["id"],
                product_code=record["code"],
                product_name=record["name"],
                product_class_id=record["product_class_id"],
                product_class_code=record["product_class_code"],
                product_class_name=record["product_class_name"],
                quantity=quantity,
                unit_price=unit_price,
                line_total_amount=line_total_amount,
                currency_code=record["currency_code"],
            )
        )

    prepared_items.sort(
        key=lambda item: (item.product_class_name.casefold(), item.product_name.casefold())
    )
    return prepared_items


def _resolve_order_currency(items: Sequence[PreparedOrderItem]) -> str:
    currency_codes = {item.currency_code for item in items}
    if not currency_codes:
        raise OrderValidationError("El pedido debe incluir al menos un producto.")
    if len(currency_codes) != 1:
        raise OrderValidationError("Todos los productos del pedido deben usar la misma moneda.")
    return next(iter(currency_codes))


def _build_order_detail(session: Session, order: CustomerOrder) -> CustomerOrderDetailResponse:
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
        raise OrderStateConflictError("No fue posible reconstruir el detalle del pedido.")

    created_by_summary = _to_user_summary(created_by)
    if created_by_summary is None:
        raise OrderStateConflictError("No fue posible reconstruir el operador del pedido.")

    item_records = session.execute(
        select(CustomerOrderItem)
        .where(CustomerOrderItem.customer_order_id == order.id)
        .order_by(CustomerOrderItem.line_number)
    ).scalars()
    payment_records = session.execute(
        select(CustomerOrderPayment, User.full_name)
        .join(User, User.id == CustomerOrderPayment.recorded_by_user_id)
        .where(CustomerOrderPayment.customer_order_id == order.id)
        .order_by(CustomerOrderPayment.sequence)
    ).all()

    advance_amount = _quantize_money(order.advance_amount)
    remaining_balance_amount = _quantize_money(order.remaining_balance_amount)
    cancellation_refund_amount = _get_cancellation_refund_amount(
        order,
        effective_at=datetime.now(tz=UTC),
    )

    return CustomerOrderDetailResponse(
        id=order.id,
        folio=_build_order_folio(order.id),
        status=order.status,
        branch=BranchSummary(
            id=branch.id,
            code=branch.code,
            name=branch.name,
            timezone=branch.timezone,
            is_active=branch.is_active,
        ),
        workstation_created=WorkstationSummary(
            id=workstation.id,
            code=workstation.code,
            name=workstation.name,
            is_active=workstation.is_active,
        ),
        created_by=created_by_summary,
        delivered_by=_to_user_summary(delivered_by),
        canceled_by=_to_user_summary(canceled_by),
        active_cash_session_id=order.active_cash_session_id,
        customer_name=order.customer_name,
        customer_phone=order.customer_phone,
        requested_for_at=order.requested_for_at,
        notes=order.notes,
        currency_code=order.currency_code,
        subtotal_amount=_quantize_money(order.subtotal_amount),
        total_amount=_quantize_money(order.total_amount),
        advance_amount=advance_amount,
        remaining_balance_amount=remaining_balance_amount,
        delivered_at=order.delivered_at,
        canceled_at=order.canceled_at,
        cancellation_reason=order.cancellation_reason,
        cancellation_refund_eligible=(
            order.status in {ORDER_STATUS_PENDING, ORDER_STATUS_READY}
            and cancellation_refund_amount > ZERO_MONEY
        ),
        cancellation_refund_amount=cancellation_refund_amount,
        created_at_utc=order.created_at_utc,
        updated_at_utc=order.updated_at_utc,
        items=[
            CustomerOrderItemView(
                id=item.id,
                line_number=item.line_number,
                product_id=item.product_id,
                product_code_snapshot=item.product_code_snapshot,
                product_name_snapshot=item.product_name_snapshot,
                product_class_id=item.product_class_id,
                product_class_code_snapshot=item.product_class_code_snapshot,
                product_class_name_snapshot=item.product_class_name_snapshot,
                quantity=_quantize_quantity(item.quantity),
                unit_price=_quantize_money(item.unit_price),
                line_total_amount=_quantize_money(item.line_total_amount),
            )
            for item in item_records
        ],
        payments=[
            CustomerOrderPaymentView(
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
        can_mark_ready=order.status == ORDER_STATUS_PENDING,
        can_deliver=order.status == ORDER_STATUS_READY,
        can_cancel=order.status in {ORDER_STATUS_PENDING, ORDER_STATUS_READY},
        requires_settlement_on_delivery=(
            order.status == ORDER_STATUS_READY and remaining_balance_amount > ZERO_MONEY
        ),
    )


def _get_order_for_branch(
    session: Session,
    *,
    order_id: uuid.UUID,
    branch_id: uuid.UUID,
) -> CustomerOrder:
    order = session.execute(
        select(CustomerOrder).where(
            CustomerOrder.id == order_id,
            CustomerOrder.branch_id == branch_id,
        )
    ).scalar_one_or_none()
    if order is None:
        raise OrderNotFoundError("Order was not found.")
    return order


def _to_user_summary(user: User | None) -> AuthenticatedUser | None:
    if user is None:
        return None
    return AuthenticatedUser(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        is_active=user.is_active,
    )


def _get_branch_brand_key(branch_code: str) -> str:
    return BRANCH_BRAND_MAPPING.get(branch_code, "EL_MEJOR_PAN")


def _build_order_folio(order_id: uuid.UUID) -> str:
    return f"PED-{str(order_id).split('-', maxsplit=1)[0].upper()}"


def _normalize_query(value: str | None) -> str | None:
    normalized = _normalize_optional_string(value)
    return normalized.casefold() if normalized else None


def _validate_status_filter(value: str | None) -> str | None:
    normalized = _normalize_optional_string(value)
    if normalized is None:
        return None
    normalized_status = normalized.upper()
    if normalized_status not in VALID_ORDER_STATUSES:
        raise OrderValidationError("El estado solicitado no es valido para pedidos.")
    return normalized_status


def _apply_requested_for_date_filters(
    statement: Select[tuple[object, ...]],
    *,
    branch_timezone: str,
    date_from: date | None,
    date_to: date | None,
) -> Select[tuple[object, ...]]:
    if date_from is None and date_to is None:
        return statement

    if date_from is not None and date_to is not None and date_from > date_to:
        raise OrderValidationError("La fecha inicial no puede ser mayor que la fecha final.")

    timezone = ZoneInfo(branch_timezone)
    if date_from is not None:
        local_start = datetime.combine(date_from, time.min, tzinfo=timezone)
        statement = statement.where(CustomerOrder.requested_for_at >= local_start.astimezone(UTC))
    if date_to is not None:
        local_end = datetime.combine(date_to + timedelta(days=1), time.min, tzinfo=timezone)
        statement = statement.where(CustomerOrder.requested_for_at < local_end.astimezone(UTC))

    return statement


def _prepare_advance_payments(
    *,
    advance_amount: Decimal,
    advance_payment_method_code: str,
    advance_payments: Sequence[CreateCustomerOrderAdvancePaymentRequest],
) -> list[PreparedOrderAdvancePayment]:
    if advance_payment_method_code != ORDER_PAYMENT_METHOD_MIXED:
        if advance_payments:
            raise OrderValidationError(
                "Solo captura el desglose del anticipo cuando el metodo sea mixto."
            )
        return [
            PreparedOrderAdvancePayment(
                payment_method_code=advance_payment_method_code,
                amount=advance_amount,
            )
        ]

    if len(advance_payments) != 2:
        raise OrderValidationError(
            "El cobro mixto del anticipo requiere efectivo y tarjeta."
        )

    normalized_payments: list[PreparedOrderAdvancePayment] = []
    seen_payment_methods: set[str] = set()
    for payment in advance_payments:
        payment_method_code = _validate_payment_method_code(payment.payment_method_code)
        if payment_method_code == ORDER_PAYMENT_METHOD_MIXED:
            raise OrderValidationError(
                "El cobro mixto del anticipo debe desglosarse en efectivo y tarjeta."
            )
        if payment_method_code in seen_payment_methods:
            raise OrderValidationError(
                "No repitas el mismo metodo dentro del anticipo mixto."
            )
        normalized_payments.append(
            PreparedOrderAdvancePayment(
                payment_method_code=payment_method_code,
                amount=_quantize_money(payment.amount),
            )
        )
        seen_payment_methods.add(payment_method_code)

    if seen_payment_methods != {ORDER_PAYMENT_METHOD_CASH, ORDER_PAYMENT_METHOD_CARD}:
        raise OrderValidationError(
            "El cobro mixto del anticipo requiere efectivo y tarjeta."
        )

    captured_amount = _quantize_money(
        sum((payment.amount for payment in normalized_payments), ZERO_MONEY)
    )
    if captured_amount != advance_amount:
        raise OrderValidationError(
            "El desglose del anticipo debe coincidir exactamente con el anticipo capturado."
        )

    return normalized_payments


def _prepare_settlement_payments(
    *,
    settlement_amount: Decimal,
    settlement_payment_method_code: str,
    settlement_payments: Sequence[DeliverCustomerOrderSettlementPaymentRequest],
) -> list[PreparedOrderAdvancePayment]:
    if settlement_payment_method_code != ORDER_PAYMENT_METHOD_MIXED:
        if settlement_payments:
            raise OrderValidationError(
                "Solo captura el desglose de la liquidacion final cuando el metodo sea mixto."
            )
        return [
            PreparedOrderAdvancePayment(
                payment_method_code=settlement_payment_method_code,
                amount=settlement_amount,
            )
        ]

    if len(settlement_payments) != 2:
        raise OrderValidationError(
            "El cobro mixto de la liquidacion final requiere efectivo y tarjeta."
        )

    normalized_payments: list[PreparedOrderAdvancePayment] = []
    seen_payment_methods: set[str] = set()
    for payment in settlement_payments:
        payment_method_code = _validate_payment_method_code(payment.payment_method_code)
        if payment_method_code == ORDER_PAYMENT_METHOD_MIXED:
            raise OrderValidationError(
                "El cobro mixto de la liquidacion final debe desglosarse en efectivo y tarjeta."
            )
        if payment_method_code in seen_payment_methods:
            raise OrderValidationError(
                "No repitas el mismo metodo dentro de la liquidacion final mixta."
            )
        normalized_payments.append(
            PreparedOrderAdvancePayment(
                payment_method_code=payment_method_code,
                amount=_quantize_money(payment.amount),
            )
        )
        seen_payment_methods.add(payment_method_code)

    if seen_payment_methods != {ORDER_PAYMENT_METHOD_CASH, ORDER_PAYMENT_METHOD_CARD}:
        raise OrderValidationError(
            "El cobro mixto de la liquidacion final requiere efectivo y tarjeta."
        )

    captured_amount = _quantize_money(
        sum((payment.amount for payment in normalized_payments), ZERO_MONEY)
    )
    if captured_amount != settlement_amount:
        raise OrderValidationError(
            "El desglose de la liquidacion final debe coincidir exactamente con el faltante "
            "del pedido."
        )

    return normalized_payments


def _prepare_cancellation_refund_payments(
    session: Session,
    *,
    order: CustomerOrder,
    refund_amount: Decimal,
) -> list[PreparedOrderAdvancePayment]:
    if refund_amount == ZERO_MONEY:
        return []

    advance_payment_records = session.execute(
        select(CustomerOrderPayment)
        .where(
            CustomerOrderPayment.customer_order_id == order.id,
            CustomerOrderPayment.payment_type == ORDER_PAYMENT_TYPE_ADVANCE,
        )
        .order_by(CustomerOrderPayment.sequence)
    ).scalars()
    prepared_refund_payments = [
        PreparedOrderAdvancePayment(
            payment_method_code=payment.payment_method_code,
            amount=_quantize_money(payment.amount),
        )
        for payment in advance_payment_records
    ]
    recorded_advance_amount = _quantize_money(
        sum((payment.amount for payment in prepared_refund_payments), ZERO_MONEY)
    )
    if recorded_advance_amount != refund_amount:
        raise OrderStateConflictError(
            "No fue posible reconstruir el anticipo para registrar su devolucion."
        )
    return prepared_refund_payments


def _get_cancellation_refund_amount(
    order: CustomerOrder,
    *,
    effective_at: datetime,
) -> Decimal:
    advance_amount = _quantize_money(order.advance_amount)
    if advance_amount == ZERO_MONEY:
        return ZERO_MONEY
    if order.status not in {ORDER_STATUS_PENDING, ORDER_STATUS_READY}:
        return ZERO_MONEY
    if order.requested_for_at is None:
        return ZERO_MONEY
    refund_cutoff = order.requested_for_at - timedelta(days=1)
    if effective_at > refund_cutoff:
        return ZERO_MONEY
    return advance_amount


def _validate_payment_method_code(value: str | None) -> str:
    normalized = _normalize_optional_string(value)
    if normalized is None:
        raise OrderValidationError("Selecciona un metodo de pago valido.")
    payment_method_code = normalized.upper()
    if payment_method_code not in VALID_ORDER_PAYMENT_METHOD_CODES:
        raise OrderValidationError("Selecciona un metodo de pago valido.")
    return payment_method_code


def _normalize_optional_string(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def _quantize_money(value: Decimal | int | None) -> Decimal:
    raw_value = ZERO_MONEY if value is None else Decimal(value)
    return raw_value.quantize(MONEY_QUANTIZER, rounding=ROUND_HALF_UP)


def _quantize_quantity(value: Decimal | int) -> Decimal:
    quantized = Decimal(value).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)
    if quantized <= Decimal("0.000"):
        raise OrderValidationError("La cantidad de cada producto debe ser mayor a cero.")
    return quantized
