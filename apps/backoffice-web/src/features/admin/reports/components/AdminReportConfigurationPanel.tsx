import { hasEffectiveCapability } from "../../../auth/authorization";
import { useBackofficeAuthorization } from "../../../auth/authorization-context";
import { AdminEmptyState } from "../../components/AdminEmptyState";
import type { AdminReportDefinition } from "../types";
import { AdminActionButton } from "../../components/AdminActionButton";

interface AdminReportConfigurationPanelProps {
  exportPending?: boolean;
  filters: Record<string, string>;
  generationPending?: boolean;
  onChangeFilter: (key: string, value: string) => void;
  onExport: () => void;
  onGenerate: () => void;
  report: AdminReportDefinition | null;
}

function badgeClass(value: string): string {
  if (value === "available") {
    return "border-emerald-200 bg-[var(--ui-color-success-soft)] text-[var(--ui-color-success)]";
  }
  if (value === "requires_backend" || value === "sensitive") {
    return "border-amber-200 bg-[var(--ui-color-warning-soft)] text-[var(--ui-color-warning)]";
  }
  return "border-slate-200 bg-slate-50 text-slate-600";
}

function formatStatus(value: string): string {
  return (
    {
      available: "Disponible",
      coming_soon: "Proximamente",
      requires_backend: "Requiere backend",
    }[value] ?? value
  );
}

export function AdminReportConfigurationPanel({
  exportPending = false,
  filters,
  generationPending = false,
  onChangeFilter,
  onExport,
  onGenerate,
  report,
}: AdminReportConfigurationPanelProps) {
  const actor = useBackofficeAuthorization();
  if (!report) {
    return (
      <section className="flex min-h-0 min-w-0 flex-col overflow-hidden rounded-[20px] border border-[var(--ui-color-border)] bg-white p-3">
        <AdminEmptyState
          description="Selecciona un reporte para configurar filtros, generar vista previa o exportar resultados."
          title="Sin reporte seleccionado"
        />
      </section>
    );
  }

  const branchIds = filters.branch_id && filters.branch_id !== "all" ? [filters.branch_id] : [];
  const hasSourceCapabilities = report.requiredPermissions.every((code) => {
    const grant = actor?.effective_grants?.find((item) => item.capability === code);
    return Boolean(grant && hasEffectiveCapability(actor, grant.capability, branchIds));
  });
  const canGenerate = report.status === "available" && hasSourceCapabilities;
  const canExport = canGenerate && report.supportedExports.includes("json");

  return (
    <section className="grid min-w-0 gap-3 rounded-[20px] border border-[var(--ui-color-border)] bg-white p-3">
      <div className="flex min-w-0 flex-wrap items-start justify-between gap-2">
        <div className="min-w-0">
          <h3 className="truncate text-base font-semibold text-slate-950">{report.name}</h3>
          <p className="text-xs text-slate-500">{report.description}</p>
        </div>
        <div className="flex shrink-0 flex-wrap gap-1.5">
          <span
            className={`rounded-full border px-2 py-1 text-xs font-semibold ${badgeClass(report.status)}`}
          >
            {formatStatus(report.status)}
          </span>
          {report.isSensitive ? (
            <span
              className={`rounded-full border px-2 py-1 text-xs font-semibold ${badgeClass("sensitive")}`}
            >
              Sensible
            </span>
          ) : null}
        </div>
      </div>

      <div className="grid gap-2 rounded-[18px] border border-[var(--ui-color-border)] bg-slate-50/80 p-3 text-xs text-slate-600">
        <p>
          <span className="font-semibold text-slate-700">Categoria:</span> {report.categoryLabel}
        </p>
        <p>
          <span className="font-semibold text-slate-700">Modulos fuente:</span>{" "}
          {report.sourceModules.join(", ")}
        </p>
        <p>
          <span className="font-semibold text-slate-700">Permisos sugeridos:</span>{" "}
          {report.requiredPermissions.length
            ? report.requiredPermissions.join(", ")
            : "Sin permiso especifico"}
        </p>
        <p>
          <span className="font-semibold text-slate-700">Historial:</span> No hay ejecuciones
          recientes para este reporte.
        </p>
      </div>

      {report.status !== "available" ? (
        <AdminEmptyState
          description={
            report.unavailableReason ??
            "Este reporte requiere soporte backend adicional antes de poder generarse."
          }
          title="Reporte no disponible"
        />
      ) : null}

      <div className="grid gap-2 md:grid-cols-2">
        {report.availableFilters.map((filter) => (
          <label className="min-w-0" key={filter.key}>
            <span className="mb-1 block truncate text-xs font-semibold uppercase tracking-[0.08em] text-slate-500">
              {filter.label}
              {filter.required ? " *" : ""}
            </span>
            {filter.type === "select" ? (
              <select
                className="h-10 w-full rounded-2xl border border-[var(--ui-color-border)] bg-white px-3 text-sm font-semibold text-slate-700 shadow-sm focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
                value={filters[filter.key] ?? "all"}
                onChange={(event) => onChangeFilter(filter.key, event.target.value)}
              >
                <option value="all">Todos</option>
                {filter.options.map((option) => (
                  <option key={option.id} value={option.id}>
                    {option.label}
                  </option>
                ))}
              </select>
            ) : (
              <input
                className="h-10 w-full rounded-2xl border border-[var(--ui-color-border)] bg-white px-3 text-sm font-semibold text-slate-700 shadow-sm focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
                placeholder={filter.type === "date" ? "YYYY-MM-DD" : filter.label}
                type={filter.type === "date" ? "date" : "text"}
                value={filters[filter.key] ?? ""}
                onChange={(event) => onChangeFilter(filter.key, event.target.value)}
              />
            )}
          </label>
        ))}
      </div>

      {report.isSensitive ? (
        <p className="rounded-2xl border border-amber-200 bg-[var(--ui-color-warning-soft)] px-3 py-2 text-xs font-semibold text-[var(--ui-color-warning)]">
          Este reporte contiene informacion sensible. La exportacion se solicita al backend y queda
          registrada en auditoria cuando corresponde.
        </p>
      ) : null}

      <div className="flex min-w-0 flex-wrap justify-end gap-2">
        <AdminActionButton
          capability="reports.view"
          branchIds={branchIds}
          className="rounded-2xl border border-[var(--ui-color-border)] bg-white px-3 py-2 text-sm font-semibold text-slate-700 transition hover:border-[var(--ui-color-info)] disabled:cursor-not-allowed disabled:opacity-40"
          disabled={!canGenerate || generationPending}
          type="button"
          onClick={onGenerate}
        >
          Generar vista previa
        </AdminActionButton>
        <AdminActionButton
          capability="reports.export"
          branchIds={branchIds}
          className="rounded-2xl border border-[var(--ui-color-border)] bg-white px-3 py-2 text-sm font-semibold text-slate-700 transition hover:border-[var(--ui-color-info)] disabled:cursor-not-allowed disabled:opacity-40"
          disabled={!canExport || exportPending}
          type="button"
          onClick={onExport}
          title={!canExport ? "La exportacion no esta disponible para este reporte." : undefined}
        >
          Exportar JSON
        </AdminActionButton>
      </div>
    </section>
  );
}
