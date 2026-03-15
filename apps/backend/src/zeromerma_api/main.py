# apps/backend/src/zeromerma_api/main.py
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import Any, cast

from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from zeromerma_api.core.deps_auth import get_current_active_user
from zeromerma_api.core.logging_config import setup_logging
from zeromerma_api.core.settings import get_settings
from zeromerma_api.routers.auth import router as auth_router
from zeromerma_api.routers.health import router as health_router
from zeromerma_api.routers.inventory import router as inventory_router
from zeromerma_api.routers.pos import router as pos_router
from zeromerma_api.routers.ready import router as ready_router

log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan hook.

    Why this exists:
    - It gives us one centralized place to initialize shared resources
      when the app starts and to release/close them when the app stops.
    - Right now we use it mainly to initialize logging after loading settings.
    - Later we can also initialize telemetry, warm caches, validate external
      dependencies, etc.

    Execution model:
    - Code before `yield` runs on startup.
    - Code after `yield` runs on shutdown.
    """
    # Load strongly-typed application settings (single source of truth).
    s = get_settings()

    # Configure logging once at startup using the configured log level.
    setup_logging(s.log_level)

    # Startup log: useful to confirm env / port / log level.
    log.info(
        "Starting %s (env=%s, log=%s, port=%s)",
        s.app_name,
        s.env,
        s.log_level,
        s.port,
    )

    # Hand control back to FastAPI so it can start serving requests.
    yield

    # Shutdown log: useful in local dev, containers, and graceful shutdown debugging.
    log.info("Shutting down %s", s.app_name)


def _error_payload(
    *,
    code: str,
    message: str,
    details: object | None = None,
) -> dict[str, object]:
    """
    Build the standard JSON error envelope for the whole API.

    Target format:
    {
      "error": {
        "code": "...",
        "message": "...",
        "details": ...optional...
      }
    }

    Why this helper exists:
    - Keeps all error responses consistent across routers and services.
    - Makes frontend parsing easier (single contract).
    - Prevents every exception handler from building a slightly different shape.
    """
    error_obj: dict[str, object] = {
        "code": code,
        "message": message,
    }

    # Only include details when we actually have something useful and safe.
    if details is not None:
        error_obj["details"] = details

    return {"error": error_obj}


def _http_status_to_error_code(status_code: int) -> str:
    """
    Map HTTP status codes to stable application-level error codes.

    Why this matters:
    - HTTP status codes are necessary, but not always sufficient for frontend logic.
    - A client can branch on `error.code` instead of parsing free-text messages.
    """
    mapping = {
        400: "BAD_REQUEST",
        401: "UNAUTHORIZED",
        403: "FORBIDDEN",
        404: "NOT_FOUND",
        409: "RESOURCE_CONFLICT",
        422: "VALIDATION_ERROR",
    }
    return mapping.get(status_code, "HTTP_ERROR")


def _normalize_http_exception_detail(detail: object) -> tuple[str, object | None]:
    """
    Normalize the `.detail` attribute from HTTPException into:

    - a human-readable message
    - optional structured details

    Why this exists:
    - FastAPI/Starlette allow `detail` to be a string OR a structured object.
    - We want to preserve useful details while keeping a stable outer contract.

    Rules:
    - If detail is a string -> treat it as the main message.
    - Otherwise -> use a generic message and put the raw detail into `details`.
    """
    if isinstance(detail, str):
        return detail, None

    return "Request failed.", detail


async def http_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Global handler for HTTPException / StarletteHTTPException.

    IMPORTANT TYPE-CHECKING NOTE:
    - We intentionally accept `exc: Exception` (generic) instead of
      `exc: StarletteHTTPException` because `add_exception_handler()` expects
      a generic exception handler signature.
    - At runtime, this function is only registered for StarletteHTTPException,
      so we safely cast it inside.

    This avoids Pylance/Pyright signature errors while keeping runtime behavior correct.
    """
    http_exc = cast(StarletteHTTPException, exc)

    message, details = _normalize_http_exception_detail(http_exc.detail)

    return JSONResponse(
        status_code=http_exc.status_code,
        content=_error_payload(
            code=_http_status_to_error_code(http_exc.status_code),
            message=message,
            details=details,
        ),
    )


async def request_validation_exception_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    """
    Global handler for request validation failures (422).

    Typical causes:
    - Missing required fields
    - Wrong data types
    - Invalid body/query/path input according to Pydantic/FastAPI validation

    IMPORTANT TYPE-CHECKING NOTE:
    - We accept `exc: Exception` to satisfy the generic handler contract.
    - This handler is only registered for RequestValidationError, so we cast
      inside before reading `.errors()`.
    """
    validation_exc = cast(RequestValidationError, exc)

    return JSONResponse(
        status_code=422,
        content=_error_payload(
            code="VALIDATION_ERROR",
            message="Request validation failed.",
            details=validation_exc.errors(),
        ),
    )


async def unhandled_exception_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    """
    Last-resort handler for unexpected server errors (500).

    Why this exists:
    - Prevents raw internal exceptions from leaking to clients.
    - Guarantees a consistent JSON error envelope even for unexpected failures.
    - Logs the real exception server-side so we can debug it safely.

    Security principle:
    - Never expose stack traces, driver errors, secrets, or internal implementation
      details in client-facing 500 responses.
    """
    log.exception(
        "Unhandled exception while processing %s %s",
        request.method,
        request.url.path,
    )

    return JSONResponse(
        status_code=500,
        content=_error_payload(
            code="INTERNAL_SERVER_ERROR",
            message="An unexpected error occurred.",
        ),
    )


def create_app() -> FastAPI:
    """
    FastAPI application factory.

    Why use an app factory:
    - Makes tests cleaner (fresh app instances when needed).
    - Centralizes app configuration in one place.
    - Keeps the module-level `app = create_app()` simple for Uvicorn.

    Build order (important):
    1) Create app
    2) Register middleware
    3) Register global exception handlers
    4) Register routers
    """
    # Read application settings once.
    s = get_settings()

    # Create the FastAPI app instance.
    app = FastAPI(
        title=s.app_name,
        version="0.0.0",  # OpenAPI metadata version; can evolve independently later
        lifespan=lifespan,
    )

    # -------------------------------------------------------------------------
    # CORS
    # -------------------------------------------------------------------------
    # Development is intentionally permissive to unblock local frontend work.
    # In production, this should be restricted to explicit trusted origins.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if s.env == "development" else [],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # -------------------------------------------------------------------------
    # Global exception handlers
    # -------------------------------------------------------------------------
    # We cast handlers to Any on registration because Starlette/FastAPI type hints
    # are stricter than what Pylance often accepts for custom async handlers.
    #
    # Runtime behavior is correct:
    # - The framework dispatches these handlers only for the registered exception type.
    # - The casts are only to satisfy static type checkers cleanly.
    app.add_exception_handler(
        StarletteHTTPException,
        cast(Any, http_exception_handler),
    )
    app.add_exception_handler(
        RequestValidationError,
        cast(Any, request_validation_exception_handler),
    )
    app.add_exception_handler(
        Exception,
        cast(Any, unhandled_exception_handler),
    )

    # -------------------------------------------------------------------------
    # Routers
    # -------------------------------------------------------------------------
    # Register routers after middleware and handlers so endpoint execution already
    # benefits from the global app behavior we configured above.
    app.include_router(health_router)
    app.include_router(ready_router)
    app.include_router(auth_router)
    app.include_router(inventory_router)
    app.include_router(
        pos_router,
        dependencies=[Depends(get_current_active_user)],
    )

    return app


# Uvicorn entrypoint:
#   uvicorn zeromerma_api.main:app --reload
#
# Keeping `app` at module scope lets Uvicorn import it directly.
app = create_app()
