from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from zeromerma_api.db.session import get_session
from zeromerma_api.modules.branches.domain.exceptions import (
    BranchAccessError,
    BranchAssignmentRequiredError,
    BranchInactiveError,
    WorkstationInactiveError,
    WorkstationNotFoundError,
)
from zeromerma_api.modules.identity.application.schemas import AuthenticatedUser
from zeromerma_api.modules.identity.application.services import user_can_access_surface
from zeromerma_api.modules.identity.domain.constants import IDENTITY_SURFACE_BACKOFFICE
from zeromerma_api.modules.identity.presentation.dependencies import get_current_user
from zeromerma_api.modules.sales.domain.exceptions import SaleNotFoundError, SaleValidationError
from zeromerma_api.modules.tickets.application.admin_schemas import (
    AdminSalesTicketDetailView,
    AdminSalesTicketsListResponse,
)
from zeromerma_api.modules.tickets.application.admin_services import AdminSalesTicketService
from zeromerma_api.modules.tickets.application.schemas import (
    TicketDetailResponse,
    TicketReprintRequest,
    TicketsBootstrapResponse,
    TicketsListResponse,
)
from zeromerma_api.modules.tickets.application.services import (
    TicketsCommandService,
    TicketsQueryService,
)
from zeromerma_api.modules.tickets.domain.exceptions import (
    TicketConflictError,
    TicketError,
    TicketNotFoundError,
    TicketValidationError,
)

router = APIRouter(prefix="/v1/tickets", tags=["tickets"])
admin_router = APIRouter(prefix="/v1/admin/sales/tickets", tags=["admin-sales-tickets"])


def _require_backoffice_user(current_user: AuthenticatedUser) -> None:
    if not user_can_access_surface(current_user, IDENTITY_SURFACE_BACKOFFICE):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Backoffice access is required.",
        )


def _to_http_exception(error: Exception) -> HTTPException:
    if isinstance(error, (WorkstationNotFoundError, SaleNotFoundError, TicketNotFoundError)):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error))

    if isinstance(error, BranchAssignmentRequiredError):
        return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(error))

    if isinstance(error, (BranchInactiveError, WorkstationInactiveError, TicketConflictError)):
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error))

    if isinstance(
        error,
        (BranchAccessError, SaleValidationError, TicketValidationError, TicketError),
    ):
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error))

    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error))


@admin_router.get("", response_model=AdminSalesTicketsListResponse)
def list_admin_sales_tickets(
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
    branch_id: UUID | None = None,
    workstation_id: UUID | None = None,
    cashier_id: UUID | None = None,
    payment_method: Annotated[str | None, Query(min_length=1)] = None,
    status_filter: Annotated[str | None, Query(alias="status", min_length=1)] = None,
    search: Annotated[str | None, Query(min_length=1)] = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    min_amount: Decimal | None = None,
    max_amount: Decimal | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 25,
) -> AdminSalesTicketsListResponse:
    _require_backoffice_user(current_user)
    try:
        return AdminSalesTicketService().list_tickets(
            session,
            branch_id=branch_id,
            cashier_id=cashier_id,
            date_from=date_from,
            date_to=date_to,
            max_amount=max_amount,
            min_amount=min_amount,
            page=page,
            page_size=page_size,
            payment_method=payment_method,
            search=search,
            status_filter=status_filter,
            workstation_id=workstation_id,
        )
    except (SaleNotFoundError, SaleValidationError, TicketError) as error:
        raise _to_http_exception(error) from error


@admin_router.get("/{ticket_id}", response_model=AdminSalesTicketDetailView)
def get_admin_sales_ticket_detail(
    ticket_id: UUID,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> AdminSalesTicketDetailView:
    _require_backoffice_user(current_user)
    try:
        return AdminSalesTicketService().get_ticket_detail(session, ticket_id=ticket_id)
    except (SaleNotFoundError, SaleValidationError, TicketError) as error:
        raise _to_http_exception(error) from error


@admin_router.post("/{ticket_id}/reprint", response_model=AdminSalesTicketDetailView)
def reprint_admin_sales_ticket(
    ticket_id: UUID,
    request: Request,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> AdminSalesTicketDetailView:
    _require_backoffice_user(current_user)
    try:
        return AdminSalesTicketService().reprint_ticket(
            session,
            current_user=current_user,
            request_id=request.headers.get("X-Request-ID"),
            ticket_id=ticket_id,
        )
    except (SaleNotFoundError, SaleValidationError, TicketError) as error:
        raise _to_http_exception(error) from error


@router.get("/bootstrap", response_model=TicketsBootstrapResponse)
def get_tickets_bootstrap(
    workstation_code: Annotated[str, Query(min_length=1)],
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> TicketsBootstrapResponse:
    try:
        return TicketsQueryService().get_bootstrap(
            session,
            current_user=current_user,
            workstation_code=workstation_code,
        )
    except (BranchAccessError, TicketError) as error:
        raise _to_http_exception(error) from error


@router.get("", response_model=TicketsListResponse)
def list_tickets(
    workstation_code: Annotated[str, Query(min_length=1)],
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
    scope: Annotated[str | None, Query(min_length=1)] = None,
    query: Annotated[str | None, Query(min_length=1)] = None,
) -> TicketsListResponse:
    try:
        return TicketsQueryService().list_tickets(
            session,
            current_user=current_user,
            workstation_code=workstation_code,
            scope=scope,
            query=query,
        )
    except (BranchAccessError, TicketError) as error:
        raise _to_http_exception(error) from error


@router.get("/{ticket_id}", response_model=TicketDetailResponse)
def get_ticket_detail(
    ticket_id: UUID,
    workstation_code: Annotated[str, Query(min_length=1)],
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> TicketDetailResponse:
    try:
        return TicketsQueryService().get_ticket_detail(
            session,
            current_user=current_user,
            workstation_code=workstation_code,
            ticket_id=ticket_id,
        )
    except (BranchAccessError, TicketError) as error:
        raise _to_http_exception(error) from error


@router.post("/{ticket_id}/reprint", response_model=TicketDetailResponse)
def reprint_ticket(
    ticket_id: UUID,
    payload: TicketReprintRequest,
    request: Request,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> TicketDetailResponse:
    try:
        return TicketsCommandService().reprint_ticket(
            session,
            current_user=current_user,
            workstation_code=payload.workstation_code,
            ticket_id=ticket_id,
            request_id=request.headers.get("X-Request-ID"),
        )
    except (BranchAccessError, TicketError) as error:
        raise _to_http_exception(error) from error

