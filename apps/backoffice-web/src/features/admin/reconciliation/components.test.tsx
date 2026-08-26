import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactElement } from "react";
import { renderToString } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { AdminReconciliationDetailPanel } from "./components/AdminReconciliationDetailPanel";
import { AdminReconciliationFilters } from "./components/AdminReconciliationFilters";
import { AdminReconciliationTable } from "./components/AdminReconciliationTable";
import { AdminReconciliationWorkflowPanel } from "./components/AdminReconciliationWorkflowPanel";
import { AdminReconciliationPage } from "./pages/AdminReconciliationPage";
import type {
  AdminPendingDiscrepancyItem,
  AdminReconciliationDetail,
  AdminReconciliationFilterOptions,
  AdminReconciliationListFilters,
  AdminReconciliationListItem,
} from "./types";

const filterOptions: AdminReconciliationFilterOptions = {
  branches: [{ id: "branch-1", label: "Centro" }],
  cashiers: [{ id: "user-1", label: "Admin" }],
  discrepancyTypes: [
    { id: "SHORTAGE", label: "Faltantes" },
    { id: "OVERAGE", label: "Sobrantes" },
  ],
  evidenceStates: [
    { id: "WITH_EVIDENCE", label: "Con evidencia" },
    { id: "WITHOUT_EVIDENCE", label: "Sin evidencia" },
  ],
  paymentMethods: [
    { id: "CASH", label: "Efectivo" },
    { id: "CARD", label: "Tarjeta" },
  ],
  reasonCodes: [
    { id: "COUNTING_ERROR", label: "Error de conteo" },
    { id: "CASH_OVER", label: "Sobrante de efectivo" },
    { id: "OTHER", label: "Otro" },
  ],
  sourceTypes: [{ id: "CASH_CUT", label: "Corte de caja" }],
  statuses: [
    { id: "IN_REVIEW", label: "En revision" },
    { id: "RECONCILED", label: "Conciliada" },
  ],
  workstations: [{ id: "station-1", label: "Mostrador 1 (POS-1)" }],
};

const filters: AdminReconciliationListFilters = {
  amountMax: "",
  amountMin: "",
  branchId: "all",
  cashierId: "all",
  dateFrom: null,
  dateTo: null,
  discrepancyType: "all",
  evidenceState: "all",
  page: 1,
  pageSize: 25,
  paymentMethod: "all",
  search: "",
  sourceType: "all",
  status: "all",
  workstationId: "all",
};

const reconciliation: AdminReconciliationListItem = {
  actualAmount: "1125.00",
  branchId: "branch-1",
  branchName: "Centro",
  differenceAmount: "5.00",
  differenceDirection: "OVERAGE",
  expectedAmount: "1120.00",
  folio: "CON-100",
  hasEvidence: true,
  id: "reconciliation-1",
  occurredAt: "2026-05-21T18:00:00Z",
  operatorId: "user-1",
  operatorName: "Admin",
  paymentMethod: "CASH",
  reasonCode: "COUNTING_ERROR",
  sourceDocumentId: "close-1",
  sourceReference: "CC-100",
  sourceType: "CASH_CUT",
  status: "IN_REVIEW",
  updatedAt: "2026-05-21T19:00:00Z",
  warningState: "warning",
  workstationId: "station-1",
  workstationName: "Mostrador 1",
};

const pendingDiscrepancy: AdminPendingDiscrepancyItem = {
  actualAmount: "1125.00",
  branchId: "branch-1",
  branchName: "Centro",
  differenceAmount: "5.00",
  differenceDirection: "OVERAGE",
  expectedAmount: "1120.00",
  occurredAt: "2026-05-21T18:00:00Z",
  operatorId: "user-1",
  operatorName: "Admin",
  paymentMethod: "CASH",
  sourceDocumentId: "close-1",
  sourceReference: "CC-100",
  sourceType: "CASH_CUT",
  suggestedWarningState: "warning",
  workstationId: "station-1",
  workstationName: "Mostrador 1",
};

const detail: AdminReconciliationDetail = {
  availableActions: {
    canAttachEvidence: false,
    canCopyFolio: true,
    canExportReport: false,
    canOpenSource: true,
    canResolve: true,
    canSaveNotes: true,
    canVoid: false,
    note: "La evidencia se registra como nota; adjuntos de archivo aun no tienen contrato.",
  },
  backendContract: {
    createEndpoint: "POST /v1/admin/reconciliation",
    detailEndpoint: "GET /v1/admin/reconciliation/{reconciliation_id}",
    evidenceEndpoint: null,
    exportEndpoint: null,
    listEndpoint: "GET /v1/admin/reconciliation",
    pendingEndpoint: "GET /v1/admin/reconciliation/pending",
    resolveEndpoint: "POST /v1/admin/reconciliation/{reconciliation_id}/resolve",
  },
  differenceBreakdown: {
    actualAmount: "1125.00",
    differenceAmount: "5.00",
    direction: "OVERAGE",
    expectedAmount: "1120.00",
    paymentMethod: "CASH",
    toleranceNote: "No hay tolerancia financiera configurable para este modulo.",
    toleranceStatus: "NOT_CONFIGURED",
  },
  evidence: {
    emptyState: "Esta conciliacion no tiene evidencia adjunta.",
    evidenceNote: "Foto de conteo.",
    files: [],
    hasEvidence: true,
    isSupported: true,
  },
  explanationReason: {
    notes: "Sobrante documentado.",
    reasonCode: "COUNTING_ERROR",
    reasonLabel: "Error de conteo",
    responsibleUserId: "user-1",
    responsibleUserName: "Admin",
    timestamp: "2026-05-21T19:00:00Z",
  },
  overview: {
    ...reconciliation,
    createdAt: "2026-05-21T19:00:00Z",
    resolvedAt: null,
  },
  relatedDocuments: [
    {
      amount: "1125.00",
      documentType: "CASH_CUT",
      folio: "CC-100",
      id: "close-1",
      occurredAt: "2026-05-21T18:00:00Z",
      routeHint: "/admin/cortes-caja?cashSession=close-1",
      status: "SOURCE",
    },
    {
      amount: "100.00",
      documentType: "TICKET",
      folio: "TCK-100",
      id: "ticket-1",
      occurredAt: "2026-05-21T14:00:00Z",
      routeHint: "/admin/ventas?ticket=ticket-1",
      status: "PAID",
    },
  ],
  resolution: {
    canResolve: true,
    evidenceSummary: "Foto de conteo.",
    finalNotes: "Sobrante documentado.",
    requiredFields: ["reason_code", "notes when reason is OTHER"],
    resolutionReason: "Error de conteo",
    resolvedAt: null,
    resolvedByUserId: null,
    resolvedByUserName: null,
    status: "IN_REVIEW",
  },
  sourceDocumentContext: {
    closedAt: "2026-05-21T18:00:00Z",
    countedCashAmount: "1125.00",
    differenceAmount: "5.00",
    expectedCashAmount: "1120.00",
    externalReportedAmount: null,
    note: "El corte se mantiene inmutable; esta conciliacion documenta la resolucion.",
    openedAt: "2026-05-21T10:00:00Z",
    operationalPaymentCategory: null,
    paymentMethod: "CASH",
    refundOriginalTicket: null,
    sourceReference: "CC-100",
    sourceRouteHint: "/admin/cortes-caja?cashSession=close-1",
    sourceType: "CASH_CUT",
    terminalReference: null,
  },
};

function render(element: ReactElement) {
  return renderToString(element);
}

describe("admin reconciliation UI components", () => {
  it("renders the reconciliation page shell with create action", () => {
    const queryClient = new QueryClient();
    const html = render(
      <QueryClientProvider client={queryClient}>
        <AdminReconciliationPage />
      </QueryClientProvider>,
    );

    expect(html).toContain("Conciliacion");
    expect(html).toContain("Nueva conciliacion");
    expect(html).toContain(
      "Selecciona una conciliacion para revisar diferencia, documentos relacionados y resolucion.",
    );
  });

  it("renders filters and quick filters", () => {
    const html = render(
      <AdminReconciliationFilters
        filters={filters}
        isBackendConnected={true}
        options={filterOptions}
        onChange={() => undefined}
      />,
    );

    expect(html).toContain("Todas las sucursales");
    expect(html).toContain("Todos los responsables");
    expect(html).toContain("Todas las diferencias");
    expect(html).toContain("Con evidencia");
    expect(html).toContain("Pendientes");
    expect(html).toContain("Tarjeta");
  });

  it("renders empty and populated reconciliation table states", () => {
    const emptyHtml = render(
      <AdminReconciliationTable
        page={1}
        pageSize={25}
        reconciliations={[]}
        total={0}
        onCopyFolio={() => undefined}
        onPageChange={() => undefined}
        onResolve={() => undefined}
        onSelectReconciliation={() => undefined}
      />,
    );
    expect(emptyHtml).toContain("No hay conciliaciones para los filtros seleccionados.");

    const tableHtml = render(
      <AdminReconciliationTable
        page={1}
        pageSize={25}
        reconciliations={[reconciliation]}
        total={1}
        onCopyFolio={() => undefined}
        onPageChange={() => undefined}
        onResolve={() => undefined}
        onSelectReconciliation={() => undefined}
      />,
    );

    expect(tableHtml).toContain("CON-100");
    expect(tableHtml).toContain("CC-100");
    expect(tableHtml).toContain("Corte de caja");
    expect(tableHtml).toContain("Resolver");
    expect(tableHtml).toContain("Evidencia");
  });

  it("renders reconciliation detail sections and related documents", () => {
    const html = render(
      <AdminReconciliationDetailPanel
        detail={detail}
        selectedReconciliation={reconciliation}
        onCopyFolio={() => undefined}
        onResolve={() => undefined}
      />,
    );

    expect(html).toContain("Diferencia");
    expect(html).toContain("Documento origen");
    expect(html).toContain("Explicacion");
    expect(html).toContain("Evidencia");
    expect(html).toContain("Documentos relacionados");
    expect(html).toContain("Resolucion");
    expect(html).toContain("TCK-100");
    expect(html).toContain("El corte se mantiene inmutable");
  });

  it("renders the create workflow and pending source summary", () => {
    const html = render(
      <AdminReconciliationWorkflowPanel
        mode="create"
        reasonOptions={filterOptions.reasonCodes}
        source={pendingDiscrepancy}
        onCancel={() => undefined}
        onCreate={() => undefined}
        onResolve={() => undefined}
      />,
    );

    expect(html).toContain("Nueva conciliacion");
    expect(html).toContain("CC-100");
    expect(html).toContain("Confirmar conciliacion");
    expect(html).toContain("Error de conteo");
    expect(html).toContain("Nota de evidencia");
  });

  it("renders no selected reconciliation empty state", () => {
    const html = render(
      <AdminReconciliationDetailPanel
        detail={null}
        selectedReconciliation={null}
        onCopyFolio={() => undefined}
        onResolve={() => undefined}
      />,
    );

    expect(html).toContain("Sin conciliacion seleccionada");
    expect(html).toContain(
      "Selecciona una conciliacion para revisar diferencia, documentos relacionados y resolucion.",
    );
  });
});
