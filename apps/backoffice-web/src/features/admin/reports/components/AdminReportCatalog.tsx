import { AdminEmptyState } from "../../components/AdminEmptyState";
import type { AdminReportDefinition } from "../types";

interface AdminReportCatalogProps {
  errorMessage?: string | null;
  isLoading?: boolean;
  onGenerate: (report: AdminReportDefinition) => void;
  onSelectReport: (report: AdminReportDefinition) => void;
  reports: AdminReportDefinition[];
  selectedReportCode?: string | null;
  total: number;
}

function badgeClass(value: string): string {
  if (value === "available" || value === "standard") {
    return "border-emerald-200 bg-[var(--ui-color-success-soft)] text-[var(--ui-color-success)]";
  }
  if (value === "requires_backend" || value === "sensitive") {
    return "border-amber-200 bg-[var(--ui-color-warning-soft)] text-[var(--ui-color-warning)]";
  }
  return "border-slate-200 bg-slate-50 text-slate-600";
}

function statusLabel(value: string): string {
  return {
    available: "Disponible",
    coming_soon: "Proximamente",
    requires_backend: "Requiere backend",
  }[value] ?? value;
}

export function AdminReportCatalog({
  errorMessage,
  isLoading = false,
  onGenerate,
  onSelectReport,
  reports,
  selectedReportCode,
  total,
}: AdminReportCatalogProps) {
  return (
    <section className="flex min-h-0 min-w-0 flex-col overflow-hidden rounded-[20px] border border-[var(--ui-color-border)] bg-white">
      <div className="flex min-w-0 shrink-0 items-center justify-between gap-3 border-b border-[var(--ui-color-border)] px-3 py-2.5">
        <div className="min-w-0">
          <h3 className="truncate text-base font-semibold text-slate-950">Reportes disponibles</h3>
          <p className="truncate text-xs text-slate-500">
            Definiciones canonicas, fuentes, filtros, sensibilidad y exportacion.
          </p>
        </div>
        <span className="shrink-0 rounded-full border border-[var(--ui-color-border)] bg-white px-3 py-1 text-xs font-semibold text-slate-600">
          {total} reportes
        </span>
      </div>

      <div className="min-h-0 min-w-0 flex-1 overflow-auto p-2.5">
        {isLoading ? (
          <AdminEmptyState
            description="Consultando definiciones de reportes del backend."
            title="Cargando reportes"
          />
        ) : errorMessage ? (
          <AdminEmptyState description={errorMessage} title="No se pudieron cargar reportes" />
        ) : reports.length > 0 ? (
          <div className="grid gap-2">
            {reports.map((report) => {
              const isSelected = report.code === selectedReportCode;
              const exportLabel = report.supportedExports.length
                ? report.supportedExports.join(", ").toUpperCase()
                : "Sin exportacion";
              return (
                <article
                  className={[
                    "grid gap-2 rounded-[18px] border p-3 transition",
                    isSelected
                      ? "border-[var(--ui-color-info)] bg-[var(--ui-color-info-soft)]"
                      : "border-[var(--ui-color-border)] bg-white hover:bg-slate-50",
                  ].join(" ")}
                  key={report.code}
                >
                  <div className="flex min-w-0 flex-wrap items-start justify-between gap-2">
                    <button
                      className="min-w-0 text-left focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
                      type="button"
                      onClick={() => onSelectReport(report)}
                    >
                      <span className="block truncate text-sm font-semibold text-slate-950">
                        {report.name}
                      </span>
                      <span className="line-clamp-2 text-xs text-slate-500">
                        {report.description}
                      </span>
                    </button>
                    <div className="flex shrink-0 flex-wrap justify-end gap-1.5">
                      <span
                        className={`rounded-full border px-2 py-1 text-xs font-semibold ${badgeClass(
                          report.status,
                        )}`}
                      >
                        {statusLabel(report.status)}
                      </span>
                      {report.isSensitive ? (
                        <span className={`rounded-full border px-2 py-1 text-xs font-semibold ${badgeClass("sensitive")}`}>
                          Sensible
                        </span>
                      ) : null}
                    </div>
                  </div>

                  <div className="grid gap-2 text-xs text-slate-600 md:grid-cols-2">
                    <p className="truncate">
                      <span className="font-semibold text-slate-700">Categoria:</span>{" "}
                      {report.categoryLabel}
                    </p>
                    <p className="truncate">
                      <span className="font-semibold text-slate-700">Fuentes:</span>{" "}
                      {report.sourceModules.join(", ")}
                    </p>
                    <p className="truncate">
                      <span className="font-semibold text-slate-700">Filtros:</span>{" "}
                      {report.availableFilters.length
                        ? report.availableFilters.map((filter) => filter.label).join(", ")
                        : "Sin filtros"}
                    </p>
                    <p className="truncate">
                      <span className="font-semibold text-slate-700">Exporta:</span>{" "}
                      {exportLabel}
                    </p>
                  </div>

                  {report.unavailableReason ? (
                    <p className="rounded-2xl border border-amber-200 bg-[var(--ui-color-warning-soft)] px-3 py-2 text-xs font-semibold text-[var(--ui-color-warning)]">
                      {report.unavailableReason}
                    </p>
                  ) : null}

                  <div className="flex min-w-0 flex-wrap justify-end gap-2">
                    <button
                      className="rounded-full border border-[var(--ui-color-border)] bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 transition hover:border-[var(--ui-color-info)]"
                      type="button"
                      onClick={() => onSelectReport(report)}
                    >
                      Configurar
                    </button>
                    <button
                      className="rounded-full border border-[var(--ui-color-border)] bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 transition hover:border-[var(--ui-color-info)] disabled:cursor-not-allowed disabled:opacity-40"
                      disabled={report.status !== "available"}
                      type="button"
                      onClick={() => onGenerate(report)}
                    >
                      Generar
                    </button>
                  </div>
                </article>
              );
            })}
          </div>
        ) : (
          <AdminEmptyState
            description="No hay reportes que coincidan con los filtros seleccionados."
            title="Sin reportes"
          />
        )}
      </div>
    </section>
  );
}
