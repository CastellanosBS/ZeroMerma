"""Audited, idempotent creation of explicit branch order policy versions."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from zeromerma_api.modules.audit.application.service import AuditRecorder
from zeromerma_api.modules.branches.infrastructure.models import Branch
from zeromerma_api.modules.idempotency.application.schemas import (
    CommandContext,
    CommandResult,
    IdempotencyResult,
    ResponsePolicy,
)
from zeromerma_api.modules.idempotency.application.service import IdempotencyExecutor
from zeromerma_api.modules.identity.application.authorization import (
    require_branches,
    resolve_authorization,
)
from zeromerma_api.modules.identity.application.schemas import AuthenticatedUser
from zeromerma_api.modules.orders.application.schemas import OrderPolicyRequest, OrderPolicyView
from zeromerma_api.modules.orders.domain.exceptions import OrderNotFoundError
from zeromerma_api.modules.orders.infrastructure.models import OrderCommitmentPolicy
from zeromerma_api.modules.outbox.application.service import OutboxWriter


def read_policy(session: Session, branch_id: UUID) -> OrderPolicyView | None:
    policy = session.scalar(
        select(OrderCommitmentPolicy)
        .where(OrderCommitmentPolicy.branch_id == branch_id)
        .order_by(OrderCommitmentPolicy.version.desc())
        .limit(1)
    )
    return _view(policy) if policy else None


def _view(policy: OrderCommitmentPolicy) -> OrderPolicyView:
    return OrderPolicyView(
        id=policy.id,
        branch_id=policy.branch_id,
        version=policy.version,
        lead_time_minutes=policy.lead_time_minutes,
        reason=policy.reason,
    )


def configure_policy(
    session: Session,
    *,
    branch_id: UUID,
    command: OrderPolicyRequest,
    current_user: AuthenticatedUser,
    key: UUID,
    request_id: str | None,
) -> IdempotencyResult:
    def context(current: Session, saved: CommandContext | None) -> CommandContext:
        if current.get(Branch, branch_id) is None:
            raise OrderNotFoundError("La sucursal no está disponible.")
        return CommandContext(
            actor_user_id=current_user.id, surface="BACKOFFICE", branch_id=branch_id
        )

    def action(current: Session) -> CommandResult:
        current.scalar(select(Branch).where(Branch.id == branch_id).with_for_update())
        previous = read_policy(current, branch_id)
        policy = OrderCommitmentPolicy(
            branch_id=branch_id,
            version=(previous.version + 1) if previous else 1,
            lead_time_minutes=command.lead_time_minutes,
            reason=command.reason.strip(),
            created_by_user_id=current_user.id,
        )
        current.add(policy)
        current.flush()
        result = _view(policy)
        AuditRecorder().record(
            current,
            actor_id=current_user.id,
            action="order.policy_configured",
            resource_type="order_commitment_policy",
            resource_id=str(policy.id),
            branch_id=branch_id,
            request_id=request_id,
            metadata=result.model_dump(mode="json"),
        )
        OutboxWriter().append(
            current,
            aggregate_type="order_commitment_policy",
            aggregate_id=str(policy.id),
            event_name="order.policy_configured.v1",
            payload=result.model_dump(mode="json"),
            headers={"request_id": request_id},
        )
        return CommandResult(
            status_code=201,
            snapshot=result,
            resource_type="order_commitment_policy",
            resource_id=str(policy.id),
        )

    def authorize(current: Session, resolved: CommandContext) -> None:
        refreshed = resolve_authorization(current, current_user, surface="BACKOFFICE")
        require_branches(refreshed, "orders.manage", [branch_id])

    return IdempotencyExecutor().execute(
        session,
        key=key,
        operation_code="order.policy.configure",
        payload={"branch_id": branch_id, "command": command},
        resolve_context=context,
        authorize=authorize,
        action=action,
        response_policy=ResponsePolicy(snapshot_model=OrderPolicyView),
        request_id=request_id,
    )


def recover_policy(
    session: Session, *, branch_id: UUID, current_user: AuthenticatedUser, key: UUID
) -> IdempotencyResult:
    def authorize(current: Session, context: CommandContext) -> None:
        refreshed = resolve_authorization(current, current_user, surface="BACKOFFICE")
        require_branches(refreshed, "orders.manage", [branch_id])

    return IdempotencyExecutor().recover(
        session,
        key=key,
        operation_code="order.policy.configure",
        resolve_context=lambda current, saved: CommandContext(
            actor_user_id=current_user.id, surface="BACKOFFICE", branch_id=branch_id
        ),
        authorize=authorize,
        response_policy=ResponsePolicy(snapshot_model=OrderPolicyView),
    )
