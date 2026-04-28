from __future__ import annotations

import uuid
from datetime import UTC, datetime, time, timedelta
from decimal import Decimal
from typing import cast as type_cast
from zoneinfo import ZoneInfo

from sqlalchemy import Select, String, cast, exists, func, or_, select
from sqlalchemy.engine import RowMapping
from sqlalchemy.orm import Session

from zeromerma_api.modules.audit.application.service import AuditRecorder
from zeromerma_api.modules.branches.application.access import (
    WorkstationAccessService,
    WorkstationContext,
)
from zeromerma_api.modules.branches.application.schemas import (
    BranchSummary,
    WorkstationSummary,
)
from zeromerma_api.modules.cash.application.schemas import CashSessionView
from zeromerma_api.modules.cash.application.services import CashSessionQueryService
from zeromerma_api.modules.identity.application.schemas import AuthenticatedUser
from zeromerma_api.modules.identity.infrastructure.models import User
from zeromerma_api.modules.operations.domain.constants import BRANCH_BRAND_MAPPING
from zeromerma_api.modules.returns.infrastructure.models import SaleReturn, SaleReturnLine
from zeromerma_api.modules.sales.application.schemas import SaleDetailView
from zeromerma_api.modules.sales.application.services import SaleQueryService
from zeromerma_api.modules.sales.infrastructure.models import Sale, SaleLine, SalePayment
from zeromerma_api.modules.tickets.application.schemas import (
    TicketDetailResponse,
    TicketLineItemView,
    TicketListItemView,
    TicketOperatorSummaryView,
    TicketPaymentDetailView,
    TicketPaymentSummaryView,
    TicketsBootstrapResponse,
    TicketScopeView,
    TicketsListResponse,
)
from zeromerma_api.modules.tickets.domain.constants import (
    AUDIT_ACTION_TICKET_REPRINTED,
    TICKET_RESOURCE_TYPE,
    TICKET_RETURN_STATUS_FULLY_RETURNED,
    TICKET_RETURN_STATUS_NOT_RETURNED,
    TICKET_RETURN_STATUS_PARTIALLY_RETURNED,
    TICKET_SCOPE_CURRENT_SHIFT,
    TICKET_SCOPE_RECENT,
    TICKET_SCOPE_TODAY,
    VALID_TICKET_SCOPES,
)
from zeromerma_api.modules.tickets.domain.exceptions import (
    TicketConflictError,
    TicketNotFoundError,
    TicketValidationError,
)

MAX_TICKETS_PER_LIST = 80
ZERO_MONEY = Decimal("0.00")
ZERO_QUANTITY = Decimal("0.000")


class TicketsQueryService:
    def __init__(
        self,
        workstation_access: WorkstationAccessService | None = None,
        cash_session_query: CashSessionQueryService | None = None,
        sale_query_service: SaleQueryService | None = None,
    ) -> None:
        self._workstation_access = workstation_access or WorkstationAccessService()
        self._cash_session_query = cash_session_query or CashSessionQueryService()
        self._sale_query_service = sale_query_service or SaleQueryService()

    def get_bootstrap(
        self,
        session: Session,
        *,
        current_user: AuthenticatedUser,
        workstation_code: str,
    ) -> TicketsBootstrapResponse:
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

        return TicketsBootstrapResponse(
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
            ticket_lookup_allowed=(
                current_open_cash_session is not None
                and current_open_cash_session.user_id == current_user.id
            ),
            default_scope=TICKET_SCOPE_CURRENT_SHIFT,
            available_scopes=[
                TicketScopeView(code=TICKET_SCOPE_CURRENT_SHIFT, label="Turno actual"),
                TicketScopeView(code=TICKET_SCOPE_TODAY, label="Hoy"),
                TicketScopeView(code=TICKET_SCOPE_RECENT, label="Recientes"),
            ],
        )

    def list_tickets(
        self,
        session: Session,
        *,
        current_user: AuthenticatedUser,
        workstation_code: str,
        scope: str | None,
        query: str | None,
    ) -> TicketsListResponse:
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

        line_stats_subquery = (
            select(
                SaleLine.sale_id.label("sale_id"),
                func.count(SaleLine.id).label("item_count"),
                func.coalesce(func.sum(SaleLine.quantity), Decimal("0.000")).label(
                    "total_quantity"
                ),
            )
            .group_by(SaleLine.sale_id)
            .subquery()
        )

        sale_statement = type_cast(
            Select[tuple[object, ...]],
            select(
                Sale.id,
                Sale.confirmed_at,
                Sale.total_amount,
                Sale.currency_code,
                Sale.change_amount,
                Sale.cash_session_id,
                User.full_name.label("operator_full_name"),
                func.coalesce(line_stats_subquery.c.item_count, 0).label("item_count"),
                func.coalesce(line_stats_subquery.c.total_quantity, Decimal("0.000")).label(
                    "total_quantity"
                ),
            )
            .select_from(Sale)
            .join(User, User.id == Sale.operator_id)
            .outerjoin(line_stats_subquery, line_stats_subquery.c.sale_id == Sale.id)
            .where(Sale.branch_id == context.branch_id),
        )
        sale_statement = _apply_scope_filters(
            sale_statement,
            normalized_scope=normalized_scope,
            context=context,
            current_cash_session_id=current_open_cash_session.id,
        )
        sale_statement = _apply_search_filters(sale_statement, normalized_query)
        sale_rows = session.execute(
            sale_statement.order_by(Sale.confirmed_at.desc()).limit(MAX_TICKETS_PER_LIST)
        ).mappings().all()

        sale_ids = [row["id"] for row in sale_rows]
        payment_rows = session.execute(
            select(
                SalePayment.sale_id,
                SalePayment.payment_method_code,
                SalePayment.applied_amount,
                SalePayment.currency_code,
            )
            .where(SalePayment.sale_id.in_(sale_ids))
            .order_by(SalePayment.sale_id.asc(), SalePayment.sequence.asc())
        ).mappings().all()
        payment_summary_by_sale: dict[uuid.UUID, list[TicketPaymentSummaryView]] = {}
        for record in payment_rows:
            payment_summary_by_sale.setdefault(record["sale_id"], []).append(
                TicketPaymentSummaryView(
                    payment_method_code=record["payment_method_code"],
                    amount=record["applied_amount"],
                    currency_code=record["currency_code"],
                )
            )
        return_summary_by_sale = _get_ticket_return_summary_by_sale_ids(
            session,
            sale_ids=sale_ids,
        )

        return TicketsListResponse(
            workstation_code=workstation_code,
            scope=normalized_scope,
            query=_normalize_optional_string(query),
            tickets=[
                _build_ticket_list_item_view(
                    row=row,
                    payment_summary=payment_summary_by_sale.get(row["id"], []),
                    return_summary=return_summary_by_sale.get(row["id"]),
                )
                for row in sale_rows
            ],
        )

    def get_ticket_detail(
        self,
        session: Session,
        *,
        current_user: AuthenticatedUser,
        workstation_code: str,
        ticket_id: uuid.UUID,
    ) -> TicketDetailResponse:
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
            sale_id=ticket_id,
            user_id=current_user.id,
        )
        if sale_detail.branch_id != context.branch_id:
            raise TicketNotFoundError("El ticket no existe en la sucursal actual.")

        return _to_ticket_detail_response(
            sale_detail,
            context=context,
            return_summary=_get_ticket_return_summary_by_sale_ids(
                session,
                sale_ids=[ticket_id],
            ).get(ticket_id),
        )


class TicketsCommandService:
    def __init__(
        self,
        workstation_access: WorkstationAccessService | None = None,
        cash_session_query: CashSessionQueryService | None = None,
        sale_query_service: SaleQueryService | None = None,
        audit_recorder: AuditRecorder | None = None,
    ) -> None:
        self._workstation_access = workstation_access or WorkstationAccessService()
        self._cash_session_query = cash_session_query or CashSessionQueryService()
        self._sale_query_service = sale_query_service or SaleQueryService()
        self._audit_recorder = audit_recorder or AuditRecorder()

    def reprint_ticket(
        self,
        session: Session,
        *,
        current_user: AuthenticatedUser,
        workstation_code: str,
        ticket_id: uuid.UUID,
        request_id: str | None,
    ) -> TicketDetailResponse:
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
            sale_id=ticket_id,
            user_id=current_user.id,
        )
        if sale_detail.branch_id != context.branch_id:
            raise TicketNotFoundError("El ticket no existe en la sucursal actual.")

        self._audit_recorder.record(
            session,
            actor_id=current_user.id,
            action=AUDIT_ACTION_TICKET_REPRINTED,
            resource_type=TICKET_RESOURCE_TYPE,
            resource_id=str(ticket_id),
            branch_id=context.branch_id,
            request_id=request_id,
            metadata={
                "ticket_id": str(ticket_id),
                "folio": _build_ticket_folio(ticket_id),
                "workstation_code": workstation_code,
            },
        )
        session.commit()
        return _to_ticket_detail_response(
            sale_detail,
            context=context,
            return_summary=_get_ticket_return_summary_by_sale_ids(
                session,
                sale_ids=[ticket_id],
            ).get(ticket_id),
        )


def _apply_scope_filters(
    statement: Select[tuple[object, ...]],
    *,
    normalized_scope: str,
    context: WorkstationContext,
    current_cash_session_id: uuid.UUID,
) -> Select[tuple[object, ...]]:
    if normalized_scope == TICKET_SCOPE_CURRENT_SHIFT:
        return statement.where(Sale.cash_session_id == current_cash_session_id)

    if normalized_scope == TICKET_SCOPE_TODAY:
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

    return statement


def _apply_search_filters(
    statement: Select[tuple[object, ...]],
    normalized_query: str | None,
) -> Select[tuple[object, ...]]:
    if normalized_query is None:
        return statement

    sale_id_prefix = normalized_query.removeprefix("tck-")
    line_match = exists(
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
            line_match,
        )
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
        raise TicketConflictError(
            "Necesitas una caja abierta en esta estacion para consultar tickets."
        )
    if current_open_cash_session.user_id != current_user.id:
        raise TicketConflictError(
            "La caja abierta de esta estacion pertenece a otro cajero."
        )
    if (
        current_open_cash_session.branch_id != context.branch_id
        or current_open_cash_session.workstation_id != context.workstation_id
    ):
        raise TicketConflictError(
            "La caja abierta no coincide con el contexto actual de la estacion."
        )
    return current_open_cash_session


def _to_ticket_detail_response(
    sale_detail: SaleDetailView,
    *,
    context: WorkstationContext,
    return_summary: dict[str, Decimal | int | str] | None = None,
) -> TicketDetailResponse:
    total_quantity = sum((line.quantity for line in sale_detail.lines), Decimal("0.000"))
    resolved_return_summary = return_summary or {
        "has_returnable_quantity": True,
        "return_count": 0,
        "return_status": TICKET_RETURN_STATUS_NOT_RETURNED,
        "returned_amount": ZERO_MONEY,
    }
    return TicketDetailResponse(
        id=sale_detail.id,
        folio=_build_ticket_folio(sale_detail.id),
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
        operator=TicketOperatorSummaryView(
            id=sale_detail.operator_id,
            email=sale_detail.operator_email,
            full_name=sale_detail.operator_full_name,
        ),
        cash_session_id=sale_detail.cash_session_id,
        currency_code=sale_detail.currency_code,
        item_count=len(sale_detail.lines),
        total_quantity=total_quantity,
        subtotal_amount=sale_detail.subtotal_amount,
        total_amount=sale_detail.total_amount,
        paid_amount=sale_detail.paid_amount,
        change_amount=sale_detail.change_amount,
        return_count=int(resolved_return_summary["return_count"]),
        returned_amount=Decimal(resolved_return_summary["returned_amount"]),
        return_status=str(resolved_return_summary["return_status"]),
        has_returnable_quantity=bool(resolved_return_summary["has_returnable_quantity"]),
        lines=[
            TicketLineItemView(
                id=line.id,
                sequence=line.sequence,
                name=line.catalog_name_snapshot,
                quantity=line.quantity,
                unit_price=line.unit_price,
                line_total_amount=line.line_total_amount,
            )
            for line in sale_detail.lines
        ],
        payments=[
            TicketPaymentDetailView(
                id=payment.id,
                sequence=payment.sequence,
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


def _build_ticket_list_item_view(
    *,
    row: RowMapping,
    payment_summary: list[TicketPaymentSummaryView],
    return_summary: dict[str, Decimal | int | str] | None,
) -> TicketListItemView:
    ticket_id = type_cast(uuid.UUID, row["id"])
    resolved_return_summary = return_summary or {
        "has_returnable_quantity": True,
        "return_count": 0,
        "return_status": TICKET_RETURN_STATUS_NOT_RETURNED,
        "returned_amount": ZERO_MONEY,
    }
    return TicketListItemView(
        id=ticket_id,
        folio=_build_ticket_folio(ticket_id),
        confirmed_at=type_cast(datetime, row["confirmed_at"]),
        total_amount=type_cast(Decimal, row["total_amount"]),
        currency_code=type_cast(str, row["currency_code"]),
        change_amount=type_cast(Decimal, row["change_amount"]),
        operator_full_name=type_cast(str, row["operator_full_name"]),
        item_count=int(type_cast(int, row["item_count"])),
        total_quantity=type_cast(Decimal, row["total_quantity"]),
        return_count=int(resolved_return_summary["return_count"]),
        returned_amount=Decimal(resolved_return_summary["returned_amount"]),
        return_status=str(resolved_return_summary["return_status"]),
        has_returnable_quantity=bool(resolved_return_summary["has_returnable_quantity"]),
        payment_summary=payment_summary,
    )


def _get_ticket_return_summary_by_sale_ids(
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
        row["sale_id"]: Decimal(row["total_quantity"]) for row in total_quantity_rows
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
        row["sale_id"]: Decimal(row["returned_quantity"]) for row in returned_quantity_rows
    }

    sale_return_rows = session.execute(
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
    sale_return_stats_by_sale_id = {
        row["original_sale_id"]: {
            "return_count": int(type_cast(int, row["return_count"])),
            "returned_amount": type_cast(Decimal, row["returned_amount"]),
        }
        for row in sale_return_rows
    }

    summary_by_sale_id: dict[uuid.UUID, dict[str, Decimal | int | str]] = {}
    for sale_id in sale_ids:
        total_quantity = total_quantity_by_sale_id.get(sale_id, ZERO_QUANTITY)
        returned_quantity = returned_quantity_by_sale_id.get(sale_id, ZERO_QUANTITY)
        sale_return_stats = sale_return_stats_by_sale_id.get(
            sale_id,
            {"return_count": 0, "returned_amount": ZERO_MONEY},
        )
        return_status = _get_ticket_return_status(
            total_quantity=total_quantity,
            returned_quantity=returned_quantity,
        )
        summary_by_sale_id[sale_id] = {
            "return_count": type_cast(int, sale_return_stats["return_count"]),
            "returned_amount": type_cast(Decimal, sale_return_stats["returned_amount"]),
            "return_status": return_status,
            "has_returnable_quantity": return_status != TICKET_RETURN_STATUS_FULLY_RETURNED,
        }

    return summary_by_sale_id


def _build_ticket_folio(ticket_id: uuid.UUID) -> str:
    return f"TCK-{str(ticket_id).split('-', maxsplit=1)[0].upper()}"


def _get_branch_brand_key(branch_code: str) -> str:
    return BRANCH_BRAND_MAPPING.get(branch_code, "EL_MEJOR_PAN")


def _validate_scope(value: str | None) -> str:
    normalized = _normalize_optional_string(value)
    if normalized is None:
        return TICKET_SCOPE_CURRENT_SHIFT
    scope_code = normalized.upper()
    if scope_code not in VALID_TICKET_SCOPES:
        raise TicketValidationError("El alcance solicitado no es valido para tickets.")
    return scope_code


def _normalize_query(value: str | None) -> str | None:
    normalized = _normalize_optional_string(value)
    return normalized.casefold() if normalized else None


def _normalize_optional_string(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def _get_ticket_return_status(
    *,
    total_quantity: Decimal,
    returned_quantity: Decimal,
) -> str:
    if returned_quantity <= ZERO_QUANTITY:
        return TICKET_RETURN_STATUS_NOT_RETURNED
    if returned_quantity >= total_quantity:
        return TICKET_RETURN_STATUS_FULLY_RETURNED
    return TICKET_RETURN_STATUS_PARTIALLY_RETURNED
