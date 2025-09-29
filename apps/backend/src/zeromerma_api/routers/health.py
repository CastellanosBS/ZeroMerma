# apps/backend/src/zeromerma_api/routers/health.py
from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

from fastapi import APIRouter
from pydantic import BaseModel

from zeromerma_api.core.settings import get_settings

router = APIRouter(tags=["meta"])


def _get_version() -> str:
    """Resolve package version if installed, else '0.0.0-dev'.

    In dev you might run from source; in CI/CD you'll have a package version.
    """
    try:
        return version("zeromerma_api")  # If you later package with this name
    except PackageNotFoundError:
        return "0.0.0-dev"


class HealthResponse(BaseModel):
    status: str
    app: str
    env: str
    version: str


@router.get("/healthz", response_model=HealthResponse)
def healthz() -> HealthResponse:
    """Liveness probe (no DB yet).

    Why: Tells load balancers / dev tools that the process is alive and responding.
    """
    s = get_settings()
    return HealthResponse(
        status="ok",
        app=s.app_name,
        env=s.env,
        version=_get_version(),
    )


class VersionResponse(BaseModel):
    version: str


@router.get("/version", response_model=VersionResponse)
def get_version() -> VersionResponse:
    """Expose API version number.

    Why: Helps clients and debugging; quick sanity check in deployments.
    """
    return VersionResponse(version=_get_version())
