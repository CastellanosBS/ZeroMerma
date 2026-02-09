# apps/backend/src/zeromerma_api/main.py
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from zeromerma_api.core.logging_config import setup_logging
from zeromerma_api.core.settings import get_settings
from zeromerma_api.routers.health import router as health_router
from zeromerma_api.routers.inventory import router as inventory_router
from zeromerma_api.routers.ready import router as ready_router

log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """App lifespan hook.

    Why: Central place to initialize resources (e.g., DB pool in Step 2),
    and to close them gracefully on shutdown.
    """
    s = get_settings()
    setup_logging(s.log_level)

    log.info(
        "Starting %s (env=%s, log=%s, port=%s)", s.app_name, s.env, s.log_level, s.port
    )
    yield
    log.info("Shutting down %s", s.app_name)


def create_app() -> FastAPI:
    s = get_settings()

    app = FastAPI(
        title=s.app_name,
        version="0.0.0",  # OpenAPI version value; /version endpoint is authoritative
        lifespan=lifespan,
    )

    # CORS (relaxed in dev; we'll tighten in prod)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if s.env == "development" else [],  # TODO: restrict on prod
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Routers
    app.include_router(health_router)
    app.include_router(ready_router)
    app.include_router(inventory_router)

    return app


# Uvicorn entrypoint: `uvicorn zeromerma_api.main:app --reload`
app = create_app()
