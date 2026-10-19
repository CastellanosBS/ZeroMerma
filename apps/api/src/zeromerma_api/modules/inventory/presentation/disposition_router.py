from __future__ import annotations

from dataclasses import replace
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.orm import Session

from zeromerma_api.db.session import get_session
from zeromerma_api.modules.idempotency.application.schemas import CommandContext
from zeromerma_api.modules.idempotency.application.service import IdempotencyExecutor
from zeromerma_api.modules.idempotency.presentation.http import (
    idempotency_response,
    require_idempotency_key,
)
from zeromerma_api.modules.identity.application.schemas import AuthenticatedUser
from zeromerma_api.modules.identity.presentation.dependencies import get_current_user
from zeromerma_api.modules.inventory.application.disposition_schemas import (
    InventoryDispositionRequest,
    InventoryDispositionResult,
)
from zeromerma_api.modules.inventory.application.dispositions import (
    OPERATIONS,
    POLICY,
    authorize_disposition,
    bind_disposition,
    commit_disposition,
)
from zeromerma_api.presentation.errors import error_responses

router = APIRouter(prefix="/v1/admin/inventory-dispositions", tags=["inventory-dispositions"])


@router.post(
    "",
    response_model=InventoryDispositionResult,
    status_code=201,
    responses={
        **error_responses(),
        201: {
            "headers": {
                "Idempotency-Replayed": {"$ref": "#/components/headers/IdempotencyReplayed"}
            }
        },
    },
)
def create_disposition(
    payload: InventoryDispositionRequest,
    request: Request,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
    key: Annotated[UUID, Depends(require_idempotency_key)],
) -> Response:
    return idempotency_response(
        commit_disposition(
            session,
            current_user=current_user,
            command=payload,
            key=key,
            request_id=request.headers.get("X-Request-ID"),
        ),
        request,
    )


@router.get("/confirmations/{idempotency_key}", response_model=InventoryDispositionResult)
def recover_disposition(
    idempotency_key: UUID,
    branch_id: UUID,
    kind: Literal["RETURN_CORRECTION", "QUARANTINE_RELEASE"],
    request: Request,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> Response:
    bind_disposition(session, current_user, kind, mutation=False)
    result = IdempotencyExecutor().recover(
        session,
        key=idempotency_key,
        operation_code=OPERATIONS[kind],
        response_policy=POLICY,
        resolve_context=lambda _current, _saved: CommandContext(
            actor_user_id=current_user.id, surface="BACKOFFICE", branch_id=branch_id
        ),
        authorize=lambda current, context: authorize_disposition(
            current, current_user, context, kind
        ),
    )
    return idempotency_response(
        replace(result, status_code=200) if result.status == "COMPLETED" else result, request
    )
