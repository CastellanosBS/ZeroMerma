from __future__ import annotations

from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from zeromerma_api.core.config import ApiSettings, get_settings
from zeromerma_api.modules.branches.application.access import WorkstationAccessService
from zeromerma_api.modules.branches.application.schemas import (
    BranchSummary,
    PosBootstrapResponse,
    TrainingModeView,
    WorkstationSummary,
)
from zeromerma_api.modules.cash.application.services import CashSessionQueryService
from zeromerma_api.modules.identity.application.schemas import AuthenticatedUser


class PosBootstrapService:
    def __init__(
        self,
        workstation_access: WorkstationAccessService | None = None,
        cash_sessions: CashSessionQueryService | None = None,
        settings: ApiSettings | None = None,
    ) -> None:
        self._workstation_access = workstation_access or WorkstationAccessService()
        self._cash_sessions = cash_sessions or CashSessionQueryService()
        self._settings = settings or get_settings()

    def get_bootstrap(
        self,
        session: Session,
        *,
        current_user: AuthenticatedUser,
        workstation_code: str,
    ) -> PosBootstrapResponse:
        context = self._workstation_access.resolve_context(
            session,
            user_id=current_user.id,
            workstation_code=workstation_code,
        )
        local_timestamp = datetime.now(tz=UTC).astimezone(ZoneInfo(context.branch_timezone))

        return PosBootstrapResponse(
            user=current_user,
            branch=BranchSummary(
                id=context.branch_id,
                code=context.branch_code,
                name=context.branch_name,
                timezone=context.branch_timezone,
                is_active=context.branch_is_active,
            ),
            workstation=WorkstationSummary(
                id=context.workstation_id,
                code=context.workstation_code,
                name=context.workstation_name,
                is_active=context.workstation_is_active,
            ),
            local_timestamp=local_timestamp,
            active_cash_session=self._cash_sessions.get_open_session_for_workstation_code(
                session,
                workstation_code=workstation_code,
            ),
            training_mode=self._build_training_mode(),
        )

    def _build_training_mode(self) -> TrainingModeView | None:
        if not self._settings.training_mode_enabled:
            return None

        return TrainingModeView(
            is_enabled=True,
            label=self._settings.training_mode_label,
            safeguard_note=(
                "Usa una API, worker y base de datos separados para entrenamiento. "
                "No mezcles esta sesion con datos operativos reales."
            ),
        )
