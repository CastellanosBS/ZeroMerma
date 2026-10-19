from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from zeromerma_api.db.access_scope import bind_authorization_scope
from zeromerma_api.modules.branches.application.access import WorkstationAccessService
from zeromerma_api.modules.branches.infrastructure.models import Workstation
from zeromerma_api.modules.cash.application.command_context import lock_cash_session
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
from zeromerma_api.modules.identity.application.schemas import (
    AuthenticatedUser,
    CapabilityCode,
    IdentitySurface,
)
from zeromerma_api.modules.identity.application.session_services import (
    AUTH_CONTEXT_KEY,
    SessionAuthentication,
    auth_error,
)
from zeromerma_api.modules.orders.application.admin_services import AdminOrdersService, _get_order
from zeromerma_api.modules.orders.application.schemas import (
    AdminOrderCommandCode,
    CancelCustomerOrderRequest,
    CreateCustomerOrderRequest,
    DeliverCustomerOrderRequest,
    OrderActionRequest,
    OrderCommandCode,
    OrderCommandResultView,
)
from zeromerma_api.modules.orders.application.services import (
    OrderCommandTrace,
    OrdersCommandService,
    PreparedOrderCreation,
    _get_order_for_branch,
    _resolve_context_and_open_session,
)

ORDER_COMMAND_OPERATIONS: dict[OrderCommandCode, str] = {
    "create": "order.create",
    "mark-ready": "order.mark_ready",
    "deliver": "order.deliver",
    "cancel": "order.cancel",
}
ORDER_COMMAND_RESPONSE_POLICY = ResponsePolicy(snapshot_model=OrderCommandResultView)
PosOrderCommand = (
    CreateCustomerOrderRequest
    | OrderActionRequest
    | DeliverCustomerOrderRequest
    | CancelCustomerOrderRequest
)


def _capability(command_code: OrderCommandCode) -> CapabilityCode:
    return "orders.cancel" if command_code == "cancel" else "orders.manage"


class OrdersIdempotencyService:
    def __init__(
        self,
        command_service: OrdersCommandService | None = None,
        admin_service: AdminOrdersService | None = None,
    ) -> None:
        self._commands = command_service or OrdersCommandService()
        self._admin = admin_service or AdminOrdersService()

    def execute_pos(
        self,
        session: Session,
        *,
        current_user: AuthenticatedUser,
        command_code: OrderCommandCode,
        command: PosOrderCommand,
        key: UUID,
        request_id: str | None,
        order_id: UUID | None = None,
    ) -> IdempotencyResult:
        expected_type = {
            "create": CreateCustomerOrderRequest,
            "mark-ready": OrderActionRequest,
            "deliver": DeliverCustomerOrderRequest,
            "cancel": CancelCustomerOrderRequest,
        }[command_code]
        if type(command) is not expected_type or (command_code == "create") != (order_id is None):
            raise IdempotencyBoundaryError("The order command does not match its operation.")
        prepared: PreparedOrderCreation | None = None

        def resolve_context(current: Session, saved: CommandContext | None) -> CommandContext:
            nonlocal prepared
            if saved is not None:
                return self._pos_context(
                    current,
                    current_user=current_user,
                    workstation_code=command.workstation_code,
                    cash_session_id=command.cash_session_id,
                )
            if isinstance(command, CreateCustomerOrderRequest):
                prepared = self._commands.prepare_create_order(
                    current, current_user=current_user, command=command
                )
                branch_id = prepared.context.branch_id
                workstation_id = prepared.context.workstation_id
            else:
                context, _cash_session = _resolve_context_and_open_session(
                    current,
                    workstation_access=WorkstationAccessService(),
                    current_user=current_user,
                    workstation_code=command.workstation_code,
                    cash_session_id=command.cash_session_id,
                )
                assert order_id is not None
                # Validate visibility before admission, but lock only inside the action.
                _get_order_for_branch(current, order_id=order_id, branch_id=context.branch_id)
                branch_id, workstation_id = context.branch_id, context.workstation_id
            return CommandContext(
                actor_user_id=current_user.id,
                surface="POS",
                branch_id=branch_id,
                workstation_id=workstation_id,
                cash_session_id=command.cash_session_id,
            )

        def action(current: Session) -> CommandResult:
            trace = self._trace(current, command_code, key)
            owner = execution(current)
            if owner is None or owner.record is None:
                raise IdempotencyBoundaryError("Order commands require their reserved context.")
            context = owner.record
            if context.workstation_id is None or context.branch_id is None:
                raise IdempotencyBoundaryError("POS orders require a workstation and branch.")
            # Reserve identity first, then serialize the shift before locking the order.
            lock_cash_session(
                current,
                current_user=current_user,
                workstation_id=context.workstation_id,
                branch_id=context.branch_id,
                cash_session_id=command.cash_session_id,
            )
            if isinstance(command, CreateCustomerOrderRequest):
                if prepared is None:
                    raise IdempotencyBoundaryError("Order creation requires validated preparation.")
                result = self._commands.create_order(
                    current,
                    current_user=current_user,
                    command=command,
                    prepared=prepared,
                    trace=trace,
                    request_id=request_id,
                )
            else:
                assert order_id is not None
                if isinstance(command, OrderActionRequest):
                    result = self._commands.mark_ready(
                        current,
                        current_user=current_user,
                        order_id=order_id,
                        command=command,
                        trace=trace,
                        request_id=request_id,
                    )
                elif isinstance(command, DeliverCustomerOrderRequest):
                    result = self._commands.deliver_order(
                        current,
                        current_user=current_user,
                        order_id=order_id,
                        command=command,
                        trace=trace,
                        request_id=request_id,
                    )
                else:
                    result = self._commands.cancel_order(
                        current,
                        current_user=current_user,
                        order_id=order_id,
                        command=command,
                        trace=trace,
                        request_id=request_id,
                    )
            return CommandResult(
                status_code=201 if command_code == "create" else 200,
                snapshot=result,
                resource_type="customer_order",
                resource_id=str(result.id),
            )

        return IdempotencyExecutor().execute(
            session,
            key=key,
            operation_code=ORDER_COMMAND_OPERATIONS[command_code],
            payload={"order_id": order_id, "command": command},
            resolve_context=resolve_context,
            authorize=lambda current, context: self._authorize(
                current, current_user, context, command_code
            ),
            action=action,
            response_policy=ORDER_COMMAND_RESPONSE_POLICY,
            request_id=request_id,
        )

    def execute_admin(
        self,
        session: Session,
        *,
        current_user: AuthenticatedUser,
        command_code: AdminOrderCommandCode,
        order_id: UUID,
        key: UUID,
        request_id: str | None,
    ) -> IdempotencyResult:
        def resolve_context(current: Session, saved: CommandContext | None) -> CommandContext:
            branch_id = (
                saved.branch_id if saved else _get_order(current, order_id=order_id).branch_id
            )
            return CommandContext(
                actor_user_id=current_user.id, surface="BACKOFFICE", branch_id=branch_id
            )

        def action(current: Session) -> CommandResult:
            method = {
                "mark-ready": self._admin.mark_ready,
                "deliver": self._admin.deliver_order,
                "cancel": self._admin.cancel_order,
            }[command_code]
            result = method(
                current,
                actor_id=current_user.id,
                order_id=order_id,
                request_id=request_id,
                trace=self._trace(current, command_code, key),
            )
            return CommandResult(
                status_code=200,
                snapshot=result,
                resource_type="customer_order",
                resource_id=str(result.id),
            )

        return IdempotencyExecutor().execute(
            session,
            key=key,
            operation_code=ORDER_COMMAND_OPERATIONS[command_code],
            payload={"order_id": order_id},
            resolve_context=resolve_context,
            authorize=lambda current, context: self._authorize(
                current, current_user, context, command_code
            ),
            action=action,
            response_policy=ORDER_COMMAND_RESPONSE_POLICY,
            request_id=request_id,
        )

    def recover_pos(
        self,
        session: Session,
        *,
        current_user: AuthenticatedUser,
        command_code: OrderCommandCode,
        key: UUID,
        workstation_code: str,
        cash_session_id: UUID,
    ) -> IdempotencyResult:
        self._bind_recovery(session, current_user, command_code, "POS")
        return IdempotencyExecutor().recover(
            session,
            key=key,
            operation_code=ORDER_COMMAND_OPERATIONS[command_code],
            resolve_context=lambda current, _saved: self._pos_context(
                current,
                current_user=current_user,
                workstation_code=workstation_code,
                cash_session_id=cash_session_id,
            ),
            authorize=lambda current, context: self._authorize(
                current, current_user, context, command_code
            ),
            response_policy=ORDER_COMMAND_RESPONSE_POLICY,
        )

    def recover_admin(
        self,
        session: Session,
        *,
        current_user: AuthenticatedUser,
        command_code: AdminOrderCommandCode,
        key: UUID,
        branch_id: UUID,
    ) -> IdempotencyResult:
        self._bind_recovery(session, current_user, command_code, "BACKOFFICE")
        require_branches(current_user, _capability(command_code), [branch_id])
        return IdempotencyExecutor().recover(
            session,
            key=key,
            operation_code=ORDER_COMMAND_OPERATIONS[command_code],
            resolve_context=lambda _current, _saved: CommandContext(
                actor_user_id=current_user.id, surface="BACKOFFICE", branch_id=branch_id
            ),
            authorize=lambda current, context: self._authorize(
                current, current_user, context, command_code
            ),
            response_policy=ORDER_COMMAND_RESPONSE_POLICY,
        )

    @staticmethod
    def _trace(session: Session, command_code: OrderCommandCode, key: UUID) -> OrderCommandTrace:
        owner = execution(session)
        if owner is None or owner.record is None:
            raise IdempotencyBoundaryError("An order action requires an owned command reservation.")
        return OrderCommandTrace(key, owner.record.id, ORDER_COMMAND_OPERATIONS[command_code])

    @staticmethod
    def _pos_context(
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
            raise auth_error(403, "FORBIDDEN", "The order context is not authorized.")
        # Historical contexts need not have an OPEN cash session; identity must still match exactly.
        return CommandContext(
            actor_user_id=current_user.id,
            surface="POS",
            branch_id=workstation.branch_id,
            workstation_id=workstation.id,
            cash_session_id=cash_session_id,
        )

    @staticmethod
    def _authorize(
        session: Session,
        current_user: AuthenticatedUser,
        context: CommandContext,
        command_code: OrderCommandCode,
    ) -> None:
        if context.branch_id is None:
            raise IdempotencyBoundaryError("An order command requires a branch.")
        if current_user.authorization_surface != context.surface:
            raise auth_error(403, "FORBIDDEN", "The order application surface is not authorized.")
        refreshed = resolve_authorization(session, current_user, surface=context.surface)
        require_branches(refreshed, _capability(command_code), [context.branch_id])

    @staticmethod
    def _bind_recovery(
        session: Session,
        current_user: AuthenticatedUser,
        command_code: OrderCommandCode,
        surface: IdentitySurface,
    ) -> None:
        if current_user.authorization_surface != surface:
            raise auth_error(403, "FORBIDDEN", "The order application surface is not authorized.")
        bind_authorization_scope(
            session,
            user=current_user,
            capabilities=(_capability(command_code),),
            mutation=False,
            surface=surface,
        )
