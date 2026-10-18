from __future__ import annotations

from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from zeromerma_api.modules.cash.application.command_context import (
    authorize_cash_command,
    lock_cash_opening,
    resolve_cash_command_context,
)
from zeromerma_api.modules.cash.application.schemas import (
    CashSessionOpenResultView,
    OpenCashSessionRequest,
)
from zeromerma_api.modules.cash.application.services import CashSessionCommandService
from zeromerma_api.modules.cash.domain.exceptions import CashSessionConflictError
from zeromerma_api.modules.idempotency.application.context import execution
from zeromerma_api.modules.idempotency.application.schemas import (
    CommandContext,
    CommandResult,
    IdempotencyResult,
    ResponsePolicy,
)
from zeromerma_api.modules.idempotency.application.service import IdempotencyExecutor
from zeromerma_api.modules.idempotency.domain.exceptions import IdempotencyBoundaryError
from zeromerma_api.modules.identity.application.schemas import AuthenticatedUser

OPERATION_CODE = "cash_session.open"
RESPONSE_POLICY = ResponsePolicy(snapshot_model=CashSessionOpenResultView)


class CashSessionOpenService:
    def __init__(self, command_service: CashSessionCommandService | None = None) -> None:
        self._commands = command_service or CashSessionCommandService()

    def open(
        self,
        session: Session,
        *,
        current_user: AuthenticatedUser,
        command: OpenCashSessionRequest,
        key: UUID,
        request_id: str | None,
    ) -> IdempotencyResult:
        def action(current: Session) -> CommandResult:
            owner = execution(current)
            if owner is None or owner.record is None:
                raise IdempotencyBoundaryError("A cash command requires its reservation.")
            lock_cash_opening(
                current,
                current_user=current_user,
                context=CommandContext(
                    actor_user_id=current_user.id,
                    surface="POS",
                    branch_id=owner.record.branch_id,
                    workstation_id=owner.record.workstation_id,
                ),
            )
            snapshot = self._commands.open_session(
                current,
                current_user=current_user,
                command=command,
                idempotency_key=key,
                operation_id=owner.record.id,
                request_id=request_id,
            )
            return CommandResult(
                status_code=201,
                snapshot=snapshot,
                resource_type="cash_session",
                resource_id=str(snapshot.id),
            )

        try:
            return IdempotencyExecutor().execute(
                session,
                key=key,
                operation_code=OPERATION_CODE,
                payload=command,
                resolve_context=lambda current, _saved: resolve_cash_command_context(
                    current,
                    current_user=current_user,
                    workstation_code=command.workstation_code,
                    cash_session_id=None,
                ),
                authorize=lambda current, context: authorize_cash_command(
                    current, current_user, context, "pos.operate"
                ),
                action=action,
                response_policy=RESPONSE_POLICY,
                request_id=request_id,
            )
        except IntegrityError as error:
            constraint = getattr(getattr(error.orig, "diag", None), "constraint_name", None)
            if constraint not in {
                "ix_cash_sessions_open_user",
                "ix_cash_sessions_open_workstation",
            }:
                raise
            raise CashSessionConflictError("An open cash session already exists.") from error

    def recover(
        self,
        session: Session,
        *,
        current_user: AuthenticatedUser,
        key: UUID,
        workstation_code: str,
    ) -> IdempotencyResult:
        return IdempotencyExecutor().recover(
            session,
            key=key,
            operation_code=OPERATION_CODE,
            resolve_context=lambda current, _saved: resolve_cash_command_context(
                current,
                current_user=current_user,
                workstation_code=workstation_code,
                cash_session_id=None,
            ),
            authorize=lambda current, context: authorize_cash_command(
                current, current_user, context, "pos.operate"
            ),
            response_policy=RESPONSE_POLICY,
        )
