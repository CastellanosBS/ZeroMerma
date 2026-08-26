from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import cast as type_cast

from sqlalchemy import Select, String, and_, cast, exists, func, or_, select
from sqlalchemy.engine import RowMapping
from sqlalchemy.orm import Session

from zeromerma_api.modules.audit.application.service import AuditRecorder
from zeromerma_api.modules.branches.infrastructure.models import Branch, Workstation
from zeromerma_api.modules.identity.application.schemas import AuthenticatedUser
from zeromerma_api.modules.identity.infrastructure.models import User
from zeromerma_api.modules.returns.infrastructure.models import SaleReturn, SaleReturnLine
from zeromerma_api.modules.sales.domain.constants import (
    SALE_PAYMENT_METHOD_CARD,
    SALE_PAYMENT_METHOD_CASH,
    SALE_STATUS_CONFIRMED,
    VALID_SALE_PAYMENT_METHOD_CODES,
)
from zeromerma_api.modules.sales.domain.exceptions import SaleNotFoundError, SaleValidationError
from zeromerma_api.modules.sales.infrastructure.models import Sale, SaleLine, SalePayment
from zeromerma_api.modules.tickets.application.admin_schemas import (
    AdminSalesTicketBackendContractView,
    AdminSalesTicketDetailView,
    AdminSalesTicketFilterOptionView,
    AdminSalesTicketFilterOptionsView,
    AdminSalesTicketLineView,
    AdminSalesTicketListItemView,
    AdminSalesTicketMetricsView,
    AdminSalesTicketOperationalContextView,
    AdminSalesTicketOverviewView,
    AdminSalesTicketPaymentSummaryView,
    AdminSalesTicketPaymentView,
    AdminSalesTicketPrintableView,
    AdminSalesTicketRelatedDocumentView,
    AdminSalesTicketsListResponse,
)
from zeromerma_api.modules.tickets.domain.constants import (
    AUDIT_ACTION_TICKET_REPRINTED,
    TICKET_RESOURCE_TYPE,
    TICKET_RETURN_STATUS_FULLY_RETURNED,
    TICKET_RETURN_STATUS_NOT_RETURNED,
    TICKET_RETURN_STATUS_PARTIALLY_RETURNED,
)

ADMIN_TICKETS_PAGE_SIZE_MAX = 100
ZERO_MONEY = Decimal("0.00")
ZERO_QUANTITY = Decimal("0.000")
STATUS_WITH_RETURNS = "WITH_RETURNS"
STATUS_WITHOUT_RETURNS = "WITHOUT_RETURNS"


class AdminSalesTicketService:
    def __init__(self, audit_recorder: AuditRecorder | None = None) -> None:
        self._audit_recorder = audit_recorder or AuditRecorder()

    def list_tickets(
        self,
        session: Session,
        *,
        branch_id: uuid.UUID | None,
        cashier_id: uuid.UUID | None,
        date_from: datetime | None,
        date_to: datetime | None,
        max_amount: Decimal | None,
        min_amount: Decimal | None,
        page: int,
        page_size: int,
        payment_method: str | None,
        search: str | None,
        status_filter: str | None,
        workstation_id: uuid.UUID | None,
    ) -> AdminSalesTicketsListResponse:
        resolved_page_size = min(page_size, ADMIN_TICKETS_PAGE_SIZE_MAX)
        conditions = self._build_conditions(
            branch_id=branch_id,
            cashier_id=cashier_id,
            date_from=date_from,
            date_to=date_to,
            max_amount=max_amount,
            min_amount=min_amount,
            payment_method=payment_method,
            search=search,
            status_filter=status_filter,
            workstation_id=workstation_id,
        )
        sale_ids_statement = self._build_sale_ids_statement(conditions)

        total = int(
            session.execute(
                select(func.count()).select_from(sale_ids_statement.subquery())
            ).scalar_one()
        )

        line_stats_subquery = (
            select(
                SaleLine.sale_id.label("sale_id"),
                func.count(SaleLine.id).label("item_count"),
                func.coalesce(func.sum(SaleLine.quantity), ZERO_QUANTITY).label("unit_count"),
            )
            .group_by(SaleLine.sale_id)
            .subquery()
        )
        rows = session.execute(
            select(
                Sale.id,
                Sale.confirmed_at,
                Sale.total_amount,
                Sale.currency_code,
                Sale.status,
                Sale.branch_id,
                Branch.name.label("branch_name"),
                Sale.workstation_id,
                Workstation.code.label("workstation_code"),
                Workstation.name.label("workstation_name"),
                Sale.operator_id.label("cashier_id"),
                User.full_name.label("cashier_name"),
                func.coalesce(line_stats_subquery.c.item_count, 0).label("item_count"),
                func.coalesce(line_stats_subquery.c.unit_count, ZERO_QUANTITY).label("unit_count"),
            )
            .select_from(Sale)
            .join(Branch, Branch.id == Sale.branch_id)
            .join(Workstation, Workstation.id == Sale.workstation_id)
            .join(User, User.id == Sale.operator_id)
            .outerjoin(line_stats_subquery, line_stats_subquery.c.sale_id == Sale.id)
            .where(Sale.id.in_(sale_ids_statement))
            .order_by(Sale.confirmed_at.desc(), Sale.id.desc())
            .limit(resolved_page_size)
            .offset((page - 1) * resolved_page_size)
        ).mappings().all()

        sale_ids = [type_cast(uuid.UUID, row["id"]) for row in rows]
        payments_by_sale_id = self._get_payment_summary_by_sale_id(session, sale_ids=sale_ids)
        returns_by_sale_id = _get_return_summary_by_sale_ids(session, sale_ids=sale_ids)

        return AdminSalesTicketsListResponse(
            backend_contract=AdminSalesTicketBackendContractView(
                detail_endpoint="GET /v1/admin/sales/tickets/{ticket_id}",
                list_endpoint="GET /v1/admin/sales/tickets",
                reprint_endpoint="POST /v1/admin/sales/tickets/{ticket_id}/reprint",
            ),
            filter_options=self._build_filter_options(session),
            is_backend_connected=True,
            items=[
                _to_list_item(
                    row=row,
                    payment_summary=payments_by_sale_id.get(type_cast(uuid.UUID, row["id"]), []),
                    return_summary=returns_by_sale_id.get(type_cast(uuid.UUID, row["id"])),
                )
                for row in rows
            ],
            metrics=self._build_metrics(session, sale_ids_statement=sale_ids_statement),
            page=page,
            page_size=resolved_page_size,
            total=total,
        )

    def get_ticket_detail(
        self,
        session: Session,
        *,
        ticket_id: uuid.UUID,
    ) -> AdminSalesTicketDetailView:
        sale_record = session.execute(
            select(
                Sale.id,
                Sale.status,
                Sale.branch_id,
                Branch.name.label("branch_name"),
                Sale.workstation_id,
                Workstation.code.label("workstation_code"),
                Workstation.name.label("workstation_name"),
                Sale.cash_session_id,
                Sale.operator_id.label("cashier_id"),
                User.email.label("cashier_email"),
                User.full_name.label("cashier_name"),
                Sale.currency_code,
                Sale.subtotal_amount,
                Sale.total_amount,
                Sale.paid_amount,
                Sale.change_amount,
                Sale.confirmed_at,
            )
            .select_from(Sale)
            .join(Branch, Branch.id == Sale.branch_id)
            .join(Workstation, Workstation.id == Sale.workstation_id)
            .join(User, User.id == Sale.operator_id)
            .where(Sale.id == ticket_id)
        ).mappings().one_or_none()
        if sale_record is None:
            raise SaleNotFoundError("Ticket was not found.")

        line_records = session.execute(
            select(
                SaleLine.id,
                SaleLine.sequence,
                SaleLine.capture_mode,
                SaleLine.product_class_id,
                SaleLine.product_id,
                SaleLine.catalog_code_snapshot,
                SaleLine.catalog_name_snapshot,
                SaleLine.quantity,
                SaleLine.unit_price,
                SaleLine.line_total_amount,
                SaleLine.physical_attribution_status,
            )
            .where(SaleLine.sale_id == ticket_id)
            .order_by(SaleLine.sequence.asc())
        ).mappings().all()
        payment_records = session.execute(
            select(
                SalePayment.id,
                SalePayment.sequence,
                SalePayment.payment_method_code,
                SalePayment.tendered_amount,
                SalePayment.applied_amount,
                SalePayment.change_amount,
                SalePayment.currency_code,
                SalePayment.received_at,
            )
            .where(SalePayment.sale_id == ticket_id)
            .order_by(SalePayment.sequence.asc())
        ).mappings().all()
        return_summary = _get_return_summary_by_sale_ids(session, sale_ids=[ticket_id]).get(ticket_id)
        resolved_return_summary = _resolve_return_summary(return_summary)

        return AdminSalesTicketDetailView(
            overview=AdminSalesTicketOverviewView(
                id=type_cast(uuid.UUID, sale_record["id"]),
                folio=build_ticket_folio(type_cast(uuid.UUID, sale_record["id"])),
                status=_resolve_admin_status(
                    sale_status=type_cast(str, sale_record["status"]),
                    return_status=str(resolved_return_summary["return_status"]),
                ),
                confirmed_at=type_cast(datetime, sale_record["confirmed_at"]),
                currency_code=type_cast(str, sale_record["currency_code"]),
                subtotal_amount=type_cast(Decimal, sale_record["subtotal_amount"]),
                total_amount=type_cast(Decimal, sale_record["total_amount"]),
                paid_amount=type_cast(Decimal, sale_record["paid_amount"]),
                change_amount=type_cast(Decimal, sale_record["change_amount"]),
                item_count=len(line_records),
                unit_count=sum((type_cast(Decimal, row["quantity"]) for row in line_records), ZERO_QUANTITY),
                return_count=int(resolved_return_summary["return_count"]),
                returned_amount=type_cast(Decimal, resolved_return_summary["returned_amount"]),
                return_status=str(resolved_return_summary["return_status"]),
            ),
            operational_context=AdminSalesTicketOperationalContextView(
                branch_id=type_cast(uuid.UUID, sale_record["branch_id"]),
                branch_name=type_cast(str, sale_record["branch_name"]),
                workstation_id=type_cast(uuid.UUID, sale_record["workstation_id"]),
                workstation_code=type_cast(str, sale_record["workstation_code"]),
                workstation_name=type_cast(str, sale_record["workstation_name"]),
                cashier_id=type_cast(uuid.UUID, sale_record["cashier_id"]),
                cashier_email=type_cast(str, sale_record["cashier_email"]),
                cashier_name=type_cast(str, sale_record["cashier_name"]),
                cash_session_id=type_cast(uuid.UUID, sale_record["cash_session_id"]),
                sale_id=type_cast(uuid.UUID, sale_record["id"]),
                created_at=type_cast(datetime, sale_record["confirmed_at"]),
                confirmed_at=type_cast(datetime, sale_record["confirmed_at"]),
            ),
            lines=[
                AdminSalesTicketLineView(
                    id=type_cast(uuid.UUID, row["id"]),
                    sequence=int(type_cast(int, row["sequence"])),
                    capture_mode=type_cast(str, row["capture_mode"]),
                    catalog_code=type_cast(str, row["catalog_code_snapshot"]),
                    catalog_name=type_cast(str, row["catalog_name_snapshot"]),
                    product_id=type_cast(uuid.UUID | None, row["product_id"]),
                    product_class_id=type_cast(uuid.UUID | None, row["product_class_id"]),
                    quantity=type_cast(Decimal, row["quantity"]),
                    unit_price=type_cast(Decimal, row["unit_price"]),
                    line_total_amount=type_cast(Decimal, row["line_total_amount"]),
                    discount_amount=ZERO_MONEY,
                    physical_attribution_status=type_cast(str, row["physical_attribution_status"]),
                )
                for row in line_records
            ],
            payments=[
                AdminSalesTicketPaymentView(
                    id=type_cast(uuid.UUID, row["id"]),
                    sequence=int(type_cast(int, row["sequence"])),
                    payment_method_code=type_cast(str, row["payment_method_code"]),
                    tendered_amount=type_cast(Decimal, row["tendered_amount"]),
                    applied_amount=type_cast(Decimal, row["applied_amount"]),
                    change_amount=type_cast(Decimal, row["change_amount"]),
                    currency_code=type_cast(str, row["currency_code"]),
                    received_at=type_cast(datetime, row["received_at"]),
                )
                for row in payment_records
            ],
            printable_ticket=AdminSalesTicketPrintableView(
                can_reprint=True,
                preview_available=False,
                note="La reimpresion registra auditoria; la vista imprimible se conectara al contrato de impresion.",
            ),
            related_documents=self._get_related_documents(session, ticket_id=ticket_id),
        )

    def reprint_ticket(
        self,
        session: Session,
        *,
        current_user: AuthenticatedUser,
        request_id: str | None,
        ticket_id: uuid.UUID,
    ) -> AdminSalesTicketDetailView:
        detail = self.get_ticket_detail(session, ticket_id=ticket_id)
        self._audit_recorder.record(
            session,
            actor_id=current_user.id,
            action=AUDIT_ACTION_TICKET_REPRINTED,
            resource_type=TICKET_RESOURCE_TYPE,
            resource_id=str(ticket_id),
            branch_id=detail.operational_context.branch_id,
            request_id=request_id,
            metadata={
                "ticket_id": str(ticket_id),
                "folio": detail.overview.folio,
                "source": "backoffice",
            },
        )
        session.commit()
        return detail

    def _build_conditions(
        self,
        *,
        branch_id: uuid.UUID | None,
        cashier_id: uuid.UUID | None,
        date_from: datetime | None,
        date_to: datetime | None,
        max_amount: Decimal | None,
        min_amount: Decimal | None,
        payment_method: str | None,
        search: str | None,
        status_filter: str | None,
        workstation_id: uuid.UUID | None,
    ) -> list[object]:
        conditions: list[object] = []
        if branch_id is not None:
            conditions.append(Sale.branch_id == branch_id)
        if workstation_id is not None:
            conditions.append(Sale.workstation_id == workstation_id)
        if cashier_id is not None:
            conditions.append(Sale.operator_id == cashier_id)
        if date_from is not None:
            conditions.append(Sale.confirmed_at >= _ensure_utc(date_from))
        if date_to is not None:
            conditions.append(Sale.confirmed_at <= _ensure_utc(date_to))
        if min_amount is not None:
            conditions.append(Sale.total_amount >= min_amount)
        if max_amount is not None:
            conditions.append(Sale.total_amount <= max_amount)
        if payment_method:
            if payment_method not in VALID_SALE_PAYMENT_METHOD_CODES:
                raise SaleValidationError("Unsupported payment method filter.")
            conditions.append(
                exists(
                    select(SalePayment.id).where(
                        SalePayment.sale_id == Sale.id,
                        SalePayment.payment_method_code == payment_method,
                    )
                )
            )
        normalized_search = _normalize_search(search)
        if normalized_search:
            sale_id_query = normalized_search.removeprefix("tck-")
            line_match = exists(
                select(SaleLine.id).where(
                    SaleLine.sale_id == Sale.id,
                    or_(
                        func.lower(SaleLine.catalog_name_snapshot).contains(normalized_search),
                        func.lower(SaleLine.catalog_code_snapshot).contains(normalized_search),
                    ),
                )
            )
            conditions.append(
                or_(
                    func.lower(cast(Sale.id, String)).like(f"{sale_id_query}%"),
                    func.lower(cast(Sale.id, String)).contains(sale_id_query),
                    func.lower(User.full_name).contains(normalized_search),
                    func.lower(Branch.name).contains(normalized_search),
                    func.lower(Workstation.name).contains(normalized_search),
                    line_match,
                )
            )
        normalized_status = _normalize_optional(status_filter)
        if normalized_status == STATUS_WITH_RETURNS:
            conditions.append(
                exists(select(SaleReturn.id).where(SaleReturn.original_sale_id == Sale.id))
            )
        elif normalized_status == STATUS_WITHOUT_RETURNS:
            conditions.append(
                ~exists(select(SaleReturn.id).where(SaleReturn.original_sale_id == Sale.id))
            )
        elif normalized_status and normalized_status != SALE_STATUS_CONFIRMED:
            raise SaleValidationError("Unsupported ticket status filter.")
        return conditions

    def _build_sale_ids_statement(self, conditions: list[object]) -> Select[tuple[uuid.UUID]]:
        statement = (
            select(Sale.id)
            .select_from(Sale)
            .join(Branch, Branch.id == Sale.branch_id)
            .join(Workstation, Workstation.id == Sale.workstation_id)
            .join(User, User.id == Sale.operator_id)
        )
        if conditions:
            statement = statement.where(and_(*conditions))
        return statement

    def _build_filter_options(self, session: Session) -> AdminSalesTicketFilterOptionsView:
        branches = session.execute(
            select(Branch.id, Branch.name).order_by(Branch.name.asc())
        ).mappings().all()
        workstations = session.execute(
            select(Workstation.id, Workstation.name, Workstation.code).order_by(Workstation.name.asc())
        ).mappings().all()
        cashiers = session.execute(
            select(User.id, User.full_name)
            .where(exists(select(Sale.id).where(Sale.operator_id == User.id)))
            .order_by(User.full_name.asc())
        ).mappings().all()
        return AdminSalesTicketFilterOptionsView(
            branches=[
                AdminSalesTicketFilterOptionView(id=str(row["id"]), label=type_cast(str, row["name"]))
                for row in branches
            ],
            cashiers=[
                AdminSalesTicketFilterOptionView(id=str(row["id"]), label=type_cast(str, row["full_name"]))
                for row in cashiers
            ],
            payment_methods=[
                AdminSalesTicketFilterOptionView(id=SALE_PAYMENT_METHOD_CASH, label="Efectivo"),
                AdminSalesTicketFilterOptionView(id=SALE_PAYMENT_METHOD_CARD, label="Tarjeta"),
            ],
            statuses=[
                AdminSalesTicketFilterOptionView(id=SALE_STATUS_CONFIRMED, label="Confirmados"),
                AdminSalesTicketFilterOptionView(id=STATUS_WITH_RETURNS, label="Con devolucion"),
                AdminSalesTicketFilterOptionView(id=STATUS_WITHOUT_RETURNS, label="Sin devolucion"),
            ],
            workstations=[
                AdminSalesTicketFilterOptionView(
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
        sale_ids_statement: Select[tuple[uuid.UUID]],
    ) -> AdminSalesTicketMetricsView:
        metrics_row = session.execute(
            select(
                func.count(Sale.id).label("ticket_count"),
                func.coalesce(func.sum(Sale.total_amount), ZERO_MONEY).label("total_sales_amount"),
                func.coalesce(func.avg(Sale.total_amount), ZERO_MONEY).label("average_ticket_amount"),
            )
            .where(Sale.id.in_(sale_ids_statement))
        ).mappings().one()
        payment_rows = session.execute(
            select(
                SalePayment.payment_method_code,
                func.coalesce(func.sum(SalePayment.applied_amount), ZERO_MONEY).label("amount"),
            )
            .where(SalePayment.sale_id.in_(sale_ids_statement))
            .group_by(SalePayment.payment_method_code)
        ).mappings().all()
        payment_totals = {
            type_cast(str, row["payment_method_code"]): type_cast(Decimal, row["amount"])
            for row in payment_rows
        }
        tickets_with_returns = int(
            session.execute(
                select(func.count(func.distinct(SaleReturn.original_sale_id))).where(
                    SaleReturn.original_sale_id.in_(sale_ids_statement)
                )
            ).scalar_one()
        )
        return AdminSalesTicketMetricsView(
            average_ticket_amount=_money(type_cast(Decimal, metrics_row["average_ticket_amount"])),
            card_amount=_money(payment_totals.get(SALE_PAYMENT_METHOD_CARD, ZERO_MONEY)),
            cash_amount=_money(payment_totals.get(SALE_PAYMENT_METHOD_CASH, ZERO_MONEY)),
            ticket_count=int(type_cast(int, metrics_row["ticket_count"])),
            tickets_with_returns=tickets_with_returns,
            total_sales_amount=_money(type_cast(Decimal, metrics_row["total_sales_amount"])),
        )

    def _get_payment_summary_by_sale_id(
        self,
        session: Session,
        *,
        sale_ids: list[uuid.UUID],
    ) -> dict[uuid.UUID, list[AdminSalesTicketPaymentSummaryView]]:
        if not sale_ids:
            return {}
        rows = session.execute(
            select(
                SalePayment.sale_id,
                SalePayment.payment_method_code,
                SalePayment.currency_code,
                func.coalesce(func.sum(SalePayment.applied_amount), ZERO_MONEY).label("amount"),
            )
            .where(SalePayment.sale_id.in_(sale_ids))
            .group_by(SalePayment.sale_id, SalePayment.payment_method_code, SalePayment.currency_code)
            .order_by(SalePayment.sale_id.asc(), SalePayment.payment_method_code.asc())
        ).mappings().all()
        result: dict[uuid.UUID, list[AdminSalesTicketPaymentSummaryView]] = {}
        for row in rows:
            result.setdefault(type_cast(uuid.UUID, row["sale_id"]), []).append(
                AdminSalesTicketPaymentSummaryView(
                    payment_method_code=type_cast(str, row["payment_method_code"]),
                    amount=type_cast(Decimal, row["amount"]),
                    currency_code=type_cast(str, row["currency_code"]),
                )
            )
        return result

    def _get_related_documents(
        self,
        session: Session,
        *,
        ticket_id: uuid.UUID,
    ) -> list[AdminSalesTicketRelatedDocumentView]:
        rows = session.execute(
            select(
                SaleReturn.id,
                SaleReturn.status,
                SaleReturn.total_refund_amount,
                SaleReturn.created_at_utc,
            )
            .where(SaleReturn.original_sale_id == ticket_id)
            .order_by(SaleReturn.created_at_utc.desc())
        ).mappings().all()
        return [
            AdminSalesTicketRelatedDocumentView(
                id=type_cast(uuid.UUID, row["id"]),
                document_type="return",
                folio=f"DEV-{str(row['id']).split('-', maxsplit=1)[0].upper()}",
                status=type_cast(str, row["status"]),
                amount=type_cast(Decimal, row["total_refund_amount"]),
                occurred_at=type_cast(datetime, row["created_at_utc"]),
                route_hint="/admin/devoluciones-correcciones",
            )
            for row in rows
        ]


def build_ticket_folio(ticket_id: uuid.UUID) -> str:
    return f"TCK-{str(ticket_id).split('-', maxsplit=1)[0].upper()}"


def _to_list_item(
    *,
    row: RowMapping,
    payment_summary: list[AdminSalesTicketPaymentSummaryView],
    return_summary: dict[str, Decimal | int | str] | None,
) -> AdminSalesTicketListItemView:
    ticket_id = type_cast(uuid.UUID, row["id"])
    resolved_return_summary = _resolve_return_summary(return_summary)
    return_status = str(resolved_return_summary["return_status"])
    return AdminSalesTicketListItemView(
        id=ticket_id,
        folio=build_ticket_folio(ticket_id),
        sale_id=ticket_id,
        occurred_at=type_cast(datetime, row["confirmed_at"]),
        branch_id=type_cast(uuid.UUID, row["branch_id"]),
        branch_name=type_cast(str, row["branch_name"]),
        workstation_id=type_cast(uuid.UUID, row["workstation_id"]),
        workstation_code=type_cast(str, row["workstation_code"]),
        workstation_name=type_cast(str, row["workstation_name"]),
        cashier_id=type_cast(uuid.UUID, row["cashier_id"]),
        cashier_name=type_cast(str, row["cashier_name"]),
        item_count=int(type_cast(int, row["item_count"])),
        unit_count=type_cast(Decimal, row["unit_count"]),
        total_amount=type_cast(Decimal, row["total_amount"]),
        currency_code=type_cast(str, row["currency_code"]),
        payment_summary=payment_summary,
        payment_methods_label=_format_payment_methods(payment_summary),
        status=_resolve_admin_status(
            sale_status=type_cast(str, row["status"]),
            return_status=return_status,
        ),
        return_count=int(resolved_return_summary["return_count"]),
        return_status=return_status,
        has_returns=int(resolved_return_summary["return_count"]) > 0,
    )


def _get_return_summary_by_sale_ids(
    session: Session,
    *,
    sale_ids: list[uuid.UUID],
) -> dict[uuid.UUID, dict[str, Decimal | int | str]]:
    if not sale_ids:
        return {}
    total_quantity_rows = session.execute(
        select(
            SaleLine.sale_id,
            func.coalesce(func.sum(SaleLine.quantity), ZERO_QUANTITY).label("total_quantity"),
        )
        .where(SaleLine.sale_id.in_(sale_ids))
        .group_by(SaleLine.sale_id)
    ).mappings()
    total_quantity_by_sale_id = {
        type_cast(uuid.UUID, row["sale_id"]): type_cast(Decimal, row["total_quantity"])
        for row in total_quantity_rows
    }
    returned_quantity_rows = session.execute(
        select(
            SaleLine.sale_id,
            func.coalesce(func.sum(SaleReturnLine.returned_quantity), ZERO_QUANTITY).label(
                "returned_quantity"
            ),
        )
        .select_from(SaleReturnLine)
        .join(SaleLine, SaleLine.id == SaleReturnLine.original_sale_line_id)
        .where(SaleLine.sale_id.in_(sale_ids))
        .group_by(SaleLine.sale_id)
    ).mappings()
    returned_quantity_by_sale_id = {
        type_cast(uuid.UUID, row["sale_id"]): type_cast(Decimal, row["returned_quantity"])
        for row in returned_quantity_rows
    }
    return_rows = session.execute(
        select(
            SaleReturn.original_sale_id,
            func.count(SaleReturn.id).label("return_count"),
            func.coalesce(func.sum(SaleReturn.total_refund_amount), ZERO_MONEY).label(
                "returned_amount"
            ),
        )
        .where(SaleReturn.original_sale_id.in_(sale_ids))
        .group_by(SaleReturn.original_sale_id)
    ).mappings()
    return_stats_by_sale_id = {
        type_cast(uuid.UUID, row["original_sale_id"]): {
            "return_count": int(type_cast(int, row["return_count"])),
            "returned_amount": type_cast(Decimal, row["returned_amount"]),
        }
        for row in return_rows
    }
    result: dict[uuid.UUID, dict[str, Decimal | int | str]] = {}
    for sale_id in sale_ids:
        total_quantity = total_quantity_by_sale_id.get(sale_id, ZERO_QUANTITY)
        returned_quantity = returned_quantity_by_sale_id.get(sale_id, ZERO_QUANTITY)
        stats = return_stats_by_sale_id.get(
            sale_id,
            {"return_count": 0, "returned_amount": ZERO_MONEY},
        )
        result[sale_id] = {
            "return_count": type_cast(int, stats["return_count"]),
            "returned_amount": type_cast(Decimal, stats["returned_amount"]),
            "return_status": _get_return_status(
                total_quantity=total_quantity,
                returned_quantity=returned_quantity,
            ),
        }
    return result


def _resolve_return_summary(
    value: dict[str, Decimal | int | str] | None,
) -> dict[str, Decimal | int | str]:
    return value or {
        "return_count": 0,
        "returned_amount": ZERO_MONEY,
        "return_status": TICKET_RETURN_STATUS_NOT_RETURNED,
    }


def _get_return_status(*, total_quantity: Decimal, returned_quantity: Decimal) -> str:
    if returned_quantity <= ZERO_QUANTITY:
        return TICKET_RETURN_STATUS_NOT_RETURNED
    if returned_quantity >= total_quantity:
        return TICKET_RETURN_STATUS_FULLY_RETURNED
    return TICKET_RETURN_STATUS_PARTIALLY_RETURNED


def _resolve_admin_status(*, sale_status: str, return_status: str) -> str:
    if return_status == TICKET_RETURN_STATUS_FULLY_RETURNED:
        return "FULLY_RETURNED"
    if return_status == TICKET_RETURN_STATUS_PARTIALLY_RETURNED:
        return "PARTIALLY_RETURNED"
    return sale_status


def _format_payment_methods(payments: list[AdminSalesTicketPaymentSummaryView]) -> str:
    if not payments:
        return "Sin pagos"
    if len(payments) > 1:
        return "Mixto"
    return payments[0].payment_method_code


def _normalize_search(value: str | None) -> str | None:
    normalized = _normalize_optional(value)
    return normalized.casefold() if normalized else None


def _normalize_optional(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def _ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _money(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"))
