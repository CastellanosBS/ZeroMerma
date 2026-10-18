from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from zeromerma_api.modules.branches.infrastructure.models import Workstation
from zeromerma_api.modules.idempotency.application.context import execution
from zeromerma_api.modules.idempotency.application.schemas import (
    CommandContext,
    CommandResult,
    IdempotencyResult,
    ResponsePolicy,
)
from zeromerma_api.modules.idempotency.application.service import IdempotencyExecutor
from zeromerma_api.modules.idempotency.domain.exceptions import IdempotencyBoundaryError
from zeromerma_api.modules.identity.application.authorization import (
    require_branches,
    resolve_authorization,
)
from zeromerma_api.modules.identity.application.schemas import AuthenticatedUser
from zeromerma_api.modules.identity.application.session_services import (
    AUTH_CONTEXT_KEY,
    SessionAuthentication,
    auth_error,
)
from zeromerma_api.modules.sales.application.schemas import (
    ConfirmSaleRequest,
    SaleConfirmationView,
)
from zeromerma_api.modules.sales.application.services import PreparedSale, SaleCommandService

SALE_CONFIRM_OPERATION = "sale.confirm"
SALE_CONFIRM_RESPONSE_POLICY = ResponsePolicy(snapshot_model=SaleConfirmationView)


class SaleConfirmationService:
    def __init__(self, command_service: SaleCommandService | None = None) -> None:
        self._command_service = command_service or SaleCommandService()

    def confirm(
        self,
        session: Session,
        *,
        current_user: AuthenticatedUser,
        command: ConfirmSaleRequest,
        key: UUID,
        request_id: str | None,
    ) -> IdempotencyResult:
        prepared: PreparedSale | None = None

        def resolve_context(current: Session, saved: CommandContext | None) -> CommandContext:
            nonlocal prepared
            if saved is not None:
                return self._request_context(
                    current,
                    current_user=current_user,
                    workstation_code=command.workstation_code,
                    cash_session_id=command.cash_session_id,
                )
            prepared = self._command_service.prepare_sale(
                current, current_user=current_user, command=command
            )
            return CommandContext(
                actor_user_id=current_user.id,
                surface="POS",
                branch_id=prepared.context.branch_id,
                workstation_id=prepared.context.workstation_id,
                cash_session_id=prepared.cash_session_id,
            )

        def action(current: Session) -> CommandResult:
            owner = execution(current)
            if prepared is None or owner is None or owner.record is None:
                raise IdempotencyBoundaryError("A sale requires its prepared command reservation.")
            snapshot = self._command_service.confirm_sale(
                current,
                current_user=current_user,
                prepared=prepared,
                request_id=request_id,
                idempotency_key=key,
                operation_id=owner.record.id,
            )
            return CommandResult(
                status_code=201,
                snapshot=snapshot,
                resource_type="sale",
                resource_id=str(snapshot.id),
            )

        return IdempotencyExecutor().execute(
            session,
            key=key,
            operation_code=SALE_CONFIRM_OPERATION,
            payload=command,
            resolve_context=resolve_context,
            authorize=lambda current, context: self._authorize(current, current_user, context),
            action=action,
            response_policy=SALE_CONFIRM_RESPONSE_POLICY,
            request_id=request_id,
        )

    def recover(
        self,
        session: Session,
        *,
        current_user: AuthenticatedUser,
        key: UUID,
        workstation_code: str,
        cash_session_id: UUID,
    ) -> IdempotencyResult:
        return IdempotencyExecutor().recover(
            session,
            key=key,
            operation_code=SALE_CONFIRM_OPERATION,
            resolve_context=lambda current, _saved: self._request_context(
                current,
                current_user=current_user,
                workstation_code=workstation_code,
                cash_session_id=cash_session_id,
            ),
            authorize=lambda current, context: self._authorize(current, current_user, context),
            response_policy=SALE_CONFIRM_RESPONSE_POLICY,
        )

    @staticmethod
    def _request_context(
        session: Session,
        *,
        current_user: AuthenticatedUser,
        workstation_code: str,
        cash_session_id: UUID,
    ) -> CommandContext:
        authentication = session.info.get(AUTH_CONTEXT_KEY)
        workstation = session.execute(
            select(Workstation.id, Workstation.branch_id).where(
                Workstation.code == workstation_code
            )
        ).one_or_none()
        if (
            not isinstance(authentication, SessionAuthentication)
            or authentication.record.audience != "POS"
            or authentication.user.id != current_user.id
            or workstation is None
            or authentication.record.workstation_id != workstation.id
        ):
            raise auth_error(403, "FORBIDDEN", "The sale context is not authorized.")
        # Historical cash need not be OPEN. Its exact identity is compared with the saved command.
        return CommandContext(
            actor_user_id=current_user.id,
            surface="POS",
            branch_id=workstation.branch_id,
            workstation_id=workstation.id,
            cash_session_id=cash_session_id,
        )

    @staticmethod
    def _authorize(
        session: Session, current_user: AuthenticatedUser, context: CommandContext
    ) -> None:
        if context.branch_id is None:
            raise IdempotencyBoundaryError("A sale command requires a branch.")
        refreshed = resolve_authorization(session, current_user, surface="POS")
        require_branches(refreshed, "pos.operate", [context.branch_id])
