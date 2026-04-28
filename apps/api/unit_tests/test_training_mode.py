from __future__ import annotations

from types import SimpleNamespace
from typing import cast
from uuid import uuid4

import pytest
from pydantic import ValidationError
from sqlalchemy.orm import Session

from zeromerma_api.core.config import ApiSettings
from zeromerma_api.modules.branches.application.access import WorkstationAccessService
from zeromerma_api.modules.cash.application.services import CashSessionQueryService
from zeromerma_api.modules.branches.application.services import PosBootstrapService
from zeromerma_api.modules.identity.application.schemas import AuthenticatedUser


class FakeWorkstationAccessService:
    def resolve_context(
        self,
        session: object,
        *,
        user_id: object,
        workstation_code: str,
    ) -> SimpleNamespace:
        return SimpleNamespace(
            branch_id=uuid4(),
            branch_code="MAIN",
            branch_name="Main Branch",
            branch_timezone="America/Hermosillo",
            branch_is_active=True,
            workstation_id=uuid4(),
            workstation_code=workstation_code,
            workstation_name="Front Register 01",
            workstation_is_active=True,
        )


class FakeCashSessionQueryService:
    def get_open_session_for_workstation_code(
        self,
        session: object,
        *,
        workstation_code: str,
    ) -> None:
        return None


def _build_user() -> AuthenticatedUser:
    return AuthenticatedUser(
        id=uuid4(),
        email="cashier@zeromerma.local",
        full_name="Main Branch Cashier",
        is_active=True,
    )


def test_api_settings_reject_training_mode_in_production() -> None:
    with pytest.raises(ValidationError):
        ApiSettings(
            environment="production",
            training_mode_enabled=True,
        )


def test_pos_bootstrap_exposes_training_mode_when_enabled() -> None:
    service = PosBootstrapService(
        workstation_access=cast(WorkstationAccessService, FakeWorkstationAccessService()),
        cash_sessions=cast(CashSessionQueryService, FakeCashSessionQueryService()),
        settings=ApiSettings(
            environment="local",
            training_mode_enabled=True,
            training_mode_label="Modo entrenamiento",
        ),
    )

    response = service.get_bootstrap(
        cast(Session, object()),
        current_user=_build_user(),
        workstation_code="POS-01",
    )

    assert response.training_mode is not None
    assert response.training_mode.is_enabled is True
    assert response.training_mode.label == "Modo entrenamiento"
    assert "base de datos" in response.training_mode.safeguard_note


def test_pos_bootstrap_omits_training_mode_when_disabled() -> None:
    service = PosBootstrapService(
        workstation_access=cast(WorkstationAccessService, FakeWorkstationAccessService()),
        cash_sessions=cast(CashSessionQueryService, FakeCashSessionQueryService()),
        settings=ApiSettings(
            environment="local",
            training_mode_enabled=False,
        ),
    )

    response = service.get_bootstrap(
        cast(Session, object()),
        current_user=_build_user(),
        workstation_code="POS-01",
    )

    assert response.training_mode is None
