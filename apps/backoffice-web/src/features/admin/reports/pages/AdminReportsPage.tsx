import { useMutation, useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";

import { toBackofficeErrorMessage } from "../../../../lib/api";
import { useBackofficeAuthStore } from "../../../auth/backoffice-auth-store";
import { AdminPageHeader } from "../../components/AdminPageHeader";
import {
  adminReportBackendContract,
  exportAdminReport,
  fetchAdminReports,
  previewAdminReport,
} from "../api";
import { AdminReportCatalog } from "../components/AdminReportCatalog";
import { AdminReportConfigurationPanel } from "../components/AdminReportConfigurationPanel";
import { AdminReportFilters } from "../components/AdminReportFilters";
import { AdminReportPreviewPanel } from "../components/AdminReportPreviewPanel";
import type {
  AdminReportCatalogFilterOptions,
  AdminReportCatalogFilters,
  AdminReportDefinitionsResponse,
  AdminReportDefinition,
  AdminReportPreview,
} from "../types";

const initialCatalogFilters: AdminReportCatalogFilters = {
  category: "all",
  exportSupport: "all",
  search: "",
  sensitivity: "all",
  sourceModule: "all",
  status: "all",
};

const emptyFilterOptions: AdminReportCatalogFilterOptions = {
  categories: [],
  exportFormats: [],
  sensitivities: [],
  sourceModules: [],
  statuses: [],
};

const emptyReportList: AdminReportDefinitionsResponse = {
  backendContract: adminReportBackendContract,
  definitions: [],
  filterOptions: emptyFilterOptions,
  isBackendConnected: false,
  metrics: {
    availableReports: "0",
    categoryCount: "0",
    exportableReports: "0",
    pendingBackendReports: "0",
    recentlyGeneratedReports: null,
    sensitiveReports: "0",
  },
  total: 0,
};

function todayIso(): string {
  return new Date().toISOString().slice(0, 10);
}

function monthStartIso(): string {
  const now = new Date();
  return new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), 1))
    .toISOString()
    .slice(0, 10);
}

function defaultReportFilters(report: AdminReportDefinition): Record<string, string> {
  const values: Record<string, string> = {};
  for (const filter of report.availableFilters) {
    if (filter.defaultValue) {
      values[filter.key] = filter.defaultValue;
    } else if (filter.key === "date_from") {
      values[filter.key] = monthStartIso();
    } else if (filter.key === "date_to") {
      values[filter.key] = todayIso();
    } else if (filter.type === "select") {
      values[filter.key] = "all";
    } else {
      values[filter.key] = "";
    }
  }
  return values;
}

function missingRequiredFilters(
  report: AdminReportDefinition,
  filters: Record<string, string>,
): string[] {
  return report.availableFilters
    .filter((filter) => filter.required)
    .filter((filter) => !filters[filter.key] || filters[filter.key] === "all")
    .map((filter) => filter.label);
}

function ReportMetricStrip({
  isLoading,
  metrics,
}: {
  isLoading: boolean;
  metrics: AdminReportDefinitionsResponse["metrics"];
}) {
  const loadingValue = isLoading ? "Cargando" : null;
  const items = [
    { label: "Reportes disponibles", value: loadingValue ?? metrics.availableReports },
    { label: "Categorias", value: loadingValue ?? metrics.categoryCount },
    { label: "Exportables", value: loadingValue ?? metrics.exportableReports },
    { label: "Sensibles", value: loadingValue ?? metrics.sensitiveReports },
    { label: "Pendientes de backend", value: loadingValue ?? metrics.pendingBackendReports },
    {
      label: "Generados recientemente",
      value: loadingValue ?? metrics.recentlyGeneratedReports ?? "No disponible",
    },
  ];

  return (
    <section className="flex min-w-0 flex-wrap items-center gap-2 rounded-[18px] border border-[var(--ui-color-border)] bg-white px-3 py-2 text-xs text-slate-600">
      <span className="shrink-0 font-semibold uppercase tracking-[0.12em] text-slate-500">
        Resumen
      </span>
      {items.map((item) => (
        <span
          className="inline-flex min-w-0 max-w-full items-center gap-1.5 rounded-full border border-[var(--ui-color-border)] bg-slate-50 px-2.5 py-1"
          key={item.label}
          title={`${item.label}: ${item.value}`}
        >
          <span className="truncate text-slate-500">{item.label}</span>
          <span className="truncate font-semibold text-slate-950">{item.value}</span>
        </span>
      ))}
    </section>
  );
}

function downloadJson(filename: string, value: unknown) {
  const blob = new Blob([JSON.stringify(value, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}

export function AdminReportsPage() {
  const accessToken = useBackofficeAuthStore((state) => state.accessToken);
  const [catalogFilters, setCatalogFilters] =
    useState<AdminReportCatalogFilters>(initialCatalogFilters);
  const [selectedReportCode, setSelectedReportCode] = useState<string | null>(null);
  const [reportFilters, setReportFilters] = useState<Record<string, string>>({});
  const [preview, setPreview] = useState<AdminReportPreview | null>(null);
  const [feedback, setFeedback] = useState<{ tone: "success" | "error"; message: string } | null>(
    null,
  );

  const reportsQuery = useQuery({
    enabled: Boolean(accessToken),
    queryFn: () => fetchAdminReports(accessToken ?? "", catalogFilters),
    queryKey: ["admin", "reports", "catalog", catalogFilters],
    retry: false,
  });

  const reportList = reportsQuery.data ?? emptyReportList;
  const selectedReport = useMemo(
    () => reportList.definitions.find((definition) => definition.code === selectedReportCode) ?? null,
    [reportList.definitions, selectedReportCode],
  );

  const previewMutation = useMutation({
    mutationFn: ({ filters, reportCode }: { filters: Record<string, string>; reportCode: string }) =>
      previewAdminReport(accessToken ?? "", reportCode, filters),
    onError: (error) => {
      setFeedback({
        tone: "error",
        message: toBackofficeErrorMessage(error, "No se pudo generar el reporte."),
      });
    },
    onSuccess: (payload) => {
      setPreview(payload);
      setFeedback({
        tone: "success",
        message: `Vista previa generada con ${payload.rows.length} filas.`,
      });
    },
  });

  const exportMutation = useMutation({
    mutationFn: ({ filters, reportCode }: { filters: Record<string, string>; reportCode: string }) =>
      exportAdminReport(accessToken ?? "", reportCode, filters, "json"),
    onError: (error) => {
      setFeedback({
        tone: "error",
        message: toBackofficeErrorMessage(error, "No se pudo exportar el reporte."),
      });
    },
    onSuccess: (payload) => {
      downloadJson(`${payload.reportCode}-${new Date().toISOString().slice(0, 10)}.json`, payload);
      setFeedback({
        tone: "success",
        message: `${payload.totalRows} filas preparadas para exportar.`,
      });
    },
  });

  const listErrorMessage = reportsQuery.isError
    ? toBackofficeErrorMessage(reportsQuery.error, "No se pudieron cargar los reportes.")
    : null;
  const previewErrorMessage = previewMutation.isError
    ? toBackofficeErrorMessage(previewMutation.error, "No se pudo generar el reporte.")
    : null;
  const pageStatusLabel = reportsQuery.isLoading
    ? "Validando API"
    : reportList.isBackendConnected
      ? "Datos conectados"
      : "Integracion parcial";

  function patchCatalogFilters(patch: Partial<AdminReportCatalogFilters>) {
    setCatalogFilters((current) => ({ ...current, ...patch }));
  }

  function selectReport(report: AdminReportDefinition) {
    setSelectedReportCode(report.code);
    setReportFilters(defaultReportFilters(report));
    setPreview(null);
    setFeedback(null);
  }

  function generateReport(report = selectedReport, filters = reportFilters) {
    if (!report) {
      setFeedback({ tone: "error", message: "Selecciona un reporte primero." });
      return;
    }
    const missing = missingRequiredFilters(report, filters);
    if (missing.length > 0) {
      setFeedback({
        tone: "error",
        message: `Completa filtros requeridos: ${missing.join(", ")}.`,
      });
      return;
    }
    previewMutation.mutate({ filters, reportCode: report.code });
  }

  function quickGenerate(report: AdminReportDefinition) {
    const defaults = defaultReportFilters(report);
    selectReport(report);
    generateReport(report, defaults);
  }

  function exportSelectedReport() {
    if (!selectedReport) {
      return;
    }
    const missing = missingRequiredFilters(selectedReport, reportFilters);
    if (missing.length > 0) {
      setFeedback({
        tone: "error",
        message: `Completa filtros requeridos: ${missing.join(", ")}.`,
      });
      return;
    }
    exportMutation.mutate({ filters: reportFilters, reportCode: selectedReport.code });
  }

  return (
    <section className="flex min-h-0 min-w-0 flex-col overflow-hidden rounded-[28px] border border-[var(--ui-color-border)] bg-white shadow-[var(--ui-shadow-subtle)] lg:h-full">
      <AdminPageHeader
        description="Consulta y exporta reportes operativos, financieros, de inventario, compras, calidad y control."
        meta={[pageStatusLabel, "Solo lectura"]}
        title="Reportes"
      />

      <div className="flex min-h-0 min-w-0 flex-1 flex-col gap-2.5 overflow-hidden p-3">
        <AdminReportFilters
          filters={catalogFilters}
          isBackendConnected={reportList.isBackendConnected}
          options={reportList.filterOptions}
          onChange={patchCatalogFilters}
        />

        <ReportMetricStrip isLoading={reportsQuery.isLoading} metrics={reportList.metrics} />

        <div className="flex min-w-0 flex-wrap gap-2">
          <button
            className="rounded-2xl border border-[var(--ui-color-border)] bg-white px-3 py-2 text-sm font-semibold text-slate-700 transition hover:border-[var(--ui-color-info)]"
            type="button"
            onClick={() => reportsQuery.refetch()}
          >
            Actualizar
          </button>
        </div>

        {feedback ? (
          <p
            className={`rounded-[18px] border px-4 py-3 text-sm font-semibold ${
              feedback.tone === "success"
                ? "border-emerald-200 bg-[var(--ui-color-success-soft)] text-[var(--ui-color-success)]"
                : "border-rose-200 bg-[var(--ui-color-danger-soft)] text-[var(--ui-color-danger)]"
            }`}
          >
            {feedback.message}
          </p>
        ) : null}

        <div className="grid min-h-0 min-w-0 flex-1 gap-2.5 xl:grid-cols-[minmax(22rem,0.42fr)_minmax(0,1fr)]">
          <AdminReportCatalog
            errorMessage={listErrorMessage}
            isLoading={reportsQuery.isLoading}
            reports={reportList.definitions}
            selectedReportCode={selectedReportCode}
            total={reportList.total}
            onGenerate={quickGenerate}
            onSelectReport={selectReport}
          />

          <div className="grid min-h-0 min-w-0 gap-2.5 xl:grid-rows-[auto_minmax(0,1fr)]">
            <AdminReportConfigurationPanel
              exportPending={exportMutation.isPending}
              filters={reportFilters}
              generationPending={previewMutation.isPending}
              report={selectedReport}
              onChangeFilter={(key, value) =>
                setReportFilters((current) => ({ ...current, [key]: value }))
              }
              onExport={exportSelectedReport}
              onGenerate={() => generateReport()}
            />
            <AdminReportPreviewPanel
              errorMessage={previewErrorMessage}
              isLoading={previewMutation.isPending}
              preview={preview}
              report={selectedReport}
            />
          </div>
        </div>
      </div>
    </section>
  );
}
