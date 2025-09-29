from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from zeromerma_api.core.settings import get_settings

router = APIRouter(tags=["meta"])


class ReadyResponse(BaseModel):
    status: str
    app: str
    env: str


@router.get("/readyz", response_model=ReadyResponse)
def readyz() -> ReadyResponse:
    s = get_settings()
    # “vivo y listo”.
    return ReadyResponse(status="ready", app=s.app_name, env=s.env)
