from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy.orm import Session

from zeromerma_api.db.session import get_session
from zeromerma_api.modules.identity.application.schemas import AuthenticatedUser
from zeromerma_api.modules.identity.application.services import user_can_access_surface
from zeromerma_api.modules.identity.domain.constants import IDENTITY_SURFACE_BACKOFFICE
from zeromerma_api.modules.identity.presentation.dependencies import get_current_user
from zeromerma_api.modules.suppliers.application.admin_schemas import (
    AdminSupplierBranchRequest,
    AdminSupplierContactRequest,
    AdminSupplierCreateRequest,
    AdminSupplierDetailView,
    AdminSupplierListResponse,
    AdminSupplierProductRequest,
    AdminSupplierStatusRequest,
    AdminSupplierUpdateRequest,
)
from zeromerma_api.modules.suppliers.application.admin_services import AdminSupplierService
from zeromerma_api.modules.suppliers.domain.exceptions import (
    SupplierNotFoundError,
    SupplierValidationError,
)

admin_router = APIRouter(prefix="/v1/admin/suppliers", tags=["admin-suppliers"])


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
    if isinstance(error, SupplierNotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error))
    if isinstance(error, SupplierValidationError):
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error))
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Unexpected supplier error.",
    )


@admin_router.get("", response_model=AdminSupplierListResponse)
def list_admin_suppliers(
    current_user: Annotated[AuthenticatedUser, Depends(_require_backoffice_user)],
    session: Annotated[Session, Depends(get_session)],
    branch_id: Annotated[UUID | None, Query()] = None,
    category: Annotated[str | None, Query(min_length=1)] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 25,
    product_kind: Annotated[str | None, Query(min_length=1)] = None,
    search: Annotated[str | None, Query(min_length=1)] = None,
    status_filter: Annotated[str | None, Query(alias="status")] = None,
    warning_state: Annotated[str | None, Query(min_length=1)] = None,
) -> AdminSupplierListResponse:
    _ = current_user
    try:
        return AdminSupplierService().list_suppliers(
            session,
            branch_id=branch_id,
            category=category,
            page=page,
            page_size=page_size,
            product_kind=product_kind,
            search=search,
            status_filter=status_filter,
            warning_state=warning_state,
        )
    except (SupplierNotFoundError, SupplierValidationError) as error:
        raise _to_http_exception(error) from error


@admin_router.get("/{supplier_id}", response_model=AdminSupplierDetailView)
def get_admin_supplier_detail(
    supplier_id: UUID,
    current_user: Annotated[AuthenticatedUser, Depends(_require_backoffice_user)],
    session: Annotated[Session, Depends(get_session)],
) -> AdminSupplierDetailView:
    _ = current_user
    try:
        return AdminSupplierService().get_supplier_detail(session, supplier_id=supplier_id)
    except (SupplierNotFoundError, SupplierValidationError) as error:
        raise _to_http_exception(error) from error


@admin_router.post("", response_model=AdminSupplierDetailView, status_code=status.HTTP_201_CREATED)
def create_admin_supplier(
    command: AdminSupplierCreateRequest,
    current_user: Annotated[AuthenticatedUser, Depends(_require_backoffice_user)],
    session: Annotated[Session, Depends(get_session)],
    request_id: Annotated[str | None, Header(alias="X-Request-ID")] = None,
) -> AdminSupplierDetailView:
    try:
        return AdminSupplierService().create_supplier(
            session,
            command=command,
            current_user=current_user,
            request_id=request_id,
        )
    except (SupplierNotFoundError, SupplierValidationError) as error:
        raise _to_http_exception(error) from error


@admin_router.patch("/{supplier_id}", response_model=AdminSupplierDetailView)
def update_admin_supplier(
    supplier_id: UUID,
    command: AdminSupplierUpdateRequest,
    current_user: Annotated[AuthenticatedUser, Depends(_require_backoffice_user)],
    session: Annotated[Session, Depends(get_session)],
    request_id: Annotated[str | None, Header(alias="X-Request-ID")] = None,
) -> AdminSupplierDetailView:
    try:
        return AdminSupplierService().update_supplier(
            session,
            command=command,
            current_user=current_user,
            request_id=request_id,
            supplier_id=supplier_id,
        )
    except (SupplierNotFoundError, SupplierValidationError) as error:
        raise _to_http_exception(error) from error


@admin_router.post("/{supplier_id}/status", response_model=AdminSupplierDetailView)
def change_admin_supplier_status(
    supplier_id: UUID,
    command: AdminSupplierStatusRequest,
    current_user: Annotated[AuthenticatedUser, Depends(_require_backoffice_user)],
    session: Annotated[Session, Depends(get_session)],
    request_id: Annotated[str | None, Header(alias="X-Request-ID")] = None,
) -> AdminSupplierDetailView:
    try:
        return AdminSupplierService().change_status(
            session,
            command=command,
            current_user=current_user,
            request_id=request_id,
            supplier_id=supplier_id,
        )
    except (SupplierNotFoundError, SupplierValidationError) as error:
        raise _to_http_exception(error) from error


@admin_router.post(
    "/{supplier_id}/contacts",
    response_model=AdminSupplierDetailView,
    status_code=status.HTTP_201_CREATED,
)
def create_admin_supplier_contact(
    supplier_id: UUID,
    command: AdminSupplierContactRequest,
    current_user: Annotated[AuthenticatedUser, Depends(_require_backoffice_user)],
    session: Annotated[Session, Depends(get_session)],
    request_id: Annotated[str | None, Header(alias="X-Request-ID")] = None,
) -> AdminSupplierDetailView:
    try:
        return AdminSupplierService().create_contact(
            session,
            command=command,
            current_user=current_user,
            request_id=request_id,
            supplier_id=supplier_id,
        )
    except (SupplierNotFoundError, SupplierValidationError) as error:
        raise _to_http_exception(error) from error


@admin_router.patch("/{supplier_id}/contacts/{contact_id}", response_model=AdminSupplierDetailView)
def update_admin_supplier_contact(
    supplier_id: UUID,
    contact_id: UUID,
    command: AdminSupplierContactRequest,
    current_user: Annotated[AuthenticatedUser, Depends(_require_backoffice_user)],
    session: Annotated[Session, Depends(get_session)],
    request_id: Annotated[str | None, Header(alias="X-Request-ID")] = None,
) -> AdminSupplierDetailView:
    try:
        return AdminSupplierService().update_contact(
            session,
            command=command,
            contact_id=contact_id,
            current_user=current_user,
            request_id=request_id,
            supplier_id=supplier_id,
        )
    except (SupplierNotFoundError, SupplierValidationError) as error:
        raise _to_http_exception(error) from error


@admin_router.post(
    "/{supplier_id}/products",
    response_model=AdminSupplierDetailView,
    status_code=status.HTTP_201_CREATED,
)
def upsert_admin_supplier_product(
    supplier_id: UUID,
    command: AdminSupplierProductRequest,
    current_user: Annotated[AuthenticatedUser, Depends(_require_backoffice_user)],
    session: Annotated[Session, Depends(get_session)],
    request_id: Annotated[str | None, Header(alias="X-Request-ID")] = None,
) -> AdminSupplierDetailView:
    try:
        return AdminSupplierService().upsert_product_relation(
            session,
            command=command,
            current_user=current_user,
            request_id=request_id,
            supplier_id=supplier_id,
        )
    except (SupplierNotFoundError, SupplierValidationError) as error:
        raise _to_http_exception(error) from error


@admin_router.patch("/{supplier_id}/products/{relation_id}", response_model=AdminSupplierDetailView)
def update_admin_supplier_product(
    supplier_id: UUID,
    relation_id: UUID,
    command: AdminSupplierProductRequest,
    current_user: Annotated[AuthenticatedUser, Depends(_require_backoffice_user)],
    session: Annotated[Session, Depends(get_session)],
    request_id: Annotated[str | None, Header(alias="X-Request-ID")] = None,
) -> AdminSupplierDetailView:
    try:
        return AdminSupplierService().update_product_relation(
            session,
            command=command,
            current_user=current_user,
            relation_id=relation_id,
            request_id=request_id,
            supplier_id=supplier_id,
        )
    except (SupplierNotFoundError, SupplierValidationError) as error:
        raise _to_http_exception(error) from error


@admin_router.post(
    "/{supplier_id}/branches",
    response_model=AdminSupplierDetailView,
    status_code=status.HTTP_201_CREATED,
)
def upsert_admin_supplier_branch(
    supplier_id: UUID,
    command: AdminSupplierBranchRequest,
    current_user: Annotated[AuthenticatedUser, Depends(_require_backoffice_user)],
    session: Annotated[Session, Depends(get_session)],
    request_id: Annotated[str | None, Header(alias="X-Request-ID")] = None,
) -> AdminSupplierDetailView:
    try:
        return AdminSupplierService().upsert_branch_relation(
            session,
            command=command,
            current_user=current_user,
            request_id=request_id,
            supplier_id=supplier_id,
        )
    except (SupplierNotFoundError, SupplierValidationError) as error:
        raise _to_http_exception(error) from error

