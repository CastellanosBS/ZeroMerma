import { useState } from "react";

import type {
  AdminIncidentCreatePayload,
  AdminIncidentFilterOptions,
  AdminIncidentFollowUpPayload,
  AdminIncidentResolvePayload,
  AdminIncidentSeverity,
  AdminIncidentSourceType,
  AdminIncidentStatus,
  AdminIncidentType,
  AdminIncidentListItem,
} from "../types";

const fieldClassName =
  "h-10 w-full min-w-0 rounded-2xl border border-[var(--ui-color-border)] bg-white px-3 text-sm font-medium text-slate-950 outline-none transition focus:border-[var(--ui-color-info)] focus:ring-4 focus:ring-[var(--ui-color-ring)]";

const textareaClassName =
  "min-h-20 w-full min-w-0 resize-y rounded-2xl border border-[var(--ui-color-border)] bg-white px-3 py-2 text-sm font-medium text-slate-950 outline-none transition placeholder:text-slate-400 focus:border-[var(--ui-color-info)] focus:ring-4 focus:ring-[var(--ui-color-ring)]";

function nowLocalInputValue() {
  const value = new Date();
  value.setMinutes(value.getMinutes() - value.getTimezoneOffset());
  return value.toISOString().slice(0, 16);
}

function localInputToIso(value: string | null) {
  return value ? new Date(value).toISOString() : null;
}

function selectOptions(options: { id: string; label: string }[], allLabel = "Selecciona") {
  return (
    <>
      <option value="">{allLabel}</option>
      {options.map((option) => (
        <option key={option.id} value={option.id}>
          {option.label}
        </option>
      ))}
    </>
  );
}

interface AdminIncidentWorkflowPanelProps {
  errorMessage?: string | null;
  incident: AdminIncidentListItem | null;
  isSubmitting?: boolean;
  mode: "create" | "followUp" | "resolve";
  options: AdminIncidentFilterOptions;
  onAddFollowUp: (payload: AdminIncidentFollowUpPayload) => void;
  onCancel: () => void;
  onCreate: (payload: AdminIncidentCreatePayload) => void;
  onResolve: (payload: AdminIncidentResolvePayload) => void;
}

export function AdminIncidentWorkflowPanel({
  errorMessage,
  incident,
  isSubmitting = false,
  mode,
  onAddFollowUp,
  onCancel,
  onCreate,
  onResolve,
  options,
}: AdminIncidentWorkflowPanelProps) {
  const [branchId, setBranchId] = useState("");
  const [areaName, setAreaName] = useState("");
  const [sourceType, setSourceType] = useState<AdminIncidentSourceType>("MANUAL");
  const [sourceDocumentId, setSourceDocumentId] = useState("");
  const [sourceReference, setSourceReference] = useState("");
  const [sourceSummary, setSourceSummary] = useState("");
  const [incidentType, setIncidentType] = useState<AdminIncidentType>("SANITATION_ISSUE");
  const [severity, setSeverity] = useState<AdminIncidentSeverity>("MEDIUM");
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [responsibleUserId, setResponsibleUserId] = useState("");
  const [dueAt, setDueAt] = useState("");
  const [correctiveAction, setCorrectiveAction] = useState("");
  const [operationalImpact, setOperationalImpact] = useState("");
  const [foodSafetyImpact, setFoodSafetyImpact] = useState(false);
  const [equipmentName, setEquipmentName] = useState("");
  const [processName, setProcessName] = useState("");
  const [productReference, setProductReference] = useState("");
  const [productionReference, setProductionReference] = useState("");
  const [evidenceNote, setEvidenceNote] = useState("");
  const [notes, setNotes] = useState("");
  const [followUpNote, setFollowUpNote] = useState("");
  const [statusChange, setStatusChange] = useState<AdminIncidentStatus | "">("");
  const [resolutionNote, setResolutionNote] = useState("");
  const [resolutionResult, setResolutionResult] = useState("");
  const [resolvedAt, setResolvedAt] = useState(nowLocalInputValue());
  const [localError, setLocalError] = useState<string | null>(null);

  function handleCreate() {
    setLocalError(null);
    if (!branchId) {
      setLocalError("Selecciona una sucursal.");
      return;
    }
    if (!title.trim()) {
      setLocalError("Captura el titulo de la incidencia.");
      return;
    }
    if (!description.trim()) {
      setLocalError("Captura la descripcion de la incidencia.");
      return;
    }
    if (incidentType === "OTHER" && !notes.trim()) {
      setLocalError("Las incidencias de tipo OTHER requieren notas.");
      return;
    }
    if (sourceType !== "MANUAL" && !sourceDocumentId.trim() && !sourceReference.trim()) {
      setLocalError("Captura el documento origen o su folio.");
      return;
    }

    onCreate({
      areaName: areaName.trim() || null,
      branchId,
      correctiveAction: correctiveAction.trim() || null,
      description: description.trim(),
      dueAt: localInputToIso(dueAt || null),
      equipmentName: equipmentName.trim() || null,
      evidenceNote: evidenceNote.trim() || null,
      foodSafetyImpact,
      incidentType,
      notes: notes.trim() || null,
      operationalImpact: operationalImpact.trim() || null,
      processName: processName.trim() || null,
      productReference: productReference.trim() || null,
      productionReference: productionReference.trim() || null,
      responsibleUserId: responsibleUserId || null,
      severity,
      sourceDocumentId: sourceDocumentId.trim() || null,
      sourceReference: sourceReference.trim() || null,
      sourceSummary: sourceSummary.trim() || null,
      sourceType,
      title: title.trim(),
    });
  }

  function handleFollowUp() {
    setLocalError(null);
    if (!incident) {
      setLocalError("Selecciona una incidencia.");
      return;
    }
    if (!followUpNote.trim()) {
      setLocalError("Captura una nota de seguimiento.");
      return;
    }
    onAddFollowUp({
      note: followUpNote.trim(),
      statusChange: statusChange || null,
    });
  }

  function handleResolve() {
    setLocalError(null);
    if (!incident) {
      setLocalError("Selecciona una incidencia.");
      return;
    }
    if (!resolutionNote.trim()) {
      setLocalError("La resolucion requiere nota.");
      return;
    }
    if (!resolutionResult.trim()) {
      setLocalError("Captura el resultado de la resolucion.");
      return;
    }
    onResolve({
      evidenceNote: evidenceNote.trim() || null,
      resolutionNote: resolutionNote.trim(),
      resolvedAt: localInputToIso(resolvedAt),
      result: resolutionResult.trim(),
    });
  }

  const titleText =
    mode === "create"
      ? "Nueva incidencia"
      : mode === "followUp"
        ? `Seguimiento ${incident?.folio ?? ""}`
        : `Resolver ${incident?.folio ?? ""}`;

  return (
    <section className="rounded-[20px] border border-[var(--ui-color-border)] bg-slate-50/80 p-4">
      <div className="flex min-w-0 flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">
            Incidencia auditada
          </p>
          <h3 className="mt-1 text-base font-semibold text-slate-950">{titleText}</h3>
          <p className="mt-1 text-sm leading-5 text-slate-600">
            Registra clasificacion, origen, responsable, accion correctiva y evidencia sin alterar
            documentos fuente.
          </p>
        </div>
        <button
          className="shrink-0 rounded-2xl border border-[var(--ui-color-border)] bg-white px-3 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-50 focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
          type="button"
          onClick={onCancel}
        >
          Cerrar
        </button>
      </div>

      {mode === "create" ? (
        <div className="mt-4 grid min-w-0 gap-3 md:grid-cols-2 xl:grid-cols-4">
          <label className="grid min-w-0 gap-1 text-xs font-semibold uppercase tracking-[0.08em] text-slate-500">
            Sucursal
            <select
              className={fieldClassName}
              value={branchId}
              onChange={(event) => setBranchId(event.target.value)}
            >
              {selectOptions(options.branches)}
            </select>
          </label>
          <label className="grid min-w-0 gap-1 text-xs font-semibold uppercase tracking-[0.08em] text-slate-500">
            Area / zona
            <input
              className={fieldClassName}
              placeholder="Cocina, produccion"
              value={areaName}
              onChange={(event) => setAreaName(event.target.value)}
            />
          </label>
          <label className="grid min-w-0 gap-1 text-xs font-semibold uppercase tracking-[0.08em] text-slate-500">
            Tipo
            <select
              className={fieldClassName}
              value={incidentType}
              onChange={(event) => setIncidentType(event.target.value as AdminIncidentType)}
            >
              {selectOptions(options.incidentTypes)}
            </select>
          </label>
          <label className="grid min-w-0 gap-1 text-xs font-semibold uppercase tracking-[0.08em] text-slate-500">
            Severidad
            <select
              className={fieldClassName}
              value={severity}
              onChange={(event) => setSeverity(event.target.value as AdminIncidentSeverity)}
            >
              {selectOptions(options.severities)}
            </select>
          </label>
          <label className="grid min-w-0 gap-1 text-xs font-semibold uppercase tracking-[0.08em] text-slate-500 xl:col-span-2">
            Titulo
            <input
              className={fieldClassName}
              placeholder="Problema detectado"
              value={title}
              onChange={(event) => setTitle(event.target.value)}
            />
          </label>
          <label className="grid min-w-0 gap-1 text-xs font-semibold uppercase tracking-[0.08em] text-slate-500">
            Responsable
            <select
              className={fieldClassName}
              value={responsibleUserId}
              onChange={(event) => setResponsibleUserId(event.target.value)}
            >
              {selectOptions(options.responsibleUsers, "Sin responsable")}
            </select>
          </label>
          <label className="grid min-w-0 gap-1 text-xs font-semibold uppercase tracking-[0.08em] text-slate-500">
            Vence
            <input
              className={fieldClassName}
              type="datetime-local"
              value={dueAt}
              onChange={(event) => setDueAt(event.target.value)}
            />
          </label>
          <label className="grid min-w-0 gap-1 text-xs font-semibold uppercase tracking-[0.08em] text-slate-500">
            Origen
            <select
              className={fieldClassName}
              value={sourceType}
              onChange={(event) => setSourceType(event.target.value as AdminIncidentSourceType)}
            >
              {selectOptions(options.sourceTypes)}
            </select>
          </label>
          <label className="grid min-w-0 gap-1 text-xs font-semibold uppercase tracking-[0.08em] text-slate-500">
            Documento origen
            <input
              className={fieldClassName}
              placeholder="UUID o referencia"
              value={sourceDocumentId}
              onChange={(event) => setSourceDocumentId(event.target.value)}
            />
          </label>
          <label className="grid min-w-0 gap-1 text-xs font-semibold uppercase tracking-[0.08em] text-slate-500">
            Folio origen
            <input
              className={fieldClassName}
              placeholder="CLN-000001"
              value={sourceReference}
              onChange={(event) => setSourceReference(event.target.value)}
            />
          </label>
          <label className="grid min-w-0 gap-1 text-xs font-semibold uppercase tracking-[0.08em] text-slate-500">
            Equipo
            <input
              className={fieldClassName}
              placeholder="Horno, vitrina"
              value={equipmentName}
              onChange={(event) => setEquipmentName(event.target.value)}
            />
          </label>
          <label className="grid min-w-0 gap-1 text-xs font-semibold uppercase tracking-[0.08em] text-slate-500">
            Proceso
            <input
              className={fieldClassName}
              placeholder="Produccion diaria"
              value={processName}
              onChange={(event) => setProcessName(event.target.value)}
            />
          </label>
          <label className="grid min-w-0 gap-1 text-xs font-semibold uppercase tracking-[0.08em] text-slate-500">
            Producto / inventario
            <input
              className={fieldClassName}
              placeholder="SKU o producto"
              value={productReference}
              onChange={(event) => setProductReference(event.target.value)}
            />
          </label>
          <label className="grid min-w-0 gap-1 text-xs font-semibold uppercase tracking-[0.08em] text-slate-500">
            Produccion
            <input
              className={fieldClassName}
              placeholder="Lote o orden"
              value={productionReference}
              onChange={(event) => setProductionReference(event.target.value)}
            />
          </label>
        </div>
      ) : null}

      {mode === "create" ? (
        <div className="mt-4 grid min-w-0 gap-3 md:grid-cols-3">
          <label className="grid min-w-0 gap-1 text-xs font-semibold uppercase tracking-[0.08em] text-slate-500">
            Descripcion
            <textarea
              className={textareaClassName}
              placeholder="Describe que ocurrio y el impacto observable"
              value={description}
              onChange={(event) => setDescription(event.target.value)}
            />
          </label>
          <label className="grid min-w-0 gap-1 text-xs font-semibold uppercase tracking-[0.08em] text-slate-500">
            Accion correctiva
            <textarea
              className={textareaClassName}
              placeholder="Accion a realizar, seguimiento o plan"
              value={correctiveAction}
              onChange={(event) => setCorrectiveAction(event.target.value)}
            />
          </label>
          <label className="grid min-w-0 gap-1 text-xs font-semibold uppercase tracking-[0.08em] text-slate-500">
            Notas
            <textarea
              className={textareaClassName}
              placeholder="Notas internas; requeridas si tipo OTHER"
              value={notes}
              onChange={(event) => setNotes(event.target.value)}
            />
          </label>
          <label className="grid min-w-0 gap-1 text-xs font-semibold uppercase tracking-[0.08em] text-slate-500">
            Impacto operativo
            <textarea
              className={textareaClassName}
              placeholder="Impacto en venta, produccion, calidad o inventario"
              value={operationalImpact}
              onChange={(event) => setOperationalImpact(event.target.value)}
            />
          </label>
          <label className="grid min-w-0 gap-1 text-xs font-semibold uppercase tracking-[0.08em] text-slate-500">
            Resumen origen
            <textarea
              className={textareaClassName}
              placeholder="Resumen del documento origen si aplica"
              value={sourceSummary}
              onChange={(event) => setSourceSummary(event.target.value)}
            />
          </label>
          <label className="grid min-w-0 gap-1 text-xs font-semibold uppercase tracking-[0.08em] text-slate-500">
            Evidencia
            <textarea
              className={textareaClassName}
              placeholder="Referencia de foto, documento o evidencia"
              value={evidenceNote}
              onChange={(event) => setEvidenceNote(event.target.value)}
            />
          </label>
          <label className="flex min-w-0 items-center gap-2 text-sm font-semibold text-slate-700">
            <input
              checked={foodSafetyImpact}
              type="checkbox"
              onChange={(event) => setFoodSafetyImpact(event.target.checked)}
            />
            Tiene impacto de inocuidad
          </label>
        </div>
      ) : null}

      {mode === "followUp" ? (
        <div className="mt-4 grid min-w-0 gap-3 md:grid-cols-[minmax(0,1fr)_16rem]">
          <label className="grid min-w-0 gap-1 text-xs font-semibold uppercase tracking-[0.08em] text-slate-500">
            Nota de seguimiento
            <textarea
              className={textareaClassName}
              placeholder="Seguimiento, avance o decision documentada"
              value={followUpNote}
              onChange={(event) => setFollowUpNote(event.target.value)}
            />
          </label>
          <label className="grid min-w-0 gap-1 text-xs font-semibold uppercase tracking-[0.08em] text-slate-500">
            Cambio de estado
            <select
              className={fieldClassName}
              value={statusChange}
              onChange={(event) => setStatusChange(event.target.value as AdminIncidentStatus | "")}
            >
              <option value="">Sin cambio</option>
              {options.statuses.map((option) => (
                <option key={option.id} value={option.id}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>
        </div>
      ) : null}

      {mode === "resolve" ? (
        <div className="mt-4 grid min-w-0 gap-3 md:grid-cols-4">
          <label className="grid min-w-0 gap-1 text-xs font-semibold uppercase tracking-[0.08em] text-slate-500 md:col-span-2">
            Nota de resolucion
            <textarea
              className={textareaClassName}
              placeholder="Explica como se resolvio la incidencia"
              value={resolutionNote}
              onChange={(event) => setResolutionNote(event.target.value)}
            />
          </label>
          <label className="grid min-w-0 gap-1 text-xs font-semibold uppercase tracking-[0.08em] text-slate-500">
            Resultado
            <input
              className={fieldClassName}
              placeholder="Corregido, contenido, descartado"
              value={resolutionResult}
              onChange={(event) => setResolutionResult(event.target.value)}
            />
          </label>
          <label className="grid min-w-0 gap-1 text-xs font-semibold uppercase tracking-[0.08em] text-slate-500">
            Resuelto en
            <input
              className={fieldClassName}
              type="datetime-local"
              value={resolvedAt}
              onChange={(event) => setResolvedAt(event.target.value)}
            />
          </label>
          <label className="grid min-w-0 gap-1 text-xs font-semibold uppercase tracking-[0.08em] text-slate-500 md:col-span-4">
            Evidencia de resolucion
            <textarea
              className={textareaClassName}
              placeholder="Referencia de evidencia o comprobante si aplica"
              value={evidenceNote}
              onChange={(event) => setEvidenceNote(event.target.value)}
            />
          </label>
        </div>
      ) : null}

      {localError || errorMessage ? (
        <p className="mt-3 rounded-[16px] border border-rose-200 bg-[var(--ui-color-danger-soft)] px-3 py-2 text-sm font-semibold text-[var(--ui-color-danger)]">
          {localError ?? errorMessage}
        </p>
      ) : null}

      <div className="mt-4 flex min-w-0 flex-wrap items-center justify-between gap-3 border-t border-[var(--ui-color-border)] pt-3">
        <p className="min-w-0 text-sm leading-5 text-slate-600">
          Las incidencias se guardan en backend con trazabilidad; no se editan documentos fuente ni
          se requiere aprobacion de supervisor.
        </p>
        <button
          className="shrink-0 rounded-2xl bg-[var(--ui-color-primary)] px-4 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-[var(--ui-color-primary-strong)] disabled:cursor-not-allowed disabled:bg-slate-300 disabled:text-slate-600"
          disabled={isSubmitting}
          type="button"
          onClick={
            mode === "create" ? handleCreate : mode === "followUp" ? handleFollowUp : handleResolve
          }
        >
          {mode === "create"
            ? "Guardar incidencia"
            : mode === "followUp"
              ? "Guardar seguimiento"
              : "Resolver incidencia"}
        </button>
      </div>
    </section>
  );
}
