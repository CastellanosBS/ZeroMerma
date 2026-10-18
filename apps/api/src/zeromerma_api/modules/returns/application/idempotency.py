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
from zeromerma_api.modules.returns.application.schemas import (
    ReturnCommitRequest,
    ReturnCommitResultView,
)
from zeromerma_api.modules.returns.application.services import (
    PreparedReturnContext,
    ReturnsCommandService,
)

RETURN_COMMIT_OPERATION = "return.commit"
RETURN_COMMIT_RESPONSE_POLICY = ResponsePolicy(snapshot_model=ReturnCommitResultView)


class ReturnCommitService:
    def __init__(self, command_service: ReturnsCommandService | None = None) -> None:
        self._commands = command_service or ReturnsCommandService()

    def commit(
        self,
        session: Session,
        *,
        current_user: AuthenticatedUser,
        command: ReturnCommitRequest,
        key: UUID,
        request_id: str | None,
    ) -> IdempotencyResult:
        prepared: PreparedReturnContext | None = None

        def resolve_context(current: Session, saved: CommandContext | None) -> CommandContext:
            nonlocal prepared
            if saved is not None:
                return self._request_context(
                    current,
                    current_user=current_user,
                    workstation_code=command.workstation_code,
                    cash_session_id=command.cash_session_id,
                )
            prepared = self._commands.prepare_return(
                current, current_user=current_user, command=command
            )
            return CommandContext(
                actor_user_id=current_user.id,
                surface="POS",
                branch_id=prepared.context.branch_id,
                workstation_id=prepared.context.workstation_id,
                cash_session_id=prepared.cash_session.id,
            )

        def action(current: Session) -> CommandResult:
            owner = execution(current)
            if prepared is None or owner is None or owner.record is None:
                raise IdempotencyBoundaryError(
                    "A return requires its prepared command reservation."
                )
            snapshot = self._commands.commit_return(
                current,
                current_user=current_user,
                command=command,
                prepared=prepared,
                idempotency_key=key,
                operation_id=owner.record.id,
                request_id=request_id,
            )
            return CommandResult(
                status_code=201,
                snapshot=snapshot,
                resource_type="sale_return",
                resource_id=str(snapshot.id),
            )

        return IdempotencyExecutor().execute(
            session,
            key=key,
            operation_code=RETURN_COMMIT_OPERATION,
            payload=command,
            resolve_context=resolve_context,
            authorize=lambda current, context: self._authorize(current, current_user, context),
            action=action,
            response_policy=RETURN_COMMIT_RESPONSE_POLICY,
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
            operation_code=RETURN_COMMIT_OPERATION,
            resolve_context=lambda current, _saved: self._request_context(
                current,
                current_user=current_user,
                workstation_code=workstation_code,
                cash_session_id=cash_session_id,
            ),
            authorize=lambda current, context: self._authorize(current, current_user, context),
            response_policy=RETURN_COMMIT_RESPONSE_POLICY,
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
            raise auth_error(403, "FORBIDDEN", "The return context is not authorized.")
        # A completed refund keeps its original context even after the cash session closes.
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
            raise IdempotencyBoundaryError("A return command requires a branch.")
        if current_user.authorization_surface != "POS" or context.surface != "POS":
            raise auth_error(403, "FORBIDDEN", "The return application surface is not authorized.")
        refreshed = resolve_authorization(session, current_user, surface="POS")
        require_branches(refreshed, "returns_corrections.manage", [context.branch_id])
