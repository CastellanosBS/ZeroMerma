import { AdminEmptyState } from "../../components/AdminEmptyState";
import type { AdminCleaningLogDetail, AdminCleaningLogListItem } from "../types";

function formatDateTime(value: string | null | undefined): string {
  if (!value) {
    return "No disponible";
  }
  return new Intl.DateTimeFormat("es-MX", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function statusLabel(value: string): string {
  const labels: Record<string, string> = {
    CANCELLED: "Cancelada",
    COMPLETED: "Completada",
    IN_PROGRESS: "En proceso",
    MISSED: "Vencida",
    PENDING: "Pendiente",
    REQUIRES_REVIEW: "Por revisar",
    SCHEDULED: "Programada",
  };
  return labels[value] ?? value;
}

function Section({ children, title }: { children: React.ReactNode; title: string }) {
  return (
    <section className="rounded-[18px] border border-[var(--ui-color-border)] bg-white p-3">
      <h4 className="text-sm font-semibold text-slate-950">{title}</h4>
      <div className="mt-2 min-w-0">{children}</div>
    </section>
  );
}

function Fact({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="min-w-0">
      <span className="block truncate text-xs font-semibold uppercase tracking-[0.08em] text-slate-500">
        {label}
      </span>
      <span className="mt-0.5 block min-w-0 truncate text-sm font-semibold text-slate-950">
        {value}
      </span>
    </div>
  );
}

interface AdminCleaningLogDetailPanelProps {
  detail: AdminCleaningLogDetail | null;
  errorMessage?: string | null;
  isLoading?: boolean;
  onCopyFolio: (item: AdminCleaningLogListItem | string) => void;
  onRegisterCompletion: (item: AdminCleaningLogListItem) => void;
  selectedCleaningLog: AdminCleaningLogListItem | null;
}

export function AdminCleaningLogDetailPanel({
  detail,
  errorMessage,
  isLoading = false,
  onCopyFolio,
  onRegisterCompletion,
  selectedCleaningLog,
}: AdminCleaningLogDetailPanelProps) {
  if (!selectedCleaningLog) {
    return (
      <AdminEmptyState
        description="Selecciona una bitacora para revisar checklist, responsable, evidencia y documentos relacionados."
        title="Sin bitacora seleccionada"
      />
    );
  }

  if (isLoading) {
    return (
      <AdminEmptyState
        description="Consultando detalle, checklist, evidencia y acciones permitidas."
        title="Cargando detalle"
      />
    );
  }

  if (errorMessage) {
    return <AdminEmptyState description={errorMessage} title="No se pudo cargar el detalle" />;
  }

  if (!detail) {
    return (
      <AdminEmptyState
        description="Selecciona una bitacora para revisar checklist, responsable, evidencia y documentos relacionados."
        title="Sin bitacora seleccionada"
      />
    );
  }

  return (
    <aside className="flex min-h-0 min-w-0 flex-col overflow-hidden rounded-[20px] border border-[var(--ui-color-border)] bg-slate-50/70">
      <div className="shrink-0 border-b border-[var(--ui-color-border)] bg-white px-3 py-3">
        <div className="flex min-w-0 items-start justify-between gap-3">
          <div className="min-w-0">
            <p className="truncate text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">
              Detalle de bitacora
            </p>
            <h3 className="mt-1 truncate text-lg font-semibold text-slate-950">
              {detail.overview.folio}
            </h3>
            <p className="mt-1 truncate text-sm text-slate-600">{detail.overview.taskName}</p>
          </div>
          <span className="shrink-0 rounded-full border border-[var(--ui-color-border)] bg-slate-50 px-3 py-1 text-xs font-semibold text-slate-700">
            {statusLabel(detail.overview.status)}
          </span>
        </div>
      </div>

      <div className="grid min-h-0 gap-2 overflow-y-auto p-2.5">
        <Section title="Resumen">
          <div className="grid gap-2 sm:grid-cols-2">
            <Fact label="Sucursal" value={detail.overview.branchName} />
            <Fact label="Area" value={detail.overview.areaName} />
            <Fact label="Equipo" value={detail.overview.equipmentName ?? "N/A"} />
            <Fact label="Tipo" value={detail.overview.cleaningType} />
            <Fact label="Riesgo" value={detail.overview.riskLevel} />
            <Fact label="Turno" value={detail.overview.shiftCode} />
            <Fact label="Programada" value={formatDateTime(detail.overview.scheduledAt)} />
            <Fact label="Completada" value={formatDateTime(detail.overview.completedAt)} />
            <Fact label="Responsable" value={detail.overview.responsibleUserName} />
            <Fact label="Creada por" value={detail.overview.createdByUserName} />
          </div>
        </Section>

        <Section title="Ubicacion / area">
          <div className="grid gap-2 sm:grid-cols-2">
            <Fact
              label="Sucursal"
              value={`${detail.locationArea.branchName} (${detail.locationArea.branchCode})`}
            />
            <Fact label="Tipo de area" value={detail.locationArea.areaType} />
            <Fact label="Zona" value={detail.locationArea.areaName} />
            <Fact
              label="Equipo"
              value={detail.locationArea.equipmentName ?? "Sin equipo vinculado"}
            />
          </div>
        </Section>

        <Section title="Tarea / plantilla">
          <div className="grid gap-2 sm:grid-cols-2">
            <Fact label="Tarea" value={detail.taskTemplate.taskName} />
            <Fact label="Plantilla" value={detail.taskTemplate.taskTemplateName ?? "Manual"} />
            <Fact label="Frecuencia" value={detail.taskTemplate.frequency ?? "Manual"} />
            <Fact
              label="Duracion"
              value={
                detail.taskTemplate.estimatedDurationMinutes == null
                  ? "N/A"
                  : `${detail.taskTemplate.estimatedDurationMinutes} min`
              }
            />
          </div>
          {detail.taskTemplate.methodSummary ? (
            <p className="mt-2 rounded-[14px] bg-slate-50 px-3 py-2 text-sm text-slate-600">
              {detail.taskTemplate.methodSummary}
            </p>
          ) : null}
          {detail.taskTemplate.requiredTools ? (
            <p className="mt-2 rounded-[14px] bg-slate-50 px-3 py-2 text-sm text-slate-600">
              {detail.taskTemplate.requiredTools}
            </p>
          ) : null}
        </Section>

        <Section title="Checklist">
          {detail.checklist.length > 0 ? (
            <div className="grid gap-1.5">
              {detail.checklist.map((item) => (
                <article
                  className="grid min-w-0 gap-2 rounded-[14px] border border-[var(--ui-color-border)] bg-slate-50 px-3 py-2 sm:grid-cols-[auto_minmax(0,1fr)_auto]"
                  key={item.id}
                >
                  <span
                    className={`mt-0.5 h-3 w-3 rounded-full ${
                      item.isCompleted ? "bg-[var(--ui-color-success)]" : "bg-slate-300"
                    }`}
                  />
                  <span className="min-w-0">
                    <span className="block truncate text-sm font-semibold text-slate-950">
                      {item.label}
                    </span>
                    {item.notes ? (
                      <span className="block truncate text-xs text-slate-500">{item.notes}</span>
                    ) : null}
                  </span>
                  <span className="text-xs font-semibold text-slate-500">
                    {item.isRequired ? "Requerido" : "Opcional"}
                  </span>
                </article>
              ))}
            </div>
          ) : (
            <p className="rounded-[14px] border border-dashed border-[var(--ui-color-border)] px-3 py-3 text-sm text-slate-600">
              Esta bitacora no tiene checklist asociado.
            </p>
          )}
        </Section>

        <Section title="Evidencia">
          {detail.evidence.hasEvidence ? (
            <p className="rounded-[14px] bg-slate-50 px-3 py-2 text-sm text-slate-700">
              {detail.evidence.evidenceNote}
            </p>
          ) : (
            <p className="rounded-[14px] border border-dashed border-[var(--ui-color-border)] px-3 py-3 text-sm text-slate-600">
              Esta bitacora no tiene evidencia adjunta.
            </p>
          )}
          <p className="mt-2 text-xs text-slate-500">{detail.evidence.emptyState}</p>
        </Section>

        <Section title="Observaciones / incidencias">
          <div className="grid gap-2">
            <p className="rounded-[14px] bg-slate-50 px-3 py-2 text-sm text-slate-700">
              {detail.observationsIssues.notes ??
                detail.observationsIssues.issueNotes ??
                detail.observationsIssues.cancellationReason ??
                "Sin observaciones registradas."}
            </p>
            {detail.warnings.length > 0 ? (
              <div className="grid gap-1.5">
                {detail.warnings.map((warning) => (
                  <p
                    className="rounded-[14px] border border-amber-200 bg-[var(--ui-color-warning-soft)] px-3 py-2 text-sm font-semibold text-[var(--ui-color-warning)]"
                    key={`${warning.code}-${warning.message}`}
                  >
                    {warning.message}
                  </p>
                ))}
              </div>
            ) : null}
          </div>
        </Section>

        <Section title="Documentos relacionados">
          {detail.relatedDocuments.length > 0 ? (
            <div className="grid gap-1.5">
              {detail.relatedDocuments.map((document) => (
                <div
                  className="rounded-[14px] border border-[var(--ui-color-border)] bg-slate-50 px-3 py-2 text-sm"
                  key={`${document.documentType}-${document.documentId}`}
                >
                  <span className="font-semibold text-slate-950">{document.folio}</span>
                  <span className="ml-2 text-slate-500">{document.documentType}</span>
                </div>
              ))}
            </div>
          ) : (
            <p className="rounded-[14px] border border-dashed border-[var(--ui-color-border)] px-3 py-3 text-sm text-slate-600">
              Esta bitacora no tiene documentos relacionados.
            </p>
          )}
        </Section>

        <Section title="Acciones disponibles">
          <div className="flex flex-wrap gap-2">
            <button
              className="rounded-full border border-[var(--ui-color-border)] bg-white px-3 py-1.5 text-xs font-semibold text-slate-700"
              type="button"
              onClick={() => onCopyFolio(detail.overview.folio)}
            >
              Copiar folio
            </button>
            <button
              className="rounded-full border border-[var(--ui-color-border)] bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 disabled:cursor-not-allowed disabled:opacity-40"
              disabled={!detail.availableActions.canComplete}
              type="button"
              onClick={() => onRegisterCompletion(detail.overview)}
            >
              Registrar completion
            </button>
            <button
              className="rounded-full border border-[var(--ui-color-border)] bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 disabled:cursor-not-allowed disabled:opacity-40"
              disabled={!detail.availableActions.canCreateIncident}
              type="button"
            >
              Crear incidencia
            </button>
          </div>
          {detail.availableActions.note ? (
            <p className="mt-2 text-xs text-slate-500">{detail.availableActions.note}</p>
          ) : null}
        </Section>
      </div>
    </aside>
  );
}
