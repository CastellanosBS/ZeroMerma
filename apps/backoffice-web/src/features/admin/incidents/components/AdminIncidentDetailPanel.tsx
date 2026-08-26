import type { ReactNode } from "react";

import { AdminEmptyState } from "../../components/AdminEmptyState";
import type { AdminIncidentDetail, AdminIncidentListItem } from "../types";

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
    CLOSED: "Cerrada",
    IN_PROGRESS: "En seguimiento",
    IN_REVIEW: "En revision",
    OPEN: "Abierta",
    RESOLVED: "Resuelta",
    WAITING_ACTION: "Esperando accion",
  };
  return labels[value] ?? value;
}

function incidentTypeLabel(value: string): string {
  const labels: Record<string, string> = {
    CLEANING_NON_COMPLIANCE: "Incumplimiento de limpieza",
    CUSTOMER_COMPLAINT: "Queja de cliente",
    EQUIPMENT_FAILURE: "Falla de equipo",
    INVENTORY_ISSUE: "Problema de inventario",
    OTHER: "Otro",
    PROCESS_DEVIATION: "Desviacion de proceso",
    PRODUCTION_ISSUE: "Problema de produccion",
    SAFETY_ISSUE: "Seguridad",
    SANITATION_ISSUE: "Sanitaria",
    TRANSFER_ISSUE: "Transferencia",
    WASTE_ISSUE: "Merma",
  };
  return labels[value] ?? value;
}

function sourceTypeLabel(value: string): string {
  const labels: Record<string, string> = {
    CLEANING_LOG: "Bitacora de limpieza",
    CORRECTION: "Correccion",
    CUSTOMER_REPORT: "Reporte de cliente",
    EQUIPMENT: "Equipo",
    INVENTORY: "Inventario",
    MANUAL: "Manual",
    PRODUCTION: "Produccion",
    SANITARY_VERIFICATION: "Verificacion sanitaria",
    TRANSFER: "Transferencia",
    WASTE_MERMA: "Merma",
  };
  return labels[value] ?? value;
}

function Section({ children, title }: { children: ReactNode; title: string }) {
  return (
    <section className="rounded-[18px] border border-[var(--ui-color-border)] bg-white p-3">
      <h4 className="text-sm font-semibold text-slate-950">{title}</h4>
      <div className="mt-2 min-w-0">{children}</div>
    </section>
  );
}

function Fact({ label, value }: { label: string; value: ReactNode }) {
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

interface AdminIncidentDetailPanelProps {
  detail: AdminIncidentDetail | null;
  errorMessage?: string | null;
  isLoading?: boolean;
  onAddFollowUp: (item: AdminIncidentListItem) => void;
  onCopyFolio: (item: AdminIncidentListItem | string) => void;
  onMarkInProgress: (item: AdminIncidentListItem) => void;
  onReopen: (item: AdminIncidentListItem) => void;
  onResolve: (item: AdminIncidentListItem) => void;
  selectedIncident: AdminIncidentListItem | null;
}

export function AdminIncidentDetailPanel({
  detail,
  errorMessage,
  isLoading = false,
  onAddFollowUp,
  onCopyFolio,
  onMarkInProgress,
  onReopen,
  onResolve,
  selectedIncident,
}: AdminIncidentDetailPanelProps) {
  if (!selectedIncident) {
    return (
      <AdminEmptyState
        description="Selecciona una incidencia para revisar origen, severidad, seguimiento y documentos relacionados."
        title="Sin incidencia seleccionada"
      />
    );
  }

  if (isLoading) {
    return (
      <AdminEmptyState
        description="Consultando origen, seguimiento, evidencia, documentos y acciones permitidas."
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
        description="Selecciona una incidencia para revisar origen, severidad, seguimiento y documentos relacionados."
        title="Sin incidencia seleccionada"
      />
    );
  }

  return (
    <aside className="flex min-h-0 min-w-0 flex-col overflow-hidden rounded-[20px] border border-[var(--ui-color-border)] bg-slate-50/70">
      <div className="shrink-0 border-b border-[var(--ui-color-border)] bg-white px-3 py-3">
        <div className="flex min-w-0 items-start justify-between gap-3">
          <div className="min-w-0">
            <p className="truncate text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">
              Detalle de incidencia
            </p>
            <h3 className="mt-1 truncate text-lg font-semibold text-slate-950">
              {detail.overview.folio}
            </h3>
            <p className="mt-1 truncate text-sm text-slate-600">{detail.overview.title}</p>
          </div>
          <span className="shrink-0 rounded-full border border-[var(--ui-color-border)] bg-slate-50 px-3 py-1 text-xs font-semibold text-slate-700">
            {statusLabel(detail.overview.status)}
          </span>
        </div>
      </div>

      <div className="grid min-h-0 gap-2 overflow-y-auto p-2.5">
        <Section title="Resumen">
          <div className="grid gap-2 sm:grid-cols-2">
            <Fact label="Titulo" value={detail.overview.title} />
            <Fact label="Sucursal" value={detail.overview.branchName} />
            <Fact label="Area" value={detail.overview.areaName ?? "Sin area"} />
            <Fact label="Tipo" value={incidentTypeLabel(detail.overview.incidentType)} />
            <Fact label="Origen" value={sourceTypeLabel(detail.overview.sourceType)} />
            <Fact label="Severidad" value={detail.overview.severity} />
            <Fact label="Estado" value={statusLabel(detail.overview.status)} />
            <Fact label="Responsable" value={detail.overview.responsibleUserName ?? "Sin responsable"} />
            <Fact label="Reportada por" value={detail.overview.reportedByUserName} />
            <Fact label="Creada" value={formatDateTime(detail.overview.createdAt)} />
            <Fact label="Vence" value={formatDateTime(detail.overview.dueAt)} />
            <Fact label="Resuelta" value={formatDateTime(detail.overview.resolvedAt)} />
          </div>
        </Section>

        <Section title="Ubicacion / alcance">
          <div className="grid gap-2 sm:grid-cols-2">
            <Fact
              label="Sucursal"
              value={`${detail.locationScope.branchName} (${detail.locationScope.branchCode})`}
            />
            <Fact label="Zona" value={detail.locationScope.areaName ?? "Sin area"} />
            <Fact label="Equipo" value={detail.locationScope.equipmentName ?? "Sin equipo"} />
            <Fact label="Proceso" value={detail.locationScope.processName ?? "Sin proceso"} />
            <Fact label="Produccion" value={detail.locationScope.productionReference ?? "N/A"} />
            <Fact label="Producto / inventario" value={detail.locationScope.productReference ?? "N/A"} />
          </div>
        </Section>

        <Section title="Documento origen">
          {detail.sourceDocument.sourceDocumentId ? (
            <div className="grid gap-2 sm:grid-cols-2">
              <Fact label="Tipo" value={sourceTypeLabel(detail.sourceDocument.sourceType)} />
              <Fact label="Folio" value={detail.sourceDocument.sourceReference ?? "Sin folio"} />
              <Fact label="Ruta" value={detail.sourceDocument.routeHint ?? "Sin ruta"} />
              <Fact label="Documento" value={detail.sourceDocument.sourceDocumentId} />
              <p className="rounded-[14px] bg-slate-50 px-3 py-2 text-sm text-slate-600 sm:col-span-2">
                {detail.sourceDocument.sourceSummary ?? "Documento origen vinculado."}
              </p>
            </div>
          ) : (
            <p className="rounded-[14px] border border-dashed border-[var(--ui-color-border)] px-3 py-3 text-sm text-slate-600">
              Esta incidencia fue registrada manualmente y no tiene documento origen.
            </p>
          )}
        </Section>

        <Section title="Descripcion / clasificacion">
          <div className="grid gap-2">
            <p className="rounded-[14px] bg-slate-50 px-3 py-2 text-sm text-slate-700">
              {detail.descriptionClassification.description}
            </p>
            <div className="grid gap-2 sm:grid-cols-2">
              <Fact
                label="Impacto operativo"
                value={detail.descriptionClassification.operationalImpact ?? "No registrado"}
              />
              <Fact
                label="Impacto inocuidad"
                value={detail.descriptionClassification.foodSafetyImpact ? "Si" : "No"}
              />
              <Fact label="Riesgo" value={detail.descriptionClassification.riskLevel} />
              <Fact label="Notas" value={detail.descriptionClassification.notes ?? "Sin notas"} />
            </div>
          </div>
        </Section>

        <Section title="Accion correctiva / seguimiento">
          <div className="grid gap-2">
            <p className="rounded-[14px] bg-slate-50 px-3 py-2 text-sm text-slate-700">
              {detail.correctiveAction.correctiveAction ?? "Sin accion correctiva registrada."}
            </p>
            <div className="grid gap-2 sm:grid-cols-2">
              <Fact label="Progreso" value={statusLabel(detail.correctiveAction.currentProgress)} />
              <Fact label="Responsable" value={detail.correctiveAction.responsibleUserName ?? "Sin responsable"} />
              <Fact label="Vence" value={formatDateTime(detail.correctiveAction.dueAt)} />
              <Fact label="Completada" value={formatDateTime(detail.correctiveAction.resolvedAt)} />
              <Fact label="Resultado" value={detail.correctiveAction.resolutionResult ?? "Pendiente"} />
              <Fact label="Resolucion" value={detail.correctiveAction.resolutionNote ?? "Pendiente"} />
            </div>
          </div>
        </Section>

        <Section title="Evidencia">
          {detail.evidence.hasEvidence ? (
            <p className="rounded-[14px] bg-slate-50 px-3 py-2 text-sm text-slate-700">
              {detail.evidence.evidenceNote ?? "Evidencia registrada."}
            </p>
          ) : (
            <p className="rounded-[14px] border border-dashed border-[var(--ui-color-border)] px-3 py-3 text-sm text-slate-600">
              Esta incidencia no tiene evidencia adjunta.
            </p>
          )}
          <p className="mt-2 text-xs text-slate-500">{detail.evidence.emptyState}</p>
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
                  <span className="ml-2 text-slate-500">{document.status}</span>
                </div>
              ))}
            </div>
          ) : (
            <p className="rounded-[14px] border border-dashed border-[var(--ui-color-border)] px-3 py-3 text-sm text-slate-600">
              Esta incidencia no tiene documentos relacionados.
            </p>
          )}
        </Section>

        <Section title="Notas de seguimiento">
          {detail.followUps.length > 0 ? (
            <div className="grid gap-1.5">
              {detail.followUps.map((note) => (
                <article
                  className="rounded-[14px] border border-[var(--ui-color-border)] bg-slate-50 px-3 py-2 text-sm"
                  key={note.id}
                >
                  <div className="flex min-w-0 flex-wrap items-center justify-between gap-2">
                    <span className="font-semibold text-slate-950">{note.createdByUserName}</span>
                    <span className="text-xs text-slate-500">{formatDateTime(note.createdAt)}</span>
                  </div>
                  <p className="mt-1 text-slate-600">{note.note}</p>
                  {note.statusChange ? (
                    <p className="mt-1 text-xs font-semibold text-slate-500">
                      Cambio de estado: {statusLabel(note.statusChange)}
                    </p>
                  ) : null}
                </article>
              ))}
            </div>
          ) : (
            <p className="rounded-[14px] border border-dashed border-[var(--ui-color-border)] px-3 py-3 text-sm text-slate-600">
              Esta incidencia no tiene notas de seguimiento.
            </p>
          )}
        </Section>

        <Section title="Timeline / auditoria">
          {detail.timeline.length > 0 ? (
            <div className="grid gap-1.5">
              {detail.timeline.map((event) => (
                <div
                  className="rounded-[14px] border border-[var(--ui-color-border)] bg-slate-50 px-3 py-2 text-sm"
                  key={`${event.label}-${event.occurredAt}`}
                >
                  <span className="font-semibold text-slate-950">{event.label}</span>
                  <span className="ml-2 text-xs text-slate-500">
                    {formatDateTime(event.occurredAt)}
                  </span>
                  {event.note ? <p className="mt-1 text-slate-600">{event.note}</p> : null}
                </div>
              ))}
            </div>
          ) : (
            <p className="rounded-[14px] border border-dashed border-[var(--ui-color-border)] px-3 py-3 text-sm text-slate-600">
              Sin eventos adicionales disponibles.
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
              disabled={!detail.availableActions.canAddFollowUp}
              type="button"
              onClick={() => onAddFollowUp(detail.overview)}
            >
              Agregar seguimiento
            </button>
            <button
              className="rounded-full border border-[var(--ui-color-border)] bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 disabled:cursor-not-allowed disabled:opacity-40"
              disabled={!detail.availableActions.canMarkInProgress}
              type="button"
              onClick={() => onMarkInProgress(detail.overview)}
            >
              Marcar en seguimiento
            </button>
            <button
              className="rounded-full border border-[var(--ui-color-border)] bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 disabled:cursor-not-allowed disabled:opacity-40"
              disabled={!detail.availableActions.canResolve}
              type="button"
              onClick={() => onResolve(detail.overview)}
            >
              Resolver
            </button>
            <button
              className="rounded-full border border-[var(--ui-color-border)] bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 disabled:cursor-not-allowed disabled:opacity-40"
              disabled={!detail.availableActions.canReopen}
              type="button"
              onClick={() => onReopen(detail.overview)}
            >
              Reabrir
            </button>
          </div>
          {detail.availableActions.note ? (
            <p className="mt-2 text-xs text-slate-500">{detail.availableActions.note}</p>
          ) : null}
          {detail.warnings.map((warning) => (
            <p
              className="mt-2 rounded-[14px] border border-amber-200 bg-[var(--ui-color-warning-soft)] px-3 py-2 text-sm font-semibold text-[var(--ui-color-warning)]"
              key={`${warning.code}-${warning.message}`}
            >
              {warning.message}
            </p>
          ))}
        </Section>
      </div>
    </aside>
  );
}
