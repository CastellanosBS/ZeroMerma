# apps/backend/src/zeromerma_api/core/request_middleware.py
# PURPOSE:
#   - Generate / propagate X-Request-ID
#   - Extract minimal auth context from JWT claims (sub/role_code/branch_id)
#   - Attach context to logs via contextvars
#   - Emit one request log line with latency and status code
#
# DESIGN NOTES:
#   - This middleware never queries the database.
#   - It decodes JWT only to get claims; if token is missing/invalid, we still log request_id.

from __future__ import annotations

import logging
import time
import uuid
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from zeromerma_api.core.request_context import (
    reset_request_context,
    set_request_context,
)
from zeromerma_api.core.security import AuthTokenError, decode_access_token

log = logging.getLogger("zeromerma_api.request")


def _extract_claims_from_authorization_header(request: Request) -> tuple[str, str, str]:
    """
    Best-effort extraction of (user_id, role_code, branch_id) from JWT claims.

    Returns "-" for any missing/invalid values.
    """
    auth = request.headers.get("Authorization", "")
    if not auth:
        return "-", "-", "-"

    parts = auth.split(" ", 1)
    if len(parts) != 2:
        return "-", "-", "-"

    scheme, token = parts[0].strip(), parts[1].strip()
    if scheme.lower() != "bearer" or not token:
        return "-", "-", "-"

    try:
        payload = decode_access_token(token)
    except AuthTokenError:
        return "invalid", "invalid", "invalid"

    user_id = str(payload.get("sub", "-"))
    role_code = str(payload.get("role_code", "-"))
    branch_id = str(payload.get("branch_id", "-"))

    return user_id, role_code, branch_id


class RequestContextMiddleware(BaseHTTPMiddleware):
    """
    Middleware that:
      - ensures every response has X-Request-ID
      - sets request-scoped contextvars used by logging filters/formatters
      - logs a concise request summary line
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # 1) Request ID (propagate if provided)
        request_id = request.headers.get("X-Request-ID", "").strip() or uuid.uuid4().hex

        # 2) Best-effort auth claims (no DB)
        user_id, role_code, branch_id = _extract_claims_from_authorization_header(
            request
        )

        # 3) Set contextvars for this request
        tokens = set_request_context(
            request_id=request_id,
            user_id=user_id,
            role_code=role_code,
            branch_id=branch_id,
        )

        start = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            # Log exception with the same request context.
            elapsed_ms = int((time.perf_counter() - start) * 1000)
            log.exception(
                "request_failed method=%s path=%s duration_ms=%s",
                request.method,
                request.url.path,
                elapsed_ms,
            )
            reset_request_context(tokens)
            raise

        elapsed_ms = int((time.perf_counter() - start) * 1000)

        # 4) Always return request id in response for correlation
        response.headers["X-Request-ID"] = request_id

        # 5) Summary request log
        log.info(
            "request method=%s path=%s status=%s duration_ms=%s",
            request.method,
            request.url.path,
            response.status_code,
            elapsed_ms,
        )

        # 6) Reset contextvars (important in async servers)
        reset_request_context(tokens)
        return response
