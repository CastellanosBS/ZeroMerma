import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactElement } from "react";
import { renderToString } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { AdminWasteFilters } from "./components/AdminWasteFilters";
import { AdminWasteDetailPanel } from "./components/AdminWasteDetailPanel";
import { AdminWasteTable } from "./components/AdminWasteTable";
import { AdminWasteWorkflowPanel } from "./components/AdminWasteWorkflowPanel";
import { AdminWastePage } from "./pages/AdminWastePage";
import type {
  AdminWasteDetail,
  AdminWasteFilterOptions,
  AdminWasteListFilters,
  AdminWasteListItem,
} from "./types";

const filterOptions: AdminWasteFilterOptions = {
  branches: [{ id: "branch-1", label: "Centro - MAIN" }],
  classes: [{ id: "class-1", label: "Pan dulce" }],
  evidenceStates: [{ id: "without_evidence", label: "Sin evidencia" }],
  impactLevels: [{ id: "high", label: "Alto impacto" }],
  locations: [{ id: "BACKROOM", label: "Fondo" }],
  operators: [{ id: "user-1", label: "Admin Backoffice" }],
  productKinds: [{ id: "FINISHED_GOOD", label: "Producto terminado" }],
  products: [{ id: "product-1", label: "Concha vainilla - CONCHA-VAN" }],
  reasons: [
    {
      code: "DAMAGED",
      displayOrder: 20,
      highImpactDefault: false,
      label: "Danado",
      requiresEvidence: false,
      requiresNote: true,
    },
  ],
  statuses: [{ id: "COMMITTED", label: "Confirmada" }],
};

const filters: AdminWasteListFilters = {
  evidenceState: "all",
  impactLevel: "all",
  locationCode: "all",
  page: 1,
  pageSize: 25,
  reasonCode: "all",
  search: "",
  status: "all",
  warningState: "all",
};

const wasteRecord: AdminWasteListItem = {
  branchId: "branch-1",
  branchName: "Centro",
  createdAt: "2026-05-20T10:00:00Z",
  estimatedValue: "120.00",
  folio: "WST-12345678",
  hasEvidence: false,
  id: "waste-1",
  impactLevel: "high",
  lineCount: 1,
  locationCode: "BACKROOM",
  locationName: "Fondo",
  operatorName: "Admin Backoffice",
  productCode: "CONCHA-VAN",
  productId: "product-1",
  productKind: "FINISHED_GOOD",
  productName: "Concha vainilla",
  quantity: "12.000",
  reasonCode: "DAMAGED",
  reasonLabel: "Danado",
  status: "COMMITTED",
  uom: "PCS",
  warningState: "warning",
  warnings: [{ code: "high_impact", message: "Merma marcada como alto impacto.", severity: "warning" }],
};

const wasteDetail: AdminWasteDetail = {
  availableActions: {
    canCreateCorrection: true,
    canEdit: false,
    canOpenInventoryMovement: true,
    canPrint: false,
  },
  evidence: {
    attachmentSupported: false,
    evidenceItems: [],
    notes: "Charola danada",
  },
  inventoryImpact: {
    integrationAvailable: true,
    movements: [
      {
        balanceAfter: "8.000",
        direction: "OUT",
        id: "movement-1",
        locationCode: "BACKROOM",
        movementType: "WASTE_RECORD",
        productId: "product-1",
        quantity: "12.000",
        sourceDocumentId: "waste-1",
        sourceDocumentType: "WASTE_RECORD",
        unitOfMeasure: "PCS",
      },
    ],
  },
  lines: [
    {
      estimatedValue: "120.00",
      lineNumber: 1,
      productCode: "CONCHA-VAN",
      productId: "product-1",
      productKind: "FINISHED_GOOD",
      productName: "Concha vainilla",
      quantity: "12.000",
      uom: "PCS",
    },
  ],
  overview: {
    branchId: "branch-1",
    branchName: "Centro",
    confirmedAt: "2026-05-20T10:00:00Z",
    createdAt: "2026-05-20T10:00:00Z",
    folio: "WST-12345678",
    hasEvidence: false,
    id: "waste-1",
    impactLevel: "high",
    locationCode: "BACKROOM",
    locationName: "Fondo",
    notes: "Charola danada",
    operatorId: "user-1",
    operatorName: "Admin Backoffice",
    quantity: "12.000",
    reasonCode: "DAMAGED",
    reasonLabel: "Danado",
    status: "COMMITTED",
    uom: "PCS",
    warningState: "warning",
    workstationCode: "POS-01",
    workstationName: "Caja principal",
  },
  productInventoryContext: {
    branchId: "branch-1",
    branchName: "Centro",
    classId: "class-1",
    className: "Pan dulce",
    currentStock: "8.000",
    productCode: "CONCHA-VAN",
    productId: "product-1",
    productIsActive: true,
    productKind: "FINISHED_GOOD",
    productName: "Concha vainilla",
    stockAfter: "8.000",
    stockBefore: "20.000",
    uom: "PCS",
  },
  reasonClassification: {
    category: "DAMAGED",
    description: "Producto danado fisicamente.",
    label: "Danado",
    requiresEvidence: false,
    requiresNote: true,
  },
  relatedDocuments: [
    {
      documentId: "movement-1",
      documentType: "INVENTORY_MOVEMENT",
      folio: "WASTE_RECORD",
      status: "OUT",
    },
  ],
  warnings: [{ code: "high_impact", message: "Merma marcada como alto impacto.", severity: "warning" }],
};

function render(element: ReactElement) {
  return renderToString(element);
}

describe("admin waste UI components", () => {
  it("renders the waste page shell", () => {
    const queryClient = new QueryClient();

    const html = render(
      <QueryClientProvider client={queryClient}>
        <AdminWastePage />
      </QueryClientProvider>,
    );

    expect(html).toContain("Merma");
    expect(html).toContain("Nueva merma");
    expect(html).toContain("Selecciona una merma para revisar producto, motivo, evidencia e impacto en inventario.");
  });

  it("renders operational filters", () => {
    const html = render(
      <AdminWasteFilters filters={filters} isBackendConnected={true} options={filterOptions} onChange={() => undefined} />,
    );

    expect(html).toContain("Buscar");
    expect(html).toContain("Desde");
    expect(html).toContain("Producto");
    expect(html).toContain("Evidencia");
    expect(html).toContain("Sin evidencia");
  });

  it("renders empty and populated table states", () => {
    const emptyHtml = render(
      <AdminWasteTable
        backendContract={{
          createEndpoint: "POST /v1/admin/waste",
          detailEndpoint: "GET /v1/admin/waste/{waste_id}",
          inventoryMovementContract: "Confirmed waste creates WASTE_RECORD inventory movement.",
          listEndpoint: "GET /v1/admin/waste",
          reasonsEndpoint: "GET /v1/admin/waste/reasons",
        }}
        isLoading={false}
        isSubmitting={false}
        page={1}
        pageSize={25}
        total={0}
        wasteRecords={[]}
        onOpenInventory={() => undefined}
        onOpenProduct={() => undefined}
        onPageChange={() => undefined}
        onSelectWaste={() => undefined}
      />,
    );
    expect(emptyHtml).toContain("No hay mermas registradas para los filtros seleccionados.");

    const tableHtml = render(
      <AdminWasteTable
        backendContract={{
          createEndpoint: "POST /v1/admin/waste",
          detailEndpoint: "GET /v1/admin/waste/{waste_id}",
          inventoryMovementContract: "Confirmed waste creates WASTE_RECORD inventory movement.",
          listEndpoint: "GET /v1/admin/waste",
          reasonsEndpoint: "GET /v1/admin/waste/reasons",
        }}
        isLoading={false}
        isSubmitting={false}
        page={1}
        pageSize={25}
        total={1}
        wasteRecords={[wasteRecord]}
        onOpenInventory={() => undefined}
        onOpenProduct={() => undefined}
        onPageChange={() => undefined}
        onSelectWaste={() => undefined}
      />,
    );

    expect(tableHtml).toContain("Ubicacion / origen");
    expect(tableHtml).toContain("Valor estimado");
    expect(tableHtml).toContain("Concha vainilla");
    expect(tableHtml).toContain("Sin evidencia");
  });

  it("renders detail and create flow sections", () => {
    const detailHtml = render(
      <AdminWasteDetailPanel
        isLoading={false}
        wasteDetail={wasteDetail}
        wastePreview={wasteRecord}
        onOpenBranch={() => undefined}
        onOpenCorrection={() => undefined}
        onOpenInventory={() => undefined}
        onOpenProduct={() => undefined}
      />,
    );

    expect(detailHtml).toContain("Producto e inventario");
    expect(detailHtml).toContain("Motivo y evidencia");
    expect(detailHtml).toContain("Impacto de inventario");
    expect(detailHtml).toContain("Documentos relacionados");

    const workflowHtml = render(
      <AdminWasteWorkflowPanel
        branchOptions={filterOptions.branches}
        isSubmitting={false}
        locationOptions={filterOptions.locations}
        productOptions={filterOptions.products}
        reasonOptions={filterOptions.reasons}
        onClose={() => undefined}
        onCreate={() => undefined}
      />,
    );

    expect(workflowHtml).toContain("Nueva merma");
    expect(workflowHtml).toContain("Confirmar baja de inventario");
    expect(workflowHtml).toContain("Confirmar merma");
  });
});
