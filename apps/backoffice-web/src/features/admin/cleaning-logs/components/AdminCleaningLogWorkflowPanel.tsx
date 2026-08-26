import { useMemo, useState } from "react";

import type {
  AdminCleaningChecklistPayload,
  AdminCleaningCompletePayload,
  AdminCleaningCreatePayload,
  AdminCleaningFilterOptions,
  AdminCleaningLogDetail,
  AdminCleaningTemplate,
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

function localInputToIso(value: string) {
  return new Date(value).toISOString();
}

function checklistFromTemplate(template: AdminCleaningTemplate): AdminCleaningChecklistPayload[] {
  return template.items.map((item) => ({
    id: null,
    isCompleted: false,
    isRequired: item.isRequired,
    label: item.label,
    notes: null,
  }));
}

function checklistFromDetail(detail: AdminCleaningLogDetail): AdminCleaningChecklistPayload[] {
  return detail.checklist.map((item) => ({
    id: item.id,
    isCompleted: item.isCompleted,
    isRequired: item.isRequired,
    label: item.label,
    notes: item.notes,
  }));
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

interface AdminCleaningLogWorkflowPanelProps {
  detail: AdminCleaningLogDetail | null;
  errorMessage?: string | null;
  isSubmitting?: boolean;
  mode: "create" | "complete";
  options: AdminCleaningFilterOptions;
  templates: AdminCleaningTemplate[];
  onCancel: () => void;
  onComplete: (payload: AdminCleaningCompletePayload) => void;
  onCreate: (payload: AdminCleaningCreatePayload) => void;
}

export function AdminCleaningLogWorkflowPanel({
  detail,
  errorMessage,
  isSubmitting = false,
  mode,
  onCancel,
  onComplete,
  onCreate,
  options,
  templates,
}: AdminCleaningLogWorkflowPanelProps) {
  const firstTemplate = templates[0] ?? null;
  const [branchId, setBranchId] = useState("");
  const [responsibleUserId, setResponsibleUserId] = useState("");
  const [taskTemplateId, setTaskTemplateId] = useState(firstTemplate?.id ?? "");
  const [taskName, setTaskName] = useState(firstTemplate?.name ?? "");
  const [areaName, setAreaName] = useState("");
  const [areaType, setAreaType] = useState(firstTemplate?.areaType ?? "OTHER");
  const [equipmentName, setEquipmentName] = useState("");
  const [shiftCode, setShiftCode] = useState("MORNING");
  const [cleaningType, setCleaningType] = useState(firstTemplate?.cleaningType ?? "ROUTINE");
  const [riskLevel, setRiskLevel] = useState<"LOW" | "MEDIUM" | "HIGH" | "CRITICAL">(
    firstTemplate?.riskLevel ?? "MEDIUM",
  );
  const [scheduledAt, setScheduledAt] = useState(nowLocalInputValue());
  const [completedAt, setCompletedAt] = useState(nowLocalInputValue());
  const [notes, setNotes] = useState("");
  const [issueNotes, setIssueNotes] = useState("");
  const [evidenceNote, setEvidenceNote] = useState("");
  const [completeImmediately, setCompleteImmediately] = useState(mode === "complete");
  const [checklistItems, setChecklistItems] = useState<AdminCleaningChecklistPayload[]>(
    mode === "complete" && detail
      ? checklistFromDetail(detail)
      : firstTemplate
        ? checklistFromTemplate(firstTemplate)
        : [
            {
              id: null,
              isCompleted: false,
              isRequired: true,
              label: "Limpieza general completada",
              notes: null,
            },
          ],
  );
  const [localError, setLocalError] = useState<string | null>(null);

  const selectedTemplate = useMemo(
    () => templates.find((template) => template.id === taskTemplateId) ?? null,
    [taskTemplateId, templates],
  );

  function handleTemplateChange(value: string) {
    setTaskTemplateId(value);
    const template = templates.find((candidate) => candidate.id === value) ?? null;
    if (!template) {
      return;
    }
    setTaskName(template.name);
    setAreaType(template.areaType);
    setCleaningType(template.cleaningType);
    setRiskLevel(template.riskLevel);
    setChecklistItems(checklistFromTemplate(template));
  }

  function patchChecklistItem(index: number, patch: Partial<AdminCleaningChecklistPayload>) {
    setChecklistItems((current) =>
      current.map((item, itemIndex) => (itemIndex === index ? { ...item, ...patch } : item)),
    );
  }

  function addChecklistItem() {
    setChecklistItems((current) => [
      ...current,
      {
        id: null,
        isCompleted: false,
        isRequired: true,
        label: "",
        notes: null,
      },
    ]);
  }

  function validateChecklistForCompletion() {
    return checklistItems.every((item) => !item.isRequired || item.isCompleted);
  }

  function handleSubmitCreate() {
    setLocalError(null);
    if (!branchId) {
      setLocalError("Selecciona una sucursal.");
      return;
    }
    if (!responsibleUserId) {
      setLocalError("Selecciona un responsable.");
      return;
    }
    if (!areaName.trim()) {
      setLocalError("Captura una zona o area.");
      return;
    }
    if (!taskTemplateId && !taskName.trim()) {
      setLocalError("Selecciona plantilla o captura una tarea manual.");
      return;
    }
    if (checklistItems.length === 0 || checklistItems.some((item) => !item.label.trim())) {
      setLocalError("La bitacora requiere checklist con etiquetas validas.");
      return;
    }
    if (completeImmediately && !validateChecklistForCompletion()) {
      setLocalError("Completa todos los puntos requeridos antes de cerrar la bitacora.");
      return;
    }
    if (
      completeImmediately &&
      (riskLevel === "HIGH" || riskLevel === "CRITICAL") &&
      !evidenceNote.trim()
    ) {
      setLocalError("Las bitacoras de alto riesgo requieren nota de evidencia.");
      return;
    }

    onCreate({
      areaName: areaName.trim(),
      areaType,
      branchId,
      checklistItems,
      cleaningType,
      completeImmediately,
      completedAt: completeImmediately ? localInputToIso(completedAt) : null,
      equipmentName: equipmentName.trim() || null,
      evidenceNote: evidenceNote.trim() || null,
      issueNotes: issueNotes.trim() || null,
      notes: notes.trim() || null,
      responsibleUserId,
      riskLevel,
      scheduledAt: localInputToIso(scheduledAt),
      shiftCode,
      taskName: taskTemplateId ? null : taskName.trim(),
      taskTemplateId: taskTemplateId || null,
    });
  }

  function handleSubmitComplete() {
    setLocalError(null);
    if (!detail) {
      setLocalError("Selecciona una bitacora para completarla.");
      return;
    }
    if (!validateChecklistForCompletion()) {
      setLocalError("Completa todos los puntos requeridos antes de cerrar la bitacora.");
      return;
    }
    if (
      (detail.taskTemplate.riskLevel === "HIGH" || detail.taskTemplate.riskLevel === "CRITICAL") &&
      !evidenceNote.trim() &&
      !detail.evidence.evidenceNote
    ) {
      setLocalError("Las bitacoras de alto riesgo requieren nota de evidencia.");
      return;
    }
    onComplete({
      checklistItems,
      completedAt: localInputToIso(completedAt),
      evidenceNote: evidenceNote.trim() || null,
      issueNotes: issueNotes.trim() || null,
      notes: notes.trim() || null,
    });
  }

  const title = mode === "create" ? "Nueva bitacora" : `Completar ${detail?.overview.folio ?? ""}`;
  const description =
    mode === "create"
      ? "Crea una bitacora pendiente o registra limpieza inmediata con checklist."
      : "Registra cierre de limpieza sin modificar historicos cerrados.";

  return (
    <section className="rounded-[20px] border border-[var(--ui-color-border)] bg-slate-50/80 p-4">
      <div className="flex min-w-0 flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">
            Captura auditada
          </p>
          <h3 className="mt-1 text-base font-semibold text-slate-950">{title}</h3>
          <p className="mt-1 text-sm leading-5 text-slate-600">{description}</p>
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
            Responsable
            <select
              className={fieldClassName}
              value={responsibleUserId}
              onChange={(event) => setResponsibleUserId(event.target.value)}
            >
              {selectOptions(options.responsibleUsers)}
            </select>
          </label>
          <label className="grid min-w-0 gap-1 text-xs font-semibold uppercase tracking-[0.08em] text-slate-500">
            Plantilla
            <select
              className={fieldClassName}
              value={taskTemplateId}
              onChange={(event) => handleTemplateChange(event.target.value)}
            >
              {selectOptions(
                templates.map((template) => ({ id: template.id, label: template.name })),
                "Manual",
              )}
            </select>
          </label>
          <label className="grid min-w-0 gap-1 text-xs font-semibold uppercase tracking-[0.08em] text-slate-500">
            Tarea manual
            <input
              className={fieldClassName}
              disabled={Boolean(taskTemplateId)}
              placeholder="Limpieza de vitrina"
              value={taskName}
              onChange={(event) => setTaskName(event.target.value)}
            />
          </label>
          <label className="grid min-w-0 gap-1 text-xs font-semibold uppercase tracking-[0.08em] text-slate-500">
            Zona / area
            <input
              className={fieldClassName}
              placeholder="Cocina, mostrador"
              value={areaName}
              onChange={(event) => setAreaName(event.target.value)}
            />
          </label>
          <label className="grid min-w-0 gap-1 text-xs font-semibold uppercase tracking-[0.08em] text-slate-500">
            Tipo area
            <select
              className={fieldClassName}
              value={areaType}
              onChange={(event) => setAreaType(event.target.value)}
            >
              {selectOptions(options.areaTypes)}
            </select>
          </label>
          <label className="grid min-w-0 gap-1 text-xs font-semibold uppercase tracking-[0.08em] text-slate-500">
            Equipo
            <input
              className={fieldClassName}
              placeholder="Horno, mesa fria"
              value={equipmentName}
              onChange={(event) => setEquipmentName(event.target.value)}
            />
          </label>
          <label className="grid min-w-0 gap-1 text-xs font-semibold uppercase tracking-[0.08em] text-slate-500">
            Turno
            <select
              className={fieldClassName}
              value={shiftCode}
              onChange={(event) => setShiftCode(event.target.value)}
            >
              {selectOptions(options.shifts)}
            </select>
          </label>
          <label className="grid min-w-0 gap-1 text-xs font-semibold uppercase tracking-[0.08em] text-slate-500">
            Tipo limpieza
            <select
              className={fieldClassName}
              value={cleaningType}
              onChange={(event) => setCleaningType(event.target.value)}
            >
              {selectOptions(options.cleaningTypes)}
            </select>
          </label>
          <label className="grid min-w-0 gap-1 text-xs font-semibold uppercase tracking-[0.08em] text-slate-500">
            Riesgo
            <select
              className={fieldClassName}
              value={riskLevel}
              onChange={(event) =>
                setRiskLevel(event.target.value as "LOW" | "MEDIUM" | "HIGH" | "CRITICAL")
              }
            >
              {selectOptions(options.riskLevels)}
            </select>
          </label>
          <label className="grid min-w-0 gap-1 text-xs font-semibold uppercase tracking-[0.08em] text-slate-500">
            Programada
            <input
              className={fieldClassName}
              type="datetime-local"
              value={scheduledAt}
              onChange={(event) => setScheduledAt(event.target.value)}
            />
          </label>
          <label className="grid min-w-0 gap-1 text-xs font-semibold uppercase tracking-[0.08em] text-slate-500">
            Completada
            <input
              className={fieldClassName}
              disabled={!completeImmediately}
              type="datetime-local"
              value={completedAt}
              onChange={(event) => setCompletedAt(event.target.value)}
            />
          </label>
        </div>
      ) : null}

      {templates.length === 0 && mode === "create" ? (
        <p className="mt-3 rounded-[16px] border border-dashed border-[var(--ui-color-border)] bg-white px-3 py-3 text-sm text-slate-600">
          No hay plantillas de limpieza configuradas.
        </p>
      ) : null}

      <div className="mt-4 rounded-[18px] border border-[var(--ui-color-border)] bg-white p-3">
        <div className="flex min-w-0 items-center justify-between gap-3">
          <div className="min-w-0">
            <h4 className="truncate text-sm font-semibold text-slate-950">Checklist</h4>
            <p className="truncate text-xs text-slate-500">
              {selectedTemplate
                ? `${selectedTemplate.items.length} puntos desde plantilla`
                : "Checklist manual persistido con la bitacora"}
            </p>
          </div>
          {mode === "create" && !taskTemplateId ? (
            <button
              className="rounded-full border border-[var(--ui-color-border)] bg-white px-3 py-1.5 text-xs font-semibold text-slate-700"
              type="button"
              onClick={addChecklistItem}
            >
              Agregar punto
            </button>
          ) : null}
        </div>
        <div className="mt-3 grid gap-2">
          {checklistItems.map((item, index) => (
            <article
              className="grid min-w-0 gap-2 rounded-[14px] bg-slate-50 p-2 sm:grid-cols-[auto_minmax(0,1fr)_auto_minmax(0,1fr)]"
              key={`${item.label}-${index}`}
            >
              <input
                aria-label={`Completar ${item.label}`}
                checked={item.isCompleted}
                className="mt-2 h-4 w-4"
                type="checkbox"
                onChange={(event) =>
                  patchChecklistItem(index, { isCompleted: event.target.checked })
                }
              />
              <input
                className={fieldClassName}
                disabled={Boolean(taskTemplateId)}
                placeholder="Punto de limpieza"
                value={item.label}
                onChange={(event) => patchChecklistItem(index, { label: event.target.value })}
              />
              <label className="flex items-center gap-2 text-xs font-semibold text-slate-600">
                <input
                  checked={item.isRequired}
                  disabled={Boolean(taskTemplateId)}
                  type="checkbox"
                  onChange={(event) =>
                    patchChecklistItem(index, { isRequired: event.target.checked })
                  }
                />
                Requerido
              </label>
              <input
                className={fieldClassName}
                placeholder="Nota por punto"
                value={item.notes ?? ""}
                onChange={(event) =>
                  patchChecklistItem(index, { notes: event.target.value || null })
                }
              />
            </article>
          ))}
        </div>
      </div>

      <div className="mt-4 grid min-w-0 gap-3 md:grid-cols-3">
        <label className="grid min-w-0 gap-1 text-xs font-semibold uppercase tracking-[0.08em] text-slate-500">
          Notas
          <textarea
            className={textareaClassName}
            placeholder="Notas generales"
            value={notes}
            onChange={(event) => setNotes(event.target.value)}
          />
        </label>
        <label className="grid min-w-0 gap-1 text-xs font-semibold uppercase tracking-[0.08em] text-slate-500">
          Observaciones
          <textarea
            className={textareaClassName}
            placeholder="Hallazgos, puntos incompletos"
            value={issueNotes}
            onChange={(event) => setIssueNotes(event.target.value)}
          />
        </label>
        <label className="grid min-w-0 gap-1 text-xs font-semibold uppercase tracking-[0.08em] text-slate-500">
          Evidencia
          <textarea
            className={textareaClassName}
            placeholder="Referencia de foto, recibo o evidencia"
            value={evidenceNote}
            onChange={(event) => setEvidenceNote(event.target.value)}
          />
        </label>
      </div>

      {mode === "create" ? (
        <label className="mt-3 flex min-w-0 items-center gap-2 text-sm font-semibold text-slate-700">
          <input
            checked={completeImmediately}
            type="checkbox"
            onChange={(event) => setCompleteImmediately(event.target.checked)}
          />
          Crear y completar inmediatamente
        </label>
      ) : null}

      {localError || errorMessage ? (
        <p className="mt-3 rounded-[16px] border border-rose-200 bg-[var(--ui-color-danger-soft)] px-3 py-2 text-sm font-semibold text-[var(--ui-color-danger)]">
          {localError ?? errorMessage}
        </p>
      ) : null}

      <div className="mt-4 flex min-w-0 flex-wrap items-center justify-between gap-3 border-t border-[var(--ui-color-border)] pt-3">
        <p className="min-w-0 text-sm leading-5 text-slate-600">
          Las bitacoras completadas quedan de solo lectura; las correcciones deben quedar trazadas.
        </p>
        <button
          className="shrink-0 rounded-2xl bg-[var(--ui-color-primary)] px-4 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-[var(--ui-color-primary-strong)] disabled:cursor-not-allowed disabled:bg-slate-300 disabled:text-slate-600"
          disabled={isSubmitting}
          type="button"
          onClick={mode === "create" ? handleSubmitCreate : handleSubmitComplete}
        >
          {mode === "create"
            ? completeImmediately
              ? "Guardar y completar"
              : "Guardar pendiente"
            : "Completar bitacora"}
        </button>
      </div>
    </section>
  );
}
