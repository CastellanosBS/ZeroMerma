from __future__ import annotations

import uuid
from collections import defaultdict
from datetime import UTC, datetime
from decimal import Decimal
from typing import cast as type_cast

from sqlalchemy import Select, String, and_, cast, exists, func, or_, select
from sqlalchemy.engine import RowMapping
from sqlalchemy.orm import Session

from zeromerma_api.modules.branches.infrastructure.models import Branch, Workstation
from zeromerma_api.modules.cash.domain.constants import (
    CASH_SESSION_STATUS_CLOSED,
    CASH_SESSION_STATUS_OPEN,
)
from zeromerma_api.modules.cash.infrastructure.models import CashSession
from zeromerma_api.modules.cash_close.application.admin_schemas import (
    AdminCashCutAvailableActionsView,
    AdminCashCutBackendContractView,
    AdminCashCutCorrectionAdjustmentItemView,
    AdminCashCutDenominationCountView,
    AdminCashCutDetailView,
    AdminCashCutExpectedVsCountedView,
    AdminCashCutFilterOptionsView,
    AdminCashCutFilterOptionView,
    AdminCashCutListItemView,
    AdminCashCutMetricsView,
    AdminCashCutOperationalPaymentItemView,
    AdminCashCutOverviewView,
    AdminCashCutPaymentBreakdownView,
    AdminCashCutReconciliationStatusView,
    AdminCashCutRefundItemView,
    AdminCashCutRelatedDocumentView,
    AdminCashCutsListResponse,
    AdminCashCutTicketItemView,
    AdminCashCutTimelineItemView,
)
from zeromerma_api.modules.cash_close.domain.constants import (
    CASH_CLOSE_PAYMENT_METHOD_CARD,
    CASH_CLOSE_PAYMENT_METHOD_CASH,
    CASH_CLOSE_PAYMENT_METHOD_MIXED,
    CASH_CLOSE_RECONCILIATION_STATUS_NOT_EVALUATED,
    CASH_CLOSE_STATUS_COMMITTED,
)
from zeromerma_api.modules.cash_close.domain.exceptions import (
    CashCloseNotFoundError,
    CashCloseValidationError,
)
from zeromerma_api.modules.cash_close.infrastructure.models import (
    CashSessionClose,
    CashSessionCloseDiscrepancyResolution,
    CashSessionCloseIssue,
    CashSessionClosePaymentMethodCount,
)
from zeromerma_api.modules.discounts.infrastructure.models import (
    OperationalDiscount,
    OperationalDiscountCategory,
)
from zeromerma_api.modules.identity.infrastructure.models import User
from zeromerma_api.modules.operations.infrastructure.models import OperationDocument
from zeromerma_api.modules.payments.infrastructure.models import (
    OperationalPayment,
    OperationalPaymentCategory,
)
from zeromerma_api.modules.returns.infrastructure.models import SaleReturn
from zeromerma_api.modules.sales.domain.constants import (
    CASH_MOVEMENT_DIRECTION_IN,
    CASH_MOVEMENT_DIRECTION_OUT,
    CASH_MOVEMENT_TYPE_OPERATIONAL_DISCOUNT,
    CASH_MOVEMENT_TYPE_OPERATIONAL_PAYMENT,
    CASH_MOVEMENT_TYPE_SALE_COLLECTION,
    SALE_PAYMENT_METHOD_CARD,
    SALE_PAYMENT_METHOD_CASH,
    SALE_PAYMENT_METHOD_MIXED,
    VALID_SALE_PAYMENT_METHOD_CODES,
)
from zeromerma_api.modules.sales.infrastructure.models import (
    CashMovement,
    Sale,
    SalePayment,
)
from zeromerma_api.modules.tickets.application.admin_services import build_ticket_folio

ADMIN_CASH_CUTS_PAGE_SIZE_MAX = 100
CASH_CUT_STATUS_OPEN = "OPEN"
CASH_CUT_STATUS_PENDING_CLOSE = "PENDING_CLOSE"
CASH_CUT_STATUS_CLOSED = "CLOSED"
CASH_CUT_STATUS_CLOSED_WITH_DIFFERENCE = "CLOSED_WITH_DIFFERENCE"
DIFFERENCE_STATE_EXACT = "EXACT"
DIFFERENCE_STATE_OVER = "OVER"
DIFFERENCE_STATE_SHORT = "SHORT"
DIFFERENCE_STATE_UNRESOLVED = "UNRESOLVED"
DIFFERENCE_FILTER_WITH_DIFFERENCE = "WITH_DIFFERENCE"
DIFFERENCE_FILTER_WITHOUT_DIFFERENCE = "WITHOUT_DIFFERENCE"
CASH_MOVEMENT_TYPE_SALE_RETURN_REFUND = "SALE_RETURN_REFUND"
ZERO_MONEY = Decimal("0.00")
MONEY_QUANTIZER = Decimal("0.01")


class AdminCashCutService:
    def list_cash_cuts(
        self,
        session: Session,
        *,
        branch_id: uuid.UUID | None,
        cashier_id: uuid.UUID | None,
        date_from: datetime | None,
        date_to: datetime | None,
        difference_state: str | None,
        has_operational_payments: bool | None,
        has_refunds: bool | None,
        page: int,
        page_size: int,
        payment_method: str | None,
        search: str | None,
        status_filter: str | None,
        workstation_id: uuid.UUID | None,
    ) -> AdminCashCutsListResponse:
        resolved_page_size = min(page_size, ADMIN_CASH_CUTS_PAGE_SIZE_MAX)
        conditions = self._build_conditions(
            branch_id=branch_id,
            cashier_id=cashier_id,
            date_from=date_from,
            date_to=date_to,
            difference_state=difference_state,
            has_operational_payments=has_operational_payments,
            has_refunds=has_refunds,
            payment_method=payment_method,
            search=search,
            status_filter=status_filter,
            workstation_id=workstation_id,
        )
        cash_session_ids_statement = self._build_cash_session_ids_statement(conditions)

        total = int(
            session.execute(
                select(func.count()).select_from(cash_session_ids_statement.subquery())
            ).scalar_one()
        )
        rows = (
            session.execute(
                self._base_list_statement()
                .where(CashSession.id.in_(cash_session_ids_statement))
                .order_by(
                    func.coalesce(
                        CashSessionClose.committed_at_utc,
                        CashSession.closed_at,
                        CashSession.opened_at,
                    ).desc(),
                    CashSession.id.desc(),
                )
                .limit(resolved_page_size)
                .offset((page - 1) * resolved_page_size)
            )
            .mappings()
            .all()
        )

        cash_session_ids = [type_cast(uuid.UUID, row["cash_session_id"]) for row in rows]
        close_ids = [
            type_cast(uuid.UUID, row["close_id"]) for row in rows if row["close_id"] is not None
        ]

        current_expected_by_session_id = self._get_current_expected_cash_by_session_id(
            session,
            rows=rows,
        )
        payment_summary_by_session_id = self._get_payment_methods_summary_by_session_id(
            session,
            cash_session_ids=cash_session_ids,
        )
        sales_total_by_session_id = self._get_sales_total_by_session_id(
            session,
            cash_session_ids=cash_session_ids,
        )
        refund_flags = self._get_refund_flags(session, cash_session_ids=cash_session_ids)
        operational_payment_flags = self._get_operational_payment_flags(
            session,
            cash_session_ids=cash_session_ids,
        )
        warning_counts = self._get_warning_counts_by_close_id(session, close_ids=close_ids)

        return AdminCashCutsListResponse(
            backend_contract=_backend_contract(),
            filter_options=self._build_filter_options(session),
            is_backend_connected=True,
            items=[
                _to_list_item(
                    row=row,
                    current_expected_amount=current_expected_by_session_id.get(
                        type_cast(uuid.UUID, row["cash_session_id"]),
                        _money(type_cast(Decimal, row["opening_amount"])),
                    ),
                    has_operational_payments=type_cast(
                        uuid.UUID,
                        row["cash_session_id"],
                    )
                    in operational_payment_flags,
                    has_refunds=type_cast(uuid.UUID, row["cash_session_id"]) in refund_flags,
                    payment_methods_summary=payment_summary_by_session_id.get(
                        type_cast(uuid.UUID, row["cash_session_id"]),
                        "Sin movimientos",
                    ),
                    total_sales_amount=sales_total_by_session_id.get(
                        type_cast(uuid.UUID, row["cash_session_id"]),
                        ZERO_MONEY,
                    ),
                    warning_count=warning_counts.get(
                        type_cast(uuid.UUID, row["close_id"]) if row["close_id"] else None,
                        0,
                    ),
                )
                for row in rows
            ],
            metrics=self._build_metrics(
                session,
                cash_session_ids_statement=cash_session_ids_statement,
            ),
            page=page,
            page_size=resolved_page_size,
            total=total,
        )

    def get_cash_cut_detail(
        self,
        session: Session,
        *,
        cash_session_id: uuid.UUID,
    ) -> AdminCashCutDetailView:
        row = (
            session.execute(self._base_list_statement().where(CashSession.id == cash_session_id))
            .mappings()
            .one_or_none()
        )
        if row is None:
            raise CashCloseNotFoundError("Cash cut was not found.")

        close_id = type_cast(uuid.UUID | None, row["close_id"])
        current_financial_summary = self._get_financial_summary(
            session,
            cash_session_id=cash_session_id,
            opening_amount=type_cast(Decimal, row["opening_amount"]),
        )
        expected_cash_amount = (
            _money(type_cast(Decimal, row["expected_cash_amount"]))
            if row["expected_cash_amount"] is not None
            else current_financial_summary["expected_cash_amount"]
        )
        counted_cash_amount = (
            _money(type_cast(Decimal, row["counted_cash_amount"]))
            if row["counted_cash_amount"] is not None
            else None
        )
        difference_amount = (
            _money(type_cast(Decimal, row["difference_amount"]))
            if row["difference_amount"] is not None
            else None
        )

        movement_amounts = self._get_cash_movement_amounts(
            session,
            cash_session_id=cash_session_id,
        )
        included_tickets = self._get_included_tickets(
            session,
            cash_session_id=cash_session_id,
        )
        returns_refunds = self._get_returns_refunds(
            session,
            cash_session_id=cash_session_id,
        )
        operational_payments = self._get_operational_payments(
            session,
            cash_session_id=cash_session_id,
        )
        corrections_adjustments = self._get_corrections_adjustments(
            session,
            cash_session_id=cash_session_id,
            close_id=close_id,
        )

        warning_count = (
            self._get_warning_counts_by_close_id(session, close_ids=[close_id]).get(close_id, 0)
            if close_id is not None
            else 0
        )
        status = _resolve_status(row)
        folio = _build_cash_cut_folio(
            close_id=close_id,
            cash_session_id=cash_session_id,
            status=status,
        )

        return AdminCashCutDetailView(
            available_actions=AdminCashCutAvailableActionsView(
                can_export_report=False,
                can_print_report=False,
                can_remote_close=False,
                remote_close_note=(
                    "El cierre debe realizarse desde el POS."
                    if status in {CASH_CUT_STATUS_OPEN, CASH_CUT_STATUS_PENDING_CLOSE}
                    else None
                ),
            ),
            audit_timeline=self._build_timeline(
                row=row,
                cash_session_id=cash_session_id,
                included_tickets=included_tickets,
                operational_payments=operational_payments,
                returns_refunds=returns_refunds,
            ),
            backend_contract=_backend_contract(),
            corrections_adjustments=corrections_adjustments,
            denomination_count=AdminCashCutDenominationCountView(
                is_supported=False,
                lines=[],
                total_counted=counted_cash_amount,
                note="El POS aun no expone conteo por denominacion para Backoffice.",
            ),
            expected_vs_counted=AdminCashCutExpectedVsCountedView(
                opening_amount=_money(type_cast(Decimal, row["opening_amount"])),
                cash_sales_amount=movement_amounts["cash_sales_amount"],
                cash_refunds_amount=movement_amounts["cash_refunds_amount"],
                cash_operational_payments_amount=movement_amounts[
                    "cash_operational_payments_amount"
                ],
                cash_operational_discounts_amount=movement_amounts[
                    "cash_operational_discounts_amount"
                ],
                cash_adjustments_amount=movement_amounts["cash_adjustments_amount"],
                expected_cash_amount=expected_cash_amount,
                counted_cash_amount=counted_cash_amount,
                difference_amount=difference_amount,
                difference_state=_resolve_difference_state(difference_amount),
                is_counted_cash_available=counted_cash_amount is not None,
                note=(
                    "Este turno sigue abierto; el conteo declarado se captura al cierre POS."
                    if counted_cash_amount is None
                    else None
                ),
            ),
            included_tickets=included_tickets,
            operational_payments=operational_payments,
            overview=AdminCashCutOverviewView(
                id=cash_session_id,
                folio=folio,
                cash_session_id=cash_session_id,
                close_id=close_id,
                status=status,
                branch_id=type_cast(uuid.UUID, row["branch_id"]),
                branch_name=type_cast(str, row["branch_name"]),
                branch_code=type_cast(str, row["branch_code"]),
                workstation_id=type_cast(uuid.UUID, row["workstation_id"]),
                workstation_code=type_cast(str, row["workstation_code"]),
                workstation_name=type_cast(str, row["workstation_name"]),
                cashier_id=type_cast(uuid.UUID, row["cashier_id"]),
                cashier_name=type_cast(str, row["cashier_name"]),
                opened_at=type_cast(datetime, row["opened_at"]),
                closed_at=type_cast(datetime | None, row["closed_at"]),
                opening_amount=_money(type_cast(Decimal, row["opening_amount"])),
                closing_notes=type_cast(str | None, row["notes"]),
                total_duration_minutes=_duration_minutes(
                    opened_at=type_cast(datetime, row["opened_at"]),
                    closed_at=type_cast(datetime | None, row["closed_at"]),
                ),
                warning_state=_resolve_warning_state(
                    status=status,
                    difference_amount=difference_amount,
                    warning_count=warning_count,
                ),
            ),
            payment_breakdown=self._get_payment_breakdown(
                session,
                cash_session_id=cash_session_id,
                close_id=close_id,
                expected_cash_amount=expected_cash_amount,
            ),
            reconciliation_status=AdminCashCutReconciliationStatusView(
                status=type_cast(
                    str,
                    row["reconciliation_status"] or CASH_CLOSE_RECONCILIATION_STATUS_NOT_EVALUATED,
                ),
                note=(
                    "Las diferencias se resuelven en Conciliacion "
                    "o mediante correcciones auditadas."
                    if difference_amount and difference_amount != ZERO_MONEY
                    else None
                ),
            ),
            related_documents=self._build_related_documents(
                close_id=close_id,
                included_tickets=included_tickets,
                operational_payments=operational_payments,
                returns_refunds=returns_refunds,
                corrections_adjustments=corrections_adjustments,
            ),
            returns_refunds=returns_refunds,
        )

    def _base_list_statement(self):
        return (
            select(
                CashSession.id.label("cash_session_id"),
                CashSession.status.label("cash_session_status"),
                CashSession.opening_amount.label("opening_amount"),
                CashSession.opened_at.label("opened_at"),
                CashSession.closed_at.label("session_closed_at"),
                CashSession.branch_id.label("branch_id"),
                Branch.code.label("branch_code"),
                Branch.name.label("branch_name"),
                CashSession.workstation_id.label("workstation_id"),
                Workstation.code.label("workstation_code"),
                Workstation.name.label("workstation_name"),
                CashSession.user_id.label("cashier_id"),
                User.full_name.label("cashier_name"),
                CashSessionClose.id.label("close_id"),
                CashSessionClose.status.label("close_status"),
                CashSessionClose.expected_cash_amount.label("expected_cash_amount"),
                CashSessionClose.counted_cash_amount.label("counted_cash_amount"),
                CashSessionClose.cash_variance_amount.label("difference_amount"),
                CashSessionClose.reconciliation_status.label("reconciliation_status"),
                CashSessionClose.notes.label("notes"),
                CashSessionClose.committed_at_utc.label("closed_at"),
            )
            .select_from(CashSession)
            .join(Branch, Branch.id == CashSession.branch_id)
            .join(Workstation, Workstation.id == CashSession.workstation_id)
            .join(User, User.id == CashSession.user_id)
            .outerjoin(CashSessionClose, CashSessionClose.cash_session_id == CashSession.id)
        )

    def _build_cash_session_ids_statement(
        self, conditions: list[object]
    ) -> Select[tuple[uuid.UUID]]:
        statement = (
            select(CashSession.id)
            .select_from(CashSession)
            .join(Branch, Branch.id == CashSession.branch_id)
            .join(Workstation, Workstation.id == CashSession.workstation_id)
            .join(User, User.id == CashSession.user_id)
            .outerjoin(CashSessionClose, CashSessionClose.cash_session_id == CashSession.id)
        )
        if conditions:
            statement = statement.where(and_(*conditions))
        return statement

    def _build_conditions(
        self,
        *,
        branch_id: uuid.UUID | None,
        cashier_id: uuid.UUID | None,
        date_from: datetime | None,
        date_to: datetime | None,
        difference_state: str | None,
        has_operational_payments: bool | None,
        has_refunds: bool | None,
        payment_method: str | None,
        search: str | None,
        status_filter: str | None,
        workstation_id: uuid.UUID | None,
    ) -> list[object]:
        conditions: list[object] = []
        if branch_id is not None:
            conditions.append(CashSession.branch_id == branch_id)
        if workstation_id is not None:
            conditions.append(CashSession.workstation_id == workstation_id)
        if cashier_id is not None:
            conditions.append(CashSession.user_id == cashier_id)
        date_expression = func.coalesce(
            CashSessionClose.committed_at_utc,
            CashSession.closed_at,
            CashSession.opened_at,
        )
        if date_from is not None:
            conditions.append(date_expression >= _ensure_utc(date_from))
        if date_to is not None:
            conditions.append(date_expression <= _ensure_utc(date_to))

        normalized_status = _normalize_optional(status_filter)
        if normalized_status:
            if normalized_status == CASH_CUT_STATUS_OPEN:
                conditions.append(CashSession.status == CASH_SESSION_STATUS_OPEN)
            elif normalized_status == CASH_CUT_STATUS_PENDING_CLOSE:
                conditions.append(
                    and_(
                        CashSession.status == CASH_SESSION_STATUS_CLOSED,
                        CashSessionClose.id.is_(None),
                    )
                )
            elif normalized_status == CASH_CUT_STATUS_CLOSED:
                conditions.append(
                    and_(
                        CashSessionClose.status == CASH_CLOSE_STATUS_COMMITTED,
                        CashSessionClose.cash_variance_amount == ZERO_MONEY,
                    )
                )
            elif normalized_status == CASH_CUT_STATUS_CLOSED_WITH_DIFFERENCE:
                conditions.append(
                    and_(
                        CashSessionClose.status == CASH_CLOSE_STATUS_COMMITTED,
                        CashSessionClose.cash_variance_amount != ZERO_MONEY,
                    )
                )
            elif normalized_status == CASH_CLOSE_STATUS_COMMITTED:
                conditions.append(CashSessionClose.status == CASH_CLOSE_STATUS_COMMITTED)
            else:
                raise CashCloseValidationError("Unsupported cash cut status filter.")

        normalized_difference = _normalize_optional(difference_state)
        if normalized_difference:
            if normalized_difference == DIFFERENCE_STATE_EXACT:
                conditions.append(CashSessionClose.cash_variance_amount == ZERO_MONEY)
            elif normalized_difference == DIFFERENCE_STATE_OVER:
                conditions.append(CashSessionClose.cash_variance_amount > ZERO_MONEY)
            elif normalized_difference == DIFFERENCE_STATE_SHORT:
                conditions.append(CashSessionClose.cash_variance_amount < ZERO_MONEY)
            elif normalized_difference == DIFFERENCE_FILTER_WITH_DIFFERENCE:
                conditions.append(CashSessionClose.cash_variance_amount != ZERO_MONEY)
            elif normalized_difference == DIFFERENCE_FILTER_WITHOUT_DIFFERENCE:
                conditions.append(
                    or_(
                        CashSessionClose.cash_variance_amount == ZERO_MONEY,
                        CashSessionClose.cash_variance_amount.is_(None),
                    )
                )
            elif normalized_difference == DIFFERENCE_STATE_UNRESOLVED:
                conditions.append(CashSessionClose.id.is_(None))
            else:
                raise CashCloseValidationError("Unsupported difference state filter.")

        normalized_payment_method = _normalize_optional(payment_method)
        if normalized_payment_method:
            if normalized_payment_method not in VALID_SALE_PAYMENT_METHOD_CODES:
                raise CashCloseValidationError("Unsupported payment method filter.")
            conditions.append(
                or_(
                    exists(
                        select(SalePayment.id)
                        .select_from(SalePayment)
                        .join(Sale, Sale.id == SalePayment.sale_id)
                        .where(
                            Sale.cash_session_id == CashSession.id,
                            SalePayment.payment_method_code == normalized_payment_method,
                        )
                    ),
                    exists(
                        select(CashSessionClosePaymentMethodCount.id).where(
                            CashSessionClosePaymentMethodCount.cash_session_close_id
                            == CashSessionClose.id,
                            CashSessionClosePaymentMethodCount.payment_method_code
                            == normalized_payment_method,
                        )
                    ),
                )
            )

        if has_refunds is not None:
            refund_exists = exists(
                select(SaleReturn.id).where(SaleReturn.cash_session_id == CashSession.id)
            )
            conditions.append(refund_exists if has_refunds else ~refund_exists)
        if has_operational_payments is not None:
            operational_payment_exists = exists(
                select(OperationalPayment.id).where(
                    OperationalPayment.active_cash_session_id == CashSession.id
                )
            )
            conditions.append(
                operational_payment_exists
                if has_operational_payments
                else ~operational_payment_exists
            )

        normalized_search = _normalize_search(search)
        if normalized_search:
            id_search = (
                normalized_search.removeprefix("cc-").removeprefix("ses-").removeprefix("cash-")
            )
            conditions.append(
                or_(
                    func.lower(cast(CashSession.id, String)).contains(id_search),
                    func.lower(cast(CashSessionClose.id, String)).contains(id_search),
                    func.lower(Branch.name).contains(normalized_search),
                    func.lower(Branch.code).contains(normalized_search),
                    func.lower(Workstation.name).contains(normalized_search),
                    func.lower(Workstation.code).contains(normalized_search),
                    func.lower(User.full_name).contains(normalized_search),
                )
            )
        return conditions

    def _build_filter_options(self, session: Session) -> AdminCashCutFilterOptionsView:
        branches = (
            session.execute(select(Branch.id, Branch.name).order_by(Branch.name.asc()))
            .mappings()
            .all()
        )
        workstations = (
            session.execute(
                select(Workstation.id, Workstation.name, Workstation.code).order_by(
                    Workstation.name.asc()
                )
            )
            .mappings()
            .all()
        )
        cashiers = (
            session.execute(
                select(User.id, User.full_name)
                .where(exists(select(CashSession.id).where(CashSession.user_id == User.id)))
                .order_by(User.full_name.asc())
            )
            .mappings()
            .all()
        )
        return AdminCashCutFilterOptionsView(
            branches=[
                AdminCashCutFilterOptionView(id=str(row["id"]), label=type_cast(str, row["name"]))
                for row in branches
            ],
            cashiers=[
                AdminCashCutFilterOptionView(
                    id=str(row["id"]),
                    label=type_cast(str, row["full_name"]),
                )
                for row in cashiers
            ],
            difference_states=[
                AdminCashCutFilterOptionView(
                    id=DIFFERENCE_FILTER_WITH_DIFFERENCE, label="Con diferencia"
                ),
                AdminCashCutFilterOptionView(
                    id=DIFFERENCE_FILTER_WITHOUT_DIFFERENCE, label="Sin diferencia"
                ),
                AdminCashCutFilterOptionView(id=DIFFERENCE_STATE_OVER, label="Sobrante"),
                AdminCashCutFilterOptionView(id=DIFFERENCE_STATE_SHORT, label="Faltante"),
                AdminCashCutFilterOptionView(
                    id=DIFFERENCE_STATE_UNRESOLVED, label="Sin conteo cerrado"
                ),
            ],
            payment_methods=[
                AdminCashCutFilterOptionView(id=SALE_PAYMENT_METHOD_CASH, label="Efectivo"),
                AdminCashCutFilterOptionView(id=SALE_PAYMENT_METHOD_CARD, label="Tarjeta"),
                AdminCashCutFilterOptionView(id=SALE_PAYMENT_METHOD_MIXED, label="Mixto"),
            ],
            statuses=[
                AdminCashCutFilterOptionView(id=CASH_CUT_STATUS_OPEN, label="Caja abierta"),
                AdminCashCutFilterOptionView(id=CASH_CUT_STATUS_CLOSED, label="Cerrado exacto"),
                AdminCashCutFilterOptionView(
                    id=CASH_CUT_STATUS_CLOSED_WITH_DIFFERENCE,
                    label="Cerrado con diferencia",
                ),
                AdminCashCutFilterOptionView(
                    id=CASH_CUT_STATUS_PENDING_CLOSE, label="Pendiente de cierre"
                ),
            ],
            workstations=[
                AdminCashCutFilterOptionView(
                    id=str(row["id"]),
                    label=f"{row['name']} ({row['code']})",
                )
                for row in workstations
            ],
        )

    def _build_metrics(
        self,
        session: Session,
        *,
        cash_session_ids_statement: Select[tuple[uuid.UUID]],
    ) -> AdminCashCutMetricsView:
        close_metrics = (
            session.execute(
                select(
                    func.count(CashSessionClose.id).label("closed_cuts_count"),
                    func.coalesce(
                        func.sum(CashSessionClose.expected_cash_amount), ZERO_MONEY
                    ).label("expected_cash_amount"),
                    func.coalesce(func.sum(CashSessionClose.counted_cash_amount), ZERO_MONEY).label(
                        "counted_cash_amount"
                    ),
                    func.coalesce(
                        func.sum(CashSessionClose.cash_variance_amount), ZERO_MONEY
                    ).label("net_difference_amount"),
                    func.count()
                    .filter(CashSessionClose.cash_variance_amount != ZERO_MONEY)
                    .label("cuts_with_difference_count"),
                ).where(
                    CashSessionClose.cash_session_id.in_(cash_session_ids_statement),
                    CashSessionClose.status == CASH_CLOSE_STATUS_COMMITTED,
                )
            )
            .mappings()
            .one()
        )
        sales_amount = session.execute(
            select(func.coalesce(func.sum(Sale.total_amount), ZERO_MONEY)).where(
                Sale.cash_session_id.in_(cash_session_ids_statement)
            )
        ).scalar_one()
        pending_close_count = int(
            session.execute(
                select(func.count(CashSession.id)).where(
                    CashSession.id.in_(cash_session_ids_statement),
                    CashSession.status == CASH_SESSION_STATUS_OPEN,
                )
            ).scalar_one()
        )
        operational_payments_amount = session.execute(
            select(func.coalesce(func.sum(OperationalPayment.cash_amount), ZERO_MONEY)).where(
                OperationalPayment.active_cash_session_id.in_(cash_session_ids_statement)
            )
        ).scalar_one()
        return AdminCashCutMetricsView(
            closed_cuts_count=int(type_cast(int, close_metrics["closed_cuts_count"])),
            counted_cash_amount=_money(type_cast(Decimal, close_metrics["counted_cash_amount"])),
            cuts_with_difference_count=int(
                type_cast(int, close_metrics["cuts_with_difference_count"])
            ),
            expected_cash_amount=_money(type_cast(Decimal, close_metrics["expected_cash_amount"])),
            net_difference_amount=_money(
                type_cast(Decimal, close_metrics["net_difference_amount"])
            ),
            net_sales_amount=_money(type_cast(Decimal, sales_amount)),
            operational_payments_amount=_money(type_cast(Decimal, operational_payments_amount)),
            pending_close_count=pending_close_count,
        )

    def _get_financial_summary(
        self,
        session: Session,
        *,
        cash_session_id: uuid.UUID,
        opening_amount: Decimal,
    ) -> dict[str, Decimal]:
        rows = (
            session.execute(
                select(
                    CashMovement.direction,
                    func.coalesce(func.sum(CashMovement.amount), ZERO_MONEY).label("amount"),
                )
                .where(CashMovement.cash_session_id == cash_session_id)
                .group_by(CashMovement.direction)
            )
            .mappings()
            .all()
        )
        total_cash_in = ZERO_MONEY
        total_cash_out = ZERO_MONEY
        for row in rows:
            amount = _money(type_cast(Decimal, row["amount"]))
            if row["direction"] == CASH_MOVEMENT_DIRECTION_IN:
                total_cash_in += amount
            elif row["direction"] == CASH_MOVEMENT_DIRECTION_OUT:
                total_cash_out += amount
        return {
            "expected_cash_amount": _money(opening_amount + total_cash_in - total_cash_out),
            "total_cash_in": _money(total_cash_in),
            "total_cash_out": _money(total_cash_out),
        }

    def _get_current_expected_cash_by_session_id(
        self,
        session: Session,
        *,
        rows: list[RowMapping],
    ) -> dict[uuid.UUID, Decimal]:
        result: dict[uuid.UUID, Decimal] = {}
        for row in rows:
            cash_session_id = type_cast(uuid.UUID, row["cash_session_id"])
            if row["expected_cash_amount"] is not None:
                result[cash_session_id] = _money(type_cast(Decimal, row["expected_cash_amount"]))
                continue
            result[cash_session_id] = self._get_financial_summary(
                session,
                cash_session_id=cash_session_id,
                opening_amount=type_cast(Decimal, row["opening_amount"]),
            )["expected_cash_amount"]
        return result

    def _get_sales_total_by_session_id(
        self,
        session: Session,
        *,
        cash_session_ids: list[uuid.UUID],
    ) -> dict[uuid.UUID, Decimal]:
        if not cash_session_ids:
            return {}
        rows = (
            session.execute(
                select(
                    Sale.cash_session_id,
                    func.coalesce(func.sum(Sale.total_amount), ZERO_MONEY).label("total_amount"),
                )
                .where(Sale.cash_session_id.in_(cash_session_ids))
                .group_by(Sale.cash_session_id)
            )
            .mappings()
            .all()
        )
        return {
            type_cast(uuid.UUID, row["cash_session_id"]): _money(
                type_cast(Decimal, row["total_amount"])
            )
            for row in rows
        }

    def _get_payment_methods_summary_by_session_id(
        self,
        session: Session,
        *,
        cash_session_ids: list[uuid.UUID],
    ) -> dict[uuid.UUID, str]:
        if not cash_session_ids:
            return {}
        rows = (
            session.execute(
                select(Sale.cash_session_id, SalePayment.payment_method_code)
                .select_from(SalePayment)
                .join(Sale, Sale.id == SalePayment.sale_id)
                .where(Sale.cash_session_id.in_(cash_session_ids))
                .group_by(Sale.cash_session_id, SalePayment.payment_method_code)
                .order_by(SalePayment.payment_method_code.asc())
            )
            .mappings()
            .all()
        )
        methods_by_session_id: dict[uuid.UUID, list[str]] = defaultdict(list)
        for row in rows:
            methods_by_session_id[type_cast(uuid.UUID, row["cash_session_id"])].append(
                type_cast(str, row["payment_method_code"])
            )
        return {
            cash_session_id: _format_payment_methods(methods)
            for cash_session_id, methods in methods_by_session_id.items()
        }

    def _get_refund_flags(
        self,
        session: Session,
        *,
        cash_session_ids: list[uuid.UUID],
    ) -> set[uuid.UUID]:
        if not cash_session_ids:
            return set()
        return set(
            session.execute(
                select(SaleReturn.cash_session_id)
                .where(SaleReturn.cash_session_id.in_(cash_session_ids))
                .group_by(SaleReturn.cash_session_id)
            ).scalars()
        )

    def _get_operational_payment_flags(
        self,
        session: Session,
        *,
        cash_session_ids: list[uuid.UUID],
    ) -> set[uuid.UUID]:
        if not cash_session_ids:
            return set()
        return set(
            session.execute(
                select(OperationalPayment.active_cash_session_id)
                .where(OperationalPayment.active_cash_session_id.in_(cash_session_ids))
                .group_by(OperationalPayment.active_cash_session_id)
            ).scalars()
        )

    def _get_warning_counts_by_close_id(
        self,
        session: Session,
        *,
        close_ids: list[uuid.UUID | None],
    ) -> dict[uuid.UUID | None, int]:
        resolved_ids = [close_id for close_id in close_ids if close_id is not None]
        if not resolved_ids:
            return {}
        rows = (
            session.execute(
                select(
                    CashSessionCloseIssue.cash_session_close_id,
                    func.count(CashSessionCloseIssue.id).label("warning_count"),
                )
                .where(CashSessionCloseIssue.cash_session_close_id.in_(resolved_ids))
                .group_by(CashSessionCloseIssue.cash_session_close_id)
            )
            .mappings()
            .all()
        )
        return {
            type_cast(uuid.UUID, row["cash_session_close_id"]): int(
                type_cast(int, row["warning_count"])
            )
            for row in rows
        }

    def _get_cash_movement_amounts(
        self,
        session: Session,
        *,
        cash_session_id: uuid.UUID,
    ) -> dict[str, Decimal]:
        rows = (
            session.execute(
                select(
                    CashMovement.movement_type,
                    CashMovement.direction,
                    func.coalesce(func.sum(CashMovement.amount), ZERO_MONEY).label("amount"),
                )
                .where(CashMovement.cash_session_id == cash_session_id)
                .group_by(CashMovement.movement_type, CashMovement.direction)
            )
            .mappings()
            .all()
        )
        result = {
            "cash_sales_amount": ZERO_MONEY,
            "cash_refunds_amount": ZERO_MONEY,
            "cash_operational_payments_amount": ZERO_MONEY,
            "cash_operational_discounts_amount": ZERO_MONEY,
            "cash_adjustments_amount": ZERO_MONEY,
        }
        known_types = {
            CASH_MOVEMENT_TYPE_SALE_COLLECTION,
            CASH_MOVEMENT_TYPE_SALE_RETURN_REFUND,
            CASH_MOVEMENT_TYPE_OPERATIONAL_PAYMENT,
            CASH_MOVEMENT_TYPE_OPERATIONAL_DISCOUNT,
        }
        for row in rows:
            amount = _money(type_cast(Decimal, row["amount"]))
            movement_type = type_cast(str, row["movement_type"])
            if movement_type == CASH_MOVEMENT_TYPE_SALE_COLLECTION:
                result["cash_sales_amount"] += amount
            elif movement_type == CASH_MOVEMENT_TYPE_SALE_RETURN_REFUND:
                result["cash_refunds_amount"] += amount
            elif movement_type == CASH_MOVEMENT_TYPE_OPERATIONAL_PAYMENT:
                result["cash_operational_payments_amount"] += amount
            elif movement_type == CASH_MOVEMENT_TYPE_OPERATIONAL_DISCOUNT:
                result["cash_operational_discounts_amount"] += amount
            elif movement_type not in known_types:
                if row["direction"] == CASH_MOVEMENT_DIRECTION_IN:
                    result["cash_adjustments_amount"] += amount
                else:
                    result["cash_adjustments_amount"] -= amount
        return {key: _money(value) for key, value in result.items()}

    def _get_payment_breakdown(
        self,
        session: Session,
        *,
        cash_session_id: uuid.UUID,
        close_id: uuid.UUID | None,
        expected_cash_amount: Decimal,
    ) -> list[AdminCashCutPaymentBreakdownView]:
        sales_rows = (
            session.execute(
                select(
                    SalePayment.payment_method_code,
                    SalePayment.currency_code,
                    func.coalesce(func.sum(SalePayment.applied_amount), ZERO_MONEY).label("amount"),
                )
                .select_from(SalePayment)
                .join(Sale, Sale.id == SalePayment.sale_id)
                .where(Sale.cash_session_id == cash_session_id)
                .group_by(SalePayment.payment_method_code, SalePayment.currency_code)
            )
            .mappings()
            .all()
        )
        refunds_rows = (
            session.execute(
                select(
                    SaleReturn.refund_method_code.label("payment_method_code"),
                    SaleReturn.currency_code,
                    func.coalesce(func.sum(SaleReturn.total_refund_amount), ZERO_MONEY).label(
                        "amount"
                    ),
                )
                .where(SaleReturn.cash_session_id == cash_session_id)
                .group_by(SaleReturn.refund_method_code, SaleReturn.currency_code)
            )
            .mappings()
            .all()
        )
        payment_rows = (
            session.execute(
                select(
                    OperationalPayment.payment_method_code,
                    OperationalPayment.currency_code,
                    func.coalesce(func.sum(OperationalPayment.total_amount), ZERO_MONEY).label(
                        "amount"
                    ),
                )
                .where(OperationalPayment.active_cash_session_id == cash_session_id)
                .group_by(OperationalPayment.payment_method_code, OperationalPayment.currency_code)
            )
            .mappings()
            .all()
        )
        discount_rows = (
            session.execute(
                select(
                    OperationalDiscount.payment_method_code,
                    OperationalDiscount.currency_code,
                    func.coalesce(func.sum(OperationalDiscount.total_amount), ZERO_MONEY).label(
                        "amount"
                    ),
                )
                .where(OperationalDiscount.active_cash_session_id == cash_session_id)
                .group_by(
                    OperationalDiscount.payment_method_code, OperationalDiscount.currency_code
                )
            )
            .mappings()
            .all()
        )
        close_rows_by_method: dict[str, RowMapping] = {}
        if close_id is not None:
            close_rows_by_method = {
                type_cast(str, row["payment_method_code"]): row
                for row in session.execute(
                    select(
                        CashSessionClosePaymentMethodCount.payment_method_code,
                        CashSessionClosePaymentMethodCount.currency_code,
                        CashSessionClosePaymentMethodCount.expected_amount,
                        CashSessionClosePaymentMethodCount.counted_amount,
                        CashSessionClosePaymentMethodCount.variance_amount,
                    ).where(CashSessionClosePaymentMethodCount.cash_session_close_id == close_id)
                )
                .mappings()
                .all()
            }

        sales_by_method = _amounts_by_method(sales_rows)
        refunds_by_method = _amounts_by_method(refunds_rows)
        payments_by_method = _amounts_by_method(payment_rows)
        discounts_by_method = _amounts_by_method(discount_rows)

        result: list[AdminCashCutPaymentBreakdownView] = []
        for method in [
            CASH_CLOSE_PAYMENT_METHOD_CASH,
            CASH_CLOSE_PAYMENT_METHOD_CARD,
            CASH_CLOSE_PAYMENT_METHOD_MIXED,
        ]:
            close_row = close_rows_by_method.get(method)
            counted_amount = (
                _money(type_cast(Decimal, close_row["counted_amount"]))
                if close_row is not None and close_row["counted_amount"] is not None
                else None
            )
            expected_amount = (
                _money(type_cast(Decimal, close_row["expected_amount"]))
                if close_row is not None and close_row["expected_amount"] is not None
                else (expected_cash_amount if method == CASH_CLOSE_PAYMENT_METHOD_CASH else None)
            )
            variance_amount = (
                _money(type_cast(Decimal, close_row["variance_amount"]))
                if close_row is not None and close_row["variance_amount"] is not None
                else None
            )
            sales_amount = sales_by_method.get(method, ZERO_MONEY)
            refund_amount = refunds_by_method.get(method, ZERO_MONEY)
            operational_payment_amount = payments_by_method.get(method, ZERO_MONEY)
            operational_discount_amount = discounts_by_method.get(method, ZERO_MONEY)
            result.append(
                AdminCashCutPaymentBreakdownView(
                    payment_method_code=method,
                    currency_code=(
                        type_cast(str, close_row["currency_code"])
                        if close_row is not None
                        else "MXN"
                    ),
                    sales_amount=sales_amount,
                    refund_amount=refund_amount,
                    operational_payment_amount=operational_payment_amount,
                    operational_discount_amount=operational_discount_amount,
                    expected_amount=expected_amount,
                    counted_amount=counted_amount,
                    variance_amount=variance_amount,
                    net_amount=_money(
                        sales_amount
                        - refund_amount
                        - operational_payment_amount
                        - operational_discount_amount
                    ),
                    is_counted_supported=close_id is not None,
                )
            )
        return result

    def _get_included_tickets(
        self,
        session: Session,
        *,
        cash_session_id: uuid.UUID,
    ) -> list[AdminCashCutTicketItemView]:
        rows = (
            session.execute(
                select(
                    Sale.id,
                    Sale.confirmed_at,
                    Sale.total_amount,
                    Sale.currency_code,
                    Sale.status,
                    User.full_name.label("cashier_name"),
                )
                .select_from(Sale)
                .join(User, User.id == Sale.operator_id)
                .where(Sale.cash_session_id == cash_session_id)
                .order_by(Sale.confirmed_at.desc(), Sale.id.desc())
            )
            .mappings()
            .all()
        )
        sale_ids = [type_cast(uuid.UUID, row["id"]) for row in rows]
        payment_summary = self._get_payment_summary_by_sale_id(session, sale_ids=sale_ids)
        return [
            AdminCashCutTicketItemView(
                ticket_id=type_cast(uuid.UUID, row["id"]),
                folio=build_ticket_folio(type_cast(uuid.UUID, row["id"])),
                occurred_at=type_cast(datetime, row["confirmed_at"]),
                total_amount=_money(type_cast(Decimal, row["total_amount"])),
                currency_code=type_cast(str, row["currency_code"]),
                payment_method_summary=_format_payment_methods(
                    payment_summary.get(type_cast(uuid.UUID, row["id"]), [])
                ),
                cashier_name=type_cast(str, row["cashier_name"]),
                status=type_cast(str, row["status"]),
                route_hint="/admin/ventas",
            )
            for row in rows
        ]

    def _get_payment_summary_by_sale_id(
        self,
        session: Session,
        *,
        sale_ids: list[uuid.UUID],
    ) -> dict[uuid.UUID, list[str]]:
        if not sale_ids:
            return {}
        rows = (
            session.execute(
                select(SalePayment.sale_id, SalePayment.payment_method_code)
                .where(SalePayment.sale_id.in_(sale_ids))
                .group_by(SalePayment.sale_id, SalePayment.payment_method_code)
                .order_by(SalePayment.payment_method_code.asc())
            )
            .mappings()
            .all()
        )
        result: dict[uuid.UUID, list[str]] = defaultdict(list)
        for row in rows:
            result[type_cast(uuid.UUID, row["sale_id"])].append(
                type_cast(str, row["payment_method_code"])
            )
        return result

    def _get_returns_refunds(
        self,
        session: Session,
        *,
        cash_session_id: uuid.UUID,
    ) -> list[AdminCashCutRefundItemView]:
        operator_alias = User
        rows = (
            session.execute(
                select(
                    SaleReturn.id,
                    SaleReturn.original_sale_id,
                    SaleReturn.status,
                    SaleReturn.reason_name,
                    SaleReturn.refund_method_code,
                    SaleReturn.total_refund_amount,
                    SaleReturn.created_at_utc,
                    operator_alias.full_name.label("operator_name"),
                )
                .select_from(SaleReturn)
                .join(operator_alias, operator_alias.id == SaleReturn.created_by_user_id)
                .where(SaleReturn.cash_session_id == cash_session_id)
                .order_by(SaleReturn.created_at_utc.desc(), SaleReturn.id.desc())
            )
            .mappings()
            .all()
        )
        return [
            AdminCashCutRefundItemView(
                id=type_cast(uuid.UUID, row["id"]),
                folio=_build_return_folio(type_cast(uuid.UUID, row["id"])),
                original_ticket_folio=build_ticket_folio(
                    type_cast(uuid.UUID, row["original_sale_id"])
                ),
                amount=_money(type_cast(Decimal, row["total_refund_amount"])),
                payment_method_code=type_cast(str, row["refund_method_code"]),
                occurred_at=type_cast(datetime, row["created_at_utc"]),
                operator_name=type_cast(str, row["operator_name"]),
                reason_name=type_cast(str, row["reason_name"]),
                status=type_cast(str, row["status"]),
                route_hint="/admin/devoluciones-correcciones",
            )
            for row in rows
        ]

    def _get_operational_payments(
        self,
        session: Session,
        *,
        cash_session_id: uuid.UUID,
    ) -> list[AdminCashCutOperationalPaymentItemView]:
        rows = (
            session.execute(
                select(
                    OperationalPayment.id,
                    OperationalPayment.category_code,
                    OperationalPaymentCategory.name.label("category_name"),
                    OperationalPayment.total_amount,
                    OperationalPayment.cash_amount,
                    OperationalPayment.payment_method_code,
                    OperationalPayment.created_at_utc,
                    OperationalPayment.notes,
                    User.full_name.label("operator_name"),
                )
                .select_from(OperationalPayment)
                .join(User, User.id == OperationalPayment.created_by_user_id)
                .outerjoin(
                    OperationalPaymentCategory,
                    OperationalPaymentCategory.code == OperationalPayment.category_code,
                )
                .where(OperationalPayment.active_cash_session_id == cash_session_id)
                .order_by(OperationalPayment.created_at_utc.desc(), OperationalPayment.id.desc())
            )
            .mappings()
            .all()
        )
        return [
            AdminCashCutOperationalPaymentItemView(
                id=type_cast(uuid.UUID, row["id"]),
                folio=_build_payment_folio(type_cast(uuid.UUID, row["id"])),
                category_code=type_cast(str | None, row["category_code"]),
                category_name=type_cast(str | None, row["category_name"]),
                amount=_money(type_cast(Decimal, row["total_amount"])),
                cash_amount=_money(type_cast(Decimal, row["cash_amount"])),
                payment_method_code=type_cast(str, row["payment_method_code"]),
                occurred_at=type_cast(datetime, row["created_at_utc"]),
                operator_name=type_cast(str, row["operator_name"]),
                notes=type_cast(str | None, row["notes"]),
                route_hint="/admin/pagos-operativos",
            )
            for row in rows
        ]

    def _get_corrections_adjustments(
        self,
        session: Session,
        *,
        cash_session_id: uuid.UUID,
        close_id: uuid.UUID | None,
    ) -> list[AdminCashCutCorrectionAdjustmentItemView]:
        result: list[AdminCashCutCorrectionAdjustmentItemView] = []
        discount_rows = (
            session.execute(
                select(
                    OperationalDiscount.id,
                    OperationalDiscount.category_code,
                    OperationalDiscountCategory.name.label("category_name"),
                    OperationalDiscount.total_amount,
                    OperationalDiscount.cash_amount,
                    OperationalDiscount.created_at_utc,
                    OperationalDiscount.notes,
                    User.full_name.label("operator_name"),
                )
                .select_from(OperationalDiscount)
                .join(User, User.id == OperationalDiscount.created_by_user_id)
                .outerjoin(
                    OperationalDiscountCategory,
                    OperationalDiscountCategory.code == OperationalDiscount.category_code,
                )
                .where(OperationalDiscount.active_cash_session_id == cash_session_id)
                .order_by(OperationalDiscount.created_at_utc.desc(), OperationalDiscount.id.desc())
            )
            .mappings()
            .all()
        )
        result.extend(
            AdminCashCutCorrectionAdjustmentItemView(
                id=type_cast(uuid.UUID, row["id"]),
                folio=_build_discount_folio(type_cast(uuid.UUID, row["id"])),
                document_type="operational_discount",
                amount=_money(type_cast(Decimal, row["cash_amount"])),
                occurred_at=type_cast(datetime, row["created_at_utc"]),
                operator_name=type_cast(str, row["operator_name"]),
                notes=type_cast(str | None, row["notes"]),
                route_hint="/admin/descuentos",
            )
            for row in discount_rows
        )
        if close_id is None:
            return result

        generated_document_ids = [
            type_cast(uuid.UUID, row["generated_document_id"])
            for row in session.execute(
                select(CashSessionCloseDiscrepancyResolution.generated_document_id).where(
                    CashSessionCloseDiscrepancyResolution.cash_session_close_id == close_id,
                    CashSessionCloseDiscrepancyResolution.generated_document_id.is_not(None),
                )
            )
            .mappings()
            .all()
        ]
        if not generated_document_ids:
            return result
        document_rows = (
            session.execute(
                select(
                    OperationDocument.id,
                    OperationDocument.document_type,
                    OperationDocument.status,
                    OperationDocument.committed_at_utc,
                    OperationDocument.notes,
                    User.full_name.label("operator_name"),
                )
                .select_from(OperationDocument)
                .join(User, User.id == OperationDocument.created_by_user_id)
                .where(OperationDocument.id.in_(generated_document_ids))
                .order_by(OperationDocument.committed_at_utc.desc(), OperationDocument.id.desc())
            )
            .mappings()
            .all()
        )
        result.extend(
            AdminCashCutCorrectionAdjustmentItemView(
                id=type_cast(uuid.UUID, row["id"]),
                folio=_build_operation_document_folio(type_cast(uuid.UUID, row["id"])),
                document_type=type_cast(str, row["document_type"]),
                amount=None,
                occurred_at=type_cast(datetime | None, row["committed_at_utc"]),
                operator_name=type_cast(str, row["operator_name"]),
                notes=type_cast(str | None, row["notes"]),
                route_hint="/admin/devoluciones-correcciones",
            )
            for row in document_rows
        )
        return result

    def _build_timeline(
        self,
        *,
        row: RowMapping,
        cash_session_id: uuid.UUID,
        included_tickets: list[AdminCashCutTicketItemView],
        operational_payments: list[AdminCashCutOperationalPaymentItemView],
        returns_refunds: list[AdminCashCutRefundItemView],
    ) -> list[AdminCashCutTimelineItemView]:
        items = [
            AdminCashCutTimelineItemView(
                event_code="CASH_SESSION_OPENED",
                label="Caja abierta",
                occurred_at=type_cast(datetime, row["opened_at"]),
                actor_name=type_cast(str, row["cashier_name"]),
                summary=f"Sesion {cash_session_id}",
            )
        ]
        if included_tickets:
            first_ticket = min(included_tickets, key=lambda item: item.occurred_at)
            last_ticket = max(included_tickets, key=lambda item: item.occurred_at)
            items.append(
                AdminCashCutTimelineItemView(
                    event_code="FIRST_TICKET",
                    label="Primera venta",
                    occurred_at=first_ticket.occurred_at,
                    actor_name=first_ticket.cashier_name,
                    summary=first_ticket.folio,
                )
            )
            if last_ticket.ticket_id != first_ticket.ticket_id:
                items.append(
                    AdminCashCutTimelineItemView(
                        event_code="LAST_TICKET",
                        label="Ultima venta",
                        occurred_at=last_ticket.occurred_at,
                        actor_name=last_ticket.cashier_name,
                        summary=last_ticket.folio,
                    )
                )
        for refund in returns_refunds[:3]:
            items.append(
                AdminCashCutTimelineItemView(
                    event_code="RETURN_REFUND",
                    label="Devolucion registrada",
                    occurred_at=refund.occurred_at,
                    actor_name=refund.operator_name,
                    summary=refund.folio,
                )
            )
        for payment in operational_payments[:3]:
            items.append(
                AdminCashCutTimelineItemView(
                    event_code="OPERATIONAL_PAYMENT",
                    label="Pago operativo",
                    occurred_at=payment.occurred_at,
                    actor_name=payment.operator_name,
                    summary=payment.folio,
                )
            )
        if row["closed_at"] is not None:
            items.append(
                AdminCashCutTimelineItemView(
                    event_code="CASH_SESSION_CLOSED",
                    label="Caja cerrada",
                    occurred_at=type_cast(datetime, row["closed_at"]),
                    actor_name=type_cast(str, row["cashier_name"]),
                    summary=(
                        "Cierre con diferencia"
                        if row["difference_amount"] and row["difference_amount"] != ZERO_MONEY
                        else "Cierre exacto"
                    ),
                )
            )
        return sorted(items, key=lambda item: item.occurred_at)

    def _build_related_documents(
        self,
        *,
        close_id: uuid.UUID | None,
        included_tickets: list[AdminCashCutTicketItemView],
        operational_payments: list[AdminCashCutOperationalPaymentItemView],
        returns_refunds: list[AdminCashCutRefundItemView],
        corrections_adjustments: list[AdminCashCutCorrectionAdjustmentItemView],
    ) -> list[AdminCashCutRelatedDocumentView]:
        result: list[AdminCashCutRelatedDocumentView] = []
        if close_id is not None:
            result.append(
                AdminCashCutRelatedDocumentView(
                    id=str(close_id),
                    document_type="cash_session_close",
                    folio=_build_close_folio(close_id),
                    status=CASH_CLOSE_STATUS_COMMITTED,
                    route_hint="/admin/cortes-caja",
                )
            )
        result.extend(
            AdminCashCutRelatedDocumentView(
                id=str(ticket.ticket_id),
                document_type="ticket",
                folio=ticket.folio,
                status=ticket.status,
                amount=ticket.total_amount,
                occurred_at=ticket.occurred_at,
                route_hint=ticket.route_hint,
            )
            for ticket in included_tickets[:5]
        )
        result.extend(
            AdminCashCutRelatedDocumentView(
                id=str(refund.id),
                document_type="return",
                folio=refund.folio,
                status=refund.status,
                amount=refund.amount,
                occurred_at=refund.occurred_at,
                route_hint=refund.route_hint,
            )
            for refund in returns_refunds
        )
        result.extend(
            AdminCashCutRelatedDocumentView(
                id=str(payment.id),
                document_type="operational_payment",
                folio=payment.folio,
                status="COMMITTED",
                amount=payment.amount,
                occurred_at=payment.occurred_at,
                route_hint=payment.route_hint,
            )
            for payment in operational_payments
        )
        result.extend(
            AdminCashCutRelatedDocumentView(
                id=str(adjustment.id),
                document_type=adjustment.document_type,
                folio=adjustment.folio,
                status="COMMITTED",
                amount=adjustment.amount,
                occurred_at=adjustment.occurred_at,
                route_hint=adjustment.route_hint,
            )
            for adjustment in corrections_adjustments
        )
        return result


def _backend_contract() -> AdminCashCutBackendContractView:
    return AdminCashCutBackendContractView(
        detail_endpoint="GET /v1/admin/cash-cuts/{cash_session_id}",
        export_endpoint=None,
        list_endpoint="GET /v1/admin/cash-cuts",
        print_endpoint=None,
    )


def _to_list_item(
    *,
    row: RowMapping,
    current_expected_amount: Decimal,
    has_operational_payments: bool,
    has_refunds: bool,
    payment_methods_summary: str,
    total_sales_amount: Decimal,
    warning_count: int,
) -> AdminCashCutListItemView:
    cash_session_id = type_cast(uuid.UUID, row["cash_session_id"])
    close_id = type_cast(uuid.UUID | None, row["close_id"])
    status = _resolve_status(row)
    difference_amount = (
        _money(type_cast(Decimal, row["difference_amount"]))
        if row["difference_amount"] is not None
        else None
    )
    return AdminCashCutListItemView(
        id=cash_session_id,
        folio=_build_cash_cut_folio(
            close_id=close_id,
            cash_session_id=cash_session_id,
            status=status,
        ),
        cash_session_id=cash_session_id,
        close_id=close_id,
        opened_at=type_cast(datetime, row["opened_at"]),
        closed_at=type_cast(datetime | None, row["closed_at"]),
        branch_id=type_cast(uuid.UUID, row["branch_id"]),
        branch_name=type_cast(str, row["branch_name"]),
        workstation_id=type_cast(uuid.UUID, row["workstation_id"]),
        workstation_code=type_cast(str, row["workstation_code"]),
        workstation_name=type_cast(str, row["workstation_name"]),
        cashier_id=type_cast(uuid.UUID, row["cashier_id"]),
        cashier_name=type_cast(str, row["cashier_name"]),
        opening_amount=_money(type_cast(Decimal, row["opening_amount"])),
        expected_cash_amount=current_expected_amount,
        counted_cash_amount=(
            _money(type_cast(Decimal, row["counted_cash_amount"]))
            if row["counted_cash_amount"] is not None
            else None
        ),
        difference_amount=difference_amount,
        total_sales_amount=total_sales_amount,
        payment_methods_summary=payment_methods_summary,
        status=status,
        difference_state=_resolve_difference_state(difference_amount),
        warning_state=_resolve_warning_state(
            status=status,
            difference_amount=difference_amount,
            warning_count=warning_count,
        ),
        warning_count=warning_count,
        has_refunds=has_refunds,
        has_operational_payments=has_operational_payments,
    )


def _resolve_status(row: RowMapping) -> str:
    if row["close_id"] is not None and row["close_status"] == CASH_CLOSE_STATUS_COMMITTED:
        difference = _money(type_cast(Decimal, row["difference_amount"] or ZERO_MONEY))
        if difference != ZERO_MONEY:
            return CASH_CUT_STATUS_CLOSED_WITH_DIFFERENCE
        return CASH_CUT_STATUS_CLOSED
    if row["cash_session_status"] == CASH_SESSION_STATUS_OPEN:
        return CASH_CUT_STATUS_OPEN
    return CASH_CUT_STATUS_PENDING_CLOSE


def _resolve_difference_state(value: Decimal | None) -> str:
    if value is None:
        return DIFFERENCE_STATE_UNRESOLVED
    if value > ZERO_MONEY:
        return DIFFERENCE_STATE_OVER
    if value < ZERO_MONEY:
        return DIFFERENCE_STATE_SHORT
    return DIFFERENCE_STATE_EXACT


def _resolve_warning_state(
    *,
    status: str,
    difference_amount: Decimal | None,
    warning_count: int,
) -> str:
    if status in {CASH_CUT_STATUS_OPEN, CASH_CUT_STATUS_PENDING_CLOSE}:
        return "pending_close"
    if difference_amount is not None and difference_amount != ZERO_MONEY:
        return "difference"
    if warning_count > 0:
        return "warning"
    return "ok"


def _amounts_by_method(rows: list[RowMapping]) -> dict[str, Decimal]:
    result: dict[str, Decimal] = {}
    for row in rows:
        result[type_cast(str, row["payment_method_code"])] = _money(
            type_cast(Decimal, row["amount"])
        )
    return result


def _format_payment_methods(methods: list[str]) -> str:
    if not methods:
        return "Sin pagos"
    unique_methods = sorted(set(methods))
    if len(unique_methods) > 1 or unique_methods[0] == SALE_PAYMENT_METHOD_MIXED:
        return "Mixto"
    return unique_methods[0]


def _build_cash_cut_folio(
    *,
    close_id: uuid.UUID | None,
    cash_session_id: uuid.UUID,
    status: str,
) -> str:
    if close_id is not None and status not in {CASH_CUT_STATUS_OPEN, CASH_CUT_STATUS_PENDING_CLOSE}:
        return _build_close_folio(close_id)
    return f"SES-{str(cash_session_id).split('-', maxsplit=1)[0].upper()}"


def _build_close_folio(close_id: uuid.UUID) -> str:
    return f"CC-{str(close_id).split('-', maxsplit=1)[0].upper()}"


def _build_payment_folio(payment_id: uuid.UUID) -> str:
    return f"PAG-{str(payment_id).split('-', maxsplit=1)[0].upper()}"


def _build_return_folio(return_id: uuid.UUID) -> str:
    return f"DEV-{str(return_id).split('-', maxsplit=1)[0].upper()}"


def _build_discount_folio(discount_id: uuid.UUID) -> str:
    return f"DES-{str(discount_id).split('-', maxsplit=1)[0].upper()}"


def _build_operation_document_folio(document_id: uuid.UUID) -> str:
    return f"OP-{str(document_id).split('-', maxsplit=1)[0].upper()}"


def _normalize_optional(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    if not stripped or stripped == "all":
        return None
    return stripped.upper()


def _normalize_search(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped.casefold() if stripped else None


def _ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _duration_minutes(*, opened_at: datetime, closed_at: datetime | None) -> int | None:
    if closed_at is None:
        return None
    return max(0, int((closed_at - opened_at).total_seconds() // 60))


def _money(value: Decimal) -> Decimal:
    return value.quantize(MONEY_QUANTIZER)
