"""Establish an HTTP attempt before any security, routing or validation rejection."""

from __future__ import annotations

import logging

from starlette.datastructures import Headers, MutableHeaders
from starlette.requests import Request
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from zeromerma_api.core.operation_context import (
    OperationContext,
    RequestOperation,
    SourceApp,
    normalize_request_id,
    request_operation,
)

logger = logging.getLogger(__name__)
_STATE_KEY = "zeromerma_request_operation"


def request_context(request: Request) -> OperationContext | None:
    carrier = request.scope.get("state", {}).get(_STATE_KEY)
    return carrier.context if isinstance(carrier, RequestOperation) else None


def request_trace_headers(request: Request) -> dict[str, str]:
    context = request_context(request)
    if context is None:
        return {}
    return {
        "X-Request-ID": context.request_id or "",
        "X-Correlation-ID": str(context.correlation_id),
    }


def request_id(request: Request) -> str | None:
    context = request_context(request)
    return context.request_id if context is not None else None


class OperationContextMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        incoming = Headers(scope=scope).getlist("X-Request-ID")
        normalized_id = normalize_request_id(incoming[0] if len(incoming) == 1 else None)
        carrier = RequestOperation(OperationContext.start(SourceApp.API, request_id=normalized_id))
        scope.setdefault("state", {})[_STATE_KEY] = carrier
        # All existing handlers consume the same normalized value. Untrusted correlation
        # never becomes an operation identity, even when a client supplies that header.
        scope["headers"] = [
            (key, value)
            for key, value in scope.get("headers", [])
            if key.lower() not in {b"x-request-id", b"x-correlation-id"}
        ] + [(b"x-request-id", normalized_id.encode("ascii"))]
        token = request_operation.set(carrier)
        status = 500

        async def traced_send(message: Message) -> None:
            nonlocal status
            if message["type"] == "http.response.start":
                status = message["status"]
                headers = MutableHeaders(scope=message)
                headers["X-Request-ID"] = normalized_id
                headers["X-Correlation-ID"] = str(carrier.context.correlation_id)
            await send(message)

        try:
            await self.app(scope, receive, traced_send)
        finally:
            logger.info(
                "HTTP request completed",
                extra={
                    "operation_context": carrier.context,
                    "http_status": status,
                },
            )
            request_operation.reset(token)
