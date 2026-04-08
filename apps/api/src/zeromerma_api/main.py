from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from zeromerma_api import __version__
from zeromerma_api.core.config import get_settings
from zeromerma_api.core.logging import configure_logging
from zeromerma_api.presentation.api import api_router


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)

    app = FastAPI(
        title="ZeroMerma API",
        version=__version__,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(api_router)
    return app


app = create_app()
