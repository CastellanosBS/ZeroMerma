from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import Response
from sqlalchemy.orm import Session

from zeromerma_api.db.session import get_session
from zeromerma_api.modules.hardware.application.schemas import (
    HardwareBootstrapView,
    HardwareCommandAcknowledgement,
    HardwareCommandRequest,
)
from zeromerma_api.modules.hardware.application.services import HardwareService
from zeromerma_api.modules.idempotency.presentation.http import (
    idempotency_response,
    require_idempotency_key,
)
from zeromerma_api.modules.identity.application.schemas import AuthenticatedUser
from zeromerma_api.modules.identity.presentation.dependencies import get_current_user
from zeromerma_api.presentation.errors import error_responses

router = APIRouter(prefix="/v1/hardware", tags=["hardware"], responses=error_responses())


def hardware_service() -> HardwareService:
    return HardwareService()


@router.get("/bootstrap", response_model=HardwareBootstrapView)
def bootstrap(
    workstation_code: Annotated[str, Query(min_length=1)],
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
    service: Annotated[HardwareService, Depends(hardware_service)],
) -> HardwareBootstrapView:
    return service.bootstrap(session, current_user, workstation_code)


@router.post("/commands", response_model=HardwareCommandAcknowledgement)
def request_command(
    command: HardwareCommandRequest,
    request: Request,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
    service: Annotated[HardwareService, Depends(hardware_service)],
    key: Annotated[UUID, Depends(require_idempotency_key)],
) -> Response:
    return idempotency_response(
        service.admit(
            session,
            user=current_user,
            command=command,
            key=key,
            request_id=request.headers.get("X-Request-ID"),
        ),
        request,
    )


@router.get("/commands/{command_id}/authorization", response_model=HardwareCommandAcknowledgement)
def renew_authorization(
    command_id: UUID,
    workstation_code: Annotated[str, Query(min_length=1)],
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
    service: Annotated[HardwareService, Depends(hardware_service)],
) -> HardwareCommandAcknowledgement:
    return service.renew_authorization(
        session, user=current_user, command_id=command_id, workstation_code=workstation_code
    )


@router.get("/commands/by-key/{idempotency_key}", response_model=HardwareCommandAcknowledgement)
def recover_command(
    idempotency_key: UUID,
    workstation_code: Annotated[str, Query(min_length=1)],
    request: Request,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
    service: Annotated[HardwareService, Depends(hardware_service)],
) -> Response:
    return idempotency_response(
        service.recover(
            session, user=current_user, key=idempotency_key, workstation_code=workstation_code
        ),
        request,
    )
