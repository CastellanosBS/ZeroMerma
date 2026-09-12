from __future__ import annotations

import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from decimal import ROUND_HALF_UP, Decimal
from typing import cast as type_cast
from zoneinfo import ZoneInfo

from sqlalchemy import Select, String, cast, exists, func, or_, select
from sqlalchemy.engine import RowMapping
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from zeromerma_api.core.config import ApiSettings, get_settings
from zeromerma_api.modules.audit.application.service import AuditRecorder
from zeromerma_api.modules.audit.application.visibility import (
    AuditVisibilityQueryService,
    BackofficeNotificationConfig,
    build_audit_actor_snapshot,
)
from zeromerma_api.modules.branches.application.access import (
    WorkstationAccessService,
    WorkstationContext,
)
from zeromerma_api.modules.branches.application.schemas import BranchSummary, WorkstationSummary
from zeromerma_api.modules.branches.infrastructure.models import Branch, Workstation
from zeromerma_api.modules.cash.application.schemas import CashSessionView
from zeromerma_api.modules.cash.application.services import CashSessionQueryService
from zeromerma_api.modules.catalog.domain.constants import (
    CATALOG_CAPTURE_MODE_CLASS_CAPTURE,
    CATALOG_CAPTURE_MODE_PRODUCT_DIRECT,
)
from zeromerma_api.modules.catalog.domain.exceptions import (
    ProductClassNotFoundError,
    ProductNotFoundError,
)
from zeromerma_api.modules.catalog.infrastructure.models import Product, ProductClass
from zeromerma_api.modules.identity.application.schemas import AuthenticatedUser
from zeromerma_api.modules.identity.infrastructure.models import User
from zeromerma_api.modules.operations.domain.constants import BRANCH_BRAND_MAPPING
from zeromerma_api.modules.outbox.application.service import OutboxWriter
from zeromerma_api.modules.returns.application.schemas import (
    ReturnableSaleLineView,
    ReturnCommitRequest,
    ReturnControlsView,
    ReturnFilterOptionView,
    ReturnHistoryListItemView,
    ReturnOriginalSaleDetailResponse,
    ReturnPaymentSummaryView,
    ReturnProductOptionView,
    ReturnReasonView,
    ReturnRefundMethodView,
    ReturnSaleSearchItemView,
    ReturnsBootstrapResponse,
    ReturnsClassProductsResponse,
    ReturnScopeView,
    ReturnsHistoryResponse,
    ReturnsSearchSalesResponse,
    SaleReturnCommittedLineView,
    SaleReturnDetailResponse,
)
from zeromerma_api.modules.returns.domain.constants import (
    OUTBOX_EVENT_SALE_RETURN_BACKOFFICE_REVIEW_REQUESTED_V1,
    OUTBOX_EVENT_SALE_RETURN_COMMITTED_V1,
    RETURN_DISPOSITION_RESTOCK_BACKROOM,
    RETURN_DISPOSITION_RESTOCK_COUNTER,
    RETURN_DISPOSITION_SEND_TO_WASTE,
    RETURN_REASON_DEFINITIONS,
    RETURN_SCOPE_CURRENT_SHIFT,
    RETURN_SCOPE_RECENT,
    RETURN_SCOPE_TODAY,
    RETURN_STATUS_COMMITTED,
    VALID_RETURN_DISPOSITION_CODES,
    VALID_RETURN_REASON_CODES,
    VALID_RETURN_REFUND_METHOD_CODES,
    VALID_RETURN_SCOPES,
)
from zeromerma_api.modules.returns.domain.exceptions import (
    SaleReturnConflictError,
    SaleReturnNotFoundError,
    SaleReturnValidationError,
)
from zeromerma_api.modules.returns.infrastructure.models import SaleReturn, SaleReturnLine
from zeromerma_api.modules.sales.application.schemas import SaleLineView
from zeromerma_api.modules.sales.application.services import SaleQueryService
from zeromerma_api.modules.sales.domain.constants import (
    CASH_MOVEMENT_DIRECTION_OUT,
    SALE_PAYMENT_METHOD_CASH,
    SALE_STATUS_CONFIRMED,
)
from zeromerma_api.modules.sales.infrastructure.models import CashMovement, Sale, SaleLine

MAX_RETURN_SEARCH_RESULTS = 80
MONEY_QUANTIZER = Decimal("0.01")
QUANTITY_QUANTIZER = Decimal("0.001")
ZERO_MONEY = Decimal("0.00")
ZERO_QUANTITY = Decimal("0.000")
CASH_MOVEMENT_TYPE_SALE_RETURN_REFUND = "SALE_RETURN_REFUND"
RETURN_STATUS_NOT_RETURNED = "NOT_RETURNED"
RETURN_STATUS_PARTIALLY_RETURNED = "PARTIALLY_RETURNED"
RETURN_STATUS_FULLY_RETURNED = "FULLY_RETURNED"


@dataclass(frozen=True)
class ReturnSaleSummary:
    return_count: int
    returned_amount: Decimal
    returned_quantity: Decimal


@dataclass(frozen=True)
class ReturnReasonDefinition:
    code: str
    label: str
    display_order: int


@dataclass(frozen=True)
class PreparedExactProduct:
    product_id: uuid.UUID
    product_code: str
    product_name: str
    product_class_id: uuid.UUID
    product_class_code: str
    product_class_name: str


@dataclass(frozen=True)
class PreparedReturnLine:
    original_sale_line_id: uuid.UUID
    original_capture_mode: str
    original_catalog_code_snapshot: str
    original_catalog_name_snapshot: str
    returned_product_id: uuid.UUID
    returned_product_code_snapshot: str
    returned_product_name_snapshot: str
    returned_product_class_id: uuid.UUID
    returned_product_class_code_snapshot: str
    returned_product_class_name_snapshot: str
    returned_quantity: Decimal
    refund_unit_price: Decimal
    refund_line_total_amount: Decimal
    disposition_code: str


class ReturnsQueryService:
    def __init__(
        self,
        settings: ApiSettings | None = None,
        workstation_access: WorkstationAccessService | None = None,
        cash_session_query: CashSessionQueryService | None = None,
        sale_query_service: SaleQueryService | None = None,
        audit_visibility: AuditVisibilityQueryService | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._workstation_access = workstation_access or WorkstationAccessService()
        self._cash_session_query = cash_session_query or CashSessionQueryService()
        self._sale_query_service = sale_query_service or SaleQueryService()
        self._audit_visibility = audit_visibility or AuditVisibilityQueryService()

    def get_bootstrap(
        self,
        session: Session,
        *,
        current_user: AuthenticatedUser,
        workstation_code: str,
    ) -> ReturnsBootstrapResponse:
        context = self._workstation_access.resolve_context(
            session,
            user_id=current_user.id,
            workstation_code=workstation_code,
        )
        current_open_cash_session = self._cash_session_query.get_open_session_for_workstation_code(
            session,
            workstation_code=workstation_code,
        )
        local_timestamp = datetime.now(tz=UTC).astimezone(ZoneInfo(context.branch_timezone))

        return ReturnsBootstrapResponse(
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
            return_operations_allowed=(
                current_open_cash_session is not None
                and current_open_cash_session.user_id == current_user.id
            ),
            default_scope=RETURN_SCOPE_CURRENT_SHIFT,
            available_scopes=[
                ReturnScopeView(code=RETURN_SCOPE_CURRENT_SHIFT, label="Turno actual"),
                ReturnScopeView(code=RETURN_SCOPE_TODAY, label="Hoy"),
                ReturnScopeView(code=RETURN_SCOPE_RECENT, label="Recientes"),
            ],
            return_reasons=[
                ReturnReasonView(code=reason.code, label=reason.label)
                for reason in _get_return_reason_definitions()
            ],
            refund_methods=[
                ReturnRefundMethodView(
                    code="CASH",
                    label="Efectivo",
                    is_enabled=True,
                ),
                ReturnRefundMethodView(
                    code="CARD",
                    label="Tarjeta",
                    is_enabled=False,
                    availability_note="Reverso de tarjeta pendiente de integracion.",
                ),
                ReturnRefundMethodView(
                    code="MIXED",
                    label="Mixto",
                    is_enabled=False,
                    availability_note="Reembolso mixto pendiente de integracion.",
                ),
            ],
            return_controls=ReturnControlsView(
                high_refund_amount_threshold=self._settings.return_high_refund_amount_threshold,
                old_sale_days_threshold=self._settings.return_old_sale_days_threshold,
                high_risk_requires_acknowledgement=True,
            ),
        )

    def search_sales(
        self,
        session: Session,
        *,
        current_user: AuthenticatedUser,
        workstation_code: str,
        scope: str | None,
        query: str | None,
        date_from: date | None,
        date_to: date | None,
    ) -> ReturnsSearchSalesResponse:
        context = self._workstation_access.resolve_context(
            session,
            user_id=current_user.id,
            workstation_code=workstation_code,
        )
        current_open_cash_session = _require_open_cash_session(
            session,
            cash_session_query=self._cash_session_query,
            current_user=current_user,
            workstation_code=workstation_code,
            context=context,
        )
        normalized_scope = _validate_scope(scope)
        normalized_query = _normalize_query(query)
        normalized_date_from, normalized_date_to = _validate_date_range(date_from, date_to)

        line_stats_subquery = (
            select(
                SaleLine.sale_id.label("sale_id"),
                func.count(SaleLine.id).label("item_count"),
                func.coalesce(func.sum(SaleLine.quantity), ZERO_QUANTITY).label("total_quantity"),
            )
            .group_by(SaleLine.sale_id)
            .subquery()
        )
        statement = type_cast(
            Select[tuple[object, ...]],
            select(
                Sale.id,
                Sale.confirmed_at,
                Sale.total_amount,
                Sale.currency_code,
                User.full_name.label("operator_full_name"),
                func.coalesce(line_stats_subquery.c.item_count, 0).label("item_count"),
                func.coalesce(line_stats_subquery.c.total_quantity, ZERO_QUANTITY).label(
                    "total_quantity"
                ),
            )
            .select_from(Sale)
            .join(User, User.id == Sale.operator_id)
            .outerjoin(line_stats_subquery, line_stats_subquery.c.sale_id == Sale.id)
            .where(
                Sale.branch_id == context.branch_id,
                Sale.status == SALE_STATUS_CONFIRMED,
            ),
        )
        if normalized_date_from is None and normalized_date_to is None:
            statement = _apply_scope_filters(
                statement,
                normalized_scope=normalized_scope,
                context=context,
                current_cash_session_id=current_open_cash_session.id,
            )
        else:
            statement = _apply_date_range_filters(
                statement,
                branch_timezone=context.branch_timezone,
                date_from=normalized_date_from,
                date_to=normalized_date_to,
            )
        statement = _apply_search_filters(statement, normalized_query)
        rows = session.execute(
            statement.order_by(Sale.confirmed_at.desc()).limit(MAX_RETURN_SEARCH_RESULTS)
        ).mappings().all()
        sale_ids = [row["id"] for row in rows]
        return_summary_by_sale_id = _get_return_summary_by_sale_ids(
            session,
            sale_ids=sale_ids,
        )

        return ReturnsSearchSalesResponse(
            workstation_code=workstation_code,
            scope=normalized_scope,
            query=_normalize_optional_string(query),
            date_from=normalized_date_from,
            date_to=normalized_date_to,
            sales=[
                _build_return_sale_search_item_view(
                    row=row,
                    summary=return_summary_by_sale_id.get(row["id"]),
                )
                for row in rows
            ],
        )

    def list_return_history(
        self,
        session: Session,
        *,
        current_user: AuthenticatedUser,
        workstation_code: str,
        scope: str | None,
        query: str | None,
        date_from: date | None,
        date_to: date | None,
        created_by_user_id: uuid.UUID | None,
        reason_code: str | None,
    ) -> ReturnsHistoryResponse:
        context = self._workstation_access.resolve_context(
            session,
            user_id=current_user.id,
            workstation_code=workstation_code,
        )
        current_open_cash_session = _require_open_cash_session(
            session,
            cash_session_query=self._cash_session_query,
            current_user=current_user,
            workstation_code=workstation_code,
            context=context,
        )
        normalized_scope = _validate_scope(scope)
        normalized_query = _normalize_query(query)
        normalized_date_from, normalized_date_to = _validate_date_range(date_from, date_to)
        normalized_reason_code = _normalize_optional_string(reason_code)
        line_count_subquery = (
            select(
                SaleReturnLine.sale_return_id.label("sale_return_id"),
                func.count(SaleReturnLine.id).label("line_count"),
            )
            .group_by(SaleReturnLine.sale_return_id)
            .subquery()
        )
        base_statement = type_cast(
            Select[tuple[object, ...]],
            select(
                SaleReturn.id,
                SaleReturn.original_sale_id,
                SaleReturn.status,
                SaleReturn.created_by_user_id,
                User.full_name.label("created_by_user_full_name"),
                SaleReturn.reason_code,
                SaleReturn.reason_name,
                SaleReturn.refund_method_code,
                SaleReturn.total_refund_amount,
                SaleReturn.currency_code,
                SaleReturn.created_at_utc,
                Branch.code.label("branch_code"),
                Branch.name.label("branch_name"),
                Workstation.code.label("workstation_code"),
                Workstation.name.label("workstation_name"),
                func.coalesce(line_count_subquery.c.line_count, 0).label("line_count"),
            )
            .select_from(SaleReturn)
            .join(User, User.id == SaleReturn.created_by_user_id)
            .join(Branch, Branch.id == SaleReturn.branch_id)
            .join(Workstation, Workstation.id == SaleReturn.workstation_id)
            .outerjoin(line_count_subquery, line_count_subquery.c.sale_return_id == SaleReturn.id)
            .where(
                SaleReturn.branch_id == context.branch_id,
                SaleReturn.workstation_id == context.workstation_id,
                SaleReturn.status == RETURN_STATUS_COMMITTED,
            ),
        )
        if normalized_date_from is None and normalized_date_to is None:
            base_statement = _apply_return_history_scope_filters(
                base_statement,
                normalized_scope=normalized_scope,
                context=context,
                current_cash_session_id=current_open_cash_session.id,
            )
        else:
            base_statement = _apply_return_history_date_range_filters(
                base_statement,
                branch_timezone=context.branch_timezone,
                date_from=normalized_date_from,
                date_to=normalized_date_to,
            )

        available_user_rows = session.execute(
            base_statement.with_only_columns(
                SaleReturn.created_by_user_id,
                User.full_name.label("created_by_user_full_name"),
            )
            .distinct()
            .order_by(User.full_name.asc())
        ).mappings().all()
        available_reason_rows = session.execute(
            base_statement.with_only_columns(
                SaleReturn.reason_code,
                SaleReturn.reason_name,
            )
            .distinct()
            .order_by(SaleReturn.reason_name.asc(), SaleReturn.reason_code.asc())
        ).mappings().all()

        filtered_statement = base_statement
        if created_by_user_id is not None:
            filtered_statement = filtered_statement.where(
                SaleReturn.created_by_user_id == created_by_user_id
            )
        if normalized_reason_code is not None:
            filtered_statement = filtered_statement.where(
                SaleReturn.reason_code == normalized_reason_code
            )
        if normalized_query is not None:
            pattern = f"%{normalized_query}%"
            filtered_statement = filtered_statement.where(
                or_(
                    SaleReturn.reason_name.ilike(pattern),
                    User.full_name.ilike(pattern),
                    SaleReturn.id.cast(String).ilike(pattern),
                    func.concat("DEV-", func.substr(SaleReturn.id.cast(String), 1, 8)).ilike(
                        pattern
                    ),
                    SaleReturn.original_sale_id.cast(String).ilike(pattern),
                )
            )

        rows = session.execute(
            filtered_statement.order_by(SaleReturn.created_at_utc.desc()).limit(MAX_RETURN_SEARCH_RESULTS)
        ).mappings().all()

        return ReturnsHistoryResponse(
            workstation_code=workstation_code,
            scope=normalized_scope,
            query=normalized_query,
            date_from=normalized_date_from,
            date_to=normalized_date_to,
            created_by_user_id=str(created_by_user_id) if created_by_user_id is not None else None,
            reason_code=normalized_reason_code,
            available_scopes=[
                ReturnScopeView(code=RETURN_SCOPE_CURRENT_SHIFT, label="Turno actual"),
                ReturnScopeView(code=RETURN_SCOPE_TODAY, label="Hoy"),
                ReturnScopeView(code=RETURN_SCOPE_RECENT, label="Recientes"),
            ],
            available_users=[
                ReturnFilterOptionView(
                    value=str(row["created_by_user_id"]),
                    label=row["created_by_user_full_name"],
                )
                for row in available_user_rows
            ],
            available_reasons=[
                ReturnFilterOptionView(
                    value=row["reason_code"],
                    label=row["reason_name"],
                )
                for row in available_reason_rows
                if row["reason_code"] is not None and row["reason_name"] is not None
            ],
            records=[
                ReturnHistoryListItemView(
                    id=row["id"],
                    folio=_build_return_folio(row["id"]),
                    original_sale_id=row["original_sale_id"],
                    original_sale_folio=_build_sale_folio(row["original_sale_id"]),
                    status=row["status"],
                    branch_code=row["branch_code"],
                    branch_name=row["branch_name"],
                    workstation_code=row["workstation_code"],
                    workstation_name=row["workstation_name"],
                    created_by_user_id=row["created_by_user_id"],
                    created_by_user_full_name=row["created_by_user_full_name"],
                    reason_code=row["reason_code"],
                    reason_name=row["reason_name"],
                    refund_method_code=row["refund_method_code"],
                    total_refund_amount=_quantize_money(row["total_refund_amount"]),
                    currency_code=row["currency_code"],
                    line_count=int(row["line_count"]),
                    created_at_utc=row["created_at_utc"],
                )
                for row in rows
            ],
        )

    def get_original_sale_detail(
        self,
        session: Session,
        *,
        current_user: AuthenticatedUser,
        workstation_code: str,
        sale_id: uuid.UUID,
    ) -> ReturnOriginalSaleDetailResponse:
        context = self._workstation_access.resolve_context(
            session,
            user_id=current_user.id,
            workstation_code=workstation_code,
        )
        _require_open_cash_session(
            session,
            cash_session_query=self._cash_session_query,
            current_user=current_user,
            workstation_code=workstation_code,
            context=context,
        )
        sale_detail = self._sale_query_service.get_sale_by_id(
            session,
            sale_id=sale_id,
            user_id=current_user.id,
        )
        if sale_detail.branch_id != context.branch_id:
            raise SaleReturnNotFoundError("La venta original no existe en la sucursal actual.")

        returned_quantities = _get_returned_quantity_by_sale_line_ids(
            session,
            sale_line_ids=[line.id for line in sale_detail.lines],
        )
        sale_summary = _get_return_summary_by_sale_ids(session, sale_ids=[sale_detail.id]).get(
            sale_detail.id,
            ReturnSaleSummary(
                return_count=0,
                returned_amount=ZERO_MONEY,
                returned_quantity=ZERO_QUANTITY,
            ),
        )
        returnable_lines = [
            _build_returnable_sale_line_view(
                line,
                already_returned_quantity=returned_quantities.get(line.id, ZERO_QUANTITY),
            )
            for line in sale_detail.lines
        ]

        return ReturnOriginalSaleDetailResponse(
            id=sale_detail.id,
            folio=_build_sale_folio(sale_detail.id),
            status=sale_detail.status,
            confirmed_at=sale_detail.confirmed_at,
            branch=BranchSummary(
                id=sale_detail.branch_id,
                code=sale_detail.branch_code,
                name=sale_detail.branch_name,
                timezone=context.branch_timezone,
                is_active=context.branch_is_active,
            ),
            workstation=WorkstationSummary(
                id=sale_detail.workstation_id,
                code=sale_detail.workstation_code,
                name=sale_detail.workstation_name,
                is_active=context.workstation_is_active,
            ),
            operator=AuthenticatedUser(
                id=sale_detail.operator_id,
                email=sale_detail.operator_email,
                full_name=sale_detail.operator_full_name,
                is_active=True,
            ),
            cash_session_id=sale_detail.cash_session_id,
            currency_code=sale_detail.currency_code,
            subtotal_amount=sale_detail.subtotal_amount,
            total_amount=sale_detail.total_amount,
            paid_amount=sale_detail.paid_amount,
            change_amount=sale_detail.change_amount,
            return_count=sale_summary.return_count,
            returned_amount=_quantize_money(sale_summary.returned_amount),
            return_status=_get_sale_return_status(
                total_quantity=_quantize_optional_quantity(
                    sum((line.quantity for line in sale_detail.lines), start=ZERO_QUANTITY)
                ),
                returned_quantity=sale_summary.returned_quantity,
            ),
            has_returnable_lines=any(
                line.remaining_returnable_quantity > ZERO_QUANTITY for line in returnable_lines
            ),
            lines=returnable_lines,
            payments=[
                ReturnPaymentSummaryView(
                    payment_method_code=payment.payment_method_code,
                    tendered_amount=payment.tendered_amount,
                    applied_amount=payment.applied_amount,
                    change_amount=payment.change_amount,
                    currency_code=payment.currency_code,
                    received_at=payment.received_at,
                )
                for payment in sale_detail.payments
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
    ) -> ReturnsClassProductsResponse:
        context = self._workstation_access.resolve_context(
            session,
            user_id=current_user.id,
            workstation_code=workstation_code,
        )
        _require_open_cash_session(
            session,
            cash_session_query=self._cash_session_query,
            current_user=current_user,
            workstation_code=workstation_code,
            context=context,
        )
        normalized_query = _normalize_query(query)
        product_class = session.execute(
            select(ProductClass).where(
                ProductClass.id == class_id,
                ProductClass.is_active.is_(True),
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
            )
            .where(
                Product.product_class_id == class_id,
                Product.is_active.is_(True),
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

        product_rows = session.execute(statement).mappings()
        return ReturnsClassProductsResponse(
            class_id=product_class.id,
            class_code=product_class.code,
            class_name=product_class.name,
            query=_normalize_optional_string(query),
            products=[
                ReturnProductOptionView(
                    id=row["id"],
                    code=row["code"],
                    name=row["name"],
                    quick_name=row["quick_name"],
                    display_order=row["display_order"],
                )
                for row in product_rows
            ],
        )

    def get_sale_return_detail(
        self,
        session: Session,
        *,
        current_user: AuthenticatedUser,
        workstation_code: str,
        return_id: uuid.UUID,
    ) -> SaleReturnDetailResponse:
        context = self._workstation_access.resolve_context(
            session,
            user_id=current_user.id,
            workstation_code=workstation_code,
        )
        _require_open_cash_session(
            session,
            cash_session_query=self._cash_session_query,
            current_user=current_user,
            workstation_code=workstation_code,
            context=context,
        )
        sale_return = session.execute(
            select(SaleReturn).where(
                SaleReturn.id == return_id,
                SaleReturn.branch_id == context.branch_id,
            )
        ).scalar_one_or_none()
        if sale_return is None:
            raise SaleReturnNotFoundError("La devolucion solicitada no existe.")

        original_sale = session.get(Sale, sale_return.original_sale_id)
        branch = session.get(Branch, sale_return.branch_id)
        workstation = session.get(Workstation, sale_return.workstation_id)
        created_by = session.get(User, sale_return.created_by_user_id)
        if original_sale is None or branch is None or workstation is None or created_by is None:
            raise SaleReturnValidationError(
                "No fue posible reconstruir el detalle de la devolucion."
            )

        line_rows = session.execute(
            select(SaleReturnLine)
            .where(SaleReturnLine.sale_return_id == sale_return.id)
            .order_by(SaleReturnLine.line_number.asc())
        ).scalars()

        return SaleReturnDetailResponse(
            id=sale_return.id,
            folio=_build_return_folio(sale_return.id),
            original_sale_id=original_sale.id,
            original_sale_folio=_build_sale_folio(original_sale.id),
            branch=BranchSummary(
                id=branch.id,
                code=branch.code,
                name=branch.name,
                timezone=branch.timezone,
                is_active=branch.is_active,
            ),
            workstation=WorkstationSummary(
                id=workstation.id,
                code=workstation.code,
                name=workstation.name,
                is_active=workstation.is_active,
            ),
            created_by=AuthenticatedUser(
                id=created_by.id,
                email=created_by.email,
                full_name=created_by.full_name,
                is_active=created_by.is_active,
            ),
            cash_session_id=sale_return.cash_session_id,
            reason_code=sale_return.reason_code,
            reason_name=sale_return.reason_name,
            refund_method_code=sale_return.refund_method_code,
            currency_code=sale_return.currency_code,
            total_refund_amount=_quantize_money(sale_return.total_refund_amount),
            notes=sale_return.notes,
            created_at_utc=sale_return.created_at_utc,
            audit_summary=self._audit_visibility.build_summary(
                session,
                created_actor=build_audit_actor_snapshot(
                    user_id=created_by.id,
                    full_name=created_by.full_name,
                    email=created_by.email,
                ),
                created_at_utc=sale_return.created_at_utc,
                confirmed_at_utc=sale_return.created_at_utc,
                acknowledgement_label="Validacion de devolucion",
                reason_label=sale_return.reason_name,
                notes=sale_return.notes,
                notification_config=BackofficeNotificationConfig(
                    aggregate_id=str(sale_return.id),
                    aggregate_type="sale_return",
                    event_names=(OUTBOX_EVENT_SALE_RETURN_BACKOFFICE_REVIEW_REQUESTED_V1,),
                    label="Revision de backoffice",
                ),
            ),
            lines=[
                SaleReturnCommittedLineView(
                    id=line.id,
                    line_number=line.line_number,
                    original_sale_line_id=line.original_sale_line_id,
                    original_catalog_name_snapshot=line.original_catalog_name_snapshot,
                    returned_product_name_snapshot=line.returned_product_name_snapshot,
                    returned_quantity=_quantize_quantity(line.returned_quantity),
                    refund_unit_price=_quantize_money(line.refund_unit_price),
                    refund_line_total_amount=_quantize_money(line.refund_line_total_amount),
                    disposition_code=line.disposition_code,
                )
                for line in line_rows
            ],
        )


class ReturnsCommandService:
    def __init__(
        self,
        settings: ApiSettings | None = None,
        workstation_access: WorkstationAccessService | None = None,
        cash_session_query: CashSessionQueryService | None = None,
        sale_query_service: SaleQueryService | None = None,
        audit_recorder: AuditRecorder | None = None,
        outbox_writer: OutboxWriter | None = None,
        query_service: ReturnsQueryService | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._workstation_access = workstation_access or WorkstationAccessService()
        self._cash_session_query = cash_session_query or CashSessionQueryService()
        self._sale_query_service = sale_query_service or SaleQueryService()
        self._audit_recorder = audit_recorder or AuditRecorder()
        self._outbox_writer = outbox_writer or OutboxWriter()
        self._query_service = query_service or ReturnsQueryService(
            settings=self._settings,
            workstation_access=self._workstation_access,
            cash_session_query=self._cash_session_query,
            sale_query_service=self._sale_query_service,
        )

    def commit_return(
        self,
        session: Session,
        *,
        current_user: AuthenticatedUser,
        command: ReturnCommitRequest,
        request_id: str | None,
    ) -> SaleReturnDetailResponse:
        context = self._workstation_access.resolve_context(
            session,
            user_id=current_user.id,
            workstation_code=command.workstation_code,
        )
        current_open_cash_session = _require_open_cash_session(
            session,
            cash_session_query=self._cash_session_query,
            current_user=current_user,
            workstation_code=command.workstation_code,
            context=context,
        )
        reason = _validate_return_reason(command.reason_code)
        refund_method_code = _validate_refund_method_code(command.refund_method_code)
        sale_detail = self._sale_query_service.get_sale_by_id(
            session,
            sale_id=command.original_sale_id,
            user_id=current_user.id,
        )
        if sale_detail.branch_id != context.branch_id:
            raise SaleReturnNotFoundError("La venta original no existe en la sucursal actual.")
        if sale_detail.status != SALE_STATUS_CONFIRMED:
            raise SaleReturnValidationError(
                "Solo se pueden devolver ventas confirmadas."
            )

        sale_lines_by_id = {line.id: line for line in sale_detail.lines}
        if not command.lines:
            raise SaleReturnValidationError("Selecciona al menos una linea para devolver.")

        seen_line_ids: set[uuid.UUID] = set()
        duplicated_line_ids: set[uuid.UUID] = set()
        for requested_line in command.lines:
            if requested_line.original_sale_line_id in seen_line_ids:
                duplicated_line_ids.add(requested_line.original_sale_line_id)
                continue
            seen_line_ids.add(requested_line.original_sale_line_id)
        if duplicated_line_ids:
            raise SaleReturnValidationError(
                "No repitas la misma linea de venta dentro de la misma devolucion."
            )

        returned_quantities = _get_returned_quantity_by_sale_line_ids(
            session,
            sale_line_ids=list(sale_lines_by_id.keys()),
        )
        prepared_lines: list[PreparedReturnLine] = []
        for line_request in command.lines:
            original_line = sale_lines_by_id.get(line_request.original_sale_line_id)
            if original_line is None:
                raise SaleReturnValidationError(
                    "La devolucion incluye una linea que no pertenece a la venta original."
                )

            already_returned_quantity = returned_quantities.get(original_line.id, ZERO_QUANTITY)
            returned_quantity = _quantize_quantity(line_request.returned_quantity)
            remaining_returnable_quantity = _quantize_quantity(
                original_line.quantity - already_returned_quantity
            )
            if returned_quantity > remaining_returnable_quantity:
                raise SaleReturnValidationError(
                    "La cantidad a devolver supera lo que aun se puede devolver en esa linea."
                )

            disposition_code = _validate_disposition_code(line_request.disposition_code)
            exact_product = _resolve_exact_return_product(
                session,
                sale_line=original_line,
                exact_product_id=line_request.exact_product_id,
                disposition_code=disposition_code,
            )
            refund_unit_price = _quantize_money(original_line.unit_price)
            prepared_lines.append(
                PreparedReturnLine(
                    original_sale_line_id=original_line.id,
                    original_capture_mode=original_line.capture_mode,
                    original_catalog_code_snapshot=original_line.catalog_code_snapshot,
                    original_catalog_name_snapshot=original_line.catalog_name_snapshot,
                    returned_product_id=exact_product.product_id,
                    returned_product_code_snapshot=exact_product.product_code,
                    returned_product_name_snapshot=exact_product.product_name,
                    returned_product_class_id=exact_product.product_class_id,
                    returned_product_class_code_snapshot=exact_product.product_class_code,
                    returned_product_class_name_snapshot=exact_product.product_class_name,
                    returned_quantity=returned_quantity,
                    refund_unit_price=refund_unit_price,
                    refund_line_total_amount=_quantize_money(refund_unit_price * returned_quantity),
                    disposition_code=disposition_code,
                )
            )

        total_refund_amount = _quantize_money(
            sum(
                (prepared_line.refund_line_total_amount for prepared_line in prepared_lines),
                ZERO_MONEY,
            )
        )
        is_high_amount = (
            total_refund_amount >= self._settings.return_high_refund_amount_threshold
        )
        sale_age_days = _get_sale_age_in_days(
            confirmed_at=sale_detail.confirmed_at,
            branch_timezone=context.branch_timezone,
        )
        is_old_sale = sale_age_days >= self._settings.return_old_sale_days_threshold
        requires_high_risk_acknowledgement = is_high_amount or is_old_sale
        if requires_high_risk_acknowledgement and not command.high_risk_acknowledged:
            raise SaleReturnValidationError(
                "Confirma la devolucion de alto riesgo antes de registrar."
            )
        created_at = datetime.now(tz=UTC)
        resolved_request_id = request_id or str(uuid.uuid4())
        sale_return = SaleReturn(
            original_sale_id=sale_detail.id,
            branch_id=context.branch_id,
            workstation_id=context.workstation_id,
            cash_session_id=current_open_cash_session.id,
            created_by_user_id=current_user.id,
            status=RETURN_STATUS_COMMITTED,
            reason_code=reason.code,
            reason_name=reason.label,
            refund_method_code=refund_method_code,
            currency_code=sale_detail.currency_code,
            total_refund_amount=total_refund_amount,
            notes=_normalize_optional_string(command.notes),
            created_at_utc=created_at,
        )

        try:
            session.add(sale_return)
            session.flush()

            for index, prepared_line in enumerate(prepared_lines, start=1):
                session.add(
                    SaleReturnLine(
                        sale_return_id=sale_return.id,
                        line_number=index,
                        original_sale_line_id=prepared_line.original_sale_line_id,
                        original_capture_mode=prepared_line.original_capture_mode,
                        original_catalog_code_snapshot=prepared_line.original_catalog_code_snapshot,
                        original_catalog_name_snapshot=prepared_line.original_catalog_name_snapshot,
                        returned_product_id=prepared_line.returned_product_id,
                        returned_product_code_snapshot=prepared_line.returned_product_code_snapshot,
                        returned_product_name_snapshot=prepared_line.returned_product_name_snapshot,
                        returned_product_class_id=prepared_line.returned_product_class_id,
                        returned_product_class_code_snapshot=prepared_line.returned_product_class_code_snapshot,
                        returned_product_class_name_snapshot=prepared_line.returned_product_class_name_snapshot,
                        returned_quantity=prepared_line.returned_quantity,
                        refund_unit_price=prepared_line.refund_unit_price,
                        refund_line_total_amount=prepared_line.refund_line_total_amount,
                        disposition_code=prepared_line.disposition_code,
                    )
                )

            session.add(
                CashMovement(
                    sale_id=sale_detail.id,
                    cash_session_id=current_open_cash_session.id,
                    branch_id=context.branch_id,
                    workstation_id=context.workstation_id,
                    operator_id=current_user.id,
                    movement_type=CASH_MOVEMENT_TYPE_SALE_RETURN_REFUND,
                    direction=CASH_MOVEMENT_DIRECTION_OUT,
                    payment_method_code=SALE_PAYMENT_METHOD_CASH,
                    amount=total_refund_amount,
                    currency_code=sale_detail.currency_code,
                    occurred_at=created_at,
                )
            )

            self._audit_recorder.record(
                session,
                actor_id=current_user.id,
                action="sale_return.committed",
                resource_type="sale_return",
                resource_id=str(sale_return.id),
                branch_id=context.branch_id,
                request_id=resolved_request_id,
                metadata={
                    "folio": _build_return_folio(sale_return.id),
                    "original_sale_id": str(sale_detail.id),
                    "original_sale_folio": _build_sale_folio(sale_detail.id),
                    "branch_code": context.branch_code,
                    "workstation_code": context.workstation_code,
                    "cash_session_id": str(current_open_cash_session.id),
                    "reason_code": reason.code,
                    "reason_name": reason.label,
                    "refund_method_code": refund_method_code,
                    "currency_code": sale_detail.currency_code,
                    "total_refund_amount": str(total_refund_amount),
                    "high_amount": is_high_amount,
                    "old_sale": is_old_sale,
                    "sale_age_days": sale_age_days,
                    "high_risk_acknowledged": command.high_risk_acknowledged,
                    "high_refund_amount_threshold": str(
                        self._settings.return_high_refund_amount_threshold
                    ),
                    "old_sale_days_threshold": self._settings.return_old_sale_days_threshold,
                    "line_count": len(prepared_lines),
                },
            )
            self._outbox_writer.append(
                session,
                aggregate_type="sale_return",
                aggregate_id=str(sale_return.id),
                event_name=OUTBOX_EVENT_SALE_RETURN_COMMITTED_V1,
                payload={
                    "sale_return_id": str(sale_return.id),
                    "folio": _build_return_folio(sale_return.id),
                    "original_sale_id": str(sale_detail.id),
                    "original_sale_folio": _build_sale_folio(sale_detail.id),
                    "branch_id": str(context.branch_id),
                    "branch_code": context.branch_code,
                    "workstation_id": str(context.workstation_id),
                    "workstation_code": context.workstation_code,
                    "cash_session_id": str(current_open_cash_session.id),
                    "created_by_user_id": str(current_user.id),
                    "reason_code": reason.code,
                    "reason_name": reason.label,
                    "refund_method_code": refund_method_code,
                    "currency_code": sale_detail.currency_code,
                    "total_refund_amount": str(total_refund_amount),
                    "high_amount": is_high_amount,
                    "old_sale": is_old_sale,
                    "sale_age_days": sale_age_days,
                    "high_risk_acknowledged": command.high_risk_acknowledged,
                    "high_refund_amount_threshold": str(
                        self._settings.return_high_refund_amount_threshold
                    ),
                    "old_sale_days_threshold": self._settings.return_old_sale_days_threshold,
                    "notes": sale_return.notes,
                    "created_at_utc": created_at.isoformat(),
                    "lines": [
                        {
                            "original_sale_line_id": str(line.original_sale_line_id),
                            "original_capture_mode": line.original_capture_mode,
                            "returned_product_id": str(line.returned_product_id),
                            "returned_product_code_snapshot": line.returned_product_code_snapshot,
                            "returned_product_name_snapshot": line.returned_product_name_snapshot,
                            "returned_product_class_id": str(line.returned_product_class_id),
                            "returned_quantity": str(line.returned_quantity),
                            "refund_unit_price": str(line.refund_unit_price),
                            "refund_line_total_amount": str(line.refund_line_total_amount),
                            "disposition_code": line.disposition_code,
                        }
                        for line in prepared_lines
                    ],
                },
                headers={"request_id": resolved_request_id},
            )
            if requires_high_risk_acknowledgement:
                self._audit_recorder.record(
                    session,
                    actor_id=current_user.id,
                    action="sale_return.backoffice_review_requested",
                    resource_type="sale_return",
                    resource_id=str(sale_return.id),
                    branch_id=context.branch_id,
                    request_id=resolved_request_id,
                    metadata={
                        "sale_return_id": str(sale_return.id),
                        "folio": _build_return_folio(sale_return.id),
                        "notification_target": "backoffice",
                        "original_sale_id": str(sale_detail.id),
                        "original_sale_folio": _build_sale_folio(sale_detail.id),
                        "reason_code": reason.code,
                        "total_refund_amount": str(total_refund_amount),
                        "high_amount": is_high_amount,
                        "old_sale": is_old_sale,
                        "sale_age_days": sale_age_days,
                    },
                )
                self._outbox_writer.append(
                    session,
                    aggregate_type="sale_return",
                    aggregate_id=str(sale_return.id),
                    event_name=OUTBOX_EVENT_SALE_RETURN_BACKOFFICE_REVIEW_REQUESTED_V1,
                    payload={
                        "sale_return_id": str(sale_return.id),
                        "folio": _build_return_folio(sale_return.id),
                        "notification_target": "backoffice",
                        "branch_code": context.branch_code,
                        "workstation_code": context.workstation_code,
                        "original_sale_id": str(sale_detail.id),
                        "original_sale_folio": _build_sale_folio(sale_detail.id),
                        "reason_code": reason.code,
                        "reason_name": reason.label,
                        "total_refund_amount": str(total_refund_amount),
                        "high_amount": is_high_amount,
                        "old_sale": is_old_sale,
                        "sale_age_days": sale_age_days,
                    },
                    headers={"request_id": resolved_request_id},
                )
            session.commit()
        except IntegrityError as error:
            session.rollback()
            raise SaleReturnValidationError(
                "Las reglas de integridad de la devolucion fallaron durante el guardado."
            ) from error

        return self._query_service.get_sale_return_detail(
            session,
            current_user=current_user,
            workstation_code=command.workstation_code,
            return_id=sale_return.id,
        )


def _build_return_sale_search_item_view(
    *,
    row: RowMapping,
    summary: ReturnSaleSummary | None,
) -> ReturnSaleSearchItemView:
    sale_summary = summary or ReturnSaleSummary(
        return_count=0,
        returned_amount=ZERO_MONEY,
        returned_quantity=ZERO_QUANTITY,
    )
    sale_id = type_cast(uuid.UUID, row["id"])
    total_quantity = _quantize_optional_quantity(type_cast(Decimal, row["total_quantity"]))
    returned_quantity = _quantize_optional_quantity(sale_summary.returned_quantity)
    return ReturnSaleSearchItemView(
        id=sale_id,
        folio=_build_sale_folio(sale_id),
        confirmed_at=type_cast(datetime, row["confirmed_at"]),
        total_amount=type_cast(Decimal, row["total_amount"]),
        currency_code=type_cast(str, row["currency_code"]),
        operator_full_name=type_cast(str, row["operator_full_name"]),
        item_count=int(type_cast(int, row["item_count"])),
        total_quantity=total_quantity,
        return_count=sale_summary.return_count,
        returned_amount=_quantize_money(sale_summary.returned_amount),
        return_status=_get_sale_return_status(
            total_quantity=total_quantity,
            returned_quantity=returned_quantity,
        ),
        has_returnable_quantity=total_quantity > returned_quantity,
    )


def _build_returnable_sale_line_view(
    line: SaleLineView,
    *,
    already_returned_quantity: Decimal,
) -> ReturnableSaleLineView:
    if line.product_class_id is None:
        raise SaleReturnValidationError(
            "La linea original no tiene una clase valida para calcular devoluciones."
        )

    normalized_returned_quantity = _quantize_optional_quantity(already_returned_quantity)
    remaining_returnable_quantity = _quantize_optional_quantity(
        line.quantity - normalized_returned_quantity
    )
    requires_exact_product_selection = line.capture_mode == CATALOG_CAPTURE_MODE_CLASS_CAPTURE

    return ReturnableSaleLineView(
        id=line.id,
        sequence=line.sequence,
        capture_mode=line.capture_mode,
        product_class_id=line.product_class_id,
        product_class_code=line.product_class_code or "",
        product_class_name=line.product_class_name or "",
        product_id=line.product_id,
        product_code=line.product_code,
        product_name=line.product_name,
        catalog_code_snapshot=line.catalog_code_snapshot,
        catalog_name_snapshot=line.catalog_name_snapshot,
        quantity=_quantize_quantity(line.quantity),
        unit_price=_quantize_money(line.unit_price),
        line_total_amount=_quantize_money(line.line_total_amount),
        already_returned_quantity=normalized_returned_quantity,
        remaining_returnable_quantity=remaining_returnable_quantity,
        requires_exact_product_selection=requires_exact_product_selection,
    )


def _get_returned_quantity_by_sale_line_ids(
    session: Session,
    *,
    sale_line_ids: Sequence[uuid.UUID],
) -> dict[uuid.UUID, Decimal]:
    if not sale_line_ids:
        return {}

    rows = session.execute(
        select(
            SaleReturnLine.original_sale_line_id,
            func.coalesce(func.sum(SaleReturnLine.returned_quantity), ZERO_QUANTITY).label(
                "returned_quantity"
            ),
        )
        .where(SaleReturnLine.original_sale_line_id.in_(tuple(sale_line_ids)))
        .group_by(SaleReturnLine.original_sale_line_id)
    ).mappings()
    return {
        row["original_sale_line_id"]: _quantize_optional_quantity(row["returned_quantity"])
        for row in rows
    }


def _get_return_summary_by_sale_ids(
    session: Session,
    *,
    sale_ids: Sequence[uuid.UUID],
) -> dict[uuid.UUID, ReturnSaleSummary]:
    if not sale_ids:
        return {}

    summary_by_sale_id = {
        sale_id: ReturnSaleSummary(
            return_count=0,
            returned_amount=ZERO_MONEY,
            returned_quantity=ZERO_QUANTITY,
        )
        for sale_id in sale_ids
    }

    return_rows = session.execute(
        select(
            SaleReturn.original_sale_id,
            func.count(SaleReturn.id).label("return_count"),
            func.coalesce(func.sum(SaleReturn.total_refund_amount), ZERO_MONEY).label(
                "returned_amount"
            ),
        )
        .where(SaleReturn.original_sale_id.in_(tuple(sale_ids)))
        .group_by(SaleReturn.original_sale_id)
    ).mappings()
    for row in return_rows:
        current_summary = summary_by_sale_id[row["original_sale_id"]]
        summary_by_sale_id[row["original_sale_id"]] = ReturnSaleSummary(
            return_count=int(row["return_count"]),
            returned_amount=_quantize_money(row["returned_amount"]),
            returned_quantity=current_summary.returned_quantity,
        )

    quantity_rows = session.execute(
        select(
            SaleLine.sale_id.label("sale_id"),
            func.coalesce(func.sum(SaleReturnLine.returned_quantity), ZERO_QUANTITY).label(
                "returned_quantity"
            ),
        )
        .select_from(SaleReturnLine)
        .join(SaleLine, SaleLine.id == SaleReturnLine.original_sale_line_id)
        .where(SaleLine.sale_id.in_(tuple(sale_ids)))
        .group_by(SaleLine.sale_id)
    ).mappings()
    for row in quantity_rows:
        current_summary = summary_by_sale_id[row["sale_id"]]
        summary_by_sale_id[row["sale_id"]] = ReturnSaleSummary(
            return_count=current_summary.return_count,
            returned_amount=current_summary.returned_amount,
            returned_quantity=_quantize_optional_quantity(row["returned_quantity"]),
        )

    return summary_by_sale_id


def _resolve_exact_return_product(
    session: Session,
    *,
    sale_line: SaleLineView,
    exact_product_id: uuid.UUID | None,
    disposition_code: str,
) -> PreparedExactProduct:
    if sale_line.capture_mode == CATALOG_CAPTURE_MODE_PRODUCT_DIRECT:
        if sale_line.product_id is None:
            raise SaleReturnValidationError(
                "La linea original no tiene producto exacto disponible para devolver."
            )
        if exact_product_id is not None and exact_product_id != sale_line.product_id:
            raise SaleReturnValidationError(
                "La devolucion de un producto directo debe usar el mismo producto "
                "exacto de la venta original."
            )
        return _load_product_snapshot(session, product_id=sale_line.product_id)

    if sale_line.capture_mode != CATALOG_CAPTURE_MODE_CLASS_CAPTURE:
        raise SaleReturnValidationError("La linea original tiene un modo de captura no soportado.")

    if exact_product_id is None:
        disposition_label = {
            RETURN_DISPOSITION_RESTOCK_COUNTER: "regresa a mostrador",
            RETURN_DISPOSITION_RESTOCK_BACKROOM: "regresa a resguardo",
            RETURN_DISPOSITION_SEND_TO_WASTE: "se manda a merma",
        }[disposition_code]
        raise SaleReturnValidationError(
            "Las devoluciones de ventas por clase requieren seleccionar el producto exacto "
            f"cuando la mercancia {disposition_label}."
        )
    if sale_line.product_class_id is None:
        raise SaleReturnValidationError(
            "La linea por clase no tiene una clase valida para seleccionar producto exacto."
        )

    exact_product = _load_product_snapshot(session, product_id=exact_product_id)
    if exact_product.product_class_id != sale_line.product_class_id:
        raise SaleReturnValidationError(
            "El producto exacto seleccionado no pertenece a la clase original de la venta."
        )
    return exact_product


def _load_product_snapshot(session: Session, *, product_id: uuid.UUID) -> PreparedExactProduct:
    record = session.execute(
        select(
            Product.id,
            Product.code,
            Product.name,
            ProductClass.id.label("product_class_id"),
            ProductClass.code.label("product_class_code"),
            ProductClass.name.label("product_class_name"),
        )
        .select_from(Product)
        .join(ProductClass, ProductClass.id == Product.product_class_id)
        .where(Product.id == product_id)
    ).mappings().one_or_none()
    if record is None:
        raise ProductNotFoundError("Product was not found.")

    return PreparedExactProduct(
        product_id=record["id"],
        product_code=record["code"],
        product_name=record["name"],
        product_class_id=record["product_class_id"],
        product_class_code=record["product_class_code"],
        product_class_name=record["product_class_name"],
    )


def _require_open_cash_session(
    session: Session,
    *,
    cash_session_query: CashSessionQueryService,
    current_user: AuthenticatedUser,
    workstation_code: str,
    context: WorkstationContext,
) -> CashSessionView:
    current_open_cash_session = cash_session_query.get_open_session_for_workstation_code(
        session,
        workstation_code=workstation_code,
    )
    if current_open_cash_session is None:
        raise SaleReturnConflictError(
            "Necesitas una caja abierta en esta estacion para registrar devoluciones."
        )
    if current_open_cash_session.user_id != current_user.id:
        raise SaleReturnConflictError(
            "La caja abierta de esta estacion pertenece a otro cajero."
        )
    if (
        current_open_cash_session.branch_id != context.branch_id
        or current_open_cash_session.workstation_id != context.workstation_id
    ):
        raise SaleReturnConflictError(
            "La caja abierta no coincide con el contexto actual de la estacion."
        )
    return current_open_cash_session


def _apply_scope_filters(
    statement: Select[tuple[object, ...]],
    *,
    normalized_scope: str,
    context: WorkstationContext,
    current_cash_session_id: uuid.UUID,
) -> Select[tuple[object, ...]]:
    if normalized_scope == RETURN_SCOPE_CURRENT_SHIFT:
        return statement.where(Sale.cash_session_id == current_cash_session_id)

    if normalized_scope == RETURN_SCOPE_TODAY:
        local_now = datetime.now(tz=UTC).astimezone(ZoneInfo(context.branch_timezone))
        local_start = datetime.combine(
            local_now.date(),
            time.min,
            tzinfo=ZoneInfo(context.branch_timezone),
        )
        local_end = local_start + timedelta(days=1)
        return statement.where(
            Sale.confirmed_at >= local_start.astimezone(UTC),
            Sale.confirmed_at < local_end.astimezone(UTC),
        )

    recent_cutoff = datetime.now(tz=UTC) - timedelta(days=30)
    return statement.where(Sale.confirmed_at >= recent_cutoff)


def _apply_date_range_filters(
    statement: Select[tuple[object, ...]],
    *,
    branch_timezone: str,
    date_from: date | None,
    date_to: date | None,
) -> Select[tuple[object, ...]]:
    if date_from is None and date_to is None:
        return statement

    timezone = ZoneInfo(branch_timezone)
    if date_from is not None:
        local_start = datetime.combine(date_from, time.min, tzinfo=timezone)
        statement = statement.where(Sale.confirmed_at >= local_start.astimezone(UTC))
    if date_to is not None:
        local_end = datetime.combine(date_to + timedelta(days=1), time.min, tzinfo=timezone)
        statement = statement.where(Sale.confirmed_at < local_end.astimezone(UTC))

    return statement


def _apply_return_history_scope_filters(
    statement: Select[tuple[object, ...]],
    *,
    normalized_scope: str,
    context: WorkstationContext,
    current_cash_session_id: uuid.UUID,
) -> Select[tuple[object, ...]]:
    if normalized_scope == RETURN_SCOPE_CURRENT_SHIFT:
        return statement.where(SaleReturn.cash_session_id == current_cash_session_id)

    if normalized_scope == RETURN_SCOPE_TODAY:
        local_now = datetime.now(tz=UTC).astimezone(ZoneInfo(context.branch_timezone))
        local_start = datetime.combine(
            local_now.date(),
            time.min,
            tzinfo=ZoneInfo(context.branch_timezone),
        )
        local_end = local_start + timedelta(days=1)
        return statement.where(
            SaleReturn.created_at_utc >= local_start.astimezone(UTC),
            SaleReturn.created_at_utc < local_end.astimezone(UTC),
        )

    recent_cutoff = datetime.now(tz=UTC) - timedelta(days=30)
    return statement.where(SaleReturn.created_at_utc >= recent_cutoff)


def _apply_return_history_date_range_filters(
    statement: Select[tuple[object, ...]],
    *,
    branch_timezone: str,
    date_from: date | None,
    date_to: date | None,
) -> Select[tuple[object, ...]]:
    if date_from is None and date_to is None:
        return statement

    timezone = ZoneInfo(branch_timezone)
    if date_from is not None:
        local_start = datetime.combine(date_from, time.min, tzinfo=timezone)
        statement = statement.where(SaleReturn.created_at_utc >= local_start.astimezone(UTC))
    if date_to is not None:
        local_end = datetime.combine(date_to + timedelta(days=1), time.min, tzinfo=timezone)
        statement = statement.where(SaleReturn.created_at_utc < local_end.astimezone(UTC))

    return statement


def _apply_search_filters(
    statement: Select[tuple[object, ...]],
    normalized_query: str | None,
) -> Select[tuple[object, ...]]:
    if normalized_query is None:
        return statement

    sale_id_prefix = normalized_query.removeprefix("tck-")
    matching_line = exists(
        select(SaleLine.id).where(
            SaleLine.sale_id == Sale.id,
            func.lower(SaleLine.catalog_name_snapshot).contains(normalized_query),
        )
    )
    return statement.where(
        or_(
            func.lower(cast(Sale.id, String)).like(f"{sale_id_prefix}%"),
            func.lower(cast(Sale.id, String)).contains(normalized_query),
            func.lower(User.full_name).contains(normalized_query),
            matching_line,
        )
    )


def _build_sale_folio(sale_id: uuid.UUID) -> str:
    return f"TCK-{str(sale_id).split('-', maxsplit=1)[0].upper()}"


def _build_return_folio(return_id: uuid.UUID) -> str:
    return f"DEV-{str(return_id).split('-', maxsplit=1)[0].upper()}"


def _get_branch_brand_key(branch_code: str) -> str:
    return BRANCH_BRAND_MAPPING.get(branch_code, "EL_MEJOR_PAN")


def _validate_scope(value: str | None) -> str:
    normalized = _normalize_optional_string(value)
    if normalized is None:
        return RETURN_SCOPE_CURRENT_SHIFT
    scope_code = normalized.upper()
    if scope_code not in VALID_RETURN_SCOPES:
        raise SaleReturnValidationError("El alcance solicitado no es valido para devoluciones.")
    return scope_code


def _validate_date_range(
    date_from: date | None,
    date_to: date | None,
) -> tuple[date | None, date | None]:
    if date_from is not None and date_to is not None and date_from > date_to:
        raise SaleReturnValidationError(
            "La fecha inicial no puede ser posterior a la fecha final."
        )
    return date_from, date_to


def _get_return_reason_definitions() -> tuple[ReturnReasonDefinition, ...]:
    return tuple(
        ReturnReasonDefinition(
            code=reason_code,
            label=label,
            display_order=display_order,
        )
        for reason_code, label, display_order in RETURN_REASON_DEFINITIONS
    )


def _validate_return_reason(value: str) -> ReturnReasonDefinition:
    reason_code = value.strip().upper()
    if reason_code not in VALID_RETURN_REASON_CODES:
        raise SaleReturnValidationError("Selecciona un motivo de devolucion valido.")

    for reason in _get_return_reason_definitions():
        if reason.code == reason_code:
            return reason

    raise SaleReturnValidationError("Selecciona un motivo de devolucion valido.")


def _validate_refund_method_code(value: str) -> str:
    refund_method_code = value.strip().upper()
    if refund_method_code not in VALID_RETURN_REFUND_METHOD_CODES:
        if refund_method_code == "CARD":
            raise SaleReturnValidationError(
                "Reverso de tarjeta pendiente de integracion. Usa efectivo para esta devolucion."
            )
        if refund_method_code == "MIXED":
            raise SaleReturnValidationError(
                "El reembolso mixto esta pendiente de integracion. "
                "Usa efectivo para esta devolucion."
            )
        raise SaleReturnValidationError("Selecciona un metodo de reembolso valido.")
    return refund_method_code


def _validate_disposition_code(value: str) -> str:
    disposition_code = value.strip().upper()
    if disposition_code not in VALID_RETURN_DISPOSITION_CODES:
        raise SaleReturnValidationError(
            "Selecciona un destino fisico valido para la mercancia devuelta."
        )
    return disposition_code


def _normalize_query(value: str | None) -> str | None:
    normalized = _normalize_optional_string(value)
    return normalized.casefold() if normalized else None


def _normalize_optional_string(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def _get_sale_return_status(
    *,
    total_quantity: Decimal,
    returned_quantity: Decimal,
) -> str:
    if returned_quantity <= ZERO_QUANTITY:
        return RETURN_STATUS_NOT_RETURNED
    if returned_quantity >= total_quantity:
        return RETURN_STATUS_FULLY_RETURNED
    return RETURN_STATUS_PARTIALLY_RETURNED


def _get_sale_age_in_days(*, confirmed_at: datetime, branch_timezone: str) -> int:
    local_now = datetime.now(tz=UTC).astimezone(ZoneInfo(branch_timezone)).date()
    local_confirmed_at = confirmed_at.astimezone(ZoneInfo(branch_timezone)).date()
    return (local_now - local_confirmed_at).days


def _quantize_money(value: Decimal | int | None) -> Decimal:
    raw_value = ZERO_MONEY if value is None else Decimal(value)
    return raw_value.quantize(MONEY_QUANTIZER, rounding=ROUND_HALF_UP)


def _quantize_quantity(value: Decimal | int) -> Decimal:
    quantized = Decimal(value).quantize(QUANTITY_QUANTIZER, rounding=ROUND_HALF_UP)
    if quantized <= ZERO_QUANTITY:
        raise SaleReturnValidationError("La cantidad devuelta debe ser mayor a cero.")
    return quantized


def _quantize_optional_quantity(value: Decimal | int | None) -> Decimal:
    raw_value = ZERO_QUANTITY if value is None else Decimal(value)
    quantized = raw_value.quantize(QUANTITY_QUANTIZER, rounding=ROUND_HALF_UP)
    return quantized if quantized >= ZERO_QUANTITY else ZERO_QUANTITY
