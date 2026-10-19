from collections.abc import Generator
from functools import lru_cache
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

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


class LocalReadinessResponse(BaseModel):
    status: Literal["READY", "UNAVAILABLE"]
    database: Literal["READY", "UNAVAILABLE"]
    internet: Literal["UNKNOWN"] = "UNKNOWN"
    transactional_mode: Literal["LOCAL_FIRST"] = "LOCAL_FIRST"
    browser_offline_mutations: Literal[False] = False


@lru_cache(maxsize=1)
def _readiness_engine() -> Engine:
    # An isolated, bounded probe pool cannot exhaust the command pool or wait on it.
    return create_engine(
        str(get_settings().database_url),
        pool_size=1,
        max_overflow=0,
        pool_timeout=1,
        connect_args={"connect_timeout": 2, "options": "-c statement_timeout=2000"},
    )


def readiness_session() -> Generator[Session, None, None]:
    with Session(_readiness_engine()) as session:
        yield session


@router.get(
    "/ready",
    response_model=LocalReadinessResponse,
    responses={503: {"model": LocalReadinessResponse}},
)
def local_readiness(
    response: Response,
    session: Annotated[Session, Depends(readiness_session)],
) -> LocalReadinessResponse:
    """Observe local writable authority without depending on external Internet services."""
    response.headers["Cache-Control"] = "no-store"
    try:
        # A healthy standby must not admit commands before a controlled promotion.
        recovery, read_only = session.execute(
            text("SELECT pg_is_in_recovery(), current_setting('transaction_read_only')")
        ).one()
        ready = not recovery and read_only == "off"
    except SQLAlchemyError:
        # Never expose connection strings or database errors through a public probe.
        ready = False
    if not ready:
        response.status_code = 503
        return LocalReadinessResponse(status="UNAVAILABLE", database="UNAVAILABLE")
    return LocalReadinessResponse(status="READY", database="READY")
