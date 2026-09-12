from __future__ import annotations

import uuid
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import cast as type_cast

from sqlalchemy import select
from sqlalchemy.engine import RowMapping
from sqlalchemy.orm import Session

from zeromerma_api.modules.branches.infrastructure.models import Branch, Workstation
from zeromerma_api.modules.cash_close.application.cash_flow_schemas import (
    AdminCashFlowAvailableActionsView,
    AdminCashFlowBackendContractView,
    AdminCashFlowFilterOptionsView,
    AdminCashFlowFilterOptionView,
    AdminCashFlowFinancialClassificationView,
    AdminCashFlowListResponse,
    AdminCashFlowMovementDetailView,
    AdminCashFlowMovementListItemView,
    AdminCashFlowMovementOverviewView,
    AdminCashFlowReconciliationView,
    AdminCashFlowRelatedDocumentView,
    AdminCashFlowSourceContextView,
    AdminCashFlowSummaryView,
    AdminCashFlowTrendPointView,
)
from zeromerma_api.modules.cash_close.domain.constants import (
    CASH_CLOSE_PAYMENT_METHOD_CASH,
    FINANCIAL_RECONCILIATION_REASON_OTHER,
    FINANCIAL_RECONCILIATION_SOURCE_CASH_CUT,
    FINANCIAL_RECONCILIATION_STATUS_IN_REVIEW,
    FINANCIAL_RECONCILIATION_STATUS_PENDING,
    FINANCIAL_RECONCILIATION_STATUS_RECONCILED,
)
from zeromerma_api.modules.cash_close.domain.exceptions import (
    CashCloseNotFoundError,
)
from zeromerma_api.modules.cash_close.infrastructure.models import (
    CashSessionClose,
    FinancialReconciliation,
)
from zeromerma_api.modules.discounts.infrastructure.models import (
    OperationalDiscount,
    OperationalDiscountCategory,
)
from zeromerma_api.modules.identity.infrastructure.models import User
from zeromerma_api.modules.payments.infrastructure.models import (
    OperationalPayment,
    OperationalPaymentCategory,
)
from zeromerma_api.modules.returns.infrastructure.models import SaleReturn
from zeromerma_api.modules.sales.domain.constants import (
    SALE_PAYMENT_METHOD_CARD,
    SALE_PAYMENT_METHOD_CASH,
    SALE_PAYMENT_METHOD_MIXED,
)
from zeromerma_api.modules.sales.infrastructure.models import Sale, SalePayment
from zeromerma_api.modules.tickets.application.admin_services import build_ticket_folio

ADMIN_CASH_FLOW_PAGE_SIZE_MAX = 100
MOVEMENT_DIRECTION_ADJUSTMENT = "ADJUSTMENT"
MOVEMENT_DIRECTION_INFLOW = "INFLOW"
MOVEMENT_DIRECTION_OUTFLOW = "OUTFLOW"
RECONCILIATION_STATUS_NOT_REQUIRED = "NOT_REQUIRED"
SOURCE_TYPE_CASH_CUT_DIFFERENCE = "CASH_CUT_DIFFERENCE"
SOURCE_TYPE_OPERATIONAL_DISCOUNT = "OPERATIONAL_DISCOUNT"
SOURCE_TYPE_OPERATIONAL_PAYMENT = "OPERATIONAL_PAYMENT"
SOURCE_TYPE_RETURN_REFUND = "RETURN_REFUND"
SOURCE_TYPE_SALE = "SALE"
WARNING_STATE_CRITICAL = "critical"
WARNING_STATE_OK = "ok"
WARNING_STATE_PENDING_CUT = "pending_cut"
WARNING_STATE_RECONCILIATION = "reconciliation"
ZERO_MONEY = Decimal("0.00")
MONEY_QUANTIZER = Decimal("0.01")
HIGH_IMPACT_DIFFERENCE_THRESHOLD = Decimal("100.00")


@dataclass(frozen=True)
class CashFlowMovement:
    id: str
    occurred_at: datetime
    branch_id: uuid.UUID
    branch_name: str
    workstation_id: uuid.UUID
    workstation_name: str
    operator_id: uuid.UUID | None
    operator_name: str
    direction: str
    source_type: str
    source_document_id: uuid.UUID
    source_reference: str
    source_status: str
    category_code: str | None
    category_label: str | None
    payment_method: str
    amount: Decimal
    signed_effect: Decimal
    currency: str
    reconciliation_status: str
    reconciliation_id: uuid.UUID | None
    reconciliation_folio: str | None
    reconciliation_reason_code: str | None
    cash_session_id: uuid.UUID | None
    cash_cut_id: uuid.UUID | None
    cash_cut_folio: str | None
    original_ticket_id: uuid.UUID | None = None
    original_ticket_folio: str | None = None
    concept: str | None = None
    expected_cash_amount: Decimal | None = None
    counted_cash_amount: Decimal | None = None
    difference_amount: Decimal | None = None


class AdminCashFlowService:
    def list_movements(
        self,
        session: Session,
        *,
        amount_max: Decimal | None,
        amount_min: Decimal | None,
        branch_id: uuid.UUID | None,
        category: str | None,
        date_from: datetime | None,
        date_to: datetime | None,
        direction: str | None,
        operator_id: uuid.UUID | None,
        page: int,
        page_size: int,
        payment_method: str | None,
        reconciliation_state: str | None,
        search: str | None,
        source_type: str | None,
        workstation_id: uuid.UUID | None,
    ) -> AdminCashFlowListResponse:
        resolved_page = max(page, 1)
        resolved_page_size = min(max(page_size, 1), ADMIN_CASH_FLOW_PAGE_SIZE_MAX)
        movements = self._collect_movements(session)
        filtered = self._filter_movements(
            movements,
            amount_max=amount_max,
            amount_min=amount_min,
            branch_id=branch_id,
            category=category,
            date_from=date_from,
            date_to=date_to,
            direction=direction,
            operator_id=operator_id,
            payment_method=payment_method,
            reconciliation_state=reconciliation_state,
            search=search,
            source_type=source_type,
            workstation_id=workstation_id,
        )
        filtered.sort(key=lambda movement: (movement.occurred_at, movement.id), reverse=True)
        total = len(filtered)
        page_start = (resolved_page - 1) * resolved_page_size
        page_end = resolved_page * resolved_page_size
        page_items = filtered[page_start:page_end]
        return AdminCashFlowListResponse(
            backend_contract=_backend_contract(),
            filter_options=self._build_filter_options(session, movements=movements),
            is_backend_connected=True,
            items=[_to_list_item(movement) for movement in page_items],
            page=resolved_page,
            page_size=resolved_page_size,
            summary=_build_summary(filtered),
            total=total,
            trend=_build_trend(filtered),
        )

    def get_movement_detail(
        self,
        session: Session,
        *,
        movement_id: str,
    ) -> AdminCashFlowMovementDetailView:
        movement = next(
            (item for item in self._collect_movements(session) if item.id == movement_id),
            None,
        )
        if movement is None:
            raise CashCloseNotFoundError("Cash-flow movement was not found.")

        source_context = _source_context(movement)
        related_documents = _related_documents(movement)
        reconciliation = _reconciliation_view(movement)
        return AdminCashFlowMovementDetailView(
            available_actions=AdminCashFlowAvailableActionsView(
                can_export=False,
                can_open_cash_cut=movement.cash_cut_id is not None,
                can_open_reconciliation=movement.reconciliation_id is not None,
                note=(
                    "Flujo de efectivo es de solo lectura; los importes se corrigen "
                    "desde el documento origen."
                ),
            ),
            backend_contract=_backend_contract(),
            financial_classification=_financial_classification(movement),
            overview=AdminCashFlowMovementOverviewView(
                amount=movement.amount,
                branch_id=movement.branch_id,
                branch_name=movement.branch_name,
                category=movement.category_label,
                currency=movement.currency,
                direction=movement.direction,
                id=movement.id,
                occurred_at=movement.occurred_at,
                operator_id=movement.operator_id,
                operator_name=movement.operator_name,
                payment_method=movement.payment_method,
                source_document_id=movement.source_document_id,
                source_reference=movement.source_reference,
                source_type=movement.source_type,
                warning_state=_warning_state(movement),
                workstation_id=movement.workstation_id,
                workstation_name=movement.workstation_name,
            ),
            reconciliation=reconciliation,
            related_documents=related_documents,
            source_document_context=source_context,
        )

    def _collect_movements(self, session: Session) -> list[CashFlowMovement]:
        reconciliations_by_close_id = self._get_reconciliations_by_cash_cut_id(session)
        return [
            *self._sale_payment_movements(session),
            *self._return_movements(session),
            *self._operational_payment_movements(session),
            *self._operational_discount_movements(session),
            *self._cash_cut_difference_movements(
                session,
                reconciliations_by_close_id=reconciliations_by_close_id,
            ),
        ]

    def _sale_payment_movements(self, session: Session) -> list[CashFlowMovement]:
        rows = (
            session.execute(
                select(
                    SalePayment.id.label("movement_row_id"),
                    SalePayment.payment_method_code,
                    SalePayment.applied_amount,
                    SalePayment.currency_code,
                    SalePayment.received_at,
                    Sale.id.label("sale_id"),
                    Sale.total_amount,
                    Sale.status,
                    Sale.branch_id,
                    Branch.name.label("branch_name"),
                    Sale.workstation_id,
                    Workstation.name.label("workstation_name"),
                    Sale.operator_id,
                    User.full_name.label("operator_name"),
                    Sale.cash_session_id,
                    CashSessionClose.id.label("cash_cut_id"),
                    CashSessionClose.cash_variance_amount,
                )
                .select_from(SalePayment)
                .join(Sale, Sale.id == SalePayment.sale_id)
                .join(Branch, Branch.id == Sale.branch_id)
                .join(Workstation, Workstation.id == Sale.workstation_id)
                .join(User, User.id == Sale.operator_id)
                .outerjoin(
                    CashSessionClose, CashSessionClose.cash_session_id == Sale.cash_session_id
                )
            )
            .mappings()
            .all()
        )
        return [
            CashFlowMovement(
                amount=_money(type_cast(Decimal, row["applied_amount"])),
                branch_id=type_cast(uuid.UUID, row["branch_id"]),
                branch_name=type_cast(str, row["branch_name"]),
                cash_cut_folio=(
                    _build_cash_cut_folio(type_cast(uuid.UUID, row["cash_cut_id"]))
                    if row["cash_cut_id"] is not None
                    else None
                ),
                cash_cut_id=type_cast(uuid.UUID | None, row["cash_cut_id"]),
                cash_session_id=type_cast(uuid.UUID, row["cash_session_id"]),
                category_code="SALES",
                category_label="Ventas",
                currency=type_cast(str, row["currency_code"]),
                direction=MOVEMENT_DIRECTION_INFLOW,
                id=f"{SOURCE_TYPE_SALE}:{row['movement_row_id']}",
                occurred_at=type_cast(datetime, row["received_at"]),
                operator_id=type_cast(uuid.UUID, row["operator_id"]),
                operator_name=type_cast(str, row["operator_name"]),
                payment_method=type_cast(str, row["payment_method_code"]),
                reconciliation_folio=None,
                reconciliation_id=None,
                reconciliation_reason_code=None,
                reconciliation_status=RECONCILIATION_STATUS_NOT_REQUIRED,
                signed_effect=_money(type_cast(Decimal, row["applied_amount"])),
                source_document_id=type_cast(uuid.UUID, row["sale_id"]),
                source_reference=build_ticket_folio(type_cast(uuid.UUID, row["sale_id"])),
                source_status=type_cast(str, row["status"]),
                source_type=SOURCE_TYPE_SALE,
                workstation_id=type_cast(uuid.UUID, row["workstation_id"]),
                workstation_name=type_cast(str, row["workstation_name"]),
            )
            for row in rows
        ]

    def _return_movements(self, session: Session) -> list[CashFlowMovement]:
        rows = (
            session.execute(
                select(
                    SaleReturn.id,
                    SaleReturn.original_sale_id,
                    SaleReturn.branch_id,
                    Branch.name.label("branch_name"),
                    SaleReturn.workstation_id,
                    Workstation.name.label("workstation_name"),
                    SaleReturn.cash_session_id,
                    SaleReturn.created_by_user_id,
                    User.full_name.label("operator_name"),
                    SaleReturn.status,
                    SaleReturn.reason_code,
                    SaleReturn.reason_name,
                    SaleReturn.refund_method_code,
                    SaleReturn.currency_code,
                    SaleReturn.total_refund_amount,
                    SaleReturn.created_at_utc,
                    CashSessionClose.id.label("cash_cut_id"),
                )
                .select_from(SaleReturn)
                .join(Branch, Branch.id == SaleReturn.branch_id)
                .join(Workstation, Workstation.id == SaleReturn.workstation_id)
                .join(User, User.id == SaleReturn.created_by_user_id)
                .outerjoin(
                    CashSessionClose,
                    CashSessionClose.cash_session_id == SaleReturn.cash_session_id,
                )
            )
            .mappings()
            .all()
        )
        return [
            CashFlowMovement(
                amount=_money(type_cast(Decimal, row["total_refund_amount"])),
                branch_id=type_cast(uuid.UUID, row["branch_id"]),
                branch_name=type_cast(str, row["branch_name"]),
                cash_cut_folio=(
                    _build_cash_cut_folio(type_cast(uuid.UUID, row["cash_cut_id"]))
                    if row["cash_cut_id"] is not None
                    else None
                ),
                cash_cut_id=type_cast(uuid.UUID | None, row["cash_cut_id"]),
                cash_session_id=type_cast(uuid.UUID, row["cash_session_id"]),
                category_code=type_cast(str, row["reason_code"]),
                category_label=type_cast(str, row["reason_name"]),
                currency=type_cast(str, row["currency_code"]),
                direction=MOVEMENT_DIRECTION_OUTFLOW,
                id=f"{SOURCE_TYPE_RETURN_REFUND}:{row['id']}",
                occurred_at=type_cast(datetime, row["created_at_utc"]),
                operator_id=type_cast(uuid.UUID, row["created_by_user_id"]),
                operator_name=type_cast(str, row["operator_name"]),
                original_ticket_id=type_cast(uuid.UUID, row["original_sale_id"]),
                original_ticket_folio=build_ticket_folio(
                    type_cast(uuid.UUID, row["original_sale_id"])
                ),
                payment_method=type_cast(str, row["refund_method_code"]),
                reconciliation_folio=None,
                reconciliation_id=None,
                reconciliation_reason_code=None,
                reconciliation_status=RECONCILIATION_STATUS_NOT_REQUIRED,
                signed_effect=-_money(type_cast(Decimal, row["total_refund_amount"])),
                source_document_id=type_cast(uuid.UUID, row["id"]),
                source_reference=_build_return_folio(type_cast(uuid.UUID, row["id"])),
                source_status=type_cast(str, row["status"]),
                source_type=SOURCE_TYPE_RETURN_REFUND,
                workstation_id=type_cast(uuid.UUID, row["workstation_id"]),
                workstation_name=type_cast(str, row["workstation_name"]),
            )
            for row in rows
        ]

    def _operational_payment_movements(self, session: Session) -> list[CashFlowMovement]:
        rows = (
            session.execute(
                select(
                    OperationalPayment.id,
                    OperationalPayment.branch_id,
                    Branch.name.label("branch_name"),
                    OperationalPayment.workstation_id,
                    Workstation.name.label("workstation_name"),
                    OperationalPayment.active_cash_session_id,
                    OperationalPayment.created_by_user_id,
                    User.full_name.label("operator_name"),
                    OperationalPayment.status,
                    OperationalPayment.payee_name,
                    OperationalPayment.concept,
                    OperationalPayment.category_code,
                    OperationalPaymentCategory.name.label("category_name"),
                    OperationalPayment.payment_method_code,
                    OperationalPayment.currency_code,
                    OperationalPayment.total_amount,
                    OperationalPayment.created_at_utc,
                    CashSessionClose.id.label("cash_cut_id"),
                )
                .select_from(OperationalPayment)
                .join(Branch, Branch.id == OperationalPayment.branch_id)
                .join(Workstation, Workstation.id == OperationalPayment.workstation_id)
                .join(User, User.id == OperationalPayment.created_by_user_id)
                .outerjoin(
                    OperationalPaymentCategory,
                    OperationalPaymentCategory.code == OperationalPayment.category_code,
                )
                .outerjoin(
                    CashSessionClose,
                    CashSessionClose.cash_session_id == OperationalPayment.active_cash_session_id,
                )
            )
            .mappings()
            .all()
        )
        return [
            CashFlowMovement(
                amount=_money(type_cast(Decimal, row["total_amount"])),
                branch_id=type_cast(uuid.UUID, row["branch_id"]),
                branch_name=type_cast(str, row["branch_name"]),
                cash_cut_folio=(
                    _build_cash_cut_folio(type_cast(uuid.UUID, row["cash_cut_id"]))
                    if row["cash_cut_id"] is not None
                    else None
                ),
                cash_cut_id=type_cast(uuid.UUID | None, row["cash_cut_id"]),
                cash_session_id=type_cast(uuid.UUID, row["active_cash_session_id"]),
                category_code=type_cast(str | None, row["category_code"]),
                category_label=type_cast(str | None, row["category_name"]) or "Pago operativo",
                concept=type_cast(str, row["concept"]),
                currency=type_cast(str, row["currency_code"]),
                direction=MOVEMENT_DIRECTION_OUTFLOW,
                id=f"{SOURCE_TYPE_OPERATIONAL_PAYMENT}:{row['id']}",
                occurred_at=type_cast(datetime, row["created_at_utc"]),
                operator_id=type_cast(uuid.UUID, row["created_by_user_id"]),
                operator_name=type_cast(str, row["operator_name"]),
                payment_method=type_cast(str, row["payment_method_code"]),
                reconciliation_folio=None,
                reconciliation_id=None,
                reconciliation_reason_code=None,
                reconciliation_status=RECONCILIATION_STATUS_NOT_REQUIRED,
                signed_effect=-_money(type_cast(Decimal, row["total_amount"])),
                source_document_id=type_cast(uuid.UUID, row["id"]),
                source_reference=_build_operational_payment_folio(type_cast(uuid.UUID, row["id"])),
                source_status=type_cast(str, row["status"]),
                source_type=SOURCE_TYPE_OPERATIONAL_PAYMENT,
                workstation_id=type_cast(uuid.UUID, row["workstation_id"]),
                workstation_name=type_cast(str, row["workstation_name"]),
            )
            for row in rows
        ]

    def _operational_discount_movements(self, session: Session) -> list[CashFlowMovement]:
        rows = (
            session.execute(
                select(
                    OperationalDiscount.id,
                    OperationalDiscount.branch_id,
                    Branch.name.label("branch_name"),
                    OperationalDiscount.workstation_id,
                    Workstation.name.label("workstation_name"),
                    OperationalDiscount.active_cash_session_id,
                    OperationalDiscount.created_by_user_id,
                    User.full_name.label("operator_name"),
                    OperationalDiscount.status,
                    OperationalDiscount.subject_name,
                    OperationalDiscount.concept,
                    OperationalDiscount.category_code,
                    OperationalDiscountCategory.name.label("category_name"),
                    OperationalDiscount.payment_method_code,
                    OperationalDiscount.currency_code,
                    OperationalDiscount.total_amount,
                    OperationalDiscount.created_at_utc,
                    CashSessionClose.id.label("cash_cut_id"),
                )
                .select_from(OperationalDiscount)
                .join(Branch, Branch.id == OperationalDiscount.branch_id)
                .join(Workstation, Workstation.id == OperationalDiscount.workstation_id)
                .join(User, User.id == OperationalDiscount.created_by_user_id)
                .outerjoin(
                    OperationalDiscountCategory,
                    OperationalDiscountCategory.code == OperationalDiscount.category_code,
                )
                .outerjoin(
                    CashSessionClose,
                    CashSessionClose.cash_session_id == OperationalDiscount.active_cash_session_id,
                )
            )
            .mappings()
            .all()
        )
        return [
            CashFlowMovement(
                amount=_money(type_cast(Decimal, row["total_amount"])),
                branch_id=type_cast(uuid.UUID, row["branch_id"]),
                branch_name=type_cast(str, row["branch_name"]),
                cash_cut_folio=(
                    _build_cash_cut_folio(type_cast(uuid.UUID, row["cash_cut_id"]))
                    if row["cash_cut_id"] is not None
                    else None
                ),
                cash_cut_id=type_cast(uuid.UUID | None, row["cash_cut_id"]),
                cash_session_id=type_cast(uuid.UUID, row["active_cash_session_id"]),
                category_code=type_cast(str | None, row["category_code"]),
                category_label=type_cast(str | None, row["category_name"]) or "Descuento operativo",
                concept=type_cast(str, row["concept"]),
                currency=type_cast(str, row["currency_code"]),
                direction=MOVEMENT_DIRECTION_OUTFLOW,
                id=f"{SOURCE_TYPE_OPERATIONAL_DISCOUNT}:{row['id']}",
                occurred_at=type_cast(datetime, row["created_at_utc"]),
                operator_id=type_cast(uuid.UUID, row["created_by_user_id"]),
                operator_name=type_cast(str, row["operator_name"]),
                payment_method=type_cast(str, row["payment_method_code"]),
                reconciliation_folio=None,
                reconciliation_id=None,
                reconciliation_reason_code=None,
                reconciliation_status=RECONCILIATION_STATUS_NOT_REQUIRED,
                signed_effect=-_money(type_cast(Decimal, row["total_amount"])),
                source_document_id=type_cast(uuid.UUID, row["id"]),
                source_reference=_build_operational_discount_folio(type_cast(uuid.UUID, row["id"])),
                source_status=type_cast(str, row["status"]),
                source_type=SOURCE_TYPE_OPERATIONAL_DISCOUNT,
                workstation_id=type_cast(uuid.UUID, row["workstation_id"]),
                workstation_name=type_cast(str, row["workstation_name"]),
            )
            for row in rows
        ]

    def _cash_cut_difference_movements(
        self,
        session: Session,
        *,
        reconciliations_by_close_id: dict[uuid.UUID, RowMapping],
    ) -> list[CashFlowMovement]:
        rows = (
            session.execute(
                select(
                    CashSessionClose.id,
                    CashSessionClose.cash_session_id,
                    CashSessionClose.branch_id,
                    Branch.name.label("branch_name"),
                    CashSessionClose.workstation_id,
                    Workstation.name.label("workstation_name"),
                    CashSessionClose.closed_by_user_id,
                    User.full_name.label("closed_by_name"),
                    CashSessionClose.status,
                    CashSessionClose.expected_cash_amount,
                    CashSessionClose.counted_cash_amount,
                    CashSessionClose.cash_variance_amount,
                    CashSessionClose.committed_at_utc,
                )
                .select_from(CashSessionClose)
                .join(Branch, Branch.id == CashSessionClose.branch_id)
                .join(Workstation, Workstation.id == CashSessionClose.workstation_id)
                .outerjoin(User, User.id == CashSessionClose.closed_by_user_id)
                .where(
                    CashSessionClose.cash_variance_amount.is_not(None),
                    CashSessionClose.cash_variance_amount != ZERO_MONEY,
                )
            )
            .mappings()
            .all()
        )
        result: list[CashFlowMovement] = []
        for row in rows:
            close_id = type_cast(uuid.UUID, row["id"])
            difference = _money(type_cast(Decimal, row["cash_variance_amount"]))
            reconciliation = reconciliations_by_close_id.get(close_id)
            result.append(
                CashFlowMovement(
                    amount=abs(difference),
                    branch_id=type_cast(uuid.UUID, row["branch_id"]),
                    branch_name=type_cast(str, row["branch_name"]),
                    cash_cut_folio=_build_cash_cut_folio(close_id),
                    cash_cut_id=close_id,
                    cash_session_id=type_cast(uuid.UUID, row["cash_session_id"]),
                    category_code="CASH_DIFFERENCE",
                    category_label="Diferencia de caja",
                    counted_cash_amount=_money(type_cast(Decimal, row["counted_cash_amount"]))
                    if row["counted_cash_amount"] is not None
                    else None,
                    currency="MXN",
                    difference_amount=difference,
                    direction=MOVEMENT_DIRECTION_ADJUSTMENT,
                    expected_cash_amount=_money(type_cast(Decimal, row["expected_cash_amount"])),
                    id=f"{SOURCE_TYPE_CASH_CUT_DIFFERENCE}:{close_id}",
                    occurred_at=type_cast(datetime, row["committed_at_utc"]),
                    operator_id=type_cast(uuid.UUID | None, row["closed_by_user_id"]),
                    operator_name=_coalesce_name(row["closed_by_name"]),
                    payment_method=CASH_CLOSE_PAYMENT_METHOD_CASH,
                    reconciliation_folio=(
                        type_cast(str, reconciliation["folio"]) if reconciliation else None
                    ),
                    reconciliation_id=(
                        type_cast(uuid.UUID, reconciliation["id"]) if reconciliation else None
                    ),
                    reconciliation_reason_code=(
                        type_cast(str | None, reconciliation["reason_code"])
                        if reconciliation
                        else None
                    ),
                    reconciliation_status=(
                        type_cast(str, reconciliation["status"])
                        if reconciliation
                        else FINANCIAL_RECONCILIATION_STATUS_PENDING
                    ),
                    signed_effect=difference,
                    source_document_id=close_id,
                    source_reference=_build_cash_cut_folio(close_id),
                    source_status=type_cast(str, row["status"]),
                    source_type=SOURCE_TYPE_CASH_CUT_DIFFERENCE,
                    workstation_id=type_cast(uuid.UUID, row["workstation_id"]),
                    workstation_name=type_cast(str, row["workstation_name"]),
                )
            )
        return result

    def _get_reconciliations_by_cash_cut_id(self, session: Session) -> dict[uuid.UUID, RowMapping]:
        rows = (
            session.execute(
                select(
                    FinancialReconciliation.id,
                    FinancialReconciliation.folio,
                    FinancialReconciliation.source_document_id,
                    FinancialReconciliation.status,
                    FinancialReconciliation.reason_code,
                ).where(
                    FinancialReconciliation.source_type == FINANCIAL_RECONCILIATION_SOURCE_CASH_CUT
                )
            )
            .mappings()
            .all()
        )
        return {type_cast(uuid.UUID, row["source_document_id"]): row for row in rows}

    def _filter_movements(
        self,
        movements: list[CashFlowMovement],
        *,
        amount_max: Decimal | None,
        amount_min: Decimal | None,
        branch_id: uuid.UUID | None,
        category: str | None,
        date_from: datetime | None,
        date_to: datetime | None,
        direction: str | None,
        operator_id: uuid.UUID | None,
        payment_method: str | None,
        reconciliation_state: str | None,
        search: str | None,
        source_type: str | None,
        workstation_id: uuid.UUID | None,
    ) -> list[CashFlowMovement]:
        normalized_category = _normalize_optional(category)
        normalized_direction = _normalize_optional(direction)
        normalized_method = _normalize_optional(payment_method)
        normalized_reconciliation = _normalize_optional(reconciliation_state)
        normalized_search = _normalize_search(search)
        normalized_source = _normalize_optional(source_type)
        start = _ensure_utc(date_from) if date_from is not None else None
        end = _ensure_utc(date_to) if date_to is not None else None
        result = []
        for movement in movements:
            if branch_id is not None and movement.branch_id != branch_id:
                continue
            if workstation_id is not None and movement.workstation_id != workstation_id:
                continue
            if operator_id is not None and movement.operator_id != operator_id:
                continue
            if start is not None and movement.occurred_at < start:
                continue
            if end is not None and movement.occurred_at > end:
                continue
            if amount_min is not None and movement.amount < amount_min:
                continue
            if amount_max is not None and movement.amount > amount_max:
                continue
            if normalized_direction is not None and movement.direction != normalized_direction:
                continue
            if normalized_method is not None and movement.payment_method != normalized_method:
                continue
            if normalized_source is not None and movement.source_type != normalized_source:
                continue
            if (
                normalized_category is not None
                and (movement.category_code or "").upper() != normalized_category
            ):
                continue
            if (
                normalized_reconciliation is not None
                and movement.reconciliation_status != normalized_reconciliation
            ):
                continue
            if normalized_search is not None and not _movement_matches_search(
                movement,
                normalized_search,
            ):
                continue
            result.append(movement)
        return result

    def _build_filter_options(
        self,
        session: Session,
        *,
        movements: list[CashFlowMovement],
    ) -> AdminCashFlowFilterOptionsView:
        return AdminCashFlowFilterOptionsView(
            branches=[
                AdminCashFlowFilterOptionView(
                    id=str(row["id"]),
                    label=type_cast(str, row["label"]),
                )
                for row in session.execute(
                    select(
                        Branch.id,
                        (Branch.name + " - " + Branch.code).label("label"),
                    ).order_by(
                        Branch.name.asc(),
                    )
                )
                .mappings()
                .all()
            ],
            categories=_dedupe_options(
                AdminCashFlowFilterOptionView(
                    id=movement.category_code,
                    label=movement.category_label or movement.category_code,
                )
                for movement in movements
                if movement.category_code is not None
            ),
            directions=[
                AdminCashFlowFilterOptionView(id=MOVEMENT_DIRECTION_INFLOW, label="Entradas"),
                AdminCashFlowFilterOptionView(id=MOVEMENT_DIRECTION_OUTFLOW, label="Salidas"),
                AdminCashFlowFilterOptionView(id=MOVEMENT_DIRECTION_ADJUSTMENT, label="Ajustes"),
            ],
            operators=_dedupe_options(
                AdminCashFlowFilterOptionView(
                    id=str(movement.operator_id), label=movement.operator_name
                )
                for movement in movements
                if movement.operator_id is not None
            ),
            payment_methods=[
                AdminCashFlowFilterOptionView(id=SALE_PAYMENT_METHOD_CASH, label="Efectivo"),
                AdminCashFlowFilterOptionView(id=SALE_PAYMENT_METHOD_CARD, label="Tarjeta"),
                AdminCashFlowFilterOptionView(id=SALE_PAYMENT_METHOD_MIXED, label="Mixto"),
            ],
            reconciliation_states=[
                AdminCashFlowFilterOptionView(
                    id=RECONCILIATION_STATUS_NOT_REQUIRED, label="No requiere"
                ),
                AdminCashFlowFilterOptionView(
                    id=FINANCIAL_RECONCILIATION_STATUS_PENDING, label="Pendiente"
                ),
                AdminCashFlowFilterOptionView(
                    id=FINANCIAL_RECONCILIATION_STATUS_IN_REVIEW, label="En revision"
                ),
                AdminCashFlowFilterOptionView(
                    id=FINANCIAL_RECONCILIATION_STATUS_RECONCILED, label="Conciliado"
                ),
            ],
            source_types=[
                AdminCashFlowFilterOptionView(id=SOURCE_TYPE_SALE, label="Venta"),
                AdminCashFlowFilterOptionView(id=SOURCE_TYPE_RETURN_REFUND, label="Devolucion"),
                AdminCashFlowFilterOptionView(
                    id=SOURCE_TYPE_OPERATIONAL_PAYMENT, label="Pago operativo"
                ),
                AdminCashFlowFilterOptionView(
                    id=SOURCE_TYPE_OPERATIONAL_DISCOUNT, label="Descuento operativo"
                ),
                AdminCashFlowFilterOptionView(
                    id=SOURCE_TYPE_CASH_CUT_DIFFERENCE, label="Diferencia de caja"
                ),
            ],
            workstations=[
                AdminCashFlowFilterOptionView(
                    id=str(row["id"]),
                    label=type_cast(str, row["label"]),
                )
                for row in session.execute(
                    select(
                        Workstation.id,
                        (Workstation.name + " - " + Workstation.code).label("label"),
                    ).order_by(Workstation.name.asc())
                )
                .mappings()
                .all()
            ],
        )


def _backend_contract() -> AdminCashFlowBackendContractView:
    return AdminCashFlowBackendContractView(
        detail_endpoint="GET /v1/admin/cash-flow/{movement_id}",
        export_endpoint=None,
        list_endpoint="GET /v1/admin/cash-flow",
        trend_endpoint=None,
    )


def _to_list_item(movement: CashFlowMovement) -> AdminCashFlowMovementListItemView:
    return AdminCashFlowMovementListItemView(
        amount=movement.amount,
        branch_id=movement.branch_id,
        branch_name=movement.branch_name,
        category=movement.category_label,
        currency=movement.currency,
        direction=movement.direction,
        id=movement.id,
        occurred_at=movement.occurred_at,
        operator_id=movement.operator_id,
        operator_name=movement.operator_name,
        payment_method=movement.payment_method,
        reconciliation_status=movement.reconciliation_status,
        source_document_id=movement.source_document_id,
        source_reference=movement.source_reference,
        source_type=movement.source_type,
        warning_state=_warning_state(movement),
        workstation_id=movement.workstation_id,
        workstation_name=movement.workstation_name,
    )


def _build_summary(movements: list[CashFlowMovement]) -> AdminCashFlowSummaryView:
    inflows = _sum_money(m.amount for m in movements if m.direction == MOVEMENT_DIRECTION_INFLOW)
    outflows = _sum_money(m.amount for m in movements if m.direction == MOVEMENT_DIRECTION_OUTFLOW)
    return AdminCashFlowSummaryView(
        card_total=_sum_money(
            m.signed_effect
            for m in movements
            if m.payment_method == SALE_PAYMENT_METHOD_CARD
            and m.direction in {MOVEMENT_DIRECTION_INFLOW, MOVEMENT_DIRECTION_OUTFLOW}
        ),
        cash_total=_sum_money(
            m.signed_effect
            for m in movements
            if m.payment_method == SALE_PAYMENT_METHOD_CASH
            and m.direction in {MOVEMENT_DIRECTION_INFLOW, MOVEMENT_DIRECTION_OUTFLOW}
        ),
        difference_total=_sum_money(
            m.signed_effect for m in movements if m.source_type == SOURCE_TYPE_CASH_CUT_DIFFERENCE
        ),
        inflows_total=inflows,
        net_total=_money(inflows - outflows),
        operational_payments_total=_sum_money(
            m.amount for m in movements if m.source_type == SOURCE_TYPE_OPERATIONAL_PAYMENT
        ),
        outflows_total=outflows,
        pending_reconciliation_total=_sum_money(
            m.amount
            for m in movements
            if m.reconciliation_status
            in {FINANCIAL_RECONCILIATION_STATUS_PENDING, FINANCIAL_RECONCILIATION_STATUS_IN_REVIEW}
        ),
        refunds_total=_sum_money(
            m.amount for m in movements if m.source_type == SOURCE_TYPE_RETURN_REFUND
        ),
    )


def _build_trend(movements: list[CashFlowMovement]) -> list[AdminCashFlowTrendPointView]:
    by_date: dict[date, dict[str, Decimal]] = {}
    for movement in movements:
        if movement.direction == MOVEMENT_DIRECTION_ADJUSTMENT:
            continue
        day = movement.occurred_at.date()
        entry = by_date.setdefault(day, {"inflows": ZERO_MONEY, "outflows": ZERO_MONEY})
        if movement.direction == MOVEMENT_DIRECTION_INFLOW:
            entry["inflows"] += movement.amount
        elif movement.direction == MOVEMENT_DIRECTION_OUTFLOW:
            entry["outflows"] += movement.amount
    return [
        AdminCashFlowTrendPointView(
            date=day,
            inflows=_money(values["inflows"]),
            net=_money(values["inflows"] - values["outflows"]),
            outflows=_money(values["outflows"]),
        )
        for day, values in sorted(by_date.items())
    ]


def _source_context(movement: CashFlowMovement) -> AdminCashFlowSourceContextView:
    return AdminCashFlowSourceContextView(
        cash_cut_folio=movement.cash_cut_folio,
        cash_cut_id=movement.cash_cut_id,
        cash_cut_route_hint=(
            f"/admin/cortes-caja?cashSession={movement.cash_session_id}"
            if movement.cash_cut_id is not None and movement.cash_session_id is not None
            else None
        ),
        cash_session_id=movement.cash_session_id,
        concept=movement.concept,
        counted_cash_amount=movement.counted_cash_amount,
        difference_amount=movement.difference_amount,
        expected_cash_amount=movement.expected_cash_amount,
        note=_source_note(movement),
        original_ticket_folio=movement.original_ticket_folio,
        source_payment_method=movement.payment_method,
        source_reference=movement.source_reference,
        source_route_hint=_source_route_hint(movement),
        source_status=movement.source_status,
        source_total_amount=movement.amount,
        source_type=movement.source_type,
    )


def _financial_classification(
    movement: CashFlowMovement,
) -> AdminCashFlowFinancialClassificationView:
    is_cash = movement.payment_method == SALE_PAYMENT_METHOD_CASH
    is_card = movement.payment_method == SALE_PAYMENT_METHOD_CARD
    return AdminCashFlowFinancialClassificationView(
        affects_bank_settlement=is_card,
        affects_cash_drawer=is_cash,
        card_impact=movement.signed_effect if is_card else ZERO_MONEY,
        cash_impact=movement.signed_effect if is_cash else ZERO_MONEY,
        direction=movement.direction,
        net_effect=movement.signed_effect
        if movement.direction != MOVEMENT_DIRECTION_ADJUSTMENT
        else ZERO_MONEY,
        note=(
            "La diferencia de caja se muestra como contexto de conciliacion; "
            "no modifica el flujo neto."
            if movement.direction == MOVEMENT_DIRECTION_ADJUSTMENT
            else None
        ),
        payment_method=movement.payment_method,
        source_category=movement.category_label,
    )


def _reconciliation_view(movement: CashFlowMovement) -> AdminCashFlowReconciliationView:
    if movement.reconciliation_status == RECONCILIATION_STATUS_NOT_REQUIRED:
        return AdminCashFlowReconciliationView(
            message="Este movimiento no requiere conciliacion.",
            status=RECONCILIATION_STATUS_NOT_REQUIRED,
        )
    if movement.reconciliation_status == FINANCIAL_RECONCILIATION_STATUS_RECONCILED:
        return AdminCashFlowReconciliationView(
            message="Este movimiento ya esta documentado en conciliacion.",
            reason_label=_reason_label(movement.reconciliation_reason_code),
            reconciliation_folio=movement.reconciliation_folio,
            reconciliation_id=movement.reconciliation_id,
            route_hint=(
                f"/admin/conciliacion?reconciliation={movement.reconciliation_id}"
                if movement.reconciliation_id is not None
                else None
            ),
            status=movement.reconciliation_status,
        )
    return AdminCashFlowReconciliationView(
        message="Este movimiento esta pendiente de conciliacion.",
        reason_label=_reason_label(movement.reconciliation_reason_code),
        reconciliation_folio=movement.reconciliation_folio,
        reconciliation_id=movement.reconciliation_id,
        route_hint=(
            f"/admin/conciliacion?reconciliation={movement.reconciliation_id}"
            if movement.reconciliation_id is not None
            else "/admin/conciliacion"
        ),
        status=movement.reconciliation_status,
        unresolved_amount=movement.amount,
    )


def _related_documents(movement: CashFlowMovement) -> list[AdminCashFlowRelatedDocumentView]:
    documents = [
        AdminCashFlowRelatedDocumentView(
            amount=movement.amount,
            document_type=movement.source_type,
            folio=movement.source_reference,
            id=str(movement.source_document_id),
            occurred_at=movement.occurred_at,
            route_hint=_source_route_hint(movement),
            status=movement.source_status,
        )
    ]
    if movement.cash_cut_id is not None:
        documents.append(
            AdminCashFlowRelatedDocumentView(
                document_type="CASH_CUT",
                folio=movement.cash_cut_folio or _build_cash_cut_folio(movement.cash_cut_id),
                id=str(movement.cash_cut_id),
                route_hint=f"/admin/cortes-caja?cashSession={movement.cash_session_id}",
                status="COMMITTED",
            )
        )
    if movement.original_ticket_id is not None and movement.original_ticket_folio is not None:
        documents.append(
            AdminCashFlowRelatedDocumentView(
                document_type="TICKET",
                folio=movement.original_ticket_folio,
                id=str(movement.original_ticket_id),
                route_hint=f"/admin/ventas?ticket={movement.original_ticket_id}",
                status="SOURCE",
            )
        )
    if movement.reconciliation_id is not None and movement.reconciliation_folio is not None:
        documents.append(
            AdminCashFlowRelatedDocumentView(
                document_type="RECONCILIATION",
                folio=movement.reconciliation_folio,
                id=str(movement.reconciliation_id),
                route_hint=f"/admin/conciliacion?reconciliation={movement.reconciliation_id}",
                status=movement.reconciliation_status,
            )
        )
    return documents


def _source_route_hint(movement: CashFlowMovement) -> str | None:
    if movement.source_type == SOURCE_TYPE_SALE:
        return f"/admin/ventas?ticket={movement.source_document_id}"
    if movement.source_type == SOURCE_TYPE_RETURN_REFUND:
        return f"/admin/devoluciones-correcciones?return={movement.source_document_id}"
    if movement.source_type == SOURCE_TYPE_OPERATIONAL_PAYMENT:
        return f"/admin/pagos-operativos?payment={movement.source_document_id}"
    if movement.source_type == SOURCE_TYPE_OPERATIONAL_DISCOUNT:
        return f"/admin/descuentos?discount={movement.source_document_id}"
    if movement.source_type == SOURCE_TYPE_CASH_CUT_DIFFERENCE:
        return f"/admin/cortes-caja?cashSession={movement.cash_session_id}"
    return None


def _source_note(movement: CashFlowMovement) -> str | None:
    if movement.source_type == SOURCE_TYPE_CASH_CUT_DIFFERENCE:
        return "Diferencia declarada al cerrar caja; la resolucion vive en Conciliacion."
    if movement.cash_cut_id is None:
        return "Este movimiento aun no esta incluido en un corte confirmado."
    return None


def _warning_state(movement: CashFlowMovement) -> str:
    if movement.reconciliation_status in {
        FINANCIAL_RECONCILIATION_STATUS_PENDING,
        FINANCIAL_RECONCILIATION_STATUS_IN_REVIEW,
    }:
        if movement.amount >= HIGH_IMPACT_DIFFERENCE_THRESHOLD:
            return WARNING_STATE_CRITICAL
        return WARNING_STATE_RECONCILIATION
    if movement.cash_cut_id is None and movement.direction != MOVEMENT_DIRECTION_ADJUSTMENT:
        return WARNING_STATE_PENDING_CUT
    return WARNING_STATE_OK


def _movement_matches_search(movement: CashFlowMovement, search: str) -> bool:
    haystack = " ".join(
        value
        for value in [
            movement.id,
            movement.source_reference,
            movement.branch_name,
            movement.workstation_name,
            movement.operator_name,
            movement.category_label or "",
            movement.concept or "",
            movement.original_ticket_folio or "",
            movement.cash_cut_folio or "",
            movement.reconciliation_folio or "",
        ]
        if value
    ).casefold()
    return search in haystack


def _dedupe_options(
    options: Iterable[AdminCashFlowFilterOptionView],
) -> list[AdminCashFlowFilterOptionView]:
    result: dict[str, AdminCashFlowFilterOptionView] = {}
    for option in options:
        if not isinstance(option, AdminCashFlowFilterOptionView):
            continue
        if option.id not in result:
            result[option.id] = option
    return sorted(result.values(), key=lambda option: option.label)


def _build_cash_cut_folio(close_id: uuid.UUID) -> str:
    return f"CC-{str(close_id).split('-')[0].upper()}"


def _build_return_folio(return_id: uuid.UUID) -> str:
    return f"DEV-{str(return_id).split('-')[0].upper()}"


def _build_operational_payment_folio(payment_id: uuid.UUID) -> str:
    return f"PAG-{str(payment_id).split('-')[0].upper()}"


def _build_operational_discount_folio(discount_id: uuid.UUID) -> str:
    return f"DES-{str(discount_id).split('-')[0].upper()}"


def _reason_label(code: str | None) -> str | None:
    if code is None:
        return None
    labels = {
        "CARD_SETTLEMENT_DIFFERENCE": "Diferencia en terminal",
        "CASH_MISSING": "Faltante de efectivo",
        "CASH_OVER": "Sobrante de efectivo",
        "CORRECTION_APPLIED": "Correccion aplicada",
        "COUNTING_ERROR": "Error de conteo",
        "DEPOSIT_DIFFERENCE": "Diferencia de deposito",
        "DUPLICATE_TICKET": "Ticket duplicado",
        "OPERATIONAL_PAYMENT_MISSING": "Pago operativo no registrado",
        FINANCIAL_RECONCILIATION_REASON_OTHER: "Otro",
        "REFUND_RECORDED": "Devolucion registrada",
    }
    return labels.get(code, code)


def _normalize_optional(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    if not stripped or stripped.lower() == "all":
        return None
    return stripped.upper()


def _normalize_search(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip().casefold()
    return stripped or None


def _ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _coalesce_name(value: object) -> str:
    if isinstance(value, str) and value.strip():
        return value
    return "Sin operador"


def _money(value: Decimal) -> Decimal:
    return Decimal(value).quantize(MONEY_QUANTIZER)


def _sum_money(values: Iterable[Decimal]) -> Decimal:
    total = ZERO_MONEY
    for value in values:
        total += Decimal(value)
    return _money(total)
