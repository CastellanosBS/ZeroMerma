from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from zeromerma_api.modules.branches.infrastructure.models import Branch
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
from zeromerma_api.modules.identity.application.session_services import auth_error
from zeromerma_api.modules.inventory.application.admin_schemas import (
    AdminInventoryAdjustmentRequest,
    AdminInventoryAdjustmentResultView,
)
from zeromerma_api.modules.inventory.application.admin_services import AdminInventoryService
from zeromerma_api.modules.inventory.domain.exceptions import InventoryNotFoundError

OPERATION_CODE = "inventory.adjust"
RESPONSE_POLICY = ResponsePolicy(snapshot_model=AdminInventoryAdjustmentResultView)


class AdminInventoryAdjustmentService:
    def __init__(self, command_service: AdminInventoryService | None = None) -> None:
        self._commands = command_service or AdminInventoryService()

    def commit(
        self,
        session: Session,
        *,
        current_user: AuthenticatedUser,
        command: AdminInventoryAdjustmentRequest,
        key: UUID,
        request_id: str | None,
    ) -> IdempotencyResult:
        def action(current: Session) -> CommandResult:
            owner = execution(current)
            if owner is None or owner.record is None:
                raise IdempotencyBoundaryError("The command requires an owned reservation.")
            result = self._commands.create_adjustment(
                current,
                current_user=current_user,
                command=command,
                idempotency_key=key,
                operation_id=owner.record.id,
                request_id=request_id,
            )
            return CommandResult(
                status_code=201,
                snapshot=result,
                resource_type="inventory_adjustment",
                resource_id=str(result.id),
            )

        return IdempotencyExecutor().execute(
            session,
            key=key,
            operation_code=OPERATION_CODE,
            payload=command,
            resolve_context=lambda _current, _saved: CommandContext(
                actor_user_id=current_user.id,
                surface="BACKOFFICE",
                branch_id=command.branch_id,
            ),
            authorize=lambda current, context: self._authorize(current, current_user, context),
            action=action,
            response_policy=RESPONSE_POLICY,
            request_id=request_id,
        )

    def recover(
        self,
        session: Session,
        *,
        current_user: AuthenticatedUser,
        key: UUID,
        branch_id: UUID,
    ) -> IdempotencyResult:
        return IdempotencyExecutor().recover(
            session,
            key=key,
            operation_code=OPERATION_CODE,
            resolve_context=lambda _current, _saved: CommandContext(
                actor_user_id=current_user.id,
                surface="BACKOFFICE",
                branch_id=branch_id,
            ),
            authorize=lambda current, context: self._authorize(current, current_user, context),
            response_policy=RESPONSE_POLICY,
        )

    @staticmethod
    def _authorize(session: Session, user: AuthenticatedUser, context: CommandContext) -> None:
        if user.authorization_surface != "BACKOFFICE" or context.branch_id is None:
            raise auth_error(403, "FORBIDDEN", "The command surface is not authorized.")
        refreshed = resolve_authorization(session, user, surface="BACKOFFICE")
        require_branches(refreshed, "inventory.adjust", [context.branch_id])
        if session.scalar(select(Branch.id).where(Branch.id == context.branch_id)) is None:
            raise InventoryNotFoundError("Branch was not found.")
