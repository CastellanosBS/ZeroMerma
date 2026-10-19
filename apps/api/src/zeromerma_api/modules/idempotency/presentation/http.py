from __future__ import annotations

from typing import Annotated, Any
from uuid import UUID

from fastapi import FastAPI, Header, Request
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, ConfigDict, Field, JsonValue, TypeAdapter

from zeromerma_api.modules.idempotency.application.canonicalization import (
    IDEMPOTENCY_KEY_PATTERN,
    parse_idempotency_key,
)
from zeromerma_api.modules.idempotency.application.schemas import IdempotencyResult
from zeromerma_api.modules.idempotency.domain.constants import IdempotencyStatus
from zeromerma_api.modules.idempotency.domain.exceptions import IdempotencyError
from zeromerma_api.presentation.errors import ApiErrorResponse
from zeromerma_api.presentation.operation_context import request_id as _request_id

IdempotencyKeyValue = Annotated[
    str,
    Field(
        min_length=36,
        max_length=36,
        pattern=IDEMPOTENCY_KEY_PATTERN,
        json_schema_extra={"format": "uuid", "x-zeromerma-uuid-version": 7},
        description="One UUIDv7 per business intention, reused for every retry.",
    ),
]


class IdempotencyRejectionSnapshot(BaseModel):
    """Persist only stable error content; request correlation belongs to the current response."""

    model_config = ConfigDict(extra="forbid")

    code: str = Field(min_length=1, max_length=80, pattern=r"^[A-Z][A-Z0-9_]*$")
    message: str = Field(min_length=1, max_length=300)
    details: dict[str, JsonValue] | None = None


def require_idempotency_key(
    request: Request,
    value: Annotated[
        str,
        Header(
            alias="Idempotency-Key",
            min_length=36,
            max_length=36,
            pattern=IDEMPOTENCY_KEY_PATTERN,
            description="A globally unique UUIDv7 identifying this business intention.",
        ),
    ],
) -> UUID:
    if len(request.headers.getlist("Idempotency-Key")) != 1:
        raise IdempotencyError(
            code="IDEMPOTENCY_KEY_INVALID",
            status_code=422,
            message="Exactly one valid Idempotency-Key is required.",
        )
    return parse_idempotency_key(value)


async def idempotency_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    if not isinstance(exc, IdempotencyError):
        raise TypeError("Idempotency handler received an incompatible exception.")
    body = ApiErrorResponse(
        code=exc.code,
        message=exc.message,
        details=None,
        request_id=_request_id(request),
        field_errors=None,
    )
    headers = {"Cache-Control": "no-store"}
    if exc.code == "IDEMPOTENCY_IN_PROGRESS":
        headers["Retry-After"] = "1"
    return JSONResponse(
        status_code=exc.status_code, content=body.model_dump(mode="json"), headers=headers
    )


def idempotency_response(result: IdempotencyResult, request: Request) -> Response:
    headers = {
        "Cache-Control": "no-store",
        "Idempotency-Replayed": "true" if result.replayed else "false",
    }
    if result.status_code in {204, 205}:
        return Response(status_code=result.status_code, headers=headers)
    payload: Any = result.payload
    if result.status == IdempotencyStatus.REJECTED:
        snapshot = IdempotencyRejectionSnapshot.model_validate(result.payload)
        payload = ApiErrorResponse(
            code=snapshot.code,
            message=snapshot.message,
            details=snapshot.details,
            request_id=_request_id(request),
            field_errors=None,
        ).model_dump(mode="json")
    return JSONResponse(status_code=result.status_code, content=payload, headers=headers)


def install_idempotency_error_handler(app: FastAPI) -> None:
    app.add_exception_handler(IdempotencyError, idempotency_exception_handler)


def add_idempotency_contract(schema: dict[str, Any]) -> None:
    """Publish reusable contracts without advertising adoption by existing business routes."""
    components = schema.setdefault("components", {})
    schemas = components.setdefault("schemas", {})
    schemas["IdempotencyKey"] = TypeAdapter(IdempotencyKeyValue).json_schema()
    schemas["IdempotencyStatus"] = TypeAdapter(IdempotencyStatus).json_schema()
    rejection = IdempotencyRejectionSnapshot.model_json_schema(
        ref_template="#/components/schemas/{model}"
    )
    schemas.update(rejection.pop("$defs", {}))
    schemas["IdempotencyRejectionSnapshot"] = rejection
    components.setdefault("parameters", {})["IdempotencyKey"] = {
        "name": "Idempotency-Key",
        "in": "header",
        "required": True,
        "description": "Reuse only for the same operation, actor, context and canonical payload.",
        "schema": {"$ref": "#/components/schemas/IdempotencyKey"},
    }
    components.setdefault("headers", {})["IdempotencyReplayed"] = {
        "description": "True when the committed result was recovered without repeating effects.",
        "schema": {"type": "boolean"},
    }
    schema["x-zeromerma-idempotency"] = {
        "contract_version": 1,
        "adoption": "PER_OPERATION",
        "key_parameter": "#/components/parameters/IdempotencyKey",
        "replay_header": "Idempotency-Replayed",
        "mismatch": "409 IDEMPOTENCY_KEY_REUSED",
        "identity_expiration": "NEVER",
        "request_id_is_idempotency_key": False,
    }
