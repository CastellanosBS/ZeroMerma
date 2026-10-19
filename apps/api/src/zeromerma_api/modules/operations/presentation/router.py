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
from zeromerma_api.modules.catalog.domain.exceptions import (
    CatalogError,
    ProductClassNotFoundError,
    ProductNotFoundError,
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
from zeromerma_api.modules.identity.presentation.dependencies import get_current_user
from zeromerma_api.modules.operations.application.idempotency import OperationCommitService
from zeromerma_api.modules.operations.application.schemas import (
    CounterTransferCommitRequest,
    OperationCommitResultView,
    OperationDocumentView,
    OperationHistoryResponse,
    OperationsBootstrapResponse,
    OperationsCatalogResponse,
    OperationsClassProductsResponse,
    WasteCommitRequest,
)
from zeromerma_api.modules.operations.application.services import (
    OperationsQueryService,
)
from zeromerma_api.modules.operations.domain.exceptions import (
    OperationDocumentNotFoundError,
    OperationError,
    OperationValidationError,
    WasteReasonNotFoundError,
)
from zeromerma_api.presentation.errors import error_responses

_REPLAY_RESPONSE = {
    "headers": {"Idempotency-Replayed": {"$ref": "#/components/headers/IdempotencyReplayed"}}
}

router = APIRouter(prefix="/v1/operations", tags=["operations"])


def _to_http_exception(error: Exception) -> HTTPException:
    if isinstance(
        error,
        (
            WorkstationNotFoundError,
            ProductClassNotFoundError,
            ProductNotFoundError,
            OperationDocumentNotFoundError,
            WasteReasonNotFoundError,
        ),
    ):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error))

    if isinstance(error, BranchAssignmentRequiredError):
        return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(error))

    if isinstance(error, (BranchInactiveError, WorkstationInactiveError)):
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error))

    if isinstance(
        error,
        (BranchAccessError, CatalogError, OperationValidationError, OperationError),
    ):
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error))

    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error))


@router.get("/bootstrap", response_model=OperationsBootstrapResponse)
def get_operations_bootstrap(
    workstation_code: Annotated[str, Query(min_length=1)],
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> OperationsBootstrapResponse:
    try:
        return OperationsQueryService().get_bootstrap(
            session,
            current_user=current_user,
            workstation_code=workstation_code,
        )
    except (BranchAccessError, CatalogError, OperationError) as error:
        raise _to_http_exception(error) from error


@router.get("/catalog", response_model=OperationsCatalogResponse)
def get_operations_catalog(
    workstation_code: Annotated[str, Query(min_length=1)],
    module: Annotated[str, Query(min_length=1)],
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
    query: Annotated[str | None, Query(min_length=1)] = None,
) -> OperationsCatalogResponse:
    try:
        return OperationsQueryService().get_catalog(
            session,
            current_user=current_user,
            workstation_code=workstation_code,
            module=module,
            query=query,
        )
    except (BranchAccessError, CatalogError, OperationError) as error:
        raise _to_http_exception(error) from error


@router.get("/classes/{class_id}/products", response_model=OperationsClassProductsResponse)
def get_operations_class_products(
    class_id: UUID,
    workstation_code: Annotated[str, Query(min_length=1)],
    module: Annotated[str, Query(min_length=1)],
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
    query: Annotated[str | None, Query(min_length=1)] = None,
) -> OperationsClassProductsResponse:
    try:
        return OperationsQueryService().get_class_products(
            session,
            current_user=current_user,
            workstation_code=workstation_code,
            class_id=class_id,
            module=module,
            query=query,
        )
    except (BranchAccessError, CatalogError, OperationError) as error:
        raise _to_http_exception(error) from error


@router.get("/history", response_model=OperationHistoryResponse)
def get_operations_history(
    workstation_code: Annotated[str, Query(min_length=1)],
    document_type: Annotated[str, Query(min_length=1)],
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
    scope: Annotated[str | None, Query(min_length=1)] = None,
    created_by_user_id: UUID | None = None,
    reason_code: Annotated[str | None, Query(min_length=1)] = None,
    product_id: UUID | None = None,
    source_bucket_code: Annotated[str | None, Query(min_length=1)] = None,
    destination_bucket_code: Annotated[str | None, Query(min_length=1)] = None,
) -> OperationHistoryResponse:
    try:
        return OperationsQueryService().list_operation_history(
            session,
            current_user=current_user,
            workstation_code=workstation_code,
            document_type=document_type,
            scope=scope,
            created_by_user_id=created_by_user_id,
            reason_code=reason_code,
            product_id=product_id,
            source_bucket_code=source_bucket_code,
            destination_bucket_code=destination_bucket_code,
        )
    except (BranchAccessError, CatalogError, OperationError) as error:
        raise _to_http_exception(error) from error


@router.get("/{document_id}", response_model=OperationDocumentView)
def get_operation_document(
    document_id: UUID,
    workstation_code: Annotated[str, Query(min_length=1)],
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> OperationDocumentView:
    try:
        return OperationsQueryService().get_operation_document_for_workstation(
            session,
            current_user=current_user,
            workstation_code=workstation_code,
            document_id=document_id,
        )
    except (BranchAccessError, CatalogError, OperationError) as error:
        raise _to_http_exception(error) from error


@router.post(
    "/counter-transfer/commit",
    response_model=OperationCommitResultView,
    status_code=status.HTTP_201_CREATED,
    responses={201: _REPLAY_RESPONSE, 409: {**error_responses()[409], **_REPLAY_RESPONSE}},
)
def commit_counter_transfer(
    payload: CounterTransferCommitRequest,
    request: Request,
    idempotency_key: Annotated[UUID, Depends(require_idempotency_key)],
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> Response:
    try:
        result = OperationCommitService().commit(
            session,
            current_user=current_user,
            command=payload,
            request_id=request.headers.get("X-Request-ID"),
            key=idempotency_key,
        )
        return idempotency_response(result, request)
    except (BranchAccessError, CatalogError, OperationError) as error:
        raise _to_http_exception(error) from error


@router.post(
    "/waste/commit",
    response_model=OperationCommitResultView,
    status_code=status.HTTP_201_CREATED,
    responses={201: _REPLAY_RESPONSE, 409: {**error_responses()[409], **_REPLAY_RESPONSE}},
)
def commit_waste_record(
    payload: WasteCommitRequest,
    request: Request,
    idempotency_key: Annotated[UUID, Depends(require_idempotency_key)],
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> Response:
    try:
        result = OperationCommitService().commit(
            session,
            current_user=current_user,
            command=payload,
            request_id=request.headers.get("X-Request-ID"),
            key=idempotency_key,
        )
        return idempotency_response(result, request)
    except (BranchAccessError, CatalogError, OperationError) as error:
        raise _to_http_exception(error) from error


@router.get(
    "/counter-transfer/confirmations/{idempotency_key}",
    response_model=OperationCommitResultView,
    responses={200: _REPLAY_RESPONSE, 409: {**error_responses()[409], **_REPLAY_RESPONSE}},
)
def recover_counter_transfer(
    idempotency_key: Annotated[str, Path(pattern=IDEMPOTENCY_KEY_PATTERN)],
    workstation_code: Annotated[str, Query(min_length=1)],
    cash_session_id: UUID,
    request: Request,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> Response:
    result = OperationCommitService().recover(
        session,
        current_user=current_user,
        key=parse_idempotency_key(idempotency_key),
        command_code="counter-transfer",
        workstation_code=workstation_code,
        cash_session_id=cash_session_id,
    )
    if result.status_code < 300:
        result = replace(result, status_code=200)
    return idempotency_response(result, request)


@router.get(
    "/waste/confirmations/{idempotency_key}",
    response_model=OperationCommitResultView,
    responses={200: _REPLAY_RESPONSE, 409: {**error_responses()[409], **_REPLAY_RESPONSE}},
)
def recover_waste(
    idempotency_key: Annotated[str, Path(pattern=IDEMPOTENCY_KEY_PATTERN)],
    workstation_code: Annotated[str, Query(min_length=1)],
    cash_session_id: UUID,
    request: Request,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> Response:
    result = OperationCommitService().recover(
        session,
        current_user=current_user,
        key=parse_idempotency_key(idempotency_key),
        command_code="waste",
        workstation_code=workstation_code,
        cash_session_id=cash_session_id,
    )
    if result.status_code < 300:
        result = replace(result, status_code=200)
    return idempotency_response(result, request)
