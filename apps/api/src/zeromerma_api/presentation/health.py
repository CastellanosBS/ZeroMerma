from fastapi import APIRouter
from pydantic import BaseModel

from zeromerma_api import __version__
from zeromerma_api.core.config import get_settings

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    status: str
    service: str
    environment: str
    version: str


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    settings = get_settings()
    return HealthResponse(
        status="ok",
        service="zeromerma-api",
        environment=settings.environment,
        version=__version__,
    )
