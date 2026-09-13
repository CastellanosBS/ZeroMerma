from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from zeromerma_api.modules.audit.application.service import AuditRecorder
from zeromerma_api.modules.branches.infrastructure.models import Branch
from zeromerma_api.modules.catalog.application.inputs_supplies_schemas import (
    AdminInputSupplyAvailableActionsView,
    AdminInputSupplyClassificationView,
    AdminInputSupplyCostView,
    AdminInputSupplyCreateRequest,
    AdminInputSupplyDetailView,
    AdminInputSupplyFilterOptionsView,
    AdminInputSupplyFilterOptionView,
    AdminInputSupplyInventoryBranchView,
    AdminInputSupplyInventoryStatusView,
    AdminInputSupplyListItemView,
    AdminInputSupplyListResponse,
    AdminInputSupplyMetricsView,
    AdminInputSupplyOverviewView,
    AdminInputSupplyRecipeUsageView,
    AdminInputSupplyRelatedDocumentView,
    AdminInputSupplyStatusRequest,
    AdminInputSupplyStockState,
    AdminInputSupplySupplierRelationRequest,
    AdminInputSupplySupplierRelationView,
    AdminInputSupplyUnitsConversionView,
    AdminInputSupplyUpdateRequest,
    AdminInputSupplyWarningState,
    AdminInputSupplyWarningView,
)
from zeromerma_api.modules.catalog.domain.constants import (
    CATALOG_INPUT_PRODUCT_KINDS,
    CATALOG_PRODUCT_KIND_CONSUMABLE,
    CATALOG_PRODUCT_KIND_DISPOSABLE,
    CATALOG_PRODUCT_KIND_RAW_MATERIAL,
    CATALOG_USAGE_TYPE_CLEANING_SANITATION,
    CATALOG_USAGE_TYPE_OPERATIONAL_SUPPLY,
    CATALOG_USAGE_TYPE_OTHER,
    CATALOG_USAGE_TYPE_PACKAGING,
    CATALOG_USAGE_TYPE_PRODUCTION_SUPPLY,
    CATALOG_USAGE_TYPE_RECIPE_INPUT,
)
from zeromerma_api.modules.catalog.domain.exceptions import (
    CatalogError,
    ProductClassNotFoundError,
    ProductNotFoundError,
)
from zeromerma_api.modules.catalog.infrastructure.models import (
    Product,
    ProductClass,
    Recipe,
    RecipeInput,
)
from zeromerma_api.modules.identity.application.actions import restrict_actions
from zeromerma_api.modules.identity.application.schemas import AuthenticatedUser
from zeromerma_api.modules.inventory.infrastructure.models import (
    InventoryBalance,
    InventoryMovement,
)
from zeromerma_api.modules.outbox.application.service import OutboxWriter
from zeromerma_api.modules.suppliers.infrastructure.models import Supplier, SupplierProduct

AUDIT_ACTION_ADMIN_INPUT_SUPPLY_CREATED = "admin.input_supply.created"
AUDIT_ACTION_ADMIN_INPUT_SUPPLY_SUPPLIER_UPDATED = "admin.input_supply.supplier_relation.updated"
AUDIT_ACTION_ADMIN_INPUT_SUPPLY_UPDATED = "admin.input_supply.updated"
OUTBOX_EVENT_ADMIN_INPUT_SUPPLY_CREATED_V1 = "admin.input_supply.created.v1"
OUTBOX_EVENT_ADMIN_INPUT_SUPPLY_UPDATED_V1 = "admin.input_supply.updated.v1"
INPUT_SUPPLY_RESOURCE_TYPE = "input_supply"
ZERO = Decimal("0")

PRODUCT_KIND_LABELS = {
    CATALOG_PRODUCT_KIND_RAW_MATERIAL: "Materia prima",
    CATALOG_PRODUCT_KIND_CONSUMABLE: "Consumible",
    CATALOG_PRODUCT_KIND_DISPOSABLE: "Desechable",
}

USAGE_TYPE_LABELS = {
    CATALOG_USAGE_TYPE_RECIPE_INPUT: "Insumo de receta",
    CATALOG_USAGE_TYPE_PRODUCTION_SUPPLY: "Suministro de produccion",
    CATALOG_USAGE_TYPE_PACKAGING: "Empaque",
    CATALOG_USAGE_TYPE_CLEANING_SANITATION: "Limpieza / sanidad",
    CATALOG_USAGE_TYPE_OPERATIONAL_SUPPLY: "Suministro operativo",
    CATALOG_USAGE_TYPE_OTHER: "Otro",
}

VALID_USAGE_TYPES = set(USAGE_TYPE_LABELS)


class AdminInputSupplyValidationError(CatalogError):
    """Raised when an input/consumable operation violates catalog rules."""


@dataclass(frozen=True)
class _InventoryBranchStock:
    branch: Branch
    last_movement_at: datetime | None
    quantity_on_hand: Decimal


@dataclass(frozen=True)
class _InputSupplyContext:
    inventory: list[_InventoryBranchStock]
    last_movement_at: datetime | None
    last_purchase_cost: Decimal | None
    product: Product
    product_class: ProductClass
    recipe_usage: list[tuple[RecipeInput, Recipe, Product]]
    suppliers: list[tuple[SupplierProduct, Supplier]]


class AdminInputSupplyService:
    def __init__(
        self,
        audit_recorder: AuditRecorder | None = None,
        outbox_writer: OutboxWriter | None = None,
    ) -> None:
        self._audit_recorder = audit_recorder or AuditRecorder()
        self._outbox_writer = outbox_writer or OutboxWriter()

    def list_items(
        self,
        session: Session,
        *,
        class_id: uuid.UUID | None,
        cost_state: str | None,
        inventory_tracked: bool | None,
        page: int,
        page_size: int,
        product_kind: str | None,
        purchasable: bool | None,
        recipe_usage: str | None,
        search: str | None,
        status_filter: str | None,
        stock_state: str | None,
        supplier_id: uuid.UUID | None,
        usage_type: str | None,
        warning_state: str | None,
        without_supplier: bool | None,
    ) -> AdminInputSupplyListResponse:
        contexts = self._fetch_contexts(session)
        contexts = self._apply_filters(
            contexts,
            class_id=class_id,
            cost_state=cost_state,
            inventory_tracked=inventory_tracked,
            product_kind=product_kind,
            purchasable=purchasable,
            recipe_usage=recipe_usage,
            search=search,
            status_filter=status_filter,
            stock_state=stock_state,
            supplier_id=supplier_id,
            usage_type=usage_type,
            warning_state=warning_state,
            without_supplier=without_supplier,
        )

        items = [self._to_list_item(context) for context in contexts]
        total = len(items)
        safe_page = max(page, 1)
        safe_page_size = min(max(page_size, 1), 100)
        offset = (safe_page - 1) * safe_page_size
        return AdminInputSupplyListResponse(
            filter_options=self._build_filter_options(session),
            items=items[offset : offset + safe_page_size],
            metrics=self._build_metrics(contexts),
            page=safe_page,
            page_size=safe_page_size,
            total=total,
        )

    def get_item_detail(
        self,
        session: Session,
        *,
        product_id: uuid.UUID,
    ) -> AdminInputSupplyDetailView:
        return self._to_detail(session, self._get_context(session, product_id))

    def create_item(
        self,
        session: Session,
        *,
        command: AdminInputSupplyCreateRequest,
        current_user: AuthenticatedUser,
        request_id: str | None,
    ) -> AdminInputSupplyDetailView:
        self._validate_command(session, command)
        product_class = self._get_product_class(session, command.product_class_id)
        self._ensure_unique_code(session, command.code)

        product = Product(
            code=command.code.strip().upper(),
            currency_code="MXN",
            is_active=command.is_active,
            is_inventory_tracked=command.is_inventory_tracked,
            is_purchasable=command.is_purchasable,
            is_sellable=False,
            minimum_stock=command.minimum_stock,
            name=command.name.strip(),
            preferred_order_quantity=command.preferred_order_quantity,
            procurement_notes=command.procurement_notes,
            product_class_id=product_class.id,
            product_kind=command.product_kind,
            purchase_conversion_factor=command.purchase_conversion_factor,
            purchase_unit_of_measure=command.purchase_uom,
            reorder_point=command.reorder_point,
            standard_cost=command.standard_cost,
            unit_of_measure=command.unit_of_measure.strip().upper(),
            unit_price=ZERO,
            usage_type=command.usage_type or CATALOG_USAGE_TYPE_OTHER,
        )

        try:
            session.add(product)
            session.flush()
            self._replace_supplier_relations(
                session, product=product, relations=command.supplier_relations
            )
            self._record_change(
                session,
                action=AUDIT_ACTION_ADMIN_INPUT_SUPPLY_CREATED,
                event_name=OUTBOX_EVENT_ADMIN_INPUT_SUPPLY_CREATED_V1,
                current_user=current_user,
                metadata=self._metadata(product),
                product=product,
                request_id=request_id,
            )
            session.commit()
        except IntegrityError as error:
            session.rollback()
            raise AdminInputSupplyValidationError("Input code must be unique.") from error

        return self.get_item_detail(session, product_id=product.id)

    def update_item(
        self,
        session: Session,
        *,
        command: AdminInputSupplyUpdateRequest,
        current_user: AuthenticatedUser,
        product_id: uuid.UUID,
        request_id: str | None,
    ) -> AdminInputSupplyDetailView:
        self._validate_command(session, command)
        product = self._get_product(session, product_id)
        product_class = self._get_product_class(session, command.product_class_id)
        if product.code != command.code.strip().upper():
            self._ensure_unique_code(session, command.code, product_id=product.id)

        product.code = command.code.strip().upper()
        product.is_active = command.is_active
        product.is_inventory_tracked = command.is_inventory_tracked
        product.is_purchasable = command.is_purchasable
        product.is_sellable = False
        product.minimum_stock = command.minimum_stock
        product.name = command.name.strip()
        product.preferred_order_quantity = command.preferred_order_quantity
        product.procurement_notes = command.procurement_notes
        product.product_class_id = product_class.id
        product.product_kind = command.product_kind
        product.purchase_conversion_factor = command.purchase_conversion_factor
        product.purchase_unit_of_measure = command.purchase_uom
        product.reorder_point = command.reorder_point
        product.standard_cost = command.standard_cost
        product.unit_of_measure = command.unit_of_measure.strip().upper()
        product.usage_type = command.usage_type or CATALOG_USAGE_TYPE_OTHER

        try:
            self._replace_supplier_relations(
                session, product=product, relations=command.supplier_relations
            )
            self._record_change(
                session,
                action=AUDIT_ACTION_ADMIN_INPUT_SUPPLY_UPDATED,
                event_name=OUTBOX_EVENT_ADMIN_INPUT_SUPPLY_UPDATED_V1,
                current_user=current_user,
                metadata=self._metadata(product),
                product=product,
                request_id=request_id,
            )
            session.commit()
        except IntegrityError as error:
            session.rollback()
            raise AdminInputSupplyValidationError(
                "Input update violates catalog integrity."
            ) from error

        return self.get_item_detail(session, product_id=product.id)

    def change_status(
        self,
        session: Session,
        *,
        command: AdminInputSupplyStatusRequest,
        current_user: AuthenticatedUser,
        product_id: uuid.UUID,
        request_id: str | None,
    ) -> AdminInputSupplyDetailView:
        product = self._get_product(session, product_id)
        product.is_active = command.is_active
        if command.notes:
            product.procurement_notes = command.notes
        self._record_change(
            session,
            action=AUDIT_ACTION_ADMIN_INPUT_SUPPLY_UPDATED,
            event_name=OUTBOX_EVENT_ADMIN_INPUT_SUPPLY_UPDATED_V1,
            current_user=current_user,
            metadata={**self._metadata(product), "status_notes": command.notes},
            product=product,
            request_id=request_id,
        )
        session.commit()
        return self.get_item_detail(session, product_id=product.id)

    def upsert_supplier_relation(
        self,
        session: Session,
        *,
        command: AdminInputSupplySupplierRelationRequest,
        current_user: AuthenticatedUser,
        product_id: uuid.UUID,
        request_id: str | None,
    ) -> AdminInputSupplyDetailView:
        product = self._get_product(session, product_id)
        supplier = self._get_supplier(session, command.supplier_id)
        relation = session.execute(
            select(SupplierProduct).where(
                SupplierProduct.product_id == product.id,
                SupplierProduct.supplier_id == supplier.id,
            )
        ).scalar_one_or_none()
        if relation is None:
            relation = SupplierProduct(product_id=product.id, supplier_id=supplier.id)
            session.add(relation)
        self._apply_supplier_relation(relation, command)
        self._record_audit_only(
            session,
            action=AUDIT_ACTION_ADMIN_INPUT_SUPPLY_SUPPLIER_UPDATED,
            current_user=current_user,
            metadata={**self._metadata(product), "supplier_id": str(supplier.id)},
            product=product,
            request_id=request_id,
        )
        session.commit()
        return self.get_item_detail(session, product_id=product.id)

    def update_supplier_relation(
        self,
        session: Session,
        *,
        command: AdminInputSupplySupplierRelationRequest,
        current_user: AuthenticatedUser,
        product_id: uuid.UUID,
        relation_id: uuid.UUID,
        request_id: str | None,
    ) -> AdminInputSupplyDetailView:
        product = self._get_product(session, product_id)
        supplier = self._get_supplier(session, command.supplier_id)
        relation = session.get(SupplierProduct, relation_id)
        if relation is None or relation.product_id != product.id:
            raise ProductNotFoundError("Supplier relation was not found.")
        relation.supplier_id = supplier.id
        self._apply_supplier_relation(relation, command)
        self._record_audit_only(
            session,
            action=AUDIT_ACTION_ADMIN_INPUT_SUPPLY_SUPPLIER_UPDATED,
            current_user=current_user,
            metadata={**self._metadata(product), "relation_id": str(relation.id)},
            product=product,
            request_id=request_id,
        )
        session.commit()
        return self.get_item_detail(session, product_id=product.id)

    def _apply_filters(
        self,
        contexts: list[_InputSupplyContext],
        *,
        class_id: uuid.UUID | None,
        cost_state: str | None,
        inventory_tracked: bool | None,
        product_kind: str | None,
        purchasable: bool | None,
        recipe_usage: str | None,
        search: str | None,
        status_filter: str | None,
        stock_state: str | None,
        supplier_id: uuid.UUID | None,
        usage_type: str | None,
        warning_state: str | None,
        without_supplier: bool | None,
    ) -> list[_InputSupplyContext]:
        normalized_kind = _normalize_optional(product_kind)
        if normalized_kind and normalized_kind != "all":
            if normalized_kind not in CATALOG_INPUT_PRODUCT_KINDS:
                raise AdminInputSupplyValidationError("Product kind is not supported for inputs.")
            contexts = [
                context for context in contexts if context.product.product_kind == normalized_kind
            ]
        if class_id is not None:
            contexts = [
                context for context in contexts if context.product.product_class_id == class_id
            ]
        if inventory_tracked is not None:
            contexts = [
                context
                for context in contexts
                if bool(context.product.is_inventory_tracked) is inventory_tracked
            ]
        if purchasable is not None:
            contexts = [
                context
                for context in contexts
                if bool(context.product.is_purchasable) is purchasable
            ]
        if supplier_id is not None:
            contexts = [
                context
                for context in contexts
                if any(
                    relation.supplier_id == supplier_id and relation.is_active
                    for relation, _ in context.suppliers
                )
            ]
        if without_supplier is True:
            contexts = [
                context
                for context in contexts
                if not any(relation.is_active for relation, _ in context.suppliers)
            ]
        elif without_supplier is False:
            contexts = [
                context
                for context in contexts
                if any(relation.is_active for relation, _ in context.suppliers)
            ]
        normalized_status = _normalize_optional(status_filter)
        if normalized_status == "active":
            contexts = [context for context in contexts if context.product.is_active]
        elif normalized_status == "inactive":
            contexts = [context for context in contexts if not context.product.is_active]
        elif normalized_status not in (None, "all"):
            raise AdminInputSupplyValidationError("Status filter is not supported.")
        normalized_usage_type = _normalize_optional(usage_type)
        if normalized_usage_type and normalized_usage_type != "all":
            contexts = [
                context
                for context in contexts
                if context.product.usage_type == normalized_usage_type
            ]
        normalized_cost_state = _normalize_optional(cost_state)
        if normalized_cost_state == "with_cost":
            contexts = [
                context
                for context in contexts
                if context.product.standard_cost is not None
                or context.last_purchase_cost is not None
            ]
        elif normalized_cost_state == "missing_cost":
            contexts = [
                context
                for context in contexts
                if context.product.standard_cost is None and context.last_purchase_cost is None
            ]
        normalized_recipe_usage = _normalize_optional(recipe_usage)
        if normalized_recipe_usage == "used":
            contexts = [context for context in contexts if context.recipe_usage]
        elif normalized_recipe_usage == "unused":
            contexts = [context for context in contexts if not context.recipe_usage]
        normalized_stock_state = _normalize_optional(stock_state)
        if normalized_stock_state and normalized_stock_state != "all":
            contexts = [
                context
                for context in contexts
                if self._stock_state(context) == normalized_stock_state
            ]
        normalized_warning_state = _normalize_optional(warning_state)
        if normalized_warning_state == "with_warnings":
            contexts = [context for context in contexts if self._build_warnings(context)]
        elif normalized_warning_state == "without_warnings":
            contexts = [context for context in contexts if not self._build_warnings(context)]
        elif normalized_warning_state in {"info", "warning", "critical"}:
            contexts = [
                context
                for context in contexts
                if self._warning_state(self._build_warnings(context)) == normalized_warning_state
            ]

        normalized_search = _normalize_optional(search)
        if normalized_search:
            contexts = [
                context for context in contexts if self._matches_search(context, normalized_search)
            ]
        return contexts

    def _fetch_contexts(self, session: Session) -> list[_InputSupplyContext]:
        rows = session.execute(
            select(Product, ProductClass)
            .join(ProductClass, ProductClass.id == Product.product_class_id)
            .where(Product.product_kind.in_(CATALOG_INPUT_PRODUCT_KINDS))
            .order_by(ProductClass.name.asc(), Product.name.asc(), Product.code.asc())
        ).all()
        return [
            self._build_context(session, product=product, product_class=product_class)
            for product, product_class in rows
        ]

    def _get_context(self, session: Session, product_id: uuid.UUID) -> _InputSupplyContext:
        row = session.execute(
            select(Product, ProductClass)
            .join(ProductClass, ProductClass.id == Product.product_class_id)
            .where(Product.id == product_id, Product.product_kind.in_(CATALOG_INPUT_PRODUCT_KINDS))
        ).one_or_none()
        if row is None:
            raise ProductNotFoundError("Input or consumable item was not found.")
        product, product_class = row
        return self._build_context(session, product=product, product_class=product_class)

    def _build_context(
        self,
        session: Session,
        *,
        product: Product,
        product_class: ProductClass,
    ) -> _InputSupplyContext:
        suppliers = list(
            session.execute(
                select(SupplierProduct, Supplier)
                .join(Supplier, Supplier.id == SupplierProduct.supplier_id)
                .where(SupplierProduct.product_id == product.id)
                .order_by(SupplierProduct.is_active.desc(), Supplier.legal_name.asc())
            )
            .tuples()
            .all()
        )
        inventory_rows = (
            session.execute(
                select(InventoryBalance, Branch)
                .join(Branch, Branch.id == InventoryBalance.branch_id)
                .where(InventoryBalance.product_id == product.id)
                .order_by(Branch.name.asc(), InventoryBalance.location_code.asc())
            )
            .tuples()
            .all()
        )
        by_branch: dict[uuid.UUID, _InventoryBranchStock] = {}
        for balance, branch in inventory_rows:
            previous = by_branch.get(branch.id)
            quantity = Decimal(balance.quantity_on_hand)
            if previous is not None:
                quantity += previous.quantity_on_hand
            by_branch[branch.id] = _InventoryBranchStock(
                branch=branch,
                last_movement_at=self._last_movement_at(session, product.id, branch.id),
                quantity_on_hand=quantity,
            )
        last_movement_at = self._last_movement_at(session, product.id, None)
        last_purchase_cost = self._last_purchase_cost(suppliers)
        recipe_usage = list(
            session.execute(
                select(RecipeInput, Recipe, Product)
                .join(Recipe, Recipe.id == RecipeInput.recipe_id)
                .join(Product, Product.id == Recipe.product_id)
                .where(RecipeInput.input_product_id == product.id)
                .order_by(Recipe.is_active.desc(), Product.name.asc())
            )
            .tuples()
            .all()
        )
        return _InputSupplyContext(
            inventory=list(by_branch.values()),
            last_movement_at=last_movement_at,
            last_purchase_cost=last_purchase_cost,
            product=product,
            product_class=product_class,
            recipe_usage=recipe_usage,
            suppliers=suppliers,
        )

    def _to_list_item(self, context: _InputSupplyContext) -> AdminInputSupplyListItemView:
        warnings = self._build_warnings(context)
        primary_supplier = next(
            (supplier for relation, supplier in context.suppliers if relation.is_active),
            None,
        )
        return AdminInputSupplyListItemView(
            base_uom=context.product.unit_of_measure,
            category_id=context.product_class.id,
            category_name=context.product_class.name,
            code=context.product.code,
            id=context.product.id,
            is_active=context.product.is_active,
            is_inventory_tracked=context.product.is_inventory_tracked,
            is_purchasable=context.product.is_purchasable,
            last_movement_at=context.last_movement_at,
            last_purchase_cost=context.last_purchase_cost,
            name=context.product.name,
            primary_supplier_name=primary_supplier.legal_name if primary_supplier else None,
            product_kind=context.product.product_kind,  # type: ignore[arg-type]
            purchase_uom=context.product.purchase_unit_of_measure,
            recipe_usage_count=len(context.recipe_usage),
            standard_cost=context.product.standard_cost,
            stock_state=self._stock_state(context),
            supplier_count=sum(1 for relation, _ in context.suppliers if relation.is_active),
            updated_at=context.product.updated_at,
            warning_state=self._warning_state(warnings),
            warnings=warnings,
        )

    def _to_detail(
        self, session: Session, context: _InputSupplyContext
    ) -> AdminInputSupplyDetailView:
        warnings = self._build_warnings(context)
        stock_state = self._stock_state(context)
        total_stock = self._total_stock(context)
        supplier_prices = [
            relation.last_known_price
            for relation, _ in context.suppliers
            if relation.last_known_price is not None and relation.is_active
        ]
        minimum_order_qty = next(
            (
                relation.minimum_order_qty
                for relation, _ in context.suppliers
                if relation.minimum_order_qty is not None and relation.is_active
            ),
            None,
        )
        return AdminInputSupplyDetailView(
            available_actions=restrict_actions(
                session,
                restrict_actions(
                    session,
                    AdminInputSupplyAvailableActionsView(),
                    {
                        "can_add_supplier": "catalog.manage",
                        "can_deactivate": "catalog.manage",
                        "can_edit": "catalog.manage",
                    },
                    branch_ids=(),
                    global_only=True,
                ),
                {
                    "can_open_inventory": "inventory.view",
                    "can_open_product": "catalog.view",
                    "can_open_recipes": "recipes.view",
                },
            ),
            classification=AdminInputSupplyClassificationView(
                kind=context.product.product_kind,  # type: ignore[arg-type]
                notes=context.product.procurement_notes,
                status="active" if context.product.is_active else "inactive",
                storage_group=context.product_class.name,
                usage_type=context.product.usage_type,
            ),
            cost=AdminInputSupplyCostView(
                cost_updated_at=context.product.updated_at,
                currency=context.product.currency_code,
                last_purchase_cost=context.last_purchase_cost,
                standard_cost=context.product.standard_cost,
                supplier_price_max=max(supplier_prices) if supplier_prices else None,
                supplier_price_min=min(supplier_prices) if supplier_prices else None,
                warnings=[
                    warning
                    for warning in warnings
                    if warning.code in {"missing_cost", "cost_without_supplier_price"}
                ],
            ),
            inventory_status=AdminInputSupplyInventoryStatusView(
                integration_available=bool(context.inventory),
                last_movement_at=context.last_movement_at,
                minimum_stock=context.product.minimum_stock,
                preferred_order_quantity=context.product.preferred_order_quantity,
                reorder_point=context.product.reorder_point,
                stock_by_branch=[
                    AdminInputSupplyInventoryBranchView(
                        branch_id=row.branch.id,
                        branch_name=row.branch.name,
                        last_movement_at=row.last_movement_at,
                        quantity_on_hand=row.quantity_on_hand,
                        stock_state=self._branch_stock_state(context, row.quantity_on_hand),
                    )
                    for row in context.inventory
                ],
                stock_state=stock_state,
                total_stock=total_stock,
                unit_of_measure=context.product.unit_of_measure,
            ),
            overview=AdminInputSupplyOverviewView(
                base_uom=context.product.unit_of_measure,
                category_id=context.product_class.id,
                category_name=context.product_class.name,
                code=context.product.code,
                created_at=context.product.created_at,
                id=context.product.id,
                is_active=context.product.is_active,
                is_inventory_tracked=context.product.is_inventory_tracked,
                is_purchasable=context.product.is_purchasable,
                last_purchase_cost=context.last_purchase_cost,
                name=context.product.name,
                product_kind=context.product.product_kind,  # type: ignore[arg-type]
                purchase_uom=context.product.purchase_unit_of_measure,
                readiness_state=self._warning_state(warnings),
                standard_cost=context.product.standard_cost,
                updated_at=context.product.updated_at,
                warning_state=self._warning_state(warnings),
            ),
            procurement_warnings=warnings,
            recipe_usage=[
                AdminInputSupplyRecipeUsageView(
                    finished_product_code=finished_product.code,
                    finished_product_id=finished_product.id,
                    finished_product_name=finished_product.name,
                    quantity=recipe_input.quantity,
                    recipe_id=recipe.id,
                    recipe_version_name=recipe.version_name,
                    unit_of_measure=context.product.unit_of_measure,
                )
                for recipe_input, recipe, finished_product in context.recipe_usage
            ],
            related_documents=self._related_documents(context),
            suppliers=[
                AdminInputSupplySupplierRelationView(
                    conversion_factor=relation.conversion_factor,
                    currency=relation.currency,
                    id=relation.id,
                    is_active=relation.is_active,
                    last_known_price=relation.last_known_price,
                    lead_time_days=relation.lead_time_days,
                    minimum_order_qty=relation.minimum_order_qty,
                    notes=relation.notes,
                    purchase_uom=relation.purchase_uom,
                    supplier_id=supplier.id,
                    supplier_name=supplier.legal_name,
                    supplier_sku=relation.supplier_sku,
                )
                for relation, supplier in context.suppliers
            ],
            units_conversion=AdminInputSupplyUnitsConversionView(
                base_uom=context.product.unit_of_measure,
                consumption_uom=context.product.unit_of_measure,
                conversion_factor=context.product.purchase_conversion_factor,
                minimum_purchase_quantity=minimum_order_qty,
                purchase_uom=context.product.purchase_unit_of_measure,
                unit_conversion_supported=context.product.purchase_conversion_factor is not None,
            ),
        )

    def _build_filter_options(self, session: Session) -> AdminInputSupplyFilterOptionsView:
        classes = session.execute(
            select(ProductClass)
            .where(ProductClass.is_active.is_(True))
            .order_by(ProductClass.name.asc())
        ).scalars()
        suppliers = session.execute(select(Supplier).order_by(Supplier.legal_name.asc())).scalars()
        return AdminInputSupplyFilterOptionsView(
            classes=[
                AdminInputSupplyFilterOptionView(id=str(product_class.id), label=product_class.name)
                for product_class in classes
            ],
            cost_states=[
                AdminInputSupplyFilterOptionView(id="with_cost", label="Con costo"),
                AdminInputSupplyFilterOptionView(id="missing_cost", label="Sin costo"),
            ],
            product_kinds=[
                AdminInputSupplyFilterOptionView(id=kind, label=label)
                for kind, label in PRODUCT_KIND_LABELS.items()
            ],
            recipe_usage_states=[
                AdminInputSupplyFilterOptionView(id="used", label="Usado en recetas"),
                AdminInputSupplyFilterOptionView(id="unused", label="Sin uso en recetas"),
            ],
            statuses=[
                AdminInputSupplyFilterOptionView(id="active", label="Activo"),
                AdminInputSupplyFilterOptionView(id="inactive", label="Inactivo"),
            ],
            stock_states=[
                AdminInputSupplyFilterOptionView(id="in_stock", label="Con existencia"),
                AdminInputSupplyFilterOptionView(id="low_stock", label="Stock bajo"),
                AdminInputSupplyFilterOptionView(id="negative_stock", label="Stock negativo"),
                AdminInputSupplyFilterOptionView(id="out_of_stock", label="Sin existencia"),
                AdminInputSupplyFilterOptionView(id="no_inventory", label="Sin inventario"),
            ],
            suppliers=[
                AdminInputSupplyFilterOptionView(id=str(supplier.id), label=supplier.legal_name)
                for supplier in suppliers
            ],
            usage_types=[
                AdminInputSupplyFilterOptionView(id=code, label=label)
                for code, label in USAGE_TYPE_LABELS.items()
            ],
            warning_states=[
                AdminInputSupplyFilterOptionView(id="with_warnings", label="Con advertencias"),
                AdminInputSupplyFilterOptionView(id="without_warnings", label="Sin advertencias"),
                AdminInputSupplyFilterOptionView(id="critical", label="Criticas"),
                AdminInputSupplyFilterOptionView(id="warning", label="Advertencia"),
            ],
        )

    def _build_metrics(self, contexts: list[_InputSupplyContext]) -> AdminInputSupplyMetricsView:
        return AdminInputSupplyMetricsView(
            active_consumables=sum(
                1
                for context in contexts
                if context.product.is_active
                and context.product.product_kind == CATALOG_PRODUCT_KIND_CONSUMABLE
            ),
            active_disposables=sum(
                1
                for context in contexts
                if context.product.is_active
                and context.product.product_kind == CATALOG_PRODUCT_KIND_DISPOSABLE
            ),
            active_raw_materials=sum(
                1
                for context in contexts
                if context.product.is_active
                and context.product.product_kind == CATALOG_PRODUCT_KIND_RAW_MATERIAL
            ),
            low_stock=sum(1 for context in contexts if self._stock_state(context) == "low_stock"),
            missing_cost=sum(
                1
                for context in contexts
                if context.product.standard_cost is None and context.last_purchase_cost is None
            ),
            used_in_recipes=sum(1 for context in contexts if context.recipe_usage),
            without_supplier=sum(
                1
                for context in contexts
                if not any(relation.is_active for relation, _ in context.suppliers)
            ),
        )

    def _build_warnings(self, context: _InputSupplyContext) -> list[AdminInputSupplyWarningView]:
        warnings: list[AdminInputSupplyWarningView] = []
        product = context.product
        if not any(relation.is_active for relation, _ in context.suppliers):
            warnings.append(
                AdminInputSupplyWarningView(
                    code="missing_supplier",
                    message="No tiene proveedor activo asociado.",
                    severity="warning",
                )
            )
        if product.standard_cost is None and context.last_purchase_cost is None:
            warnings.append(
                AdminInputSupplyWarningView(
                    code="missing_cost",
                    message="No tiene costo estandar ni ultimo costo de compra.",
                    severity="warning",
                )
            )
        if product.is_purchasable and not product.purchase_unit_of_measure:
            warnings.append(
                AdminInputSupplyWarningView(
                    code="missing_purchase_uom",
                    message="Falta unidad de compra para compras.",
                    severity="info",
                )
            )
        if (
            product.purchase_unit_of_measure
            and product.purchase_unit_of_measure != product.unit_of_measure
            and product.purchase_conversion_factor is None
        ):
            warnings.append(
                AdminInputSupplyWarningView(
                    code="missing_conversion_factor",
                    message="La unidad de compra difiere de la base sin factor de conversion.",
                    severity="critical",
                )
            )
        if not product.is_active and (self._total_stock(context) or ZERO) > ZERO:
            warnings.append(
                AdminInputSupplyWarningView(
                    code="inactive_with_stock",
                    message="El insumo esta inactivo pero conserva existencia.",
                    severity="warning",
                )
            )
        if product.is_active and not product.is_purchasable:
            warnings.append(
                AdminInputSupplyWarningView(
                    code="active_not_purchasable",
                    message="El insumo esta activo pero no marcado como comprable.",
                    severity="warning",
                )
            )
        if product.product_kind == CATALOG_PRODUCT_KIND_RAW_MATERIAL and not context.recipe_usage:
            warnings.append(
                AdminInputSupplyWarningView(
                    code="raw_material_without_recipe_usage",
                    message="Materia prima sin uso registrado en recetas.",
                    severity="info",
                )
            )
        if self._stock_state(context) == "low_stock":
            warnings.append(
                AdminInputSupplyWarningView(
                    code="low_stock",
                    message="Existencia por debajo del punto de reorden o minimo configurado.",
                    severity="warning",
                )
            )
        if any(not relation.is_active for relation, _ in context.suppliers):
            warnings.append(
                AdminInputSupplyWarningView(
                    code="inactive_supplier_relation",
                    message="Tiene relacion con proveedor inactiva.",
                    severity="info",
                )
            )
        if not product.is_inventory_tracked:
            warnings.append(
                AdminInputSupplyWarningView(
                    code="not_inventory_tracked",
                    message="No esta marcado como inventariable.",
                    severity="info",
                )
            )
        return warnings

    def _related_documents(
        self, context: _InputSupplyContext
    ) -> list[AdminInputSupplyRelatedDocumentView]:
        documents: list[AdminInputSupplyRelatedDocumentView] = []
        documents.extend(
            AdminInputSupplyRelatedDocumentView(
                document_id=relation.id,
                document_type="SUPPLIER_PRODUCT",
                folio=supplier.code,
                status="active" if relation.is_active else "inactive",
            )
            for relation, supplier in context.suppliers
        )
        documents.extend(
            AdminInputSupplyRelatedDocumentView(
                document_id=recipe.id,
                document_type="RECIPE_USAGE",
                folio=finished_product.code,
                status="active" if recipe.is_active else "inactive",
            )
            for _, recipe, finished_product in context.recipe_usage
        )
        return documents

    def _replace_supplier_relations(
        self,
        session: Session,
        *,
        product: Product,
        relations: list[AdminInputSupplySupplierRelationRequest],
    ) -> None:
        supplier_ids = [relation.supplier_id for relation in relations]
        if len(supplier_ids) != len(set(supplier_ids)):
            raise AdminInputSupplyValidationError("Supplier relations must be unique.")
        existing = (
            session.execute(select(SupplierProduct).where(SupplierProduct.product_id == product.id))
            .scalars()
            .all()
        )
        requested = set(supplier_ids)
        for existing_relation in existing:
            if existing_relation.supplier_id not in requested:
                existing_relation.is_active = False
        for relation_command in relations:
            supplier = self._get_supplier(session, relation_command.supplier_id)
            relation = next(
                (item for item in existing if item.supplier_id == supplier.id),
                None,
            )
            if relation is None:
                relation = SupplierProduct(product_id=product.id, supplier_id=supplier.id)
                session.add(relation)
            self._apply_supplier_relation(relation, relation_command)

    def _apply_supplier_relation(
        self,
        relation: SupplierProduct,
        command: AdminInputSupplySupplierRelationRequest,
    ) -> None:
        relation.conversion_factor = command.conversion_factor
        relation.currency = command.currency
        relation.is_active = command.is_active
        relation.last_known_price = command.last_known_price
        relation.lead_time_days = command.lead_time_days
        relation.minimum_order_qty = command.minimum_order_qty
        relation.notes = command.notes
        relation.purchase_uom = command.purchase_uom
        relation.supplier_sku = command.supplier_sku

    def _validate_command(
        self,
        session: Session,
        command: AdminInputSupplyCreateRequest | AdminInputSupplyUpdateRequest,
    ) -> None:
        _ = session
        if command.product_kind not in CATALOG_INPUT_PRODUCT_KINDS:
            raise AdminInputSupplyValidationError(
                "Only input and supply product kinds are supported."
            )
        if command.usage_type and command.usage_type not in VALID_USAGE_TYPES:
            raise AdminInputSupplyValidationError("Usage type is not supported.")
        if (
            command.purchase_uom
            and command.purchase_uom.strip().upper() != command.unit_of_measure.strip().upper()
            and command.purchase_conversion_factor is None
        ):
            raise AdminInputSupplyValidationError(
                "Conversion factor is required when purchase UOM differs."
            )

    def _get_product(self, session: Session, product_id: uuid.UUID) -> Product:
        product = session.get(Product, product_id)
        if product is None or product.product_kind not in CATALOG_INPUT_PRODUCT_KINDS:
            raise ProductNotFoundError("Input or consumable item was not found.")
        return product

    def _get_product_class(self, session: Session, class_id: uuid.UUID) -> ProductClass:
        product_class = session.get(ProductClass, class_id)
        if product_class is None:
            raise ProductClassNotFoundError("Product class was not found.")
        return product_class

    def _get_supplier(self, session: Session, supplier_id: uuid.UUID) -> Supplier:
        supplier = session.get(Supplier, supplier_id)
        if supplier is None:
            raise AdminInputSupplyValidationError("Supplier was not found.")
        return supplier

    def _ensure_unique_code(
        self,
        session: Session,
        code: str,
        *,
        product_id: uuid.UUID | None = None,
    ) -> None:
        statement = select(Product).where(Product.code == code.strip().upper())
        if product_id is not None:
            statement = statement.where(Product.id != product_id)
        if session.execute(statement).scalar_one_or_none() is not None:
            raise AdminInputSupplyValidationError("Input code must be unique.")

    def _last_movement_at(
        self,
        session: Session,
        product_id: uuid.UUID,
        branch_id: uuid.UUID | None,
    ) -> datetime | None:
        statement = select(func.max(InventoryMovement.occurred_at)).where(
            InventoryMovement.product_id == product_id
        )
        if branch_id is not None:
            statement = statement.where(InventoryMovement.branch_id == branch_id)
        return session.execute(statement).scalar_one_or_none()

    def _last_purchase_cost(
        self, suppliers: list[tuple[SupplierProduct, Supplier]]
    ) -> Decimal | None:
        prices = [
            relation.last_known_price
            for relation, _ in sorted(
                suppliers,
                key=lambda item: item[0].updated_at,
                reverse=True,
            )
            if relation.last_known_price is not None
        ]
        return prices[0] if prices else None

    def _stock_state(self, context: _InputSupplyContext) -> AdminInputSupplyStockState:
        total_stock = self._total_stock(context)
        if total_stock is None:
            return "no_inventory"
        return self._branch_stock_state(context, total_stock)

    def _branch_stock_state(
        self,
        context: _InputSupplyContext,
        quantity: Decimal,
    ) -> AdminInputSupplyStockState:
        if quantity < ZERO:
            return "negative_stock"
        if quantity == ZERO:
            return "out_of_stock"
        threshold = context.product.reorder_point or context.product.minimum_stock
        if threshold is not None and quantity <= threshold:
            return "low_stock"
        return "in_stock"

    def _total_stock(self, context: _InputSupplyContext) -> Decimal | None:
        if not context.inventory:
            return None
        return sum((row.quantity_on_hand for row in context.inventory), ZERO)

    def _warning_state(
        self,
        warnings: list[AdminInputSupplyWarningView],
    ) -> AdminInputSupplyWarningState:
        if any(warning.severity == "critical" for warning in warnings):
            return "critical"
        if any(warning.severity == "warning" for warning in warnings):
            return "warning"
        if warnings:
            return "info"
        return "ok"

    def _matches_search(self, context: _InputSupplyContext, search: str) -> bool:
        needle = search.lower()
        values = [
            context.product.code,
            context.product.name,
            context.product.quick_name,
            context.product.search_aliases,
            context.product_class.code,
            context.product_class.name,
            *(supplier.legal_name for _, supplier in context.suppliers),
            *(supplier.commercial_name for _, supplier in context.suppliers),
            *(relation.supplier_sku for relation, _ in context.suppliers),
        ]
        return any(needle in str(value).lower() for value in values if value)

    def _metadata(self, product: Product) -> dict[str, object]:
        return {
            "code": product.code,
            "is_active": product.is_active,
            "is_inventory_tracked": product.is_inventory_tracked,
            "is_purchasable": product.is_purchasable,
            "product_id": str(product.id),
            "product_kind": product.product_kind,
        }

    def _record_change(
        self,
        session: Session,
        *,
        action: str,
        current_user: AuthenticatedUser,
        event_name: str,
        metadata: dict[str, object],
        product: Product,
        request_id: str | None,
    ) -> None:
        self._record_audit_only(
            session,
            action=action,
            current_user=current_user,
            metadata=metadata,
            product=product,
            request_id=request_id,
        )
        self._outbox_writer.append(
            session,
            aggregate_type=INPUT_SUPPLY_RESOURCE_TYPE,
            aggregate_id=str(product.id),
            event_name=event_name,
            payload=metadata,
            headers={"request_id": request_id} if request_id else {},
        )

    def _record_audit_only(
        self,
        session: Session,
        *,
        action: str,
        current_user: AuthenticatedUser,
        metadata: dict[str, object],
        product: Product,
        request_id: str | None,
    ) -> None:
        self._audit_recorder.record(
            session,
            actor_id=current_user.id,
            action=action,
            resource_type=INPUT_SUPPLY_RESOURCE_TYPE,
            resource_id=str(product.id),
            branch_id=None,
            request_id=request_id,
            metadata=metadata,
        )


def _normalize_optional(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None
