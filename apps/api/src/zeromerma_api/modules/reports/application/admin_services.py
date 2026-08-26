from __future__ import annotations

import uuid
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime, time
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session, aliased

from zeromerma_api.modules.audit.application.service import AuditRecorder
from zeromerma_api.modules.branches.infrastructure.models import Branch, Workstation
from zeromerma_api.modules.cash_close.infrastructure.models import CashSessionClose
from zeromerma_api.modules.catalog.infrastructure.models import Product
from zeromerma_api.modules.identity.application.schemas import AuthenticatedUser
from zeromerma_api.modules.identity.domain.constants import (
    IDENTITY_SURFACE_BACKOFFICE,
    IDENTITY_SURFACE_POS,
)
from zeromerma_api.modules.identity.infrastructure.models import (
    Role,
    User,
    UserBranchAssignment,
    UserRoleAssignment,
)
from zeromerma_api.modules.inventory.infrastructure.models import InventoryBalance
from zeromerma_api.modules.operations.domain.constants import (
    OPERATION_DOCUMENT_STATUS_COMMITTED,
    OPERATION_DOCUMENT_STATUS_IN_TRANSIT,
    OPERATION_DOCUMENT_TYPE_BRANCH_TRANSFER_SHIPMENT,
    OPERATION_DOCUMENT_TYPE_WASTE_RECORD,
)
from zeromerma_api.modules.operations.infrastructure.models import (
    OperationDocument,
    OperationDocumentLine,
    WasteReason,
)
from zeromerma_api.modules.payments.infrastructure.models import (
    OperationalPayment,
    OperationalPaymentCategory,
)
from zeromerma_api.modules.quality.infrastructure.models import CleaningLog
from zeromerma_api.modules.reports.application.admin_schemas import (
    AdminReportCatalogFilterOptionsView,
    AdminReportCatalogMetricsView,
    AdminReportColumnView,
    AdminReportDefinitionsResponse,
    AdminReportDefinitionView,
    AdminReportExportResponse,
    AdminReportFilterDefinitionView,
    AdminReportFilterOptionView,
    AdminReportPreviewResponse,
    AdminReportRelatedLinkView,
    AdminReportRowView,
    AdminReportSummaryCardView,
)
from zeromerma_api.modules.reports.domain.exceptions import (
    ReportNotFoundError,
    ReportUnavailableError,
    ReportValidationError,
)
from zeromerma_api.modules.sales.infrastructure.models import Sale, SalePayment

REPORT_STATUS_AVAILABLE = "available"
REPORT_STATUS_REQUIRES_BACKEND = "requires_backend"
REPORT_STATUS_COMING_SOON = "coming_soon"
REPORT_EXPORT_JSON = "json"
AUDIT_ACTION_REPORT_EXPORTED = "admin.report.exported"
REPORT_RESOURCE_TYPE = "report"
MAX_PREVIEW_ROWS = 100

CATEGORY_LABELS = {
    "ventas_pedidos": "Ventas y pedidos",
    "caja_finanzas": "Caja y finanzas",
    "catalogo_costos": "Catalogo y costos",
    "operacion_multisucursal": "Operacion multisucursal",
    "compras_abastecimiento": "Compras y abastecimiento",
    "calidad_higiene": "Calidad e higiene",
    "control": "Control",
}

SOURCE_MODULE_LABELS = {
    "audit": "Auditoria",
    "cash_close": "Cortes de caja",
    "cleaning_logs": "Bitacoras de limpieza",
    "inventory": "Inventario",
    "payments": "Pagos operativos",
    "reports": "Reportes",
    "sales": "Ventas",
    "tickets": "Tickets",
    "transfers": "Transferencias",
    "users": "Usuarios",
    "waste": "Merma",
}


@dataclass(frozen=True)
class _FilterDefinition:
    key: str
    label: str
    type: str
    options_source: str | None = None
    required: bool = False
    default_value: str | None = None
    static_options: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True)
class _ReportDefinition:
    code: str
    name: str
    description: str
    category: str
    source_modules: tuple[str, ...]
    filters: tuple[_FilterDefinition, ...]
    supported_exports: tuple[str, ...]
    status: str
    is_sensitive: bool
    required_permissions: tuple[str, ...]
    preview_kind: str
    unavailable_reason: str | None = None


_ReportPreviewBuilder = Callable[
    [Session, _ReportDefinition, dict[str, Any]],
    AdminReportPreviewResponse,
]


class AdminReportService:
    def __init__(self, audit_recorder: AuditRecorder | None = None) -> None:
        self._audit_recorder = audit_recorder or AuditRecorder()

    def list_reports(
        self,
        session: Session,
        *,
        search: str | None,
        category: str | None,
        status_filter: str | None,
        export_support: str | None,
        sensitivity: str | None,
        source_module: str | None,
    ) -> AdminReportDefinitionsResponse:
        definitions = list(_REPORT_DEFINITIONS)
        filtered = self._apply_catalog_filters(
            definitions,
            search=search,
            category=category,
            status_filter=status_filter,
            export_support=export_support,
            sensitivity=sensitivity,
            source_module=source_module,
        )
        return AdminReportDefinitionsResponse(
            definitions=[self._to_definition_view(session, definition) for definition in filtered],
            filter_options=self._catalog_filter_options(definitions),
            metrics=self._catalog_metrics(definitions),
            total=len(filtered),
        )

    def generate_preview(
        self,
        session: Session,
        *,
        report_code: str,
        filters: dict[str, Any],
    ) -> AdminReportPreviewResponse:
        definition = self._get_definition(report_code)
        if definition.status != REPORT_STATUS_AVAILABLE:
            raise ReportUnavailableError(
                definition.unavailable_reason or "This report requires additional backend support.",
            )
        normalized_filters = self._validate_filters(definition, filters)
        builders: dict[str, _ReportPreviewBuilder] = {
            "sales_summary_by_branch": self._sales_summary_by_branch,
            "cash_cuts_with_differences": self._cash_cuts_with_differences,
            "operational_payments_by_category": self._operational_payments_by_category,
            "inventory_low_negative_stock": self._inventory_low_negative_stock,
            "waste_summary": self._waste_summary,
            "transfers_in_transit": self._transfers_in_transit,
            "cleaning_compliance": self._cleaning_compliance,
            "user_access_summary": self._user_access_summary,
        }
        builder = builders.get(definition.code)
        if builder is None:
            raise ReportUnavailableError("This report does not have a preview builder.")
        return builder(session, definition, normalized_filters)

    def export_report(
        self,
        session: Session,
        *,
        current_user: AuthenticatedUser,
        report_code: str,
        filters: dict[str, Any],
        export_format: str,
        request_id: str | None,
    ) -> AdminReportExportResponse:
        definition = self._get_definition(report_code)
        normalized_format = export_format.strip().lower()
        if normalized_format not in definition.supported_exports:
            raise ReportValidationError("Unsupported export format for this report.")

        preview = self.generate_preview(session, report_code=report_code, filters=filters)
        self._audit_recorder.record(
            session,
            actor_id=current_user.id,
            action=AUDIT_ACTION_REPORT_EXPORTED,
            resource_type=REPORT_RESOURCE_TYPE,
            resource_id=definition.code,
            branch_id=_uuid_filter(preview.filters_applied, "branch_id"),
            request_id=request_id,
            metadata={
                "format": normalized_format,
                "filters": preview.filters_applied,
                "is_sensitive": definition.is_sensitive,
                "module": "reports",
                "report_code": definition.code,
                "report_name": definition.name,
                "result": "success",
                "row_count": len(preview.rows),
                "source_app": "BACKOFFICE",
            },
        )
        session.commit()
        return AdminReportExportResponse(
            format=normalized_format,
            generated_at=datetime.now(tz=UTC),
            report_code=definition.code,
            report_name=definition.name,
            filters_applied=preview.filters_applied,
            total_rows=len(preview.rows),
            rows=preview.rows,
            warnings=preview.warnings,
        )

    def _sales_summary_by_branch(
        self,
        session: Session,
        definition: _ReportDefinition,
        filters: dict[str, Any],
    ) -> AdminReportPreviewResponse:
        date_from, date_to = _date_range(filters)
        branch_id = _uuid_filter(filters, "branch_id")
        sale_conditions = [Sale.confirmed_at >= date_from, Sale.confirmed_at <= date_to]
        if branch_id is not None:
            sale_conditions.append(Sale.branch_id == branch_id)

        sale_rows = (
            session.execute(
                select(
                    Sale.branch_id,
                    Branch.name.label("branch_name"),
                    Branch.code.label("branch_code"),
                    func.count(Sale.id).label("ticket_count"),
                    func.coalesce(func.sum(Sale.total_amount), Decimal("0")).label("total_sales"),
                    func.coalesce(func.avg(Sale.total_amount), Decimal("0")).label(
                        "average_ticket"
                    ),
                )
                .join(Branch, Branch.id == Sale.branch_id)
                .where(*sale_conditions)
                .group_by(Sale.branch_id, Branch.name, Branch.code)
                .order_by(Branch.name.asc())
            )
            .mappings()
            .all()
        )
        payment_rows = (
            session.execute(
                select(
                    Sale.branch_id,
                    SalePayment.payment_method_code,
                    func.coalesce(func.sum(SalePayment.applied_amount), Decimal("0")).label(
                        "amount"
                    ),
                )
                .join(SalePayment, SalePayment.sale_id == Sale.id)
                .where(*sale_conditions)
                .group_by(Sale.branch_id, SalePayment.payment_method_code)
            )
            .mappings()
            .all()
        )
        payments_by_branch: dict[uuid.UUID, dict[str, Decimal]] = defaultdict(dict)
        for row in payment_rows:
            payments_by_branch[row["branch_id"]][row["payment_method_code"]] = row["amount"]

        rows: list[AdminReportRowView] = []
        for row in sale_rows[:MAX_PREVIEW_ROWS]:
            branch_uuid = row["branch_id"]
            payments = payments_by_branch.get(branch_uuid, {})
            rows.append(
                AdminReportRowView(
                    id=str(branch_uuid),
                    cells={
                        "branch": f"{row['branch_name']} ({row['branch_code']})",
                        "ticket_count": str(row["ticket_count"]),
                        "total_sales": _money(row["total_sales"]),
                        "average_ticket": _money(row["average_ticket"]),
                        "cash_total": _money(payments.get("CASH", Decimal("0"))),
                        "card_total": _money(payments.get("CARD", Decimal("0"))),
                        "mixed_total": _money(payments.get("MIXED", Decimal("0"))),
                    },
                    source_document_links=[
                        _link("Abrir ventas", "sales", "/admin/ventas"),
                    ],
                )
            )

        total_sales = sum((Decimal(row["total_sales"]) for row in sale_rows), Decimal("0"))
        ticket_count = sum((int(row["ticket_count"]) for row in sale_rows), 0)
        return self._preview(
            definition,
            filters,
            summary_cards=[
                _card("Ventas", _money(total_sales), "Total confirmado del periodo", "success"),
                _card("Tickets", str(ticket_count), "Tickets confirmados"),
                _card(
                    "Ticket promedio",
                    _money(total_sales / ticket_count if ticket_count else Decimal("0")),
                    "Promedio sobre tickets filtrados",
                ),
                _card("Sucursales", str(len(sale_rows)), "Sucursales con venta"),
            ],
            columns=[
                _column("branch", "Sucursal"),
                _column("ticket_count", "Tickets", "number"),
                _column("total_sales", "Ventas", "money"),
                _column("average_ticket", "Ticket promedio", "money"),
                _column("cash_total", "Efectivo", "money"),
                _column("card_total", "Tarjeta", "money"),
                _column("mixed_total", "Mixto", "money"),
            ],
            rows=rows,
            related_links=[_link("Ventas / tickets", "sales", "/admin/ventas")],
        )

    def _cash_cuts_with_differences(
        self,
        session: Session,
        definition: _ReportDefinition,
        filters: dict[str, Any],
    ) -> AdminReportPreviewResponse:
        date_from, date_to = _date_range(filters)
        branch_id = _uuid_filter(filters, "branch_id")
        conditions = [
            CashSessionClose.started_at_utc >= date_from,
            CashSessionClose.started_at_utc <= date_to,
        ]
        if branch_id is not None:
            conditions.append(CashSessionClose.branch_id == branch_id)
        rows_raw = session.execute(
            select(CashSessionClose, Branch, Workstation, User)
            .join(Branch, Branch.id == CashSessionClose.branch_id)
            .join(Workstation, Workstation.id == CashSessionClose.workstation_id)
            .outerjoin(User, User.id == CashSessionClose.closed_by_user_id)
            .where(*conditions)
            .order_by(CashSessionClose.started_at_utc.desc())
        ).all()

        rows = [
            AdminReportRowView(
                id=str(close.id),
                cells={
                    "folio": _cash_cut_folio(close.id),
                    "branch": branch.name,
                    "station": workstation.name,
                    "status": close.status,
                    "opened": _date_text(close.started_at_utc),
                    "committed": _date_text(close.committed_at_utc),
                    "expected": _money(close.expected_cash_amount),
                    "counted": _money(close.counted_cash_amount),
                    "difference": _money(close.cash_variance_amount),
                    "reconciliation": close.reconciliation_status,
                    "closed_by": user.full_name if user is not None else "Sin usuario",
                },
                source_document_links=[
                    _link(
                        "Abrir corte de caja",
                        "cash_close",
                        "/admin/cortes-caja",
                        document_type="cash_cut",
                        document_id=str(close.id),
                        reference=_cash_cut_folio(close.id),
                    )
                ],
            )
            for close, branch, workstation, user in rows_raw[:MAX_PREVIEW_ROWS]
        ]
        differences = [
            Decimal(close.cash_variance_amount or Decimal("0"))
            for close, _branch, _workstation, _user in rows_raw
        ]
        return self._preview(
            definition,
            filters,
            summary_cards=[
                _card("Cortes", str(len(rows_raw)), "Cortes encontrados"),
                _card(
                    "Con diferencia",
                    str(sum(1 for amount in differences if amount != Decimal("0"))),
                    "Cortes con variacion distinta de cero",
                    "warning",
                ),
                _card(
                    "Diferencia neta",
                    _money(sum(differences, Decimal("0"))),
                    "Suma de variaciones",
                    "warning",
                ),
            ],
            columns=[
                _column("folio", "Folio"),
                _column("branch", "Sucursal"),
                _column("station", "Caja / estacion"),
                _column("status", "Estado"),
                _column("opened", "Inicio"),
                _column("committed", "Cierre"),
                _column("expected", "Esperado", "money"),
                _column("counted", "Contado", "money"),
                _column("difference", "Diferencia", "money"),
                _column("reconciliation", "Conciliacion"),
                _column("closed_by", "Responsable"),
            ],
            rows=rows,
            related_links=[_link("Cortes de caja", "cash_close", "/admin/cortes-caja")],
        )

    def _operational_payments_by_category(
        self,
        session: Session,
        definition: _ReportDefinition,
        filters: dict[str, Any],
    ) -> AdminReportPreviewResponse:
        date_from, date_to = _date_range(filters)
        branch_id = _uuid_filter(filters, "branch_id")
        conditions = [
            OperationalPayment.committed_at_utc >= date_from,
            OperationalPayment.committed_at_utc <= date_to,
        ]
        if branch_id is not None:
            conditions.append(OperationalPayment.branch_id == branch_id)
        rows_raw = (
            session.execute(
                select(
                    func.coalesce(OperationalPayment.category_code, "OTHER").label("category_code"),
                    func.coalesce(
                        OperationalPaymentCategory.name,
                        "Sin categoria",
                    ).label("category_name"),
                    func.count(OperationalPayment.id).label("payment_count"),
                    func.coalesce(
                        func.sum(OperationalPayment.total_amount),
                        Decimal("0"),
                    ).label("total_amount"),
                    func.coalesce(
                        func.sum(OperationalPayment.cash_amount),
                        Decimal("0"),
                    ).label("cash_amount"),
                    func.coalesce(
                        func.sum(OperationalPayment.non_cash_amount),
                        Decimal("0"),
                    ).label("non_cash_amount"),
                )
                .outerjoin(
                    OperationalPaymentCategory,
                    OperationalPaymentCategory.code == OperationalPayment.category_code,
                )
                .where(*conditions)
                .group_by(OperationalPayment.category_code, OperationalPaymentCategory.name)
                .order_by(
                    func.coalesce(func.sum(OperationalPayment.total_amount), Decimal("0")).desc()
                )
            )
            .mappings()
            .all()
        )
        rows = [
            AdminReportRowView(
                id=str(row["category_code"]),
                cells={
                    "category": str(row["category_name"]),
                    "payment_count": str(row["payment_count"]),
                    "total_amount": _money(row["total_amount"]),
                    "cash_amount": _money(row["cash_amount"]),
                    "non_cash_amount": _money(row["non_cash_amount"]),
                },
                source_document_links=[
                    _link("Pagos operativos", "payments", "/admin/pagos-operativos"),
                ],
            )
            for row in rows_raw[:MAX_PREVIEW_ROWS]
        ]
        total = sum((Decimal(row["total_amount"]) for row in rows_raw), Decimal("0"))
        return self._preview(
            definition,
            filters,
            summary_cards=[
                _card("Pagos operativos", _money(total), "Total egresado del periodo", "warning"),
                _card("Categorias", str(len(rows_raw)), "Categorias con movimiento"),
                _card(
                    "Registros",
                    str(sum((int(row["payment_count"]) for row in rows_raw), 0)),
                    "Pagos confirmados",
                ),
            ],
            columns=[
                _column("category", "Categoria"),
                _column("payment_count", "Pagos", "number"),
                _column("total_amount", "Total", "money"),
                _column("cash_amount", "Efectivo", "money"),
                _column("non_cash_amount", "No efectivo", "money"),
            ],
            rows=rows,
            related_links=[_link("Pagos operativos", "payments", "/admin/pagos-operativos")],
        )

    def _inventory_low_negative_stock(
        self,
        session: Session,
        definition: _ReportDefinition,
        filters: dict[str, Any],
    ) -> AdminReportPreviewResponse:
        branch_id = _uuid_filter(filters, "branch_id")
        conditions = [
            or_(
                InventoryBalance.quantity_on_hand < Decimal("0"),
                and_(
                    Product.minimum_stock.is_not(None),
                    InventoryBalance.quantity_on_hand <= Product.minimum_stock,
                ),
            )
        ]
        if branch_id is not None:
            conditions.append(InventoryBalance.branch_id == branch_id)
        rows_raw = session.execute(
            select(InventoryBalance, Product, Branch)
            .join(Product, Product.id == InventoryBalance.product_id)
            .join(Branch, Branch.id == InventoryBalance.branch_id)
            .where(*conditions)
            .order_by(Branch.name.asc(), Product.name.asc(), InventoryBalance.location_code.asc())
        ).all()
        rows = []
        negative_count = 0
        low_count = 0
        for balance, product, branch in rows_raw[:MAX_PREVIEW_ROWS]:
            state = "negative" if balance.quantity_on_hand < Decimal("0") else "low_stock"
            if state == "negative":
                negative_count += 1
            else:
                low_count += 1
            rows.append(
                AdminReportRowView(
                    id=str(balance.id),
                    cells={
                        "product": f"{product.name} ({product.code})",
                        "branch": branch.name,
                        "location": balance.location_code,
                        "quantity_on_hand": _quantity(balance.quantity_on_hand),
                        "minimum_stock": _quantity(product.minimum_stock),
                        "state": state,
                        "updated_at": _date_text(balance.updated_at),
                    },
                    source_document_links=[
                        _link("Inventario", "inventory", "/admin/inventario"),
                    ],
                )
            )
        negative_total = sum(
            1 for balance, _product, _branch in rows_raw if balance.quantity_on_hand < Decimal("0")
        )
        low_total = len(rows_raw) - negative_total
        return self._preview(
            definition,
            filters,
            summary_cards=[
                _card(
                    "Productos revisables",
                    str(len(rows_raw)),
                    "Stocks bajos o negativos",
                    "warning",
                ),
                _card("Negativos", str(negative_total), "Balances bajo cero", "danger"),
                _card("Bajo minimo", str(low_total), "Balances en minimo o debajo", "warning"),
            ],
            columns=[
                _column("product", "Producto"),
                _column("branch", "Sucursal"),
                _column("location", "Ubicacion"),
                _column("quantity_on_hand", "Existencia", "quantity"),
                _column("minimum_stock", "Minimo", "quantity"),
                _column("state", "Estado"),
                _column("updated_at", "Actualizado"),
            ],
            rows=rows,
            related_links=[_link("Inventario", "inventory", "/admin/inventario")],
            warnings=(
                []
                if negative_count + low_count == len(rows)
                else ["La vista previa esta limitada a los primeros registros del reporte."]
            ),
        )

    def _waste_summary(
        self,
        session: Session,
        definition: _ReportDefinition,
        filters: dict[str, Any],
    ) -> AdminReportPreviewResponse:
        date_from, date_to = _date_range(filters)
        branch_id = _uuid_filter(filters, "branch_id")
        conditions = [
            OperationDocument.document_type == OPERATION_DOCUMENT_TYPE_WASTE_RECORD,
            OperationDocument.status == OPERATION_DOCUMENT_STATUS_COMMITTED,
            OperationDocument.created_at_utc >= date_from,
            OperationDocument.created_at_utc <= date_to,
        ]
        if branch_id is not None:
            conditions.append(OperationDocument.source_branch_id == branch_id)
        line_rows = session.execute(
            select(OperationDocument, Branch, WasteReason, OperationDocumentLine, Product)
            .join(Branch, Branch.id == OperationDocument.source_branch_id)
            .join(WasteReason, WasteReason.code == OperationDocument.reason_code)
            .join(
                OperationDocumentLine,
                OperationDocumentLine.operation_document_id == OperationDocument.id,
            )
            .join(Product, Product.id == OperationDocumentLine.product_id)
            .where(*conditions)
            .order_by(Branch.name.asc(), WasteReason.name.asc())
        ).all()
        grouped: dict[tuple[uuid.UUID, str], dict[str, Any]] = {}
        for document, branch, reason, line, product in line_rows:
            key = (branch.id, reason.code)
            bucket = grouped.setdefault(
                key,
                {
                    "branch": branch,
                    "documents": set(),
                    "estimated": Decimal("0"),
                    "has_missing_cost": False,
                    "quantity": Decimal("0"),
                    "reason": reason,
                },
            )
            bucket["documents"].add(document.id)
            bucket["quantity"] += Decimal(line.quantity)
            if product.standard_cost is None:
                bucket["has_missing_cost"] = True
            else:
                bucket["estimated"] += Decimal(line.quantity) * Decimal(product.standard_cost)

        rows = [
            AdminReportRowView(
                id=f"{branch_id_value}-{reason_code}",
                cells={
                    "branch": bucket["branch"].name,
                    "reason": bucket["reason"].name,
                    "record_count": str(len(bucket["documents"])),
                    "quantity": _quantity(bucket["quantity"]),
                    "estimated_value": (
                        "Costo incompleto"
                        if bucket["has_missing_cost"]
                        else _money(bucket["estimated"])
                    ),
                },
                source_document_links=[_link("Merma", "waste", "/admin/merma")],
            )
            for (branch_id_value, reason_code), bucket in list(grouped.items())[:MAX_PREVIEW_ROWS]
        ]
        total_quantity = sum((bucket["quantity"] for bucket in grouped.values()), Decimal("0"))
        total_records = len({document.id for document, *_rest in line_rows})
        warnings = (
            [
                "Algunas lineas no tienen costo estandar; "
                "el valor estimado se muestra como incompleto."
            ]
            if any(bucket["has_missing_cost"] for bucket in grouped.values())
            else []
        )
        return self._preview(
            definition,
            filters,
            summary_cards=[
                _card("Registros de merma", str(total_records), "Documentos confirmados"),
                _card(
                    "Cantidad total",
                    _quantity(total_quantity),
                    "Unidades / medida registrada",
                    "warning",
                ),
                _card("Motivos", str(len({key[1] for key in grouped})), "Motivos usados"),
            ],
            columns=[
                _column("branch", "Sucursal"),
                _column("reason", "Motivo"),
                _column("record_count", "Registros", "number"),
                _column("quantity", "Cantidad", "quantity"),
                _column("estimated_value", "Valor estimado", "money"),
            ],
            rows=rows,
            related_links=[_link("Merma", "waste", "/admin/merma")],
            warnings=warnings,
        )

    def _transfers_in_transit(
        self,
        session: Session,
        definition: _ReportDefinition,
        filters: dict[str, Any],
    ) -> AdminReportPreviewResponse:
        branch_id = _uuid_filter(filters, "branch_id")
        origin_branch = aliased(Branch)
        destination_branch = aliased(Branch)
        line_stats = (
            select(
                OperationDocumentLine.operation_document_id.label("document_id"),
                func.count(OperationDocumentLine.id).label("line_count"),
                func.coalesce(
                    func.sum(OperationDocumentLine.quantity),
                    Decimal("0"),
                ).label("quantity"),
            )
            .group_by(OperationDocumentLine.operation_document_id)
            .subquery()
        )
        conditions = [
            OperationDocument.document_type == OPERATION_DOCUMENT_TYPE_BRANCH_TRANSFER_SHIPMENT,
            OperationDocument.status == OPERATION_DOCUMENT_STATUS_IN_TRANSIT,
        ]
        if branch_id is not None:
            conditions.append(
                or_(
                    OperationDocument.source_branch_id == branch_id,
                    OperationDocument.destination_branch_id == branch_id,
                )
            )
        rows_raw = (
            session.execute(
                select(
                    OperationDocument.id.label("document_id"),
                    OperationDocument.status,
                    OperationDocument.created_at_utc,
                    OperationDocument.committed_at_utc,
                    origin_branch.name.label("origin_name"),
                    destination_branch.name.label("destination_name"),
                    func.coalesce(line_stats.c.line_count, 0).label("line_count"),
                    func.coalesce(line_stats.c.quantity, Decimal("0")).label("quantity"),
                )
                .join(origin_branch, origin_branch.id == OperationDocument.source_branch_id)
                .join(
                    destination_branch,
                    destination_branch.id == OperationDocument.destination_branch_id,
                )
                .outerjoin(line_stats, line_stats.c.document_id == OperationDocument.id)
                .where(*conditions)
                .order_by(OperationDocument.created_at_utc.desc())
            )
            .mappings()
            .all()
        )
        rows = [
            AdminReportRowView(
                id=str(row["document_id"]),
                cells={
                    "folio": _transfer_folio(row["document_id"]),
                    "origin": str(row["origin_name"]),
                    "destination": str(row["destination_name"]),
                    "created_at": _date_text(row["created_at_utc"]),
                    "dispatched_at": _date_text(row["committed_at_utc"]),
                    "line_count": str(row["line_count"]),
                    "quantity": _quantity(row["quantity"]),
                    "status": row["status"],
                },
                source_document_links=[
                    _link(
                        "Abrir transferencia",
                        "transfers",
                        "/admin/transferencias",
                        document_type="branch_transfer",
                        document_id=str(row["document_id"]),
                        reference=_transfer_folio(row["document_id"]),
                    )
                ],
            )
            for row in rows_raw[:MAX_PREVIEW_ROWS]
        ]
        return self._preview(
            definition,
            filters,
            summary_cards=[
                _card(
                    "En transito",
                    str(len(rows_raw)),
                    "Transferencias pendientes de recepcion",
                    "warning",
                ),
                _card(
                    "Unidades",
                    _quantity(sum((Decimal(row["quantity"]) for row in rows_raw), Decimal("0"))),
                    "Cantidad enviada pendiente",
                ),
            ],
            columns=[
                _column("folio", "Folio"),
                _column("origin", "Origen"),
                _column("destination", "Destino"),
                _column("created_at", "Creada"),
                _column("dispatched_at", "Enviada"),
                _column("line_count", "Lineas", "number"),
                _column("quantity", "Cantidad", "quantity"),
                _column("status", "Estado"),
            ],
            rows=rows,
            related_links=[_link("Transferencias", "transfers", "/admin/transferencias")],
        )

    def _cleaning_compliance(
        self,
        session: Session,
        definition: _ReportDefinition,
        filters: dict[str, Any],
    ) -> AdminReportPreviewResponse:
        date_from, date_to = _date_range(filters)
        branch_id = _uuid_filter(filters, "branch_id")
        conditions = [
            CleaningLog.scheduled_at >= date_from,
            CleaningLog.scheduled_at <= date_to,
        ]
        if branch_id is not None:
            conditions.append(CleaningLog.branch_id == branch_id)
        rows_raw = session.execute(
            select(CleaningLog, Branch)
            .join(Branch, Branch.id == CleaningLog.branch_id)
            .where(*conditions)
            .order_by(Branch.name.asc(), CleaningLog.scheduled_at.desc())
        ).all()
        grouped: dict[uuid.UUID, dict[str, Any]] = {}
        for log, branch in rows_raw:
            bucket = grouped.setdefault(
                branch.id,
                {
                    "branch": branch,
                    "completed": 0,
                    "evidence": 0,
                    "high_risk": 0,
                    "missed": 0,
                    "pending": 0,
                    "requires_review": 0,
                    "total": 0,
                },
            )
            bucket["total"] += 1
            if log.status == "COMPLETED":
                bucket["completed"] += 1
            if log.status in {"SCHEDULED", "PENDING", "IN_PROGRESS"}:
                bucket["pending"] += 1
            if log.status == "MISSED":
                bucket["missed"] += 1
            if log.status == "REQUIRES_REVIEW":
                bucket["requires_review"] += 1
            if log.has_evidence:
                bucket["evidence"] += 1
            if log.risk_level in {"HIGH", "CRITICAL"}:
                bucket["high_risk"] += 1

        rows = []
        for branch_uuid, bucket in list(grouped.items())[:MAX_PREVIEW_ROWS]:
            total = int(bucket["total"])
            completed = int(bucket["completed"])
            rows.append(
                AdminReportRowView(
                    id=str(branch_uuid),
                    cells={
                        "branch": bucket["branch"].name,
                        "total": str(total),
                        "completed": str(completed),
                        "compliance": _percent(completed, total),
                        "pending": str(bucket["pending"]),
                        "missed": str(bucket["missed"]),
                        "requires_review": str(bucket["requires_review"]),
                        "with_evidence": str(bucket["evidence"]),
                        "high_risk": str(bucket["high_risk"]),
                    },
                    source_document_links=[
                        _link(
                            "Bitacoras de limpieza",
                            "cleaning_logs",
                            "/admin/bitacoras-limpieza",
                        ),
                    ],
                )
            )
        total_logs = len(rows_raw)
        completed_logs = sum(1 for log, _branch in rows_raw if log.status == "COMPLETED")
        attention_required = sum(
            1 for log, _branch in rows_raw if log.status in {"MISSED", "REQUIRES_REVIEW"}
        )
        return self._preview(
            definition,
            filters,
            summary_cards=[
                _card("Bitacoras", str(total_logs), "Programadas o registradas"),
                _card("Completadas", str(completed_logs), "Registros completados", "success"),
                _card("Cumplimiento", _percent(completed_logs, total_logs), "Completadas / total"),
                _card(
                    "Vencidas o por revisar",
                    str(attention_required),
                    "Atencion requerida",
                    "warning",
                ),
            ],
            columns=[
                _column("branch", "Sucursal"),
                _column("total", "Total", "number"),
                _column("completed", "Completadas", "number"),
                _column("compliance", "Cumplimiento"),
                _column("pending", "Pendientes", "number"),
                _column("missed", "Vencidas", "number"),
                _column("requires_review", "Por revisar", "number"),
                _column("with_evidence", "Con evidencia", "number"),
                _column("high_risk", "Alto riesgo", "number"),
            ],
            rows=rows,
            related_links=[
                _link(
                    "Bitacoras de limpieza",
                    "cleaning_logs",
                    "/admin/bitacoras-limpieza",
                )
            ],
        )

    def _user_access_summary(
        self,
        session: Session,
        definition: _ReportDefinition,
        filters: dict[str, Any],
    ) -> AdminReportPreviewResponse:
        branch_id = _uuid_filter(filters, "branch_id")
        user_status = _optional_filter(filters, "user_status")
        app_access = _optional_filter(filters, "app_access")
        users = (
            session.execute(select(User).order_by(User.full_name.asc(), User.email.asc()))
            .scalars()
            .all()
        )
        branch_rows = session.execute(
            select(UserBranchAssignment, Branch)
            .join(Branch, Branch.id == UserBranchAssignment.branch_id)
            .where(UserBranchAssignment.is_active.is_(True))
            .order_by(Branch.name.asc())
        ).all()
        role_rows = session.execute(
            select(UserRoleAssignment, Role)
            .join(Role, Role.id == UserRoleAssignment.role_id)
            .where(UserRoleAssignment.is_active.is_(True))
            .order_by(Role.name.asc())
        ).all()
        branches_by_user: dict[uuid.UUID, list[Branch]] = defaultdict(list)
        for assignment, branch in branch_rows:
            branches_by_user[assignment.user_id].append(branch)
        roles_by_user: dict[uuid.UUID, list[Role]] = defaultdict(list)
        for assignment, role in role_rows:
            roles_by_user[assignment.user_id].append(role)

        filtered_users = []
        for user in users:
            user_branch_ids = {branch.id for branch in branches_by_user[user.id]}
            if branch_id is not None and branch_id not in user_branch_ids:
                continue
            if user_status and _user_status(user) != user_status:
                continue
            if app_access and not _matches_surface(user.allowed_surfaces, app_access):
                continue
            filtered_users.append(user)

        rows = [
            AdminReportRowView(
                id=str(user.id),
                cells={
                    "full_name": user.full_name,
                    "email": user.email,
                    "status": _user_status(user),
                    "access": _surface_label(user.allowed_surfaces),
                    "branches": _join_names(branches_by_user[user.id]),
                    "roles": _join_names(roles_by_user[user.id]),
                    "last_login": _date_text(user.last_login_at),
                    "created_at": _date_text(user.created_at),
                    "warning": _user_warning(
                        user,
                        branches_by_user[user.id],
                        roles_by_user[user.id],
                    ),
                },
                source_document_links=[
                    _link(
                        "Abrir usuarios",
                        "users",
                        "/admin/usuarios",
                        document_type="user",
                        document_id=str(user.id),
                        reference=user.email,
                    )
                ],
            )
            for user in filtered_users[:MAX_PREVIEW_ROWS]
        ]
        return self._preview(
            definition,
            filters,
            summary_cards=[
                _card("Usuarios", str(len(filtered_users)), "Usuarios filtrados"),
                _card(
                    "Activos",
                    str(sum(1 for user in filtered_users if _user_status(user) == "active")),
                    "Listos para operar",
                    "success",
                ),
                _card(
                    "Bloqueados",
                    str(sum(1 for user in filtered_users if _user_status(user) == "locked")),
                    "Acceso bloqueado",
                    "danger",
                ),
                _card(
                    "Sin sucursal",
                    str(sum(1 for user in filtered_users if not branches_by_user[user.id])),
                    "Usuarios sin sucursal activa",
                    "warning",
                ),
            ],
            columns=[
                _column("full_name", "Nombre"),
                _column("email", "Correo"),
                _column("status", "Estado"),
                _column("access", "Acceso"),
                _column("branches", "Sucursales"),
                _column("roles", "Roles"),
                _column("last_login", "Ultimo acceso"),
                _column("created_at", "Creado"),
                _column("warning", "Advertencia"),
            ],
            rows=rows,
            related_links=[
                _link("Usuarios", "users", "/admin/usuarios"),
                _link("Roles y permisos", "roles_permissions", "/admin/roles-permisos"),
            ],
        )

    def _preview(
        self,
        definition: _ReportDefinition,
        filters: dict[str, Any],
        *,
        columns: list[AdminReportColumnView],
        related_links: list[AdminReportRelatedLinkView],
        rows: list[AdminReportRowView],
        summary_cards: list[AdminReportSummaryCardView],
        warnings: list[str] | None = None,
    ) -> AdminReportPreviewResponse:
        return AdminReportPreviewResponse(
            report_code=definition.code,
            report_name=definition.name,
            generated_at=datetime.now(tz=UTC),
            filters_applied=_filters_applied(filters),
            summary_cards=summary_cards,
            columns=columns,
            rows=rows,
            related_links=related_links,
            warnings=warnings or [],
        )

    def _get_definition(self, code: str) -> _ReportDefinition:
        normalized = code.strip().lower()
        for definition in _REPORT_DEFINITIONS:
            if definition.code == normalized:
                return definition
        raise ReportNotFoundError("Report definition was not found.")

    def _to_definition_view(
        self,
        session: Session,
        definition: _ReportDefinition,
    ) -> AdminReportDefinitionView:
        return AdminReportDefinitionView(
            available_filters=[
                self._to_filter_view(session, filter_definition)
                for filter_definition in definition.filters
            ],
            backend_endpoint=(
                f"POST /v1/admin/reports/{definition.code}/preview"
                if definition.status == REPORT_STATUS_AVAILABLE
                else None
            ),
            category=definition.category,
            category_label=CATEGORY_LABELS[definition.category],
            code=definition.code,
            description=definition.description,
            is_sensitive=definition.is_sensitive,
            name=definition.name,
            preview_kind=definition.preview_kind,
            required_permissions=list(definition.required_permissions),
            source_modules=list(definition.source_modules),
            status=definition.status,
            supported_exports=list(definition.supported_exports),
            unavailable_reason=definition.unavailable_reason,
        )

    def _to_filter_view(
        self,
        session: Session,
        definition: _FilterDefinition,
    ) -> AdminReportFilterDefinitionView:
        options = list(definition.static_options)
        if definition.options_source == "branches":
            options = [
                (str(branch.id), f"{branch.name} - {branch.code}")
                for branch in session.execute(
                    select(Branch).order_by(Branch.name.asc(), Branch.code.asc())
                )
                .scalars()
                .all()
            ]
        return AdminReportFilterDefinitionView(
            default_value=definition.default_value,
            key=definition.key,
            label=definition.label,
            options=[
                AdminReportFilterOptionView(code=code, label=label) for code, label in options
            ],
            options_source=definition.options_source,
            required=definition.required,
            type=definition.type,
        )

    def _validate_filters(
        self,
        definition: _ReportDefinition,
        filters: dict[str, Any],
    ) -> dict[str, Any]:
        normalized: dict[str, Any] = {}
        allowed_keys = {item.key for item in definition.filters}
        for key, value in filters.items():
            if key in allowed_keys and not _is_empty_filter(value):
                normalized[key] = str(value).strip()
        for filter_definition in definition.filters:
            if filter_definition.default_value and filter_definition.key not in normalized:
                normalized[filter_definition.key] = filter_definition.default_value
            if filter_definition.required and filter_definition.key not in normalized:
                raise ReportValidationError(f"Filter {filter_definition.label} is required.")
        if "date_from" in allowed_keys:
            normalized["date_from_dt"] = _parse_datetime_filter(
                normalized.get("date_from"),
                "date_from",
            )
        if "date_to" in allowed_keys:
            normalized["date_to_dt"] = _parse_datetime_filter(
                normalized.get("date_to"),
                "date_to",
                end_of_day=True,
            )
        if normalized.get("date_from_dt") and normalized.get("date_to_dt"):
            if normalized["date_from_dt"] > normalized["date_to_dt"]:
                raise ReportValidationError("Date range is invalid.")
        if "branch_id" in normalized:
            _uuid_filter(normalized, "branch_id")
        return normalized

    def _apply_catalog_filters(
        self,
        definitions: list[_ReportDefinition],
        *,
        category: str | None,
        export_support: str | None,
        search: str | None,
        sensitivity: str | None,
        source_module: str | None,
        status_filter: str | None,
    ) -> list[_ReportDefinition]:
        filtered = definitions
        normalized_search = _normalize(search)
        if normalized_search:
            filtered = [
                definition
                for definition in filtered
                if normalized_search
                in " ".join(
                    [
                        definition.code,
                        definition.name,
                        definition.description,
                        CATEGORY_LABELS[definition.category],
                        *definition.source_modules,
                    ]
                ).lower()
            ]
        normalized_category = _normalize_filter(category)
        if normalized_category:
            filtered = [
                definition for definition in filtered if definition.category == normalized_category
            ]
        normalized_status = _normalize_filter(status_filter)
        if normalized_status:
            filtered = [
                definition for definition in filtered if definition.status == normalized_status
            ]
        normalized_export = _normalize_filter(export_support)
        if normalized_export == "yes":
            filtered = [definition for definition in filtered if definition.supported_exports]
        elif normalized_export == "no":
            filtered = [definition for definition in filtered if not definition.supported_exports]
        normalized_sensitivity = _normalize_filter(sensitivity)
        if normalized_sensitivity == "sensitive":
            filtered = [definition for definition in filtered if definition.is_sensitive]
        elif normalized_sensitivity == "standard":
            filtered = [definition for definition in filtered if not definition.is_sensitive]
        normalized_source = _normalize_filter(source_module)
        if normalized_source:
            filtered = [
                definition
                for definition in filtered
                if normalized_source in definition.source_modules
            ]
        return filtered

    def _catalog_metrics(
        self,
        definitions: list[_ReportDefinition],
    ) -> AdminReportCatalogMetricsView:
        return AdminReportCatalogMetricsView(
            available_reports=sum(
                1 for definition in definitions if definition.status == REPORT_STATUS_AVAILABLE
            ),
            category_count=len({definition.category for definition in definitions}),
            exportable_reports=sum(1 for definition in definitions if definition.supported_exports),
            pending_backend_reports=sum(
                1
                for definition in definitions
                if definition.status == REPORT_STATUS_REQUIRES_BACKEND
            ),
            recently_generated_reports=None,
            sensitive_reports=sum(1 for definition in definitions if definition.is_sensitive),
        )

    def _catalog_filter_options(
        self,
        definitions: list[_ReportDefinition],
    ) -> AdminReportCatalogFilterOptionsView:
        source_modules = sorted(
            {module for definition in definitions for module in definition.source_modules}
        )
        return AdminReportCatalogFilterOptionsView(
            categories=[
                AdminReportFilterOptionView(code=key, label=label)
                for key, label in CATEGORY_LABELS.items()
                if key in {definition.category for definition in definitions}
            ],
            export_formats=[AdminReportFilterOptionView(code=REPORT_EXPORT_JSON, label="JSON")],
            sensitivities=[
                AdminReportFilterOptionView(code="sensitive", label="Sensibles"),
                AdminReportFilterOptionView(code="standard", label="Operativos"),
            ],
            source_modules=[
                AdminReportFilterOptionView(
                    code=module,
                    label=SOURCE_MODULE_LABELS.get(module, _humanize(module)),
                )
                for module in source_modules
            ],
            statuses=[
                AdminReportFilterOptionView(code=REPORT_STATUS_AVAILABLE, label="Disponibles"),
                AdminReportFilterOptionView(
                    code=REPORT_STATUS_REQUIRES_BACKEND,
                    label="Requieren backend",
                ),
                AdminReportFilterOptionView(code=REPORT_STATUS_COMING_SOON, label="Proximamente"),
            ],
        )


def _date_filter(required: bool = True) -> tuple[_FilterDefinition, _FilterDefinition]:
    return (
        _FilterDefinition(
            key="date_from",
            label="Desde",
            type="date",
            required=required,
        ),
        _FilterDefinition(
            key="date_to",
            label="Hasta",
            type="date",
            required=required,
        ),
    )


def _branch_filter() -> _FilterDefinition:
    return _FilterDefinition(
        key="branch_id",
        label="Sucursal",
        type="select",
        options_source="branches",
    )


def _status_filter() -> _FilterDefinition:
    return _FilterDefinition(
        key="user_status",
        label="Estado de usuario",
        type="select",
        static_options=(
            ("active", "Activos"),
            ("inactive", "Inactivos"),
            ("locked", "Bloqueados"),
        ),
    )


def _app_access_filter() -> _FilterDefinition:
    return _FilterDefinition(
        key="app_access",
        label="Acceso",
        type="select",
        static_options=(
            ("POS", "POS"),
            ("BACKOFFICE", "Backoffice"),
            ("BOTH", "Ambos"),
        ),
    )


_REPORT_DEFINITIONS = (
    _ReportDefinition(
        code="sales_summary_by_branch",
        name="Resumen de ventas por sucursal",
        description=(
            "Totales de tickets confirmados, ticket promedio y metodos de pago por sucursal."
        ),
        category="ventas_pedidos",
        source_modules=("sales", "tickets"),
        filters=(*_date_filter(), _branch_filter()),
        supported_exports=(REPORT_EXPORT_JSON,),
        status=REPORT_STATUS_AVAILABLE,
        is_sensitive=False,
        required_permissions=("sales_tickets.view",),
        preview_kind="summary_table",
    ),
    _ReportDefinition(
        code="cash_cuts_with_differences",
        name="Cortes de caja con diferencias",
        description=(
            "Cortes por periodo con esperado, contado, diferencia y estado de conciliacion."
        ),
        category="caja_finanzas",
        source_modules=("cash_close",),
        filters=(*_date_filter(), _branch_filter()),
        supported_exports=(REPORT_EXPORT_JSON,),
        status=REPORT_STATUS_AVAILABLE,
        is_sensitive=True,
        required_permissions=("cash_finance.view",),
        preview_kind="table",
    ),
    _ReportDefinition(
        code="operational_payments_by_category",
        name="Pagos operativos por categoria",
        description="Egresos operativos confirmados agrupados por categoria y metodo de pago.",
        category="caja_finanzas",
        source_modules=("payments",),
        filters=(*_date_filter(), _branch_filter()),
        supported_exports=(REPORT_EXPORT_JSON,),
        status=REPORT_STATUS_AVAILABLE,
        is_sensitive=True,
        required_permissions=("cash_finance.view",),
        preview_kind="summary_table",
    ),
    _ReportDefinition(
        code="inventory_low_negative_stock",
        name="Inventario bajo o negativo",
        description="Balances bajo minimo o bajo cero por producto, sucursal y ubicacion.",
        category="operacion_multisucursal",
        source_modules=("inventory",),
        filters=(_branch_filter(),),
        supported_exports=(REPORT_EXPORT_JSON,),
        status=REPORT_STATUS_AVAILABLE,
        is_sensitive=True,
        required_permissions=("inventory.adjust",),
        preview_kind="table",
    ),
    _ReportDefinition(
        code="waste_summary",
        name="Resumen de merma",
        description=(
            "Merma confirmada agrupada por sucursal y motivo, con cantidad y valor estimado."
        ),
        category="operacion_multisucursal",
        source_modules=("waste", "inventory"),
        filters=(*_date_filter(), _branch_filter()),
        supported_exports=(REPORT_EXPORT_JSON,),
        status=REPORT_STATUS_AVAILABLE,
        is_sensitive=True,
        required_permissions=("multibranch_operations.manage",),
        preview_kind="summary_table",
    ),
    _ReportDefinition(
        code="transfers_in_transit",
        name="Transferencias en transito",
        description="Transferencias despachadas y pendientes de recepcion entre sucursales.",
        category="operacion_multisucursal",
        source_modules=("transfers", "inventory"),
        filters=(_branch_filter(),),
        supported_exports=(REPORT_EXPORT_JSON,),
        status=REPORT_STATUS_AVAILABLE,
        is_sensitive=False,
        required_permissions=("multibranch_operations.manage",),
        preview_kind="table",
    ),
    _ReportDefinition(
        code="cleaning_compliance",
        name="Cumplimiento de limpieza",
        description="Bitacoras de limpieza por sucursal, estado, evidencia y riesgo.",
        category="calidad_higiene",
        source_modules=("cleaning_logs",),
        filters=(*_date_filter(), _branch_filter()),
        supported_exports=(REPORT_EXPORT_JSON,),
        status=REPORT_STATUS_AVAILABLE,
        is_sensitive=False,
        required_permissions=("quality_hygiene.manage",),
        preview_kind="summary_table",
    ),
    _ReportDefinition(
        code="user_access_summary",
        name="Resumen de acceso de usuarios",
        description="Usuarios, estado de cuenta, acceso a POS/Backoffice, sucursales y roles.",
        category="control",
        source_modules=("users",),
        filters=(_branch_filter(), _status_filter(), _app_access_filter()),
        supported_exports=(REPORT_EXPORT_JSON,),
        status=REPORT_STATUS_AVAILABLE,
        is_sensitive=True,
        required_permissions=("users.manage",),
        preview_kind="table",
    ),
    _ReportDefinition(
        code="purchase_supplier_activity",
        name="Actividad de proveedores",
        description="Compras, entradas y actividad por proveedor.",
        category="compras_abastecimiento",
        source_modules=("purchases", "suppliers"),
        filters=(*_date_filter(), _branch_filter()),
        supported_exports=(),
        status=REPORT_STATUS_REQUIRES_BACKEND,
        is_sensitive=True,
        required_permissions=("purchases_supply.manage",),
        preview_kind="table",
        unavailable_reason=(
            "Este reporte requiere agregados de compras por proveedor antes de generarse."
        ),
    ),
    _ReportDefinition(
        code="product_catalog_health",
        name="Salud del catalogo",
        description="Productos sin precio, sin receta o con datos incompletos.",
        category="catalogo_costos",
        source_modules=("catalog",),
        filters=(),
        supported_exports=(),
        status=REPORT_STATUS_REQUIRES_BACKEND,
        is_sensitive=True,
        required_permissions=("catalog_products.manage",),
        preview_kind="table",
        unavailable_reason="Este reporte requiere reglas canonicas de salud de catalogo.",
    ),
    _ReportDefinition(
        code="audit_activity_summary",
        name="Resumen de actividad de auditoria",
        description="Conteo de eventos por modulo, accion, resultado y sensibilidad.",
        category="control",
        source_modules=("audit",),
        filters=(*_date_filter(),),
        supported_exports=(),
        status=REPORT_STATUS_REQUIRES_BACKEND,
        is_sensitive=True,
        required_permissions=("audit.view",),
        preview_kind="summary_table",
        unavailable_reason=(
            "La consulta detallada vive en Auditoria; el resumen agregado se "
            "agregara con contrato dedicado."
        ),
    ),
)


def _column(key: str, label: str, kind: str = "text") -> AdminReportColumnView:
    return AdminReportColumnView(key=key, label=label, kind=kind)


def _card(
    label: str,
    value: str,
    helper_text: str | None = None,
    tone: str = "neutral",
) -> AdminReportSummaryCardView:
    return AdminReportSummaryCardView(
        label=label,
        value=value,
        helper_text=helper_text,
        tone=tone,
    )


def _link(
    label: str,
    module: str,
    route_hint: str,
    *,
    can_open: bool = True,
    document_id: str | None = None,
    document_type: str | None = None,
    reference: str | None = None,
) -> AdminReportRelatedLinkView:
    return AdminReportRelatedLinkView(
        can_open=can_open,
        document_id=document_id,
        document_type=document_type,
        label=label,
        module=module,
        reference=reference,
        route_hint=route_hint,
    )


def _date_range(filters: dict[str, Any]) -> tuple[datetime, datetime]:
    date_from = filters.get("date_from_dt")
    date_to = filters.get("date_to_dt")
    if not isinstance(date_from, datetime) or not isinstance(date_to, datetime):
        raise ReportValidationError("Date range is required.")
    return date_from, date_to


def _parse_datetime_filter(
    value: Any,
    key: str,
    *,
    end_of_day: bool = False,
) -> datetime | None:
    if _is_empty_filter(value):
        return None
    text = str(value).strip()
    try:
        if len(text) == 10:
            parsed_date = date.fromisoformat(text)
            return datetime.combine(
                parsed_date,
                time.max if end_of_day else time.min,
                tzinfo=UTC,
            )
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as error:
        raise ReportValidationError(f"Filter {key} must be a valid date.") from error
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _uuid_filter(filters: dict[str, Any], key: str) -> uuid.UUID | None:
    value = filters.get(key)
    if _is_empty_filter(value):
        return None
    try:
        return uuid.UUID(str(value))
    except ValueError as error:
        raise ReportValidationError(f"Filter {key} must be a valid UUID.") from error


def _optional_filter(filters: dict[str, Any], key: str) -> str | None:
    value = filters.get(key)
    if _is_empty_filter(value):
        return None
    return str(value).strip()


def _filters_applied(filters: dict[str, Any]) -> dict[str, str | None]:
    return {
        key: str(value) if value is not None else None
        for key, value in filters.items()
        if not key.endswith("_dt")
    }


def _is_empty_filter(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return value.strip() in {"", "all"}
    return False


def _normalize(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip().lower()
    return normalized or None


def _normalize_filter(value: str | None) -> str | None:
    normalized = _normalize(value)
    if normalized in {None, "all"}:
        return None
    return normalized


def _money(value: Any) -> str:
    if value is None:
        return "0.00"
    return f"{Decimal(value).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)}"


def _quantity(value: Any) -> str:
    if value is None:
        return "Sin dato"
    return f"{Decimal(value).quantize(Decimal('0.001'), rounding=ROUND_HALF_UP)}"


def _percent(part: int, whole: int) -> str:
    if whole <= 0:
        return "0%"
    value = (Decimal(part) / Decimal(whole) * Decimal("100")).quantize(
        Decimal("0.1"),
        rounding=ROUND_HALF_UP,
    )
    return f"{value}%"


def _date_text(value: datetime | None) -> str:
    if value is None:
        return "Sin registro"
    return value.astimezone(UTC).isoformat()


def _cash_cut_folio(cash_cut_id: uuid.UUID) -> str:
    return f"CC-{str(cash_cut_id).split('-', maxsplit=1)[0].upper()}"


def _transfer_folio(transfer_id: uuid.UUID) -> str:
    return f"ENV-{str(transfer_id).split('-', maxsplit=1)[0].upper()}"


def _surface_label(values: list[str]) -> str:
    surfaces = {value.upper() for value in values}
    if {IDENTITY_SURFACE_POS, IDENTITY_SURFACE_BACKOFFICE} <= surfaces:
        return "Both"
    if IDENTITY_SURFACE_BACKOFFICE in surfaces:
        return "Backoffice"
    if IDENTITY_SURFACE_POS in surfaces:
        return "POS"
    return "Sin acceso"


def _matches_surface(values: list[str], app_access: str) -> bool:
    normalized = app_access.upper()
    surfaces = {value.upper() for value in values}
    if normalized == "BOTH":
        return {IDENTITY_SURFACE_POS, IDENTITY_SURFACE_BACKOFFICE} <= surfaces
    return normalized in surfaces


def _user_status(user: User) -> str:
    if user.is_locked:
        return "locked"
    return "active" if user.is_active else "inactive"


def _user_warning(user: User, branches: list[Branch], roles: list[Role]) -> str:
    if not user.is_active:
        return "Usuario inactivo"
    if user.is_locked:
        return "Cuenta bloqueada"
    allowed_surfaces = {surface.upper() for surface in user.allowed_surfaces}
    if IDENTITY_SURFACE_POS in allowed_surfaces and not branches:
        return "POS sin sucursal"
    if IDENTITY_SURFACE_BACKOFFICE in allowed_surfaces and not roles:
        return "Backoffice sin rol"
    return "Sin advertencias"


def _join_names(items: list[Any]) -> str:
    names = [str(item.name) for item in items]
    return ", ".join(names) if names else "Sin datos"


def _humanize(value: str) -> str:
    return value.replace("_", " ").replace(".", " ").title()
