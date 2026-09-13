from __future__ import annotations

import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import ROUND_HALF_UP, Decimal

from pydantic import TypeAdapter
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from zeromerma_api.core.config import ApiSettings, get_settings
from zeromerma_api.modules.audit.application.service import AuditRecorder
from zeromerma_api.modules.branches.infrastructure.models import Branch, Workstation
from zeromerma_api.modules.catalog.infrastructure.models import Product, ProductClass
from zeromerma_api.modules.identity.application.actions import restrict_actions
from zeromerma_api.modules.identity.application.schemas import AuthenticatedUser
from zeromerma_api.modules.identity.infrastructure.models import User
from zeromerma_api.modules.inventory.domain.constants import (
    INVENTORY_LOCATION_BACKROOM,
    INVENTORY_LOCATION_COUNTER,
    INVENTORY_LOCATION_IN_TRANSIT,
    INVENTORY_MOVEMENT_DIRECTION_OUT,
    INVENTORY_MOVEMENT_TYPE_WASTE_RECORD,
)
from zeromerma_api.modules.inventory.infrastructure.models import (
    InventoryBalance,
    InventoryMovement,
)
from zeromerma_api.modules.operations.domain.constants import (
    OPERATION_BUCKET_WASTE,
    OPERATION_DOCUMENT_STATUS_CANCELLED,
    OPERATION_DOCUMENT_STATUS_COMMITTED,
    OPERATION_DOCUMENT_TYPE_WASTE_RECORD,
    OUTBOX_EVENT_WASTE_RECORD_COMMITTED_V1,
    OUTBOX_EVENT_WASTE_RECORD_HIGH_IMPACT_ALERT_V1,
    WASTE_REASON_CODES_REQUIRING_NOTE,
    WASTE_REASON_CONTAMINATED,
    WASTE_REASON_DAMAGED,
    WASTE_REASON_EXPIRED,
    WASTE_REASON_OLD_COUNTER,
)
from zeromerma_api.modules.operations.infrastructure.models import (
    OperationDocument,
    OperationDocumentLine,
    WasteReason,
)
from zeromerma_api.modules.outbox.application.service import OutboxWriter
from zeromerma_api.modules.waste.application.admin_schemas import (
    AdminWasteAvailableActionsView,
    AdminWasteCreateRequest,
    AdminWasteDetailView,
    AdminWasteEvidenceView,
    AdminWasteFilterOptionsView,
    AdminWasteFilterOptionView,
    AdminWasteImpactLevel,
    AdminWasteInventoryImpactView,
    AdminWasteInventoryMovementView,
    AdminWasteLineView,
    AdminWasteListItemView,
    AdminWasteListResponse,
    AdminWasteLocationCode,
    AdminWasteMetricsView,
    AdminWasteOverviewView,
    AdminWasteProductInventoryContextView,
    AdminWasteProductKind,
    AdminWasteReasonClassificationView,
    AdminWasteReasonView,
    AdminWasteRelatedDocumentView,
    AdminWasteStatus,
    AdminWasteWarningSeverity,
    AdminWasteWarningView,
)
from zeromerma_api.modules.waste.domain.constants import (
    ADMIN_WASTE_IMPACT_LEVEL_HIGH,
    ADMIN_WASTE_IMPACT_LEVEL_NORMAL,
    ADMIN_WASTE_RESOURCE_TYPE,
    ADMIN_WASTE_SOURCE_DOCUMENT_TYPE,
    AUDIT_ACTION_ADMIN_WASTE_CONFIRMED,
    AUDIT_ACTION_ADMIN_WASTE_HIGH_IMPACT_NOTIFIED,
)
from zeromerma_api.modules.waste.domain.exceptions import WasteNotFoundError, WasteValidationError

_ADMIN_WASTE_IMPACT_LEVEL_ADAPTER: TypeAdapter[AdminWasteImpactLevel] = TypeAdapter(
    AdminWasteImpactLevel
)
_ADMIN_WASTE_LOCATION_CODE_ADAPTER: TypeAdapter[AdminWasteLocationCode] = TypeAdapter(
    AdminWasteLocationCode
)
_ADMIN_WASTE_PRODUCT_KIND_ADAPTER: TypeAdapter[AdminWasteProductKind] = TypeAdapter(
    AdminWasteProductKind
)
_ADMIN_WASTE_STATUS_ADAPTER: TypeAdapter[AdminWasteStatus] = TypeAdapter(AdminWasteStatus)
DECIMAL_3 = Decimal("0.001")
ZERO = Decimal("0")

LOCATION_LABELS = {
    INVENTORY_LOCATION_BACKROOM: "Fondo",
    INVENTORY_LOCATION_COUNTER: "Mostrador",
    INVENTORY_LOCATION_IN_TRANSIT: "En transito",
}

PRODUCT_KIND_LABELS = {
    "FINISHED_GOOD": "Producto terminado",
    "RAW_MATERIAL": "Materia prima",
    "CONSUMABLE": "Consumible",
    "DISPOSABLE": "Desechable",
}

REASON_DESCRIPTIONS = {
    WASTE_REASON_OLD_COUNTER: "Producto del mostrador que ya no puede venderse.",
    WASTE_REASON_DAMAGED: "Producto danado fisicamente durante manejo u operacion.",
    WASTE_REASON_CONTAMINATED: "Riesgo sanitario o contaminacion que impide uso o venta.",
    WASTE_REASON_EXPIRED: "Producto o insumo caducado.",
    "OTHER": "Motivo no clasificado; requiere nota operacional.",
}


@dataclass(frozen=True)
class _WasteLine:
    line: OperationDocumentLine
    product: Product
    product_class: ProductClass


@dataclass(frozen=True)
class _WasteRow:
    branch: Branch
    created_by_user: User
    document: OperationDocument
    lines: list[_WasteLine]
    reason: WasteReason
    workstation: Workstation


@dataclass(frozen=True)
class _ResolvedProduct:
    product: Product
    product_class: ProductClass


class AdminWasteService:
    def __init__(
        self,
        audit_recorder: AuditRecorder | None = None,
        outbox_writer: OutboxWriter | None = None,
        settings: ApiSettings | None = None,
    ) -> None:
        self._audit_recorder = audit_recorder or AuditRecorder()
        self._outbox_writer = outbox_writer or OutboxWriter()
        self._settings = settings or get_settings()

    def list_waste(
        self,
        session: Session,
        *,
        branch_id: uuid.UUID | None,
        class_id: uuid.UUID | None,
        date_from: datetime | None,
        date_to: datetime | None,
        evidence_state: str | None,
        impact_level: str | None,
        location_code: str | None,
        operator_user_id: uuid.UUID | None,
        product_id: uuid.UUID | None,
        product_kind: str | None,
        reason_code: str | None,
        search: str | None,
        status_filter: str | None,
        warning_state: str | None,
        page: int,
        page_size: int,
    ) -> AdminWasteListResponse:
        rows = self._fetch_rows(
            session,
            branch_id=branch_id,
            date_from=date_from,
            date_to=date_to,
            location_code=location_code,
            operator_user_id=operator_user_id,
            reason_code=reason_code,
            status_filter=status_filter,
        )

        if class_id is not None:
            rows = [
                row for row in rows if any(line.product_class.id == class_id for line in row.lines)
            ]
        if product_id is not None:
            rows = [row for row in rows if any(line.product.id == product_id for line in row.lines)]
        normalized_kind = _normalize_optional(product_kind)
        if normalized_kind and normalized_kind != "all":
            rows = [
                row
                for row in rows
                if any(line.product.product_kind == normalized_kind for line in row.lines)
            ]
        normalized_evidence = _normalize_optional(evidence_state)
        if normalized_evidence == "with_evidence":
            rows = [row for row in rows if self._has_evidence(row)]
        elif normalized_evidence == "without_evidence":
            rows = [row for row in rows if not self._has_evidence(row)]
        normalized_impact = _normalize_optional(impact_level)
        if normalized_impact and normalized_impact != "all":
            rows = [row for row in rows if self._impact_level(row) == normalized_impact]
        normalized_warning = _normalize_optional(warning_state)
        if normalized_warning and normalized_warning != "all":
            rows = [row for row in rows if self._warning_state(row, session) == normalized_warning]
        normalized_search = _normalize_optional(search)
        if normalized_search:
            rows = [row for row in rows if self._matches_search(row, normalized_search)]

        items = [self._to_list_item(session, row) for row in rows]
        total = len(items)
        safe_page = max(page, 1)
        safe_page_size = min(max(page_size, 1), 100)
        offset = (safe_page - 1) * safe_page_size

        return AdminWasteListResponse(
            filter_options=self._build_filter_options(session),
            items=items[offset : offset + safe_page_size],
            metrics=self._build_metrics(rows),
            page=safe_page,
            page_size=safe_page_size,
            total=total,
        )

    def get_waste_detail(self, session: Session, *, waste_id: uuid.UUID) -> AdminWasteDetailView:
        return self._to_detail(session, self._get_row(session, waste_id))

    def list_reasons(self, session: Session) -> list[AdminWasteReasonView]:
        return self._reason_views(
            session.execute(
                select(WasteReason)
                .where(WasteReason.is_active.is_(True))
                .order_by(WasteReason.display_order.asc(), WasteReason.name.asc()),
            )
            .scalars()
            .all(),
        )

    def create_waste(
        self,
        session: Session,
        *,
        command: AdminWasteCreateRequest,
        current_user: AuthenticatedUser,
        request_id: str | None,
    ) -> AdminWasteDetailView:
        branch = self._get_branch(session, command.branch_id)
        if not branch.is_active:
            raise WasteValidationError("Waste branch is inactive.")
        workstation = self._get_active_workstation_for_branch(session, branch.id)
        reason = self._get_reason(session, command.reason_code)
        resolved_product = self._resolve_product(session, command.product_id)
        location_code = command.location_code
        if location_code not in LOCATION_LABELS:
            raise WasteValidationError("Waste source location is not supported.")

        quantity = _q3(command.quantity)
        is_high_impact = self._is_high_impact(reason_code=reason.code, quantity=quantity)
        notes_required = reason.code in WASTE_REASON_CODES_REQUIRING_NOTE or is_high_impact
        if notes_required and not _has_text(command.notes):
            raise WasteValidationError("Notes are required for this waste reason or impact level.")

        balance = self._get_balance(
            session,
            branch_id=branch.id,
            location_code=location_code,
            product_id=resolved_product.product.id,
            for_update=True,
        )
        if balance is None or Decimal(balance.quantity_on_hand) < quantity:
            raise WasteValidationError(
                "Waste quantity exceeds available stock for selected branch and location."
            )

        previous_quantity = _q3(Decimal(balance.quantity_on_hand))
        new_quantity = _q3(previous_quantity - quantity)
        now = _utc_now()
        document = OperationDocument(
            committed_at_utc=now,
            created_by_user_id=current_user.id,
            destination_bucket_code=OPERATION_BUCKET_WASTE,
            document_type=OPERATION_DOCUMENT_TYPE_WASTE_RECORD,
            notes=command.notes,
            reason_code=reason.code,
            source_branch_id=branch.id,
            source_bucket_code=location_code,
            status=OPERATION_DOCUMENT_STATUS_COMMITTED,
            workstation_id=workstation.id,
        )

        try:
            session.add(document)
            session.flush()
            session.add(
                OperationDocumentLine(
                    operation_document_id=document.id,
                    line_number=1,
                    product_id=resolved_product.product.id,
                    product_code_snapshot=resolved_product.product.code,
                    product_name_snapshot=resolved_product.product.name,
                    product_class_id=resolved_product.product_class.id,
                    product_class_code_snapshot=resolved_product.product_class.code,
                    product_class_name_snapshot=resolved_product.product_class.name,
                    quantity=quantity,
                    unit_of_measure_code=resolved_product.product.unit_of_measure,
                ),
            )
            balance.quantity_on_hand = new_quantity
            movement = InventoryMovement(
                balance_after=new_quantity,
                branch_id=branch.id,
                direction=INVENTORY_MOVEMENT_DIRECTION_OUT,
                location_code=location_code,
                movement_type=INVENTORY_MOVEMENT_TYPE_WASTE_RECORD,
                notes=command.notes,
                operator_user_id=current_user.id,
                product_id=resolved_product.product.id,
                quantity=quantity,
                reason=reason.code,
                source_document_id=document.id,
                source_document_type=ADMIN_WASTE_SOURCE_DOCUMENT_TYPE,
                unit_of_measure=resolved_product.product.unit_of_measure,
            )
            session.add(movement)
            self._record_confirmed(
                session,
                branch=branch,
                current_user=current_user,
                document=document,
                high_impact=is_high_impact,
                location_code=location_code,
                movement=movement,
                quantity=quantity,
                reason=reason,
                request_id=request_id,
            )
            session.commit()
        except IntegrityError as error:
            session.rollback()
            raise WasteValidationError("Waste record could not be confirmed.") from error

        return self.get_waste_detail(session, waste_id=document.id)

    def _fetch_rows(
        self,
        session: Session,
        *,
        branch_id: uuid.UUID | None,
        date_from: datetime | None,
        date_to: datetime | None,
        location_code: str | None,
        operator_user_id: uuid.UUID | None,
        reason_code: str | None,
        status_filter: str | None,
    ) -> list[_WasteRow]:
        query = (
            select(OperationDocument, Branch, User, Workstation, WasteReason)
            .join(Branch, Branch.id == OperationDocument.source_branch_id)
            .join(User, User.id == OperationDocument.created_by_user_id)
            .join(Workstation, Workstation.id == OperationDocument.workstation_id)
            .join(WasteReason, WasteReason.code == OperationDocument.reason_code)
            .where(OperationDocument.document_type == OPERATION_DOCUMENT_TYPE_WASTE_RECORD)
            .order_by(OperationDocument.created_at_utc.desc())
        )
        if branch_id is not None:
            query = query.where(OperationDocument.source_branch_id == branch_id)
        if date_from is not None:
            query = query.where(OperationDocument.created_at_utc >= date_from)
        if date_to is not None:
            query = query.where(OperationDocument.created_at_utc <= date_to)
        normalized_location = _normalize_optional(location_code)
        if normalized_location and normalized_location != "all":
            query = query.where(OperationDocument.source_bucket_code == normalized_location)
        if operator_user_id is not None:
            query = query.where(OperationDocument.created_by_user_id == operator_user_id)
        normalized_reason = _normalize_optional(reason_code)
        if normalized_reason and normalized_reason != "all":
            query = query.where(OperationDocument.reason_code == normalized_reason)
        normalized_status = _normalize_optional(status_filter)
        if normalized_status and normalized_status != "all":
            query = query.where(OperationDocument.status == normalized_status)

        document_rows = session.execute(query).all()
        documents = [document for document, _, _, _, _ in document_rows]
        lines_by_document = self._lines_by_document(
            session, [document.id for document in documents]
        )
        return [
            _WasteRow(
                branch=branch,
                created_by_user=user,
                document=document,
                lines=lines_by_document.get(document.id, []),
                reason=reason,
                workstation=workstation,
            )
            for document, branch, user, workstation, reason in document_rows
        ]

    def _get_row(self, session: Session, waste_id: uuid.UUID) -> _WasteRow:
        result = session.execute(
            select(OperationDocument, Branch, User, Workstation, WasteReason)
            .join(Branch, Branch.id == OperationDocument.source_branch_id)
            .join(User, User.id == OperationDocument.created_by_user_id)
            .join(Workstation, Workstation.id == OperationDocument.workstation_id)
            .join(WasteReason, WasteReason.code == OperationDocument.reason_code)
            .where(
                OperationDocument.id == waste_id,
                OperationDocument.document_type == OPERATION_DOCUMENT_TYPE_WASTE_RECORD,
            ),
        ).one_or_none()
        if result is None:
            raise WasteNotFoundError("Waste record was not found.")
        document, branch, user, workstation, reason = result
        lines = self._lines_by_document(session, [document.id]).get(document.id, [])
        if not lines:
            raise WasteValidationError("Waste record has no product lines.")
        return _WasteRow(
            branch=branch,
            created_by_user=user,
            document=document,
            lines=lines,
            reason=reason,
            workstation=workstation,
        )

    def _lines_by_document(
        self,
        session: Session,
        document_ids: list[uuid.UUID],
    ) -> dict[uuid.UUID, list[_WasteLine]]:
        if not document_ids:
            return {}
        rows = session.execute(
            select(OperationDocumentLine, Product, ProductClass)
            .join(Product, Product.id == OperationDocumentLine.product_id)
            .join(ProductClass, ProductClass.id == Product.product_class_id)
            .where(OperationDocumentLine.operation_document_id.in_(document_ids))
            .order_by(
                OperationDocumentLine.operation_document_id.asc(),
                OperationDocumentLine.line_number.asc(),
            ),
        ).all()
        grouped: dict[uuid.UUID, list[_WasteLine]] = {}
        for line, product, product_class in rows:
            grouped.setdefault(line.operation_document_id, []).append(
                _WasteLine(line=line, product=product, product_class=product_class),
            )
        return grouped

    def _to_list_item(self, session: Session, row: _WasteRow) -> AdminWasteListItemView:
        primary = row.lines[0]
        quantity = self._total_quantity(row)
        warnings = self._build_warnings(row, session)
        return AdminWasteListItemView(
            branch_id=row.branch.id,
            branch_name=row.branch.name,
            created_at=row.document.created_at_utc,
            estimated_value=self._estimated_value(row),
            folio=_build_folio(row.document.id),
            has_evidence=self._has_evidence(row),
            id=row.document.id,
            impact_level=_ADMIN_WASTE_IMPACT_LEVEL_ADAPTER.validate_python(self._impact_level(row)),
            line_count=len(row.lines),
            location_code=_ADMIN_WASTE_LOCATION_CODE_ADAPTER.validate_python(
                row.document.source_bucket_code or INVENTORY_LOCATION_BACKROOM
            ),
            location_name=self._location_name(row.document.source_bucket_code),
            operator_name=row.created_by_user.full_name,
            product_code=primary.product.code,
            product_id=primary.product.id,
            product_kind=_ADMIN_WASTE_PRODUCT_KIND_ADAPTER.validate_python(
                primary.product.product_kind
            ),
            product_name=primary.product.name
            if len(row.lines) == 1
            else f"{primary.product.name} +{len(row.lines) - 1}",
            quantity=quantity,
            reason_code=row.reason.code,
            reason_label=row.reason.name,
            status=_ADMIN_WASTE_STATUS_ADAPTER.validate_python(row.document.status),
            uom=primary.product.unit_of_measure if len(row.lines) == 1 else "mixed",
            warning_state=self._warning_state_from_warnings(warnings),
            warnings=warnings,
        )

    def _to_detail(self, session: Session, row: _WasteRow) -> AdminWasteDetailView:
        primary = row.lines[0]
        warnings = self._build_warnings(row, session)
        movements = self._inventory_movements(session, row.document.id)
        primary_movement = next(
            (movement for movement in movements if movement.product_id == primary.product.id), None
        )
        stock_after = primary_movement.balance_after if primary_movement else None
        stock_before = (
            _q3(Decimal(stock_after) + Decimal(primary.line.quantity))
            if stock_after is not None
            else None
        )
        current_balance = self._get_balance(
            session,
            branch_id=row.branch.id,
            location_code=row.document.source_bucket_code or INVENTORY_LOCATION_BACKROOM,
            product_id=primary.product.id,
            for_update=False,
        )
        return AdminWasteDetailView(
            available_actions=restrict_actions(
                session,
                AdminWasteAvailableActionsView(),
                {
                    "can_create_correction": "returns_corrections.manage",
                    "can_open_inventory_movement": "inventory.view",
                },
                branch_ids=(row.branch.id,),
                global_only=False,
            ),
            evidence=AdminWasteEvidenceView(notes=row.document.notes),
            inventory_impact=AdminWasteInventoryImpactView(
                integration_available=True,
                movements=[self._to_movement_view(movement) for movement in movements],
                notes=None
                if movements
                else "No hay movimiento de inventario vinculado a este documento.",
            ),
            lines=[
                AdminWasteLineView(
                    estimated_value=self._line_estimated_value(line),
                    line_number=line.line.line_number,
                    product_code=line.product.code,
                    product_id=line.product.id,
                    product_kind=_ADMIN_WASTE_PRODUCT_KIND_ADAPTER.validate_python(
                        line.product.product_kind
                    ),
                    product_name=line.product.name,
                    quantity=line.line.quantity,
                    uom=line.line.unit_of_measure_code,
                )
                for line in row.lines
            ],
            overview=AdminWasteOverviewView(
                branch_id=row.branch.id,
                branch_name=row.branch.name,
                confirmed_at=row.document.committed_at_utc,
                created_at=row.document.created_at_utc,
                folio=_build_folio(row.document.id),
                has_evidence=self._has_evidence(row),
                id=row.document.id,
                impact_level=_ADMIN_WASTE_IMPACT_LEVEL_ADAPTER.validate_python(
                    self._impact_level(row)
                ),
                location_code=_ADMIN_WASTE_LOCATION_CODE_ADAPTER.validate_python(
                    row.document.source_bucket_code or INVENTORY_LOCATION_BACKROOM
                ),
                location_name=self._location_name(row.document.source_bucket_code),
                notes=row.document.notes,
                operator_id=row.created_by_user.id,
                operator_name=row.created_by_user.full_name,
                quantity=self._total_quantity(row),
                reason_code=row.reason.code,
                reason_label=row.reason.name,
                status=_ADMIN_WASTE_STATUS_ADAPTER.validate_python(row.document.status),
                uom=primary.line.unit_of_measure_code if len(row.lines) == 1 else "mixed",
                warning_state=self._warning_state_from_warnings(warnings),
                workstation_code=row.workstation.code,
                workstation_name=row.workstation.name,
            ),
            product_inventory_context=AdminWasteProductInventoryContextView(
                branch_id=row.branch.id,
                branch_name=row.branch.name,
                class_id=primary.product_class.id,
                class_name=primary.product_class.name,
                current_stock=current_balance.quantity_on_hand if current_balance else None,
                product_code=primary.product.code,
                product_id=primary.product.id,
                product_is_active=primary.product.is_active,
                product_kind=_ADMIN_WASTE_PRODUCT_KIND_ADAPTER.validate_python(
                    primary.product.product_kind
                ),
                product_name=primary.product.name,
                stock_after=stock_after,
                stock_before=stock_before,
                uom=primary.product.unit_of_measure,
            ),
            reason_classification=AdminWasteReasonClassificationView(
                category=row.reason.code,
                description=REASON_DESCRIPTIONS.get(row.reason.code),
                label=row.reason.name,
                requires_evidence=False,
                requires_note=row.reason.code in WASTE_REASON_CODES_REQUIRING_NOTE,
            ),
            related_documents=self._related_documents(row, movements),
            warnings=warnings,
        )

    def _build_filter_options(self, session: Session) -> AdminWasteFilterOptionsView:
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
        operators = (
            session.execute(
                select(User)
                .join(OperationDocument, OperationDocument.created_by_user_id == User.id)
                .where(OperationDocument.document_type == OPERATION_DOCUMENT_TYPE_WASTE_RECORD)
                .order_by(User.full_name.asc()),
            )
            .scalars()
            .unique()
            .all()
        )
        reasons = (
            session.execute(
                select(WasteReason)
                .where(WasteReason.is_active.is_(True))
                .order_by(WasteReason.display_order.asc(), WasteReason.name.asc()),
            )
            .scalars()
            .all()
        )
        return AdminWasteFilterOptionsView(
            branches=[
                AdminWasteFilterOptionView(
                    id=str(branch.id), label=f"{branch.name} - {branch.code}"
                )
                for branch in branches
            ],
            classes=[
                AdminWasteFilterOptionView(id=str(product_class.id), label=product_class.name)
                for product_class in classes
            ],
            evidence_states=[
                AdminWasteFilterOptionView(id="with_evidence", label="Con evidencia"),
                AdminWasteFilterOptionView(id="without_evidence", label="Sin evidencia"),
            ],
            impact_levels=[
                AdminWasteFilterOptionView(id=ADMIN_WASTE_IMPACT_LEVEL_NORMAL, label="Normal"),
                AdminWasteFilterOptionView(id=ADMIN_WASTE_IMPACT_LEVEL_HIGH, label="Alto impacto"),
            ],
            locations=[
                AdminWasteFilterOptionView(id=code, label=label)
                for code, label in LOCATION_LABELS.items()
            ],
            operators=[
                AdminWasteFilterOptionView(id=str(user.id), label=user.full_name)
                for user in operators
            ],
            product_kinds=[
                AdminWasteFilterOptionView(id=code, label=label)
                for code, label in PRODUCT_KIND_LABELS.items()
            ],
            products=[
                AdminWasteFilterOptionView(
                    id=str(product.id), label=f"{product.name} - {product.code}"
                )
                for product in products
            ],
            reasons=self._reason_views(reasons),
            statuses=[
                AdminWasteFilterOptionView(
                    id=OPERATION_DOCUMENT_STATUS_COMMITTED, label="Confirmada"
                ),
                AdminWasteFilterOptionView(
                    id=OPERATION_DOCUMENT_STATUS_CANCELLED, label="Cancelada"
                ),
            ],
        )

    def _build_metrics(self, rows: list[_WasteRow]) -> AdminWasteMetricsView:
        estimated_values = [self._estimated_value(row) for row in rows]
        return AdminWasteMetricsView(
            contaminated_or_damaged=sum(
                1
                for row in rows
                if row.reason.code in {WASTE_REASON_CONTAMINATED, WASTE_REASON_DAMAGED}
            ),
            evidence_records=sum(1 for row in rows if self._has_evidence(row)),
            estimated_value=sum((value or ZERO for value in estimated_values), ZERO),
            expired_records=sum(1 for row in rows if row.reason.code == WASTE_REASON_EXPIRED),
            high_impact_records=sum(
                1 for row in rows if self._impact_level(row) == ADMIN_WASTE_IMPACT_LEVEL_HIGH
            ),
            total_quantity=sum((self._total_quantity(row) for row in rows), ZERO),
            total_records=len(rows),
        )

    def _record_confirmed(
        self,
        session: Session,
        *,
        branch: Branch,
        current_user: AuthenticatedUser,
        document: OperationDocument,
        high_impact: bool,
        location_code: str,
        movement: InventoryMovement,
        quantity: Decimal,
        reason: WasteReason,
        request_id: str | None,
    ) -> None:
        metadata = {
            "branch_id": str(branch.id),
            "folio": _build_folio(document.id),
            "high_impact": high_impact,
            "inventory_movement_id": str(movement.id),
            "location_code": location_code,
            "quantity": str(quantity),
            "reason_code": reason.code,
            "status": document.status,
            "waste_id": str(document.id),
        }
        self._audit_recorder.record(
            session,
            actor_id=current_user.id,
            action=AUDIT_ACTION_ADMIN_WASTE_CONFIRMED,
            resource_type=ADMIN_WASTE_RESOURCE_TYPE,
            resource_id=str(document.id),
            branch_id=branch.id,
            request_id=request_id,
            metadata=metadata,
        )
        self._outbox_writer.append(
            session,
            aggregate_type=ADMIN_WASTE_RESOURCE_TYPE,
            aggregate_id=str(document.id),
            event_name=OUTBOX_EVENT_WASTE_RECORD_COMMITTED_V1,
            payload=metadata,
            headers={"request_id": request_id} if request_id else {},
        )
        if high_impact:
            alert_payload = {
                **metadata,
                "notification_target": "backoffice",
                "threshold_quantity": str(self._settings.waste_high_impact_quantity_threshold),
            }
            self._audit_recorder.record(
                session,
                actor_id=current_user.id,
                action=AUDIT_ACTION_ADMIN_WASTE_HIGH_IMPACT_NOTIFIED,
                resource_type=ADMIN_WASTE_RESOURCE_TYPE,
                resource_id=str(document.id),
                branch_id=branch.id,
                request_id=request_id,
                metadata=alert_payload,
            )
            self._outbox_writer.append(
                session,
                aggregate_type=ADMIN_WASTE_RESOURCE_TYPE,
                aggregate_id=str(document.id),
                event_name=OUTBOX_EVENT_WASTE_RECORD_HIGH_IMPACT_ALERT_V1,
                payload=alert_payload,
                headers={"request_id": request_id} if request_id else {},
            )

    def _build_warnings(self, row: _WasteRow, session: Session) -> list[AdminWasteWarningView]:
        warnings: list[AdminWasteWarningView] = []
        if not row.branch.is_active:
            warnings.append(
                AdminWasteWarningView(
                    code="inactive_branch", message="La sucursal esta inactiva.", severity="warning"
                )
            )
        if any(not line.product.is_active for line in row.lines):
            warnings.append(
                AdminWasteWarningView(
                    code="inactive_product",
                    message="La merma incluye producto inactivo.",
                    severity="warning",
                )
            )
        if self._impact_level(row) == ADMIN_WASTE_IMPACT_LEVEL_HIGH:
            warnings.append(
                AdminWasteWarningView(
                    code="high_impact",
                    message="Merma marcada como alto impacto.",
                    severity="warning",
                )
            )
        if not self._inventory_movements(session, row.document.id):
            warnings.append(
                AdminWasteWarningView(
                    code="missing_inventory_movement",
                    message="No hay movimiento de inventario vinculado.",
                    severity="critical",
                )
            )
        if self._estimated_value(row) is None:
            warnings.append(
                AdminWasteWarningView(
                    code="missing_standard_cost",
                    message="No hay costo estandar para estimar valor.",
                    severity="info",
                )
            )
        return warnings

    def _related_documents(
        self,
        row: _WasteRow,
        movements: list[InventoryMovement],
    ) -> list[AdminWasteRelatedDocumentView]:
        documents = [
            AdminWasteRelatedDocumentView(
                document_id=row.branch.id,
                document_type="BRANCH",
                folio=row.branch.code,
                status="active" if row.branch.is_active else "inactive",
            )
        ]
        documents.extend(
            AdminWasteRelatedDocumentView(
                document_id=movement.id,
                document_type="INVENTORY_MOVEMENT",
                folio=movement.movement_type,
                status=movement.direction,
            )
            for movement in movements
        )
        return documents

    def _inventory_movements(
        self, session: Session, waste_id: uuid.UUID
    ) -> list[InventoryMovement]:
        return list(
            session.execute(
                select(InventoryMovement)
                .where(
                    InventoryMovement.source_document_id == waste_id,
                    InventoryMovement.source_document_type == ADMIN_WASTE_SOURCE_DOCUMENT_TYPE,
                )
                .order_by(InventoryMovement.occurred_at.asc()),
            )
            .scalars()
            .all()
        )

    def _to_movement_view(self, movement: InventoryMovement) -> AdminWasteInventoryMovementView:
        return AdminWasteInventoryMovementView(
            balance_after=movement.balance_after,
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

    def _reason_views(self, reasons: Sequence[WasteReason]) -> list[AdminWasteReasonView]:
        return [
            AdminWasteReasonView(
                code=reason.code,
                display_order=reason.display_order,
                high_impact_default=reason.code == WASTE_REASON_CONTAMINATED,
                label=reason.name,
                requires_note=reason.code in WASTE_REASON_CODES_REQUIRING_NOTE,
            )
            for reason in reasons
        ]

    def _resolve_product(self, session: Session, product_id: uuid.UUID) -> _ResolvedProduct:
        result = session.execute(
            select(Product, ProductClass)
            .join(ProductClass, ProductClass.id == Product.product_class_id)
            .where(Product.id == product_id),
        ).one_or_none()
        if result is None:
            raise WasteNotFoundError("Product was not found.")
        product, product_class = result
        return _ResolvedProduct(product=product, product_class=product_class)

    def _get_branch(self, session: Session, branch_id: uuid.UUID) -> Branch:
        branch = session.get(Branch, branch_id)
        if branch is None:
            raise WasteNotFoundError("Branch was not found.")
        return branch

    def _get_active_workstation_for_branch(
        self, session: Session, branch_id: uuid.UUID
    ) -> Workstation:
        workstation = session.execute(
            select(Workstation)
            .where(Workstation.branch_id == branch_id, Workstation.is_active.is_(True))
            .order_by(Workstation.code.asc())
            .limit(1),
        ).scalar_one_or_none()
        if workstation is None:
            raise WasteValidationError(
                "Branch needs an active workstation before waste can be managed."
            )
        return workstation

    def _get_reason(self, session: Session, reason_code: str) -> WasteReason:
        reason = session.execute(
            select(WasteReason).where(
                WasteReason.code == reason_code, WasteReason.is_active.is_(True)
            ),
        ).scalar_one_or_none()
        if reason is None:
            raise WasteNotFoundError("Waste reason was not found.")
        return reason

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

    def _matches_search(self, row: _WasteRow, search: str) -> bool:
        normalized = search.lower()
        haystack = [
            _build_folio(row.document.id),
            row.branch.code,
            row.branch.name,
            row.created_by_user.full_name,
            row.reason.code,
            row.reason.name,
            *(line.product.code for line in row.lines),
            *(line.product.name for line in row.lines),
            *(line.product_class.name for line in row.lines),
        ]
        return any(normalized in str(value).lower() for value in haystack if value)

    def _total_quantity(self, row: _WasteRow) -> Decimal:
        return sum((Decimal(line.line.quantity) for line in row.lines), ZERO)

    def _estimated_value(self, row: _WasteRow) -> Decimal | None:
        values: list[Decimal] = []
        for line in row.lines:
            line_value = self._line_estimated_value(line)
            if line_value is None:
                return None
            values.append(line_value)
        return sum(values, ZERO)

    def _line_estimated_value(self, line: _WasteLine) -> Decimal | None:
        if line.product.standard_cost is None:
            return None
        return Decimal(line.line.quantity) * Decimal(line.product.standard_cost)

    def _impact_level(self, row: _WasteRow) -> str:
        if self._is_high_impact(reason_code=row.reason.code, quantity=self._total_quantity(row)):
            return ADMIN_WASTE_IMPACT_LEVEL_HIGH
        return ADMIN_WASTE_IMPACT_LEVEL_NORMAL

    def _has_evidence(self, row: _WasteRow) -> bool:
        _ = row
        return False

    def _is_high_impact(self, *, reason_code: str, quantity: Decimal) -> bool:
        return (
            quantity > self._settings.waste_high_impact_quantity_threshold
            or reason_code == WASTE_REASON_CONTAMINATED
        )

    def _warning_state(self, row: _WasteRow, session: Session) -> str | None:
        return self._warning_state_from_warnings(self._build_warnings(row, session))

    def _warning_state_from_warnings(
        self,
        warnings: list[AdminWasteWarningView],
    ) -> AdminWasteWarningSeverity | None:
        if any(warning.severity == "critical" for warning in warnings):
            return "critical"
        if any(warning.severity == "warning" for warning in warnings):
            return "warning"
        if warnings:
            return "info"
        return None

    def _location_name(self, location_code: str | None) -> str:
        return LOCATION_LABELS.get(
            location_code or INVENTORY_LOCATION_BACKROOM, location_code or "BACKROOM"
        )


def _normalize_optional(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def _has_text(value: str | None) -> bool:
    return value is not None and value.strip() != ""


def _q3(value: Decimal) -> Decimal:
    return Decimal(value).quantize(DECIMAL_3, rounding=ROUND_HALF_UP)


def _utc_now() -> datetime:
    return datetime.now(tz=UTC)


def _build_folio(waste_id: uuid.UUID) -> str:
    return f"WST-{str(waste_id)[:8].upper()}"
