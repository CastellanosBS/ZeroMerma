from __future__ import annotations

import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from pydantic import TypeAdapter
from sqlalchemy import Select, and_, func, or_, select
from sqlalchemy.orm import Session

from zeromerma_api.modules.audit.application.service import AuditRecorder
from zeromerma_api.modules.branches.infrastructure.models import Branch
from zeromerma_api.modules.catalog.domain.constants import (
    CATALOG_PRODUCT_KIND_CONSUMABLE,
    CATALOG_PRODUCT_KIND_DISPOSABLE,
    CATALOG_PRODUCT_KIND_FINISHED_GOOD,
    CATALOG_PRODUCT_KIND_RAW_MATERIAL,
)
from zeromerma_api.modules.catalog.infrastructure.models import Product, ProductClass
from zeromerma_api.modules.identity.application.schemas import AuthenticatedUser
from zeromerma_api.modules.identity.infrastructure.models import User
from zeromerma_api.modules.inventory.application.admin_schemas import (
    AdminInventoryAdjustmentRequest,
    AdminInventoryAdjustmentType,
    AdminInventoryAdjustmentView,
    AdminInventoryBranchLocationView,
    AdminInventoryDetailView,
    AdminInventoryFilterOptionsView,
    AdminInventoryFilterOptionView,
    AdminInventoryListItemView,
    AdminInventoryListResponse,
    AdminInventoryLocationCode,
    AdminInventoryMetricsView,
    AdminInventoryMovementDirection,
    AdminInventoryMovementsResponse,
    AdminInventoryMovementSummaryView,
    AdminInventoryMovementView,
    AdminInventoryProductKind,
    AdminInventoryProductView,
    AdminInventoryRelatedActionsView,
    AdminInventoryStockBreakdownView,
    AdminInventoryStockState,
    AdminInventoryWarningSeverity,
    AdminInventoryWarningView,
)
from zeromerma_api.modules.inventory.domain.constants import (
    INVENTORY_ADJUSTMENT_TYPE_DECREASE,
    INVENTORY_ADJUSTMENT_TYPE_INCREASE,
    INVENTORY_ADJUSTMENT_TYPE_SET_COUNTED,
    INVENTORY_LOCATION_BACKROOM,
    INVENTORY_LOCATION_COUNTER,
    INVENTORY_LOCATION_IN_TRANSIT,
    INVENTORY_LOCATION_WASTE,
    INVENTORY_MOVEMENT_DIRECTION_IN,
    INVENTORY_MOVEMENT_DIRECTION_OUT,
    INVENTORY_MOVEMENT_TYPE_MANUAL_ADJUSTMENT,
    INVENTORY_STOCK_STATE_IN_STOCK,
    INVENTORY_STOCK_STATE_LOW_STOCK,
    INVENTORY_STOCK_STATE_NEGATIVE_STOCK,
    INVENTORY_STOCK_STATE_OUT_OF_STOCK,
    OUTBOX_EVENT_ADMIN_INVENTORY_ADJUSTMENT_CREATED_V1,
    VALID_INVENTORY_LOCATION_CODES,
)
from zeromerma_api.modules.inventory.domain.exceptions import (
    InventoryNotFoundError,
    InventoryValidationError,
)
from zeromerma_api.modules.inventory.infrastructure.models import (
    InventoryAdjustment,
    InventoryBalance,
    InventoryMovement,
)
from zeromerma_api.modules.outbox.application.service import OutboxWriter

_ADMIN_INVENTORY_ADJUSTMENT_TYPE_ADAPTER: TypeAdapter[AdminInventoryAdjustmentType] = TypeAdapter(
    AdminInventoryAdjustmentType
)
_ADMIN_INVENTORY_LOCATION_CODE_ADAPTER: TypeAdapter[AdminInventoryLocationCode] = TypeAdapter(
    AdminInventoryLocationCode
)
_ADMIN_INVENTORY_MOVEMENT_DIRECTION_ADAPTER: TypeAdapter[AdminInventoryMovementDirection] = (
    TypeAdapter(AdminInventoryMovementDirection)
)
_ADMIN_INVENTORY_PRODUCT_KIND_ADAPTER: TypeAdapter[AdminInventoryProductKind] = TypeAdapter(
    AdminInventoryProductKind
)
AUDIT_ACTION_ADMIN_INVENTORY_ADJUSTMENT_CREATED = "admin.inventory.adjustment.created"
INVENTORY_BALANCE_RESOURCE_TYPE = "inventory_balance"
INVENTORY_ADJUSTMENT_SOURCE_DOCUMENT_TYPE = "INVENTORY_ADJUSTMENT"
STALE_MOVEMENT_DAYS = 30

LOCATION_LABELS = {
    INVENTORY_LOCATION_BACKROOM: "Fondo",
    INVENTORY_LOCATION_COUNTER: "Mostrador",
    INVENTORY_LOCATION_IN_TRANSIT: "En transito",
    INVENTORY_LOCATION_WASTE: "Merma / descarte",
}

PRODUCT_KIND_LABELS = {
    CATALOG_PRODUCT_KIND_FINISHED_GOOD: "Producto terminado",
    CATALOG_PRODUCT_KIND_RAW_MATERIAL: "Materia prima",
    CATALOG_PRODUCT_KIND_CONSUMABLE: "Consumible",
    CATALOG_PRODUCT_KIND_DISPOSABLE: "Desechable",
}


@dataclass(frozen=True)
class _InventoryRow:
    balance: InventoryBalance
    branch: Branch
    last_movement_at: datetime | None
    product: Product
    product_class: ProductClass


class AdminInventoryService:
    def __init__(
        self,
        audit_recorder: AuditRecorder | None = None,
        outbox_writer: OutboxWriter | None = None,
    ) -> None:
        self._audit_recorder = audit_recorder or AuditRecorder()
        self._outbox_writer = outbox_writer or OutboxWriter()

    def list_inventory(
        self,
        session: Session,
        *,
        branch_id: uuid.UUID | None,
        class_id: uuid.UUID | None,
        location_code: str | None,
        product_kind: str | None,
        product_status: str | None,
        stock_state: str | None,
        search: str | None,
        page: int,
        page_size: int,
    ) -> AdminInventoryListResponse:
        rows = self._fetch_rows(
            session,
            branch_id=branch_id,
            class_id=class_id,
            location_code=location_code,
            product_kind=product_kind,
            product_status=product_status,
            search=search,
        )

        normalized_stock_state = _normalize_optional(stock_state)
        if normalized_stock_state and normalized_stock_state != "all":
            rows = [row for row in rows if self._stock_state(row) == normalized_stock_state]

        items = [self._to_list_item(row) for row in rows]
        total = len(items)
        safe_page = max(page, 1)
        safe_page_size = min(max(page_size, 1), 100)
        offset = (safe_page - 1) * safe_page_size

        return AdminInventoryListResponse(
            filter_options=self._build_filter_options(session),
            items=items[offset : offset + safe_page_size],
            metrics=self._build_metrics(rows),
            page=safe_page,
            page_size=safe_page_size,
            total=total,
        )

    def get_inventory_detail(
        self,
        session: Session,
        *,
        balance_id: uuid.UUID,
    ) -> AdminInventoryDetailView:
        row = self._get_row(session, balance_id)
        return self._to_detail(session, row)

    def list_movements(
        self,
        session: Session,
        *,
        balance_id: uuid.UUID,
        page: int,
        page_size: int,
    ) -> AdminInventoryMovementsResponse:
        row = self._get_row(session, balance_id)
        query = self._movement_query(row).order_by(InventoryMovement.occurred_at.desc())
        movements = session.execute(query).scalars().all()
        total = len(movements)
        safe_page = max(page, 1)
        safe_page_size = min(max(page_size, 1), 100)
        offset = (safe_page - 1) * safe_page_size
        page_movements = movements[offset : offset + safe_page_size]

        return AdminInventoryMovementsResponse(
            items=[self._to_movement_view(session, movement) for movement in page_movements],
            page=safe_page,
            page_size=safe_page_size,
            total=total,
        )

    def create_adjustment(
        self,
        session: Session,
        *,
        current_user: AuthenticatedUser,
        command: AdminInventoryAdjustmentRequest,
        request_id: str | None,
    ) -> AdminInventoryAdjustmentView:
        product = session.get(Product, command.product_id)
        if product is None:
            raise InventoryNotFoundError("Product was not found.")

        branch = session.get(Branch, command.branch_id)
        if branch is None:
            raise InventoryNotFoundError("Branch was not found.")

        if command.location_code not in VALID_INVENTORY_LOCATION_CODES:
            raise InventoryValidationError("Inventory location is not supported.")

        balance = self._get_or_create_balance(
            session,
            product_id=product.id,
            branch_id=branch.id,
            location_code=command.location_code,
        )
        previous_quantity = Decimal(balance.quantity_on_hand)
        new_quantity = self._calculate_new_quantity(
            previous_quantity=previous_quantity,
            adjustment_type=command.adjustment_type,
            quantity=command.quantity,
        )
        movement_quantity = abs(new_quantity - previous_quantity)
        if movement_quantity <= 0:
            raise InventoryValidationError("Adjustment must change inventory quantity.")

        direction = (
            INVENTORY_MOVEMENT_DIRECTION_IN
            if new_quantity > previous_quantity
            else INVENTORY_MOVEMENT_DIRECTION_OUT
        )

        adjustment = InventoryAdjustment(
            adjustment_type=command.adjustment_type,
            branch_id=branch.id,
            created_by_user_id=current_user.id,
            location_code=command.location_code,
            new_quantity=new_quantity,
            notes=command.notes,
            previous_quantity=previous_quantity,
            product_id=product.id,
            quantity=command.quantity,
            reason=command.reason,
        )
        session.add(adjustment)
        session.flush()

        balance.quantity_on_hand = new_quantity
        movement = InventoryMovement(
            adjustment_id=adjustment.id,
            balance_after=new_quantity,
            branch_id=branch.id,
            direction=direction,
            location_code=command.location_code,
            movement_type=INVENTORY_MOVEMENT_TYPE_MANUAL_ADJUSTMENT,
            notes=command.notes,
            operator_user_id=current_user.id,
            product_id=product.id,
            quantity=movement_quantity,
            reason=command.reason,
            source_document_id=adjustment.id,
            source_document_type=INVENTORY_ADJUSTMENT_SOURCE_DOCUMENT_TYPE,
            unit_of_measure=product.unit_of_measure,
        )
        session.add(movement)
        session.flush()

        metadata = {
            "adjustment_id": str(adjustment.id),
            "adjustment_type": command.adjustment_type,
            "branch_id": str(branch.id),
            "location_code": command.location_code,
            "new_quantity": str(new_quantity),
            "previous_quantity": str(previous_quantity),
            "product_id": str(product.id),
            "quantity": str(command.quantity),
            "reason": command.reason,
        }
        self._audit_recorder.record(
            session,
            actor_id=current_user.id,
            action=AUDIT_ACTION_ADMIN_INVENTORY_ADJUSTMENT_CREATED,
            resource_type=INVENTORY_BALANCE_RESOURCE_TYPE,
            resource_id=str(balance.id),
            branch_id=branch.id,
            request_id=request_id,
            metadata=metadata,
        )
        self._outbox_writer.append(
            session,
            aggregate_type=INVENTORY_BALANCE_RESOURCE_TYPE,
            aggregate_id=str(balance.id),
            event_name=OUTBOX_EVENT_ADMIN_INVENTORY_ADJUSTMENT_CREATED_V1,
            payload=metadata,
            headers={"request_id": request_id} if request_id else {},
        )
        session.commit()

        return AdminInventoryAdjustmentView(
            adjustment_type=_ADMIN_INVENTORY_ADJUSTMENT_TYPE_ADAPTER.validate_python(
                adjustment.adjustment_type
            ),
            balance_id=balance.id,
            branch_id=adjustment.branch_id,
            created_at=adjustment.created_at,
            created_by_user_id=adjustment.created_by_user_id,
            id=adjustment.id,
            location_code=_ADMIN_INVENTORY_LOCATION_CODE_ADAPTER.validate_python(
                adjustment.location_code
            ),
            new_quantity=adjustment.new_quantity,
            notes=adjustment.notes,
            previous_quantity=adjustment.previous_quantity,
            product_id=adjustment.product_id,
            quantity=adjustment.quantity,
            reason=adjustment.reason,
        )

    def _fetch_rows(
        self,
        session: Session,
        *,
        branch_id: uuid.UUID | None,
        class_id: uuid.UUID | None,
        location_code: str | None,
        product_kind: str | None,
        product_status: str | None,
        search: str | None,
    ) -> list[_InventoryRow]:
        last_movement_subquery = (
            select(
                InventoryMovement.product_id.label("product_id"),
                InventoryMovement.branch_id.label("branch_id"),
                InventoryMovement.location_code.label("location_code"),
                func.max(InventoryMovement.occurred_at).label("last_movement_at"),
            )
            .group_by(
                InventoryMovement.product_id,
                InventoryMovement.branch_id,
                InventoryMovement.location_code,
            )
            .subquery()
        )
        query = (
            select(
                InventoryBalance,
                Product,
                ProductClass,
                Branch,
                last_movement_subquery.c.last_movement_at,
            )
            .join(Product, InventoryBalance.product_id == Product.id)
            .join(ProductClass, Product.product_class_id == ProductClass.id)
            .join(Branch, InventoryBalance.branch_id == Branch.id)
            .outerjoin(
                last_movement_subquery,
                and_(
                    last_movement_subquery.c.product_id == InventoryBalance.product_id,
                    last_movement_subquery.c.branch_id == InventoryBalance.branch_id,
                    last_movement_subquery.c.location_code == InventoryBalance.location_code,
                ),
            )
        )

        if branch_id is not None:
            query = query.where(InventoryBalance.branch_id == branch_id)
        if class_id is not None:
            query = query.where(Product.product_class_id == class_id)

        normalized_location = _normalize_optional(location_code)
        if normalized_location and normalized_location != "all":
            query = query.where(InventoryBalance.location_code == normalized_location)

        normalized_kind = _normalize_optional(product_kind)
        if normalized_kind and normalized_kind != "all":
            query = query.where(Product.product_kind == normalized_kind)

        normalized_status = _normalize_optional(product_status)
        if normalized_status == "active":
            query = query.where(Product.is_active.is_(True))
        elif normalized_status == "inactive":
            query = query.where(Product.is_active.is_(False))

        normalized_search = _normalize_optional(search)
        if normalized_search:
            pattern = f"%{normalized_search.lower()}%"
            query = query.where(
                or_(
                    func.lower(Product.code).like(pattern),
                    func.lower(Product.name).like(pattern),
                    func.lower(ProductClass.name).like(pattern),
                    func.lower(Branch.name).like(pattern),
                    func.lower(Branch.code).like(pattern),
                ),
            )

        records = session.execute(
            query.order_by(
                Branch.name.asc(), Product.name.asc(), InventoryBalance.location_code.asc()
            ),
        ).all()
        return [
            _InventoryRow(
                balance=balance,
                branch=branch,
                last_movement_at=last_movement_at,
                product=product,
                product_class=product_class,
            )
            for balance, product, product_class, branch, last_movement_at in records
        ]

    def _get_row(self, session: Session, balance_id: uuid.UUID) -> _InventoryRow:
        result = session.execute(
            select(InventoryBalance, Product, ProductClass, Branch)
            .join(Product, InventoryBalance.product_id == Product.id)
            .join(ProductClass, Product.product_class_id == ProductClass.id)
            .join(Branch, InventoryBalance.branch_id == Branch.id)
            .where(InventoryBalance.id == balance_id),
        ).one_or_none()
        if result is None:
            raise InventoryNotFoundError("Inventory balance was not found.")

        balance, product, product_class, branch = result
        last_movement_at = session.execute(
            select(func.max(InventoryMovement.occurred_at)).where(
                InventoryMovement.product_id == balance.product_id,
                InventoryMovement.branch_id == balance.branch_id,
                InventoryMovement.location_code == balance.location_code,
            ),
        ).scalar_one_or_none()
        return _InventoryRow(
            balance=balance,
            branch=branch,
            last_movement_at=last_movement_at,
            product=product,
            product_class=product_class,
        )

    def _to_list_item(self, row: _InventoryRow) -> AdminInventoryListItemView:
        warnings = self._build_warnings(row)
        warning_state = self._warning_state(warnings)
        return AdminInventoryListItemView(
            available_quantity=row.balance.quantity_on_hand,
            balance_id=row.balance.id,
            branch_id=row.branch.id,
            branch_is_active=row.branch.is_active,
            branch_name=row.branch.name,
            class_id=row.product_class.id,
            class_name=row.product_class.name,
            in_transit_quantity=None,
            last_movement_at=row.last_movement_at,
            location_code=_ADMIN_INVENTORY_LOCATION_CODE_ADAPTER.validate_python(
                row.balance.location_code
            ),
            location_name=self._location_name(row.balance.location_code),
            product_code=row.product.code,
            product_id=row.product.id,
            product_is_active=row.product.is_active,
            product_kind=_ADMIN_INVENTORY_PRODUCT_KIND_ADAPTER.validate_python(
                row.product.product_kind
            ),
            product_name=row.product.name,
            quantity_on_hand=row.balance.quantity_on_hand,
            reserved_quantity=None,
            stock_state=self._stock_state(row),
            unit_of_measure=row.product.unit_of_measure,
            warning_state=warning_state,
            warnings=warnings,
        )

    def _to_detail(self, session: Session, row: _InventoryRow) -> AdminInventoryDetailView:
        movements = (
            session.execute(
                self._movement_query(row).order_by(InventoryMovement.occurred_at.desc()).limit(20),
            )
            .scalars()
            .all()
        )
        warnings = self._build_warnings(row)
        estimated_value = self._estimated_value(row)

        return AdminInventoryDetailView(
            balance_id=row.balance.id,
            branch_location=AdminInventoryBranchLocationView(
                branch_id=row.branch.id,
                branch_is_active=row.branch.is_active,
                branch_name=row.branch.name,
                location_code=_ADMIN_INVENTORY_LOCATION_CODE_ADAPTER.validate_python(
                    row.balance.location_code
                ),
                location_name=self._location_name(row.balance.location_code),
            ),
            movement_summary=self._movement_summary(movements),
            movements=[self._to_movement_view(session, movement) for movement in movements],
            product=AdminInventoryProductView(
                class_id=row.product_class.id,
                class_name=row.product_class.name,
                code=row.product.code,
                id=row.product.id,
                is_active=row.product.is_active,
                is_sellable=row.product.is_sellable,
                name=row.product.name,
                product_kind=_ADMIN_INVENTORY_PRODUCT_KIND_ADAPTER.validate_python(
                    row.product.product_kind
                ),
                standard_cost=row.product.standard_cost,
                unit_of_measure=row.product.unit_of_measure,
            ),
            related_actions=AdminInventoryRelatedActionsView(),
            stock_breakdown=AdminInventoryStockBreakdownView(
                available_quantity=row.balance.quantity_on_hand,
                estimated_value=estimated_value,
                in_transit_quantity=None,
                quantity_on_hand=row.balance.quantity_on_hand,
                reserved_quantity=None,
                unit_of_measure=row.product.unit_of_measure,
            ),
            stock_state=self._stock_state(row),
            warnings=warnings,
        )

    def _build_metrics(self, rows: list[_InventoryRow]) -> AdminInventoryMetricsView:
        return AdminInventoryMetricsView(
            estimated_value=sum(
                ((self._estimated_value(row) or Decimal("0")) for row in rows), Decimal("0")
            ),
            negative_stock=sum(1 for row in rows if row.balance.quantity_on_hand < 0),
            products_with_stock=sum(1 for row in rows if row.balance.quantity_on_hand > 0),
            stale_stock=sum(1 for row in rows if self._is_stale(row)),
            total_records=len(rows),
        )

    def _build_filter_options(self, session: Session) -> AdminInventoryFilterOptionsView:
        branches = (
            session.execute(select(Branch).order_by(Branch.name.asc(), Branch.code.asc()))
            .scalars()
            .all()
        )
        classes = (
            session.execute(
                select(ProductClass).order_by(ProductClass.name.asc(), ProductClass.code.asc()),
            )
            .scalars()
            .all()
        )
        products = (
            session.execute(select(Product).order_by(Product.name.asc(), Product.code.asc()))
            .scalars()
            .all()
        )
        return AdminInventoryFilterOptionsView(
            branches=[
                AdminInventoryFilterOptionView(id=branch.id, label=f"{branch.name} - {branch.code}")
                for branch in branches
            ],
            classes=[
                AdminInventoryFilterOptionView(id=product_class.id, label=product_class.name)
                for product_class in classes
            ],
            locations=[
                AdminInventoryFilterOptionView(id=code, label=label)
                for code, label in LOCATION_LABELS.items()
            ],
            products=[
                AdminInventoryFilterOptionView(
                    id=product.id, label=f"{product.name} - {product.code}"
                )
                for product in products
            ],
            product_kinds=[
                AdminInventoryFilterOptionView(id=code, label=label)
                for code, label in PRODUCT_KIND_LABELS.items()
            ],
        )

    def _build_warnings(self, row: _InventoryRow) -> list[AdminInventoryWarningView]:
        warnings: list[AdminInventoryWarningView] = []
        if row.balance.quantity_on_hand < 0:
            warnings.append(
                AdminInventoryWarningView(
                    code="negative_stock",
                    message="La existencia registrada es negativa.",
                    severity="critical",
                ),
            )
        if not row.branch.is_active:
            warnings.append(
                AdminInventoryWarningView(
                    code="inactive_branch",
                    message="La sucursal esta inactiva y conserva inventario registrado.",
                    severity="warning",
                ),
            )
        if not row.product.is_active and row.balance.quantity_on_hand != 0:
            warnings.append(
                AdminInventoryWarningView(
                    code="inactive_product_with_stock",
                    message="El producto esta inactivo pero tiene existencia registrada.",
                    severity="warning",
                ),
            )
        if self._is_stale(row):
            warnings.append(
                AdminInventoryWarningView(
                    code="stale_stock",
                    message="No hay movimientos recientes para este registro de inventario.",
                    severity="info",
                ),
            )
        if row.product.standard_cost is None and row.balance.quantity_on_hand != 0:
            warnings.append(
                AdminInventoryWarningView(
                    code="missing_standard_cost",
                    message="No hay costo estandar para estimar valor de inventario.",
                    severity="info",
                ),
            )
        return warnings

    def _stock_state(self, row: _InventoryRow) -> AdminInventoryStockState:
        if row.balance.quantity_on_hand < 0:
            return INVENTORY_STOCK_STATE_NEGATIVE_STOCK
        if row.balance.quantity_on_hand == 0:
            return INVENTORY_STOCK_STATE_OUT_OF_STOCK
        return INVENTORY_STOCK_STATE_IN_STOCK

    def _movement_query(self, row: _InventoryRow) -> Select[tuple[InventoryMovement]]:
        return select(InventoryMovement).where(
            InventoryMovement.product_id == row.balance.product_id,
            InventoryMovement.branch_id == row.balance.branch_id,
            InventoryMovement.location_code == row.balance.location_code,
        )

    def _movement_summary(
        self, movements: Sequence[InventoryMovement]
    ) -> AdminInventoryMovementSummaryView:
        last_inbound = next(
            (
                movement.occurred_at
                for movement in movements
                if movement.direction == INVENTORY_MOVEMENT_DIRECTION_IN
            ),
            None,
        )
        last_outbound = next(
            (
                movement.occurred_at
                for movement in movements
                if movement.direction == INVENTORY_MOVEMENT_DIRECTION_OUT
            ),
            None,
        )
        last_adjustment = next(
            (
                movement.occurred_at
                for movement in movements
                if movement.movement_type == INVENTORY_MOVEMENT_TYPE_MANUAL_ADJUSTMENT
            ),
            None,
        )
        return AdminInventoryMovementSummaryView(
            last_adjustment_at=last_adjustment,
            last_inbound_at=last_inbound,
            last_movement_at=movements[0].occurred_at if movements else None,
            last_outbound_at=last_outbound,
        )

    def _to_movement_view(
        self, session: Session, movement: InventoryMovement
    ) -> AdminInventoryMovementView:
        branch = session.get(Branch, movement.branch_id)
        user = session.get(User, movement.operator_user_id) if movement.operator_user_id else None
        return AdminInventoryMovementView(
            balance_after=movement.balance_after,
            branch_id=movement.branch_id,
            branch_name=branch.name if branch else "Sucursal no disponible",
            direction=_ADMIN_INVENTORY_MOVEMENT_DIRECTION_ADAPTER.validate_python(
                movement.direction
            ),
            id=movement.id,
            location_code=_ADMIN_INVENTORY_LOCATION_CODE_ADAPTER.validate_python(
                movement.location_code
            ),
            movement_type=movement.movement_type,
            notes=movement.notes,
            occurred_at=movement.occurred_at,
            operator_name=user.full_name if user else None,
            product_id=movement.product_id,
            quantity=movement.quantity,
            reason=movement.reason,
            source_document_id=movement.source_document_id,
            source_document_type=movement.source_document_type,
            unit_of_measure=movement.unit_of_measure,
        )

    def _get_or_create_balance(
        self,
        session: Session,
        *,
        product_id: uuid.UUID,
        branch_id: uuid.UUID,
        location_code: str,
    ) -> InventoryBalance:
        balance = session.execute(
            select(InventoryBalance)
            .where(
                InventoryBalance.product_id == product_id,
                InventoryBalance.branch_id == branch_id,
                InventoryBalance.location_code == location_code,
            )
            .with_for_update(),
        ).scalar_one_or_none()
        if balance is not None:
            return balance

        balance = InventoryBalance(
            branch_id=branch_id,
            location_code=location_code,
            product_id=product_id,
            quantity_on_hand=Decimal("0"),
        )
        session.add(balance)
        session.flush()
        return balance

    def _calculate_new_quantity(
        self,
        *,
        adjustment_type: str,
        previous_quantity: Decimal,
        quantity: Decimal,
    ) -> Decimal:
        if adjustment_type == INVENTORY_ADJUSTMENT_TYPE_INCREASE:
            return previous_quantity + quantity
        if adjustment_type == INVENTORY_ADJUSTMENT_TYPE_DECREASE:
            return previous_quantity - quantity
        if adjustment_type == INVENTORY_ADJUSTMENT_TYPE_SET_COUNTED:
            return quantity
        raise InventoryValidationError("Unsupported inventory adjustment type.")

    def _location_name(self, location_code: str) -> str:
        return LOCATION_LABELS.get(location_code, location_code)

    def _warning_state(
        self,
        warnings: list[AdminInventoryWarningView],
    ) -> AdminInventoryWarningSeverity | None:
        if any(warning.severity == "critical" for warning in warnings):
            return "critical"
        if any(warning.severity == "warning" for warning in warnings):
            return "warning"
        if warnings:
            return "info"
        return None

    def _is_stale(self, row: _InventoryRow) -> bool:
        if row.last_movement_at is None:
            return True
        return row.last_movement_at < datetime.now(tz=UTC) - timedelta(days=STALE_MOVEMENT_DAYS)

    def _estimated_value(self, row: _InventoryRow) -> Decimal | None:
        if row.product.standard_cost is None:
            return None
        return Decimal(row.balance.quantity_on_hand) * Decimal(row.product.standard_cost)


def _normalize_optional(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


_ = INVENTORY_STOCK_STATE_LOW_STOCK
