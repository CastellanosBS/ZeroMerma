import { useMemo, useState } from "react";

import type {
  AdminDirectEntryPayload,
  AdminPurchaseCancelPayload,
  AdminPurchaseDetail,
  AdminPurchaseFilterOptions,
  AdminPurchasePayload,
  AdminPurchaseReceiptPayload,
} from "../types";

type WorkflowMode = "purchase" | "direct" | "receive" | "cancel";

const inputClassName =
  "h-9 w-full min-w-0 rounded-2xl border border-[var(--ui-color-border)] bg-white px-3 text-sm font-medium text-slate-950 outline-none transition placeholder:text-slate-400 focus:border-[var(--ui-color-info)] focus:ring-4 focus:ring-[var(--ui-color-ring)] disabled:cursor-not-allowed disabled:bg-slate-100 disabled:text-slate-500";

interface EditableLine {
  notes: string;
  productId: string;
  quantity: string;
  unitCost: string;
}

interface ReceiptLineState {
  discrepancyReason: string;
  notes: string;
  purchaseLineId: string;
  receivedQuantity: string;
  unitCost: string;
}

interface AdminPurchaseWorkflowPanelProps {
  errorMessage?: string | null;
  isSubmitting?: boolean;
  mode: WorkflowMode;
  onClose: () => void;
  onSubmitCancel: (payload: AdminPurchaseCancelPayload) => void;
  onSubmitDirectEntry: (payload: AdminDirectEntryPayload) => void;
  onSubmitPurchase: (payload: AdminPurchasePayload) => void;
  onSubmitReceipt: (payload: AdminPurchaseReceiptPayload) => void;
  options: AdminPurchaseFilterOptions;
  purchase?: AdminPurchaseDetail | null;
}

function newLine(): EditableLine {
  return {
    notes: "",
    productId: "",
    quantity: "1.000",
    unitCost: "0.0000",
  };
}

function toNumber(value: string): number {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : Number.NaN;
}

export function AdminPurchaseWorkflowPanel({
  errorMessage,
  isSubmitting = false,
  mode,
  onClose,
  onSubmitCancel,
  onSubmitDirectEntry,
  onSubmitPurchase,
  onSubmitReceipt,
  options,
  purchase,
}: AdminPurchaseWorkflowPanelProps) {
  const [branchId, setBranchId] = useState(purchase?.overview.branchId ?? "");
  const [supplierId, setSupplierId] = useState(purchase?.overview.supplierId ?? "");
  const [externalDocumentType, setExternalDocumentType] = useState("REMISSION");
  const [externalDocumentNumber, setExternalDocumentNumber] = useState("");
  const [notes, setNotes] = useState("");
  const [confirmNow, setConfirmNow] = useState(mode === "direct");
  const [lines, setLines] = useState<EditableLine[]>([newLine()]);
  const [cancelReason, setCancelReason] = useState("");
  const [formError, setFormError] = useState<string | null>(null);
  const [receiptLines, setReceiptLines] = useState<ReceiptLineState[]>(
    () =>
      purchase?.lines
        .filter((line) => Number(line.pendingQuantity) > 0)
        .map((line) => ({
          discrepancyReason: "",
          notes: "",
          purchaseLineId: line.purchaseLineId,
          receivedQuantity: line.pendingQuantity,
          unitCost: line.unitCost,
        })) ?? [],
  );

  const title = {
    cancel: "Cancelar compra",
    direct: "Nueva entrada directa",
    purchase: "Nueva compra",
    receive: "Recibir mercancia",
  }[mode];

  const primaryLabel = {
    cancel: "Confirmar cancelacion",
    direct: "Confirmar entrada",
    purchase: confirmNow ? "Confirmar compra" : "Guardar borrador",
    receive: "Confirmar recepcion",
  }[mode];

  const hasDiscrepancy = useMemo(() => {
    if (mode !== "receive" || !purchase) {
      return false;
    }
    const pendingByLine = new Map(purchase.lines.map((line) => [line.purchaseLineId, line.pendingQuantity]));
    return receiptLines.some((line) => line.receivedQuantity !== pendingByLine.get(line.purchaseLineId));
  }, [mode, purchase, receiptLines]);

  function patchLine(index: number, patch: Partial<EditableLine>) {
    setLines((current) => current.map((line, lineIndex) => (lineIndex === index ? { ...line, ...patch } : line)));
  }

  function patchReceiptLine(index: number, patch: Partial<ReceiptLineState>) {
    setReceiptLines((current) =>
      current.map((line, lineIndex) => (lineIndex === index ? { ...line, ...patch } : line)),
    );
  }

  function validateCommon() {
    if (!supplierId) {
      return "Selecciona un proveedor.";
    }
    if (!branchId) {
      return "Selecciona una sucursal receptora.";
    }
    if (lines.length === 0) {
      return "Agrega al menos una linea.";
    }
    for (const line of lines) {
      if (!line.productId) {
        return "Selecciona producto en cada linea.";
      }
      if (toNumber(line.quantity) <= 0) {
        return "La cantidad debe ser mayor a 0.";
      }
      if (toNumber(line.unitCost) < 0) {
        return "El costo unitario no puede ser negativo.";
      }
    }
    return null;
  }

  function handleSubmit() {
    setFormError(null);
    if (mode === "cancel") {
      if (!cancelReason.trim()) {
        setFormError("Captura un motivo de cancelacion.");
        return;
      }
      onSubmitCancel({ reason: cancelReason.trim() });
      return;
    }

    if (mode === "receive") {
      if (!purchase) {
        setFormError("Selecciona una compra para recibir.");
        return;
      }
      if (!receiptLines.some((line) => toNumber(line.receivedQuantity) > 0)) {
        setFormError("Captura al menos una cantidad recibida.");
        return;
      }
      if (
        hasDiscrepancy &&
        receiptLines.some((line) => {
          const sourceLine = purchase.lines.find((purchaseLine) => purchaseLine.purchaseLineId === line.purchaseLineId);
          return sourceLine?.pendingQuantity !== line.receivedQuantity && !line.discrepancyReason.trim();
        })
      ) {
        setFormError("La razon de discrepancia es obligatoria cuando recibido y esperado difieren.");
        return;
      }
      onSubmitReceipt({
        lines: receiptLines.map((line) => ({
          discrepancyReason: line.discrepancyReason.trim() || null,
          notes: line.notes.trim() || null,
          purchaseLineId: line.purchaseLineId,
          receivedQuantity: line.receivedQuantity,
          unitCost: line.unitCost || null,
        })),
        notes: notes.trim() || null,
      });
      return;
    }

    const validation = validateCommon();
    if (validation) {
      setFormError(validation);
      return;
    }

    if (mode === "direct") {
      onSubmitDirectEntry({
        branchId,
        externalDocumentNumber: externalDocumentNumber.trim() || null,
        externalDocumentType: externalDocumentType || null,
        lines: lines.map((line) => ({
          notes: line.notes.trim() || null,
          productId: line.productId,
          receivedQuantity: line.quantity,
          unitCost: line.unitCost,
        })),
        notes: notes.trim() || null,
        supplierId,
      });
      return;
    }

    onSubmitPurchase({
      branchId,
      confirmNow,
      externalDocumentNumber: externalDocumentNumber.trim() || null,
      externalDocumentType: externalDocumentType || null,
      lines: lines.map((line) => ({
        notes: line.notes.trim() || null,
        orderedQuantity: line.quantity,
        productId: line.productId,
        unitCost: line.unitCost,
      })),
      notes: notes.trim() || null,
      supplierId,
    });
  }

  return (
    <aside className="flex min-h-0 min-w-0 flex-col overflow-hidden rounded-[20px] border border-[var(--ui-color-border)] bg-white">
      <div className="flex min-w-0 shrink-0 items-center justify-between gap-3 border-b border-[var(--ui-color-border)] px-3 py-2.5">
        <div className="min-w-0">
          <h3 className="truncate text-base font-semibold text-slate-950" title={title}>
            {title}
          </h3>
          <p className="truncate text-xs text-slate-500">
            La persistencia, movimientos y auditoria se confirman en backend.
          </p>
        </div>
        <button
          className="shrink-0 rounded-full border border-[var(--ui-color-border)] bg-white px-3 py-1 text-xs font-semibold text-slate-600 transition hover:bg-slate-50 focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
          type="button"
          onClick={onClose}
        >
          Cerrar
        </button>
      </div>

      <div className="min-h-0 flex-1 space-y-2 overflow-y-auto p-3">
        {errorMessage || formError ? (
          <p className="rounded-[16px] border border-rose-200 bg-[var(--ui-color-danger-soft)] px-3 py-2 text-sm font-semibold text-[var(--ui-color-danger)]">
            {formError ?? errorMessage}
          </p>
        ) : null}

        {mode === "cancel" ? (
          <label className="grid gap-1 text-xs font-semibold uppercase tracking-[0.1em] text-slate-500">
            Motivo de cancelacion
            <input
              className={inputClassName}
              value={cancelReason}
              onChange={(event) => setCancelReason(event.target.value)}
            />
          </label>
        ) : mode === "receive" && purchase ? (
          <div className="grid gap-2">
            <div className="rounded-[16px] border border-[var(--ui-color-border)] bg-slate-50 p-3 text-sm text-slate-700">
              <p className="font-semibold text-slate-950">{purchase.overview.folio}</p>
              <p className="text-xs text-slate-500">{purchase.supplierContext.supplierName}</p>
            </div>
            {receiptLines.length > 0 ? (
              receiptLines.map((line, index) => {
                const sourceLine = purchase.lines.find(
                  (purchaseLine) => purchaseLine.purchaseLineId === line.purchaseLineId,
                );
                return (
                  <div
                    className="grid gap-2 rounded-[16px] border border-[var(--ui-color-border)] bg-slate-50 p-3"
                    key={line.purchaseLineId}
                  >
                    <p className="truncate text-sm font-semibold text-slate-950" title={sourceLine?.productName}>
                      {sourceLine?.productName}
                    </p>
                    <div className="grid gap-2 md:grid-cols-3">
                      <label className="grid gap-1 text-xs font-semibold uppercase tracking-[0.1em] text-slate-500">
                        Pendiente
                        <input className={inputClassName} disabled value={sourceLine?.pendingQuantity ?? "0"} />
                      </label>
                      <label className="grid gap-1 text-xs font-semibold uppercase tracking-[0.1em] text-slate-500">
                        Recibido
                        <input
                          className={inputClassName}
                          min="0"
                          step="0.001"
                          type="number"
                          value={line.receivedQuantity}
                          onChange={(event) => patchReceiptLine(index, { receivedQuantity: event.target.value })}
                        />
                      </label>
                      <label className="grid gap-1 text-xs font-semibold uppercase tracking-[0.1em] text-slate-500">
                        Costo
                        <input
                          className={inputClassName}
                          min="0"
                          step="0.0001"
                          type="number"
                          value={line.unitCost}
                          onChange={(event) => patchReceiptLine(index, { unitCost: event.target.value })}
                        />
                      </label>
                    </div>
                    <label className="grid gap-1 text-xs font-semibold uppercase tracking-[0.1em] text-slate-500">
                      Razon de discrepancia
                      <input
                        className={inputClassName}
                        placeholder="Obligatoria si recibido difiere de pendiente"
                        value={line.discrepancyReason}
                        onChange={(event) => patchReceiptLine(index, { discrepancyReason: event.target.value })}
                      />
                    </label>
                  </div>
                );
              })
            ) : (
              <p className="rounded-[16px] border border-[var(--ui-color-border)] bg-slate-50 px-3 py-2 text-sm text-slate-600">
                No hay compras pendientes de recepcion.
              </p>
            )}
          </div>
        ) : (
          <div className="grid gap-2">
            <div className="grid gap-2 md:grid-cols-2">
              <label className="grid gap-1 text-xs font-semibold uppercase tracking-[0.1em] text-slate-500">
                Proveedor
                <select className={inputClassName} value={supplierId} onChange={(event) => setSupplierId(event.target.value)}>
                  <option value="">Selecciona proveedor</option>
                  {options.suppliers.map((option) => (
                    <option key={option.id} value={option.id}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </label>
              <label className="grid gap-1 text-xs font-semibold uppercase tracking-[0.1em] text-slate-500">
                Sucursal receptora
                <select className={inputClassName} value={branchId} onChange={(event) => setBranchId(event.target.value)}>
                  <option value="">Selecciona sucursal</option>
                  {options.branches.map((option) => (
                    <option key={option.id} value={option.id}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </label>
            </div>

            <div className="grid gap-2 md:grid-cols-2">
              <label className="grid gap-1 text-xs font-semibold uppercase tracking-[0.1em] text-slate-500">
                Tipo documento externo
                <select
                  className={inputClassName}
                  value={externalDocumentType}
                  onChange={(event) => setExternalDocumentType(event.target.value)}
                >
                  <option value="INVOICE">Factura</option>
                  <option value="REMISSION">Remision</option>
                  <option value="SUPPLIER_NOTE">Nota proveedor</option>
                  <option value="PURCHASE_REFERENCE">Referencia compra</option>
                  <option value="OTHER">Otro</option>
                </select>
              </label>
              <label className="grid gap-1 text-xs font-semibold uppercase tracking-[0.1em] text-slate-500">
                Numero externo
                <input
                  className={inputClassName}
                  value={externalDocumentNumber}
                  onChange={(event) => setExternalDocumentNumber(event.target.value)}
                />
              </label>
            </div>

            {mode === "purchase" ? (
              <label className="flex items-center gap-2 rounded-[16px] border border-[var(--ui-color-border)] bg-slate-50 px-3 py-2 text-sm font-semibold text-slate-700">
                <input checked={confirmNow} type="checkbox" onChange={(event) => setConfirmNow(event.target.checked)} />
                Confirmar compra al guardar
              </label>
            ) : null}

            <div className="grid gap-2">
              {lines.map((line, index) => (
                <div className="grid gap-2 rounded-[16px] border border-[var(--ui-color-border)] bg-slate-50 p-3" key={index}>
                  <label className="grid gap-1 text-xs font-semibold uppercase tracking-[0.1em] text-slate-500">
                    Producto
                    <select
                      className={inputClassName}
                      value={line.productId}
                      onChange={(event) => patchLine(index, { productId: event.target.value })}
                    >
                      <option value="">Selecciona producto</option>
                      {options.products.map((option) => (
                        <option key={option.id} value={option.id}>
                          {option.label}
                        </option>
                      ))}
                    </select>
                  </label>
                  <div className="grid gap-2 md:grid-cols-3">
                    <label className="grid gap-1 text-xs font-semibold uppercase tracking-[0.1em] text-slate-500">
                      {mode === "direct" ? "Cantidad recibida" : "Cantidad ordenada"}
                      <input
                        className={inputClassName}
                        min="0"
                        step="0.001"
                        type="number"
                        value={line.quantity}
                        onChange={(event) => patchLine(index, { quantity: event.target.value })}
                      />
                    </label>
                    <label className="grid gap-1 text-xs font-semibold uppercase tracking-[0.1em] text-slate-500">
                      Costo unitario
                      <input
                        className={inputClassName}
                        min="0"
                        step="0.0001"
                        type="number"
                        value={line.unitCost}
                        onChange={(event) => patchLine(index, { unitCost: event.target.value })}
                      />
                    </label>
                    <label className="grid gap-1 text-xs font-semibold uppercase tracking-[0.1em] text-slate-500">
                      Notas
                      <input
                        className={inputClassName}
                        value={line.notes}
                        onChange={(event) => patchLine(index, { notes: event.target.value })}
                      />
                    </label>
                  </div>
                  {lines.length > 1 ? (
                    <button
                      className="justify-self-start rounded-full border border-[var(--ui-color-border)] bg-white px-3 py-1 text-xs font-semibold text-slate-600"
                      type="button"
                      onClick={() => setLines((current) => current.filter((_, lineIndex) => lineIndex !== index))}
                    >
                      Quitar linea
                    </button>
                  ) : null}
                </div>
              ))}
              <button
                className="justify-self-start rounded-full border border-[var(--ui-color-border)] bg-white px-3 py-1 text-xs font-semibold text-slate-600 transition hover:bg-slate-50 focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
                type="button"
                onClick={() => setLines((current) => [...current, newLine()])}
              >
                Agregar linea
              </button>
            </div>
          </div>
        )}

        {mode !== "cancel" ? (
          <label className="grid gap-1 text-xs font-semibold uppercase tracking-[0.1em] text-slate-500">
            Notas
            <textarea
              className="min-h-[5rem] w-full min-w-0 rounded-2xl border border-[var(--ui-color-border)] bg-white px-3 py-2 text-sm font-medium text-slate-950 outline-none transition placeholder:text-slate-400 focus:border-[var(--ui-color-info)] focus:ring-4 focus:ring-[var(--ui-color-ring)]"
              value={notes}
              onChange={(event) => setNotes(event.target.value)}
            />
          </label>
        ) : null}
      </div>

      <div className="flex shrink-0 justify-end gap-2 border-t border-[var(--ui-color-border)] px-3 py-2">
        <button
          className="rounded-full border border-[var(--ui-color-border)] bg-white px-3 py-1.5 text-sm font-semibold text-slate-700 transition hover:bg-slate-50 focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
          type="button"
          onClick={onClose}
        >
          Cancelar
        </button>
        <button
          className="rounded-full bg-[var(--ui-color-info)] px-3 py-1.5 text-sm font-semibold text-white transition hover:brightness-95 focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)] disabled:cursor-not-allowed disabled:bg-slate-300"
          disabled={isSubmitting}
          type="button"
          onClick={handleSubmit}
        >
          {isSubmitting ? "Guardando" : primaryLabel}
        </button>
      </div>
    </aside>
  );
}
