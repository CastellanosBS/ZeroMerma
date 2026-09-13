import { AdminActionButton } from "../../components/AdminActionButton";
import type { ReactNode } from "react";

import { AdminEmptyState } from "../../components/AdminEmptyState";
import type { AdminSanitaryVerificationDetail, AdminSanitaryVerificationListItem } from "../types";

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
    PENDING: "Pendiente",
    REQUIRES_FOLLOW_UP: "Por seguimiento",
    SCHEDULED: "Programada",
  };
  return labels[value] ?? value;
}

function resultLabel(value: string): string {
  const labels: Record<string, string> = {
    FAILED: "Fallida",
    NOT_EVALUATED: "Sin evaluar",
    PARTIAL: "Parcial",
    PASSED: "Aprobada",
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

interface AdminSanitaryVerificationDetailPanelProps {
  detail: AdminSanitaryVerificationDetail | null;
  errorMessage?: string | null;
  isLoading?: boolean;
  onCopyFolio: (item: AdminSanitaryVerificationListItem | string) => void;
  onExecute: (item: AdminSanitaryVerificationListItem) => void;
  onStart: (item: AdminSanitaryVerificationListItem) => void;
  selectedVerification: AdminSanitaryVerificationListItem | null;
}

export function AdminSanitaryVerificationDetailPanel({
  detail,
  errorMessage,
  isLoading = false,
  onCopyFolio,
  onExecute,
  onStart,
  selectedVerification,
}: AdminSanitaryVerificationDetailPanelProps) {
  if (!selectedVerification) {
    return (
      <AdminEmptyState
        description="Selecciona una verificacion para revisar checklist, resultado, evidencia e incidencias relacionadas."
        title="Sin verificacion seleccionada"
      />
    );
  }

  if (isLoading) {
    return (
      <AdminEmptyState
        description="Consultando detalle, checklist, hallazgos, evidencia y acciones permitidas."
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
        description="Selecciona una verificacion para revisar checklist, resultado, evidencia e incidencias relacionadas."
        title="Sin verificacion seleccionada"
      />
    );
  }

  return (
    <aside className="flex min-h-0 min-w-0 flex-col overflow-hidden rounded-[20px] border border-[var(--ui-color-border)] bg-slate-50/70">
      <div className="shrink-0 border-b border-[var(--ui-color-border)] bg-white px-3 py-3">
        <div className="flex min-w-0 items-start justify-between gap-3">
          <div className="min-w-0">
            <p className="truncate text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">
              Detalle sanitario
            </p>
            <h3 className="mt-1 truncate text-lg font-semibold text-slate-950">
              {detail.overview.folio}
            </h3>
            <p className="mt-1 truncate text-sm text-slate-600">
              {detail.checklistTemplate.templateName}
            </p>
          </div>
          <span className="shrink-0 rounded-full border border-[var(--ui-color-border)] bg-slate-50 px-3 py-1 text-xs font-semibold text-slate-700">
            {resultLabel(detail.overview.result)}
          </span>
        </div>
      </div>

      <div className="grid min-h-0 gap-2 overflow-y-auto p-2.5">
        <Section title="Resumen">
          <div className="grid gap-2 sm:grid-cols-2">
            <Fact label="Sucursal" value={detail.overview.branchName} />
            <Fact label="Area" value={detail.overview.areaName} />
            <Fact label="Equipo" value={detail.overview.equipmentName ?? "N/A"} />
            <Fact label="Proceso" value={detail.overview.processName ?? "N/A"} />
            <Fact label="Resultado" value={resultLabel(detail.overview.result)} />
            <Fact label="Estado" value={statusLabel(detail.overview.status)} />
            <Fact label="Riesgo" value={detail.overview.riskLevel} />
            <Fact label="Inspector" value={detail.overview.inspectorUserName} />
            <Fact label="Programada" value={formatDateTime(detail.overview.scheduledAt)} />
            <Fact label="Realizada" value={formatDateTime(detail.overview.completedAt)} />
            <Fact label="Creada por" value={detail.overview.createdByUserName} />
            <Fact label="Creada" value={formatDateTime(detail.overview.createdAt)} />
          </div>
        </Section>

        <Section title="Ubicacion / alcance">
          <div className="grid gap-2 sm:grid-cols-2">
            <Fact
              label="Sucursal"
              value={`${detail.scope.branchName} (${detail.scope.branchCode})`}
            />
            <Fact label="Tipo area" value={detail.scope.areaType} />
            <Fact label="Zona" value={detail.scope.areaName} />
            <Fact label="Proceso" value={detail.scope.processName ?? detail.scope.processType} />
            <Fact label="Equipo" value={detail.scope.equipmentName ?? "Sin equipo vinculado"} />
          </div>
        </Section>

        <Section title="Checklist / plantilla">
          <div className="grid gap-2 sm:grid-cols-2">
            <Fact label="Plantilla" value={detail.checklistTemplate.templateName} />
            <Fact label="Frecuencia" value={detail.checklistTemplate.frequency ?? "Manual"} />
            <Fact label="Puntos" value={detail.checklistTemplate.totalItems} />
            <Fact label="Umbral" value={`${detail.checklistTemplate.passThresholdPercent}%`} />
            <Fact label="Aprobados" value={detail.checklistTemplate.passedItems} />
            <Fact label="Fallidos" value={detail.checklistTemplate.failedItems} />
          </div>
          {detail.checklistTemplate.description ? (
            <p className="mt-2 rounded-[14px] bg-slate-50 px-3 py-2 text-sm text-slate-600">
              {detail.checklistTemplate.description}
            </p>
          ) : null}
        </Section>

        <Section title="Resultados del checklist">
          {detail.checklistResults.length > 0 ? (
            <div className="grid gap-1.5">
              {detail.checklistResults.map((item) => (
                <article
                  className="grid min-w-0 gap-2 rounded-[14px] border border-[var(--ui-color-border)] bg-slate-50 px-3 py-2 sm:grid-cols-[auto_minmax(0,1fr)_auto]"
                  key={item.id ?? `${item.label}-${item.displayOrder ?? 0}`}
                >
                  <span
                    className={`mt-0.5 h-3 w-3 rounded-full ${
                      item.result === "PASSED"
                        ? "bg-[var(--ui-color-success)]"
                        : item.result === "FAILED"
                          ? "bg-[var(--ui-color-danger)]"
                          : "bg-slate-300"
                    }`}
                  />
                  <span className="min-w-0">
                    <span className="block truncate text-sm font-semibold text-slate-950">
                      {item.label}
                    </span>
                    {item.expectedStandard ? (
                      <span className="block truncate text-xs text-slate-500">
                        {item.expectedStandard}
                      </span>
                    ) : null}
                    {item.notes ? (
                      <span className="block truncate text-xs text-slate-500">{item.notes}</span>
                    ) : null}
                  </span>
                  <span className="text-xs font-semibold text-slate-500">
                    {resultLabel(item.result)}
                  </span>
                </article>
              ))}
            </div>
          ) : (
            <p className="rounded-[14px] border border-dashed border-[var(--ui-color-border)] px-3 py-3 text-sm text-slate-600">
              Esta verificacion no tiene checklist asociado.
            </p>
          )}
        </Section>

        <Section title="Puntaje / resultado">
          <div className="grid gap-2 sm:grid-cols-3">
            <Fact label="Puntaje" value={detail.scoreResult.score ?? "N/A"} />
            <Fact label="Maximo" value={detail.scoreResult.maxScore ?? "N/A"} />
            <Fact
              label="Porcentaje"
              value={
                detail.scoreResult.percentage == null
                  ? "No disponible"
                  : `${detail.scoreResult.percentage}%`
              }
            />
          </div>
        </Section>

        <Section title="Evidencia">
          {detail.evidence.hasEvidence ? (
            <p className="rounded-[14px] bg-slate-50 px-3 py-2 text-sm text-slate-700">
              {detail.evidence.evidenceNote}
            </p>
          ) : (
            <p className="rounded-[14px] border border-dashed border-[var(--ui-color-border)] px-3 py-3 text-sm text-slate-600">
              Esta verificacion no tiene evidencia adjunta.
            </p>
          )}
          <p className="mt-2 text-xs text-slate-500">{detail.evidence.emptyState}</p>
        </Section>

        <Section title="Hallazgos / observaciones">
          <div className="grid gap-2">
            <p className="rounded-[14px] bg-slate-50 px-3 py-2 text-sm text-slate-700">
              {detail.findingsObservations.findingsNotes ??
                detail.findingsObservations.notes ??
                detail.findingsObservations.cancellationReason ??
                "Sin hallazgos registrados."}
            </p>
            {detail.findingsObservations.followUpRequired ? (
              <p className="rounded-[14px] border border-amber-200 bg-[var(--ui-color-warning-soft)] px-3 py-2 text-sm font-semibold text-[var(--ui-color-warning)]">
                Requiere seguimiento documentado.
              </p>
            ) : null}
            {detail.warnings.map((warning) => (
              <p
                className="rounded-[14px] border border-amber-200 bg-[var(--ui-color-warning-soft)] px-3 py-2 text-sm font-semibold text-[var(--ui-color-warning)]"
                key={`${warning.code}-${warning.message}`}
              >
                {warning.message}
              </p>
            ))}
          </div>
        </Section>

        <Section title="Bitacoras de limpieza relacionadas">
          {detail.relatedCleaningLogs.length > 0 ? (
            <div className="grid gap-1.5">
              {detail.relatedCleaningLogs.map((log) => (
                <div
                  className="rounded-[14px] border border-[var(--ui-color-border)] bg-slate-50 px-3 py-2 text-sm"
                  key={log.id}
                >
                  <span className="font-semibold text-slate-950">{log.folio}</span>
                  <span className="ml-2 text-slate-500">{log.status}</span>
                  <span className="ml-2 text-slate-500">{log.responsibleUserName}</span>
                </div>
              ))}
            </div>
          ) : (
            <p className="rounded-[14px] border border-dashed border-[var(--ui-color-border)] px-3 py-3 text-sm text-slate-600">
              No hay bitacoras de limpieza relacionadas con esta verificacion.
            </p>
          )}
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
              Esta verificacion no tiene documentos relacionados.
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
            <AdminActionButton
              capability="quality_hygiene.manage"
              branchIds={[detail.overview.branchId]}
              className="rounded-full border border-[var(--ui-color-border)] bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 disabled:cursor-not-allowed disabled:opacity-40"
              disabled={!detail.availableActions.canStart}
              type="button"
              onClick={() => onStart(detail.overview)}
            >
              Iniciar
            </AdminActionButton>
            <AdminActionButton
              capability="quality_hygiene.manage"
              branchIds={[detail.overview.branchId]}
              className="rounded-full border border-[var(--ui-color-border)] bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 disabled:cursor-not-allowed disabled:opacity-40"
              disabled={!detail.availableActions.canComplete}
              type="button"
              onClick={() => onExecute(detail.overview)}
            >
              Ejecutar checklist
            </AdminActionButton>
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
