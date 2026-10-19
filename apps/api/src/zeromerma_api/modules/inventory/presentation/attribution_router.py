from __future__ import annotations

from dataclasses import replace
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session

from zeromerma_api.db.session import get_session
from zeromerma_api.modules.idempotency.application.service import IdempotencyExecutor
from zeromerma_api.modules.idempotency.presentation.http import (
    idempotency_response,
    require_idempotency_key,
)
from zeromerma_api.modules.identity.application.schemas import AuthenticatedUser
from zeromerma_api.modules.identity.presentation.dependencies import get_current_user
from zeromerma_api.modules.inventory.application.attribution_commands import (
    OPERATION,
    POLICY,
    commit_class_attribution,
)
from zeromerma_api.modules.inventory.application.attribution_schemas import (
    ClassAttributionRequest,
    ClassAttributionResult,
)
from zeromerma_api.modules.sales.application.idempotency import SaleConfirmationService
from zeromerma_api.presentation.errors import error_responses

router = APIRouter(prefix="/v1/sales", tags=["inventory-attribution"])


@router.post(
    "/{sale_id}/attribute-inventory",
    response_model=ClassAttributionResult,
    responses={
        **error_responses(),
        200: {
            "headers": {
                "Idempotency-Replayed": {"$ref": "#/components/headers/IdempotencyReplayed"}
            }
        },
    },
)
def attribute_inventory(
    sale_id: UUID,
    payload: ClassAttributionRequest,
    request: Request,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
    key: Annotated[UUID, Depends(require_idempotency_key)],
) -> Response:
    return idempotency_response(
        commit_class_attribution(
            session,
            current_user=current_user,
            sale_id=sale_id,
            command=payload,
            key=key,
            request_id=request.headers.get("X-Request-ID"),
        ),
        request,
    )


@router.get(
    "/{sale_id}/inventory-attributions/{idempotency_key}", response_model=ClassAttributionResult
)
def recover_attribution(
    sale_id: UUID,
    idempotency_key: UUID,
    workstation_code: str,
    cash_session_id: UUID,
    request: Request,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> Response:
    result = IdempotencyExecutor().recover(
        session,
        key=idempotency_key,
        operation_code=OPERATION,
        resolve_context=lambda current, _: SaleConfirmationService._request_context(
            current,
            current_user=current_user,
            workstation_code=workstation_code,
            cash_session_id=cash_session_id,
        ),
        authorize=lambda current, context: SaleConfirmationService._authorize(
            current, current_user, context
        ),
        response_policy=POLICY,
    )
    if result.status == "COMPLETED" and result.payload.get("sale_id") != str(sale_id):
        raise HTTPException(404, "Attribution does not belong to this sale.")
    return idempotency_response(
        replace(result, status_code=200) if result.status == "COMPLETED" else result, request
    )
