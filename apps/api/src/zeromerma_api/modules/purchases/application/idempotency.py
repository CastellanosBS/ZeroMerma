from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from zeromerma_api.db.access_scope import bind_authorization_scope
from zeromerma_api.modules.branches.infrastructure.models import Branch
from zeromerma_api.modules.idempotency.application.context import execution
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
from zeromerma_api.modules.identity.application.authorization import (
    require_branches,
    resolve_authorization,
)
from zeromerma_api.modules.identity.application.schemas import AuthenticatedUser, CapabilityCode
from zeromerma_api.modules.identity.application.session_services import auth_error
from zeromerma_api.modules.purchases.application.admin_schemas import (
    AdminPurchaseCancelRequest,
    AdminPurchaseCreateRequest,
    AdminPurchaseDirectEntryRequest,
    AdminPurchaseReceiveRequest,
    AdminPurchaseUpdateRequest,
    PurchaseCommandCode,
    PurchaseCommandLineResultView,
    PurchaseCommandRejectionView,
    PurchaseCommandResultView,
)
from zeromerma_api.modules.purchases.application.admin_services import AdminPurchaseService
from zeromerma_api.modules.purchases.domain.exceptions import (
    PurchaseNotFoundError,
    PurchaseValidationError,
)
from zeromerma_api.modules.purchases.infrastructure.models import PurchaseDocument

PurchaseCommand = (
    AdminPurchaseCreateRequest
    | AdminPurchaseUpdateRequest
    | AdminPurchaseDirectEntryRequest
    | AdminPurchaseReceiveRequest
    | AdminPurchaseCancelRequest
)
PURCHASE_OPERATIONS: dict[PurchaseCommandCode, str] = {
    "create": "purchase.create",
    "update": "purchase.update",
    "direct-entry": "purchase.direct_entry",
    "confirm": "purchase.confirm",
    "receive": "purchase.receive",
    "cancel": "purchase.cancel",
}
PURCHASE_RESPONSE_POLICY = ResponsePolicy(
    snapshot_model=PurchaseCommandResultView,
    rejection_model=PurchaseCommandRejectionView,
)


def _capability(code: PurchaseCommandCode) -> CapabilityCode:
    capabilities: dict[PurchaseCommandCode, CapabilityCode] = {
        "create": "purchases.manage",
        "update": "purchases.manage",
        "direct-entry": "purchases.manage",
        "confirm": "purchases.confirm",
        "receive": "purchases.receive",
        "cancel": "purchases.cancel",
    }
    return capabilities[code]


class PurchaseCommandService:
    def __init__(self, commands: AdminPurchaseService | None = None) -> None:
        self._commands = commands or AdminPurchaseService()

    def execute(
        self,
        session: Session,
        *,
        current_user: AuthenticatedUser,
        command_code: PurchaseCommandCode,
        command: PurchaseCommand | None,
        key: UUID,
        request_id: str | None,
        purchase_id: UUID | None = None,
    ) -> IdempotencyResult:
        expected = {
            "create": AdminPurchaseCreateRequest,
            "update": AdminPurchaseUpdateRequest,
            "direct-entry": AdminPurchaseDirectEntryRequest,
            "confirm": type(None),
            "receive": AdminPurchaseReceiveRequest,
            "cancel": AdminPurchaseCancelRequest,
        }[command_code]
        if type(command) is not expected or (command_code in {"create", "direct-entry"}) != (
            purchase_id is None
        ):
            raise IdempotencyBoundaryError("The purchase command does not match its operation.")
        if current_user.authorization_surface != "BACKOFFICE":
            raise auth_error(403, "FORBIDDEN", "Backoffice access is required.")
        bind_authorization_scope(
            session,
            user=current_user,
            capabilities=(_capability(command_code),),
            mutation=True,
            surface="BACKOFFICE",
        )

        def resolve_context(current: Session, saved: CommandContext | None) -> CommandContext:
            if saved is not None:
                return saved.model_copy(update={"actor_user_id": current_user.id})
            related: tuple[UUID, ...] = ()
            if isinstance(command, (AdminPurchaseCreateRequest, AdminPurchaseDirectEntryRequest)):
                branch_id = command.branch_id
            else:
                document = current.get(PurchaseDocument, purchase_id)
                if document is None:
                    raise PurchaseNotFoundError("Purchase was not found.")
                branch_id = document.receiving_branch_id
                if isinstance(command, AdminPurchaseUpdateRequest) and command.branch_id:
                    if command.branch_id != branch_id:
                        related = (command.branch_id,)
            return CommandContext(
                actor_user_id=current_user.id,
                surface="BACKOFFICE",
                branch_id=branch_id,
                related_branch_ids=related,
            )

        def action(current: Session) -> CommandResult:
            owner = execution(current)
            if owner is None or owner.record is None:
                raise IdempotencyBoundaryError("A purchase requires its command reservation.")
            try:
                if purchase_id is not None:
                    document = current.execute(
                        select(PurchaseDocument)
                        .where(PurchaseDocument.id == purchase_id)
                        .with_for_update()
                        .execution_options(populate_existing=True)
                    ).scalar_one_or_none()
                    if document is None:
                        raise PurchaseNotFoundError("Purchase was not found.")
                    if document.receiving_branch_id != owner.record.branch_id:
                        raise PurchaseValidationError(
                            "The purchase branch changed; refresh the document."
                        )
                if isinstance(command, AdminPurchaseCreateRequest):
                    detail = self._commands.create_purchase(
                        current,
                        command=command,
                        current_user=current_user,
                        request_id=request_id,
                    )
                elif isinstance(command, AdminPurchaseDirectEntryRequest):
                    detail = self._commands.create_direct_entry(
                        current,
                        command=command,
                        current_user=current_user,
                        request_id=request_id,
                    )
                else:
                    assert purchase_id is not None
                    if isinstance(command, AdminPurchaseUpdateRequest):
                        detail = self._commands.update_purchase(
                            current,
                            command=command,
                            current_user=current_user,
                            purchase_id=purchase_id,
                            request_id=request_id,
                        )
                    elif isinstance(command, AdminPurchaseReceiveRequest):
                        detail = self._commands.receive_purchase(
                            current,
                            command=command,
                            current_user=current_user,
                            purchase_id=purchase_id,
                            request_id=request_id,
                        )
                    elif isinstance(command, AdminPurchaseCancelRequest):
                        detail = self._commands.cancel_purchase(
                            current,
                            command=command,
                            current_user=current_user,
                            purchase_id=purchase_id,
                            request_id=request_id,
                        )
                    else:
                        detail = self._commands.confirm_purchase(
                            current,
                            current_user=current_user,
                            purchase_id=purchase_id,
                            request_id=request_id,
                        )
            except PurchaseValidationError as error:
                raise DeterministicRejection(
                    code="PURCHASE_COMMAND_REJECTED",
                    status_code=409,
                    message=str(error),
                    snapshot=PurchaseCommandRejectionView(message=str(error)),
                ) from error
            snapshot = PurchaseCommandResultView(
                id=detail.overview.id,
                branch_id=detail.overview.branch_id,
                folio=detail.overview.folio,
                status=detail.overview.status,
                document_type=detail.overview.document_type,
                receipt_ids=[
                    receipt.id
                    for receipt in self._commands._get_receipts(current, detail.overview.id)
                ],
                inventory_movement_ids=[
                    movement.id for movement in detail.inventory_impact.movements
                ],
                lines=[
                    PurchaseCommandLineResultView(
                        purchase_line_id=line.purchase_line_id,
                        product_id=line.product_id,
                        ordered_quantity=line.ordered_quantity,
                        received_quantity=line.received_quantity,
                        pending_quantity=line.pending_quantity,
                    )
                    for line in detail.lines
                ],
            )
            return CommandResult(
                status_code=201 if command_code in {"create", "direct-entry"} else 200,
                snapshot=snapshot,
                resource_type="purchase_document",
                resource_id=str(snapshot.id),
            )

        return IdempotencyExecutor().execute(
            session,
            key=key,
            operation_code=PURCHASE_OPERATIONS[command_code],
            payload={
                "purchase_id": purchase_id,
                "command": command.model_dump(
                    exclude_unset=isinstance(command, AdminPurchaseUpdateRequest)
                )
                if command is not None
                else None,
            },
            resolve_context=resolve_context,
            authorize=lambda current, context: self._authorize(
                current,
                current_user,
                context,
                command_code,
                confirm_now=isinstance(command, AdminPurchaseCreateRequest) and command.confirm_now,
            ),
            action=action,
            response_policy=PURCHASE_RESPONSE_POLICY,
            request_id=request_id,
        )

    def recover(
        self,
        session: Session,
        *,
        current_user: AuthenticatedUser,
        command_code: PurchaseCommandCode,
        key: UUID,
        branch_id: UUID,
    ) -> IdempotencyResult:
        bind_authorization_scope(
            session,
            user=current_user,
            capabilities=(_capability(command_code),),
            mutation=False,
            surface="BACKOFFICE",
        )
        return IdempotencyExecutor().recover(
            session,
            key=key,
            operation_code=PURCHASE_OPERATIONS[command_code],
            resolve_context=lambda _current, saved: CommandContext(
                actor_user_id=current_user.id,
                surface="BACKOFFICE",
                branch_id=branch_id,
                related_branch_ids=saved.related_branch_ids if saved else (),
            ),
            authorize=lambda current, context: self._authorize(
                current, current_user, context, command_code
            ),
            response_policy=PURCHASE_RESPONSE_POLICY,
        )

    @staticmethod
    def _authorize(
        session: Session,
        user: AuthenticatedUser,
        context: CommandContext,
        code: PurchaseCommandCode,
        *,
        confirm_now: bool = False,
    ) -> None:
        if user.authorization_surface != "BACKOFFICE" or context.branch_id is None:
            raise auth_error(403, "FORBIDDEN", "The purchase context is not authorized.")
        refreshed = resolve_authorization(session, user, surface="BACKOFFICE")
        require_branches(
            refreshed, _capability(code), [context.branch_id, *context.related_branch_ids]
        )
        for branch_id in (context.branch_id, *context.related_branch_ids):
            if session.get(Branch, branch_id) is None:
                raise PurchaseNotFoundError("Branch was not found.")
        if code == "create":
            owner = execution(session)
            record = owner.record if owner else None
            if record is not None and record.status == "COMPLETED":
                original_status = (record.response_payload or {}).get("status")
                if original_status not in {"DRAFT", "ORDERED"}:
                    raise IdempotencyBoundaryError("The original purchase state is unavailable.")
                confirm_now = confirm_now or original_status == "ORDERED"
            if confirm_now:
                require_branches(refreshed, "purchases.confirm", [context.branch_id])
