import { withCapabilities } from "../../../test-support/authorization";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactElement } from "react";
import { renderToString } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { AdminCashCutsFilters } from "./components/AdminCashCutsFilters";
import { AdminCashCutsTable } from "./components/AdminCashCutsTable";
import { AdminCashCutDetailPanel } from "./components/AdminCashCutDetailPanel";
import { AdminCashCutsPage } from "./pages/AdminCashCutsPage";
import type {
  AdminCashCutDetail,
  AdminCashCutFilterOptions,
  AdminCashCutListFilters,
  AdminCashCutListItem,
} from "./types";

const filterOptions: AdminCashCutFilterOptions = {
  branches: [{ id: "branch-1", label: "Centro - MAIN" }],
  cashiers: [{ id: "user-1", label: "Admin" }],
  differenceStates: [
    { id: "WITH_DIFFERENCE", label: "Con diferencia" },
    { id: "WITHOUT_DIFFERENCE", label: "Sin diferencia" },
  ],
  paymentMethods: [
    { id: "CASH", label: "Efectivo" },
    { id: "CARD", label: "Tarjeta" },
  ],
  statuses: [
    { id: "OPEN", label: "Caja abierta" },
    { id: "CLOSED_WITH_DIFFERENCE", label: "Con diferencia" },
  ],
  workstations: [{ id: "station-1", label: "Mostrador 1 - POS-1" }],
};

const filters: AdminCashCutListFilters = {
  branchId: "all",
  cashierId: "all",
  dateFrom: null,
  dateTo: null,
  differenceState: "all",
  hasOperationalPayments: "all",
  hasRefunds: "all",
  page: 1,
  pageSize: 25,
  paymentMethod: "all",
  search: "",
  status: "all",
  workstationId: "all",
};

const cashCut: AdminCashCutListItem = {
  branchId: "branch-1",
  branchName: "Centro",
  cashSessionId: "session-1",
  cashierId: "user-1",
  cashierName: "Admin",
  closeId: "close-1",
  closedAt: "2026-05-21T18:00:00Z",
  countedCashAmount: "1125.00",
  differenceAmount: "5.00",
  differenceState: "OVER",
  expectedCashAmount: "1120.00",
  folio: "CC-100",
  hasOperationalPayments: true,
  hasRefunds: true,
  id: "session-1",
  openedAt: "2026-05-21T10:00:00Z",
  openingAmount: "500.00",
  paymentMethodsSummary: "CASH, CARD",
  status: "CLOSED_WITH_DIFFERENCE",
  totalSalesAmount: "720.00",
  warningCount: 1,
  warningState: "warning",
  workstationCode: "POS-1",
  workstationId: "station-1",
  workstationName: "Mostrador 1",
};

const cashCutDetail: AdminCashCutDetail = {
  auditTimeline: [
    {
      actorName: "Admin",
      eventCode: "cash_session_closed",
      label: "Corte confirmado",
      occurredAt: "2026-05-21T18:00:00Z",
      summary: "Cierre POS persistido",
    },
  ],
  availableActions: {
    canCopyFolio: true,
    canExportReport: false,
    canOpenOperationalPayments: true,
    canOpenReturns: true,
    canOpenTickets: true,
    canPrintReport: false,
    canRemoteClose: false,
    remoteCloseNote: null,
  },
  backendContract: {
    detailEndpoint: "GET /v1/admin/cash-cuts/{cash_session_id}",
    exportEndpoint: null,
    listEndpoint: "GET /v1/admin/cash-cuts",
    printEndpoint: null,
  },
  correctionsAdjustments: [
    {
      amount: "5.00",
      documentType: "CASH_CLOSE_DISCREPANCY",
      folio: "close-1",
      id: "close-1",
      notes: "Diferencia declarada en cierre.",
      occurredAt: "2026-05-21T18:00:00Z",
      operatorName: "Admin",
      routeHint: null,
    },
  ],
  denominationCount: {
    isSupported: false,
    lines: [],
    note: "El POS no capturo conteo por denominacion.",
    totalCounted: null,
  },
  expectedVsCounted: {
    cashAdjustmentsAmount: "0.00",
    cashOperationalDiscountsAmount: "0.00",
    cashOperationalPaymentsAmount: "50.00",
    cashRefundsAmount: "25.00",
    cashSalesAmount: "695.00",
    countedCashAmount: "1125.00",
    differenceAmount: "5.00",
    differenceState: "OVER",
    expectedCashAmount: "1120.00",
    isCountedCashAvailable: true,
    note: null,
    openingAmount: "500.00",
  },
  includedTickets: [
    {
      cashierName: "Admin",
      currencyCode: "MXN",
      folio: "TCK-100",
      occurredAt: "2026-05-21T12:00:00Z",
      paymentMethodSummary: "CASH",
      routeHint: "/admin/ventas-tickets?ticket=TCK-100",
      status: "PAID",
      ticketId: "ticket-1",
      totalAmount: "720.00",
    },
  ],
  operationalPayments: [
    {
      amount: "50.00",
      cashAmount: "50.00",
      categoryCode: "SUPPLIES",
      categoryName: "Insumos",
      folio: "PAGO-100",
      id: "payment-1",
      notes: "Compra menor",
      occurredAt: "2026-05-21T14:00:00Z",
      operatorName: "Admin",
      paymentMethodCode: "CASH",
      routeHint: "/admin/pagos-operativos?payment=payment-1",
    },
  ],
  overview: {
    branchCode: "MAIN",
    branchId: "branch-1",
    branchName: "Centro",
    cashSessionId: "session-1",
    cashierId: "user-1",
    cashierName: "Admin",
    closeId: "close-1",
    closedAt: "2026-05-21T18:00:00Z",
    closingNotes: "Cierre con sobrante menor.",
    folio: "CC-100",
    id: "session-1",
    openedAt: "2026-05-21T10:00:00Z",
    openingAmount: "500.00",
    status: "CLOSED_WITH_DIFFERENCE",
    totalDurationMinutes: 480,
    warningState: "warning",
    workstationCode: "POS-1",
    workstationId: "station-1",
    workstationName: "Mostrador 1",
  },
  paymentBreakdown: [
    {
      countedAmount: "1125.00",
      currencyCode: "MXN",
      expectedAmount: "1120.00",
      isCountedSupported: true,
      netAmount: "695.00",
      operationalDiscountAmount: "0.00",
      operationalPaymentAmount: "50.00",
      paymentMethodCode: "CASH",
      refundAmount: "25.00",
      salesAmount: "720.00",
      varianceAmount: "5.00",
    },
    {
      countedAmount: null,
      currencyCode: "MXN",
      expectedAmount: null,
      isCountedSupported: false,
      netAmount: "100.00",
      operationalDiscountAmount: "0.00",
      operationalPaymentAmount: "0.00",
      paymentMethodCode: "CARD",
      refundAmount: "0.00",
      salesAmount: "100.00",
      varianceAmount: null,
    },
  ],
  reconciliationStatus: {
    note: "Conciliacion no disponible en este modulo.",
    reconciledAt: null,
    reconciledByName: null,
    relatedDocumentId: null,
    routeHint: null,
    status: "UNRECONCILED",
  },
  relatedDocuments: [
    {
      amount: "720.00",
      documentType: "TICKET",
      folio: "TCK-100",
      id: "ticket-1",
      occurredAt: "2026-05-21T12:00:00Z",
      routeHint: "/admin/ventas-tickets?ticket=TCK-100",
      status: "PAID",
    },
  ],
  returnsRefunds: [
    {
      amount: "25.00",
      folio: "DEV-100",
      id: "return-1",
      occurredAt: "2026-05-21T13:00:00Z",
      operatorName: "Admin",
      originalTicketFolio: "TCK-100",
      paymentMethodCode: "CASH",
      reasonName: "Cambio",
      routeHint: "/admin/devoluciones-correcciones?return=return-1",
      status: "COMMITTED",
    },
  ],
};

function render(element: ReactElement) {
  return renderToString(withCapabilities(element, ["cash_finance.view"]));
}

describe("admin cash cuts UI components", () => {
  it("renders the cash cuts page shell without a create action", () => {
    const queryClient = new QueryClient();
    const html = render(
      <QueryClientProvider client={queryClient}>
        <AdminCashCutsPage />
      </QueryClientProvider>,
    );

    expect(html).toContain("Cortes de caja");
    expect(html).toContain("Actualizar");
    expect(html).not.toContain("Nuevo corte");
    expect(html).toContain(
      "Selecciona un corte para revisar ventas, pagos, diferencias y documentos relacionados.",
    );
  });

  it("renders compact filter toolbar", () => {
    const html = render(
      <AdminCashCutsFilters
        filters={filters}
        isBackendConnected={true}
        options={filterOptions}
        onChange={() => undefined}
      />,
    );

    expect(html).toContain("Buscar folio, cajero, sucursal o estacion");
    expect(html).toContain("Filtros");
    expect(html).toContain("Datos conectados");
    expect(html).not.toContain("Todas las sucursales");
  });

  it("renders empty and populated cash cut table states", () => {
    const emptyHtml = render(
      <AdminCashCutsTable
        cashCuts={[]}
        page={1}
        pageSize={25}
        total={0}
        onCopyFolio={() => undefined}
        onPageChange={() => undefined}
        onSelectCashCut={() => undefined}
      />,
    );
    expect(emptyHtml).toContain("No hay cortes de caja para los filtros seleccionados.");

    const tableHtml = render(
      <AdminCashCutsTable
        cashCuts={[cashCut]}
        page={1}
        pageSize={25}
        total={1}
        onCopyFolio={() => undefined}
        onPageChange={() => undefined}
        onSelectCashCut={() => undefined}
      />,
    );

    expect(tableHtml).toContain("CC-100");
    expect(tableHtml).toContain("Centro");
    expect(tableHtml).toContain("Ventas");
    expect(tableHtml).toContain("CASH, CARD");
    expect(tableHtml).toContain("Con diferencia");
    expect(tableHtml).toContain("Copiar");
  });

  it("renders cash cut detail sections, related documents and report action states", () => {
    const html = render(
      <AdminCashCutDetailPanel
        detail={cashCutDetail}
        selectedCashCut={cashCut}
        onCopyFolio={() => undefined}
      />,
    );

    expect(html).toContain("Esperado vs contado");
    expect(html).toContain("Metodos de pago");
    expect(html).toContain("Tickets incluidos");
    expect(html).toContain("Devoluciones");
    expect(html).toContain("Pagos operativos");
    expect(html).toContain("Correcciones / ajustes");
    expect(html).toContain("Conteo por denominacion");
    expect(html).toContain("Conciliacion y auditoria");
    expect(html).toContain("TCK-100");
    expect(html).toContain("DEV-100");
    expect(html).toContain("PAGO-100");
    expect(html).toContain("Exportar");
    expect(html).toContain("Imprimir");
  });

  it("renders the no selected cut empty state", () => {
    const html = render(
      <AdminCashCutDetailPanel
        detail={null}
        selectedCashCut={null}
        onCopyFolio={() => undefined}
      />,
    );

    expect(html).toContain("Sin corte seleccionado");
    expect(html).toContain(
      "Selecciona un corte para revisar ventas, pagos, diferencias y documentos relacionados.",
    );
  });
});
