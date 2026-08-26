import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactElement } from "react";
import { renderToString } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { AdminPurchaseDetailPanel } from "./components/AdminPurchaseDetailPanel";
import { AdminPurchasesFilters } from "./components/AdminPurchasesFilters";
import { AdminPurchasesTable } from "./components/AdminPurchasesTable";
import { AdminPurchaseWorkflowPanel } from "./components/AdminPurchaseWorkflowPanel";
import { AdminPurchasesPage } from "./pages/AdminPurchasesPage";
import type {
  AdminPurchaseDetail,
  AdminPurchaseFilterOptions,
  AdminPurchaseListFilters,
  AdminPurchaseListItem,
} from "./types";

const filterOptions: AdminPurchaseFilterOptions = {
  branches: [{ id: "branch-1", label: "Centro - MAIN" }],
  operators: [{ id: "user-1", label: "Admin" }],
  productKinds: [{ id: "RAW_MATERIAL", label: "Materia prima" }],
  products: [{ id: "product-1", label: "Harina - HARINA" }],
  statuses: [
    { id: "DRAFT", label: "Borrador" },
    { id: "ORDERED", label: "Pendiente" },
    { id: "PARTIALLY_RECEIVED", label: "Parcial" },
    { id: "RECEIVED", label: "Recibida" },
  ],
  suppliers: [{ id: "supplier-1", label: "Harinas del Centro" }],
};

const filters: AdminPurchaseListFilters = {
  discrepancyState: "all",
  page: 1,
  pageSize: 25,
  productKind: "all",
  search: "",
  status: "all",
  warningState: "all",
};

const purchase: AdminPurchaseListItem = {
  branchId: "branch-1",
  branchName: "Centro",
  createdAt: "2026-05-20T10:00:00Z",
  documentDate: "2026-05-20T10:00:00Z",
  documentType: "PURCHASE",
  externalDocumentNumber: "REM-100",
  folio: "CMP-100",
  hasDiscrepancy: true,
  id: "purchase-1",
  lineCount: 1,
  operatorName: "Admin",
  receivedAt: "2026-05-20T11:00:00Z",
  receivedUnitCount: "2.000",
  status: "PARTIALLY_RECEIVED",
  supplierId: "supplier-1",
  supplierName: "Harinas del Centro",
  totalAmount: "120.0000",
  warningState: "critical",
  warnings: [{ code: "receipt_discrepancy", message: "Diferencia de recepcion.", severity: "critical" }],
};

const purchaseDetail: AdminPurchaseDetail = {
  availableActions: {
    canCancel: false,
    canConfirm: false,
    canEdit: false,
    canReceive: true,
    canViewMovements: true,
  },
  costSummary: {
    currency: "MXN",
    receivedTotal: "24.0000",
    subtotal: "120.0000",
    taxes: null,
    total: "120.0000",
  },
  inventoryImpact: {
    integrationAvailable: true,
    movements: [
      {
        balanceAfter: "2.000",
        branchId: "branch-1",
        direction: "IN",
        id: "movement-1",
        locationCode: "BACKROOM",
        movementType: "PURCHASE_RECEIPT",
        productId: "product-1",
        quantity: "2.000",
        sourceDocumentId: "receipt-1",
        sourceDocumentType: "PURCHASE_RECEIPT",
        unitOfMeasure: "KG",
      },
    ],
    notes: null,
  },
  lines: [
    {
      discrepancy: "8.000",
      discrepancyReason: "Entrega parcial",
      lineStatus: "partial",
      lineTotal: "120.0000",
      notes: null,
      orderedQuantity: "10.000",
      pendingQuantity: "8.000",
      productCode: "HARINA",
      productId: "product-1",
      productKind: "RAW_MATERIAL",
      productName: "Harina",
      purchaseLineId: "line-1",
      receivedQuantity: "2.000",
      standardCost: null,
      supplierLastKnownPrice: "12.0000",
      unitCost: "12.0000",
      unitOfMeasure: "KG",
    },
  ],
  overview: {
    branchId: "branch-1",
    branchName: "Centro",
    confirmedAt: "2026-05-20T10:10:00Z",
    createdAt: "2026-05-20T10:00:00Z",
    createdByUserId: "user-1",
    createdByUserName: "Admin",
    documentDate: "2026-05-20T10:00:00Z",
    documentType: "PURCHASE",
    externalDocumentNumber: "REM-100",
    externalDocumentType: "REMISSION",
    folio: "CMP-100",
    hasDiscrepancy: true,
    id: "purchase-1",
    lineCount: 1,
    notes: "Compra semanal",
    receivedAt: "2026-05-20T11:00:00Z",
    receivedUnitCount: "2.000",
    status: "PARTIALLY_RECEIVED",
    supplierId: "supplier-1",
    supplierName: "Harinas del Centro",
    totalAmount: "120.0000",
    warningState: "critical",
  },
  receipt: {
    expectedQuantity: "10.000",
    hasDiscrepancy: true,
    pendingQuantity: "8.000",
    receiptCount: 1,
    receivedQuantity: "2.000",
    state: "partial",
  },
  receivingBranch: {
    branchCode: "MAIN",
    branchId: "branch-1",
    branchIsActive: true,
    branchName: "Centro",
    timezone: "America/Hermosillo",
  },
  relatedDocuments: [{ documentId: "receipt-1", documentType: "PURCHASE_RECEIPT", folio: "REC-1", status: "COMMITTED" }],
  supplierContext: {
    commercialName: "Harinas Centro",
    leadTimeDays: 2,
    paymentTermsSummary: "Credito 15 dias",
    primaryContact: "Ana - 555",
    status: "ACTIVE",
    supplierId: "supplier-1",
    supplierName: "Harinas del Centro",
  },
  warnings: [{ code: "receipt_discrepancy", message: "Diferencia de recepcion.", severity: "critical" }],
};

function render(element: ReactElement) {
  return renderToString(element);
}

describe("admin purchases UI components", () => {
  it("renders the purchases page shell", () => {
    const queryClient = new QueryClient();
    const html = render(
      <QueryClientProvider client={queryClient}>
        <AdminPurchasesPage />
      </QueryClientProvider>,
    );

    expect(html).toContain("Compras / entradas");
    expect(html).toContain("Nueva compra");
    expect(html).toContain("Nueva entrada directa");
    expect(html).toContain("Selecciona una compra para revisar proveedor, productos, recepcion e impacto en inventario.");
  });

  it("renders filters and quick filters", () => {
    const html = render(
      <AdminPurchasesFilters filters={filters} isBackendConnected={true} options={filterOptions} onChange={() => undefined} />,
    );

    expect(html).toContain("Proveedor");
    expect(html).toContain("Sucursal");
    expect(html).toContain("Con discrepancias");
    expect(html).toContain("Materia prima");
    expect(html).toContain("Datos conectados");
  });

  it("renders empty and populated purchase table states with lifecycle actions", () => {
    const backendContract = {
      cancelEndpoint: "POST /v1/admin/purchases/{purchase_id}/cancel",
      confirmEndpoint: "POST /v1/admin/purchases/{purchase_id}/confirm",
      createDirectEntryEndpoint: "POST /v1/admin/purchases/direct-entry",
      createEndpoint: "POST /v1/admin/purchases",
      detailEndpoint: "GET /v1/admin/purchases/{purchase_id}",
      listEndpoint: "GET /v1/admin/purchases",
      receiveEndpoint: "POST /v1/admin/purchases/{purchase_id}/receive",
      updateEndpoint: "PATCH /v1/admin/purchases/{purchase_id}",
    };
    const emptyHtml = render(
      <AdminPurchasesTable
        backendContract={backendContract}
        page={1}
        pageSize={25}
        purchases={[]}
        total={0}
        onCancel={() => undefined}
        onConfirm={() => undefined}
        onOpenBranch={() => undefined}
        onOpenSupplier={() => undefined}
        onPageChange={() => undefined}
        onReceive={() => undefined}
        onSelectPurchase={() => undefined}
      />,
    );
    expect(emptyHtml).toContain("No hay compras o entradas para los filtros seleccionados.");

    const tableHtml = render(
      <AdminPurchasesTable
        backendContract={backendContract}
        page={1}
        pageSize={25}
        purchases={[purchase]}
        total={1}
        onCancel={() => undefined}
        onConfirm={() => undefined}
        onOpenBranch={() => undefined}
        onOpenSupplier={() => undefined}
        onPageChange={() => undefined}
        onReceive={() => undefined}
        onSelectPurchase={() => undefined}
      />,
    );

    expect(tableHtml).toContain("CMP-100");
    expect(tableHtml).toContain("Harinas del Centro");
    expect(tableHtml).toContain("Discrepancia");
    expect(tableHtml).toContain("Recibir");
  });

  it("renders purchase detail sections, movements and warnings", () => {
    const html = render(
      <AdminPurchaseDetailPanel
        purchaseDetail={purchaseDetail}
        purchasePreview={purchase}
        onCancel={() => undefined}
        onConfirm={() => undefined}
        onOpenBranch={() => undefined}
        onOpenProduct={() => undefined}
        onOpenSupplier={() => undefined}
        onReceive={() => undefined}
      />,
    );

    expect(html).toContain("Proveedor");
    expect(html).toContain("Sucursal receptora");
    expect(html).toContain("Lineas de compra / recepcion");
    expect(html).toContain("Recepcion / discrepancias");
    expect(html).toContain("Costo / valuacion");
    expect(html).toContain("Impacto en inventario");
    expect(html).toContain("Recepcion de compra");
    expect(html).toContain("receipt_discrepancy");
  });

  it("renders create, direct entry, receive and validation surfaces", () => {
    const createHtml = render(
      <AdminPurchaseWorkflowPanel
        errorMessage="Selecciona un proveedor."
        isSubmitting={false}
        mode="purchase"
        options={filterOptions}
        onClose={() => undefined}
        onSubmitCancel={() => undefined}
        onSubmitDirectEntry={() => undefined}
        onSubmitPurchase={() => undefined}
        onSubmitReceipt={() => undefined}
      />,
    );
    expect(createHtml).toContain("Nueva compra");
    expect(createHtml).toContain("Confirmar compra al guardar");
    expect(createHtml).toContain("Selecciona un proveedor.");

    const directHtml = render(
      <AdminPurchaseWorkflowPanel
        isSubmitting={false}
        mode="direct"
        options={filterOptions}
        onClose={() => undefined}
        onSubmitCancel={() => undefined}
        onSubmitDirectEntry={() => undefined}
        onSubmitPurchase={() => undefined}
        onSubmitReceipt={() => undefined}
      />,
    );
    expect(directHtml).toContain("Nueva entrada directa");
    expect(directHtml).toContain("Cantidad recibida");

    const receiveHtml = render(
      <AdminPurchaseWorkflowPanel
        isSubmitting={false}
        mode="receive"
        options={filterOptions}
        purchase={purchaseDetail}
        onClose={() => undefined}
        onSubmitCancel={() => undefined}
        onSubmitDirectEntry={() => undefined}
        onSubmitPurchase={() => undefined}
        onSubmitReceipt={() => undefined}
      />,
    );
    expect(receiveHtml).toContain("Recibir mercancia");
    expect(receiveHtml).toContain("Razon de discrepancia");
    expect(receiveHtml).toContain("Harina");
  });
});
