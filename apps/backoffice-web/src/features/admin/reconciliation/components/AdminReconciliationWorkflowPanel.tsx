import { AdminActionButton } from "../../components/AdminActionButton";
import type { FormEvent } from "react";
import { useEffect, useState } from "react";

import type {
  AdminPendingDiscrepancyItem,
  AdminReconciliationFilterOption,
  AdminReconciliationListItem,
} from "../types";

type WorkflowMode = "create" | "resolve";

interface AdminReconciliationWorkflowPanelProps {
  errorMessage?: string | null;
  isSubmitting?: boolean;
  mode: WorkflowMode;
  onCancel: () => void;
  onCreate: (payload: {
    evidenceNote: string | null;
    finalStatus: string;
    notes: string | null;
    reasonCode: string;
    sourceDocumentId: string;
    sourceType: string;
  }) => void;
  onResolve: (payload: {
    evidenceNote: string | null;
    notes: string | null;
    reasonCode: string;
  }) => void;
  reasonOptions: AdminReconciliationFilterOption[];
  reconciliation?: AdminReconciliationListItem | null;
  source?: AdminPendingDiscrepancyItem | null;
}

function formatMoney(value: string | null | undefined): string {
  if (!value) {
    return "N/A";
  }
  const numericValue = Number(value);
  if (!Number.isFinite(numericValue)) {
    return `${value} MXN`;
  }
  return new Intl.NumberFormat("es-MX", { currency: "MXN", style: "currency" }).format(
    numericValue,
  );
}

function reasonRequiresNotes(reasonCode: string): boolean {
  return reasonCode === "OTHER";
}

export function AdminReconciliationWorkflowPanel({
  errorMessage,
  isSubmitting = false,
  mode,
  onCancel,
  onCreate,
  onResolve,
  reasonOptions,
  reconciliation,
  source,
}: AdminReconciliationWorkflowPanelProps) {
  const [sourceDocumentId, setSourceDocumentId] = useState(
    source?.sourceDocumentId ?? reconciliation?.sourceDocumentId ?? "",
  );
  const [sourceType, setSourceType] = useState(
    source?.sourceType ?? reconciliation?.sourceType ?? "CASH_CUT",
  );
  const [finalStatus, setFinalStatus] = useState("RECONCILED");
  const [reasonCode, setReasonCode] = useState(reasonOptions[0]?.id ?? "COUNTING_ERROR");
  const [notes, setNotes] = useState("");
  const [evidenceNote, setEvidenceNote] = useState("");
  const [validationMessage, setValidationMessage] = useState<string | null>(null);

  useEffect(() => {
    setSourceDocumentId(source?.sourceDocumentId ?? reconciliation?.sourceDocumentId ?? "");
    setSourceType(source?.sourceType ?? reconciliation?.sourceType ?? "CASH_CUT");
  }, [reconciliation?.sourceDocumentId, reconciliation?.sourceType, source]);

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (mode === "create" && !sourceDocumentId.trim()) {
      setValidationMessage("Selecciona un documento origen para conciliar.");
      return;
    }
    if (!reasonCode) {
      setValidationMessage("Selecciona un motivo de conciliacion.");
      return;
    }
    if (reasonRequiresNotes(reasonCode) && !notes.trim()) {
      setValidationMessage("El motivo OTRO requiere notas.");
      return;
    }

    setValidationMessage(null);

    if (mode === "create") {
      onCreate({
        evidenceNote: evidenceNote.trim() || null,
        finalStatus,
        notes: notes.trim() || null,
        reasonCode,
        sourceDocumentId: sourceDocumentId.trim(),
        sourceType,
      });
      return;
    }

    onResolve({
      evidenceNote: evidenceNote.trim() || null,
      notes: notes.trim() || null,
      reasonCode,
    });
  }

  const sourceSummary = source ?? reconciliation;

  return (
    <section className="rounded-[20px] border border-[var(--ui-color-border)] bg-white p-3 shadow-[var(--ui-shadow-subtle)]">
      <div className="flex min-w-0 items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">
            {mode === "create" ? "Nueva conciliacion" : "Resolver conciliacion"}
          </p>
          <h3 className="mt-1 truncate text-base font-semibold text-slate-950">
            {sourceSummary?.sourceReference ?? reconciliation?.folio ?? "Documento origen"}
          </h3>
        </div>
        <button
          className="rounded-full border border-[var(--ui-color-border)] bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 transition hover:border-[var(--ui-color-info)] hover:text-[var(--ui-color-info)]"
          type="button"
          onClick={onCancel}
        >
          Cerrar
        </button>
      </div>

      {sourceSummary ? (
        <div className="mt-3 grid gap-2 rounded-[16px] border border-[var(--ui-color-border)] bg-slate-50 p-3 text-sm sm:grid-cols-4">
          <span className="min-w-0">
            <span className="block text-xs text-slate-500">Esperado</span>
            <span className="block truncate font-semibold text-slate-950">
              {formatMoney(sourceSummary.expectedAmount)}
            </span>
          </span>
          <span className="min-w-0">
            <span className="block text-xs text-slate-500">Reportado</span>
            <span className="block truncate font-semibold text-slate-950">
              {formatMoney(sourceSummary.actualAmount)}
            </span>
          </span>
          <span className="min-w-0">
            <span className="block text-xs text-slate-500">Diferencia</span>
            <span className="block truncate font-semibold text-slate-950">
              {formatMoney(sourceSummary.differenceAmount)}
            </span>
          </span>
          <span className="min-w-0">
            <span className="block text-xs text-slate-500">Metodo</span>
            <span className="block truncate font-semibold text-slate-950">
              {sourceSummary.paymentMethod}
            </span>
          </span>
        </div>
      ) : null}

      <form className="mt-3 grid gap-3" onSubmit={handleSubmit}>
        {mode === "create" ? (
          <div className="grid gap-2 sm:grid-cols-[minmax(9rem,0.45fr)_minmax(12rem,1fr)_minmax(9rem,0.45fr)]">
            <select
              className="h-10 rounded-2xl border border-[var(--ui-color-border)] bg-white px-3 text-sm font-medium text-slate-700"
              value={sourceType}
              onChange={(event) => setSourceType(event.target.value)}
            >
              <option value="CASH_CUT">Corte de caja</option>
            </select>
            <input
              className="h-10 rounded-2xl border border-[var(--ui-color-border)] bg-white px-3 text-sm text-slate-800"
              placeholder="ID del documento origen"
              readOnly={Boolean(source)}
              value={sourceDocumentId}
              onChange={(event) => setSourceDocumentId(event.target.value)}
            />
            <select
              className="h-10 rounded-2xl border border-[var(--ui-color-border)] bg-white px-3 text-sm font-medium text-slate-700"
              value={finalStatus}
              onChange={(event) => setFinalStatus(event.target.value)}
            >
              <option value="RECONCILED">Conciliar ahora</option>
              <option value="IN_REVIEW">Guardar en revision</option>
              <option value="PENDING">Guardar pendiente</option>
            </select>
          </div>
        ) : null}

        <div className="grid gap-2 sm:grid-cols-[minmax(10rem,0.45fr)_minmax(0,1fr)]">
          <select
            className="h-10 rounded-2xl border border-[var(--ui-color-border)] bg-white px-3 text-sm font-medium text-slate-700"
            value={reasonCode}
            onChange={(event) => setReasonCode(event.target.value)}
          >
            {reasonOptions.map((option) => (
              <option key={option.id} value={option.id}>
                {option.label}
              </option>
            ))}
          </select>
          <input
            className="h-10 rounded-2xl border border-[var(--ui-color-border)] bg-white px-3 text-sm text-slate-800"
            placeholder="Nota de evidencia o referencia de soporte"
            value={evidenceNote}
            onChange={(event) => setEvidenceNote(event.target.value)}
          />
        </div>

        <textarea
          className="min-h-24 rounded-[18px] border border-[var(--ui-color-border)] bg-white px-3 py-2 text-sm text-slate-800"
          placeholder="Notas de conciliacion. Requeridas cuando el motivo es OTRO."
          value={notes}
          onChange={(event) => setNotes(event.target.value)}
        />

        {validationMessage || errorMessage ? (
          <p className="rounded-[16px] border border-rose-200 bg-[var(--ui-color-danger-soft)] px-3 py-2 text-sm font-semibold text-[var(--ui-color-danger)]">
            {validationMessage ?? errorMessage}
          </p>
        ) : null}

        <div className="flex min-w-0 justify-end gap-2">
          <button
            className="h-10 rounded-2xl border border-[var(--ui-color-border)] bg-white px-4 text-sm font-semibold text-slate-700"
            disabled={isSubmitting}
            type="button"
            onClick={onCancel}
          >
            Cancelar
          </button>
          <AdminActionButton
            capability="cash_finance.manage"
            branchIds={[]}
            className="h-10 rounded-2xl border border-[var(--ui-color-primary)] bg-[var(--ui-color-primary)] px-4 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-50"
            disabled={isSubmitting}
            type="submit"
          >
            {isSubmitting
              ? "Guardando"
              : mode === "create"
                ? "Confirmar conciliacion"
                : "Marcar como conciliada"}
          </AdminActionButton>
        </div>
      </form>
    </section>
  );
}
