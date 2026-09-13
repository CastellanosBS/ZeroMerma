from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import ROUND_HALF_UP, Decimal

from pydantic import TypeAdapter
from sqlalchemy import String, cast, delete, or_, select
from sqlalchemy.orm import Session

from zeromerma_api.modules.audit.application.service import AuditRecorder
from zeromerma_api.modules.branches.infrastructure.models import Branch
from zeromerma_api.modules.catalog.domain.constants import CATALOG_PRODUCT_KIND_FINISHED_GOOD
from zeromerma_api.modules.catalog.infrastructure.models import Product, Recipe, RecipeInput
from zeromerma_api.modules.identity.application.actions import restrict_actions
from zeromerma_api.modules.identity.application.schemas import AuthenticatedUser
from zeromerma_api.modules.identity.infrastructure.models import User
from zeromerma_api.modules.inventory.domain.constants import (
    INVENTORY_LOCATION_BACKROOM,
    INVENTORY_MOVEMENT_DIRECTION_IN,
    INVENTORY_MOVEMENT_DIRECTION_OUT,
    INVENTORY_MOVEMENT_TYPE_PRODUCTION_CONSUMPTION,
    INVENTORY_MOVEMENT_TYPE_PRODUCTION_OUTPUT,
)
from zeromerma_api.modules.inventory.infrastructure.models import (
    InventoryBalance,
    InventoryMovement,
)
from zeromerma_api.modules.outbox.application.service import OutboxWriter
from zeromerma_api.modules.production.application.admin_schemas import (
    AdminProductionActualConsumptionLineView,
    AdminProductionAvailableActionsView,
    AdminProductionCancelRequest,
    AdminProductionCompleteRequest,
    AdminProductionCreateRequest,
    AdminProductionDetailView,
    AdminProductionFilterOptionsView,
    AdminProductionFilterOptionView,
    AdminProductionInputLineView,
    AdminProductionInputStatus,
    AdminProductionInventoryImpactView,
    AdminProductionInventoryMovementView,
    AdminProductionListItemView,
    AdminProductionListResponse,
    AdminProductionMetricsView,
    AdminProductionOutputYieldView,
    AdminProductionOverviewView,
    AdminProductionProductRecipeView,
    AdminProductionRelatedDocumentView,
    AdminProductionStartRequest,
    AdminProductionStatus,
    AdminProductionUpdateRequest,
    AdminProductionWarningSeverity,
    AdminProductionWarningView,
    AdminProductionWasteScrapView,
)
from zeromerma_api.modules.production.domain.constants import (
    AUDIT_ACTION_ADMIN_PRODUCTION_CANCELLED,
    AUDIT_ACTION_ADMIN_PRODUCTION_COMPLETED,
    AUDIT_ACTION_ADMIN_PRODUCTION_CREATED,
    AUDIT_ACTION_ADMIN_PRODUCTION_STARTED,
    AUDIT_ACTION_ADMIN_PRODUCTION_UPDATED,
    OUTBOX_EVENT_ADMIN_PRODUCTION_CANCELLED_V1,
    OUTBOX_EVENT_ADMIN_PRODUCTION_COMPLETED_V1,
    OUTBOX_EVENT_ADMIN_PRODUCTION_CREATED_V1,
    OUTBOX_EVENT_ADMIN_PRODUCTION_STARTED_V1,
    OUTBOX_EVENT_ADMIN_PRODUCTION_UPDATED_V1,
    PRODUCTION_INPUT_STATUS_AVAILABLE,
    PRODUCTION_INPUT_STATUS_INSUFFICIENT,
    PRODUCTION_INPUT_STATUS_UNAVAILABLE,
    PRODUCTION_RESOURCE_TYPE,
    PRODUCTION_SOURCE_DOCUMENT_TYPE,
    PRODUCTION_STATUS_CANCELLED,
    PRODUCTION_STATUS_COMPLETED,
    PRODUCTION_STATUS_DRAFT,
    PRODUCTION_STATUS_IN_PROGRESS,
)
from zeromerma_api.modules.production.domain.exceptions import (
    ProductionNotFoundError,
    ProductionValidationError,
)
from zeromerma_api.modules.production.infrastructure.models import (
    ProductionBatch,
    ProductionBatchInput,
)

_ADMIN_PRODUCTION_INPUT_STATUS_ADAPTER: TypeAdapter[AdminProductionInputStatus] = TypeAdapter(
    AdminProductionInputStatus
)
_ADMIN_PRODUCTION_STATUS_ADAPTER: TypeAdapter[AdminProductionStatus] = TypeAdapter(
    AdminProductionStatus
)
DECIMAL_3 = Decimal("0.001")
DECIMAL_4 = Decimal("0.0001")
ZERO = Decimal("0")


@dataclass(frozen=True)
class _ProductionRow:
    batch: ProductionBatch
    branch: Branch
    created_by_user: User
    product: Product
    recipe: Recipe


@dataclass(frozen=True)
class _InputPlan:
    input_product: Product
    required_qty: Decimal
    available_qty: Decimal
    shortage_qty: Decimal
    status: str
    display_order: int


class AdminProductionService:
    def __init__(
        self,
        audit_recorder: AuditRecorder | None = None,
        outbox_writer: OutboxWriter | None = None,
    ) -> None:
        self._audit_recorder = audit_recorder or AuditRecorder()
        self._outbox_writer = outbox_writer or OutboxWriter()

    def list_production(
        self,
        session: Session,
        *,
        branch_id: uuid.UUID | None,
        date_from: datetime | None,
        date_to: datetime | None,
        operator_user_id: uuid.UUID | None,
        product_id: uuid.UUID | None,
        recipe_id: uuid.UUID | None,
        search: str | None,
        status_filter: str | None,
        variance_state: str | None,
        warning_state: str | None,
        page: int,
        page_size: int,
    ) -> AdminProductionListResponse:
        rows = self._fetch_rows(
            session,
            branch_id=branch_id,
            date_from=date_from,
            date_to=date_to,
            product_id=product_id,
            recipe_id=recipe_id,
            search=search,
            status_filter=status_filter,
        )

        if operator_user_id is not None:
            rows = [
                row
                for row in rows
                if operator_user_id
                in {
                    row.batch.created_by_user_id,
                    row.batch.started_by_user_id,
                    row.batch.completed_by_user_id,
                    row.batch.cancelled_by_user_id,
                }
            ]

        normalized_variance = _normalize_optional(variance_state)
        if normalized_variance == "with_variance":
            rows = [row for row in rows if row.batch.variance_qty not in (None, ZERO)]
        elif normalized_variance == "without_variance":
            rows = [row for row in rows if row.batch.variance_qty in (None, ZERO)]

        normalized_warning = _normalize_optional(warning_state)
        if normalized_warning and normalized_warning != "all":
            rows = [row for row in rows if self._warning_state(session, row) == normalized_warning]

        items = [self._to_list_item(session, row) for row in rows]
        total = len(items)
        safe_page = max(page, 1)
        safe_page_size = min(max(page_size, 1), 100)
        offset = (safe_page - 1) * safe_page_size

        return AdminProductionListResponse(
            filter_options=self._build_filter_options(session),
            items=items[offset : offset + safe_page_size],
            metrics=self._build_metrics(session, rows),
            page=safe_page,
            page_size=safe_page_size,
            total=total,
        )

    def get_production_detail(
        self, session: Session, *, production_id: uuid.UUID
    ) -> AdminProductionDetailView:
        return self._to_detail(session, self._get_row(session, production_id))

    def create_production(
        self,
        session: Session,
        *,
        command: AdminProductionCreateRequest,
        current_user: AuthenticatedUser,
        request_id: str | None,
    ) -> AdminProductionDetailView:
        branch = self._get_branch(session, command.branch_id)
        product = self._get_finished_product(session, command.product_id)
        recipe = self._resolve_recipe(session, product_id=product.id, recipe_id=command.recipe_id)

        batch = ProductionBatch(
            branch_id=branch.id,
            created_by_user_id=current_user.id,
            notes=command.notes,
            planned_at=command.planned_at,
            planned_output_qty=_q3(command.planned_output_qty),
            product_id=product.id,
            recipe_id=recipe.id,
            status=PRODUCTION_STATUS_DRAFT,
        )
        session.add(batch)
        session.flush()
        self._replace_input_plan(session, batch=batch, recipe=recipe, branch=branch)
        self._record_change(
            session,
            action=AUDIT_ACTION_ADMIN_PRODUCTION_CREATED,
            batch=batch,
            current_user=current_user,
            event_name=OUTBOX_EVENT_ADMIN_PRODUCTION_CREATED_V1,
            metadata={"product_id": str(product.id), "recipe_id": str(recipe.id)},
            request_id=request_id,
        )
        session.commit()
        return self.get_production_detail(session, production_id=batch.id)

    def update_production(
        self,
        session: Session,
        *,
        command: AdminProductionUpdateRequest,
        current_user: AuthenticatedUser,
        production_id: uuid.UUID,
        request_id: str | None,
    ) -> AdminProductionDetailView:
        row = self._get_row(session, production_id)
        if row.batch.status != PRODUCTION_STATUS_DRAFT:
            raise ProductionValidationError("Only draft production can be edited.")

        product = row.product
        if command.product_id is not None and command.product_id != row.product.id:
            product = self._get_finished_product(session, command.product_id)

        recipe_id: uuid.UUID | None = (
            command.recipe_id if command.recipe_id is not None else row.recipe.id
        )
        if product.id != row.product.id and command.recipe_id is None:
            recipe_id = None
        recipe = self._resolve_recipe(session, product_id=product.id, recipe_id=recipe_id)

        row.batch.product_id = product.id
        row.batch.recipe_id = recipe.id
        if command.planned_output_qty is not None:
            row.batch.planned_output_qty = _q3(command.planned_output_qty)
        if "planned_at" in command.model_fields_set:
            row.batch.planned_at = command.planned_at
        if "notes" in command.model_fields_set:
            row.batch.notes = command.notes
        self._replace_input_plan(session, batch=row.batch, recipe=recipe, branch=row.branch)
        self._record_change(
            session,
            action=AUDIT_ACTION_ADMIN_PRODUCTION_UPDATED,
            batch=row.batch,
            current_user=current_user,
            event_name=OUTBOX_EVENT_ADMIN_PRODUCTION_UPDATED_V1,
            metadata={"product_id": str(product.id), "recipe_id": str(recipe.id)},
            request_id=request_id,
        )
        session.commit()
        return self.get_production_detail(session, production_id=row.batch.id)

    def start_production(
        self,
        session: Session,
        *,
        command: AdminProductionStartRequest,
        current_user: AuthenticatedUser,
        production_id: uuid.UUID,
        request_id: str | None,
    ) -> AdminProductionDetailView:
        row = self._get_row(session, production_id)
        if row.batch.status != PRODUCTION_STATUS_DRAFT:
            raise ProductionValidationError("Only draft production can be started.")
        if not row.branch.is_active:
            raise ProductionValidationError("Production branch is inactive.")
        if not row.product.is_active:
            raise ProductionValidationError("Production product is inactive.")
        if not row.recipe.is_active:
            raise ProductionValidationError("Production recipe is inactive.")

        self._replace_input_plan(session, batch=row.batch, recipe=row.recipe, branch=row.branch)
        shortages = self._list_inputs(session, row.batch.id)
        if any((line.shortage_qty_snapshot or ZERO) > ZERO for line in shortages):
            raise ProductionValidationError(
                "Production cannot start while raw material shortages exist."
            )

        row.batch.status = PRODUCTION_STATUS_IN_PROGRESS
        row.batch.started_at = _utc_now()
        row.batch.started_by_user_id = current_user.id
        if command.notes is not None:
            row.batch.notes = command.notes
        self._record_change(
            session,
            action=AUDIT_ACTION_ADMIN_PRODUCTION_STARTED,
            batch=row.batch,
            current_user=current_user,
            event_name=OUTBOX_EVENT_ADMIN_PRODUCTION_STARTED_V1,
            metadata={},
            request_id=request_id,
        )
        session.commit()
        return self.get_production_detail(session, production_id=row.batch.id)

    def complete_production(
        self,
        session: Session,
        *,
        command: AdminProductionCompleteRequest,
        current_user: AuthenticatedUser,
        production_id: uuid.UUID,
        request_id: str | None,
    ) -> AdminProductionDetailView:
        row = self._get_row(session, production_id)
        if row.batch.status != PRODUCTION_STATUS_IN_PROGRESS:
            raise ProductionValidationError("Only in-progress production can be completed.")

        actual_output = _q3(command.actual_output_qty)
        variance_qty = _q3(actual_output - row.batch.planned_output_qty)
        if actual_output == ZERO and command.variance_reason is None:
            raise ProductionValidationError("Zero output requires a variance reason.")
        if variance_qty != ZERO and command.variance_reason is None:
            raise ProductionValidationError("Yield variance requires a reason.")

        inputs = self._list_inputs(session, row.batch.id)
        if not inputs:
            raise ProductionValidationError("Production requires recipe inputs.")

        now = _utc_now()
        for input_line in inputs:
            input_product = self._get_product(session, input_line.input_product_id)
            balance = self._get_balance(
                session,
                product_id=input_line.input_product_id,
                branch_id=row.branch.id,
                location_code=INVENTORY_LOCATION_BACKROOM,
                for_update=True,
            )
            available = Decimal(balance.quantity_on_hand) if balance is not None else ZERO
            required = Decimal(input_line.required_qty)
            if available < required:
                raise ProductionValidationError(
                    "Raw material stock changed and is no longer sufficient."
                )
            assert balance is not None
            balance.quantity_on_hand = _q3(available - required)
            input_line.consumed_qty = required
            input_line.available_qty_snapshot = available
            input_line.shortage_qty_snapshot = ZERO
            input_line.status = PRODUCTION_INPUT_STATUS_AVAILABLE
            session.add(
                InventoryMovement(
                    balance_after=balance.quantity_on_hand,
                    branch_id=row.branch.id,
                    direction=INVENTORY_MOVEMENT_DIRECTION_OUT,
                    location_code=INVENTORY_LOCATION_BACKROOM,
                    movement_type=INVENTORY_MOVEMENT_TYPE_PRODUCTION_CONSUMPTION,
                    notes=command.notes,
                    operator_user_id=current_user.id,
                    product_id=input_line.input_product_id,
                    quantity=required,
                    reason="Production raw material consumption",
                    source_document_id=row.batch.id,
                    source_document_type=PRODUCTION_SOURCE_DOCUMENT_TYPE,
                    unit_of_measure=input_product.unit_of_measure,
                ),
            )

        if actual_output > ZERO:
            output_balance = self._get_or_create_balance(
                session,
                product_id=row.product.id,
                branch_id=row.branch.id,
                location_code=INVENTORY_LOCATION_BACKROOM,
            )
            previous_output = Decimal(output_balance.quantity_on_hand)
            output_balance.quantity_on_hand = _q3(previous_output + actual_output)
            session.add(
                InventoryMovement(
                    balance_after=output_balance.quantity_on_hand,
                    branch_id=row.branch.id,
                    direction=INVENTORY_MOVEMENT_DIRECTION_IN,
                    location_code=INVENTORY_LOCATION_BACKROOM,
                    movement_type=INVENTORY_MOVEMENT_TYPE_PRODUCTION_OUTPUT,
                    notes=command.notes,
                    operator_user_id=current_user.id,
                    product_id=row.product.id,
                    quantity=actual_output,
                    reason="Production finished goods output",
                    source_document_id=row.batch.id,
                    source_document_type=PRODUCTION_SOURCE_DOCUMENT_TYPE,
                    unit_of_measure=row.product.unit_of_measure,
                ),
            )

        row.batch.actual_output_qty = actual_output
        row.batch.completed_at = now
        row.batch.completed_by_user_id = current_user.id
        row.batch.notes = command.notes
        row.batch.status = PRODUCTION_STATUS_COMPLETED
        row.batch.variance_qty = variance_qty
        row.batch.variance_percent = _variance_percent(variance_qty, row.batch.planned_output_qty)
        row.batch.variance_reason = command.variance_reason
        self._record_change(
            session,
            action=AUDIT_ACTION_ADMIN_PRODUCTION_COMPLETED,
            batch=row.batch,
            current_user=current_user,
            event_name=OUTBOX_EVENT_ADMIN_PRODUCTION_COMPLETED_V1,
            metadata={
                "actual_output_qty": str(actual_output),
                "variance_qty": str(variance_qty),
                "variance_reason": command.variance_reason,
            },
            request_id=request_id,
        )
        session.commit()
        return self.get_production_detail(session, production_id=row.batch.id)

    def cancel_production(
        self,
        session: Session,
        *,
        command: AdminProductionCancelRequest,
        current_user: AuthenticatedUser,
        production_id: uuid.UUID,
        request_id: str | None,
    ) -> AdminProductionDetailView:
        row = self._get_row(session, production_id)
        if row.batch.status == PRODUCTION_STATUS_COMPLETED:
            raise ProductionValidationError(
                "Completed production cannot be cancelled. "
                "Use corrections or inventory adjustments."
            )
        if row.batch.status == PRODUCTION_STATUS_CANCELLED:
            raise ProductionValidationError("Production is already cancelled.")
        row.batch.status = PRODUCTION_STATUS_CANCELLED
        row.batch.cancelled_at = _utc_now()
        row.batch.cancelled_by_user_id = current_user.id
        if command.reason:
            row.batch.notes = command.reason
        self._record_change(
            session,
            action=AUDIT_ACTION_ADMIN_PRODUCTION_CANCELLED,
            batch=row.batch,
            current_user=current_user,
            event_name=OUTBOX_EVENT_ADMIN_PRODUCTION_CANCELLED_V1,
            metadata={"reason": command.reason},
            request_id=request_id,
        )
        session.commit()
        return self.get_production_detail(session, production_id=row.batch.id)

    def _fetch_rows(
        self,
        session: Session,
        *,
        branch_id: uuid.UUID | None,
        date_from: datetime | None,
        date_to: datetime | None,
        product_id: uuid.UUID | None,
        recipe_id: uuid.UUID | None,
        search: str | None,
        status_filter: str | None,
    ) -> list[_ProductionRow]:
        query = (
            select(ProductionBatch, Branch, Product, Recipe, User)
            .join(Branch, Branch.id == ProductionBatch.branch_id)
            .join(Product, Product.id == ProductionBatch.product_id)
            .join(Recipe, Recipe.id == ProductionBatch.recipe_id)
            .join(User, User.id == ProductionBatch.created_by_user_id)
            .order_by(ProductionBatch.created_at.desc())
        )
        if branch_id is not None:
            query = query.where(ProductionBatch.branch_id == branch_id)
        if product_id is not None:
            query = query.where(ProductionBatch.product_id == product_id)
        if recipe_id is not None:
            query = query.where(ProductionBatch.recipe_id == recipe_id)
        if date_from is not None:
            query = query.where(ProductionBatch.created_at >= date_from)
        if date_to is not None:
            query = query.where(ProductionBatch.created_at <= date_to)
        normalized_status = _normalize_optional(status_filter)
        if normalized_status and normalized_status != "all":
            query = query.where(ProductionBatch.status == normalized_status)
        normalized_search = _normalize_optional(search)
        if normalized_search:
            pattern = f"%{normalized_search.lower()}%"
            id_pattern = pattern
            if normalized_search.lower().startswith("prod-"):
                id_pattern = f"{normalized_search[5:].lower()}%"
            query = query.where(
                or_(
                    Branch.name.ilike(pattern),
                    Branch.code.ilike(pattern),
                    Product.name.ilike(pattern),
                    Product.code.ilike(pattern),
                    Recipe.version_name.ilike(pattern),
                    cast(ProductionBatch.id, String).ilike(id_pattern),
                ),
            )
        return [
            _ProductionRow(
                batch=batch, branch=branch, created_by_user=user, product=product, recipe=recipe
            )
            for batch, branch, product, recipe, user in session.execute(query).all()
        ]

    def _get_row(self, session: Session, production_id: uuid.UUID) -> _ProductionRow:
        row = session.execute(
            select(ProductionBatch, Branch, Product, Recipe, User)
            .join(Branch, Branch.id == ProductionBatch.branch_id)
            .join(Product, Product.id == ProductionBatch.product_id)
            .join(Recipe, Recipe.id == ProductionBatch.recipe_id)
            .join(User, User.id == ProductionBatch.created_by_user_id)
            .where(ProductionBatch.id == production_id),
        ).one_or_none()
        if row is None:
            raise ProductionNotFoundError("Production batch was not found.")
        batch, branch, product, recipe, user = row
        return _ProductionRow(
            batch=batch, branch=branch, created_by_user=user, product=product, recipe=recipe
        )

    def _to_detail(self, session: Session, row: _ProductionRow) -> AdminProductionDetailView:
        input_rows = self._list_inputs(session, row.batch.id)
        warnings = self._build_warnings(session, row)
        warning_state = self._warning_state_from_warnings(warnings)
        started_by = (
            session.get(User, row.batch.started_by_user_id)
            if row.batch.started_by_user_id
            else None
        )
        completed_by = (
            session.get(User, row.batch.completed_by_user_id)
            if row.batch.completed_by_user_id
            else None
        )
        return AdminProductionDetailView(
            actual_consumption=[
                AdminProductionActualConsumptionLineView(
                    consumed_qty=input_line.consumed_qty,
                    difference_qty=(
                        _q3(Decimal(input_line.consumed_qty) - Decimal(input_line.required_qty))
                        if input_line.consumed_qty is not None
                        else None
                    ),
                    expected_qty=input_line.required_qty,
                    input_product_code=input_product.code,
                    input_product_id=input_product.id,
                    input_product_name=input_product.name,
                    uom=input_line.unit_of_measure,
                )
                for input_line, input_product in self._input_rows_with_products(session, input_rows)
            ],
            available_actions=restrict_actions(
                session,
                AdminProductionAvailableActionsView(
                    can_cancel=row.batch.status
                    in {PRODUCTION_STATUS_DRAFT, PRODUCTION_STATUS_IN_PROGRESS},
                    can_complete=row.batch.status == PRODUCTION_STATUS_IN_PROGRESS,
                    can_edit=row.batch.status == PRODUCTION_STATUS_DRAFT,
                    can_start=row.batch.status == PRODUCTION_STATUS_DRAFT,
                    can_view_movements=True,
                ),
                {
                    "can_cancel": "production.cancel",
                    "can_complete": "production.execute",
                    "can_edit": "production.manage",
                    "can_start": "production.execute",
                    "can_view_movements": "inventory.view",
                },
                branch_ids=(row.branch.id,),
                global_only=False,
            ),
            inventory_impact=self._inventory_impact(session, row.batch.id),
            output_yield=AdminProductionOutputYieldView(
                actual_output_qty=row.batch.actual_output_qty,
                planned_output_qty=row.batch.planned_output_qty,
                uom=row.product.unit_of_measure,
                variance_percent=row.batch.variance_percent,
                variance_qty=row.batch.variance_qty,
                variance_reason=row.batch.variance_reason,
            ),
            overview=AdminProductionOverviewView(
                actual_output_qty=row.batch.actual_output_qty,
                branch_id=row.branch.id,
                branch_name=row.branch.name,
                cancelled_at=row.batch.cancelled_at,
                completed_at=row.batch.completed_at,
                completed_by_user_id=completed_by.id if completed_by else None,
                completed_by_user_name=completed_by.full_name if completed_by else None,
                created_at=row.batch.created_at,
                created_by_user_id=row.created_by_user.id,
                created_by_user_name=row.created_by_user.full_name,
                folio=_build_folio(row.batch.id),
                id=row.batch.id,
                notes=row.batch.notes,
                planned_at=row.batch.planned_at,
                planned_output_qty=row.batch.planned_output_qty,
                started_at=row.batch.started_at,
                started_by_user_id=started_by.id if started_by else None,
                started_by_user_name=started_by.full_name if started_by else None,
                status=_ADMIN_PRODUCTION_STATUS_ADAPTER.validate_python(row.batch.status),
                variance_percent=row.batch.variance_percent,
                variance_qty=row.batch.variance_qty,
                variance_reason=row.batch.variance_reason,
                warning_state=warning_state,
            ),
            planned_inputs=[
                AdminProductionInputLineView(
                    available_qty=input_line.available_qty_snapshot,
                    input_product_code=input_product.code,
                    input_product_id=input_product.id,
                    input_product_name=input_product.name,
                    required_qty=input_line.required_qty,
                    shortage_qty=input_line.shortage_qty_snapshot,
                    standard_cost=input_line.standard_cost_snapshot,
                    status=_ADMIN_PRODUCTION_INPUT_STATUS_ADAPTER.validate_python(
                        input_line.status
                    ),
                    uom=input_line.unit_of_measure,
                )
                for input_line, input_product in self._input_rows_with_products(session, input_rows)
            ],
            product_recipe=AdminProductionProductRecipeView(
                product_code=row.product.code,
                product_id=row.product.id,
                product_is_active=row.product.is_active,
                product_kind=row.product.product_kind,
                product_name=row.product.name,
                product_unit_of_measure=row.product.unit_of_measure,
                recipe_id=row.recipe.id,
                recipe_is_active=row.recipe.is_active,
                recipe_name=_recipe_name(row.recipe),
                recipe_yield_qty=row.recipe.yield_qty,
                recipe_yield_uom=row.recipe.yield_uom,
            ),
            related_documents=self._related_documents(row),
            warnings=warnings,
            waste_scrap=AdminProductionWasteScrapView(),
        )

    def _to_list_item(self, session: Session, row: _ProductionRow) -> AdminProductionListItemView:
        warnings = self._build_warnings(session, row)
        return AdminProductionListItemView(
            actual_output_qty=row.batch.actual_output_qty,
            branch_id=row.branch.id,
            branch_name=row.branch.name,
            completed_at=row.batch.completed_at,
            folio=_build_folio(row.batch.id),
            id=row.batch.id,
            operator_name=row.created_by_user.full_name,
            planned_at=row.batch.planned_at,
            planned_output_qty=row.batch.planned_output_qty,
            product_code=row.product.code,
            product_id=row.product.id,
            product_name=row.product.name,
            recipe_id=row.recipe.id,
            recipe_name=_recipe_name(row.recipe),
            started_at=row.batch.started_at,
            status=_ADMIN_PRODUCTION_STATUS_ADAPTER.validate_python(row.batch.status),
            variance_percent=row.batch.variance_percent,
            variance_qty=row.batch.variance_qty,
            warning_state=self._warning_state_from_warnings(warnings),
            warnings=warnings,
        )

    def _replace_input_plan(
        self,
        session: Session,
        *,
        batch: ProductionBatch,
        branch: Branch,
        recipe: Recipe,
    ) -> None:
        session.execute(
            delete(ProductionBatchInput).where(ProductionBatchInput.production_batch_id == batch.id)
        )
        session.flush()
        for plan in self._build_input_plan(session, batch=batch, branch=branch, recipe=recipe):
            session.add(
                ProductionBatchInput(
                    available_qty_snapshot=plan.available_qty,
                    display_order=plan.display_order,
                    input_product_id=plan.input_product.id,
                    production_batch_id=batch.id,
                    required_qty=plan.required_qty,
                    shortage_qty_snapshot=plan.shortage_qty,
                    standard_cost_snapshot=plan.input_product.standard_cost,
                    status=plan.status,
                    unit_of_measure=plan.input_product.unit_of_measure,
                ),
            )
        session.flush()

    def _build_input_plan(
        self,
        session: Session,
        *,
        batch: ProductionBatch,
        branch: Branch,
        recipe: Recipe,
    ) -> list[_InputPlan]:
        recipe_inputs = session.execute(
            select(RecipeInput, Product)
            .join(Product, Product.id == RecipeInput.input_product_id)
            .where(RecipeInput.recipe_id == recipe.id)
            .order_by(RecipeInput.display_order.asc(), Product.name.asc()),
        ).all()
        if not recipe_inputs:
            raise ProductionValidationError("Production recipe requires at least one input.")

        plans: list[_InputPlan] = []
        for recipe_input, input_product in recipe_inputs:
            required = _q3(
                Decimal(recipe_input.quantity)
                * Decimal(batch.planned_output_qty)
                / Decimal(recipe.yield_qty)
            )
            balance = self._get_balance(
                session,
                product_id=input_product.id,
                branch_id=branch.id,
                location_code=INVENTORY_LOCATION_BACKROOM,
                for_update=False,
            )
            available = _q3(Decimal(balance.quantity_on_hand)) if balance is not None else ZERO
            shortage = _q3(max(required - available, ZERO))
            status = (
                PRODUCTION_INPUT_STATUS_AVAILABLE
                if shortage == ZERO
                else PRODUCTION_INPUT_STATUS_UNAVAILABLE
                if available == ZERO
                else PRODUCTION_INPUT_STATUS_INSUFFICIENT
            )
            plans.append(
                _InputPlan(
                    available_qty=available,
                    display_order=recipe_input.display_order,
                    input_product=input_product,
                    required_qty=required,
                    shortage_qty=shortage,
                    status=status,
                ),
            )
        return plans

    def _build_metrics(
        self, session: Session, rows: list[_ProductionRow]
    ) -> AdminProductionMetricsView:
        return AdminProductionMetricsView(
            completed_batches=sum(
                1 for row in rows if row.batch.status == PRODUCTION_STATUS_COMPLETED
            ),
            in_progress_batches=sum(
                1 for row in rows if row.batch.status == PRODUCTION_STATUS_IN_PROGRESS
            ),
            pending_batches=sum(1 for row in rows if row.batch.status == PRODUCTION_STATUS_DRAFT),
            produced_units=sum(
                (
                    Decimal(row.batch.actual_output_qty or ZERO)
                    for row in rows
                    if row.batch.status == PRODUCTION_STATUS_COMPLETED
                ),
                ZERO,
            ),
            total_batches=len(rows),
            with_shortages=sum(1 for row in rows if self._has_shortage(session, row.batch.id)),
            with_variance=sum(1 for row in rows if row.batch.variance_qty not in (None, ZERO)),
        )

    def _build_filter_options(self, session: Session) -> AdminProductionFilterOptionsView:
        branches = session.execute(select(Branch).order_by(Branch.name.asc())).scalars().all()
        products = (
            session.execute(
                select(Product)
                .where(Product.product_kind == CATALOG_PRODUCT_KIND_FINISHED_GOOD)
                .order_by(Product.name.asc()),
            )
            .scalars()
            .all()
        )
        recipes = session.execute(
            select(Recipe, Product)
            .join(Product, Product.id == Recipe.product_id)
            .order_by(Product.name.asc())
        ).all()
        operators = (
            session.execute(
                select(User)
                .join(ProductionBatch, ProductionBatch.created_by_user_id == User.id)
                .order_by(User.full_name.asc()),
            )
            .scalars()
            .unique()
            .all()
        )
        return AdminProductionFilterOptionsView(
            branches=[
                AdminProductionFilterOptionView(
                    id=str(branch.id), label=f"{branch.name} - {branch.code}"
                )
                for branch in branches
            ],
            operators=[
                AdminProductionFilterOptionView(id=str(user.id), label=user.full_name)
                for user in operators
            ],
            products=[
                AdminProductionFilterOptionView(
                    id=str(product.id), label=f"{product.name} - {product.code}"
                )
                for product in products
            ],
            recipes=[
                AdminProductionFilterOptionView(
                    id=str(recipe.id), label=f"{product.name} - {_recipe_name(recipe)}"
                )
                for recipe, product in recipes
            ],
            statuses=[
                AdminProductionFilterOptionView(id=PRODUCTION_STATUS_DRAFT, label="Pendiente"),
                AdminProductionFilterOptionView(
                    id=PRODUCTION_STATUS_IN_PROGRESS, label="En proceso"
                ),
                AdminProductionFilterOptionView(id=PRODUCTION_STATUS_COMPLETED, label="Completada"),
                AdminProductionFilterOptionView(id=PRODUCTION_STATUS_CANCELLED, label="Cancelada"),
            ],
        )

    def _build_warnings(
        self, session: Session, row: _ProductionRow
    ) -> list[AdminProductionWarningView]:
        warnings: list[AdminProductionWarningView] = []
        if not row.branch.is_active:
            warnings.append(
                AdminProductionWarningView(
                    code="inactive_branch",
                    message="La sucursal esta inactiva.",
                    severity="critical",
                )
            )
        if not row.product.is_active:
            warnings.append(
                AdminProductionWarningView(
                    code="inactive_product",
                    message="El producto terminado esta inactivo.",
                    severity="critical",
                )
            )
        if not row.recipe.is_active:
            warnings.append(
                AdminProductionWarningView(
                    code="inactive_recipe",
                    message="La receta usada no esta activa.",
                    severity="critical",
                )
            )
        if self._has_shortage(session, row.batch.id) and row.batch.status in {
            PRODUCTION_STATUS_DRAFT,
            PRODUCTION_STATUS_IN_PROGRESS,
        }:
            warnings.append(
                AdminProductionWarningView(
                    code="raw_material_shortage",
                    message="Hay faltantes de insumos para esta produccion.",
                    severity="critical",
                )
            )
        if row.batch.status == PRODUCTION_STATUS_COMPLETED and row.batch.variance_qty not in (
            None,
            ZERO,
        ):
            warnings.append(
                AdminProductionWarningView(
                    code="yield_variance",
                    message="La produccion cerro con variacion de rendimiento.",
                    severity="warning",
                )
            )
        if row.batch.status == PRODUCTION_STATUS_COMPLETED and not self._inventory_movements(
            session, row.batch.id
        ):
            warnings.append(
                AdminProductionWarningView(
                    code="missing_inventory_movements",
                    message="No hay movimientos de inventario vinculados.",
                    severity="critical",
                )
            )
        return warnings

    def _warning_state(
        self, session: Session, row: _ProductionRow
    ) -> AdminProductionWarningSeverity | None:
        return self._warning_state_from_warnings(self._build_warnings(session, row))

    def _warning_state_from_warnings(
        self,
        warnings: list[AdminProductionWarningView],
    ) -> AdminProductionWarningSeverity | None:
        if any(warning.severity == "critical" for warning in warnings):
            return "critical"
        if any(warning.severity == "warning" for warning in warnings):
            return "warning"
        if warnings:
            return "info"
        return None

    def _inventory_impact(
        self, session: Session, batch_id: uuid.UUID
    ) -> AdminProductionInventoryImpactView:
        return AdminProductionInventoryImpactView(
            integration_available=True,
            movements=[
                self._to_movement_view(movement)
                for movement in self._inventory_movements(session, batch_id)
            ],
        )

    def _to_movement_view(
        self, movement: InventoryMovement
    ) -> AdminProductionInventoryMovementView:
        return AdminProductionInventoryMovementView(
            balance_after=movement.balance_after,
            branch_id=movement.branch_id,
            direction=movement.direction,
            id=movement.id,
            location_code=movement.location_code,
            movement_type=movement.movement_type,
            product_id=movement.product_id,
            quantity=movement.quantity,
            source_document_id=movement.source_document_id,
            source_document_type=movement.source_document_type,
            unit_of_measure=movement.unit_of_measure,
        )

    def _related_documents(self, row: _ProductionRow) -> list[AdminProductionRelatedDocumentView]:
        documents = [
            AdminProductionRelatedDocumentView(
                document_id=row.recipe.id,
                document_type="RECIPE",
                folio=_recipe_name(row.recipe),
                status="active" if row.recipe.is_active else "inactive",
            ),
            AdminProductionRelatedDocumentView(
                document_id=row.product.id,
                document_type="PRODUCT",
                folio=row.product.code,
                status="active" if row.product.is_active else "inactive",
            ),
        ]
        return documents

    def _list_inputs(self, session: Session, batch_id: uuid.UUID) -> list[ProductionBatchInput]:
        return list(
            session.execute(
                select(ProductionBatchInput)
                .where(ProductionBatchInput.production_batch_id == batch_id)
                .order_by(ProductionBatchInput.display_order.asc()),
            )
            .scalars()
            .all()
        )

    def _input_rows_with_products(
        self,
        session: Session,
        input_rows: list[ProductionBatchInput],
    ) -> list[tuple[ProductionBatchInput, Product]]:
        products = {
            product.id: product
            for product in session.execute(
                select(Product).where(
                    Product.id.in_([input_line.input_product_id for input_line in input_rows])
                ),
            )
            .scalars()
            .all()
        }
        return [(input_line, products[input_line.input_product_id]) for input_line in input_rows]

    def _has_shortage(self, session: Session, batch_id: uuid.UUID) -> bool:
        inputs = self._list_inputs(session, batch_id)
        return any((line.shortage_qty_snapshot or ZERO) > ZERO for line in inputs)

    def _inventory_movements(
        self, session: Session, batch_id: uuid.UUID
    ) -> list[InventoryMovement]:
        return list(
            session.execute(
                select(InventoryMovement)
                .where(
                    InventoryMovement.source_document_type == PRODUCTION_SOURCE_DOCUMENT_TYPE,
                    InventoryMovement.source_document_id == batch_id,
                )
                .order_by(InventoryMovement.occurred_at.asc()),
            )
            .scalars()
            .all()
        )

    def _get_branch(self, session: Session, branch_id: uuid.UUID) -> Branch:
        branch = session.get(Branch, branch_id)
        if branch is None:
            raise ProductionNotFoundError("Branch was not found.")
        return branch

    def _get_product(self, session: Session, product_id: uuid.UUID) -> Product:
        product = session.get(Product, product_id)
        if product is None:
            raise ProductionNotFoundError("Product was not found.")
        return product

    def _get_finished_product(self, session: Session, product_id: uuid.UUID) -> Product:
        product = self._get_product(session, product_id)
        if product.product_kind != CATALOG_PRODUCT_KIND_FINISHED_GOOD:
            raise ProductionValidationError("Production output must be a FINISHED_GOOD product.")
        return product

    def _resolve_recipe(
        self,
        session: Session,
        *,
        product_id: uuid.UUID,
        recipe_id: uuid.UUID | None,
    ) -> Recipe:
        if recipe_id is None:
            recipe = session.execute(
                select(Recipe).where(Recipe.product_id == product_id, Recipe.is_active.is_(True)),
            ).scalar_one_or_none()
            if recipe is None:
                raise ProductionValidationError(
                    "Product requires an active recipe before production."
                )
            return recipe

        recipe = session.get(Recipe, recipe_id)
        if recipe is None:
            raise ProductionNotFoundError("Recipe was not found.")
        if recipe.product_id != product_id:
            raise ProductionValidationError("Recipe does not belong to selected product.")
        if not recipe.is_active:
            raise ProductionValidationError("Production requires an active recipe.")
        return recipe

    def _get_balance(
        self,
        session: Session,
        *,
        branch_id: uuid.UUID,
        for_update: bool,
        location_code: str,
        product_id: uuid.UUID,
    ) -> InventoryBalance | None:
        query = select(InventoryBalance).where(
            InventoryBalance.branch_id == branch_id,
            InventoryBalance.location_code == location_code,
            InventoryBalance.product_id == product_id,
        )
        if for_update:
            query = query.with_for_update()
        return session.execute(query).scalar_one_or_none()

    def _get_or_create_balance(
        self,
        session: Session,
        *,
        branch_id: uuid.UUID,
        location_code: str,
        product_id: uuid.UUID,
    ) -> InventoryBalance:
        balance = self._get_balance(
            session,
            branch_id=branch_id,
            location_code=location_code,
            product_id=product_id,
            for_update=True,
        )
        if balance is not None:
            return balance
        balance = InventoryBalance(
            branch_id=branch_id,
            location_code=location_code,
            product_id=product_id,
            quantity_on_hand=ZERO,
        )
        session.add(balance)
        session.flush()
        return balance

    def _record_change(
        self,
        session: Session,
        *,
        action: str,
        batch: ProductionBatch,
        current_user: AuthenticatedUser,
        event_name: str,
        metadata: dict[str, object],
        request_id: str | None,
    ) -> None:
        payload = {
            "branch_id": str(batch.branch_id),
            "production_id": str(batch.id),
            "status": batch.status,
            **metadata,
        }
        self._audit_recorder.record(
            session,
            actor_id=current_user.id,
            action=action,
            resource_type=PRODUCTION_RESOURCE_TYPE,
            resource_id=str(batch.id),
            branch_id=batch.branch_id,
            request_id=request_id,
            metadata=payload,
        )
        self._outbox_writer.append(
            session,
            aggregate_type="production",
            aggregate_id=str(batch.id),
            event_name=event_name,
            payload=payload,
            headers={"request_id": request_id} if request_id else {},
        )


def _normalize_optional(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    if not normalized:
        return None
    return normalized


def _utc_now() -> datetime:
    return datetime.now(tz=UTC)


def _q3(value: Decimal) -> Decimal:
    return Decimal(value).quantize(DECIMAL_3, rounding=ROUND_HALF_UP)


def _q4(value: Decimal) -> Decimal:
    return Decimal(value).quantize(DECIMAL_4, rounding=ROUND_HALF_UP)


def _variance_percent(variance_qty: Decimal, planned_qty: Decimal) -> Decimal | None:
    if planned_qty == ZERO:
        return None
    return _q4((variance_qty / planned_qty) * Decimal("100"))


def _build_folio(batch_id: uuid.UUID) -> str:
    return f"PROD-{str(batch_id)[:8].upper()}"


def _recipe_name(recipe: Recipe) -> str:
    return recipe.version_name or f"Receta {str(recipe.id)[:8]}"
