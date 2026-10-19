from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from zeromerma_api.db.access_scope import bind_authorization_scope
from zeromerma_api.modules.branches.infrastructure.models import Branch
from zeromerma_api.modules.idempotency.application.schemas import (
    CommandContext,
    CommandResult,
    IdempotencyResult,
    ResponsePolicy,
)
from zeromerma_api.modules.idempotency.application.service import IdempotencyExecutor
from zeromerma_api.modules.idempotency.domain.exceptions import (
    DeterministicRejection,
    IdempotencyBoundaryError,
)
from zeromerma_api.modules.idempotency.presentation.http import IdempotencyRejectionSnapshot
from zeromerma_api.modules.identity.application.authorization import (
    require_branches,
    resolve_authorization,
)
from zeromerma_api.modules.identity.application.schemas import AuthenticatedUser, CapabilityCode
from zeromerma_api.modules.identity.application.session_services import auth_error
from zeromerma_api.modules.inventory.domain.exceptions import InventoryValidationError
from zeromerma_api.modules.production.application.admin_schemas import (
    AdminProductionCancelRequest,
    AdminProductionCompleteRequest,
    AdminProductionCreateRequest,
    AdminProductionReleaseRequest,
    AdminProductionUpdateRequest,
    ProductionCommandCode,
    ProductionCommandResultView,
)
from zeromerma_api.modules.production.application.admin_services import AdminProductionService
from zeromerma_api.modules.production.domain.exceptions import (
    ProductionNotFoundError,
    ProductionValidationError,
)
from zeromerma_api.modules.production.infrastructure.models import ProductionBatch

ProductionCommand = (
    AdminProductionCreateRequest
    | AdminProductionUpdateRequest
    | AdminProductionReleaseRequest
    | AdminProductionCompleteRequest
    | AdminProductionCancelRequest
)
PRODUCTION_RESPONSE_POLICY = ResponsePolicy(
    snapshot_model=ProductionCommandResultView, rejection_model=IdempotencyRejectionSnapshot
)


def production_capability(command_code: ProductionCommandCode) -> CapabilityCode:
    if command_code == "cancel":
        return "production.cancel"
    if command_code in {"release", "complete"}:
        return "production.execute"
    return "production.manage"


class ProductionIdempotencyService:
    def __init__(self, commands: AdminProductionService | None = None) -> None:
        self._commands = commands or AdminProductionService()

    def execute(
        self,
        session: Session,
        *,
        current_user: AuthenticatedUser,
        command_code: ProductionCommandCode,
        command: ProductionCommand,
        key: UUID,
        request_id: str | None,
        production_id: UUID | None = None,
    ) -> IdempotencyResult:
        expected_type = {
            "create": AdminProductionCreateRequest,
            "update": AdminProductionUpdateRequest,
            "release": AdminProductionReleaseRequest,
            "complete": AdminProductionCompleteRequest,
            "cancel": AdminProductionCancelRequest,
        }[command_code]
        if type(command) is not expected_type or (command_code == "create") != (
            production_id is None
        ):
            raise IdempotencyBoundaryError("The production command does not match its operation.")
        self._bind(session, current_user, command_code, mutation=True)

        def context(current: Session, saved: CommandContext | None) -> CommandContext:
            if isinstance(command, AdminProductionCreateRequest):
                branch_id = command.branch_id
            elif saved is not None:
                branch_id = saved.branch_id
            else:
                branch_id = current.scalar(
                    select(ProductionBatch.branch_id).where(ProductionBatch.id == production_id)
                )
                if branch_id is None:
                    raise ProductionNotFoundError("Production batch was not found.")
            return CommandContext(
                actor_user_id=current_user.id, surface="BACKOFFICE", branch_id=branch_id
            )

        def action(current: Session) -> CommandResult:
            try:
                if isinstance(command, AdminProductionCreateRequest):
                    result = self._commands.create_production(
                        current, command=command, current_user=current_user, request_id=request_id
                    )
                else:
                    assert production_id is not None
                    if isinstance(command, AdminProductionUpdateRequest):
                        result = self._commands.update_production(
                            current,
                            command=command,
                            current_user=current_user,
                            production_id=production_id,
                            request_id=request_id,
                        )
                    elif isinstance(command, AdminProductionReleaseRequest):
                        result = self._commands.release_production(
                            current,
                            command=command,
                            current_user=current_user,
                            production_id=production_id,
                            request_id=request_id,
                        )
                    elif isinstance(command, AdminProductionCompleteRequest):
                        result = self._commands.complete_production(
                            current,
                            command=command,
                            current_user=current_user,
                            production_id=production_id,
                            request_id=request_id,
                        )
                    else:
                        result = self._commands.cancel_production(
                            current,
                            command=command,
                            current_user=current_user,
                            production_id=production_id,
                            request_id=request_id,
                        )
            except (ProductionValidationError, InventoryValidationError) as error:
                snapshot = IdempotencyRejectionSnapshot(
                    code="PRODUCTION_CONFLICT", message=str(error)
                )
                raise DeterministicRejection(
                    code=snapshot.code,
                    status_code=409,
                    message=snapshot.message,
                    snapshot=snapshot,
                ) from error
            return CommandResult(
                status_code=201 if command_code == "create" else 200,
                snapshot=result,
                resource_type="production_batch",
                resource_id=str(result.id),
            )

        # PATCH distinguishes omitted fields from explicit null; other DTO defaults are canonical.
        payload = command.model_dump(
            mode="python", exclude_unset=isinstance(command, AdminProductionUpdateRequest)
        )
        return IdempotencyExecutor().execute(
            session,
            key=key,
            operation_code=f"production.{command_code}",
            payload={"production_id": production_id, "command": payload},
            resolve_context=context,
            authorize=lambda current, resolved: self._authorize(
                current, current_user, command_code, resolved
            ),
            action=action,
            response_policy=PRODUCTION_RESPONSE_POLICY,
            request_id=request_id,
        )

    def recover(
        self,
        session: Session,
        *,
        current_user: AuthenticatedUser,
        command_code: ProductionCommandCode,
        key: UUID,
        branch_id: UUID,
    ) -> IdempotencyResult:
        self._bind(session, current_user, command_code, mutation=False)
        return IdempotencyExecutor().recover(
            session,
            key=key,
            operation_code=f"production.{command_code}",
            resolve_context=lambda _current, _saved: CommandContext(
                actor_user_id=current_user.id, surface="BACKOFFICE", branch_id=branch_id
            ),
            authorize=lambda current, resolved: self._authorize(
                current, current_user, command_code, resolved
            ),
            response_policy=PRODUCTION_RESPONSE_POLICY,
        )

    @staticmethod
    def _bind(
        session: Session,
        user: AuthenticatedUser,
        command_code: ProductionCommandCode,
        *,
        mutation: bool,
    ) -> None:
        if user.authorization_surface != "BACKOFFICE":
            raise auth_error(403, "FORBIDDEN", "Backoffice access is required.")
        bind_authorization_scope(
            session,
            user=user,
            capabilities=(production_capability(command_code),),
            mutation=mutation,
            surface="BACKOFFICE",
        )

    @staticmethod
    def _authorize(
        session: Session,
        user: AuthenticatedUser,
        command_code: ProductionCommandCode,
        context: CommandContext,
    ) -> None:
        if context.branch_id is None:
            raise IdempotencyBoundaryError("Production commands require an explicit branch.")
        refreshed = resolve_authorization(session, user, surface="BACKOFFICE")
        require_branches(refreshed, production_capability(command_code), [context.branch_id])
        if session.get(Branch, context.branch_id) is None:
            raise ProductionNotFoundError("Branch was not found.")
