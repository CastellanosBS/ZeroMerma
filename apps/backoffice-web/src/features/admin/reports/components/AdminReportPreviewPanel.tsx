import { AdminEmptyState } from "../../components/AdminEmptyState";
import type { AdminReportDefinition, AdminReportPreview } from "../types";

interface AdminReportPreviewPanelProps {
  errorMessage?: string | null;
  isLoading?: boolean;
  preview: AdminReportPreview | null;
  report: AdminReportDefinition | null;
}

function formatDateTime(value: string | null | undefined): string {
  if (!value) {
    return "Sin registro";
  }
  return new Intl.DateTimeFormat("es-MX", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function cardClass(tone: string): string {
  if (tone === "success") {
    return "border-emerald-200 bg-[var(--ui-color-success-soft)]";
  }
  if (tone === "warning") {
    return "border-amber-200 bg-[var(--ui-color-warning-soft)]";
  }
  if (tone === "danger") {
    return "border-rose-200 bg-[var(--ui-color-danger-soft)]";
  }
  return "border-[var(--ui-color-border)] bg-white";
}

export function AdminReportPreviewPanel({
  errorMessage,
  isLoading = false,
  preview,
  report,
}: AdminReportPreviewPanelProps) {
  return (
    <section className="flex min-h-0 min-w-0 flex-col overflow-hidden rounded-[20px] border border-[var(--ui-color-border)] bg-white">
      <div className="flex min-w-0 shrink-0 items-center justify-between gap-3 border-b border-[var(--ui-color-border)] px-3 py-2.5">
        <div className="min-w-0">
          <h3 className="truncate text-base font-semibold text-slate-950">Vista previa</h3>
          <p className="truncate text-xs text-slate-500">
            Resultados generados por el backend, con filtros aplicados y enlaces fuente.
          </p>
        </div>
        {preview ? (
          <span className="shrink-0 rounded-full border border-[var(--ui-color-border)] bg-white px-3 py-1 text-xs font-semibold text-slate-600">
            {preview.rows.length} filas
          </span>
        ) : null}
      </div>

      <div className="min-h-0 min-w-0 flex-1 overflow-auto p-2.5">
        {isLoading ? (
          <AdminEmptyState
            description="Generando vista previa con datos persistidos del backend."
            title="Generando reporte"
          />
        ) : errorMessage ? (
          <AdminEmptyState description={errorMessage} title="No se pudo generar reporte" />
        ) : report?.status !== "available" ? (
          <AdminEmptyState
            description="Este reporte requiere soporte backend adicional antes de poder generarse."
            title="Reporte no disponible"
          />
        ) : !preview ? (
          <AdminEmptyState
            description="Selecciona un reporte para configurar filtros, generar vista previa o exportar resultados."
            title="Sin vista previa"
          />
        ) : (
          <div className="grid gap-2">
            <div className="grid gap-2 md:grid-cols-2 xl:grid-cols-4">
              {preview.summaryCards.map((card) => (
                <article
                  className={`rounded-[18px] border p-3 ${cardClass(card.tone)}`}
                  key={card.label}
                >
                  <p className="truncate text-xs font-semibold uppercase tracking-[0.08em] text-slate-500">
                    {card.label}
                  </p>
                  <p className="truncate text-lg font-semibold text-slate-950">{card.value}</p>
                  {card.helperText ? (
                    <p className="truncate text-xs text-slate-500">{card.helperText}</p>
                  ) : null}
                </article>
              ))}
            </div>

            <div className="rounded-[18px] border border-[var(--ui-color-border)] bg-slate-50/80 p-3 text-xs text-slate-600">
              <p>
                <span className="font-semibold text-slate-700">Generado:</span>{" "}
                {formatDateTime(preview.generatedAt)}
              </p>
              <p className="truncate">
                <span className="font-semibold text-slate-700">Filtros:</span>{" "}
                {Object.entries(preview.filtersApplied)
                  .map(([key, value]) => `${key}: ${value}`)
                  .join(" | ") || "Sin filtros"}
              </p>
            </div>

            {preview.warnings.length > 0 ? (
              <div className="grid gap-1">
                {preview.warnings.map((warning) => (
                  <p
                    className="rounded-2xl border border-amber-200 bg-[var(--ui-color-warning-soft)] px-3 py-2 text-xs font-semibold text-[var(--ui-color-warning)]"
                    key={warning}
                  >
                    {warning}
                  </p>
                ))}
              </div>
            ) : null}

            {preview.rows.length > 0 ? (
              <div className="min-w-[72rem] overflow-hidden rounded-[16px] border border-[var(--ui-color-border)]">
                <div
                  className="grid border-b border-[var(--ui-color-border)] bg-slate-50 px-3 py-2 text-xs font-semibold uppercase tracking-[0.08em] text-slate-500"
                  style={{
                    gridTemplateColumns: `repeat(${preview.columns.length}, minmax(9rem, 1fr))`,
                  }}
                >
                  {preview.columns.map((column) => (
                    <span className="truncate" key={column.key}>
                      {column.label}
                    </span>
                  ))}
                </div>
                <div className="divide-y divide-[var(--ui-color-border)]">
                  {preview.rows.map((row) => (
                    <article
                      className="grid bg-white px-3 py-2 text-sm hover:bg-slate-50"
                      key={row.id}
                      style={{
                        gridTemplateColumns: `repeat(${preview.columns.length}, minmax(9rem, 1fr))`,
                      }}
                    >
                      {preview.columns.map((column) => (
                        <span
                          className="truncate text-slate-700"
                          key={column.key}
                          title={row.cells[column.key] ?? ""}
                        >
                          {row.cells[column.key] ?? "Sin dato"}
                        </span>
                      ))}
                    </article>
                  ))}
                </div>
              </div>
            ) : (
              <AdminEmptyState
                description="El reporte no tiene resultados para los filtros seleccionados."
                title="Sin resultados"
              />
            )}

            <div className="rounded-[18px] border border-[var(--ui-color-border)] bg-white p-3">
              <p className="mb-2 text-sm font-semibold text-slate-950">Documentos y modulos fuente</p>
              {preview.relatedLinks.length > 0 ? (
                <div className="flex flex-wrap gap-2">
                  {preview.relatedLinks.map((link) => (
                    <a
                      className="rounded-full border border-[var(--ui-color-border)] bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 transition hover:border-[var(--ui-color-info)]"
                      href={link.routeHint ?? "#"}
                      key={`${link.module}-${link.label}`}
                    >
                      {link.label}
                    </a>
                  ))}
                </div>
              ) : (
                <AdminEmptyState
                  description="El reporte no tiene enlaces a documentos relacionados."
                  title="Sin documentos relacionados"
                />
              )}
            </div>
          </div>
        )}
      </div>
    </section>
  );
}
