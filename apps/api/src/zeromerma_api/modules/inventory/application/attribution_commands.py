from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from zeromerma_api.modules.audit.application.service import AuditRecorder
from zeromerma_api.modules.cash.application.command_context import lock_cash_session
from zeromerma_api.modules.catalog.infrastructure.models import Product
from zeromerma_api.modules.idempotency.application.context import execution
from zeromerma_api.modules.idempotency.application.schemas import (
    CommandResult,
    IdempotencyResult,
    ResponsePolicy,
)
from zeromerma_api.modules.idempotency.application.service import IdempotencyExecutor
from zeromerma_api.modules.identity.application.schemas import AuthenticatedUser
from zeromerma_api.modules.inventory.application.attribution_schemas import (
    ClassAttributionRequest,
    ClassAttributionResult,
    ClassAttributionResultLine,
)
from zeromerma_api.modules.inventory.application.class_inventory import (
    attribute_class_inventory,
    lock_class_obligations,
)
from zeromerma_api.modules.inventory.application.mutations import (
    InventoryBalanceKey,
    lock_inventory_balances,
)
from zeromerma_api.modules.inventory.domain.quantities import InventoryLotQuantity
from zeromerma_api.modules.outbox.application.service import OutboxWriter
from zeromerma_api.modules.sales.application.idempotency import SaleConfirmationService
from zeromerma_api.modules.sales.infrastructure.models import Sale, SaleLine

OPERATION = "inventory.class_attribute"
POLICY = ResponsePolicy(snapshot_model=ClassAttributionResult)


def commit_class_attribution(
    session: Session,
    *,
    current_user: AuthenticatedUser,
    sale_id: UUID,
    command: ClassAttributionRequest,
    key: UUID,
    request_id: str | None,
) -> IdempotencyResult:
    def action(current: Session) -> CommandResult:
        owner = execution(current)
        if owner is None or owner.record is None:
            raise RuntimeError("Attribution requires its command owner.")
        context = SaleConfirmationService._request_context(
            current,
            current_user=current_user,
            workstation_code=command.workstation_code,
            cash_session_id=command.cash_session_id,
        )
        if context.branch_id is None or context.workstation_id is None:
            raise HTTPException(403, "Attribution requires a branch and workstation.")
        lock_cash_session(
            current,
            current_user=current_user,
            branch_id=context.branch_id,
            workstation_id=context.workstation_id,
            cash_session_id=command.cash_session_id,
        )
        sale = current.scalar(
            select(Sale)
            .where(Sale.id == sale_id, Sale.branch_id == context.branch_id)
            .with_for_update()
        )
        if sale is None:
            raise HTTPException(404, "Sale not found in this branch.")
        original = {
            line.id: line
            for line in current.scalars(select(SaleLine).where(SaleLine.sale_id == sale_id))
        }
        products = {
            product.id: product
            for product in current.scalars(
                select(Product).where(Product.id.in_([line.product_id for line in command.lines]))
            )
        }
        if any(
            line.sale_line_id not in original
            or original[line.sale_line_id].capture_mode != "CLASS_CAPTURE"
            or line.product_id not in products
            for line in command.lines
        ):
            raise HTTPException(
                409, "Only original class sale lines and exact existing products can be attributed."
            )
        balances = lock_inventory_balances(
            current,
            [
                InventoryBalanceKey(sale.branch_id, product.id, "COUNTER")
                for product in products.values()
                if product.is_inventory_tracked
            ],
        )
        obligations = lock_class_obligations(current, [line.sale_line_id for line in command.lines])
        result_lines = []
        for index, line in enumerate(command.lines):
            obligation = obligations.get(line.sale_line_id)
            if obligation is None:
                raise HTTPException(409, "The original physical obligation is missing.")
            attribution = attribute_class_inventory(
                current,
                balances=balances,
                obligation=obligation,
                product=products[line.product_id],
                quantity=line.quantity,
                actor_id=current_user.id,
                source_document_type="SALE_ATTRIBUTION",
                source_document_id=sale.id,
                causal_effect_code=f"attribution:{index}",
                lot_allocations=[InventoryLotQuantity(line.lot_id, line.quantity)]
                if line.lot_id
                else None,
            )
            current.flush()
            result_lines.append(
                ClassAttributionResultLine(
                    attribution_id=attribution.id,
                    sale_line_id=line.sale_line_id,
                    product_id=line.product_id,
                    quantity=line.quantity,
                    remaining_quantity=obligation.required_quantity
                    - obligation.attributed_quantity,
                    inventory_movement_id=attribution.inventory_movement_id,
                )
            )
        result = ClassAttributionResult(
            sale_id=sale.id, operation_id=owner.record.id, lines=result_lines
        )
        facts = result.model_dump(mode="json")
        AuditRecorder().record(
            current,
            actor_id=current_user.id,
            action="inventory.class_attributed",
            resource_type="sale",
            resource_id=str(sale.id),
            branch_id=sale.branch_id,
            request_id=request_id,
            metadata=facts,
        )
        OutboxWriter().append(
            current,
            aggregate_type="sale",
            aggregate_id=str(sale.id),
            event_name="inventory.class_attributed.v1",
            payload=facts,
            headers={"request_id": request_id} if request_id else {},
        )
        return CommandResult(
            status_code=200, snapshot=result, resource_type="sale", resource_id=str(sale.id)
        )

    return IdempotencyExecutor().execute(
        session,
        key=key,
        operation_code=OPERATION,
        payload={"sale_id": str(sale_id), **command.model_dump(mode="json")},
        resolve_context=lambda current, _: SaleConfirmationService._request_context(
            current,
            current_user=current_user,
            workstation_code=command.workstation_code,
            cash_session_id=command.cash_session_id,
        ),
        authorize=lambda current, context: SaleConfirmationService._authorize(
            current, current_user, context
        ),
        action=action,
        response_policy=POLICY,
        request_id=request_id,
    )
