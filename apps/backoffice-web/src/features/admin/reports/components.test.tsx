import { withCapabilities } from "../../../test-support/authorization";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactElement } from "react";
import { renderToString } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { AdminReportCatalog } from "./components/AdminReportCatalog";
import { AdminReportConfigurationPanel } from "./components/AdminReportConfigurationPanel";
import { AdminReportFilters } from "./components/AdminReportFilters";
import { AdminReportPreviewPanel } from "./components/AdminReportPreviewPanel";
import { AdminReportsPage } from "./pages/AdminReportsPage";
import type {
  AdminReportCatalogFilterOptions,
  AdminReportCatalogFilters,
  AdminReportDefinition,
  AdminReportPreview,
} from "./types";

const catalogFilters: AdminReportCatalogFilters = {
  category: "all",
  exportSupport: "all",
  search: "",
  sensitivity: "all",
  sourceModule: "all",
  status: "all",
};

const filterOptions: AdminReportCatalogFilterOptions = {
  categories: [{ id: "ventas_pedidos", label: "Ventas y pedidos" }],
  exportFormats: [{ id: "json", label: "JSON" }],
  sensitivities: [{ id: "sensitive", label: "Sensibles" }],
  sourceModules: [{ id: "sales", label: "Ventas" }],
  statuses: [{ id: "available", label: "Disponibles" }],
};

const report: AdminReportDefinition = {
  availableFilters: [
    {
      defaultValue: null,
      key: "date_from",
      label: "Desde",
      options: [],
      optionsSource: null,
      required: true,
      type: "date",
    },
    {
      defaultValue: null,
      key: "branch_id",
      label: "Sucursal",
      options: [{ id: "branch-1", label: "Centro - MAIN" }],
      optionsSource: "branches",
      required: false,
      type: "select",
    },
  ],
  backendEndpoint: "POST /v1/admin/reports/sales_summary_by_branch/preview",
  category: "ventas_pedidos",
  categoryLabel: "Ventas y pedidos",
  code: "sales_summary_by_branch",
  description: "Totales de tickets confirmados por sucursal.",
  isSensitive: false,
  name: "Resumen de ventas por sucursal",
  previewKind: "summary_table",
  requiredPermissions: ["sales_tickets.view"],
  sourceModules: ["sales", "tickets"],
  status: "available",
  supportedExports: ["json"],
  unavailableReason: null,
};

const unavailableReport: AdminReportDefinition = {
  ...report,
  code: "purchase_supplier_activity",
  isSensitive: true,
  name: "Actividad de proveedores",
  status: "requires_backend",
  supportedExports: [],
  unavailableReason: "Este reporte requiere soporte backend adicional antes de poder generarse.",
};

const preview: AdminReportPreview = {
  columns: [
    { key: "branch", kind: "text", label: "Sucursal" },
    { key: "total_sales", kind: "money", label: "Ventas" },
  ],
  filtersApplied: { date_from: "2026-05-01", date_to: "2026-05-22" },
  generatedAt: "2026-05-22T10:00:00Z",
  relatedLinks: [
    {
      canOpen: true,
      documentId: null,
      documentType: null,
      label: "Ventas / tickets",
      module: "sales",
      reference: null,
      routeHint: "/admin/ventas",
    },
  ],
  reportCode: "sales_summary_by_branch",
  reportName: "Resumen de ventas por sucursal",
  rows: [
    {
      cells: { branch: "Centro", total_sales: "1200.00" },
      id: "branch-1",
      sourceDocumentLinks: [],
    },
  ],
  summaryCards: [
    { helperText: "Total confirmado", label: "Ventas", tone: "success", value: "1200.00" },
  ],
  warnings: ["Vista previa limitada."],
};

function render(element: ReactElement) {
  return renderToString(
    withCapabilities(element, ["reports.view", "reports.export", "sales_tickets.view"]),
  );
}

describe("admin reports UI components", () => {
  it("renders the page shell without a create action", () => {
    const queryClient = new QueryClient();
    const html = render(
      <QueryClientProvider client={queryClient}>
        <AdminReportsPage />
      </QueryClientProvider>,
    );

    expect(html).toContain("Reportes");
    expect(html).toContain("Solo lectura");
    expect(html).not.toContain("Nuevo reporte");
  });

  it("renders compact catalog filter toolbar", () => {
    const html = render(
      <AdminReportFilters
        filters={catalogFilters}
        isBackendConnected={true}
        options={filterOptions}
        onChange={() => undefined}
      />,
    );

    expect(html).toContain("Nombre, modulo o fuente");
    expect(html).toContain("Filtros");
    expect(html).toContain("Definiciones desde backend");
    expect(html).not.toContain("Pendientes");
  });

  it("renders catalog populated and empty states", () => {
    const emptyHtml = render(
      <AdminReportCatalog
        reports={[]}
        total={0}
        onGenerate={() => undefined}
        onSelectReport={() => undefined}
      />,
    );
    expect(emptyHtml).toContain("No hay reportes que coincidan con los filtros seleccionados.");

    const html = render(
      <AdminReportCatalog
        reports={[report, unavailableReport]}
        total={2}
        onGenerate={() => undefined}
        onSelectReport={() => undefined}
      />,
    );
    expect(html).toContain("Resumen de ventas por sucursal");
    expect(html).toContain("Requiere backend");
    expect(html).toContain("Sensible");
  });

  it("renders configuration filters, sensitivity and export state", () => {
    const html = render(
      <AdminReportConfigurationPanel
        filters={{ branch_id: "branch-1", date_from: "2026-05-01" }}
        report={unavailableReport}
        onChangeFilter={() => undefined}
        onExport={() => undefined}
        onGenerate={() => undefined}
      />,
    );

    expect(html).toContain("Actividad de proveedores");
    expect(html).toContain("Reporte no disponible");
    expect(html).toContain("La exportacion no esta disponible para este reporte.");
    expect(html).toContain("No hay ejecuciones recientes para este reporte.");
  });

  it("renders preview rows, warnings, source links and no-result state", () => {
    const html = render(<AdminReportPreviewPanel preview={preview} report={report} />);

    expect(html).toContain("Vista previa");
    expect(html).toContain("Centro");
    expect(html).toContain("1200.00");
    expect(html).toContain("Vista previa limitada.");
    expect(html).toContain("Ventas / tickets");

    const emptyHtml = render(
      <AdminReportPreviewPanel preview={{ ...preview, rows: [] }} report={report} />,
    );
    expect(emptyHtml).toContain("El reporte no tiene resultados para los filtros seleccionados.");
  });
});
