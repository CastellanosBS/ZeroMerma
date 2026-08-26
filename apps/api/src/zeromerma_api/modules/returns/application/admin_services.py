from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import cast as type_cast

from sqlalchemy import Select, String, and_, cast, exists, func, or_, select
from sqlalchemy.engine import RowMapping
from sqlalchemy.orm import Session

from zeromerma_api.modules.audit.application.visibility import (
    AuditVisibilityQueryService,
    BackofficeNotificationConfig,
    build_audit_actor_snapshot,
)
from zeromerma_api.modules.branches.infrastructure.models import Branch, Workstation
from zeromerma_api.modules.identity.infrastructure.models import User
from zeromerma_api.modules.returns.application.admin_schemas import (
    AdminReturnAvailableActionsView,
    AdminReturnCorrectionFilterOptionView,
    AdminReturnDetailView,
    AdminReturnFilterOptionsView,
    AdminReturnListItemView,
    AdminReturnMetricsView,
    AdminReturnOriginalTicketView,
    AdminReturnOverviewView,
    AdminReturnRefundImpactView,
    AdminReturnRelatedDocumentView,
    AdminReturnsBackendContractView,
    AdminReturnsListResponse,
    AdminReturnedLineView,
)
from zeromerma_api.modules.returns.domain.constants import (
    OUTBOX_EVENT_SALE_RETURN_BACKOFFICE_REVIEW_REQUESTED_V1,
    RETURN_REFUND_METHOD_CASH,
    RETURN_STATUS_COMMITTED,
)
from zeromerma_api.modules.returns.domain.exceptions import (
    SaleReturnNotFoundError,
    SaleReturnValidationError,
)
from zeromerma_api.modules.returns.infrastructure.models import SaleReturn, SaleReturnLine
from zeromerma_api.modules.sales.infrastructure.models import CashMovement, Sale, SaleLine, SalePayment

ADMIN_RETURN_PAGE_SIZE_MAX = 100
CASH_MOVEMENT_TYPE_SALE_RETURN_REFUND = "SALE_RETURN_REFUND"
ZERO_MONEY = Decimal("0.00")
ZERO_QUANTITY = Decimal("0.000")


class AdminReturnsService:
    def __init__(self, audit_visibility: AuditVisibilityQueryService | None = None) -> None:
        self._audit_visibility = audit_visibility or AuditVisibilityQueryService()

    def list_returns(
        self,
        session: Session,
        *,
        branch_id: uuid.UUID | None,
        date_from: datetime | None,
        date_to: datetime | None,
        max_amount: Decimal | None,
        min_amount: Decimal | None,
        operator_id: uuid.UUID | None,
        page: int,
        page_size: int,
        refund_method: str | None,
        search: str | None,
        status_filter: str | None,
    ) -> AdminReturnsListResponse:
        resolved_page = max(page, 1)
        resolved_page_size = min(max(page_size, 1), ADMIN_RETURN_PAGE_SIZE_MAX)
        conditions = _build_return_conditions(
            branch_id=branch_id,
            date_from=date_from,
            date_to=date_to,
            max_amount=max_amount,
            min_amount=min_amount,
            operator_id=operator_id,
            refund_method=refund_method,
            search=search,
            status_filter=status_filter,
        )
        base_statement = _build_return_base_statement(conditions)
        total = int(
            session.execute(
                select(func.count()).select_from(base_statement.order_by(None).subquery())
            ).scalar_one()
        )
        rows = session.execute(
            base_statement.order_by(SaleReturn.created_at_utc.desc(), SaleReturn.id.desc())
            .limit(resolved_page_size)
            .offset((resolved_page - 1) * resolved_page_size)
        ).mappings().all()

        return AdminReturnsListResponse(
            backend_contract=_backend_contract(),
            filter_options=_build_filter_options(session),
            is_backend_connected=True,
            items=[_map_return_list_item(row) for row in rows],
            metrics=_build_metrics(session, conditions),
            page=resolved_page,
            page_size=resolved_page_size,
            total=total,
        )

    def get_return_detail(self, session: Session, *, return_id: uuid.UUID) -> AdminReturnDetailView:
        return_record = _get_return_record(session, return_id=return_id)
        overview_row = session.execute(
            select(
                SaleReturn.id,
                SaleReturn.original_sale_id,
                SaleReturn.status,
                SaleReturn.created_by_user_id,
                User.email.label("operator_email"),
                User.full_name.label("operator_name"),
                SaleReturn.reason_code,
                SaleReturn.reason_name,
                SaleReturn.refund_method_code,
                SaleReturn.total_refund_amount,
                SaleReturn.currency_code,
                SaleReturn.notes,
                SaleReturn.created_at_utc,
                SaleReturn.branch_id,
                Branch.name.label("branch_name"),
                SaleReturn.workstation_id,
                Workstation.code.label("workstation_code"),
                Workstation.name.label("workstation_name"),
                SaleReturn.cash_session_id,
                Sale.status.label("sale_status"),
                Sale.confirmed_at.label("sale_confirmed_at"),
                Sale.total_amount.label("sale_total_amount"),
                Sale.operator_id.label("sale_operator_id"),
                Sale.cash_session_id.label("sale_cash_session_id"),
            )
            .select_from(SaleReturn)
            .join(User, User.id == SaleReturn.created_by_user_id)
            .join(Branch, Branch.id == SaleReturn.branch_id)
            .join(Workstation, Workstation.id == SaleReturn.workstation_id)
            .join(Sale, Sale.id == SaleReturn.original_sale_id)
            .where(SaleReturn.id == return_id)
        ).mappings().one()

        line_rows = session.execute(
            select(
                SaleReturnLine.id,
                SaleReturnLine.original_sale_line_id,
                SaleReturnLine.returned_product_code_snapshot,
                SaleReturnLine.returned_product_name_snapshot,
                SaleReturnLine.returned_product_class_code_snapshot,
                SaleReturnLine.returned_product_class_name_snapshot,
                SaleReturnLine.returned_quantity,
                SaleReturnLine.refund_unit_price,
                SaleReturnLine.refund_line_total_amount,
                SaleReturnLine.disposition_code,
                SaleLine.quantity.label("original_quantity"),
            )
            .select_from(SaleReturnLine)
            .join(SaleLine, SaleLine.id == SaleReturnLine.original_sale_line_id)
            .where(SaleReturnLine.sale_return_id == return_id)
            .order_by(SaleReturnLine.line_number.asc())
        ).mappings().all()
        payment_methods_label = _get_payment_methods_label(
            session,
            sale_id=type_cast(uuid.UUID, overview_row["original_sale_id"]),
        )
        sale_cashier_name = _get_user_name(
            session,
            user_id=type_cast(uuid.UUID, overview_row["sale_operator_id"]),
        )
        cash_movement_id = session.execute(
            select(CashMovement.id)
            .where(
                CashMovement.sale_id == overview_row["original_sale_id"],
                CashMovement.movement_type == CASH_MOVEMENT_TYPE_SALE_RETURN_REFUND,
                CashMovement.amount == overview_row["total_refund_amount"],
                CashMovement.cash_session_id == overview_row["cash_session_id"],
            )
            .order_by(CashMovement.occurred_at.desc())
        ).scalar_one_or_none()
        audit_summary = self._audit_visibility.build_summary(
            session,
            created_actor=build_audit_actor_snapshot(
                user_id=type_cast(uuid.UUID, overview_row["created_by_user_id"]),
                full_name=type_cast(str, overview_row["operator_name"]),
                email=type_cast(str | None, overview_row["operator_email"]),
            ),
            created_at_utc=type_cast(datetime, overview_row["created_at_utc"]),
            confirmed_at_utc=type_cast(datetime, overview_row["created_at_utc"]),
            reason_label=type_cast(str, overview_row["reason_name"]),
            notes=type_cast(str | None, overview_row["notes"]),
            notification_config=BackofficeNotificationConfig(
                aggregate_id=str(return_id),
                aggregate_type="sale_return",
                event_names=(OUTBOX_EVENT_SALE_RETURN_BACKOFFICE_REVIEW_REQUESTED_V1,),
                label="Revision de backoffice",
            ),
        )

        return AdminReturnDetailView(
            audit_summary=audit_summary,
            available_actions=AdminReturnAvailableActionsView(
                creation_note=(
                    "Las devoluciones nuevas requieren caja abierta y se registran desde el flujo operativo."
                )
            ),
            backend_contract=_backend_contract(),
            original_ticket=AdminReturnOriginalTicketView(
                sale_id=type_cast(uuid.UUID, overview_row["original_sale_id"]),
                folio=_build_sale_folio(type_cast(uuid.UUID, overview_row["original_sale_id"])),
                status=type_cast(str, overview_row["sale_status"]),
                sale_date=type_cast(datetime, overview_row["sale_confirmed_at"]),
                total_amount=type_cast(Decimal, overview_row["sale_total_amount"]),
                payment_methods_label=payment_methods_label,
                cashier_name=sale_cashier_name,
                branch_name=type_cast(str, overview_row["branch_name"]),
                workstation_name=type_cast(str, overview_row["workstation_name"]),
                cash_session_id=type_cast(uuid.UUID, overview_row["sale_cash_session_id"]),
            ),
            overview=AdminReturnOverviewView(
                id=type_cast(uuid.UUID, overview_row["id"]),
                folio=_build_return_folio(type_cast(uuid.UUID, overview_row["id"])),
                status=type_cast(str, overview_row["status"]),
                created_at=type_cast(datetime, overview_row["created_at_utc"]),
                branch_id=type_cast(uuid.UUID, overview_row["branch_id"]),
                branch_name=type_cast(str, overview_row["branch_name"]),
                workstation_id=type_cast(uuid.UUID, overview_row["workstation_id"]),
                workstation_name=type_cast(str, overview_row["workstation_name"]),
                workstation_code=type_cast(str, overview_row["workstation_code"]),
                operator_id=type_cast(uuid.UUID, overview_row["created_by_user_id"]),
                operator_name=type_cast(str, overview_row["operator_name"]),
                total_refund_amount=type_cast(Decimal, overview_row["total_refund_amount"]),
                refund_method=type_cast(str, overview_row["refund_method_code"]),
                reason_code=type_cast(str, overview_row["reason_code"]),
                reason_name=type_cast(str, overview_row["reason_name"]),
                notes=type_cast(str | None, overview_row["notes"]),
                is_partial_return=_is_partial_return(
                    session,
                    sale_id=type_cast(uuid.UUID, overview_row["original_sale_id"]),
                ),
            ),
            refund_impact=AdminReturnRefundImpactView(
                refund_method=type_cast(str, overview_row["refund_method_code"]),
                refund_amount=type_cast(Decimal, overview_row["total_refund_amount"]),
                cash_session_id=type_cast(uuid.UUID, overview_row["cash_session_id"]),
                cash_impact_amount=type_cast(Decimal, overview_row["total_refund_amount"]),
                linked_cash_movement_id=cash_movement_id,
                currency_code=type_cast(str, overview_row["currency_code"]),
            ),
            related_documents=[
                AdminReturnRelatedDocumentView(
                    id=str(overview_row["original_sale_id"]),
                    document_type="ticket",
                    folio=_build_sale_folio(type_cast(uuid.UUID, overview_row["original_sale_id"])),
                    status=type_cast(str, overview_row["sale_status"]),
                    amount=type_cast(Decimal, overview_row["sale_total_amount"]),
                    occurred_at=type_cast(datetime, overview_row["sale_confirmed_at"]),
                    route_hint="/admin/ventas",
                )
            ],
            returned_lines=[
                AdminReturnedLineView(
                    id=type_cast(uuid.UUID, row["id"]),
                    original_sale_line_id=type_cast(uuid.UUID, row["original_sale_line_id"]),
                    product_name=type_cast(str, row["returned_product_name_snapshot"]),
                    product_code=type_cast(str, row["returned_product_code_snapshot"]),
                    product_class_name=type_cast(str, row["returned_product_class_name_snapshot"]),
                    product_class_code=type_cast(str, row["returned_product_class_code_snapshot"]),
                    original_quantity=type_cast(Decimal, row["original_quantity"]),
                    returned_quantity=type_cast(Decimal, row["returned_quantity"]),
                    unit_price=type_cast(Decimal, row["refund_unit_price"]),
                    refund_amount=type_cast(Decimal, row["refund_line_total_amount"]),
                    disposition_code=type_cast(str, row["disposition_code"]),
                    line_status="COMMITTED",
                )
                for row in line_rows
            ],
        )


def _backend_contract() -> AdminReturnsBackendContractView:
    return AdminReturnsBackendContractView(
        create_endpoint=None,
        detail_endpoint="GET /v1/admin/returns-corrections/returns/{return_id}",
        list_endpoint="GET /v1/admin/returns-corrections/returns",
        reprint_endpoint=None,
    )


def _build_return_base_statement(conditions: list[object]) -> Select[tuple[object, ...]]:
    line_count_subquery = (
        select(
            SaleReturnLine.sale_return_id.label("sale_return_id"),
            func.count(SaleReturnLine.id).label("line_count"),
        )
        .group_by(SaleReturnLine.sale_return_id)
        .subquery()
    )
    statement = (
        select(
            SaleReturn.id,
            SaleReturn.original_sale_id,
            SaleReturn.status,
            SaleReturn.created_at_utc,
            SaleReturn.branch_id,
            Branch.name.label("branch_name"),
            SaleReturn.workstation_id,
            Workstation.code.label("workstation_code"),
            Workstation.name.label("workstation_name"),
            SaleReturn.created_by_user_id.label("operator_id"),
            User.full_name.label("operator_name"),
            SaleReturn.refund_method_code,
            SaleReturn.total_refund_amount,
            func.coalesce(line_count_subquery.c.line_count, 0).label("line_count"),
        )
        .select_from(SaleReturn)
        .join(Branch, Branch.id == SaleReturn.branch_id)
        .join(Workstation, Workstation.id == SaleReturn.workstation_id)
        .join(User, User.id == SaleReturn.created_by_user_id)
        .outerjoin(line_count_subquery, line_count_subquery.c.sale_return_id == SaleReturn.id)
    )
    if conditions:
        statement = statement.where(and_(*conditions))
    return statement


def _build_return_conditions(
    *,
    branch_id: uuid.UUID | None,
    date_from: datetime | None,
    date_to: datetime | None,
    max_amount: Decimal | None,
    min_amount: Decimal | None,
    operator_id: uuid.UUID | None,
    refund_method: str | None,
    search: str | None,
    status_filter: str | None,
) -> list[object]:
    conditions: list[object] = []
    if branch_id is not None:
        conditions.append(SaleReturn.branch_id == branch_id)
    if operator_id is not None:
        conditions.append(SaleReturn.created_by_user_id == operator_id)
    if date_from is not None:
        conditions.append(SaleReturn.created_at_utc >= date_from)
    if date_to is not None:
        conditions.append(SaleReturn.created_at_utc <= date_to)
    if min_amount is not None:
        conditions.append(SaleReturn.total_refund_amount >= min_amount)
    if max_amount is not None:
        conditions.append(SaleReturn.total_refund_amount <= max_amount)
    normalized_refund_method = _normalize_optional(refund_method)
    if normalized_refund_method is not None:
        if normalized_refund_method != RETURN_REFUND_METHOD_CASH:
            raise SaleReturnValidationError("El metodo de reembolso solicitado no es valido.")
        conditions.append(SaleReturn.refund_method_code == normalized_refund_method)
    normalized_status = _normalize_optional(status_filter)
    if normalized_status is not None:
        if normalized_status != RETURN_STATUS_COMMITTED:
            raise SaleReturnValidationError("El estado solicitado no es valido para devoluciones.")
        conditions.append(SaleReturn.status == normalized_status)
    normalized_search = _normalize_search(search)
    if normalized_search:
        sale_id_query = normalized_search.removeprefix("tck-")
        return_id_query = normalized_search.removeprefix("dev-")
        line_match = exists(
            select(SaleReturnLine.id).where(
                SaleReturnLine.sale_return_id == SaleReturn.id,
                or_(
                    func.lower(SaleReturnLine.returned_product_name_snapshot).contains(
                        normalized_search
                    ),
                    func.lower(SaleReturnLine.returned_product_code_snapshot).contains(
                        normalized_search
                    ),
                ),
            )
        )
        conditions.append(
            or_(
                func.lower(cast(SaleReturn.id, String)).like(f"{return_id_query}%"),
                func.lower(cast(SaleReturn.id, String)).contains(return_id_query),
                func.lower(cast(SaleReturn.original_sale_id, String)).like(f"{sale_id_query}%"),
                func.lower(cast(SaleReturn.original_sale_id, String)).contains(sale_id_query),
                func.lower(SaleReturn.reason_name).contains(normalized_search),
                func.lower(User.full_name).contains(normalized_search),
                func.lower(Branch.name).contains(normalized_search),
                line_match,
            )
        )
    return conditions


def _build_filter_options(session: Session) -> AdminReturnFilterOptionsView:
    branch_rows = session.execute(select(Branch.id, Branch.name).order_by(Branch.name.asc())).mappings()
    operator_rows = session.execute(
        select(User.id, User.full_name)
        .where(exists(select(SaleReturn.id).where(SaleReturn.created_by_user_id == User.id)))
        .order_by(User.full_name.asc())
    ).mappings()
    return AdminReturnFilterOptionsView(
        branches=[
            AdminReturnCorrectionFilterOptionView(id=str(row["id"]), label=type_cast(str, row["name"]))
            for row in branch_rows
        ],
        operators=[
            AdminReturnCorrectionFilterOptionView(id=str(row["id"]), label=type_cast(str, row["full_name"]))
            for row in operator_rows
        ],
        refund_methods=[
            AdminReturnCorrectionFilterOptionView(id=RETURN_REFUND_METHOD_CASH, label="Efectivo")
        ],
        statuses=[
            AdminReturnCorrectionFilterOptionView(id=RETURN_STATUS_COMMITTED, label="Confirmada")
        ],
    )


def _build_metrics(session: Session, conditions: list[object]) -> AdminReturnMetricsView:
    return_ids_statement = _build_return_base_statement(conditions).with_only_columns(
        SaleReturn.id
    ).order_by(None)
    metric_row = session.execute(
        select(
            func.count(SaleReturn.id).label("returns_count"),
            func.coalesce(func.sum(SaleReturn.total_refund_amount), ZERO_MONEY).label(
                "refunded_amount"
            ),
            func.coalesce(
                func.sum(
                    SaleReturn.total_refund_amount
                ).filter(SaleReturn.refund_method_code == RETURN_REFUND_METHOD_CASH),
                ZERO_MONEY,
            ).label("cash_refunded_amount"),
        ).where(SaleReturn.id.in_(return_ids_statement))
    ).mappings().one()
    returned_line_count = int(
        session.execute(
            select(func.count(SaleReturnLine.id)).where(
                SaleReturnLine.sale_return_id.in_(return_ids_statement)
            )
        ).scalar_one()
    )
    return AdminReturnMetricsView(
        returns_count=int(metric_row["returns_count"] or 0),
        refunded_amount=type_cast(Decimal, metric_row["refunded_amount"]),
        cash_refunded_amount=type_cast(Decimal, metric_row["cash_refunded_amount"]),
        returned_line_count=returned_line_count,
        pending_review_count=0,
    )


def _map_return_list_item(row: RowMapping) -> AdminReturnListItemView:
    return_id = type_cast(uuid.UUID, row["id"])
    original_sale_id = type_cast(uuid.UUID, row["original_sale_id"])
    return AdminReturnListItemView(
        id=return_id,
        folio=_build_return_folio(return_id),
        original_sale_id=original_sale_id,
        original_ticket_folio=_build_sale_folio(original_sale_id),
        created_at=type_cast(datetime, row["created_at_utc"]),
        branch_id=type_cast(uuid.UUID, row["branch_id"]),
        branch_name=type_cast(str, row["branch_name"]),
        workstation_id=type_cast(uuid.UUID, row["workstation_id"]),
        workstation_name=type_cast(str, row["workstation_name"]),
        workstation_code=type_cast(str, row["workstation_code"]),
        operator_id=type_cast(uuid.UUID, row["operator_id"]),
        operator_name=type_cast(str, row["operator_name"]),
        returned_line_count=int(type_cast(int, row["line_count"])),
        refunded_amount=type_cast(Decimal, row["total_refund_amount"]),
        refund_method=type_cast(str, row["refund_method_code"]),
        status=type_cast(str, row["status"]),
        warning_state=None,
    )


def _get_return_record(session: Session, *, return_id: uuid.UUID) -> SaleReturn:
    record = session.get(SaleReturn, return_id)
    if record is None:
        raise SaleReturnNotFoundError("La devolucion solicitada no existe.")
    return record


def _get_payment_methods_label(session: Session, *, sale_id: uuid.UUID) -> str:
    methods = [
        row[0]
        for row in session.execute(
            select(SalePayment.payment_method_code)
            .where(SalePayment.sale_id == sale_id)
            .distinct()
            .order_by(SalePayment.payment_method_code.asc())
        ).all()
    ]
    if not methods:
        return "Sin pagos"
    if len(methods) > 1:
        return "Mixto"
    return str(methods[0])


def _get_user_name(session: Session, *, user_id: uuid.UUID) -> str:
    user = session.get(User, user_id)
    return user.full_name if user is not None else "N/A"


def _is_partial_return(session: Session, *, sale_id: uuid.UUID) -> bool:
    sale_quantity = session.execute(
        select(func.coalesce(func.sum(SaleLine.quantity), ZERO_QUANTITY)).where(
            SaleLine.sale_id == sale_id
        )
    ).scalar_one()
    returned_quantity = session.execute(
        select(func.coalesce(func.sum(SaleReturnLine.returned_quantity), ZERO_QUANTITY))
        .select_from(SaleReturnLine)
        .join(SaleLine, SaleLine.id == SaleReturnLine.original_sale_line_id)
        .where(SaleLine.sale_id == sale_id)
    ).scalar_one()
    return type_cast(Decimal, returned_quantity) < type_cast(Decimal, sale_quantity)


def _build_sale_folio(sale_id: uuid.UUID) -> str:
    return f"TCK-{str(sale_id).split('-', maxsplit=1)[0].upper()}"


def _build_return_folio(return_id: uuid.UUID) -> str:
    return f"DEV-{str(return_id).split('-', maxsplit=1)[0].upper()}"


def _normalize_search(value: str | None) -> str | None:
    normalized = _normalize_optional(value)
    return normalized.casefold() if normalized else None


def _normalize_optional(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized.upper() if normalized else None
