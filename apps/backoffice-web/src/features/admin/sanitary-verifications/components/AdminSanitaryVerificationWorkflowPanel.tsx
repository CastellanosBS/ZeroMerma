import { useMemo, useState } from "react";

import type {
  AdminSanitaryChecklistPayload,
  AdminSanitaryCompletePayload,
  AdminSanitaryCreatePayload,
  AdminSanitaryFilterOptions,
  AdminSanitaryItemResult,
  AdminSanitaryRiskLevel,
  AdminSanitaryTemplate,
  AdminSanitaryVerificationDetail,
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

function checklistFromTemplate(template: AdminSanitaryTemplate): AdminSanitaryChecklistPayload[] {
  return template.items.map((item) => ({
    displayOrder: item.displayOrder,
    evidenceRequiredOnFailure: item.evidenceRequiredOnFailure,
    expectedStandard: item.expectedStandard,
    id: null,
    isRequired: item.isRequired,
    label: item.label,
    notes: null,
    result: "PENDING",
    riskLevel: item.riskLevel,
  }));
}

function checklistFromDetail(detail: AdminSanitaryVerificationDetail) {
  return detail.checklistResults.map((item) => ({
    ...item,
    result: item.result === "PENDING" ? "PASSED" : item.result,
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

interface AdminSanitaryVerificationWorkflowPanelProps {
  detail: AdminSanitaryVerificationDetail | null;
  errorMessage?: string | null;
  isSubmitting?: boolean;
  mode: "create" | "execute";
  options: AdminSanitaryFilterOptions;
  templates: AdminSanitaryTemplate[];
  onCancel: () => void;
  onComplete: (payload: AdminSanitaryCompletePayload) => void;
  onCreate: (payload: AdminSanitaryCreatePayload) => void;
}

export function AdminSanitaryVerificationWorkflowPanel({
  detail,
  errorMessage,
  isSubmitting = false,
  mode,
  onCancel,
  onComplete,
  onCreate,
  options,
  templates,
}: AdminSanitaryVerificationWorkflowPanelProps) {
  const firstTemplate = templates[0] ?? null;
  const [branchId, setBranchId] = useState("");
  const [inspectorUserId, setInspectorUserId] = useState("");
  const [templateId, setTemplateId] = useState(firstTemplate?.id ?? "");
  const [templateName, setTemplateName] = useState(firstTemplate?.name ?? "");
  const [areaName, setAreaName] = useState("");
  const [areaType, setAreaType] = useState(firstTemplate?.areaType ?? "OTHER");
  const [equipmentName, setEquipmentName] = useState("");
  const [processName, setProcessName] = useState("");
  const [processType, setProcessType] = useState(firstTemplate?.processType ?? "OTHER");
  const [riskLevel, setRiskLevel] = useState<AdminSanitaryRiskLevel>(
    firstTemplate?.riskLevel ?? "MEDIUM",
  );
  const [scheduledAt, setScheduledAt] = useState(nowLocalInputValue());
  const [completedAt, setCompletedAt] = useState(nowLocalInputValue());
  const [notes, setNotes] = useState("");
  const [findingsNotes, setFindingsNotes] = useState("");
  const [evidenceNote, setEvidenceNote] = useState("");
  const [completeImmediately, setCompleteImmediately] = useState(mode === "execute");
  const [checklistResults, setChecklistResults] = useState<AdminSanitaryChecklistPayload[]>(
    mode === "execute" && detail
      ? checklistFromDetail(detail)
      : firstTemplate
        ? checklistFromTemplate(firstTemplate)
        : [
            {
              displayOrder: 1,
              evidenceRequiredOnFailure: false,
              expectedStandard: "Cumple criterio sanitario definido.",
              id: null,
              isRequired: true,
              label: "Punto sanitario verificado",
              notes: null,
              result: "PENDING",
              riskLevel: "MEDIUM",
            },
          ],
  );
  const [localError, setLocalError] = useState<string | null>(null);

  const selectedTemplate = useMemo(
    () => templates.find((template) => template.id === templateId) ?? null,
    [templateId, templates],
  );

  function handleTemplateChange(value: string) {
    setTemplateId(value);
    const template = templates.find((candidate) => candidate.id === value) ?? null;
    if (!template) {
      return;
    }
    setTemplateName(template.name);
    setAreaType(template.areaType);
    setProcessType(template.processType);
    setRiskLevel(template.riskLevel);
    setChecklistResults(checklistFromTemplate(template));
  }

  function patchChecklistItem(index: number, patch: Partial<AdminSanitaryChecklistPayload>) {
    setChecklistResults((current) =>
      current.map((item, itemIndex) => (itemIndex === index ? { ...item, ...patch } : item)),
    );
  }

  function addChecklistItem() {
    setChecklistResults((current) => [
      ...current,
      {
        displayOrder: current.length + 1,
        evidenceRequiredOnFailure: false,
        expectedStandard: "",
        id: null,
        isRequired: true,
        label: "",
        notes: null,
        result: "PENDING",
        riskLevel: "MEDIUM",
      },
    ]);
  }

  function validateChecklistForCompletion() {
    return checklistResults.every((item) => !item.isRequired || item.result !== "PENDING");
  }

  function hasFailedRequiredWithoutNotes() {
    return checklistResults.some(
      (item) => item.isRequired && item.result === "FAILED" && !item.notes?.trim(),
    );
  }

  function requiresEvidenceNote() {
    return checklistResults.some(
      (item) =>
        item.result === "FAILED" &&
        item.evidenceRequiredOnFailure &&
        (riskLevel === "HIGH" || riskLevel === "CRITICAL" || item.riskLevel === "CRITICAL"),
    );
  }

  function normalizeChecklistResult(item: AdminSanitaryChecklistPayload) {
    return {
      ...item,
      expectedStandard: item.expectedStandard?.trim() || null,
      label: item.label.trim(),
      notes: item.notes?.trim() || null,
    };
  }

  function handleSubmitCreate() {
    setLocalError(null);
    if (!branchId) {
      setLocalError("Selecciona una sucursal.");
      return;
    }
    if (!inspectorUserId) {
      setLocalError("Selecciona un inspector.");
      return;
    }
    if (!areaName.trim()) {
      setLocalError("Captura una zona o area.");
      return;
    }
    if (!templateId && !templateName.trim()) {
      setLocalError("Selecciona plantilla o captura un checklist manual.");
      return;
    }
    if (checklistResults.length === 0 || checklistResults.some((item) => !item.label.trim())) {
      setLocalError("La verificacion requiere checklist con etiquetas validas.");
      return;
    }
    if (completeImmediately && !validateChecklistForCompletion()) {
      setLocalError("Responde todos los puntos requeridos antes de completar la verificacion.");
      return;
    }
    if (completeImmediately && hasFailedRequiredWithoutNotes()) {
      setLocalError("Los puntos requeridos fallidos necesitan notas.");
      return;
    }
    if (
      completeImmediately &&
      checklistResults.some((item) => item.result === "FAILED") &&
      !findingsNotes.trim()
    ) {
      setLocalError("Agrega hallazgos para completar una verificacion fallida.");
      return;
    }
    if (completeImmediately && requiresEvidenceNote() && !evidenceNote.trim()) {
      setLocalError("Las fallas de alto riesgo requieren nota de evidencia.");
      return;
    }

    onCreate({
      areaName: areaName.trim(),
      areaType,
      branchId,
      checklistResults: checklistResults.map(normalizeChecklistResult),
      completeImmediately,
      completedAt: completeImmediately ? localInputToIso(completedAt) : null,
      equipmentName: equipmentName.trim() || null,
      evidenceNote: evidenceNote.trim() || null,
      findingsNotes: findingsNotes.trim() || null,
      inspectorUserId,
      notes: notes.trim() || null,
      processName: processName.trim() || null,
      processType,
      riskLevel,
      scheduledAt: localInputToIso(scheduledAt),
      templateId: templateId || null,
      templateName: templateId ? null : templateName.trim(),
    });
  }

  function handleSubmitComplete() {
    setLocalError(null);
    if (!detail) {
      setLocalError("Selecciona una verificacion para ejecutarla.");
      return;
    }
    if (!validateChecklistForCompletion()) {
      setLocalError("Responde todos los puntos requeridos antes de completar la verificacion.");
      return;
    }
    if (hasFailedRequiredWithoutNotes()) {
      setLocalError("Los puntos requeridos fallidos necesitan notas.");
      return;
    }
    if (checklistResults.some((item) => item.result === "FAILED") && !findingsNotes.trim()) {
      setLocalError("Agrega hallazgos para completar una verificacion fallida.");
      return;
    }
    if (requiresEvidenceNote() && !evidenceNote.trim() && !detail.evidence.evidenceNote) {
      setLocalError("Las fallas de alto riesgo requieren nota de evidencia.");
      return;
    }
    onComplete({
      checklistResults: checklistResults.map(normalizeChecklistResult),
      completedAt: localInputToIso(completedAt),
      evidenceNote: evidenceNote.trim() || null,
      findingsNotes: findingsNotes.trim() || null,
      notes: notes.trim() || null,
    });
  }

  const title =
    mode === "create" ? "Nueva verificacion" : `Ejecutar ${detail?.overview.folio ?? ""}`;
  const description =
    mode === "create"
      ? "Crea una verificacion pendiente o registra una inspeccion inmediata con checklist."
      : "Captura resultados pass/fail sin editar documentos sanitarios cerrados.";

  return (
    <section className="rounded-[20px] border border-[var(--ui-color-border)] bg-slate-50/80 p-4">
      <div className="flex min-w-0 flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">
            Control sanitario auditado
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
            Inspector
            <select
              className={fieldClassName}
              value={inspectorUserId}
              onChange={(event) => setInspectorUserId(event.target.value)}
            >
              {selectOptions(options.inspectors)}
            </select>
          </label>
          <label className="grid min-w-0 gap-1 text-xs font-semibold uppercase tracking-[0.08em] text-slate-500">
            Plantilla
            <select
              className={fieldClassName}
              value={templateId}
              onChange={(event) => handleTemplateChange(event.target.value)}
            >
              {selectOptions(
                templates.map((template) => ({ id: template.id, label: template.name })),
                "Manual",
              )}
            </select>
          </label>
          <label className="grid min-w-0 gap-1 text-xs font-semibold uppercase tracking-[0.08em] text-slate-500">
            Checklist manual
            <input
              className={fieldClassName}
              disabled={Boolean(templateId)}
              placeholder="Revision sanitaria"
              value={templateName}
              onChange={(event) => setTemplateName(event.target.value)}
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
            Tipo proceso
            <select
              className={fieldClassName}
              value={processType}
              onChange={(event) => setProcessType(event.target.value)}
            >
              {selectOptions(options.processTypes)}
            </select>
          </label>
          <label className="grid min-w-0 gap-1 text-xs font-semibold uppercase tracking-[0.08em] text-slate-500">
            Riesgo
            <select
              className={fieldClassName}
              value={riskLevel}
              onChange={(event) => setRiskLevel(event.target.value as AdminSanitaryRiskLevel)}
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
            Realizada
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
          No hay plantillas de verificacion sanitaria configuradas.
        </p>
      ) : null}

      <div className="mt-4 rounded-[18px] border border-[var(--ui-color-border)] bg-white p-3">
        <div className="flex min-w-0 items-center justify-between gap-3">
          <div className="min-w-0">
            <h4 className="truncate text-sm font-semibold text-slate-950">Checklist sanitario</h4>
            <p className="truncate text-xs text-slate-500">
              {selectedTemplate
                ? `${selectedTemplate.items.length} puntos desde plantilla`
                : "Checklist manual persistido con la verificacion"}
            </p>
          </div>
          {mode === "create" && !templateId ? (
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
          {checklistResults.map((item, index) => (
            <article
              className="grid min-w-0 gap-2 rounded-[14px] bg-slate-50 p-2 xl:grid-cols-[minmax(0,1fr)_10rem_8rem_minmax(0,1fr)]"
              key={`${item.label}-${index}`}
            >
              <input
                className={fieldClassName}
                disabled={Boolean(templateId)}
                placeholder="Punto sanitario"
                value={item.label}
                onChange={(event) => patchChecklistItem(index, { label: event.target.value })}
              />
              <select
                aria-label={`Resultado ${item.label}`}
                className={fieldClassName}
                value={item.result}
                onChange={(event) =>
                  patchChecklistItem(index, {
                    result: event.target.value as AdminSanitaryItemResult,
                  })
                }
              >
                <option value="PENDING">Pendiente</option>
                <option value="PASSED">Cumple</option>
                <option value="FAILED">No cumple</option>
                <option value="NOT_APPLICABLE">No aplica</option>
              </select>
              <label className="flex items-center gap-2 text-xs font-semibold text-slate-600">
                <input
                  checked={item.isRequired}
                  disabled={Boolean(templateId)}
                  type="checkbox"
                  onChange={(event) =>
                    patchChecklistItem(index, { isRequired: event.target.checked })
                  }
                />
                Requerido
              </label>
              <input
                className={fieldClassName}
                placeholder="Nota o hallazgo por punto"
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
          Hallazgos
          <textarea
            className={textareaClassName}
            placeholder="Hallazgos, no conformidades, seguimiento"
            value={findingsNotes}
            onChange={(event) => setFindingsNotes(event.target.value)}
          />
        </label>
        <label className="grid min-w-0 gap-1 text-xs font-semibold uppercase tracking-[0.08em] text-slate-500">
          Evidencia
          <textarea
            className={textareaClassName}
            placeholder="Referencia de foto, acta o evidencia"
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
          Las verificaciones completadas quedan de solo lectura; fallas e incidencias deben quedar
          trazadas por backend.
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
            : "Completar verificacion"}
        </button>
      </div>
    </section>
  );
}
