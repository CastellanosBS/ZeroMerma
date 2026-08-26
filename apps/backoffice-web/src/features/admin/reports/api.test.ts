import { afterEach, describe, expect, it, vi } from "vitest";

import { exportAdminReport, fetchAdminReports, previewAdminReport } from "./api";
import type { AdminReportCatalogFilters } from "./types";

const filters: AdminReportCatalogFilters = {
  category: "all",
  exportSupport: "all",
  search: "",
  sensitivity: "all",
  sourceModule: "all",
  status: "all",
};

const apiDefinition = {
  available_filters: [
    {
      default_value: null,
      key: "date_from",
      label: "Desde",
      options: [],
      options_source: null,
      required: true,
      type: "date",
    },
  ],
  backend_endpoint: "POST /v1/admin/reports/sales_summary_by_branch/preview",
  category: "ventas_pedidos",
  category_label: "Ventas y pedidos",
  code: "sales_summary_by_branch",
  description: "Ventas confirmadas por sucursal.",
  is_sensitive: false,
  name: "Resumen de ventas por sucursal",
  preview_kind: "summary_table",
  required_permissions: ["sales_tickets.view"],
  source_modules: ["sales", "tickets"],
  status: "available",
  supported_exports: ["json"],
  unavailable_reason: null,
};

const apiPreview = {
  columns: [
    { key: "branch", kind: "text", label: "Sucursal" },
    { key: "total_sales", kind: "money", label: "Ventas" },
  ],
  filters_applied: { date_from: "2026-05-01", date_to: "2026-05-22" },
  generated_at: "2026-05-22T10:00:00Z",
  related_links: [
    {
      can_open: true,
      document_id: null,
      document_type: null,
      label: "Ventas / tickets",
      module: "sales",
      reference: null,
      route_hint: "/admin/ventas",
    },
  ],
  report_code: "sales_summary_by_branch",
  report_name: "Resumen de ventas por sucursal",
  rows: [
    {
      cells: { branch: "Centro", total_sales: "1200.00" },
      id: "branch-1",
      source_document_links: [],
    },
  ],
  summary_cards: [
    { helper_text: "Total confirmado", label: "Ventas", tone: "success", value: "1200.00" },
  ],
  warnings: [],
};

function mockJsonResponse(payload: unknown, status = 200) {
  return Promise.resolve(
    new Response(JSON.stringify(payload), {
      headers: { "Content-Type": "application/json" },
      status,
    }),
  );
}

afterEach(() => {
  vi.restoreAllMocks();
});

describe("admin reports API boundary", () => {
  it("fetches and maps report definitions from backend", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockImplementation(() =>
      mockJsonResponse({
        backend_contract: {
          async_jobs_supported: false,
          definitions_endpoint: "GET /v1/admin/reports",
          export_endpoint: "POST /v1/admin/reports/{report_code}/export",
          generation_history_supported: false,
          preview_endpoint: "POST /v1/admin/reports/{report_code}/preview",
          saved_configurations_supported: false,
          supported_export_formats: ["json"],
        },
        definitions: [apiDefinition],
        filter_options: {
          categories: [{ code: "ventas_pedidos", label: "Ventas y pedidos" }],
          export_formats: [{ code: "json", label: "JSON" }],
          sensitivities: [{ code: "standard", label: "Operativos" }],
          source_modules: [{ code: "sales", label: "Ventas" }],
          statuses: [{ code: "available", label: "Disponibles" }],
        },
        is_backend_connected: true,
        metrics: {
          available_reports: 1,
          category_count: 1,
          exportable_reports: 1,
          pending_backend_reports: 0,
          recently_generated_reports: null,
          sensitive_reports: 0,
        },
        total: 1,
      }),
    );

    const response = await fetchAdminReports("token-1", {
      ...filters,
      category: "ventas_pedidos",
      status: "available",
    });

    expect(fetchSpy).toHaveBeenCalledWith(
      expect.stringContaining("/v1/admin/reports?"),
      expect.objectContaining({ method: "GET" }),
    );
    expect(response.definitions[0]?.code).toBe("sales_summary_by_branch");
    expect(response.metrics.availableReports).toBe("1");
  });

  it("generates preview through backend POST", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockImplementation(() => mockJsonResponse(apiPreview));

    const preview = await previewAdminReport("token-1", "sales_summary_by_branch", {
      date_from: "2026-05-01",
      date_to: "2026-05-22",
    });

    expect(fetchSpy).toHaveBeenCalledWith(
      expect.stringContaining("/v1/admin/reports/sales_summary_by_branch/preview"),
      expect.objectContaining({ method: "POST" }),
    );
    expect(preview.rows[0]?.cells.branch).toBe("Centro");
    expect(preview.summaryCards[0]?.tone).toBe("success");
  });

  it("exports supported report as JSON payload", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockImplementation(() =>
      mockJsonResponse({
        filters_applied: { app_access: "BACKOFFICE" },
        format: "json",
        generated_at: "2026-05-22T10:00:00Z",
        report_code: "user_access_summary",
        report_name: "Resumen de acceso de usuarios",
        rows: [{ cells: { email: "admin@zeromerma.local" }, id: "user-1", source_document_links: [] }],
        total_rows: 1,
        warnings: [],
      }),
    );

    const payload = await exportAdminReport("token-1", "user_access_summary", {
      app_access: "BACKOFFICE",
    });

    expect(fetchSpy).toHaveBeenCalledWith(
      expect.stringContaining("/v1/admin/reports/user_access_summary/export"),
      expect.objectContaining({ method: "POST" }),
    );
    expect(payload.totalRows).toBe(1);
    expect(payload.rows[0]?.cells.email).toBe("admin@zeromerma.local");
  });
});
