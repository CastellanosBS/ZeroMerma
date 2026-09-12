from __future__ import annotations

import logging
from collections.abc import Iterable

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from zeromerma_api import __version__
from zeromerma_api.core.config import ApiSettings, get_settings
from zeromerma_api.core.logging import configure_logging
from zeromerma_api.presentation.api import api_router
from zeromerma_api.presentation.contracts import install_contract_openapi
from zeromerma_api.presentation.errors import error_responses, install_error_handlers

logger = logging.getLogger(__name__)


def _normalize_origins(origins: str | Iterable[str] | None) -> list[str]:
    """
    Normalize CORS origins to avoid common mismatches:
    - remove surrounding spaces
    - remove trailing slash
    - deduplicate while preserving order
    """
    if origins is None:
        return []

    if isinstance(origins, str):
        raw_origins = origins.split(",")
    else:
        raw_origins = list(origins)

    normalized: list[str] = []
    seen: set[str] = set()

    for origin in raw_origins:
        value = str(origin).strip().rstrip("/")
        if not value or value in seen:
            continue
        seen.add(value)
        normalized.append(value)

    return normalized


def _build_allowed_origins(settings: ApiSettings) -> list[str]:
    """
    Merge configured origins with safe development defaults.
    Important: these must be FRONTEND origins, not the API URL.
    """
    configured_origins = _normalize_origins(getattr(settings, "cors_origins", []))

    development_origins = _normalize_origins(
        [
            "http://localhost:5173",
            "http://localhost:5174",
            "http://127.0.0.1:5173",
            "http://127.0.0.1:5174",
            "http://192.168.1.69:5173",
            "http://192.168.1.69:5174",
            "http://172.30.96.1:5173",
            "http://172.30.96.1:5174",
        ]
    )

    return _normalize_origins([*configured_origins, *development_origins])


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)

    allowed_origins = _build_allowed_origins(settings)
    logger.info("CORS allowed origins: %s", allowed_origins)

    app = FastAPI(
        title="ZeroMerma API",
        version=__version__,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        responses=error_responses(),
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_router)
    install_error_handlers(app)
    install_contract_openapi(app)
    return app


app = create_app()
