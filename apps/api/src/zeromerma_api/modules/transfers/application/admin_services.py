from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import delete, exists, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, aliased

from zeromerma_api.modules.audit.application.service import AuditRecorder
from zeromerma_api.modules.branches.infrastructure.models import Branch, Workstation
from zeromerma_api.modules.catalog.infrastructure.models import Product, ProductClass
from zeromerma_api.modules.identity.application.schemas import AuthenticatedUser
from zeromerma_api.modules.identity.infrastructure.models import User
from zeromerma_api.modules.inventory.domain.constants import (
    INVENTORY_LOCATION_BACKROOM,
    INVENTORY_LOCATION_IN_TRANSIT,
    INVENTORY_MOVEMENT_DIRECTION_IN,
    INVENTORY_MOVEMENT_DIRECTION_OUT,
    INVENTORY_MOVEMENT_TYPE_TRANSFER_DISPATCH,
    INVENTORY_MOVEMENT_TYPE_TRANSFER_RECEIPT,
)
from zeromerma_api.modules.inventory.infrastructure.models import InventoryBalance, InventoryMovement
from zeromerma_api.modules.operations.domain.constants import (
    OPERATION_BUCKET_BACKROOM,
    OPERATION_BUCKET_IN_TRANSIT,
    OPERATION_DOCUMENT_STATUS_CANCELLED,
    OPERATION_DOCUMENT_STATUS_DRAFT,
    OPERATION_DOCUMENT_STATUS_IN_TRANSIT,
    OPERATION_DOCUMENT_STATUS_RECEIVED,
    OPERATION_DOCUMENT_STATUS_RECEIVED_WITH_VARIANCE,
    OPERATION_DOCUMENT_TYPE_BRANCH_TRANSFER_RECEIPT,
    OPERATION_DOCUMENT_TYPE_BRANCH_TRANSFER_SHIPMENT,
    OUTBOX_EVENT_TRANSFER_DISPATCHED_V1,
    OUTBOX_EVENT_TRANSFER_RECEIVED_V1,
)
from zeromerma_api.modules.operations.infrastructure.models import OperationDocument, OperationDocumentLine
from zeromerma_api.modules.outbox.application.service import OutboxWriter
from zeromerma_api.modules.transfers.application.admin_schemas import (
    AdminTransferAvailableActionsView,
    AdminTransferBranchView,
    AdminTransferCancelRequest,
    AdminTransferCreateRequest,
    AdminTransferDetailView,
    AdminTransferDispatchRequest,
    AdminTransferFilterOptionView,
    AdminTransferFilterOptionsView,
    AdminTransferInventoryImpactView,
    AdminTransferInventoryMovementView,
    AdminTransferLineInput,
    AdminTransferLineView,
    AdminTransferListItemView,
    AdminTransferListResponse,
    AdminTransferMetricsView,
    AdminTransferOverviewView,
    AdminTransferReceiptView,
    AdminTransferReceiveRequest,
    AdminTransferRelatedDocumentView,
    AdminTransferUpdateRequest,
    AdminTransferWarningSeverity,
    AdminTransferWarningView,
)
from zeromerma_api.modules.transfers.domain.exceptions import (
    TransferAlreadyReceivedError,
    TransferNotFoundError,
    TransferValidationError,
)

ADMIN_TRANSFER_CREATED_EVENT = "admin.transfer.created.v1"
ADMIN_TRANSFER_CANCELLED_EVENT = "admin.transfer.cancelled.v1"
ADMIN_TRANSFER_RESOURCE_TYPE = "operation_document"
TRANSFER_MOVEMENT_SOURCE_DISPATCH = "BRANCH_TRANSFER_SHIPMENT"
TRANSFER_MOVEMENT_SOURCE_RECEIPT = "BRANCH_TRANSFER_RECEIPT"
VALID_ADMIN_TRANSFER_STATUSES = {
    OPERATION_DOCUMENT_STATUS_DRAFT,
    OPERATION_DOCUMENT_STATUS_IN_TRANSIT,
    OPERATION_DOCUMENT_STATUS_RECEIVED,
    OPERATION_DOCUMENT_STATUS_RECEIVED_WITH_VARIANCE,
    OPERATION_DOCUMENT_STATUS_CANCELLED,
}


@dataclass(frozen=True)
class _ResolvedProduct:
    product: Product
    product_class: ProductClass


@dataclass(frozen=True)
class _AdminTransferRow:
    created_by_user: User
    destination_branch: Branch
    origin_branch: Branch
    receipt: OperationDocument | None
    receipt_created_by_user: User | None
    shipment: OperationDocument
    workstation: Workstation


class AdminTransferService:
    def __init__(
        self,
        audit_recorder: AuditRecorder | None = None,
        outbox_writer: OutboxWriter | None = None,
    ) -> None:
        self._audit_recorder = audit_recorder or AuditRecorder()
        self._outbox_writer = outbox_writer or OutboxWriter()

    def list_transfers(
        self,
        session: Session,
        *,
        date_from: datetime | None,
        date_to: datetime | None,
        destination_branch_id: uuid.UUID | None,
        discrepancy_state: str | None,
        operator_user_id: uuid.UUID | None,
        origin_branch_id: uuid.UUID | None,
        product_id: uuid.UUID | None,
        search: str | None,
        status_filter: str | None,
        page: int,
        page_size: int,
    ) -> AdminTransferListResponse:
        rows = self._fetch_rows(
            session,
            date_from=date_from,
            date_to=date_to,
            destination_branch_id=destination_branch_id,
            operator_user_id=operator_user_id,
            origin_branch_id=origin_branch_id,
            product_id=product_id,
            status_filter=status_filter,
        )

        normalized_discrepancy_state = _normalize_optional(discrepancy_state)
        if normalized_discrepancy_state == "with_discrepancy":
            rows = [row for row in rows if self._has_discrepancy(session, row)]
        elif normalized_discrepancy_state == "without_discrepancy":
            rows = [row for row in rows if not self._has_discrepancy(session, row)]

        normalized_search = _normalize_optional(search)
        if normalized_search:
            rows = [row for row in rows if self._matches_search(row, normalized_search)]

        items = [self._to_list_item(session, row) for row in rows]
        total = len(items)
        safe_page = max(page, 1)
        safe_page_size = min(max(page_size, 1), 100)
        offset = (safe_page - 1) * safe_page_size

        return AdminTransferListResponse(
            filter_options=self._build_filter_options(session),
            items=items[offset : offset + safe_page_size],
            metrics=self._build_metrics(session, rows),
            page=safe_page,
            page_size=safe_page_size,
            total=total,
        )

    def get_transfer_detail(
        self,
        session: Session,
        *,
        transfer_id: uuid.UUID,
    ) -> AdminTransferDetailView:
        row = self._get_row(session, transfer_id)
        return self._to_detail(session, row)

    def create_transfer(
        self,
        session: Session,
        *,
        current_user: AuthenticatedUser,
        command: AdminTransferCreateRequest,
        request_id: str | None,
    ) -> AdminTransferDetailView:
        origin_branch = self._get_branch(session, command.origin_branch_id)
        destination_branch = self._get_branch(session, command.destination_branch_id)
        self._validate_transfer_branches(origin_branch, destination_branch, for_dispatch=False)
        workstation = self._get_active_workstation_for_branch(session, origin_branch.id)
        resolved_products = self._resolve_products(session, command.lines)

        shipment = OperationDocument(
            document_type=OPERATION_DOCUMENT_TYPE_BRANCH_TRANSFER_SHIPMENT,
            status=OPERATION_DOCUMENT_STATUS_DRAFT,
            source_branch_id=origin_branch.id,
            destination_branch_id=destination_branch.id,
            source_bucket_code=OPERATION_BUCKET_BACKROOM,
            destination_bucket_code=OPERATION_BUCKET_BACKROOM,
            workstation_id=workstation.id,
            created_by_user_id=current_user.id,
            notes=command.notes,
            committed_at_utc=None,
        )

        try:
            session.add(shipment)
            session.flush()
            self._replace_lines(session, shipment=shipment, lines=command.lines, resolved_products=resolved_products)
            self._record_change(
                session,
                current_user=current_user,
                shipment=shipment,
                action="admin.transfer.created",
                event_name=ADMIN_TRANSFER_CREATED_EVENT,
                request_id=request_id,
                metadata={
                    "destination_branch_id": str(destination_branch.id),
                    "line_count": len(command.lines),
                    "origin_branch_id": str(origin_branch.id),
                    "status": shipment.status,
                },
            )
            session.commit()
        except IntegrityError as error:
            session.rollback()
            raise TransferValidationError("Transfer draft could not be created.") from error

        return self.get_transfer_detail(session, transfer_id=shipment.id)

    def update_transfer(
        self,
        session: Session,
        *,
        current_user: AuthenticatedUser,
        transfer_id: uuid.UUID,
        command: AdminTransferUpdateRequest,
        request_id: str | None,
    ) -> AdminTransferDetailView:
        shipment = self._get_shipment(session, transfer_id)
        if shipment.status != OPERATION_DOCUMENT_STATUS_DRAFT:
            raise TransferValidationError("Only draft transfers can be edited.")

        origin_branch = self._get_branch(session, command.origin_branch_id or shipment.source_branch_id)
        if shipment.destination_branch_id is None and command.destination_branch_id is None:
            raise TransferValidationError("Destination branch is required.")
        destination_branch = self._get_branch(
            session,
            command.destination_branch_id or shipment.destination_branch_id,
        )
        self._validate_transfer_branches(origin_branch, destination_branch, for_dispatch=False)

        shipment.source_branch_id = origin_branch.id
        shipment.destination_branch_id = destination_branch.id
        shipment.workstation_id = self._get_active_workstation_for_branch(session, origin_branch.id).id
        if "notes" in command.model_fields_set:
            shipment.notes = command.notes

        try:
            if command.lines is not None:
                resolved_products = self._resolve_products(session, command.lines)
                self._replace_lines(
                    session,
                    shipment=shipment,
                    lines=command.lines,
                    resolved_products=resolved_products,
                )
            self._record_change(
                session,
                current_user=current_user,
                shipment=shipment,
                action="admin.transfer.updated",
                event_name=ADMIN_TRANSFER_CREATED_EVENT,
                request_id=request_id,
                metadata={
                    "destination_branch_id": str(destination_branch.id),
                    "origin_branch_id": str(origin_branch.id),
                    "status": shipment.status,
                },
            )
            session.commit()
        except IntegrityError as error:
            session.rollback()
            raise TransferValidationError("Transfer draft could not be updated.") from error

        return self.get_transfer_detail(session, transfer_id=shipment.id)

    def dispatch_transfer(
        self,
        session: Session,
        *,
        current_user: AuthenticatedUser,
        transfer_id: uuid.UUID,
        command: AdminTransferDispatchRequest,
        request_id: str | None,
    ) -> AdminTransferDetailView:
        shipment = self._get_shipment(session, transfer_id)
        if shipment.status != OPERATION_DOCUMENT_STATUS_DRAFT:
            raise TransferValidationError("Only draft transfers can be dispatched.")
        if shipment.destination_branch_id is None:
            raise TransferValidationError("Destination branch is required.")

        origin_branch = self._get_branch(session, shipment.source_branch_id)
        destination_branch = self._get_branch(session, shipment.destination_branch_id)
        self._validate_transfer_branches(origin_branch, destination_branch, for_dispatch=True)
        shipment_lines = self._get_shipment_lines(session, shipment.id)
        if not shipment_lines:
            raise TransferValidationError("Transfer must contain at least one line.")

        self._validate_origin_stock(session, shipment_lines=shipment_lines, origin_branch_id=origin_branch.id)
        committed_at = datetime.now(tz=UTC)
        shipment.status = OPERATION_DOCUMENT_STATUS_IN_TRANSIT
        shipment.committed_at_utc = committed_at
        if command.notes is not None:
            shipment.notes = command.notes

        try:
            self._apply_dispatch_inventory(
                session,
                current_user=current_user,
                shipment=shipment,
                shipment_lines=shipment_lines,
                destination_branch_id=destination_branch.id,
            )
            self._record_change(
                session,
                current_user=current_user,
                shipment=shipment,
                action="transfer.dispatched",
                event_name=OUTBOX_EVENT_TRANSFER_DISPATCHED_V1,
                request_id=request_id,
                metadata={
                    "destination_branch_id": str(destination_branch.id),
                    "line_count": len(shipment_lines),
                    "origin_branch_id": str(origin_branch.id),
                    "status": shipment.status,
                },
            )
            session.commit()
        except IntegrityError as error:
            session.rollback()
            raise TransferValidationError("Transfer dispatch could not be persisted.") from error

        return self.get_transfer_detail(session, transfer_id=shipment.id)

    def receive_transfer(
        self,
        session: Session,
        *,
        current_user: AuthenticatedUser,
        transfer_id: uuid.UUID,
        command: AdminTransferReceiveRequest,
        request_id: str | None,
    ) -> AdminTransferDetailView:
        shipment = self._get_shipment(session, transfer_id)
        if shipment.status != OPERATION_DOCUMENT_STATUS_IN_TRANSIT:
            raise TransferAlreadyReceivedError("Transfer shipment is no longer pending receipt.")
        if shipment.destination_branch_id is None:
            raise TransferValidationError("Transfer destination branch is missing.")

        existing_receipt = self._get_receipt(session, shipment.id)
        if existing_receipt is not None:
            raise TransferAlreadyReceivedError("Transfer shipment is no longer pending receipt.")

        shipment_lines = self._get_shipment_lines(session, shipment.id)
        if not shipment_lines:
            raise TransferValidationError("Transfer shipment has no lines.")

        receipt_by_line_id = {line.shipment_line_id: line for line in command.lines}
        if {line.id for line in shipment_lines} != set(receipt_by_line_id):
            raise TransferValidationError("Transfer receipt lines must match the pending shipment lines exactly.")

        for shipment_line in shipment_lines:
            receipt_line = receipt_by_line_id[shipment_line.id]
            if receipt_line.received_quantity != shipment_line.quantity and not receipt_line.variance_reason:
                raise TransferValidationError(
                    "Variance reason is required when the received quantity differs from the shipment."
                )

        destination_branch = self._get_branch(session, shipment.destination_branch_id)
        workstation = self._get_active_workstation_for_branch(session, destination_branch.id)
        committed_at = datetime.now(tz=UTC)
        has_discrepancy = False
        receipt = OperationDocument(
            document_type=OPERATION_DOCUMENT_TYPE_BRANCH_TRANSFER_RECEIPT,
            status=OPERATION_DOCUMENT_STATUS_RECEIVED,
            source_branch_id=shipment.source_branch_id,
            destination_branch_id=destination_branch.id,
            source_bucket_code=OPERATION_BUCKET_IN_TRANSIT,
            destination_bucket_code=OPERATION_BUCKET_BACKROOM,
            workstation_id=workstation.id,
            created_by_user_id=current_user.id,
            notes=command.notes,
            reference_document_id=shipment.id,
            committed_at_utc=committed_at,
        )

        try:
            session.add(receipt)
            session.flush()
            for shipment_line in shipment_lines:
                receipt_line = receipt_by_line_id[shipment_line.id]
                if receipt_line.received_quantity != shipment_line.quantity:
                    has_discrepancy = True
                session.add(
                    OperationDocumentLine(
                        operation_document_id=receipt.id,
                        line_number=shipment_line.line_number,
                        product_id=shipment_line.product_id,
                        product_code_snapshot=shipment_line.product_code_snapshot,
                        product_name_snapshot=shipment_line.product_name_snapshot,
                        product_class_id=shipment_line.product_class_id,
                        product_class_code_snapshot=shipment_line.product_class_code_snapshot,
                        product_class_name_snapshot=shipment_line.product_class_name_snapshot,
                        quantity=shipment_line.quantity,
                        expected_quantity=shipment_line.quantity,
                        received_quantity=receipt_line.received_quantity,
                        unit_of_measure_code=shipment_line.unit_of_measure_code,
                        variance_reason=receipt_line.variance_reason,
                        notes=receipt_line.notes,
                    )
                )

            receipt.status = (
                OPERATION_DOCUMENT_STATUS_RECEIVED_WITH_VARIANCE
                if has_discrepancy
                else OPERATION_DOCUMENT_STATUS_RECEIVED
            )
            shipment.status = receipt.status
            self._apply_receipt_inventory(
                session,
                current_user=current_user,
                shipment=shipment,
                receipt=receipt,
                shipment_lines=shipment_lines,
                receipt_by_line_id=receipt_by_line_id,
            )
            self._record_change(
                session,
                current_user=current_user,
                shipment=shipment,
                action="transfer.received",
                event_name=OUTBOX_EVENT_TRANSFER_RECEIVED_V1,
                request_id=request_id,
                metadata={
                    "destination_branch_id": str(destination_branch.id),
                    "line_count": len(shipment_lines),
                    "receipt_id": str(receipt.id),
                    "shipment_id": str(shipment.id),
                    "status": receipt.status,
                },
            )
            session.commit()
        except IntegrityError as error:
            session.rollback()
            raise TransferValidationError("Transfer receipt could not be persisted.") from error

        return self.get_transfer_detail(session, transfer_id=shipment.id)

    def cancel_transfer(
        self,
        session: Session,
        *,
        current_user: AuthenticatedUser,
        transfer_id: uuid.UUID,
        command: AdminTransferCancelRequest,
        request_id: str | None,
    ) -> AdminTransferDetailView:
        shipment = self._get_shipment(session, transfer_id)
        if shipment.status != OPERATION_DOCUMENT_STATUS_DRAFT:
            raise TransferValidationError("Only draft transfers can be cancelled.")

        shipment.status = OPERATION_DOCUMENT_STATUS_CANCELLED
        shipment.committed_at_utc = datetime.now(tz=UTC)
        if command.reason:
            shipment.notes = command.reason if not shipment.notes else f"{shipment.notes}\nCancel: {command.reason}"

        self._record_change(
            session,
            current_user=current_user,
            shipment=shipment,
            action="admin.transfer.cancelled",
            event_name=ADMIN_TRANSFER_CANCELLED_EVENT,
            request_id=request_id,
            metadata={"reason": command.reason, "status": shipment.status},
        )
        session.commit()

        return self.get_transfer_detail(session, transfer_id=shipment.id)

    def _fetch_rows(
        self,
        session: Session,
        *,
        date_from: datetime | None,
        date_to: datetime | None,
        destination_branch_id: uuid.UUID | None,
        operator_user_id: uuid.UUID | None,
        origin_branch_id: uuid.UUID | None,
        product_id: uuid.UUID | None,
        status_filter: str | None,
    ) -> list[_AdminTransferRow]:
        origin_branch = aliased(Branch)
        destination_branch = aliased(Branch)
        receipt_document = aliased(OperationDocument)
        receipt_user = aliased(User)

        query = (
            select(
                OperationDocument,
                origin_branch,
                destination_branch,
                Workstation,
                User,
                receipt_document,
                receipt_user,
            )
            .select_from(OperationDocument)
            .join(origin_branch, origin_branch.id == OperationDocument.source_branch_id)
            .join(destination_branch, destination_branch.id == OperationDocument.destination_branch_id)
            .join(Workstation, Workstation.id == OperationDocument.workstation_id)
            .join(User, User.id == OperationDocument.created_by_user_id)
            .outerjoin(
                receipt_document,
                (receipt_document.reference_document_id == OperationDocument.id)
                & (receipt_document.document_type == OPERATION_DOCUMENT_TYPE_BRANCH_TRANSFER_RECEIPT),
            )
            .outerjoin(receipt_user, receipt_user.id == receipt_document.created_by_user_id)
            .where(OperationDocument.document_type == OPERATION_DOCUMENT_TYPE_BRANCH_TRANSFER_SHIPMENT)
        )

        if date_from is not None:
            query = query.where(OperationDocument.created_at_utc >= date_from)
        if date_to is not None:
            query = query.where(OperationDocument.created_at_utc <= date_to)
        if origin_branch_id is not None:
            query = query.where(OperationDocument.source_branch_id == origin_branch_id)
        if destination_branch_id is not None:
            query = query.where(OperationDocument.destination_branch_id == destination_branch_id)
        if operator_user_id is not None:
            query = query.where(OperationDocument.created_by_user_id == operator_user_id)

        normalized_status = _normalize_optional(status_filter)
        if normalized_status and normalized_status != "all":
            if normalized_status not in VALID_ADMIN_TRANSFER_STATUSES:
                raise TransferValidationError("Transfer status filter is not supported.")
            query = query.where(OperationDocument.status == normalized_status)

        if product_id is not None:
            line_exists = exists().where(
                OperationDocumentLine.operation_document_id == OperationDocument.id,
                OperationDocumentLine.product_id == product_id,
            )
            query = query.where(line_exists)

        rows = session.execute(
            query.order_by(
                OperationDocument.committed_at_utc.desc().nullslast(),
                OperationDocument.created_at_utc.desc(),
            )
        ).all()

        return [
            _AdminTransferRow(
                created_by_user=created_by_user,
                destination_branch=destination,
                origin_branch=origin,
                receipt=receipt,
                receipt_created_by_user=receipt_user_record,
                shipment=shipment,
                workstation=workstation,
            )
            for shipment, origin, destination, workstation, created_by_user, receipt, receipt_user_record in rows
        ]

    def _get_row(self, session: Session, transfer_id: uuid.UUID) -> _AdminTransferRow:
        return next(
            (row for row in self._fetch_rows(
                session,
                date_from=None,
                date_to=None,
                destination_branch_id=None,
                operator_user_id=None,
                origin_branch_id=None,
                product_id=None,
                status_filter=None,
            ) if row.shipment.id == transfer_id),
            None,
        ) or self._raise_not_found()

    def _raise_not_found(self) -> _AdminTransferRow:
        raise TransferNotFoundError("Transfer was not found.")

    def _get_shipment(self, session: Session, transfer_id: uuid.UUID) -> OperationDocument:
        shipment = session.execute(
            select(OperationDocument).where(
                OperationDocument.id == transfer_id,
                OperationDocument.document_type == OPERATION_DOCUMENT_TYPE_BRANCH_TRANSFER_SHIPMENT,
            )
        ).scalar_one_or_none()
        if shipment is None:
            raise TransferNotFoundError("Transfer was not found.")
        return shipment

    def _get_receipt(self, session: Session, shipment_id: uuid.UUID) -> OperationDocument | None:
        return session.execute(
            select(OperationDocument).where(
                OperationDocument.reference_document_id == shipment_id,
                OperationDocument.document_type == OPERATION_DOCUMENT_TYPE_BRANCH_TRANSFER_RECEIPT,
            )
        ).scalar_one_or_none()

    def _get_branch(self, session: Session, branch_id: uuid.UUID) -> Branch:
        branch = session.get(Branch, branch_id)
        if branch is None:
            raise TransferValidationError("Branch was not found.")
        return branch

    def _get_active_workstation_for_branch(self, session: Session, branch_id: uuid.UUID) -> Workstation:
        workstation = session.execute(
            select(Workstation)
            .where(Workstation.branch_id == branch_id, Workstation.is_active.is_(True))
            .order_by(Workstation.code.asc())
            .limit(1)
        ).scalar_one_or_none()
        if workstation is None:
            raise TransferValidationError("Branch needs an active workstation before transfers can be managed.")
        return workstation

    def _validate_transfer_branches(
        self,
        origin_branch: Branch,
        destination_branch: Branch,
        *,
        for_dispatch: bool,
    ) -> None:
        if origin_branch.id == destination_branch.id:
            raise TransferValidationError("Origin and destination branches must differ.")
        if not origin_branch.is_active:
            raise TransferValidationError("Origin branch is inactive.")
        if for_dispatch and not destination_branch.is_active:
            raise TransferValidationError("Destination branch is inactive.")

    def _resolve_products(
        self,
        session: Session,
        lines: list[AdminTransferLineInput],
    ) -> dict[uuid.UUID, _ResolvedProduct]:
        product_ids = [line.product_id for line in lines]
        if len(product_ids) != len(set(product_ids)):
            raise TransferValidationError("Transfer lines cannot contain duplicate products.")

        records = session.execute(
            select(Product, ProductClass)
            .join(ProductClass, ProductClass.id == Product.product_class_id)
            .where(Product.id.in_(set(product_ids)))
        ).all()
        resolved = {product.id: _ResolvedProduct(product=product, product_class=product_class) for product, product_class in records}
        for product_id in product_ids:
            if product_id not in resolved:
                raise TransferValidationError("Product was not found.")
            if not resolved[product_id].product.is_active:
                raise TransferValidationError("Inactive products cannot be transferred.")
        return resolved

    def _replace_lines(
        self,
        session: Session,
        *,
        shipment: OperationDocument,
        lines: list[AdminTransferLineInput],
        resolved_products: dict[uuid.UUID, _ResolvedProduct],
    ) -> None:
        session.execute(delete(OperationDocumentLine).where(OperationDocumentLine.operation_document_id == shipment.id))
        session.flush()
        for line_number, line in enumerate(lines, start=1):
            resolved = resolved_products[line.product_id]
            session.add(
                OperationDocumentLine(
                    operation_document_id=shipment.id,
                    line_number=line_number,
                    product_id=line.product_id,
                    product_code_snapshot=resolved.product.code,
                    product_name_snapshot=resolved.product.name,
                    product_class_id=resolved.product_class.id,
                    product_class_code_snapshot=resolved.product_class.code,
                    product_class_name_snapshot=resolved.product_class.name,
                    quantity=line.quantity,
                    expected_quantity=line.quantity,
                    received_quantity=None,
                    unit_of_measure_code=resolved.product.unit_of_measure,
                    notes=line.notes,
                )
            )

    def _get_shipment_lines(self, session: Session, shipment_id: uuid.UUID) -> list[OperationDocumentLine]:
        return session.execute(
            select(OperationDocumentLine)
            .where(OperationDocumentLine.operation_document_id == shipment_id)
            .order_by(OperationDocumentLine.line_number.asc())
        ).scalars().all()

    def _get_receipt_lines_by_shipment_line_id(
        self,
        session: Session,
        receipt: OperationDocument | None,
    ) -> dict[uuid.UUID, OperationDocumentLine]:
        if receipt is None:
            return {}
        rows = session.execute(
            select(OperationDocumentLine)
            .where(OperationDocumentLine.operation_document_id == receipt.id)
            .order_by(OperationDocumentLine.line_number.asc())
        ).scalars().all()
        return {line.id: line for line in rows}

    def _validate_origin_stock(
        self,
        session: Session,
        *,
        shipment_lines: list[OperationDocumentLine],
        origin_branch_id: uuid.UUID,
    ) -> None:
        for line in shipment_lines:
            balance = self._get_balance(
                session,
                product_id=line.product_id,
                branch_id=origin_branch_id,
                location_code=INVENTORY_LOCATION_BACKROOM,
                for_update=True,
            )
            if balance is None or balance.quantity_on_hand < line.quantity:
                raise TransferValidationError(
                    f"Origin stock is insufficient for {line.product_code_snapshot}."
                )

    def _apply_dispatch_inventory(
        self,
        session: Session,
        *,
        current_user: AuthenticatedUser,
        destination_branch_id: uuid.UUID,
        shipment: OperationDocument,
        shipment_lines: list[OperationDocumentLine],
    ) -> None:
        for line in shipment_lines:
            self._apply_stock_delta(
                session,
                branch_id=shipment.source_branch_id,
                current_user=current_user,
                delta=-line.quantity,
                location_code=INVENTORY_LOCATION_BACKROOM,
                movement_type=INVENTORY_MOVEMENT_TYPE_TRANSFER_DISPATCH,
                notes=line.notes,
                product_id=line.product_id,
                reason="Transfer dispatch",
                source_document_id=shipment.id,
                source_document_type=TRANSFER_MOVEMENT_SOURCE_DISPATCH,
                unit_of_measure=line.unit_of_measure_code,
            )
            self._apply_stock_delta(
                session,
                branch_id=destination_branch_id,
                current_user=current_user,
                delta=line.quantity,
                location_code=INVENTORY_LOCATION_IN_TRANSIT,
                movement_type=INVENTORY_MOVEMENT_TYPE_TRANSFER_DISPATCH,
                notes=line.notes,
                product_id=line.product_id,
                reason="Transfer in transit",
                source_document_id=shipment.id,
                source_document_type=TRANSFER_MOVEMENT_SOURCE_DISPATCH,
                unit_of_measure=line.unit_of_measure_code,
            )

    def _apply_receipt_inventory(
        self,
        session: Session,
        *,
        current_user: AuthenticatedUser,
        receipt: OperationDocument,
        receipt_by_line_id: dict[uuid.UUID, object],
        shipment: OperationDocument,
        shipment_lines: list[OperationDocumentLine],
    ) -> None:
        if shipment.destination_branch_id is None:
            raise TransferValidationError("Transfer destination branch is missing.")
        for shipment_line in shipment_lines:
            receipt_line = receipt_by_line_id[shipment_line.id]
            self._apply_stock_delta(
                session,
                branch_id=shipment.destination_branch_id,
                current_user=current_user,
                delta=-shipment_line.quantity,
                location_code=INVENTORY_LOCATION_IN_TRANSIT,
                movement_type=INVENTORY_MOVEMENT_TYPE_TRANSFER_RECEIPT,
                notes=getattr(receipt_line, "notes", None),
                product_id=shipment_line.product_id,
                reason="Transfer receipt resolved in transit",
                source_document_id=receipt.id,
                source_document_type=TRANSFER_MOVEMENT_SOURCE_RECEIPT,
                unit_of_measure=shipment_line.unit_of_measure_code,
            )
            received_quantity = getattr(receipt_line, "received_quantity")
            if received_quantity > 0:
                self._apply_stock_delta(
                    session,
                    branch_id=shipment.destination_branch_id,
                    current_user=current_user,
                    delta=received_quantity,
                    location_code=INVENTORY_LOCATION_BACKROOM,
                    movement_type=INVENTORY_MOVEMENT_TYPE_TRANSFER_RECEIPT,
                    notes=getattr(receipt_line, "notes", None),
                    product_id=shipment_line.product_id,
                    reason=getattr(receipt_line, "variance_reason", None) or "Transfer receipt",
                    source_document_id=receipt.id,
                    source_document_type=TRANSFER_MOVEMENT_SOURCE_RECEIPT,
                    unit_of_measure=shipment_line.unit_of_measure_code,
                )

    def _apply_stock_delta(
        self,
        session: Session,
        *,
        branch_id: uuid.UUID,
        current_user: AuthenticatedUser,
        delta: Decimal,
        location_code: str,
        movement_type: str,
        notes: str | None,
        product_id: uuid.UUID,
        reason: str,
        source_document_id: uuid.UUID,
        source_document_type: str,
        unit_of_measure: str,
    ) -> None:
        if delta == 0:
            return
        balance = self._get_or_create_balance(
            session,
            product_id=product_id,
            branch_id=branch_id,
            location_code=location_code,
        )
        new_quantity = Decimal(balance.quantity_on_hand) + delta
        direction = INVENTORY_MOVEMENT_DIRECTION_IN if delta > 0 else INVENTORY_MOVEMENT_DIRECTION_OUT
        movement_quantity = abs(delta)
        balance.quantity_on_hand = new_quantity
        session.add(
            InventoryMovement(
                balance_after=new_quantity,
                branch_id=branch_id,
                direction=direction,
                location_code=location_code,
                movement_type=movement_type,
                notes=notes,
                operator_user_id=current_user.id,
                product_id=product_id,
                quantity=movement_quantity,
                reason=reason,
                source_document_id=source_document_id,
                source_document_type=source_document_type,
                unit_of_measure=unit_of_measure,
            )
        )

    def _get_balance(
        self,
        session: Session,
        *,
        branch_id: uuid.UUID,
        for_update: bool = False,
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
            product_id=product_id,
            branch_id=branch_id,
            location_code=location_code,
            for_update=True,
        )
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

    def _record_change(
        self,
        session: Session,
        *,
        action: str,
        current_user: AuthenticatedUser,
        event_name: str,
        metadata: dict[str, object],
        request_id: str | None,
        shipment: OperationDocument,
    ) -> None:
        self._audit_recorder.record(
            session,
            actor_id=current_user.id,
            action=action,
            resource_type=ADMIN_TRANSFER_RESOURCE_TYPE,
            resource_id=str(shipment.id),
            branch_id=shipment.source_branch_id,
            request_id=request_id,
            metadata={
                "document_type": shipment.document_type,
                "transfer_id": str(shipment.id),
                **metadata,
            },
        )
        self._outbox_writer.append(
            session,
            aggregate_type="transfer",
            aggregate_id=str(shipment.id),
            event_name=event_name,
            payload={
                "document_type": shipment.document_type,
                "transfer_id": str(shipment.id),
                **metadata,
            },
            headers={"request_id": request_id} if request_id else {},
        )

    def _to_list_item(self, session: Session, row: _AdminTransferRow) -> AdminTransferListItemView:
        shipment_lines = self._get_shipment_lines(session, row.shipment.id)
        receipt_lines = self._get_receipt_lines(session, row.receipt)
        sent_total = _sum_line_quantity(shipment_lines)
        received_total = _sum_received_quantity(receipt_lines) if row.receipt is not None else None
        has_discrepancy = self._has_discrepancy_from_lines(shipment_lines, receipt_lines)
        warnings = self._build_warnings(
            session,
            row=row,
            has_discrepancy=has_discrepancy,
            shipment_lines=shipment_lines,
        )
        return AdminTransferListItemView(
            created_at=row.shipment.created_at_utc,
            destination_branch_code=row.destination_branch.code,
            destination_branch_id=row.destination_branch.id,
            destination_branch_name=row.destination_branch.name,
            dispatched_at=row.shipment.committed_at_utc if row.shipment.status != OPERATION_DOCUMENT_STATUS_DRAFT else None,
            folio=_build_transfer_folio(row.shipment.id),
            has_discrepancy=has_discrepancy,
            id=row.shipment.id,
            line_count=len(shipment_lines),
            operator_name=row.created_by_user.full_name,
            origin_branch_code=row.origin_branch.code,
            origin_branch_id=row.origin_branch.id,
            origin_branch_name=row.origin_branch.name,
            received_at=row.receipt.committed_at_utc if row.receipt is not None else None,
            received_unit_count=received_total,
            requested_unit_count=sent_total,
            sent_unit_count=sent_total,
            status=row.shipment.status,
            warning_state=self._warning_state(warnings),
            warnings=warnings,
        )

    def _to_detail(self, session: Session, row: _AdminTransferRow) -> AdminTransferDetailView:
        shipment_lines = self._get_shipment_lines(session, row.shipment.id)
        receipt_lines = self._get_receipt_lines(session, row.receipt)
        lines = self._build_detail_lines(session, shipment_lines, receipt_lines)
        sent_total = _sum_line_quantity(shipment_lines)
        received_total = _sum_received_quantity(receipt_lines) if row.receipt is not None else None
        has_discrepancy = any(line.difference not in (None, Decimal("0")) for line in lines)
        warnings = self._build_warnings(
            session,
            row=row,
            has_discrepancy=has_discrepancy,
            shipment_lines=shipment_lines,
        )
        receipt_state = (
            "pending"
            if row.receipt is None and row.shipment.status == OPERATION_DOCUMENT_STATUS_IN_TRANSIT
            else "not_dispatched"
            if row.shipment.status == OPERATION_DOCUMENT_STATUS_DRAFT
            else "cancelled"
            if row.shipment.status == OPERATION_DOCUMENT_STATUS_CANCELLED
            else "received_with_discrepancy"
            if has_discrepancy
            else "received"
        )
        return AdminTransferDetailView(
            available_actions=AdminTransferAvailableActionsView(
                can_cancel=row.shipment.status == OPERATION_DOCUMENT_STATUS_DRAFT,
                can_dispatch=row.shipment.status == OPERATION_DOCUMENT_STATUS_DRAFT and len(shipment_lines) > 0,
                can_edit=row.shipment.status == OPERATION_DOCUMENT_STATUS_DRAFT,
                can_receive=row.shipment.status == OPERATION_DOCUMENT_STATUS_IN_TRANSIT,
                can_view_movements=True,
            ),
            destination=self._to_branch_view(row.destination_branch),
            inventory_impact=self._inventory_impact(session, row),
            lines=lines,
            origin=self._to_branch_view(row.origin_branch),
            overview=AdminTransferOverviewView(
                created_at=row.shipment.created_at_utc,
                created_by_user_id=row.created_by_user.id,
                created_by_user_name=row.created_by_user.full_name,
                dispatched_at=(
                    row.shipment.committed_at_utc
                    if row.shipment.status != OPERATION_DOCUMENT_STATUS_DRAFT
                    else None
                ),
                folio=_build_transfer_folio(row.shipment.id),
                has_discrepancy=has_discrepancy,
                id=row.shipment.id,
                line_count=len(shipment_lines),
                notes=row.shipment.notes,
                received_at=row.receipt.committed_at_utc if row.receipt else None,
                received_by_user_id=row.receipt_created_by_user.id if row.receipt_created_by_user else None,
                received_by_user_name=(
                    row.receipt_created_by_user.full_name if row.receipt_created_by_user else None
                ),
                received_unit_count=received_total,
                requested_unit_count=sent_total,
                sent_unit_count=sent_total,
                status=row.shipment.status,
            ),
            receipt=AdminTransferReceiptView(
                difference=(received_total - sent_total if received_total is not None else None),
                discrepancy_reason_required=has_discrepancy,
                expected_total_quantity=sent_total,
                has_discrepancy=has_discrepancy,
                receipt_document_id=row.receipt.id if row.receipt else None,
                received_total_quantity=received_total,
                state=receipt_state,
            ),
            related_documents=self._related_documents(row),
            warnings=warnings,
        )

    def _build_detail_lines(
        self,
        session: Session,
        shipment_lines: list[OperationDocumentLine],
        receipt_lines: list[OperationDocumentLine],
    ) -> list[AdminTransferLineView]:
        receipt_by_line_number = {line.line_number: line for line in receipt_lines}
        product_ids = {line.product_id for line in shipment_lines}
        products = {
            product.id: product
            for product in session.execute(select(Product).where(Product.id.in_(product_ids))).scalars().all()
        }
        views: list[AdminTransferLineView] = []
        for shipment_line in shipment_lines:
            receipt_line = receipt_by_line_number.get(shipment_line.line_number)
            received_quantity = receipt_line.received_quantity if receipt_line is not None else None
            difference = received_quantity - shipment_line.quantity if received_quantity is not None else None
            product = products.get(shipment_line.product_id)
            views.append(
                AdminTransferLineView(
                    difference=difference,
                    line_status=(
                        "pending_receipt"
                        if receipt_line is None
                        else "discrepancy"
                        if difference != Decimal("0")
                        else "matched"
                    ),
                    notes=(receipt_line.notes if receipt_line is not None else shipment_line.notes),
                    product_code=shipment_line.product_code_snapshot,
                    product_id=shipment_line.product_id,
                    product_kind=product.product_kind if product is not None else "UNKNOWN",
                    product_name=shipment_line.product_name_snapshot,
                    received_quantity=received_quantity,
                    requested_quantity=shipment_line.quantity,
                    sent_quantity=shipment_line.quantity,
                    shipment_line_id=shipment_line.id,
                    unit_of_measure=shipment_line.unit_of_measure_code,
                    variance_reason=receipt_line.variance_reason if receipt_line is not None else None,
                )
            )
        return views

    def _to_branch_view(self, branch: Branch) -> AdminTransferBranchView:
        return AdminTransferBranchView(
            branch_code=branch.code,
            branch_id=branch.id,
            branch_is_active=branch.is_active,
            branch_name=branch.name,
            timezone=branch.timezone,
        )

    def _inventory_impact(
        self,
        session: Session,
        row: _AdminTransferRow,
    ) -> AdminTransferInventoryImpactView:
        document_ids = [row.shipment.id]
        if row.receipt is not None:
            document_ids.append(row.receipt.id)
        movements = session.execute(
            select(InventoryMovement)
            .where(InventoryMovement.source_document_id.in_(document_ids))
            .order_by(InventoryMovement.occurred_at.asc())
        ).scalars().all()
        return AdminTransferInventoryImpactView(
            integration_available=True,
            movements=[
                AdminTransferInventoryMovementView(
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
            notes=None if movements else "No hay movimientos de inventario vinculados a esta transferencia.",
        )

    def _related_documents(self, row: _AdminTransferRow) -> list[AdminTransferRelatedDocumentView]:
        documents = [
            AdminTransferRelatedDocumentView(
                document_id=row.shipment.id,
                document_type=row.shipment.document_type,
                folio=_build_transfer_folio(row.shipment.id),
                status=row.shipment.status,
            )
        ]
        if row.receipt is not None:
            documents.append(
                AdminTransferRelatedDocumentView(
                    document_id=row.receipt.id,
                    document_type=row.receipt.document_type,
                    folio=_build_receipt_folio(row.receipt.id),
                    status=row.receipt.status,
                )
            )
        return documents

    def _build_metrics(self, session: Session, rows: list[_AdminTransferRow]) -> AdminTransferMetricsView:
        in_transit_rows = [row for row in rows if row.shipment.status == OPERATION_DOCUMENT_STATUS_IN_TRANSIT]
        return AdminTransferMetricsView(
            cancelled_transfers=sum(1 for row in rows if row.shipment.status == OPERATION_DOCUMENT_STATUS_CANCELLED),
            in_transit_transfers=len(in_transit_rows),
            pending_receipt_transfers=len(in_transit_rows),
            received_transfers=sum(
                1
                for row in rows
                if row.shipment.status
                in (OPERATION_DOCUMENT_STATUS_RECEIVED, OPERATION_DOCUMENT_STATUS_RECEIVED_WITH_VARIANCE)
            ),
            total_transfers=len(rows),
            units_in_transit=sum(
                (_sum_line_quantity(self._get_shipment_lines(session, row.shipment.id)) for row in in_transit_rows),
                Decimal("0"),
            ),
            with_discrepancies=sum(1 for row in rows if self._has_discrepancy(session, row)),
        )

    def _build_filter_options(self, session: Session) -> AdminTransferFilterOptionsView:
        branches = session.execute(select(Branch).order_by(Branch.name.asc(), Branch.code.asc())).scalars().all()
        operators = session.execute(select(User).order_by(User.full_name.asc(), User.email.asc())).scalars().all()
        products = session.execute(select(Product).order_by(Product.name.asc(), Product.code.asc())).scalars().all()
        return AdminTransferFilterOptionsView(
            branches=[
                AdminTransferFilterOptionView(id=branch.id, label=f"{branch.name} - {branch.code}")
                for branch in branches
            ],
            operators=[
                AdminTransferFilterOptionView(id=user.id, label=user.full_name)
                for user in operators
            ],
            products=[
                AdminTransferFilterOptionView(id=product.id, label=f"{product.name} - {product.code}")
                for product in products
            ],
            statuses=[
                AdminTransferFilterOptionView(id=status, label=_status_label(status))
                for status in (
                    OPERATION_DOCUMENT_STATUS_DRAFT,
                    OPERATION_DOCUMENT_STATUS_IN_TRANSIT,
                    OPERATION_DOCUMENT_STATUS_RECEIVED,
                    OPERATION_DOCUMENT_STATUS_RECEIVED_WITH_VARIANCE,
                    OPERATION_DOCUMENT_STATUS_CANCELLED,
                )
            ],
        )

    def _build_warnings(
        self,
        session: Session,
        *,
        has_discrepancy: bool,
        row: _AdminTransferRow,
        shipment_lines: list[OperationDocumentLine],
    ) -> list[AdminTransferWarningView]:
        warnings: list[AdminTransferWarningView] = []
        if not row.origin_branch.is_active:
            warnings.append(
                AdminTransferWarningView(
                    code="inactive_origin",
                    message="La sucursal origen esta inactiva.",
                    severity="critical",
                )
            )
        if not row.destination_branch.is_active:
            warnings.append(
                AdminTransferWarningView(
                    code="inactive_destination",
                    message="La sucursal destino esta inactiva.",
                    severity="warning",
                )
            )
        if row.shipment.status == OPERATION_DOCUMENT_STATUS_DRAFT and not shipment_lines:
            warnings.append(
                AdminTransferWarningView(
                    code="empty_draft",
                    message="El borrador no tiene productos capturados.",
                    severity="critical",
                )
            )
        if row.shipment.status == OPERATION_DOCUMENT_STATUS_IN_TRANSIT:
            warnings.append(
                AdminTransferWarningView(
                    code="pending_receipt",
                    message="La transferencia esta enviada y pendiente de recepcion.",
                    severity="warning",
                )
            )
        if has_discrepancy:
            warnings.append(
                AdminTransferWarningView(
                    code="quantity_discrepancy",
                    message="Existen diferencias entre cantidades enviadas y recibidas.",
                    severity="critical",
                )
            )
        if row.shipment.status == OPERATION_DOCUMENT_STATUS_DRAFT:
            for line in shipment_lines:
                balance = self._get_balance(
                    session,
                    product_id=line.product_id,
                    branch_id=row.origin_branch.id,
                    location_code=INVENTORY_LOCATION_BACKROOM,
                )
                if balance is None or balance.quantity_on_hand < line.quantity:
                    warnings.append(
                        AdminTransferWarningView(
                            code="insufficient_origin_stock",
                            message=(
                                f"Stock origen insuficiente para {line.product_code_snapshot}."
                            ),
                            severity="warning",
                        )
                    )
                    break
        return warnings

    def _warning_state(
        self,
        warnings: list[AdminTransferWarningView],
    ) -> AdminTransferWarningSeverity | None:
        if any(warning.severity == "critical" for warning in warnings):
            return "critical"
        if any(warning.severity == "warning" for warning in warnings):
            return "warning"
        if warnings:
            return "info"
        return None

    def _has_discrepancy(self, session: Session, row: _AdminTransferRow) -> bool:
        shipment_lines = self._get_shipment_lines(session, row.shipment.id)
        receipt_lines = self._get_receipt_lines(session, row.receipt)
        return self._has_discrepancy_from_lines(shipment_lines, receipt_lines)

    def _has_discrepancy_from_lines(
        self,
        shipment_lines: list[OperationDocumentLine],
        receipt_lines: list[OperationDocumentLine],
    ) -> bool:
        if not receipt_lines:
            return False
        receipt_by_line_number = {line.line_number: line for line in receipt_lines}
        return any(
            receipt_by_line_number.get(line.line_number) is not None
            and receipt_by_line_number[line.line_number].received_quantity != line.quantity
            for line in shipment_lines
        )

    def _get_receipt_lines(
        self,
        session: Session,
        receipt: OperationDocument | None,
    ) -> list[OperationDocumentLine]:
        if receipt is None:
            return []
        return session.execute(
            select(OperationDocumentLine)
            .where(OperationDocumentLine.operation_document_id == receipt.id)
            .order_by(OperationDocumentLine.line_number.asc())
        ).scalars().all()

    def _matches_search(self, row: _AdminTransferRow, search: str) -> bool:
        haystack = " ".join(
            [
                _build_transfer_folio(row.shipment.id),
                row.origin_branch.code,
                row.origin_branch.name,
                row.destination_branch.code,
                row.destination_branch.name,
                row.created_by_user.full_name,
                row.shipment.status,
            ]
        ).lower()
        return search.lower() in haystack


def _build_transfer_folio(document_id: uuid.UUID) -> str:
    return f"ENV-{str(document_id).split('-', maxsplit=1)[0].upper()}"


def _build_receipt_folio(document_id: uuid.UUID) -> str:
    return f"REC-{str(document_id).split('-', maxsplit=1)[0].upper()}"


def _normalize_optional(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def _status_label(status: str) -> str:
    return {
        OPERATION_DOCUMENT_STATUS_CANCELLED: "Cancelada",
        OPERATION_DOCUMENT_STATUS_DRAFT: "Borrador",
        OPERATION_DOCUMENT_STATUS_IN_TRANSIT: "En transito",
        OPERATION_DOCUMENT_STATUS_RECEIVED: "Recibida",
        OPERATION_DOCUMENT_STATUS_RECEIVED_WITH_VARIANCE: "Recibida con diferencia",
    }.get(status, status)


def _sum_line_quantity(lines: list[OperationDocumentLine]) -> Decimal:
    return sum((line.quantity for line in lines), Decimal("0"))


def _sum_received_quantity(lines: list[OperationDocumentLine]) -> Decimal:
    return sum((line.received_quantity or Decimal("0") for line in lines), Decimal("0"))
