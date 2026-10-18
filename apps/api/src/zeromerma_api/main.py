from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from zeromerma_api import __version__
from zeromerma_api.core.config import ApiSettings, get_settings
from zeromerma_api.core.logging import configure_logging
from zeromerma_api.core.security import install_security_boundary
from zeromerma_api.presentation.api import api_router
from zeromerma_api.presentation.contracts import install_contract_openapi
from zeromerma_api.presentation.errors import error_responses, install_error_handlers


def _build_allowed_origins(settings: ApiSettings) -> list[str]:
    return list(settings.cors_origins)


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)

    allowed_origins = _build_allowed_origins(settings)
    app = FastAPI(
        title="ZeroMerma API",
        version=__version__,
        docs_url="/docs" if settings.enable_api_docs else None,
        redoc_url="/redoc" if settings.enable_api_docs else None,
        openapi_url="/openapi.json" if settings.environment in {"local", "test"} else None,
        responses=error_responses(),
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "HEAD", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "X-CSRF-Token", "X-ZeroMerma-Surface", "X-Request-ID"],
    )

    app.include_router(api_router)
    if settings.environment in {"staging", "production"}:
        app.router.routes[:] = [
            route
            for route in app.router.routes
            if not getattr(route, "path", "").startswith("/dev/")
        ]
    install_error_handlers(app)
    install_security_boundary(app, settings)
    install_contract_openapi(app)
    return app


app = create_app()
