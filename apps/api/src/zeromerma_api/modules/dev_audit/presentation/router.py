from __future__ import annotations

from hmac import compare_digest
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy.orm import Session

from zeromerma_api.core.config import ApiSettings, get_settings
from zeromerma_api.db.session import get_session
from zeromerma_api.modules.dev_audit.application.schemas import DevAuditSnapshotResponse
from zeromerma_api.modules.dev_audit.application.service import DevAuditSnapshotService

router = APIRouter(prefix="/dev/audit", tags=["dev-audit"])


def _require_dev_audit_access(
    settings: Annotated[ApiSettings, Depends(get_settings)],
    audit_token: Annotated[str | None, Header(alias="X-Audit-Token")] = None,
) -> ApiSettings:
    if not settings.enable_dev_audit_endpoint:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Development audit endpoint is disabled.",
        )

    expected_token = settings.dev_audit_token
    if (
        expected_token is None
        or audit_token is None
        or not compare_digest(audit_token, expected_token)
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid development audit token.",
        )

    return settings


@router.get(
    "/snapshot",
    response_model=DevAuditSnapshotResponse,
    include_in_schema=False,
)
def get_dev_audit_snapshot(
    settings: Annotated[ApiSettings, Depends(_require_dev_audit_access)],
    session: Annotated[Session, Depends(get_session)],
    branch_code: Annotated[str | None, Query(min_length=1)] = None,
    workstation_code: Annotated[str | None, Query(min_length=1)] = None,
    include_recent_rows: bool = True,
    recent_limit: Annotated[int, Query(ge=1, le=20)] = 5,
) -> DevAuditSnapshotResponse:
    try:
        return DevAuditSnapshotService().build_snapshot(
            session,
            environment=settings.environment,
            dev_audit_feature_enabled=settings.enable_dev_audit_endpoint,
            branch_code=branch_code,
            workstation_code=workstation_code,
            include_recent_rows=include_recent_rows,
            recent_limit=recent_limit,
        )
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error
