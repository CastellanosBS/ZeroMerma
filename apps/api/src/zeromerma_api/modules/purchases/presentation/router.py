from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy.orm import Session

from zeromerma_api.db.session import get_session
from zeromerma_api.modules.identity.application.schemas import AuthenticatedUser
from zeromerma_api.modules.identity.application.services import user_can_access_surface
from zeromerma_api.modules.identity.domain.constants import IDENTITY_SURFACE_BACKOFFICE
from zeromerma_api.modules.identity.presentation.dependencies import get_current_user
from zeromerma_api.modules.purchases.application.admin_schemas import (
    AdminPurchaseCancelRequest,
    AdminPurchaseCreateRequest,
    AdminPurchaseDetailView,
    AdminPurchaseDirectEntryRequest,
    AdminPurchaseListResponse,
    AdminPurchaseReceiveRequest,
    AdminPurchaseUpdateRequest,
)
from zeromerma_api.modules.purchases.application.admin_services import AdminPurchaseService
from zeromerma_api.modules.purchases.domain.exceptions import (
    PurchaseNotFoundError,
    PurchaseValidationError,
)

admin_router = APIRouter(prefix="/v1/admin/purchases", tags=["admin-purchases"])


def _require_backoffice_user(
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
) -> AuthenticatedUser:
    if not user_can_access_surface(current_user, IDENTITY_SURFACE_BACKOFFICE):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Backoffice access is required.",
        )
    return current_user


def _to_http_exception(error: Exception) -> HTTPException:
    if isinstance(error, PurchaseNotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error))
    if isinstance(error, PurchaseValidationError):
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error))
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Unexpected purchase error."
    )


def _parse_optional_datetime(value: str | None, *, end_of_day: bool = False) -> datetime | None:
    if not value:
        return None
    if len(value) == 10:
        parsed = datetime.fromisoformat(value)
        if end_of_day:
            parsed = parsed.replace(hour=23, minute=59, second=59, microsecond=999999)
        return parsed.replace(tzinfo=UTC)
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed


@admin_router.get("", response_model=AdminPurchaseListResponse)
def list_admin_purchases(
    current_user: Annotated[AuthenticatedUser, Depends(_require_backoffice_user)],
    session: Annotated[Session, Depends(get_session)],
    amount_max: Annotated[Decimal | None, Query(ge=Decimal("0"))] = None,
    amount_min: Annotated[Decimal | None, Query(ge=Decimal("0"))] = None,
    branch_id: Annotated[UUID | None, Query()] = None,
    date_from: Annotated[str | None, Query()] = None,
    date_to: Annotated[str | None, Query()] = None,
    discrepancy_state: Annotated[str | None, Query(min_length=1)] = None,
    operator_user_id: Annotated[UUID | None, Query()] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 25,
    product_id: Annotated[UUID | None, Query()] = None,
    product_kind: Annotated[str | None, Query(min_length=1)] = None,
    search: Annotated[str | None, Query(min_length=1)] = None,
    status_filter: Annotated[str | None, Query(alias="status")] = None,
    supplier_id: Annotated[UUID | None, Query()] = None,
    warning_state: Annotated[str | None, Query(min_length=1)] = None,
) -> AdminPurchaseListResponse:
    _ = current_user
    try:
        return AdminPurchaseService().list_purchases(
            session,
            amount_max=amount_max,
            amount_min=amount_min,
            branch_id=branch_id,
            date_from=_parse_optional_datetime(date_from),
            date_to=_parse_optional_datetime(date_to, end_of_day=True),
            discrepancy_state=discrepancy_state,
            operator_user_id=operator_user_id,
            page=page,
            page_size=page_size,
            product_id=product_id,
            product_kind=product_kind,
            search=search,
            status_filter=status_filter,
            supplier_id=supplier_id,
            warning_state=warning_state,
        )
    except (PurchaseNotFoundError, PurchaseValidationError) as error:
        raise _to_http_exception(error) from error


@admin_router.get("/{purchase_id}", response_model=AdminPurchaseDetailView)
def get_admin_purchase_detail(
    purchase_id: UUID,
    current_user: Annotated[AuthenticatedUser, Depends(_require_backoffice_user)],
    session: Annotated[Session, Depends(get_session)],
) -> AdminPurchaseDetailView:
    _ = current_user
    try:
        return AdminPurchaseService().get_purchase_detail(session, purchase_id=purchase_id)
    except (PurchaseNotFoundError, PurchaseValidationError) as error:
        raise _to_http_exception(error) from error


@admin_router.post("", response_model=AdminPurchaseDetailView, status_code=status.HTTP_201_CREATED)
def create_admin_purchase(
    command: AdminPurchaseCreateRequest,
    current_user: Annotated[AuthenticatedUser, Depends(_require_backoffice_user)],
    session: Annotated[Session, Depends(get_session)],
    request_id: Annotated[str | None, Header(alias="X-Request-ID")] = None,
) -> AdminPurchaseDetailView:
    try:
        return AdminPurchaseService().create_purchase(
            session,
            command=command,
            current_user=current_user,
            request_id=request_id,
        )
    except (PurchaseNotFoundError, PurchaseValidationError) as error:
        raise _to_http_exception(error) from error


@admin_router.patch("/{purchase_id}", response_model=AdminPurchaseDetailView)
def update_admin_purchase(
    purchase_id: UUID,
    command: AdminPurchaseUpdateRequest,
    current_user: Annotated[AuthenticatedUser, Depends(_require_backoffice_user)],
    session: Annotated[Session, Depends(get_session)],
    request_id: Annotated[str | None, Header(alias="X-Request-ID")] = None,
) -> AdminPurchaseDetailView:
    try:
        return AdminPurchaseService().update_purchase(
            session,
            command=command,
            current_user=current_user,
            purchase_id=purchase_id,
            request_id=request_id,
        )
    except (PurchaseNotFoundError, PurchaseValidationError) as error:
        raise _to_http_exception(error) from error


@admin_router.post(
    "/direct-entry", response_model=AdminPurchaseDetailView, status_code=status.HTTP_201_CREATED
)
def create_admin_direct_entry(
    command: AdminPurchaseDirectEntryRequest,
    current_user: Annotated[AuthenticatedUser, Depends(_require_backoffice_user)],
    session: Annotated[Session, Depends(get_session)],
    request_id: Annotated[str | None, Header(alias="X-Request-ID")] = None,
) -> AdminPurchaseDetailView:
    try:
        return AdminPurchaseService().create_direct_entry(
            session,
            command=command,
            current_user=current_user,
            request_id=request_id,
        )
    except (PurchaseNotFoundError, PurchaseValidationError) as error:
        raise _to_http_exception(error) from error


@admin_router.post("/{purchase_id}/confirm", response_model=AdminPurchaseDetailView)
def confirm_admin_purchase(
    purchase_id: UUID,
    current_user: Annotated[AuthenticatedUser, Depends(_require_backoffice_user)],
    session: Annotated[Session, Depends(get_session)],
    request_id: Annotated[str | None, Header(alias="X-Request-ID")] = None,
) -> AdminPurchaseDetailView:
    try:
        return AdminPurchaseService().confirm_purchase(
            session,
            current_user=current_user,
            purchase_id=purchase_id,
            request_id=request_id,
        )
    except (PurchaseNotFoundError, PurchaseValidationError) as error:
        raise _to_http_exception(error) from error


@admin_router.post("/{purchase_id}/receive", response_model=AdminPurchaseDetailView)
def receive_admin_purchase(
    purchase_id: UUID,
    command: AdminPurchaseReceiveRequest,
    current_user: Annotated[AuthenticatedUser, Depends(_require_backoffice_user)],
    session: Annotated[Session, Depends(get_session)],
    request_id: Annotated[str | None, Header(alias="X-Request-ID")] = None,
) -> AdminPurchaseDetailView:
    try:
        return AdminPurchaseService().receive_purchase(
            session,
            command=command,
            current_user=current_user,
            purchase_id=purchase_id,
            request_id=request_id,
        )
    except (PurchaseNotFoundError, PurchaseValidationError) as error:
        raise _to_http_exception(error) from error


@admin_router.post("/{purchase_id}/cancel", response_model=AdminPurchaseDetailView)
def cancel_admin_purchase(
    purchase_id: UUID,
    command: AdminPurchaseCancelRequest,
    current_user: Annotated[AuthenticatedUser, Depends(_require_backoffice_user)],
    session: Annotated[Session, Depends(get_session)],
    request_id: Annotated[str | None, Header(alias="X-Request-ID")] = None,
) -> AdminPurchaseDetailView:
    try:
        return AdminPurchaseService().cancel_purchase(
            session,
            command=command,
            current_user=current_user,
            purchase_id=purchase_id,
            request_id=request_id,
        )
    except (PurchaseNotFoundError, PurchaseValidationError) as error:
        raise _to_http_exception(error) from error

