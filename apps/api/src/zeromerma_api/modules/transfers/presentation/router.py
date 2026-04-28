from __future__ import annotations

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
from zeromerma_api.modules.catalog.domain.exceptions import CatalogError, ProductNotFoundError
from zeromerma_api.modules.identity.application.schemas import AuthenticatedUser
from zeromerma_api.modules.identity.presentation.dependencies import get_current_user
from zeromerma_api.modules.operations.domain.exceptions import (
    OperationDocumentNotFoundError,
    OperationError,
)
from zeromerma_api.modules.transfers.application.schemas import (
    PendingInboundTransfersResponse,
    TransferDetailResponse,
    TransferDispatchCommitRequest,
    TransferDispatchHistoryResponse,
    TransferReceiptHistoryResponse,
    TransferReceiveRequest,
)
from zeromerma_api.modules.transfers.application.services import (
    TransferCommandService,
    TransferQueryService,
)
from zeromerma_api.modules.transfers.domain.exceptions import (
    TransferAlreadyReceivedError,
    TransferError,
    TransferNotFoundError,
    TransferValidationError,
)

router = APIRouter(prefix="/v1/transfers", tags=["transfers"])


def _to_http_exception(error: Exception) -> HTTPException:
    if isinstance(
        error,
        (
            WorkstationNotFoundError,
            ProductNotFoundError,
            OperationDocumentNotFoundError,
            TransferNotFoundError,
        ),
    ):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error))

    if isinstance(error, BranchAssignmentRequiredError):
        return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(error))

    if isinstance(
        error,
        (
            BranchInactiveError,
            WorkstationInactiveError,
            TransferAlreadyReceivedError,
        ),
    ):
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error))

    if isinstance(
        error,
        (
            BranchAccessError,
            CatalogError,
            OperationError,
            TransferValidationError,
            TransferError,
        ),
    ):
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error))

    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error))


@router.post(
    "/dispatch/commit",
    response_model=TransferDetailResponse,
    status_code=status.HTTP_201_CREATED,
)
def commit_transfer_dispatch(
    payload: TransferDispatchCommitRequest,
    request: Request,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> TransferDetailResponse:
    try:
        return TransferCommandService().commit_dispatch(
            session,
            current_user=current_user,
            command=payload,
            request_id=request.headers.get("X-Request-ID"),
        )
    except (BranchAccessError, CatalogError, OperationError, TransferError) as error:
        raise _to_http_exception(error) from error


@router.get("/inbound/pending", response_model=PendingInboundTransfersResponse)
def get_pending_inbound_transfers(
    workstation_code: Annotated[str, Query(min_length=1)],
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> PendingInboundTransfersResponse:
    try:
        return TransferQueryService().get_pending_inbound_transfers(
            session,
            current_user=current_user,
            workstation_code=workstation_code,
        )
    except (BranchAccessError, CatalogError, OperationError, TransferError) as error:
        raise _to_http_exception(error) from error


@router.get("/outbound/history", response_model=TransferDispatchHistoryResponse)
def get_outbound_transfer_history(
    workstation_code: Annotated[str, Query(min_length=1)],
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
    scope: Annotated[str | None, Query()] = None,
    created_by_user_id: Annotated[UUID | None, Query()] = None,
    destination_branch_id: Annotated[UUID | None, Query()] = None,
) -> TransferDispatchHistoryResponse:
    try:
        return TransferQueryService().get_outbound_dispatch_history(
            session,
            current_user=current_user,
            workstation_code=workstation_code,
            scope=scope,
            created_by_user_id=created_by_user_id,
            destination_branch_id=destination_branch_id,
        )
    except (BranchAccessError, CatalogError, OperationError, TransferError) as error:
        raise _to_http_exception(error) from error


@router.get("/inbound/history", response_model=TransferReceiptHistoryResponse)
def get_inbound_transfer_history(
    workstation_code: Annotated[str, Query(min_length=1)],
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
    scope: Annotated[str | None, Query()] = None,
    created_by_user_id: Annotated[UUID | None, Query()] = None,
    source_branch_id: Annotated[UUID | None, Query()] = None,
    status_filter: Annotated[str | None, Query(alias="status")] = None,
) -> TransferReceiptHistoryResponse:
    try:
        return TransferQueryService().get_inbound_receipt_history(
            session,
            current_user=current_user,
            workstation_code=workstation_code,
            scope=scope,
            created_by_user_id=created_by_user_id,
            source_branch_id=source_branch_id,
            status=status_filter,
        )
    except (BranchAccessError, CatalogError, OperationError, TransferError) as error:
        raise _to_http_exception(error) from error


@router.get("/{transfer_id}", response_model=TransferDetailResponse)
def get_transfer_detail(
    transfer_id: UUID,
    workstation_code: Annotated[str, Query(min_length=1)],
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> TransferDetailResponse:
    try:
        return TransferQueryService().get_transfer_detail(
            session,
            current_user=current_user,
            workstation_code=workstation_code,
            transfer_id=transfer_id,
        )
    except (BranchAccessError, CatalogError, OperationError, TransferError) as error:
        raise _to_http_exception(error) from error


@router.post("/{transfer_id}/receive", response_model=TransferDetailResponse)
def receive_transfer(
    transfer_id: UUID,
    payload: TransferReceiveRequest,
    request: Request,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> TransferDetailResponse:
    try:
        return TransferCommandService().receive_transfer(
            session,
            current_user=current_user,
            workstation_code=payload.workstation_code,
            transfer_id=transfer_id,
            command=payload,
            request_id=request.headers.get("X-Request-ID"),
        )
    except (BranchAccessError, CatalogError, OperationError, TransferError) as error:
        raise _to_http_exception(error) from error
