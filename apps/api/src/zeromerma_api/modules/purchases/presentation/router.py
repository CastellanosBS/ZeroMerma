from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request, Response, status
from sqlalchemy.orm import Session

from zeromerma_api.db.session import get_session
from zeromerma_api.modules.idempotency.application.canonicalization import (
    IDEMPOTENCY_KEY_PATTERN,
    parse_idempotency_key,
)
from zeromerma_api.modules.idempotency.presentation.http import (
    idempotency_response,
    require_idempotency_key,
)
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
    AdminPurchaseReverseReceiptRequest,
    AdminPurchaseUpdateRequest,
    PurchaseCommandCode,
    PurchaseCommandResultView,
)
from zeromerma_api.modules.purchases.application.admin_services import AdminPurchaseService
from zeromerma_api.modules.purchases.application.idempotency import PurchaseCommandService
from zeromerma_api.modules.purchases.domain.exceptions import (
    PurchaseNotFoundError,
    PurchaseValidationError,
)
from zeromerma_api.presentation.errors import error_responses

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


_REPLAY_RESPONSE = {
    "headers": {"Idempotency-Replayed": {"$ref": "#/components/headers/IdempotencyReplayed"}}
}
_REJECTION_RESPONSE = {**error_responses()[409], **_REPLAY_RESPONSE}


@admin_router.get(
    "/commands/{command_code}/{idempotency_key}",
    response_model=PurchaseCommandResultView,
    responses={200: _REPLAY_RESPONSE, 409: _REJECTION_RESPONSE},
)
def recover_admin_purchase_command(
    command_code: PurchaseCommandCode,
    idempotency_key: Annotated[str, Path(pattern=IDEMPOTENCY_KEY_PATTERN)],
    branch_id: UUID,
    request: Request,
    current_user: Annotated[AuthenticatedUser, Depends(_require_backoffice_user)],
    session: Annotated[Session, Depends(get_session)],
) -> Response:
    result = PurchaseCommandService().recover(
        session,
        current_user=current_user,
        command_code=command_code,
        key=parse_idempotency_key(idempotency_key),
        branch_id=branch_id,
    )
    return idempotency_response(
        replace(result, status_code=200) if result.status_code < 300 else result, request
    )


@admin_router.post(
    "",
    response_model=PurchaseCommandResultView,
    status_code=201,
    responses={201: _REPLAY_RESPONSE, 409: _REJECTION_RESPONSE},
)
def create_admin_purchase(
    command: AdminPurchaseCreateRequest,
    request: Request,
    current_user: Annotated[AuthenticatedUser, Depends(_require_backoffice_user)],
    session: Annotated[Session, Depends(get_session)],
    key: Annotated[UUID, Depends(require_idempotency_key)],
) -> Response:
    try:
        result = PurchaseCommandService().execute(
            session,
            current_user=current_user,
            command_code="create",
            command=command,
            key=key,
            request_id=request.headers.get("X-Request-ID"),
        )
        return idempotency_response(result, request)
    except (PurchaseNotFoundError, PurchaseValidationError) as error:
        raise _to_http_exception(error) from error


@admin_router.patch(
    "/{purchase_id}",
    response_model=PurchaseCommandResultView,
    status_code=200,
    responses={200: _REPLAY_RESPONSE, 409: _REJECTION_RESPONSE},
)
def update_admin_purchase(
    purchase_id: UUID,
    command: AdminPurchaseUpdateRequest,
    request: Request,
    current_user: Annotated[AuthenticatedUser, Depends(_require_backoffice_user)],
    session: Annotated[Session, Depends(get_session)],
    key: Annotated[UUID, Depends(require_idempotency_key)],
) -> Response:
    try:
        result = PurchaseCommandService().execute(
            session,
            current_user=current_user,
            command_code="update",
            command=command,
            key=key,
            purchase_id=purchase_id,
            request_id=request.headers.get("X-Request-ID"),
        )
        return idempotency_response(result, request)
    except (PurchaseNotFoundError, PurchaseValidationError) as error:
        raise _to_http_exception(error) from error


@admin_router.post(
    "/direct-entry",
    response_model=PurchaseCommandResultView,
    status_code=201,
    responses={201: _REPLAY_RESPONSE, 409: _REJECTION_RESPONSE},
)
def create_admin_direct_entry(
    command: AdminPurchaseDirectEntryRequest,
    request: Request,
    current_user: Annotated[AuthenticatedUser, Depends(_require_backoffice_user)],
    session: Annotated[Session, Depends(get_session)],
    key: Annotated[UUID, Depends(require_idempotency_key)],
) -> Response:
    try:
        result = PurchaseCommandService().execute(
            session,
            current_user=current_user,
            command_code="direct-entry",
            command=command,
            key=key,
            request_id=request.headers.get("X-Request-ID"),
        )
        return idempotency_response(result, request)
    except (PurchaseNotFoundError, PurchaseValidationError) as error:
        raise _to_http_exception(error) from error


@admin_router.post(
    "/{purchase_id}/confirm",
    response_model=PurchaseCommandResultView,
    status_code=200,
    responses={200: _REPLAY_RESPONSE, 409: _REJECTION_RESPONSE},
)
def confirm_admin_purchase(
    purchase_id: UUID,
    request: Request,
    current_user: Annotated[AuthenticatedUser, Depends(_require_backoffice_user)],
    session: Annotated[Session, Depends(get_session)],
    key: Annotated[UUID, Depends(require_idempotency_key)],
) -> Response:
    try:
        result = PurchaseCommandService().execute(
            session,
            current_user=current_user,
            command_code="confirm",
            command=None,
            key=key,
            purchase_id=purchase_id,
            request_id=request.headers.get("X-Request-ID"),
        )
        return idempotency_response(result, request)
    except (PurchaseNotFoundError, PurchaseValidationError) as error:
        raise _to_http_exception(error) from error


@admin_router.post(
    "/{purchase_id}/receive",
    response_model=PurchaseCommandResultView,
    status_code=200,
    responses={200: _REPLAY_RESPONSE, 409: _REJECTION_RESPONSE},
)
def receive_admin_purchase(
    purchase_id: UUID,
    command: AdminPurchaseReceiveRequest,
    request: Request,
    current_user: Annotated[AuthenticatedUser, Depends(_require_backoffice_user)],
    session: Annotated[Session, Depends(get_session)],
    key: Annotated[UUID, Depends(require_idempotency_key)],
) -> Response:
    try:
        result = PurchaseCommandService().execute(
            session,
            current_user=current_user,
            command_code="receive",
            command=command,
            key=key,
            purchase_id=purchase_id,
            request_id=request.headers.get("X-Request-ID"),
        )
        return idempotency_response(result, request)
    except (PurchaseNotFoundError, PurchaseValidationError) as error:
        raise _to_http_exception(error) from error


@admin_router.post(
    "/{purchase_id}/reverse-receipt",
    response_model=PurchaseCommandResultView,
    responses={200: _REPLAY_RESPONSE, 409: _REJECTION_RESPONSE},
)
def reverse_admin_purchase_receipt(
    purchase_id: UUID,
    command: AdminPurchaseReverseReceiptRequest,
    request: Request,
    current_user: Annotated[AuthenticatedUser, Depends(_require_backoffice_user)],
    session: Annotated[Session, Depends(get_session)],
    key: Annotated[UUID, Depends(require_idempotency_key)],
) -> Response:
    try:
        result = PurchaseCommandService().execute(
            session,
            current_user=current_user,
            command_code="reverse-receipt",
            command=command,
            key=key,
            purchase_id=purchase_id,
            request_id=request.headers.get("X-Request-ID"),
        )
        return idempotency_response(result, request)
    except (PurchaseNotFoundError, PurchaseValidationError) as error:
        raise _to_http_exception(error) from error


@admin_router.post(
    "/{purchase_id}/cancel",
    response_model=PurchaseCommandResultView,
    status_code=200,
    responses={200: _REPLAY_RESPONSE, 409: _REJECTION_RESPONSE},
)
def cancel_admin_purchase(
    purchase_id: UUID,
    command: AdminPurchaseCancelRequest,
    request: Request,
    current_user: Annotated[AuthenticatedUser, Depends(_require_backoffice_user)],
    session: Annotated[Session, Depends(get_session)],
    key: Annotated[UUID, Depends(require_idempotency_key)],
) -> Response:
    try:
        result = PurchaseCommandService().execute(
            session,
            current_user=current_user,
            command_code="cancel",
            command=command,
            key=key,
            purchase_id=purchase_id,
            request_id=request.headers.get("X-Request-ID"),
        )
        return idempotency_response(result, request)
    except (PurchaseNotFoundError, PurchaseValidationError) as error:
        raise _to_http_exception(error) from error
