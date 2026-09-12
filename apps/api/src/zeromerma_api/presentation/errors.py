from __future__ import annotations

import logging
import re
from collections.abc import Mapping
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)

ERROR_CODE_BY_STATUS = {
    400: "BAD_REQUEST",
    401: "AUTHENTICATION_REQUIRED",
    403: "FORBIDDEN",
    404: "NOT_FOUND",
    409: "CONFLICT",
    422: "VALIDATION_ERROR",
    500: "INTERNAL_SERVER_ERROR",
}
ERROR_STATUS_CODES = tuple(ERROR_CODE_BY_STATUS)
_SENSITIVE_KEY = re.compile(r"(?:password|secret|token|authorization|cookie)", re.IGNORECASE)
_REQUEST_ID_MAX_LENGTH = 128


class ApiFieldError(BaseModel):
    location: list[str | int]
    message: str
    type: str


class ApiErrorResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str
    message: str
    details: dict[str, Any] | list[Any] | None
    request_id: str | None
    field_errors: list[ApiFieldError] | None


def _request_id(request: Request) -> str | None:
    value = request.headers.get("x-request-id")
    if value is None:
        return None
    normalized = value.strip()
    if not normalized:
        return None
    return normalized[:_REQUEST_ID_MAX_LENGTH]


def _redact(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {
            str(key): "[REDACTED]" if _SENSITIVE_KEY.search(str(key)) else _redact(item)
            for key, item in value.items()
        }
    if isinstance(value, list | tuple):
        return [_redact(item) for item in value]
    if isinstance(value, str | int | float | bool) or value is None:
        return value
    return str(value)


def _safe_http_detail(
    detail: Any, status_code: int
) -> tuple[str, dict[str, Any] | list[Any] | None]:
    if isinstance(detail, str) and detail.strip():
        return detail, None
    if isinstance(detail, Mapping):
        redacted = _redact(detail)
        message = redacted.get("message") if isinstance(redacted, dict) else None
        if not isinstance(message, str) or not message.strip():
            message = (
                ERROR_CODE_BY_STATUS.get(status_code, "REQUEST_FAILED").replace("_", " ").title()
            )
        return message, redacted
    if isinstance(detail, list):
        return "Request failed.", _redact(detail)
    return "Request failed.", None


def _response(
    *,
    status_code: int,
    request: Request,
    message: str,
    details: dict[str, Any] | list[Any] | None = None,
    field_errors: list[ApiFieldError] | None = None,
    headers: Mapping[str, str] | None = None,
) -> JSONResponse:
    payload = ApiErrorResponse(
        code=ERROR_CODE_BY_STATUS.get(status_code, "REQUEST_FAILED"),
        message=message,
        details=details,
        request_id=_request_id(request),
        field_errors=field_errors,
    )
    return JSONResponse(
        status_code=status_code,
        content=payload.model_dump(mode="json"),
        headers=dict(headers or {}),
    )


async def http_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    if not isinstance(exc, StarletteHTTPException):
        raise TypeError("HTTP exception handler received an incompatible exception")
    if exc.status_code >= 500:
        return _response(
            status_code=exc.status_code,
            request=request,
            message="An unexpected error occurred.",
        )
    message, details = _safe_http_detail(exc.detail, exc.status_code)
    return _response(
        status_code=exc.status_code,
        request=request,
        message=message,
        details=details,
        headers=exc.headers,
    )


async def validation_exception_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    if not isinstance(exc, RequestValidationError):
        raise TypeError("validation handler received an incompatible exception")
    field_errors = [
        ApiFieldError(
            location=[str(part) if not isinstance(part, int) else part for part in error["loc"]],
            message=str(error["msg"]),
            type=str(error["type"]),
        )
        for error in exc.errors()
    ]
    return _response(
        status_code=422,
        request=request,
        message="Request validation failed.",
        field_errors=field_errors,
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error(
        "Unhandled API exception request_id=%s exception_type=%s",
        _request_id(request),
        type(exc).__name__,
    )
    return _response(
        status_code=500,
        request=request,
        message="An unexpected error occurred.",
    )


def error_responses() -> dict[int | str, dict[str, Any]]:
    return {
        status_code: {
            "model": ApiErrorResponse,
            "description": ERROR_CODE_BY_STATUS[status_code].replace("_", " ").title(),
        }
        for status_code in ERROR_STATUS_CODES
    }


def install_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
