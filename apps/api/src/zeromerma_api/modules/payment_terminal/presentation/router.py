from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from fastapi.responses import Response
from sqlalchemy.orm import Session

from zeromerma_api.db.session import get_session
from zeromerma_api.modules.idempotency.presentation.http import (
    idempotency_response,
    require_idempotency_key,
)
from zeromerma_api.modules.identity.application.schemas import AuthenticatedUser
from zeromerma_api.modules.identity.presentation.dependencies import get_current_user
from zeromerma_api.modules.payment_terminal.application.schemas import (
    TerminalBootstrapView,
    TerminalOperationAcknowledgement,
    TerminalOperationRequest,
    TerminalOperationView,
)
from zeromerma_api.modules.payment_terminal.application.services import PaymentTerminalService
from zeromerma_api.presentation.errors import error_responses

router = APIRouter(
    prefix="/v1/payment-terminal",
    tags=["payment-terminal"],
    responses=error_responses(),
)


def terminal_service() -> PaymentTerminalService:
    return PaymentTerminalService()


@router.get("/bootstrap", response_model=TerminalBootstrapView)
def bootstrap(
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
    service: Annotated[PaymentTerminalService, Depends(terminal_service)],
) -> TerminalBootstrapView:
    return service.bootstrap(session, current_user)


@router.post(
    "/operations",
    response_model=TerminalOperationAcknowledgement,
    status_code=202,
    responses={
        202: {
            "headers": {
                "Idempotency-Replayed": {"$ref": "#/components/headers/IdempotencyReplayed"}
            }
        }
    },
)
def request_operation(
    command: TerminalOperationRequest,
    request: Request,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
    service: Annotated[PaymentTerminalService, Depends(terminal_service)],
    key: Annotated[UUID, Depends(require_idempotency_key)],
) -> Response:
    return idempotency_response(
        service.admit(session, current_user=current_user, command=command, key=key), request
    )


@router.get("/operations/{operation_id}", response_model=TerminalOperationView)
def get_operation(
    operation_id: UUID,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
    service: Annotated[PaymentTerminalService, Depends(terminal_service)],
) -> TerminalOperationView:
    return service.get(session, current_user=current_user, operation_id=operation_id)


@router.post("/operations/{operation_id}/dispatch", response_model=TerminalOperationView)
def dispatch(
    operation_id: UUID,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
    service: Annotated[PaymentTerminalService, Depends(terminal_service)],
) -> TerminalOperationView:
    return service.dispatch(session, current_user=current_user, operation_id=operation_id)


@router.post("/operations/{operation_id}/reconcile", response_model=TerminalOperationView)
def reconcile(
    operation_id: UUID,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
    service: Annotated[PaymentTerminalService, Depends(terminal_service)],
) -> TerminalOperationView:
    return service.dispatch(
        session, current_user=current_user, operation_id=operation_id, reconcile_only=True
    )
