from __future__ import annotations

import uuid
from dataclasses import dataclass

from pydantic import TypeAdapter
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
from zeromerma_api.modules.catalog.infrastructure.models import Product, ProductClass
from zeromerma_api.modules.identity.application.schemas import AuthenticatedUser
from zeromerma_api.modules.outbox.application.service import OutboxWriter
from zeromerma_api.modules.suppliers.application.admin_schemas import (
    AdminSupplierAvailableActionsView,
    AdminSupplierBranchApplicabilityView,
    AdminSupplierBranchRequest,
    AdminSupplierCommercialTermsView,
    AdminSupplierContactRequest,
    AdminSupplierContactView,
    AdminSupplierCreateRequest,
    AdminSupplierDetailView,
    AdminSupplierFilterOptionsView,
    AdminSupplierFilterOptionView,
    AdminSupplierFiscalLegalView,
    AdminSupplierListItemView,
    AdminSupplierListResponse,
    AdminSupplierMetricsView,
    AdminSupplierOperationalActivityView,
    AdminSupplierOverviewView,
    AdminSupplierProductAssociationView,
    AdminSupplierProductRequest,
    AdminSupplierRelatedDocumentView,
    AdminSupplierStatus,
    AdminSupplierStatusRequest,
    AdminSupplierUpdateRequest,
    AdminSupplierWarningSeverity,
    AdminSupplierWarningView,
)
from zeromerma_api.modules.suppliers.domain.constants import (
    AUDIT_ACTION_ADMIN_SUPPLIER_CONTACT_CREATED,
    AUDIT_ACTION_ADMIN_SUPPLIER_CONTACT_UPDATED,
    AUDIT_ACTION_ADMIN_SUPPLIER_CREATED,
    AUDIT_ACTION_ADMIN_SUPPLIER_PRODUCT_LINKED,
    AUDIT_ACTION_ADMIN_SUPPLIER_PRODUCT_UPDATED,
    AUDIT_ACTION_ADMIN_SUPPLIER_STATUS_CHANGED,
    AUDIT_ACTION_ADMIN_SUPPLIER_UPDATED,
    OUTBOX_EVENT_ADMIN_SUPPLIER_CREATED_V1,
    OUTBOX_EVENT_ADMIN_SUPPLIER_STATUS_CHANGED_V1,
    OUTBOX_EVENT_ADMIN_SUPPLIER_UPDATED_V1,
    SUPPLIER_CATEGORY_MIXED,
    SUPPLIER_CATEGORY_OTHER,
    SUPPLIER_CATEGORY_PACKAGING,
    SUPPLIER_CATEGORY_RAW_MATERIALS,
    SUPPLIER_CATEGORY_SERVICES,
    SUPPLIER_PAYMENT_TERMS_CASH,
    SUPPLIER_PAYMENT_TERMS_CREDIT,
    SUPPLIER_PAYMENT_TERMS_MIXED,
    SUPPLIER_PAYMENT_TERMS_TRANSFER,
    SUPPLIER_RESOURCE_TYPE,
    SUPPLIER_STATUS_ACTIVE,
    SUPPLIER_STATUS_BLOCKED,
    SUPPLIER_STATUS_INACTIVE,
    VALID_SUPPLIER_CATEGORIES,
    VALID_SUPPLIER_PAYMENT_TERMS,
    VALID_SUPPLIER_STATUSES,
)
from zeromerma_api.modules.suppliers.domain.exceptions import (
    SupplierNotFoundError,
    SupplierValidationError,
)
from zeromerma_api.modules.suppliers.infrastructure.models import (
    Supplier,
    SupplierBranch,
    SupplierContact,
    SupplierProduct,
)

_ADMIN_SUPPLIER_STATUS_ADAPTER: TypeAdapter[AdminSupplierStatus] = TypeAdapter(AdminSupplierStatus)
PRODUCT_KIND_LABELS = {
    CATALOG_PRODUCT_KIND_FINISHED_GOOD: "Producto terminado",
    CATALOG_PRODUCT_KIND_RAW_MATERIAL: "Materia prima",
    CATALOG_PRODUCT_KIND_CONSUMABLE: "Consumible",
    CATALOG_PRODUCT_KIND_DISPOSABLE: "Desechable",
}

SUPPLIER_CATEGORY_LABELS = {
    SUPPLIER_CATEGORY_RAW_MATERIALS: "Materia prima",
    SUPPLIER_CATEGORY_PACKAGING: "Empaque / desechables",
    SUPPLIER_CATEGORY_SERVICES: "Servicios",
    SUPPLIER_CATEGORY_MIXED: "Mixto",
    SUPPLIER_CATEGORY_OTHER: "Otro",
}

SUPPLIER_STATUS_LABELS = {
    SUPPLIER_STATUS_ACTIVE: "Activo",
    SUPPLIER_STATUS_INACTIVE: "Inactivo",
    SUPPLIER_STATUS_BLOCKED: "Bloqueado",
}

SUPPLIER_PAYMENT_TERMS_LABELS = {
    SUPPLIER_PAYMENT_TERMS_CASH: "Contado",
    SUPPLIER_PAYMENT_TERMS_CREDIT: "Credito",
    SUPPLIER_PAYMENT_TERMS_TRANSFER: "Transferencia",
    SUPPLIER_PAYMENT_TERMS_MIXED: "Mixto",
}


@dataclass(frozen=True)
class _SupplierRow:
    branches: list[tuple[SupplierBranch, Branch]]
    contacts: list[SupplierContact]
    products: list[tuple[SupplierProduct, Product, ProductClass]]
    supplier: Supplier


class AdminSupplierService:
    def __init__(
        self,
        audit_recorder: AuditRecorder | None = None,
        outbox_writer: OutboxWriter | None = None,
    ) -> None:
        self._audit_recorder = audit_recorder or AuditRecorder()
        self._outbox_writer = outbox_writer or OutboxWriter()

    def list_suppliers(
        self,
        session: Session,
        *,
        branch_id: uuid.UUID | None,
        category: str | None,
        product_kind: str | None,
        search: str | None,
        status_filter: str | None,
        warning_state: str | None,
        page: int,
        page_size: int,
    ) -> AdminSupplierListResponse:
        rows = self._fetch_rows(session)

        normalized_status = _normalize_optional(status_filter)
        if normalized_status and normalized_status != "all":
            rows = [row for row in rows if row.supplier.status == normalized_status]

        normalized_category = _normalize_optional(category)
        if normalized_category and normalized_category != "all":
            rows = [row for row in rows if row.supplier.category == normalized_category]

        if branch_id is not None:
            rows = [
                row
                for row in rows
                if any(
                    branch.branch_id == branch_id and branch.is_active for branch, _ in row.branches
                )
            ]

        normalized_kind = _normalize_optional(product_kind)
        if normalized_kind and normalized_kind != "all":
            rows = [
                row
                for row in rows
                if any(
                    product.product_kind == normalized_kind and relation.is_active
                    for relation, product, _ in row.products
                )
            ]

        normalized_search = _normalize_optional(search)
        if normalized_search:
            rows = [row for row in rows if self._matches_search(row, normalized_search)]

        normalized_warning = _normalize_optional(warning_state)
        if normalized_warning == "with_warnings":
            rows = [row for row in rows if self._build_warnings(row)]
        elif normalized_warning == "without_warnings":
            rows = [row for row in rows if not self._build_warnings(row)]

        items = [self._to_list_item(row) for row in rows]
        total = len(items)
        safe_page = max(page, 1)
        safe_page_size = min(max(page_size, 1), 100)
        offset = (safe_page - 1) * safe_page_size

        return AdminSupplierListResponse(
            filter_options=self._build_filter_options(session),
            items=items[offset : offset + safe_page_size],
            metrics=self._build_metrics(rows),
            page=safe_page,
            page_size=safe_page_size,
            total=total,
        )

    def get_supplier_detail(
        self, session: Session, *, supplier_id: uuid.UUID
    ) -> AdminSupplierDetailView:
        return self._to_detail(self._get_row(session, supplier_id))

    def create_supplier(
        self,
        session: Session,
        *,
        command: AdminSupplierCreateRequest,
        current_user: AuthenticatedUser,
        request_id: str | None,
    ) -> AdminSupplierDetailView:
        self._validate_supplier_command(command)
        code = (
            self._normalize_supplier_code(command.code)
            if command.code
            else self._generate_supplier_code(session)
        )
        self._ensure_unique_code(session, code)
        if command.tax_id:
            self._ensure_unique_tax_id(session, command.tax_id)

        supplier = Supplier(
            category=command.category,
            code=code,
            commercial_name=command.commercial_name,
            credit_days=command.credit_days,
            default_currency=command.default_currency,
            delivery_notes=command.delivery_notes,
            fiscal_address=command.fiscal_address,
            fiscal_regime=command.fiscal_regime,
            lead_time_days=command.lead_time_days,
            legal_name=command.legal_name.strip(),
            minimum_order_amount=command.minimum_order_amount,
            notes=command.notes,
            payment_fiscal_email=command.payment_fiscal_email,
            payment_terms_type=command.payment_terms_type,
            purchase_notes=command.purchase_notes,
            status=command.status,
            tax_id=command.tax_id,
        )

        try:
            session.add(supplier)
            session.flush()
            self._replace_contacts(session, supplier=supplier, contacts=command.contacts)
            self._upsert_product_relations(
                session, supplier=supplier, relations=command.product_relations
            )
            self._replace_branch_relations(
                session, supplier=supplier, branch_ids=command.branch_ids
            )
            self._record_change(
                session,
                action=AUDIT_ACTION_ADMIN_SUPPLIER_CREATED,
                event_name=OUTBOX_EVENT_ADMIN_SUPPLIER_CREATED_V1,
                current_user=current_user,
                metadata=self._metadata(supplier),
                request_id=request_id,
                supplier=supplier,
            )
            session.commit()
        except IntegrityError as error:
            session.rollback()
            raise SupplierValidationError("Supplier code or tax id must be unique.") from error

        return self.get_supplier_detail(session, supplier_id=supplier.id)

    def update_supplier(
        self,
        session: Session,
        *,
        command: AdminSupplierUpdateRequest,
        current_user: AuthenticatedUser,
        request_id: str | None,
        supplier_id: uuid.UUID,
    ) -> AdminSupplierDetailView:
        self._validate_supplier_command(command)
        row = self._get_row(session, supplier_id)
        supplier = row.supplier
        code = self._normalize_supplier_code(command.code) if command.code else supplier.code
        if code != supplier.code:
            self._ensure_unique_code(session, code)
        if command.tax_id and command.tax_id != supplier.tax_id:
            self._ensure_unique_tax_id(session, command.tax_id)

        supplier.category = command.category
        supplier.code = code
        supplier.commercial_name = command.commercial_name
        supplier.credit_days = command.credit_days
        supplier.default_currency = command.default_currency
        supplier.delivery_notes = command.delivery_notes
        supplier.fiscal_address = command.fiscal_address
        supplier.fiscal_regime = command.fiscal_regime
        supplier.lead_time_days = command.lead_time_days
        supplier.legal_name = command.legal_name.strip()
        supplier.minimum_order_amount = command.minimum_order_amount
        supplier.notes = command.notes
        supplier.payment_fiscal_email = command.payment_fiscal_email
        supplier.payment_terms_type = command.payment_terms_type
        supplier.purchase_notes = command.purchase_notes
        supplier.status = command.status
        supplier.tax_id = command.tax_id

        try:
            self._replace_contacts(session, supplier=supplier, contacts=command.contacts)
            self._upsert_product_relations(
                session, supplier=supplier, relations=command.product_relations
            )
            self._replace_branch_relations(
                session, supplier=supplier, branch_ids=command.branch_ids
            )
            self._record_change(
                session,
                action=AUDIT_ACTION_ADMIN_SUPPLIER_UPDATED,
                event_name=OUTBOX_EVENT_ADMIN_SUPPLIER_UPDATED_V1,
                current_user=current_user,
                metadata=self._metadata(supplier),
                request_id=request_id,
                supplier=supplier,
            )
            session.commit()
        except IntegrityError as error:
            session.rollback()
            raise SupplierValidationError("Supplier code or tax id must be unique.") from error

        return self.get_supplier_detail(session, supplier_id=supplier.id)

    def change_status(
        self,
        session: Session,
        *,
        command: AdminSupplierStatusRequest,
        current_user: AuthenticatedUser,
        request_id: str | None,
        supplier_id: uuid.UUID,
    ) -> AdminSupplierDetailView:
        if command.status not in VALID_SUPPLIER_STATUSES:
            raise SupplierValidationError("Supplier status is not supported.")
        supplier = self._get_supplier(session, supplier_id)
        supplier.status = command.status
        if command.notes:
            supplier.notes = command.notes
        self._record_change(
            session,
            action=AUDIT_ACTION_ADMIN_SUPPLIER_STATUS_CHANGED,
            event_name=OUTBOX_EVENT_ADMIN_SUPPLIER_STATUS_CHANGED_V1,
            current_user=current_user,
            metadata={**self._metadata(supplier), "status_notes": command.notes},
            request_id=request_id,
            supplier=supplier,
        )
        session.commit()
        return self.get_supplier_detail(session, supplier_id=supplier.id)

    def create_contact(
        self,
        session: Session,
        *,
        command: AdminSupplierContactRequest,
        current_user: AuthenticatedUser,
        request_id: str | None,
        supplier_id: uuid.UUID,
    ) -> AdminSupplierDetailView:
        supplier = self._get_supplier(session, supplier_id)
        self._upsert_contact(session, supplier=supplier, command=command)
        self._record_audit_only(
            session,
            action=AUDIT_ACTION_ADMIN_SUPPLIER_CONTACT_CREATED,
            current_user=current_user,
            metadata=self._metadata(supplier),
            request_id=request_id,
            supplier=supplier,
        )
        session.commit()
        return self.get_supplier_detail(session, supplier_id=supplier.id)

    def update_contact(
        self,
        session: Session,
        *,
        command: AdminSupplierContactRequest,
        contact_id: uuid.UUID,
        current_user: AuthenticatedUser,
        request_id: str | None,
        supplier_id: uuid.UUID,
    ) -> AdminSupplierDetailView:
        supplier = self._get_supplier(session, supplier_id)
        contact = session.get(SupplierContact, contact_id)
        if contact is None or contact.supplier_id != supplier.id:
            raise SupplierNotFoundError("Supplier contact was not found.")
        self._apply_contact(contact, command)
        if command.is_primary:
            self._clear_other_primary_contacts(
                session, supplier_id=supplier.id, except_contact_id=contact.id
            )
        self._record_audit_only(
            session,
            action=AUDIT_ACTION_ADMIN_SUPPLIER_CONTACT_UPDATED,
            current_user=current_user,
            metadata=self._metadata(supplier),
            request_id=request_id,
            supplier=supplier,
        )
        session.commit()
        return self.get_supplier_detail(session, supplier_id=supplier.id)

    def upsert_product_relation(
        self,
        session: Session,
        *,
        command: AdminSupplierProductRequest,
        current_user: AuthenticatedUser,
        request_id: str | None,
        supplier_id: uuid.UUID,
    ) -> AdminSupplierDetailView:
        supplier = self._get_supplier(session, supplier_id)
        created = self._upsert_product_relation(session, supplier=supplier, command=command)
        self._record_audit_only(
            session,
            action=AUDIT_ACTION_ADMIN_SUPPLIER_PRODUCT_LINKED
            if created
            else AUDIT_ACTION_ADMIN_SUPPLIER_PRODUCT_UPDATED,
            current_user=current_user,
            metadata={
                **self._metadata(supplier),
                "product_id": str(command.product_id),
                "is_active": command.is_active,
            },
            request_id=request_id,
            supplier=supplier,
        )
        session.commit()
        return self.get_supplier_detail(session, supplier_id=supplier.id)

    def update_product_relation(
        self,
        session: Session,
        *,
        command: AdminSupplierProductRequest,
        current_user: AuthenticatedUser,
        relation_id: uuid.UUID,
        request_id: str | None,
        supplier_id: uuid.UUID,
    ) -> AdminSupplierDetailView:
        supplier = self._get_supplier(session, supplier_id)
        relation = session.get(SupplierProduct, relation_id)
        if relation is None or relation.supplier_id != supplier.id:
            raise SupplierNotFoundError("Supplier product relation was not found.")
        self._apply_product_relation(
            relation, command, self._get_product(session, command.product_id)
        )
        self._record_audit_only(
            session,
            action=AUDIT_ACTION_ADMIN_SUPPLIER_PRODUCT_UPDATED,
            current_user=current_user,
            metadata={
                **self._metadata(supplier),
                "relation_id": str(relation.id),
                "is_active": relation.is_active,
            },
            request_id=request_id,
            supplier=supplier,
        )
        session.commit()
        return self.get_supplier_detail(session, supplier_id=supplier.id)

    def upsert_branch_relation(
        self,
        session: Session,
        *,
        command: AdminSupplierBranchRequest,
        current_user: AuthenticatedUser,
        request_id: str | None,
        supplier_id: uuid.UUID,
    ) -> AdminSupplierDetailView:
        supplier = self._get_supplier(session, supplier_id)
        branch = self._get_branch(session, command.branch_id)
        relation = session.execute(
            select(SupplierBranch).where(
                SupplierBranch.supplier_id == supplier.id, SupplierBranch.branch_id == branch.id
            ),
        ).scalar_one_or_none()
        if relation is None:
            relation = SupplierBranch(
                branch_id=branch.id,
                delivery_notes=command.delivery_notes,
                is_active=command.is_active,
                supplier_id=supplier.id,
            )
            session.add(relation)
        else:
            relation.delivery_notes = command.delivery_notes
            relation.is_active = command.is_active
        self._record_audit_only(
            session,
            action=AUDIT_ACTION_ADMIN_SUPPLIER_UPDATED,
            current_user=current_user,
            metadata={
                **self._metadata(supplier),
                "branch_id": str(branch.id),
                "branch_relation_active": relation.is_active,
            },
            request_id=request_id,
            supplier=supplier,
        )
        session.commit()
        return self.get_supplier_detail(session, supplier_id=supplier.id)

    def _fetch_rows(self, session: Session) -> list[_SupplierRow]:
        suppliers = (
            session.execute(
                select(Supplier).order_by(Supplier.legal_name.asc(), Supplier.code.asc())
            )
            .scalars()
            .all()
        )
        return [self._row_from_supplier(session, supplier) for supplier in suppliers]

    def _get_row(self, session: Session, supplier_id: uuid.UUID) -> _SupplierRow:
        supplier = self._get_supplier(session, supplier_id)
        return self._row_from_supplier(session, supplier)

    def _row_from_supplier(self, session: Session, supplier: Supplier) -> _SupplierRow:
        contacts = (
            session.execute(
                select(SupplierContact)
                .where(SupplierContact.supplier_id == supplier.id)
                .order_by(SupplierContact.is_primary.desc(), SupplierContact.name.asc()),
            )
            .scalars()
            .all()
        )
        products = (
            session.execute(
                select(SupplierProduct, Product, ProductClass)
                .join(Product, Product.id == SupplierProduct.product_id)
                .join(ProductClass, ProductClass.id == Product.product_class_id)
                .where(SupplierProduct.supplier_id == supplier.id)
                .order_by(Product.name.asc(), Product.code.asc()),
            )
            .tuples()
            .all()
        )
        branches = (
            session.execute(
                select(SupplierBranch, Branch)
                .join(Branch, Branch.id == SupplierBranch.branch_id)
                .where(SupplierBranch.supplier_id == supplier.id)
                .order_by(Branch.name.asc(), Branch.code.asc()),
            )
            .tuples()
            .all()
        )
        return _SupplierRow(
            branches=list(branches),
            contacts=list(contacts),
            products=list(products),
            supplier=supplier,
        )

    def _to_list_item(self, row: _SupplierRow) -> AdminSupplierListItemView:
        primary_contact = self._primary_contact(row)
        warnings = self._build_warnings(row)
        return AdminSupplierListItemView(
            branch_count=sum(1 for relation, _ in row.branches if relation.is_active),
            category=row.supplier.category,
            code=row.supplier.code,
            commercial_name=row.supplier.commercial_name,
            id=row.supplier.id,
            legal_name=row.supplier.legal_name,
            primary_contact_email=primary_contact.email if primary_contact else None,
            primary_contact_name=primary_contact.name if primary_contact else None,
            primary_contact_phone=primary_contact.phone if primary_contact else None,
            product_count=sum(1 for relation, _, _ in row.products if relation.is_active),
            status=_ADMIN_SUPPLIER_STATUS_ADAPTER.validate_python(row.supplier.status),
            tax_id=row.supplier.tax_id,
            terms_summary=self._terms_summary(row.supplier),
            updated_at=row.supplier.updated_at,
            warning_state=self._warning_state(warnings),
            warnings=warnings,
        )

    def _to_detail(self, row: _SupplierRow) -> AdminSupplierDetailView:
        warnings = self._build_warnings(row)
        return AdminSupplierDetailView(
            available_actions=AdminSupplierAvailableActionsView(),
            branch_applicability=[
                AdminSupplierBranchApplicabilityView(
                    branch_code=branch.code,
                    branch_id=branch.id,
                    branch_name=branch.name,
                    branch_status="active" if branch.is_active else "inactive",
                    delivery_notes=relation.delivery_notes,
                    is_active=relation.is_active,
                )
                for relation, branch in row.branches
            ],
            commercial_terms=AdminSupplierCommercialTermsView(
                credit_days=row.supplier.credit_days,
                default_currency=row.supplier.default_currency,
                delivery_notes=row.supplier.delivery_notes,
                lead_time_days=row.supplier.lead_time_days,
                minimum_order_amount=row.supplier.minimum_order_amount,
                payment_terms_type=row.supplier.payment_terms_type,
                purchase_notes=row.supplier.purchase_notes,
                summary=self._terms_summary(row.supplier),
            ),
            contacts=[
                AdminSupplierContactView(
                    email=contact.email,
                    id=contact.id,
                    is_active=contact.is_active,
                    is_primary=contact.is_primary,
                    name=contact.name,
                    notes=contact.notes,
                    phone=contact.phone,
                    role=contact.role,
                    whatsapp=contact.whatsapp,
                )
                for contact in row.contacts
            ],
            fiscal_legal=AdminSupplierFiscalLegalView(
                fiscal_address=row.supplier.fiscal_address,
                fiscal_regime=row.supplier.fiscal_regime,
                legal_name=row.supplier.legal_name,
                notes=row.supplier.notes,
                payment_fiscal_email=row.supplier.payment_fiscal_email,
                tax_id=row.supplier.tax_id,
            ),
            operational_activity=AdminSupplierOperationalActivityView(),
            overview=AdminSupplierOverviewView(
                category=row.supplier.category,
                code=row.supplier.code,
                commercial_name=row.supplier.commercial_name,
                created_at=row.supplier.created_at,
                id=row.supplier.id,
                legal_name=row.supplier.legal_name,
                readiness_state=self._warning_state(warnings),
                status=_ADMIN_SUPPLIER_STATUS_ADAPTER.validate_python(row.supplier.status),
                tax_id=row.supplier.tax_id,
                updated_at=row.supplier.updated_at,
            ),
            product_associations=[
                AdminSupplierProductAssociationView(
                    conversion_factor=relation.conversion_factor,
                    currency=relation.currency,
                    id=relation.id,
                    is_active=relation.is_active,
                    last_known_price=relation.last_known_price,
                    lead_time_days=relation.lead_time_days,
                    minimum_order_qty=relation.minimum_order_qty,
                    notes=relation.notes,
                    product_code=product.code,
                    product_id=product.id,
                    product_kind=product.product_kind,
                    product_name=product.name,
                    purchase_uom=relation.purchase_uom or product.unit_of_measure,
                    supplier_sku=relation.supplier_sku,
                )
                for relation, product, _ in row.products
            ],
            related_documents=self._related_documents(row),
            warnings=warnings,
        )

    def _build_filter_options(self, session: Session) -> AdminSupplierFilterOptionsView:
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
        return AdminSupplierFilterOptionsView(
            branches=[
                AdminSupplierFilterOptionView(
                    id=str(branch.id), label=f"{branch.name} - {branch.code}"
                )
                for branch in branches
            ],
            categories=[
                AdminSupplierFilterOptionView(id=code, label=label)
                for code, label in SUPPLIER_CATEGORY_LABELS.items()
            ],
            product_kinds=[
                AdminSupplierFilterOptionView(id=code, label=label)
                for code, label in PRODUCT_KIND_LABELS.items()
            ],
            products=[
                AdminSupplierFilterOptionView(
                    id=str(product.id), label=f"{product.name} - {product.code}"
                )
                for product in products
            ],
            statuses=[
                AdminSupplierFilterOptionView(id=code, label=label)
                for code, label in SUPPLIER_STATUS_LABELS.items()
            ],
            warning_states=[
                AdminSupplierFilterOptionView(id="with_warnings", label="Con advertencias"),
                AdminSupplierFilterOptionView(id="without_warnings", label="Sin advertencias"),
            ],
        )

    def _build_metrics(self, rows: list[_SupplierRow]) -> AdminSupplierMetricsView:
        return AdminSupplierMetricsView(
            active_suppliers=sum(
                1 for row in rows if row.supplier.status == SUPPLIER_STATUS_ACTIVE
            ),
            blocked_suppliers=sum(
                1 for row in rows if row.supplier.status == SUPPLIER_STATUS_BLOCKED
            ),
            inactive_suppliers=sum(
                1 for row in rows if row.supplier.status == SUPPLIER_STATUS_INACTIVE
            ),
            suppliers_with_recent_activity=0,
            suppliers_with_warnings=sum(1 for row in rows if self._build_warnings(row)),
            suppliers_without_products=sum(
                1 for row in rows if not any(relation.is_active for relation, _, _ in row.products)
            ),
            total_suppliers=len(rows),
        )

    def _build_warnings(self, row: _SupplierRow) -> list[AdminSupplierWarningView]:
        warnings: list[AdminSupplierWarningView] = []
        if row.supplier.status == SUPPLIER_STATUS_BLOCKED:
            warnings.append(
                AdminSupplierWarningView(
                    code="blocked_supplier",
                    message="Proveedor bloqueado para nuevas compras.",
                    severity="critical",
                )
            )
        if row.supplier.status == SUPPLIER_STATUS_INACTIVE:
            warnings.append(
                AdminSupplierWarningView(
                    code="inactive_supplier", message="Proveedor inactivo.", severity="warning"
                )
            )
        if self._primary_contact(row) is None:
            warnings.append(
                AdminSupplierWarningView(
                    code="missing_primary_contact",
                    message="Falta contacto principal.",
                    severity="warning",
                )
            )
        if not row.supplier.tax_id:
            warnings.append(
                AdminSupplierWarningView(
                    code="missing_tax_id", message="Falta RFC / Tax ID.", severity="info"
                )
            )
        if not any(relation.is_active for relation, _, _ in row.products):
            warnings.append(
                AdminSupplierWarningView(
                    code="no_products",
                    message="Proveedor sin productos o insumos asociados.",
                    severity="warning",
                )
            )
        if not any(relation.is_active for relation, _ in row.branches):
            warnings.append(
                AdminSupplierWarningView(
                    code="no_branches",
                    message="Proveedor sin sucursales asociadas.",
                    severity="info",
                )
            )
        if row.supplier.lead_time_days <= 0:
            warnings.append(
                AdminSupplierWarningView(
                    code="missing_lead_time", message="Lead time no definido.", severity="info"
                )
            )
        if any(
            relation.is_active and not product.is_active for relation, product, _ in row.products
        ):
            warnings.append(
                AdminSupplierWarningView(
                    code="inactive_product_relation",
                    message="Incluye productos inactivos.",
                    severity="warning",
                )
            )
        return warnings

    def _related_documents(self, row: _SupplierRow) -> list[AdminSupplierRelatedDocumentView]:
        documents: list[AdminSupplierRelatedDocumentView] = []
        documents.extend(
            AdminSupplierRelatedDocumentView(
                document_id=relation.id,
                document_type="SUPPLIER_PRODUCT",
                folio=product.code,
                status="active" if relation.is_active else "inactive",
            )
            for relation, product, _ in row.products
        )
        documents.extend(
            AdminSupplierRelatedDocumentView(
                document_id=relation.id,
                document_type="SUPPLIER_BRANCH",
                folio=branch.code,
                status="active" if relation.is_active else "inactive",
            )
            for relation, branch in row.branches
        )
        return documents

    def _replace_contacts(
        self,
        session: Session,
        *,
        contacts: list[AdminSupplierContactRequest],
        supplier: Supplier,
    ) -> None:
        existing_contacts = (
            session.execute(
                select(SupplierContact).where(SupplierContact.supplier_id == supplier.id)
            )
            .scalars()
            .all()
        )
        for contact in existing_contacts:
            session.delete(contact)
        session.flush()
        for index, contact_command in enumerate(contacts):
            contact_data = contact_command.model_dump()
            contact_data["is_primary"] = contact_command.is_primary or index == 0
            self._upsert_contact(
                session,
                supplier=supplier,
                command=AdminSupplierContactRequest(**contact_data),
            )

    def _upsert_contact(
        self, session: Session, *, command: AdminSupplierContactRequest, supplier: Supplier
    ) -> SupplierContact:
        if command.is_primary:
            self._clear_other_primary_contacts(session, supplier_id=supplier.id)
        contact = SupplierContact(supplier_id=supplier.id)
        self._apply_contact(contact, command)
        session.add(contact)
        return contact

    def _apply_contact(
        self, contact: SupplierContact, command: AdminSupplierContactRequest
    ) -> None:
        if not command.phone and not command.email and not command.whatsapp:
            raise SupplierValidationError("Supplier contact needs at least one contact channel.")
        contact.email = command.email
        contact.is_active = True
        contact.is_primary = command.is_primary
        contact.name = command.name.strip()
        contact.notes = command.notes
        contact.phone = command.phone
        contact.role = command.role
        contact.whatsapp = command.whatsapp

    def _clear_other_primary_contacts(
        self,
        session: Session,
        *,
        supplier_id: uuid.UUID,
        except_contact_id: uuid.UUID | None = None,
    ) -> None:
        contacts = (
            session.execute(
                select(SupplierContact).where(SupplierContact.supplier_id == supplier_id)
            )
            .scalars()
            .all()
        )
        for contact in contacts:
            if except_contact_id is None or contact.id != except_contact_id:
                contact.is_primary = False

    def _upsert_product_relations(
        self,
        session: Session,
        *,
        relations: list[AdminSupplierProductRequest],
        supplier: Supplier,
    ) -> None:
        existing = (
            session.execute(
                select(SupplierProduct).where(SupplierProduct.supplier_id == supplier.id)
            )
            .scalars()
            .all()
        )
        requested_product_ids = {relation.product_id for relation in relations}
        for relation in existing:
            if relation.product_id not in requested_product_ids:
                relation.is_active = False

        for relation_command in relations:
            self._upsert_product_relation(session, supplier=supplier, command=relation_command)

    def _upsert_product_relation(
        self, session: Session, *, command: AdminSupplierProductRequest, supplier: Supplier
    ) -> bool:
        product = self._get_product(session, command.product_id)
        relation = session.execute(
            select(SupplierProduct).where(
                SupplierProduct.supplier_id == supplier.id, SupplierProduct.product_id == product.id
            ),
        ).scalar_one_or_none()
        created = relation is None
        if relation is None:
            relation = SupplierProduct(supplier_id=supplier.id, product_id=product.id)
            session.add(relation)
        self._apply_product_relation(relation, command, product)
        return created

    def _apply_product_relation(
        self, relation: SupplierProduct, command: AdminSupplierProductRequest, product: Product
    ) -> None:
        relation.currency = command.currency
        relation.conversion_factor = command.conversion_factor
        relation.is_active = command.is_active
        relation.last_known_price = command.last_known_price
        relation.lead_time_days = command.lead_time_days
        relation.minimum_order_qty = command.minimum_order_qty
        relation.notes = command.notes
        relation.product_id = product.id
        relation.purchase_uom = command.purchase_uom or product.unit_of_measure
        relation.supplier_sku = command.supplier_sku

    def _replace_branch_relations(
        self, session: Session, *, branch_ids: list[uuid.UUID], supplier: Supplier
    ) -> None:
        existing = (
            session.execute(select(SupplierBranch).where(SupplierBranch.supplier_id == supplier.id))
            .scalars()
            .all()
        )
        requested = set(branch_ids)
        for relation in existing:
            relation.is_active = relation.branch_id in requested
        existing_branch_ids = {relation.branch_id for relation in existing}
        for branch_id in requested - existing_branch_ids:
            branch = self._get_branch(session, branch_id)
            session.add(
                SupplierBranch(branch_id=branch.id, supplier_id=supplier.id, is_active=True)
            )

    def _primary_contact(self, row: _SupplierRow) -> SupplierContact | None:
        return next(
            (contact for contact in row.contacts if contact.is_active and contact.is_primary), None
        ) or next(
            (contact for contact in row.contacts if contact.is_active),
            None,
        )

    def _matches_search(self, row: _SupplierRow, search: str) -> bool:
        normalized = search.lower()
        values = [
            row.supplier.code,
            row.supplier.legal_name,
            row.supplier.commercial_name,
            row.supplier.tax_id,
            *(contact.name for contact in row.contacts),
            *(contact.phone for contact in row.contacts),
            *(contact.email for contact in row.contacts),
            *(product.code for _, product, _ in row.products),
            *(product.name for _, product, _ in row.products),
        ]
        return any(normalized in str(value).lower() for value in values if value)

    def _terms_summary(self, supplier: Supplier) -> str:
        label = SUPPLIER_PAYMENT_TERMS_LABELS.get(
            supplier.payment_terms_type, supplier.payment_terms_type
        )
        if supplier.payment_terms_type == SUPPLIER_PAYMENT_TERMS_CREDIT:
            return f"{label} {supplier.credit_days} dias - lead {supplier.lead_time_days} dias"
        return f"{label} - lead {supplier.lead_time_days} dias"

    def _warning_state(
        self, warnings: list[AdminSupplierWarningView]
    ) -> AdminSupplierWarningSeverity | None:
        if any(warning.severity == "critical" for warning in warnings):
            return "critical"
        if any(warning.severity == "warning" for warning in warnings):
            return "warning"
        if warnings:
            return "info"
        return None

    def _validate_supplier_command(
        self, command: AdminSupplierCreateRequest | AdminSupplierUpdateRequest
    ) -> None:
        if command.category not in VALID_SUPPLIER_CATEGORIES:
            raise SupplierValidationError("Supplier category is not supported.")
        if command.status not in VALID_SUPPLIER_STATUSES:
            raise SupplierValidationError("Supplier status is not supported.")
        if command.payment_terms_type not in VALID_SUPPLIER_PAYMENT_TERMS:
            raise SupplierValidationError("Supplier payment terms are not supported.")
        if command.payment_fiscal_email and "@" not in command.payment_fiscal_email:
            raise SupplierValidationError("Supplier fiscal email must be valid.")
        product_ids = [relation.product_id for relation in command.product_relations]
        if len(product_ids) != len(set(product_ids)):
            raise SupplierValidationError("Supplier product relations must be unique by product.")

    def _get_supplier(self, session: Session, supplier_id: uuid.UUID) -> Supplier:
        supplier = session.get(Supplier, supplier_id)
        if supplier is None:
            raise SupplierNotFoundError("Supplier was not found.")
        return supplier

    def _get_product(self, session: Session, product_id: uuid.UUID) -> Product:
        product = session.get(Product, product_id)
        if product is None:
            raise SupplierNotFoundError("Product was not found.")
        return product

    def _get_branch(self, session: Session, branch_id: uuid.UUID) -> Branch:
        branch = session.get(Branch, branch_id)
        if branch is None:
            raise SupplierNotFoundError("Branch was not found.")
        return branch

    def _ensure_unique_code(self, session: Session, code: str) -> None:
        if (
            session.execute(select(Supplier).where(Supplier.code == code)).scalar_one_or_none()
            is not None
        ):
            raise SupplierValidationError("Supplier code must be unique.")

    def _ensure_unique_tax_id(self, session: Session, tax_id: str) -> None:
        if (
            session.execute(select(Supplier).where(Supplier.tax_id == tax_id)).scalar_one_or_none()
            is not None
        ):
            raise SupplierValidationError("Supplier tax id must be unique.")

    def _generate_supplier_code(self, session: Session) -> str:
        while True:
            code = f"SUP-{str(uuid.uuid4())[:8].upper()}"
            if (
                session.execute(select(Supplier).where(Supplier.code == code)).scalar_one_or_none()
                is None
            ):
                return code

    def _normalize_supplier_code(self, value: str) -> str:
        code = value.strip().upper()
        if not code:
            raise SupplierValidationError("Supplier code is required.")
        return code

    def _metadata(self, supplier: Supplier) -> dict[str, object]:
        return {
            "category": supplier.category,
            "code": supplier.code,
            "commercial_name": supplier.commercial_name,
            "legal_name": supplier.legal_name,
            "status": supplier.status,
            "supplier_id": str(supplier.id),
            "tax_id": supplier.tax_id,
        }

    def _record_change(
        self,
        session: Session,
        *,
        action: str,
        current_user: AuthenticatedUser,
        event_name: str,
        metadata: dict[str, object],
        request_id: str | None,
        supplier: Supplier,
    ) -> None:
        self._record_audit_only(
            session,
            action=action,
            current_user=current_user,
            metadata=metadata,
            request_id=request_id,
            supplier=supplier,
        )
        self._outbox_writer.append(
            session,
            aggregate_type=SUPPLIER_RESOURCE_TYPE,
            aggregate_id=str(supplier.id),
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
        request_id: str | None,
        supplier: Supplier,
    ) -> None:
        self._audit_recorder.record(
            session,
            actor_id=current_user.id,
            action=action,
            resource_type=SUPPLIER_RESOURCE_TYPE,
            resource_id=str(supplier.id),
            branch_id=None,
            request_id=request_id,
            metadata=metadata,
        )


def _normalize_optional(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None
