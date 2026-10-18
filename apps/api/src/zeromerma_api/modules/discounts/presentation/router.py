from __future__ import annotations

from dataclasses import replace
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request, Response, status
from sqlalchemy.orm import Session

from zeromerma_api.db.session import get_session
from zeromerma_api.modules.branches.domain.exceptions import (
    BranchAccessError,
    BranchAssignmentRequiredError,
    BranchInactiveError,
    WorkstationInactiveError,
    WorkstationNotFoundError,
)
from zeromerma_api.modules.discounts.application.idempotency import OperationalDiscountCommitService
from zeromerma_api.modules.discounts.application.schemas import (
    AdminCommercialDiscountCreateRequest,
    AdminCommercialDiscountDuplicateRequest,
    AdminCommercialDiscountsListResponse,
    AdminCommercialDiscountUpdateRequest,
    AdminCommercialDiscountView,
    CreateOperationalDiscountRequest,
    DiscountsBootstrapResponse,
    DiscountsListResponse,
    OperationalDiscountCommitResultView,
    OperationalDiscountDetailResponse,
)
from zeromerma_api.modules.discounts.application.services import (
    AdminCommercialDiscountService,
    DiscountsQueryService,
)
from zeromerma_api.modules.discounts.domain.exceptions import (
    OperationalDiscountConflictError,
    OperationalDiscountError,
    OperationalDiscountNotFoundError,
    OperationalDiscountValidationError,
)
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
from zeromerma_api.presentation.errors import error_responses

_REPLAY_RESPONSE = {
    "headers": {"Idempotency-Replayed": {"$ref": "#/components/headers/IdempotencyReplayed"}}
}

router = APIRouter(prefix="/v1/discounts", tags=["discounts"])
admin_router = APIRouter(prefix="/v1/admin/discounts", tags=["admin-discounts"])


def _require_backoffice_user(current_user: AuthenticatedUser) -> None:
    if not user_can_access_surface(current_user, IDENTITY_SURFACE_BACKOFFICE):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Backoffice access is required.",
        )


def _to_http_exception(error: Exception) -> HTTPException:
    if isinstance(error, (WorkstationNotFoundError, OperationalDiscountNotFoundError)):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error))

    if isinstance(error, BranchAssignmentRequiredError):
        return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(error))

    if isinstance(
        error,
        (BranchInactiveError, WorkstationInactiveError, OperationalDiscountConflictError),
    ):
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error))

    if isinstance(
        error,
        (
            BranchAccessError,
            OperationalDiscountValidationError,
            OperationalDiscountError,
        ),
    ):
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error))

    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error))


@router.get("/bootstrap", response_model=DiscountsBootstrapResponse)
def get_discounts_bootstrap(
    workstation_code: Annotated[str, Query(min_length=1)],
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> DiscountsBootstrapResponse:
    try:
        return DiscountsQueryService().get_bootstrap(
            session,
            current_user=current_user,
            workstation_code=workstation_code,
        )
    except (BranchAccessError, OperationalDiscountError) as error:
        raise _to_http_exception(error) from error


@router.get("", response_model=DiscountsListResponse)
def list_discounts(
    workstation_code: Annotated[str, Query(min_length=1)],
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
    scope: Annotated[str | None, Query(min_length=1)] = None,
    created_by_user_id: UUID | None = None,
    query: Annotated[str | None, Query(min_length=1)] = None,
    category: Annotated[str | None, Query(min_length=1)] = None,
    payment_method: Annotated[str | None, Query(min_length=1)] = None,
) -> DiscountsListResponse:
    try:
        return DiscountsQueryService().list_discounts(
            session,
            current_user=current_user,
            workstation_code=workstation_code,
            scope=scope,
            created_by_user_id=created_by_user_id,
            query=query,
            category_filter=category,
            payment_method_filter=payment_method,
        )
    except (BranchAccessError, OperationalDiscountError) as error:
        raise _to_http_exception(error) from error


@router.get("/{discount_id}", response_model=OperationalDiscountDetailResponse)
def get_discount_detail(
    discount_id: UUID,
    workstation_code: Annotated[str, Query(min_length=1)],
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> OperationalDiscountDetailResponse:
    try:
        return DiscountsQueryService().get_discount_detail(
            session,
            current_user=current_user,
            workstation_code=workstation_code,
            discount_id=discount_id,
        )
    except (BranchAccessError, OperationalDiscountError) as error:
        raise _to_http_exception(error) from error


@router.post(
    "",
    response_model=OperationalDiscountCommitResultView,
    status_code=status.HTTP_201_CREATED,
    responses={201: _REPLAY_RESPONSE, 409: {**error_responses()[409], **_REPLAY_RESPONSE}},
)
def create_discount(
    payload: CreateOperationalDiscountRequest,
    request: Request,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
    key: Annotated[UUID, Depends(require_idempotency_key)],
) -> Response:
    try:
        result = OperationalDiscountCommitService().commit(
            session,
            current_user=current_user,
            command=payload,
            key=key,
            request_id=request.headers.get("X-Request-ID"),
        )
        return idempotency_response(result, request)
    except (BranchAccessError, OperationalDiscountError) as error:
        raise _to_http_exception(error) from error


@admin_router.get("", response_model=AdminCommercialDiscountsListResponse)
def list_admin_discounts(
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
    brand_id: UUID | None = None,
    class_id: UUID | None = None,
    status_filter: Annotated[str | None, Query(alias="status", min_length=1)] = None,
    discount_type: Annotated[str | None, Query(min_length=1)] = None,
    target_scope: Annotated[str | None, Query(min_length=1)] = None,
    validity: Annotated[str | None, Query(min_length=1)] = None,
    warning_state: Annotated[str | None, Query(min_length=1)] = None,
    search: Annotated[str | None, Query(min_length=1)] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 25,
) -> AdminCommercialDiscountsListResponse:
    _require_backoffice_user(current_user)
    try:
        return AdminCommercialDiscountService().list_discounts(
            session,
            brand_id=brand_id,
            class_id=class_id,
            status_filter=status_filter,
            discount_type=discount_type,
            target_scope=target_scope,
            validity=validity,
            warning_state=warning_state,
            search=search,
            page=page,
            page_size=page_size,
        )
    except OperationalDiscountError as error:
        raise _to_http_exception(error) from error


@admin_router.get("/{discount_id}", response_model=AdminCommercialDiscountView)
def get_admin_discount_detail(
    discount_id: UUID,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> AdminCommercialDiscountView:
    _require_backoffice_user(current_user)
    try:
        return AdminCommercialDiscountService().get_discount_detail(
            session,
            discount_id=discount_id,
        )
    except OperationalDiscountError as error:
        raise _to_http_exception(error) from error


@admin_router.post(
    "",
    response_model=AdminCommercialDiscountView,
    status_code=status.HTTP_201_CREATED,
)
def create_admin_discount(
    payload: AdminCommercialDiscountCreateRequest,
    request: Request,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> AdminCommercialDiscountView:
    _require_backoffice_user(current_user)
    try:
        return AdminCommercialDiscountService().create_discount(
            session,
            current_user=current_user,
            command=payload,
            request_id=request.headers.get("X-Request-ID"),
        )
    except OperationalDiscountError as error:
        raise _to_http_exception(error) from error


@admin_router.patch("/{discount_id}", response_model=AdminCommercialDiscountView)
def update_admin_discount(
    discount_id: UUID,
    payload: AdminCommercialDiscountUpdateRequest,
    request: Request,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> AdminCommercialDiscountView:
    _require_backoffice_user(current_user)
    try:
        return AdminCommercialDiscountService().update_discount(
            session,
            current_user=current_user,
            discount_id=discount_id,
            command=payload,
            request_id=request.headers.get("X-Request-ID"),
        )
    except OperationalDiscountError as error:
        raise _to_http_exception(error) from error


@admin_router.post("/{discount_id}/duplicate", response_model=AdminCommercialDiscountView)
def duplicate_admin_discount(
    discount_id: UUID,
    payload: AdminCommercialDiscountDuplicateRequest,
    request: Request,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> AdminCommercialDiscountView:
    _require_backoffice_user(current_user)
    try:
        return AdminCommercialDiscountService().duplicate_discount(
            session,
            current_user=current_user,
            discount_id=discount_id,
            command=payload,
            request_id=request.headers.get("X-Request-ID"),
        )
    except OperationalDiscountError as error:
        raise _to_http_exception(error) from error


@router.get(
    "/confirmations/{idempotency_key}",
    response_model=OperationalDiscountCommitResultView,
    responses={200: _REPLAY_RESPONSE, 409: {**error_responses()[409], **_REPLAY_RESPONSE}},
)
def recover_operational_discount(
    idempotency_key: Annotated[str, Path(pattern=IDEMPOTENCY_KEY_PATTERN)],
    workstation_code: Annotated[str, Query(min_length=1)],
    cash_session_id: UUID,
    request: Request,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> Response:
    result = OperationalDiscountCommitService().recover(
        session,
        current_user=current_user,
        key=parse_idempotency_key(idempotency_key),
        workstation_code=workstation_code,
        cash_session_id=cash_session_id,
    )
    if result.status_code < 300:
        result = replace(result, status_code=200)
    return idempotency_response(result, request)
