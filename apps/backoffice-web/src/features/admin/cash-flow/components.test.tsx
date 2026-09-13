import { withCapabilities } from "../../../test-support/authorization";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactElement } from "react";
import { renderToString } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { AdminCashFlowDetailPanel } from "./components/AdminCashFlowDetailPanel";
import { AdminCashFlowFilters } from "./components/AdminCashFlowFilters";
import { AdminCashFlowTable } from "./components/AdminCashFlowTable";
import { AdminCashFlowPage } from "./pages/AdminCashFlowPage";
import type {
  AdminCashFlowFilterOptions,
  AdminCashFlowListFilters,
  AdminCashFlowMovementDetail,
  AdminCashFlowMovementListItem,
} from "./types";

const filterOptions: AdminCashFlowFilterOptions = {
  branches: [{ id: "branch-1", label: "Centro" }],
  categories: [{ id: "Pago operativo", label: "Pago operativo" }],
  directions: [
    { id: "INFLOW", label: "Entradas" },
    { id: "OUTFLOW", label: "Salidas" },
  ],
  operators: [{ id: "user-1", label: "Admin" }],
  paymentMethods: [
    { id: "CASH", label: "Efectivo" },
    { id: "CARD", label: "Tarjeta" },
  ],
  reconciliationStates: [
    { id: "PENDING", label: "Pendiente" },
    { id: "NOT_REQUIRED", label: "No requerida" },
  ],
  sourceTypes: [
    { id: "SALE", label: "Venta" },
    { id: "OPERATIONAL_PAYMENT", label: "Pago operativo" },
  ],
  workstations: [{ id: "station-1", label: "Mostrador 1" }],
};

const filters: AdminCashFlowListFilters = {
  amountMax: "",
  amountMin: "",
  branchId: "all",
  category: "all",
  dateFrom: null,
  dateTo: null,
  direction: "all",
  operatorId: "all",
  page: 1,
  pageSize: 25,
  paymentMethod: "all",
  reconciliationState: "all",
  search: "",
  sourceType: "all",
  workstationId: "all",
};

const movement: AdminCashFlowMovementListItem = {
  amount: "125.00",
  branchId: "branch-1",
  branchName: "Centro",
  category: "Pago operativo",
  currency: "MXN",
  direction: "OUTFLOW",
  id: "OPERATIONAL_PAYMENT:payment-1",
  occurredAt: "2026-05-21T18:00:00Z",
  operatorId: "user-1",
  operatorName: "Admin",
  paymentMethod: "CASH",
  reconciliationStatus: "NOT_REQUIRED",
  sourceDocumentId: "payment-1",
  sourceReference: "PAGO-100",
  sourceType: "OPERATIONAL_PAYMENT",
  warningState: "ok",
  workstationId: "station-1",
  workstationName: "Mostrador 1",
};

const detail: AdminCashFlowMovementDetail = {
  availableActions: {
    canCopyReference: true,
    canExport: false,
    canOpenCashCut: true,
    canOpenReconciliation: false,
    canOpenSource: true,
    note: "La exportacion aun no tiene contrato backend.",
  },
  backendContract: {
    detailEndpoint: "GET /v1/admin/cash-flow/{movement_id}",
    exportEndpoint: null,
    listEndpoint: "GET /v1/admin/cash-flow",
    trendEndpoint: null,
  },
  financialClassification: {
    affectsBankSettlement: false,
    affectsCashDrawer: true,
    cardImpact: "0.00",
    cashImpact: "-125.00",
    direction: "OUTFLOW",
    netEffect: "-125.00",
    note: null,
    paymentMethod: "CASH",
    sourceCategory: "Pago operativo",
  },
  overview: movement,
  reconciliation: {
    message: "Este movimiento no requiere conciliacion.",
    reasonLabel: null,
    reconciliationFolio: null,
    reconciliationId: null,
    routeHint: null,
    status: "NOT_REQUIRED",
    unresolvedAmount: null,
  },
  relatedDocuments: [
    {
      amount: "125.00",
      documentType: "OPERATIONAL_PAYMENT",
      folio: "PAGO-100",
      id: "payment-1",
      occurredAt: "2026-05-21T18:00:00Z",
      routeHint: "/admin/pagos-operativos?payment=payment-1",
      status: "CONFIRMED",
    },
  ],
  sourceDocumentContext: {
    cashCutFolio: "CC-100",
    cashCutId: "close-1",
    cashCutRouteHint: "/admin/cortes-caja?cashSession=session-1",
    cashSessionId: "session-1",
    concept: "Pago menor",
    countedCashAmount: null,
    differenceAmount: null,
    expectedCashAmount: null,
    note: null,
    originalTicketFolio: null,
    sourcePaymentMethod: "CASH",
    sourceReference: "PAGO-100",
    sourceRouteHint: "/admin/pagos-operativos?payment=payment-1",
    sourceStatus: "CONFIRMED",
    sourceTotalAmount: "125.00",
    sourceType: "OPERATIONAL_PAYMENT",
  },
};

function render(element: ReactElement) {
  return renderToString(withCapabilities(element, ["cash_finance.view"]));
}

describe("admin cash flow UI components", () => {
  it("renders the cash flow page shell without a create action", () => {
    const queryClient = new QueryClient();
    const html = render(
      <QueryClientProvider client={queryClient}>
        <AdminCashFlowPage />
      </QueryClientProvider>,
    );

    expect(html).toContain("Flujo de efectivo");
    expect(html).toContain("Actualizar");
    expect(html).not.toContain("Nuevo movimiento");
    expect(html).toContain(
      "Selecciona un movimiento para revisar origen, impacto financiero y documentos relacionados.",
    );
    expect(html).toContain("No hay datos suficientes para mostrar la tendencia del periodo.");
  });

  it("renders filters and quick filters", () => {
    const html = render(
      <AdminCashFlowFilters
        filters={filters}
        isBackendConnected={true}
        options={filterOptions}
        onChange={() => undefined}
      />,
    );

    expect(html).toContain("Todas las sucursales");
    expect(html).toContain("Todas las cajas");
    expect(html).toContain("Todas las direcciones");
    expect(html).toContain("Pendiente de conciliacion");
    expect(html).toContain("Entradas");
    expect(html).toContain("Tarjeta");
  });

  it("renders empty and populated cash flow table states", () => {
    const emptyHtml = render(
      <AdminCashFlowTable
        movements={[]}
        page={1}
        pageSize={25}
        total={0}
        onCopyReference={() => undefined}
        onPageChange={() => undefined}
        onSelectMovement={() => undefined}
      />,
    );
    expect(emptyHtml).toContain(
      "No hay movimientos de flujo de efectivo para los filtros seleccionados.",
    );

    const tableHtml = render(
      <AdminCashFlowTable
        movements={[movement]}
        page={1}
        pageSize={25}
        total={1}
        onCopyReference={() => undefined}
        onPageChange={() => undefined}
        onSelectMovement={() => undefined}
      />,
    );

    expect(tableHtml).toContain("PAGO-100");
    expect(tableHtml).toContain("Centro");
    expect(tableHtml).toContain("Pago operativo");
    expect(tableHtml).toContain("Salida");
    expect(tableHtml).toContain("Copiar");
  });

  it("renders movement detail sections, reconciliation and related documents", () => {
    const html = render(
      <AdminCashFlowDetailPanel
        detail={detail}
        selectedMovement={movement}
        onCopyReference={() => undefined}
      />,
    );

    expect(html).toContain("Resumen");
    expect(html).toContain("Documento origen");
    expect(html).toContain("Clasificacion financiera");
    expect(html).toContain("Conciliacion");
    expect(html).toContain("Documentos relacionados");
    expect(html).toContain("PAGO-100");
    expect(html).toContain("Este movimiento no requiere conciliacion.");
  });

  it("renders no selected movement empty state", () => {
    const html = render(
      <AdminCashFlowDetailPanel
        detail={null}
        selectedMovement={null}
        onCopyReference={() => undefined}
      />,
    );

    expect(html).toContain("Sin movimiento seleccionado");
    expect(html).toContain(
      "Selecciona un movimiento para revisar origen, impacto financiero y documentos relacionados.",
    );
  });
});
