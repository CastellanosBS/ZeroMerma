from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from zeromerma_api.db.session import get_session
from zeromerma_api.modules.catalog.application.admin_schemas import (
    AdminPriceDetailView,
    AdminPricesListResponse,
    AdminPriceUpdateRequest,
    AdminProductAvailabilityRequest,
    AdminProductClassCreateRequest,
    AdminProductClassesListResponse,
    AdminProductClassUpdateRequest,
    AdminProductClassView,
    AdminProductCreateRequest,
    AdminProductsListResponse,
    AdminProductUpdateRequest,
    AdminProductView,
    AdminRecipeCostDetailView,
    AdminRecipeCostsListResponse,
    AdminRecipeCreateRequest,
    AdminRecipeDuplicateRequest,
)
from zeromerma_api.modules.catalog.application.admin_services import (
    AdminPriceCatalogService,
    AdminProductCatalogService,
    AdminProductClassCatalogService,
    AdminProductValidationError,
    AdminRecipeCostCatalogService,
)
from zeromerma_api.modules.catalog.application.inputs_supplies_schemas import (
    AdminInputSupplyCreateRequest,
    AdminInputSupplyDetailView,
    AdminInputSupplyListResponse,
    AdminInputSupplyStatusRequest,
    AdminInputSupplySupplierRelationRequest,
    AdminInputSupplyUpdateRequest,
)
from zeromerma_api.modules.catalog.application.inputs_supplies_services import (
    AdminInputSupplyService,
    AdminInputSupplyValidationError,
)
from zeromerma_api.modules.catalog.domain.exceptions import (
    CatalogError,
    ProductClassNotFoundError,
    ProductNotFoundError,
    RecipeNotFoundError,
)
from zeromerma_api.modules.identity.application.schemas import AuthenticatedUser
from zeromerma_api.modules.identity.application.services import user_can_access_surface
from zeromerma_api.modules.identity.domain.constants import IDENTITY_SURFACE_BACKOFFICE
from zeromerma_api.modules.identity.presentation.dependencies import get_current_user

router = APIRouter(prefix="/v1/admin/products", tags=["admin-products"])
product_classes_router = APIRouter(
    prefix="/v1/admin/product-classes",
    tags=["admin-product-classes"],
)
recipes_costs_router = APIRouter(
    prefix="/v1/admin/recipes-costs",
    tags=["admin-recipes-costs"],
)
prices_router = APIRouter(prefix="/v1/admin/prices", tags=["admin-prices"])
inputs_supplies_router = APIRouter(
    prefix="/v1/admin/inputs-supplies",
    tags=["admin-inputs-supplies"],
)


def _require_backoffice_user(current_user: AuthenticatedUser) -> None:
    if not user_can_access_surface(current_user, IDENTITY_SURFACE_BACKOFFICE):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Backoffice access is required.",
        )


def _to_http_exception(error: Exception) -> HTTPException:
    if isinstance(error, (ProductClassNotFoundError, ProductNotFoundError, RecipeNotFoundError)):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error))
    if isinstance(error, (AdminProductValidationError, AdminInputSupplyValidationError)):
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error))
    if isinstance(error, CatalogError):
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error))
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error))


@inputs_supplies_router.get("", response_model=AdminInputSupplyListResponse)
def list_admin_inputs_supplies(
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
    class_id: UUID | None = None,
    cost_state: Annotated[str | None, Query(min_length=1)] = None,
    inventory_tracked: bool | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 25,
    product_kind: Annotated[str | None, Query(min_length=1)] = None,
    purchasable: bool | None = None,
    recipe_usage: Annotated[str | None, Query(min_length=1)] = None,
    search: Annotated[str | None, Query(min_length=1)] = None,
    status_filter: Annotated[str | None, Query(alias="status", min_length=1)] = None,
    stock_state: Annotated[str | None, Query(min_length=1)] = None,
    supplier_id: UUID | None = None,
    usage_type: Annotated[str | None, Query(min_length=1)] = None,
    warning_state: Annotated[str | None, Query(min_length=1)] = None,
    without_supplier: bool | None = None,
) -> AdminInputSupplyListResponse:
    _require_backoffice_user(current_user)
    try:
        return AdminInputSupplyService().list_items(
            session,
            class_id=class_id,
            cost_state=cost_state,
            inventory_tracked=inventory_tracked,
            page=page,
            page_size=page_size,
            product_kind=product_kind,
            purchasable=purchasable,
            recipe_usage=recipe_usage,
            search=search,
            status_filter=status_filter,
            stock_state=stock_state,
            supplier_id=supplier_id,
            usage_type=usage_type,
            warning_state=warning_state,
            without_supplier=without_supplier,
        )
    except CatalogError as error:
        raise _to_http_exception(error) from error


@inputs_supplies_router.get("/{product_id}", response_model=AdminInputSupplyDetailView)
def get_admin_input_supply_detail(
    product_id: UUID,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> AdminInputSupplyDetailView:
    _require_backoffice_user(current_user)
    try:
        return AdminInputSupplyService().get_item_detail(session, product_id=product_id)
    except CatalogError as error:
        raise _to_http_exception(error) from error


@inputs_supplies_router.post(
    "",
    response_model=AdminInputSupplyDetailView,
    status_code=status.HTTP_201_CREATED,
)
def create_admin_input_supply(
    payload: AdminInputSupplyCreateRequest,
    request: Request,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> AdminInputSupplyDetailView:
    _require_backoffice_user(current_user)
    try:
        return AdminInputSupplyService().create_item(
            session,
            command=payload,
            current_user=current_user,
            request_id=request.headers.get("X-Request-ID"),
        )
    except CatalogError as error:
        raise _to_http_exception(error) from error


@inputs_supplies_router.patch("/{product_id}", response_model=AdminInputSupplyDetailView)
def update_admin_input_supply(
    product_id: UUID,
    payload: AdminInputSupplyUpdateRequest,
    request: Request,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> AdminInputSupplyDetailView:
    _require_backoffice_user(current_user)
    try:
        return AdminInputSupplyService().update_item(
            session,
            command=payload,
            current_user=current_user,
            product_id=product_id,
            request_id=request.headers.get("X-Request-ID"),
        )
    except CatalogError as error:
        raise _to_http_exception(error) from error


@inputs_supplies_router.post("/{product_id}/status", response_model=AdminInputSupplyDetailView)
def change_admin_input_supply_status(
    product_id: UUID,
    payload: AdminInputSupplyStatusRequest,
    request: Request,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> AdminInputSupplyDetailView:
    _require_backoffice_user(current_user)
    try:
        return AdminInputSupplyService().change_status(
            session,
            command=payload,
            current_user=current_user,
            product_id=product_id,
            request_id=request.headers.get("X-Request-ID"),
        )
    except CatalogError as error:
        raise _to_http_exception(error) from error


@inputs_supplies_router.post(
    "/{product_id}/suppliers",
    response_model=AdminInputSupplyDetailView,
    status_code=status.HTTP_201_CREATED,
)
def upsert_admin_input_supply_supplier(
    product_id: UUID,
    payload: AdminInputSupplySupplierRelationRequest,
    request: Request,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> AdminInputSupplyDetailView:
    _require_backoffice_user(current_user)
    try:
        return AdminInputSupplyService().upsert_supplier_relation(
            session,
            command=payload,
            current_user=current_user,
            product_id=product_id,
            request_id=request.headers.get("X-Request-ID"),
        )
    except CatalogError as error:
        raise _to_http_exception(error) from error


@inputs_supplies_router.patch(
    "/{product_id}/suppliers/{relation_id}",
    response_model=AdminInputSupplyDetailView,
)
def update_admin_input_supply_supplier(
    product_id: UUID,
    relation_id: UUID,
    payload: AdminInputSupplySupplierRelationRequest,
    request: Request,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> AdminInputSupplyDetailView:
    _require_backoffice_user(current_user)
    try:
        return AdminInputSupplyService().update_supplier_relation(
            session,
            command=payload,
            current_user=current_user,
            product_id=product_id,
            relation_id=relation_id,
            request_id=request.headers.get("X-Request-ID"),
        )
    except CatalogError as error:
        raise _to_http_exception(error) from error


@router.get("", response_model=AdminProductsListResponse)
def list_admin_products(
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
    brand_id: UUID | None = None,
    branch_id: UUID | None = None,
    status_filter: Annotated[str | None, Query(alias="status", min_length=1)] = None,
    class_id: UUID | None = None,
    capture_mode: Annotated[str | None, Query(min_length=1)] = None,
    readiness: Annotated[str | None, Query(min_length=1)] = None,
    search: Annotated[str | None, Query(min_length=1)] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 25,
) -> AdminProductsListResponse:
    _require_backoffice_user(current_user)
    try:
        return AdminProductCatalogService().list_products(
            session,
            brand_id=brand_id,
            branch_id=branch_id,
            status_filter=status_filter,
            class_id=class_id,
            capture_mode=capture_mode,
            readiness=readiness,
            search=search,
            page=page,
            page_size=page_size,
        )
    except CatalogError as error:
        raise _to_http_exception(error) from error


@router.get("/{product_id}", response_model=AdminProductView)
def get_admin_product_detail(
    product_id: UUID,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> AdminProductView:
    _require_backoffice_user(current_user)
    try:
        return AdminProductCatalogService().get_product_detail(session, product_id=product_id)
    except CatalogError as error:
        raise _to_http_exception(error) from error


@router.post("", response_model=AdminProductView, status_code=status.HTTP_201_CREATED)
def create_admin_product(
    payload: AdminProductCreateRequest,
    request: Request,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> AdminProductView:
    _require_backoffice_user(current_user)
    try:
        return AdminProductCatalogService().create_product(
            session,
            current_user=current_user,
            command=payload,
            request_id=request.headers.get("X-Request-ID"),
        )
    except CatalogError as error:
        raise _to_http_exception(error) from error


@router.patch("/{product_id}", response_model=AdminProductView)
def update_admin_product(
    product_id: UUID,
    payload: AdminProductUpdateRequest,
    request: Request,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> AdminProductView:
    _require_backoffice_user(current_user)
    try:
        return AdminProductCatalogService().update_product(
            session,
            current_user=current_user,
            product_id=product_id,
            command=payload,
            request_id=request.headers.get("X-Request-ID"),
        )
    except CatalogError as error:
        raise _to_http_exception(error) from error


@router.post("/{product_id}/availability", response_model=AdminProductView)
def configure_admin_product_availability(
    product_id: UUID,
    payload: AdminProductAvailabilityRequest,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
) -> AdminProductView:
    _require_backoffice_user(current_user)
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail=(
            "Product branch availability is pending a canonical product-branch availability schema."
        ),
    )


@product_classes_router.get("", response_model=AdminProductClassesListResponse)
def list_admin_product_classes(
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
    brand_id: UUID | None = None,
    status_filter: Annotated[str | None, Query(alias="status", min_length=1)] = None,
    capture_mode: Annotated[str | None, Query(min_length=1)] = None,
    product_presence: Annotated[str | None, Query(min_length=1)] = None,
    search: Annotated[str | None, Query(min_length=1)] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 25,
) -> AdminProductClassesListResponse:
    _require_backoffice_user(current_user)
    try:
        return AdminProductClassCatalogService().list_classes(
            session,
            brand_id=brand_id,
            status_filter=status_filter,
            capture_mode=capture_mode,
            product_presence=product_presence,
            search=search,
            page=page,
            page_size=page_size,
        )
    except CatalogError as error:
        raise _to_http_exception(error) from error


@product_classes_router.get("/{class_id}", response_model=AdminProductClassView)
def get_admin_product_class_detail(
    class_id: UUID,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> AdminProductClassView:
    _require_backoffice_user(current_user)
    try:
        return AdminProductClassCatalogService().get_class_detail(session, class_id=class_id)
    except CatalogError as error:
        raise _to_http_exception(error) from error


@product_classes_router.post(
    "", response_model=AdminProductClassView, status_code=status.HTTP_201_CREATED
)
def create_admin_product_class(
    payload: AdminProductClassCreateRequest,
    request: Request,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> AdminProductClassView:
    _require_backoffice_user(current_user)
    try:
        return AdminProductClassCatalogService().create_class(
            session,
            current_user=current_user,
            command=payload,
            request_id=request.headers.get("X-Request-ID"),
        )
    except CatalogError as error:
        raise _to_http_exception(error) from error


@product_classes_router.patch("/{class_id}", response_model=AdminProductClassView)
def update_admin_product_class(
    class_id: UUID,
    payload: AdminProductClassUpdateRequest,
    request: Request,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> AdminProductClassView:
    _require_backoffice_user(current_user)
    try:
        return AdminProductClassCatalogService().update_class(
            session,
            current_user=current_user,
            class_id=class_id,
            command=payload,
            request_id=request.headers.get("X-Request-ID"),
        )
    except CatalogError as error:
        raise _to_http_exception(error) from error


@prices_router.get("", response_model=AdminPricesListResponse)
def list_admin_prices(
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
    brand_id: UUID | None = None,
    class_id: UUID | None = None,
    entity_type: Annotated[str | None, Query(min_length=1)] = None,
    capture_mode: Annotated[str | None, Query(min_length=1)] = None,
    status_filter: Annotated[str | None, Query(alias="status", min_length=1)] = None,
    price_health: Annotated[str | None, Query(min_length=1)] = None,
    updated_from: datetime | None = None,
    updated_to: datetime | None = None,
    search: Annotated[str | None, Query(min_length=1)] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 25,
) -> AdminPricesListResponse:
    _require_backoffice_user(current_user)
    try:
        return AdminPriceCatalogService().list_prices(
            session,
            brand_id=brand_id,
            class_id=class_id,
            entity_type=entity_type,
            capture_mode=capture_mode,
            status_filter=status_filter,
            price_health=price_health,
            updated_from=updated_from,
            updated_to=updated_to,
            search=search,
            page=page,
            page_size=page_size,
        )
    except CatalogError as error:
        raise _to_http_exception(error) from error


@prices_router.get("/{entity_type}/{entity_id}", response_model=AdminPriceDetailView)
def get_admin_price_detail(
    entity_type: str,
    entity_id: UUID,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> AdminPriceDetailView:
    _require_backoffice_user(current_user)
    try:
        return AdminPriceCatalogService().get_price_detail(
            session,
            entity_type=entity_type,
            entity_id=entity_id,
        )
    except CatalogError as error:
        raise _to_http_exception(error) from error


@prices_router.patch("/{entity_type}/{entity_id}", response_model=AdminPriceDetailView)
def update_admin_price(
    entity_type: str,
    entity_id: UUID,
    payload: AdminPriceUpdateRequest,
    request: Request,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> AdminPriceDetailView:
    _require_backoffice_user(current_user)
    try:
        return AdminPriceCatalogService().update_price(
            session,
            current_user=current_user,
            entity_type=entity_type,
            entity_id=entity_id,
            command=payload,
            request_id=request.headers.get("X-Request-ID"),
        )
    except CatalogError as error:
        raise _to_http_exception(error) from error


@recipes_costs_router.get("/products", response_model=AdminRecipeCostsListResponse)
def list_admin_recipe_cost_products(
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
    brand_id: UUID | None = None,
    class_id: UUID | None = None,
    recipe_state: Annotated[str | None, Query(min_length=1)] = None,
    search: Annotated[str | None, Query(min_length=1)] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 25,
) -> AdminRecipeCostsListResponse:
    _require_backoffice_user(current_user)
    try:
        return AdminRecipeCostCatalogService().list_recipe_costs(
            session,
            brand_id=brand_id,
            class_id=class_id,
            recipe_state=recipe_state,
            search=search,
            page=page,
            page_size=page_size,
        )
    except CatalogError as error:
        raise _to_http_exception(error) from error


@recipes_costs_router.get("/products/{product_id}", response_model=AdminRecipeCostDetailView)
def get_admin_recipe_cost_product_detail(
    product_id: UUID,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> AdminRecipeCostDetailView:
    _require_backoffice_user(current_user)
    try:
        return AdminRecipeCostCatalogService().get_product_recipe_detail(
            session,
            product_id=product_id,
        )
    except CatalogError as error:
        raise _to_http_exception(error) from error


@recipes_costs_router.post(
    "/recipes", response_model=AdminRecipeCostDetailView, status_code=status.HTTP_201_CREATED
)
def create_admin_recipe(
    payload: AdminRecipeCreateRequest,
    request: Request,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> AdminRecipeCostDetailView:
    _require_backoffice_user(current_user)
    try:
        return AdminRecipeCostCatalogService().create_recipe(
            session,
            current_user=current_user,
            command=payload,
            request_id=request.headers.get("X-Request-ID"),
        )
    except CatalogError as error:
        raise _to_http_exception(error) from error


@recipes_costs_router.post(
    "/recipes/{recipe_id}/activate", response_model=AdminRecipeCostDetailView
)
def activate_admin_recipe(
    recipe_id: UUID,
    request: Request,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> AdminRecipeCostDetailView:
    _require_backoffice_user(current_user)
    try:
        return AdminRecipeCostCatalogService().activate_recipe(
            session,
            current_user=current_user,
            recipe_id=recipe_id,
            request_id=request.headers.get("X-Request-ID"),
        )
    except CatalogError as error:
        raise _to_http_exception(error) from error


@recipes_costs_router.post(
    "/recipes/{recipe_id}/duplicate", response_model=AdminRecipeCostDetailView
)
def duplicate_admin_recipe(
    recipe_id: UUID,
    payload: AdminRecipeDuplicateRequest,
    request: Request,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> AdminRecipeCostDetailView:
    _require_backoffice_user(current_user)
    try:
        return AdminRecipeCostCatalogService().duplicate_recipe(
            session,
            current_user=current_user,
            recipe_id=recipe_id,
            command=payload,
            request_id=request.headers.get("X-Request-ID"),
        )
    except CatalogError as error:
        raise _to_http_exception(error) from error


@recipes_costs_router.post(
    "/recipes/{recipe_id}/apply-standard-cost", response_model=AdminRecipeCostDetailView
)
def apply_admin_recipe_standard_cost(
    recipe_id: UUID,
    request: Request,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> AdminRecipeCostDetailView:
    _require_backoffice_user(current_user)
    try:
        return AdminRecipeCostCatalogService().apply_recipe_cost_to_product(
            session,
            current_user=current_user,
            recipe_id=recipe_id,
            request_id=request.headers.get("X-Request-ID"),
        )
    except CatalogError as error:
        raise _to_http_exception(error) from error

