from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from zeromerma_api.modules.audit.application.service import AuditRecorder
from zeromerma_api.modules.branches.infrastructure.models import Branch
from zeromerma_api.modules.catalog.domain.constants import (
    CATALOG_PRODUCT_KIND_CONSUMABLE,
    CATALOG_PRODUCT_KIND_DISPOSABLE,
    CATALOG_PRODUCT_KIND_FINISHED_GOOD,
    CATALOG_PRODUCT_KIND_RAW_MATERIAL,
)
from zeromerma_api.modules.catalog.infrastructure.models import Product
from zeromerma_api.modules.identity.application.schemas import AuthenticatedUser
from zeromerma_api.modules.identity.infrastructure.models import User
from zeromerma_api.modules.inventory.domain.constants import (
    INVENTORY_LOCATION_BACKROOM,
    INVENTORY_MOVEMENT_DIRECTION_IN,
    INVENTORY_MOVEMENT_TYPE_PURCHASE_RECEIPT,
)
from zeromerma_api.modules.inventory.infrastructure.models import (
    InventoryBalance,
    InventoryMovement,
)
from zeromerma_api.modules.outbox.application.service import OutboxWriter
from zeromerma_api.modules.purchases.application.admin_schemas import (
    AdminPurchaseAvailableActionsView,
    AdminPurchaseBranchView,
    AdminPurchaseCancelRequest,
    AdminPurchaseCostSummaryView,
    AdminPurchaseCreateRequest,
    AdminPurchaseDetailView,
    AdminPurchaseDirectEntryLineInput,
    AdminPurchaseDirectEntryRequest,
    AdminPurchaseFilterOptionsView,
    AdminPurchaseFilterOptionView,
    AdminPurchaseInventoryImpactView,
    AdminPurchaseInventoryMovementView,
    AdminPurchaseLineInput,
    AdminPurchaseLineView,
    AdminPurchaseListItemView,
    AdminPurchaseListResponse,
    AdminPurchaseMetricsView,
    AdminPurchaseOverviewView,
    AdminPurchaseReceiptLineInput,
    AdminPurchaseReceiptSummaryView,
    AdminPurchaseReceiveRequest,
    AdminPurchaseRelatedDocumentView,
    AdminPurchaseSupplierContextView,
    AdminPurchaseUpdateRequest,
    AdminPurchaseWarningSeverity,
    AdminPurchaseWarningView,
)
from zeromerma_api.modules.purchases.domain.constants import (
    AUDIT_ACTION_ADMIN_PURCHASE_CANCELLED,
    AUDIT_ACTION_ADMIN_PURCHASE_CONFIRMED,
    AUDIT_ACTION_ADMIN_PURCHASE_CREATED,
    AUDIT_ACTION_ADMIN_PURCHASE_RECEIVED,
    AUDIT_ACTION_ADMIN_PURCHASE_UPDATED,
    OUTBOX_EVENT_ADMIN_PURCHASE_CANCELLED_V1,
    OUTBOX_EVENT_ADMIN_PURCHASE_CONFIRMED_V1,
    OUTBOX_EVENT_ADMIN_PURCHASE_CREATED_V1,
    OUTBOX_EVENT_ADMIN_PURCHASE_RECEIVED_V1,
    PURCHASE_DOCUMENT_TYPE_DIRECT_ENTRY,
    PURCHASE_DOCUMENT_TYPE_PURCHASE,
    PURCHASE_RECEIPT_RESOURCE_TYPE,
    PURCHASE_RECEIPT_SOURCE_DOCUMENT_TYPE,
    PURCHASE_RESOURCE_TYPE,
    PURCHASE_STATUS_CANCELLED,
    PURCHASE_STATUS_DRAFT,
    PURCHASE_STATUS_ORDERED,
    PURCHASE_STATUS_PARTIALLY_RECEIVED,
    PURCHASE_STATUS_RECEIVED,
    VALID_PURCHASE_EXTERNAL_DOCUMENT_TYPES,
)
from zeromerma_api.modules.purchases.domain.exceptions import (
    PurchaseNotFoundError,
    PurchaseValidationError,
)
from zeromerma_api.modules.purchases.infrastructure.models import (
    PurchaseDocument,
    PurchaseDocumentLine,
    PurchaseReceipt,
    PurchaseReceiptLine,
)
from zeromerma_api.modules.suppliers.domain.constants import (
    SUPPLIER_PAYMENT_TERMS_CREDIT,
    SUPPLIER_STATUS_ACTIVE,
)
from zeromerma_api.modules.suppliers.infrastructure.models import (
    Supplier,
    SupplierContact,
    SupplierProduct,
)

ZERO = Decimal("0")

PRODUCT_KIND_LABELS = {
    CATALOG_PRODUCT_KIND_FINISHED_GOOD: "Producto terminado",
    CATALOG_PRODUCT_KIND_RAW_MATERIAL: "Materia prima",
    CATALOG_PRODUCT_KIND_CONSUMABLE: "Consumible",
    CATALOG_PRODUCT_KIND_DISPOSABLE: "Desechable",
}


@dataclass(frozen=True)
class _PurchaseRow:
    branch: Branch
    created_by_user: User
    document: PurchaseDocument
    lines: list[PurchaseDocumentLine]
    receipts: list[PurchaseReceipt]
    supplier: Supplier


class AdminPurchaseService:
    def __init__(
        self,
        audit_recorder: AuditRecorder | None = None,
        outbox_writer: OutboxWriter | None = None,
    ) -> None:
        self._audit_recorder = audit_recorder or AuditRecorder()
        self._outbox_writer = outbox_writer or OutboxWriter()

    def list_purchases(
        self,
        session: Session,
        *,
        amount_max: Decimal | None,
        amount_min: Decimal | None,
        branch_id: uuid.UUID | None,
        date_from: datetime | None,
        date_to: datetime | None,
        discrepancy_state: str | None,
        operator_user_id: uuid.UUID | None,
        product_id: uuid.UUID | None,
        product_kind: str | None,
        search: str | None,
        status_filter: str | None,
        supplier_id: uuid.UUID | None,
        warning_state: str | None,
        page: int,
        page_size: int,
    ) -> AdminPurchaseListResponse:
        rows = self._fetch_rows(
            session,
            branch_id=branch_id,
            date_from=date_from,
            date_to=date_to,
            operator_user_id=operator_user_id,
            status_filter=status_filter,
            supplier_id=supplier_id,
        )

        if product_id is not None:
            rows = [row for row in rows if any(line.product_id == product_id for line in row.lines)]

        normalized_product_kind = _normalize_optional(product_kind)
        if normalized_product_kind and normalized_product_kind != "all":
            product_ids = {line.product_id for row in rows for line in row.lines}
            products = self._products_by_id(session, product_ids)
            rows = [
                row
                for row in rows
                if any(
                    products[line.product_id].product_kind == normalized_product_kind
                    for line in row.lines
                )
            ]

        normalized_discrepancy = _normalize_optional(discrepancy_state)
        if normalized_discrepancy == "with_discrepancy":
            rows = [row for row in rows if self._has_discrepancy(session, row)]
        elif normalized_discrepancy == "without_discrepancy":
            rows = [row for row in rows if not self._has_discrepancy(session, row)]

        normalized_search = _normalize_optional(search)
        if normalized_search:
            rows = [row for row in rows if self._matches_search(row, normalized_search)]

        if amount_min is not None:
            rows = [row for row in rows if self._document_total(row.lines) >= amount_min]
        if amount_max is not None:
            rows = [row for row in rows if self._document_total(row.lines) <= amount_max]

        normalized_warning_state = _normalize_optional(warning_state)
        if normalized_warning_state == "with_warnings":
            rows = [
                row
                for row in rows
                if self._warning_state(self._build_warnings(session, row)) is not None
            ]
        elif normalized_warning_state == "without_warnings":
            rows = [
                row
                for row in rows
                if self._warning_state(self._build_warnings(session, row)) is None
            ]
        elif normalized_warning_state in {"info", "warning", "critical"}:
            rows = [
                row
                for row in rows
                if self._warning_state(self._build_warnings(session, row))
                == normalized_warning_state
            ]

        items = [self._to_list_item(session, row) for row in rows]
        total = len(items)
        safe_page = max(page, 1)
        safe_page_size = min(max(page_size, 1), 100)
        offset = (safe_page - 1) * safe_page_size

        return AdminPurchaseListResponse(
            filter_options=self._build_filter_options(session),
            items=items[offset : offset + safe_page_size],
            metrics=self._build_metrics(session, rows),
            page=safe_page,
            page_size=safe_page_size,
            total=total,
        )

    def get_purchase_detail(
        self, session: Session, *, purchase_id: uuid.UUID
    ) -> AdminPurchaseDetailView:
        return self._to_detail(session, self._get_row(session, purchase_id))

    def create_purchase(
        self,
        session: Session,
        *,
        command: AdminPurchaseCreateRequest,
        current_user: AuthenticatedUser,
        request_id: str | None,
    ) -> AdminPurchaseDetailView:
        supplier = self._get_supplier(session, command.supplier_id)
        branch = self._get_branch(session, command.branch_id)
        self._validate_supplier_and_branch(supplier, branch)
        self._validate_external_document_type(command.external_document_type)
        products = self._resolve_line_products(session, command.lines)
        now = datetime.now(tz=UTC)
        document = PurchaseDocument(
            confirmed_at=now if command.confirm_now else None,
            confirmed_by_user_id=current_user.id if command.confirm_now else None,
            created_by_user_id=current_user.id,
            document_date=command.document_date or now,
            document_type=PURCHASE_DOCUMENT_TYPE_PURCHASE,
            external_document_date=command.external_document_date,
            external_document_number=command.external_document_number,
            external_document_type=command.external_document_type.upper()
            if command.external_document_type
            else None,
            folio=self._generate_folio(session, PURCHASE_DOCUMENT_TYPE_PURCHASE),
            notes=command.notes,
            receiving_branch_id=branch.id,
            status=PURCHASE_STATUS_ORDERED if command.confirm_now else PURCHASE_STATUS_DRAFT,
            supplier_id=supplier.id,
        )
        try:
            session.add(document)
            session.flush()
            self._replace_lines(session, document=document, lines=command.lines, products=products)
            self._record_change(
                session,
                action=AUDIT_ACTION_ADMIN_PURCHASE_CONFIRMED
                if command.confirm_now
                else AUDIT_ACTION_ADMIN_PURCHASE_CREATED,
                branch_id=branch.id,
                current_user=current_user,
                document=document,
                event_name=OUTBOX_EVENT_ADMIN_PURCHASE_CONFIRMED_V1
                if command.confirm_now
                else OUTBOX_EVENT_ADMIN_PURCHASE_CREATED_V1,
                request_id=request_id,
            )
            session.commit()
        except IntegrityError as error:
            session.rollback()
            raise PurchaseValidationError("Purchase could not be created.") from error

        return self.get_purchase_detail(session, purchase_id=document.id)

    def update_purchase(
        self,
        session: Session,
        *,
        command: AdminPurchaseUpdateRequest,
        current_user: AuthenticatedUser,
        purchase_id: uuid.UUID,
        request_id: str | None,
    ) -> AdminPurchaseDetailView:
        document = self._get_document(session, purchase_id)
        if document.status != PURCHASE_STATUS_DRAFT:
            raise PurchaseValidationError("Only draft purchases can be edited.")

        supplier = self._get_supplier(session, command.supplier_id or document.supplier_id)
        branch = self._get_branch(session, command.branch_id or document.receiving_branch_id)
        self._validate_supplier_and_branch(supplier, branch)
        self._validate_external_document_type(command.external_document_type)

        document.supplier_id = supplier.id
        document.receiving_branch_id = branch.id
        if command.document_date is not None:
            document.document_date = command.document_date
        if "external_document_date" in command.model_fields_set:
            document.external_document_date = command.external_document_date
        if "external_document_number" in command.model_fields_set:
            document.external_document_number = command.external_document_number
        if "external_document_type" in command.model_fields_set:
            document.external_document_type = (
                command.external_document_type.upper() if command.external_document_type else None
            )
        if "notes" in command.model_fields_set:
            document.notes = command.notes

        try:
            if command.lines is not None:
                products = self._resolve_line_products(session, command.lines)
                self._replace_lines(
                    session, document=document, lines=command.lines, products=products
                )
            self._record_change(
                session,
                action=AUDIT_ACTION_ADMIN_PURCHASE_UPDATED,
                branch_id=branch.id,
                current_user=current_user,
                document=document,
                event_name=OUTBOX_EVENT_ADMIN_PURCHASE_CREATED_V1,
                request_id=request_id,
            )
            session.commit()
        except IntegrityError as error:
            session.rollback()
            raise PurchaseValidationError("Purchase could not be updated.") from error

        return self.get_purchase_detail(session, purchase_id=document.id)

    def confirm_purchase(
        self,
        session: Session,
        *,
        current_user: AuthenticatedUser,
        purchase_id: uuid.UUID,
        request_id: str | None,
    ) -> AdminPurchaseDetailView:
        document = self._get_document(session, purchase_id)
        if document.status != PURCHASE_STATUS_DRAFT:
            raise PurchaseValidationError("Only draft purchases can be confirmed.")
        lines = self._get_lines(session, document.id)
        if not lines:
            raise PurchaseValidationError("Purchase must contain at least one line.")
        supplier = self._get_supplier(session, document.supplier_id)
        branch = self._get_branch(session, document.receiving_branch_id)
        self._validate_supplier_and_branch(supplier, branch)
        document.status = PURCHASE_STATUS_ORDERED
        document.confirmed_at = datetime.now(tz=UTC)
        document.confirmed_by_user_id = current_user.id
        self._record_change(
            session,
            action=AUDIT_ACTION_ADMIN_PURCHASE_CONFIRMED,
            branch_id=branch.id,
            current_user=current_user,
            document=document,
            event_name=OUTBOX_EVENT_ADMIN_PURCHASE_CONFIRMED_V1,
            request_id=request_id,
        )
        session.commit()
        return self.get_purchase_detail(session, purchase_id=document.id)

    def create_direct_entry(
        self,
        session: Session,
        *,
        command: AdminPurchaseDirectEntryRequest,
        current_user: AuthenticatedUser,
        request_id: str | None,
    ) -> AdminPurchaseDetailView:
        supplier = self._get_supplier(session, command.supplier_id)
        branch = self._get_branch(session, command.branch_id)
        self._validate_supplier_and_branch(supplier, branch)
        self._validate_external_document_type(command.external_document_type)
        products = self._resolve_direct_entry_products(session, command.lines)
        now = datetime.now(tz=UTC)
        document = PurchaseDocument(
            confirmed_at=now,
            confirmed_by_user_id=current_user.id,
            created_by_user_id=current_user.id,
            document_date=command.document_date or now,
            document_type=PURCHASE_DOCUMENT_TYPE_DIRECT_ENTRY,
            external_document_date=command.external_document_date,
            external_document_number=command.external_document_number,
            external_document_type=command.external_document_type.upper()
            if command.external_document_type
            else None,
            folio=self._generate_folio(session, PURCHASE_DOCUMENT_TYPE_DIRECT_ENTRY),
            notes=command.notes,
            receiving_branch_id=branch.id,
            status=PURCHASE_STATUS_ORDERED,
            supplier_id=supplier.id,
        )
        purchase_lines = [
            AdminPurchaseLineInput(
                notes=line.notes,
                ordered_quantity=line.received_quantity,
                product_id=line.product_id,
                unit_cost=line.unit_cost,
            )
            for line in command.lines
        ]
        receipt_lines: list[AdminPurchaseReceiptLineInput] = []
        try:
            session.add(document)
            session.flush()
            self._replace_lines(session, document=document, lines=purchase_lines, products=products)
            stored_lines = self._get_lines(session, document.id)
            for stored_line, command_line in zip(stored_lines, command.lines, strict=True):
                receipt_lines.append(
                    AdminPurchaseReceiptLineInput(
                        notes=command_line.notes,
                        purchase_line_id=stored_line.id,
                        received_quantity=command_line.received_quantity,
                        unit_cost=command_line.unit_cost,
                    )
                )
            self._receive_document(
                session,
                command=AdminPurchaseReceiveRequest(lines=receipt_lines, notes=command.notes),
                current_user=current_user,
                document=document,
                request_id=request_id,
            )
            self._record_change(
                session,
                action=AUDIT_ACTION_ADMIN_PURCHASE_CREATED,
                branch_id=branch.id,
                current_user=current_user,
                document=document,
                event_name=OUTBOX_EVENT_ADMIN_PURCHASE_CREATED_V1,
                request_id=request_id,
            )
            session.commit()
        except IntegrityError as error:
            session.rollback()
            raise PurchaseValidationError("Direct entry could not be created.") from error

        return self.get_purchase_detail(session, purchase_id=document.id)

    def receive_purchase(
        self,
        session: Session,
        *,
        command: AdminPurchaseReceiveRequest,
        current_user: AuthenticatedUser,
        purchase_id: uuid.UUID,
        request_id: str | None,
    ) -> AdminPurchaseDetailView:
        document = self._get_document(session, purchase_id)
        self._receive_document(
            session,
            command=command,
            current_user=current_user,
            document=document,
            request_id=request_id,
        )
        session.commit()
        return self.get_purchase_detail(session, purchase_id=document.id)

    def cancel_purchase(
        self,
        session: Session,
        *,
        command: AdminPurchaseCancelRequest,
        current_user: AuthenticatedUser,
        purchase_id: uuid.UUID,
        request_id: str | None,
    ) -> AdminPurchaseDetailView:
        document = self._get_document(session, purchase_id)
        if document.status not in {PURCHASE_STATUS_DRAFT, PURCHASE_STATUS_ORDERED}:
            raise PurchaseValidationError(
                "Only draft or ordered purchases without receipts can be cancelled."
            )
        if self._get_receipts(session, document.id):
            raise PurchaseValidationError(
                "Purchases with receipts cannot be cancelled destructively."
            )
        document.status = PURCHASE_STATUS_CANCELLED
        document.cancelled_at = datetime.now(tz=UTC)
        document.cancelled_by_user_id = current_user.id
        if command.reason:
            document.notes = (
                f"{document.notes}\nCancelacion: {command.reason}"
                if document.notes
                else command.reason
            )
        self._record_change(
            session,
            action=AUDIT_ACTION_ADMIN_PURCHASE_CANCELLED,
            branch_id=document.receiving_branch_id,
            current_user=current_user,
            document=document,
            event_name=OUTBOX_EVENT_ADMIN_PURCHASE_CANCELLED_V1,
            request_id=request_id,
        )
        session.commit()
        return self.get_purchase_detail(session, purchase_id=document.id)

    def _receive_document(
        self,
        session: Session,
        *,
        command: AdminPurchaseReceiveRequest,
        current_user: AuthenticatedUser,
        document: PurchaseDocument,
        request_id: str | None,
    ) -> None:
        if document.status == PURCHASE_STATUS_CANCELLED:
            raise PurchaseValidationError("Cancelled purchases cannot be received.")
        if document.status == PURCHASE_STATUS_RECEIVED:
            raise PurchaseValidationError("Purchase is already fully received.")
        if document.status not in {
            PURCHASE_STATUS_DRAFT,
            PURCHASE_STATUS_ORDERED,
            PURCHASE_STATUS_PARTIALLY_RECEIVED,
        }:
            raise PurchaseValidationError("Purchase status does not allow receipt.")

        supplier = self._get_supplier(session, document.supplier_id)
        branch = self._get_branch(session, document.receiving_branch_id)
        self._validate_supplier_and_branch(supplier, branch)
        lines = self._get_lines(session, document.id, for_update=True)
        if not lines:
            raise PurchaseValidationError("Purchase must contain at least one line.")
        lines_by_id = {line.id: line for line in lines}
        receipt_line_ids = {line.purchase_line_id for line in command.lines}
        if not receipt_line_ids.issubset(lines_by_id):
            raise PurchaseValidationError("Receipt lines must belong to the selected purchase.")

        received_any = any(line.received_quantity > ZERO for line in command.lines)
        if not received_any:
            raise PurchaseValidationError("Receipt must include at least one received quantity.")

        receipt = PurchaseReceipt(
            folio=self._generate_receipt_folio(session),
            purchase_document_id=document.id,
            received_by_user_id=current_user.id,
            notes=command.notes,
        )
        session.add(receipt)
        session.flush()

        products = self._products_by_id(session, {line.product_id for line in lines})
        has_discrepancy = False
        for command_line in command.lines:
            purchase_line = lines_by_id[command_line.purchase_line_id]
            pending_quantity = Decimal(purchase_line.ordered_quantity) - Decimal(
                purchase_line.received_quantity
            )
            if pending_quantity <= ZERO:
                raise PurchaseValidationError(
                    "Receipt includes a line that is already fully received."
                )
            if command_line.received_quantity > pending_quantity:
                raise PurchaseValidationError("Received quantity cannot exceed pending quantity.")
            if (
                command_line.received_quantity != pending_quantity
                and not command_line.discrepancy_reason
            ):
                raise PurchaseValidationError(
                    "Discrepancy reason is required when received quantity differs "
                    "from pending quantity."
                )
            if command_line.received_quantity != pending_quantity:
                has_discrepancy = True
            unit_cost = (
                command_line.unit_cost
                if command_line.unit_cost is not None
                else purchase_line.unit_cost
            )
            receipt_line = PurchaseReceiptLine(
                discrepancy_reason=command_line.discrepancy_reason,
                line_number=purchase_line.line_number,
                notes=command_line.notes,
                product_id=purchase_line.product_id,
                purchase_line_id=purchase_line.id,
                purchase_receipt_id=receipt.id,
                received_quantity=command_line.received_quantity,
                unit_cost=unit_cost,
            )
            session.add(receipt_line)
            purchase_line.received_quantity = (
                Decimal(purchase_line.received_quantity) + command_line.received_quantity
            )
            purchase_line.unit_cost = unit_cost
            product = products[purchase_line.product_id]
            if command_line.received_quantity > ZERO:
                self._apply_receipt_inventory(
                    session,
                    branch=branch,
                    current_user=current_user,
                    line=purchase_line,
                    product=product,
                    quantity=command_line.received_quantity,
                    receipt=receipt,
                    reason=command_line.discrepancy_reason,
                    notes=command_line.notes,
                )
                self._update_supplier_last_known_price(
                    session,
                    product=product,
                    supplier=supplier,
                    unit_cost=unit_cost,
                )

        receipt.has_discrepancy = has_discrepancy
        document.received_at = receipt.received_at
        if document.confirmed_at is None:
            document.confirmed_at = receipt.received_at
            document.confirmed_by_user_id = current_user.id
        document.status = (
            PURCHASE_STATUS_RECEIVED
            if all(
                Decimal(line.received_quantity) >= Decimal(line.ordered_quantity) for line in lines
            )
            else PURCHASE_STATUS_PARTIALLY_RECEIVED
        )
        self._record_change(
            session,
            action=AUDIT_ACTION_ADMIN_PURCHASE_RECEIVED,
            branch_id=branch.id,
            current_user=current_user,
            document=document,
            event_name=OUTBOX_EVENT_ADMIN_PURCHASE_RECEIVED_V1,
            request_id=request_id,
            receipt=receipt,
        )

    def _apply_receipt_inventory(
        self,
        session: Session,
        *,
        branch: Branch,
        current_user: AuthenticatedUser,
        line: PurchaseDocumentLine,
        notes: str | None,
        product: Product,
        quantity: Decimal,
        reason: str | None,
        receipt: PurchaseReceipt,
    ) -> None:
        balance = self._get_or_create_balance(
            session,
            branch_id=branch.id,
            product_id=product.id,
        )
        new_quantity = Decimal(balance.quantity_on_hand) + quantity
        balance.quantity_on_hand = new_quantity
        session.add(
            InventoryMovement(
                balance_after=new_quantity,
                branch_id=branch.id,
                direction=INVENTORY_MOVEMENT_DIRECTION_IN,
                location_code=INVENTORY_LOCATION_BACKROOM,
                movement_type=INVENTORY_MOVEMENT_TYPE_PURCHASE_RECEIPT,
                notes=notes,
                operator_user_id=current_user.id,
                product_id=product.id,
                quantity=quantity,
                reason=reason or "Supplier receipt",
                source_document_id=receipt.id,
                source_document_type=PURCHASE_RECEIPT_SOURCE_DOCUMENT_TYPE,
                unit_of_measure=line.unit_of_measure,
            )
        )

    def _get_or_create_balance(
        self, session: Session, *, branch_id: uuid.UUID, product_id: uuid.UUID
    ) -> InventoryBalance:
        balance = session.execute(
            select(InventoryBalance)
            .where(
                InventoryBalance.branch_id == branch_id,
                InventoryBalance.location_code == INVENTORY_LOCATION_BACKROOM,
                InventoryBalance.product_id == product_id,
            )
            .with_for_update(),
        ).scalar_one_or_none()
        if balance is not None:
            return balance
        balance = InventoryBalance(
            branch_id=branch_id,
            location_code=INVENTORY_LOCATION_BACKROOM,
            product_id=product_id,
            quantity_on_hand=ZERO,
        )
        session.add(balance)
        session.flush()
        return balance

    def _fetch_rows(
        self,
        session: Session,
        *,
        branch_id: uuid.UUID | None,
        date_from: datetime | None,
        date_to: datetime | None,
        operator_user_id: uuid.UUID | None,
        status_filter: str | None,
        supplier_id: uuid.UUID | None,
    ) -> list[_PurchaseRow]:
        query = (
            select(PurchaseDocument, Supplier, Branch, User)
            .join(Supplier, PurchaseDocument.supplier_id == Supplier.id)
            .join(Branch, PurchaseDocument.receiving_branch_id == Branch.id)
            .join(User, PurchaseDocument.created_by_user_id == User.id)
        )
        if branch_id is not None:
            query = query.where(PurchaseDocument.receiving_branch_id == branch_id)
        if date_from is not None:
            query = query.where(PurchaseDocument.document_date >= date_from)
        if date_to is not None:
            query = query.where(PurchaseDocument.document_date <= date_to)
        if operator_user_id is not None:
            query = query.where(PurchaseDocument.created_by_user_id == operator_user_id)
        normalized_status = _normalize_optional(status_filter)
        if normalized_status and normalized_status != "all":
            query = query.where(PurchaseDocument.status == normalized_status.upper())
        if supplier_id is not None:
            query = query.where(PurchaseDocument.supplier_id == supplier_id)

        records = session.execute(
            query.order_by(
                PurchaseDocument.document_date.desc(), PurchaseDocument.created_at.desc()
            )
        ).all()
        return [
            _PurchaseRow(
                branch=branch,
                created_by_user=user,
                document=document,
                lines=self._get_lines(session, document.id),
                receipts=self._get_receipts(session, document.id),
                supplier=supplier,
            )
            for document, supplier, branch, user in records
        ]

    def _get_row(self, session: Session, purchase_id: uuid.UUID) -> _PurchaseRow:
        result = session.execute(
            select(PurchaseDocument, Supplier, Branch, User)
            .join(Supplier, PurchaseDocument.supplier_id == Supplier.id)
            .join(Branch, PurchaseDocument.receiving_branch_id == Branch.id)
            .join(User, PurchaseDocument.created_by_user_id == User.id)
            .where(PurchaseDocument.id == purchase_id),
        ).one_or_none()
        if result is None:
            raise PurchaseNotFoundError("Purchase was not found.")
        document, supplier, branch, user = result
        return _PurchaseRow(
            branch=branch,
            created_by_user=user,
            document=document,
            lines=self._get_lines(session, document.id),
            receipts=self._get_receipts(session, document.id),
            supplier=supplier,
        )

    def _to_list_item(self, session: Session, row: _PurchaseRow) -> AdminPurchaseListItemView:
        warnings = self._build_warnings(session, row)
        return AdminPurchaseListItemView(
            branch_id=row.branch.id,
            branch_name=row.branch.name,
            created_at=row.document.created_at,
            document_date=row.document.document_date,
            document_type=row.document.document_type,
            external_document_number=row.document.external_document_number,
            folio=row.document.folio,
            has_discrepancy=self._has_discrepancy(session, row),
            id=row.document.id,
            line_count=len(row.lines),
            operator_name=row.created_by_user.full_name,
            received_at=row.document.received_at,
            received_unit_count=self._received_quantity(row.lines),
            status=row.document.status,
            supplier_id=row.supplier.id,
            supplier_name=row.supplier.legal_name,
            total_amount=self._document_total(row.lines),
            warning_state=self._warning_state(warnings),
            warnings=warnings,
        )

    def _to_detail(self, session: Session, row: _PurchaseRow) -> AdminPurchaseDetailView:
        warnings = self._build_warnings(session, row)
        receipt_lines = self._receipt_lines_for_document(session, row.document.id)
        movements = self._inventory_movements(session, row.receipts)
        return AdminPurchaseDetailView(
            available_actions=AdminPurchaseAvailableActionsView(
                can_cancel=row.document.status in {PURCHASE_STATUS_DRAFT, PURCHASE_STATUS_ORDERED}
                and not row.receipts,
                can_confirm=row.document.status == PURCHASE_STATUS_DRAFT,
                can_edit=row.document.status == PURCHASE_STATUS_DRAFT,
                can_receive=row.document.status
                in {
                    PURCHASE_STATUS_DRAFT,
                    PURCHASE_STATUS_ORDERED,
                    PURCHASE_STATUS_PARTIALLY_RECEIVED,
                },
                can_view_movements=True,
            ),
            cost_summary=AdminPurchaseCostSummaryView(
                currency=row.supplier.default_currency,
                received_total=self._received_total(row.lines),
                subtotal=self._document_total(row.lines),
                taxes=None,
                total=self._document_total(row.lines),
            ),
            inventory_impact=AdminPurchaseInventoryImpactView(
                integration_available=True,
                movements=[
                    AdminPurchaseInventoryMovementView(
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
                    for movement in movements
                ],
                notes=None
                if movements
                else "No hay movimientos de inventario vinculados a esta compra.",
            ),
            lines=self._line_views(session, row.lines, receipt_lines, row.supplier.id),
            overview=AdminPurchaseOverviewView(
                branch_id=row.branch.id,
                branch_name=row.branch.name,
                confirmed_at=row.document.confirmed_at,
                created_at=row.document.created_at,
                created_by_user_id=row.created_by_user.id,
                created_by_user_name=row.created_by_user.full_name,
                document_date=row.document.document_date,
                document_type=row.document.document_type,
                external_document_number=row.document.external_document_number,
                external_document_type=row.document.external_document_type,
                folio=row.document.folio,
                has_discrepancy=self._has_discrepancy(session, row),
                id=row.document.id,
                line_count=len(row.lines),
                notes=row.document.notes,
                received_at=row.document.received_at,
                received_unit_count=self._received_quantity(row.lines),
                status=row.document.status,
                supplier_id=row.supplier.id,
                supplier_name=row.supplier.legal_name,
                total_amount=self._document_total(row.lines),
                warning_state=self._warning_state(warnings),
            ),
            receipt=AdminPurchaseReceiptSummaryView(
                expected_quantity=self._ordered_quantity(row.lines),
                has_discrepancy=self._has_discrepancy(session, row),
                pending_quantity=self._pending_quantity(row.lines),
                receipt_count=len(row.receipts),
                received_quantity=self._received_quantity(row.lines),
                state=self._receipt_state(row),
            ),
            receiving_branch=AdminPurchaseBranchView(
                branch_code=row.branch.code,
                branch_id=row.branch.id,
                branch_is_active=row.branch.is_active,
                branch_name=row.branch.name,
                timezone=row.branch.timezone,
            ),
            related_documents=self._related_documents(row),
            supplier_context=AdminPurchaseSupplierContextView(
                commercial_name=row.supplier.commercial_name,
                lead_time_days=row.supplier.lead_time_days,
                payment_terms_summary=self._payment_terms_summary(row.supplier),
                primary_contact=self._primary_contact_label(session, row.supplier.id),
                status=row.supplier.status,
                supplier_id=row.supplier.id,
                supplier_name=row.supplier.legal_name,
            ),
            warnings=warnings,
        )

    def _line_views(
        self,
        session: Session,
        lines: list[PurchaseDocumentLine],
        receipt_lines: list[PurchaseReceiptLine],
        supplier_id: uuid.UUID,
    ) -> list[AdminPurchaseLineView]:
        products = self._products_by_id(session, {line.product_id for line in lines})
        supplier_products = {
            relation.product_id: relation
            for relation in session.execute(
                select(SupplierProduct).where(SupplierProduct.supplier_id == supplier_id),
            )
            .scalars()
            .all()
        }
        receipt_reasons: dict[uuid.UUID, str] = {}
        for receipt_line in receipt_lines:
            if receipt_line.discrepancy_reason:
                receipt_reasons[receipt_line.purchase_line_id] = receipt_line.discrepancy_reason

        views: list[AdminPurchaseLineView] = []
        for line in lines:
            product = products[line.product_id]
            pending = Decimal(line.ordered_quantity) - Decimal(line.received_quantity)
            discrepancy = ZERO if pending == ZERO else pending
            supplier_product = supplier_products.get(line.product_id)
            views.append(
                AdminPurchaseLineView(
                    discrepancy=discrepancy,
                    discrepancy_reason=receipt_reasons.get(line.id),
                    line_status=(
                        "received"
                        if pending == ZERO
                        else "partial"
                        if line.received_quantity > ZERO
                        else "pending"
                    ),
                    line_total=Decimal(line.ordered_quantity) * Decimal(line.unit_cost),
                    notes=line.notes,
                    ordered_quantity=line.ordered_quantity,
                    pending_quantity=pending,
                    product_code=line.product_code_snapshot,
                    product_id=line.product_id,
                    product_kind=line.product_kind_snapshot,
                    product_name=line.product_name_snapshot,
                    purchase_line_id=line.id,
                    received_quantity=line.received_quantity,
                    standard_cost=product.standard_cost,
                    supplier_last_known_price=supplier_product.last_known_price
                    if supplier_product
                    else None,
                    unit_cost=line.unit_cost,
                    unit_of_measure=line.unit_of_measure,
                )
            )
        return views

    def _build_filter_options(self, session: Session) -> AdminPurchaseFilterOptionsView:
        branches = (
            session.execute(select(Branch).order_by(Branch.name.asc(), Branch.code.asc()))
            .scalars()
            .all()
        )
        products = (
            session.execute(select(Product).order_by(Product.name.asc(), Product.code.asc()))
            .scalars()
            .all()
        )
        suppliers = (
            session.execute(
                select(Supplier).order_by(Supplier.legal_name.asc(), Supplier.code.asc())
            )
            .scalars()
            .all()
        )
        operators = (
            session.execute(select(User).order_by(User.full_name.asc(), User.email.asc()))
            .scalars()
            .all()
        )
        return AdminPurchaseFilterOptionsView(
            branches=[
                AdminPurchaseFilterOptionView(id=branch.id, label=f"{branch.name} - {branch.code}")
                for branch in branches
            ],
            operators=[
                AdminPurchaseFilterOptionView(id=user.id, label=user.full_name)
                for user in operators
            ],
            product_kinds=[
                AdminPurchaseFilterOptionView(id=code, label=label)
                for code, label in PRODUCT_KIND_LABELS.items()
            ],
            products=[
                AdminPurchaseFilterOptionView(
                    id=product.id, label=f"{product.name} - {product.code}"
                )
                for product in products
            ],
            statuses=[
                AdminPurchaseFilterOptionView(id=status, label=_status_label(status))
                for status in (
                    PURCHASE_STATUS_DRAFT,
                    PURCHASE_STATUS_ORDERED,
                    PURCHASE_STATUS_PARTIALLY_RECEIVED,
                    PURCHASE_STATUS_RECEIVED,
                    PURCHASE_STATUS_CANCELLED,
                )
            ],
            suppliers=[
                AdminPurchaseFilterOptionView(
                    id=supplier.id, label=f"{supplier.legal_name} - {supplier.code}"
                )
                for supplier in suppliers
            ],
        )

    def _build_metrics(
        self, session: Session, rows: list[_PurchaseRow]
    ) -> AdminPurchaseMetricsView:
        _ = session
        return AdminPurchaseMetricsView(
            active_suppliers_used=len(
                {row.supplier.id for row in rows if row.supplier.status == SUPPLIER_STATUS_ACTIVE}
            ),
            confirmed_entries=sum(
                1 for row in rows if row.document.status == PURCHASE_STATUS_RECEIVED
            ),
            partially_received=sum(
                1 for row in rows if row.document.status == PURCHASE_STATUS_PARTIALLY_RECEIVED
            ),
            pending_receipt=sum(
                1
                for row in rows
                if row.document.status
                in {PURCHASE_STATUS_ORDERED, PURCHASE_STATUS_PARTIALLY_RECEIVED}
            ),
            total_amount=sum((self._document_total(row.lines) for row in rows), ZERO),
            total_documents=len(rows),
            with_discrepancies=sum(1 for row in rows if self._has_discrepancy(session, row)),
        )

    def _build_warnings(
        self, session: Session, row: _PurchaseRow
    ) -> list[AdminPurchaseWarningView]:
        warnings: list[AdminPurchaseWarningView] = []
        if row.supplier.status != SUPPLIER_STATUS_ACTIVE:
            warnings.append(
                AdminPurchaseWarningView(
                    code="supplier_not_active",
                    message="El proveedor no esta activo.",
                    severity="critical",
                )
            )
        if not row.branch.is_active:
            warnings.append(
                AdminPurchaseWarningView(
                    code="branch_inactive",
                    message="La sucursal receptora esta inactiva.",
                    severity="critical",
                )
            )
        if row.document.status in {PURCHASE_STATUS_ORDERED, PURCHASE_STATUS_PARTIALLY_RECEIVED}:
            warnings.append(
                AdminPurchaseWarningView(
                    code="pending_receipt",
                    message="La compra tiene recepcion pendiente.",
                    severity="warning",
                )
            )
        if self._has_discrepancy(session, row):
            warnings.append(
                AdminPurchaseWarningView(
                    code="receipt_discrepancy",
                    message="La compra tiene diferencias de recepcion.",
                    severity="critical",
                )
            )
        if row.document.status == PURCHASE_STATUS_DRAFT and not row.lines:
            warnings.append(
                AdminPurchaseWarningView(
                    code="empty_draft", message="El borrador no tiene lineas.", severity="critical"
                )
            )
        if self._has_unlinked_supplier_products(session, row):
            warnings.append(
                AdminPurchaseWarningView(
                    code="supplier_product_unlinked",
                    message="Hay productos no asociados al proveedor.",
                    severity="info",
                )
            )
        return warnings

    def _has_unlinked_supplier_products(self, session: Session, row: _PurchaseRow) -> bool:
        if not row.lines:
            return False
        active_product_ids = {
            relation.product_id
            for relation in session.execute(
                select(SupplierProduct).where(
                    SupplierProduct.supplier_id == row.supplier.id,
                    SupplierProduct.is_active.is_(True),
                ),
            )
            .scalars()
            .all()
        }
        return any(line.product_id not in active_product_ids for line in row.lines)

    def _validate_supplier_and_branch(self, supplier: Supplier, branch: Branch) -> None:
        if supplier.status != SUPPLIER_STATUS_ACTIVE:
            raise PurchaseValidationError("Supplier must be active for new purchases or receipts.")
        if not branch.is_active:
            raise PurchaseValidationError("Receiving branch must be active.")

    def _validate_external_document_type(self, value: str | None) -> None:
        if value is not None and value.upper() not in VALID_PURCHASE_EXTERNAL_DOCUMENT_TYPES:
            raise PurchaseValidationError("External document type is not supported.")

    def _resolve_line_products(
        self, session: Session, lines: list[AdminPurchaseLineInput]
    ) -> dict[uuid.UUID, Product]:
        products = self._products_by_id(session, {line.product_id for line in lines})
        self._validate_active_products(products)
        return products

    def _resolve_direct_entry_products(
        self, session: Session, lines: list[AdminPurchaseDirectEntryLineInput]
    ) -> dict[uuid.UUID, Product]:
        products = self._products_by_id(session, {line.product_id for line in lines})
        self._validate_active_products(products)
        return products

    def _products_by_id(
        self, session: Session, product_ids: set[uuid.UUID]
    ) -> dict[uuid.UUID, Product]:
        if not product_ids:
            return {}
        products = {
            product.id: product
            for product in session.execute(select(Product).where(Product.id.in_(product_ids)))
            .scalars()
            .all()
        }
        missing = product_ids - set(products)
        if missing:
            raise PurchaseNotFoundError("Product was not found.")
        return products

    def _validate_active_products(self, products: dict[uuid.UUID, Product]) -> None:
        if any(not product.is_active for product in products.values()):
            raise PurchaseValidationError("Products must be active for purchase entries.")

    def _replace_lines(
        self,
        session: Session,
        *,
        document: PurchaseDocument,
        lines: list[AdminPurchaseLineInput],
        products: dict[uuid.UUID, Product],
    ) -> None:
        for line in self._get_lines(session, document.id):
            session.delete(line)
        session.flush()
        for index, line in enumerate(lines, start=1):
            product = products[line.product_id]
            session.add(
                PurchaseDocumentLine(
                    line_number=index,
                    notes=line.notes,
                    ordered_quantity=line.ordered_quantity,
                    product_code_snapshot=product.code,
                    product_id=product.id,
                    product_kind_snapshot=product.product_kind,
                    product_name_snapshot=product.name,
                    purchase_document_id=document.id,
                    received_quantity=ZERO,
                    unit_cost=line.unit_cost,
                    unit_of_measure=product.unit_of_measure,
                )
            )
        session.flush()

    def _get_document(self, session: Session, purchase_id: uuid.UUID) -> PurchaseDocument:
        document = session.get(PurchaseDocument, purchase_id)
        if document is None:
            raise PurchaseNotFoundError("Purchase was not found.")
        return document

    def _get_supplier(self, session: Session, supplier_id: uuid.UUID) -> Supplier:
        supplier = session.get(Supplier, supplier_id)
        if supplier is None:
            raise PurchaseNotFoundError("Supplier was not found.")
        return supplier

    def _get_branch(self, session: Session, branch_id: uuid.UUID) -> Branch:
        branch = session.get(Branch, branch_id)
        if branch is None:
            raise PurchaseNotFoundError("Branch was not found.")
        return branch

    def _get_lines(
        self, session: Session, document_id: uuid.UUID, *, for_update: bool = False
    ) -> list[PurchaseDocumentLine]:
        query = (
            select(PurchaseDocumentLine)
            .where(PurchaseDocumentLine.purchase_document_id == document_id)
            .order_by(PurchaseDocumentLine.line_number.asc())
        )
        if for_update:
            query = query.with_for_update()
        return session.execute(query).scalars().all()

    def _get_receipts(self, session: Session, document_id: uuid.UUID) -> list[PurchaseReceipt]:
        return (
            session.execute(
                select(PurchaseReceipt)
                .where(PurchaseReceipt.purchase_document_id == document_id)
                .order_by(PurchaseReceipt.received_at.asc()),
            )
            .scalars()
            .all()
        )

    def _receipt_lines_for_document(
        self, session: Session, document_id: uuid.UUID
    ) -> list[PurchaseReceiptLine]:
        return (
            session.execute(
                select(PurchaseReceiptLine)
                .join(
                    PurchaseReceipt, PurchaseReceiptLine.purchase_receipt_id == PurchaseReceipt.id
                )
                .where(PurchaseReceipt.purchase_document_id == document_id)
                .order_by(PurchaseReceipt.received_at.asc(), PurchaseReceiptLine.line_number.asc()),
            )
            .scalars()
            .all()
        )

    def _inventory_movements(
        self, session: Session, receipts: list[PurchaseReceipt]
    ) -> list[InventoryMovement]:
        receipt_ids = [receipt.id for receipt in receipts]
        if not receipt_ids:
            return []
        return (
            session.execute(
                select(InventoryMovement)
                .where(
                    InventoryMovement.source_document_type == PURCHASE_RECEIPT_SOURCE_DOCUMENT_TYPE,
                    InventoryMovement.source_document_id.in_(receipt_ids),
                )
                .order_by(InventoryMovement.occurred_at.asc()),
            )
            .scalars()
            .all()
        )

    def _has_discrepancy(self, session: Session, row: _PurchaseRow) -> bool:
        _ = session
        return any(receipt.has_discrepancy for receipt in row.receipts)

    def _matches_search(self, row: _PurchaseRow, search: str) -> bool:
        haystack = " ".join(
            [
                row.document.folio,
                row.document.external_document_number or "",
                row.supplier.legal_name,
                row.supplier.commercial_name or "",
                row.supplier.code,
                row.branch.name,
                row.branch.code,
                row.document.status,
            ]
        ).lower()
        return search.lower() in haystack

    def _update_supplier_last_known_price(
        self, session: Session, *, product: Product, supplier: Supplier, unit_cost: Decimal
    ) -> None:
        relation = session.execute(
            select(SupplierProduct).where(
                SupplierProduct.supplier_id == supplier.id, SupplierProduct.product_id == product.id
            ),
        ).scalar_one_or_none()
        if relation is None:
            relation = SupplierProduct(
                product_id=product.id,
                purchase_uom=product.unit_of_measure,
                supplier_id=supplier.id,
            )
            session.add(relation)
        relation.currency = supplier.default_currency
        relation.is_active = True
        relation.last_known_price = unit_cost
        relation.purchase_uom = relation.purchase_uom or product.unit_of_measure

    def _record_change(
        self,
        session: Session,
        *,
        action: str,
        branch_id: uuid.UUID,
        current_user: AuthenticatedUser,
        document: PurchaseDocument,
        event_name: str,
        request_id: str | None,
        receipt: PurchaseReceipt | None = None,
    ) -> None:
        metadata = {
            "document_type": document.document_type,
            "folio": document.folio,
            "purchase_id": str(document.id),
            "receipt_id": str(receipt.id) if receipt else None,
            "status": document.status,
            "supplier_id": str(document.supplier_id),
        }
        self._audit_recorder.record(
            session,
            actor_id=current_user.id,
            action=action,
            branch_id=branch_id,
            metadata=metadata,
            request_id=request_id,
            resource_id=str(document.id),
            resource_type=PURCHASE_RESOURCE_TYPE,
        )
        self._outbox_writer.append(
            session,
            aggregate_id=str(receipt.id if receipt else document.id),
            aggregate_type=PURCHASE_RECEIPT_RESOURCE_TYPE if receipt else PURCHASE_RESOURCE_TYPE,
            event_name=event_name,
            headers={"request_id": request_id} if request_id else {},
            payload=metadata,
        )

    def _related_documents(self, row: _PurchaseRow) -> list[AdminPurchaseRelatedDocumentView]:
        documents = [
            AdminPurchaseRelatedDocumentView(
                document_id=row.supplier.id,
                document_type="SUPPLIER",
                folio=row.supplier.code,
                status=row.supplier.status,
            )
        ]
        documents.extend(
            AdminPurchaseRelatedDocumentView(
                document_id=receipt.id,
                document_type=PURCHASE_RECEIPT_SOURCE_DOCUMENT_TYPE,
                folio=receipt.folio,
                status="COMMITTED",
            )
            for receipt in row.receipts
        )
        return documents

    def _primary_contact_label(self, session: Session, supplier_id: uuid.UUID) -> str | None:
        contact = (
            session.execute(
                select(SupplierContact)
                .where(
                    SupplierContact.supplier_id == supplier_id, SupplierContact.is_active.is_(True)
                )
                .order_by(SupplierContact.is_primary.desc(), SupplierContact.created_at.asc()),
            )
            .scalars()
            .first()
        )
        if contact is None:
            return None
        channel = contact.phone or contact.email or contact.whatsapp
        return f"{contact.name} - {channel}" if channel else contact.name

    def _payment_terms_summary(self, supplier: Supplier) -> str:
        if supplier.payment_terms_type == SUPPLIER_PAYMENT_TERMS_CREDIT:
            return f"Credito {supplier.credit_days} dias"
        return supplier.payment_terms_type

    def _receipt_state(self, row: _PurchaseRow) -> str:
        if row.document.status == PURCHASE_STATUS_CANCELLED:
            return "cancelled"
        if row.document.status == PURCHASE_STATUS_DRAFT:
            return "draft"
        if row.document.status == PURCHASE_STATUS_ORDERED:
            return "pending"
        if row.document.status == PURCHASE_STATUS_PARTIALLY_RECEIVED:
            return "partial"
        return "received"

    def _warning_state(
        self, warnings: list[AdminPurchaseWarningView]
    ) -> AdminPurchaseWarningSeverity | None:
        if any(warning.severity == "critical" for warning in warnings):
            return "critical"
        if any(warning.severity == "warning" for warning in warnings):
            return "warning"
        if warnings:
            return "info"
        return None

    def _generate_folio(self, session: Session, document_type: str) -> str:
        prefix = "ENT" if document_type == PURCHASE_DOCUMENT_TYPE_DIRECT_ENTRY else "CMP"
        return self._generate_unique_code(session, prefix, PurchaseDocument.folio)

    def _generate_receipt_folio(self, session: Session) -> str:
        return self._generate_unique_code(session, "REC", PurchaseReceipt.folio)

    def _generate_unique_code(self, session: Session, prefix: str, column) -> str:
        for _ in range(20):
            code = f"{prefix}-{str(uuid.uuid4()).split('-', maxsplit=1)[0].upper()}"
            if session.execute(select(column).where(column == code)).scalar_one_or_none() is None:
                return code
        raise PurchaseValidationError("Could not generate document folio.")

    def _document_total(self, lines: list[PurchaseDocumentLine]) -> Decimal:
        return sum(
            (Decimal(line.ordered_quantity) * Decimal(line.unit_cost) for line in lines), ZERO
        )

    def _received_total(self, lines: list[PurchaseDocumentLine]) -> Decimal:
        return sum(
            (Decimal(line.received_quantity) * Decimal(line.unit_cost) for line in lines), ZERO
        )

    def _ordered_quantity(self, lines: list[PurchaseDocumentLine]) -> Decimal:
        return sum((Decimal(line.ordered_quantity) for line in lines), ZERO)

    def _received_quantity(self, lines: list[PurchaseDocumentLine]) -> Decimal:
        return sum((Decimal(line.received_quantity) for line in lines), ZERO)

    def _pending_quantity(self, lines: list[PurchaseDocumentLine]) -> Decimal:
        return sum(
            (Decimal(line.ordered_quantity) - Decimal(line.received_quantity) for line in lines),
            ZERO,
        )


def _normalize_optional(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def _status_label(status: str) -> str:
    return {
        PURCHASE_STATUS_CANCELLED: "Cancelada",
        PURCHASE_STATUS_DRAFT: "Borrador",
        PURCHASE_STATUS_ORDERED: "Pendiente de recepcion",
        PURCHASE_STATUS_PARTIALLY_RECEIVED: "Recibida parcialmente",
        PURCHASE_STATUS_RECEIVED: "Recibida",
    }.get(status, status)
