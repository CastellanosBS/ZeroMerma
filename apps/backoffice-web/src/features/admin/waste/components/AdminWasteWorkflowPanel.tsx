import { useMemo, useState } from "react";

import type { AdminWasteCreatePayload, AdminWasteFilterOption, AdminWasteReason } from "../types";

interface AdminWasteWorkflowPanelProps {
  branchOptions: AdminWasteFilterOption[];
  errorMessage?: string | null;
  isSubmitting: boolean;
  locationOptions: AdminWasteFilterOption[];
  productOptions: AdminWasteFilterOption[];
  reasonOptions: AdminWasteReason[];
  onClose: () => void;
  onCreate: (payload: AdminWasteCreatePayload) => void;
}

export function AdminWasteWorkflowPanel({
  branchOptions,
  errorMessage,
  isSubmitting,
  locationOptions,
  productOptions,
  reasonOptions,
  onClose,
  onCreate,
}: AdminWasteWorkflowPanelProps) {
  const [branchId, setBranchId] = useState("");
  const [locationCode, setLocationCode] = useState("BACKROOM");
  const [notes, setNotes] = useState("");
  const [productId, setProductId] = useState("");
  const [quantity, setQuantity] = useState("");
  const [reasonCode, setReasonCode] = useState("");
  const [validationMessage, setValidationMessage] = useState<string | null>(null);

  const selectedReason = useMemo(
    () => reasonOptions.find((reason) => reason.code === reasonCode) ?? null,
    [reasonCode, reasonOptions],
  );
  const noteRequired = selectedReason?.requiresNote || selectedReason?.highImpactDefault;

  function handleSubmit() {
    if (!branchId) {
      setValidationMessage("Selecciona una sucursal.");
      return;
    }
    if (!productId) {
      setValidationMessage("Selecciona un producto.");
      return;
    }
    if (!reasonCode) {
      setValidationMessage("Selecciona un motivo.");
      return;
    }
    if (!quantity || Number(quantity) <= 0) {
      setValidationMessage("La cantidad debe ser mayor que cero.");
      return;
    }
    if (noteRequired && !notes.trim()) {
      setValidationMessage("Este motivo requiere nota operacional.");
      return;
    }

    setValidationMessage(null);
    onCreate({
      branchId,
      locationCode: locationCode as AdminWasteCreatePayload["locationCode"],
      notes: notes.trim() || null,
      productId,
      quantity,
      reasonCode,
    });
  }

  return (
    <section className="rounded-[20px] border border-[var(--ui-color-border)] bg-white p-4 shadow-[var(--ui-shadow-subtle)]">
      <div className="mb-3 flex items-start justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">Nueva merma</p>
          <h2 className="text-lg font-semibold text-slate-950">Confirmar baja de inventario</h2>
          <p className="text-sm text-slate-600">La merma se confirma en backend y crea movimiento auditable.</p>
        </div>
        <button className="rounded-full border border-slate-200 px-3 py-1.5 text-xs font-semibold text-slate-700" type="button" onClick={onClose}>
          Cerrar
        </button>
      </div>

      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-6">
        <label className="flex flex-col gap-1 xl:col-span-2">
          <span className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">Sucursal</span>
          <select className="rounded-xl border border-slate-200 px-3 py-2 text-sm" value={branchId} onChange={(event) => setBranchId(event.target.value)}>
            <option value="">Selecciona sucursal</option>
            {branchOptions.map((option) => (
              <option key={option.id} value={option.id}>
                {option.label}
              </option>
            ))}
          </select>
        </label>

        <label className="flex flex-col gap-1 xl:col-span-2">
          <span className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">Producto</span>
          <select className="rounded-xl border border-slate-200 px-3 py-2 text-sm" value={productId} onChange={(event) => setProductId(event.target.value)}>
            <option value="">Selecciona producto</option>
            {productOptions.map((option) => (
              <option key={option.id} value={option.id}>
                {option.label}
              </option>
            ))}
          </select>
        </label>

        <label className="flex flex-col gap-1">
          <span className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">Origen</span>
          <select className="rounded-xl border border-slate-200 px-3 py-2 text-sm" value={locationCode} onChange={(event) => setLocationCode(event.target.value)}>
            {locationOptions.map((option) => (
              <option key={option.id} value={option.id}>
                {option.label}
              </option>
            ))}
          </select>
        </label>

        <label className="flex flex-col gap-1">
          <span className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">Cantidad</span>
          <input className="rounded-xl border border-slate-200 px-3 py-2 text-sm" min="0" step="0.001" type="number" value={quantity} onChange={(event) => setQuantity(event.target.value)} />
        </label>

        <label className="flex flex-col gap-1 xl:col-span-2">
          <span className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">Motivo</span>
          <select className="rounded-xl border border-slate-200 px-3 py-2 text-sm" value={reasonCode} onChange={(event) => setReasonCode(event.target.value)}>
            <option value="">Selecciona motivo</option>
            {reasonOptions.map((reason) => (
              <option key={reason.code} value={reason.code}>
                {reason.label}
              </option>
            ))}
          </select>
        </label>

        <label className="flex flex-col gap-1 xl:col-span-4">
          <span className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">Notas</span>
          <input className="rounded-xl border border-slate-200 px-3 py-2 text-sm" placeholder={noteRequired ? "Nota requerida para este motivo" : "Notas operativas"} value={notes} onChange={(event) => setNotes(event.target.value)} />
        </label>
      </div>

      {selectedReason ? (
        <p className="mt-3 rounded-xl bg-slate-50 px-3 py-2 text-xs font-semibold text-slate-600">
          {selectedReason.requiresNote ? "Este motivo requiere nota. " : ""}
          {selectedReason.requiresEvidence ? "Requiere evidencia. " : "La evidencia adjunta aun no esta soportada por backend."}
        </p>
      ) : null}

      {validationMessage || errorMessage ? (
        <p className="mt-3 rounded-xl border border-rose-200 bg-[var(--ui-color-danger-soft)] px-3 py-2 text-sm font-semibold text-[var(--ui-color-danger)]">
          {validationMessage ?? errorMessage}
        </p>
      ) : null}

      <div className="mt-4 flex justify-end gap-2">
        <button className="rounded-xl border border-slate-200 px-4 py-2 text-sm font-semibold text-slate-700" disabled={isSubmitting} type="button" onClick={onClose}>
          Cancelar
        </button>
        <button className="rounded-xl bg-[var(--ui-color-primary)] px-4 py-2 text-sm font-semibold text-white disabled:opacity-60" disabled={isSubmitting} type="button" onClick={handleSubmit}>
          Confirmar merma
        </button>
      </div>
    </section>
  );
}
