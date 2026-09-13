import { AdminActionButton } from "../../components/AdminActionButton";
import { useMemo, useState } from "react";
import type { FormEvent } from "react";

import type {
  AdminInventoryAdjustmentPayload,
  AdminInventoryAdjustmentType,
  AdminInventoryDetail,
  AdminInventoryFilterOption,
  AdminInventoryListItem,
  AdminInventoryLocationCode,
} from "../types";

const inputClassName =
  "h-10 w-full min-w-0 rounded-2xl border border-[var(--ui-color-border)] bg-white px-3 text-sm font-medium text-slate-950 outline-none transition placeholder:text-slate-400 focus:border-[var(--ui-color-info)] focus:ring-4 focus:ring-[var(--ui-color-ring)] disabled:cursor-not-allowed disabled:bg-slate-100 disabled:text-slate-500";

const adjustmentTypeOptions: Array<{ label: string; value: AdminInventoryAdjustmentType }> = [
  { value: "INCREASE", label: "Aumentar existencia" },
  { value: "DECREASE", label: "Disminuir existencia" },
  { value: "SET_COUNTED", label: "Fijar cantidad contada" },
];

function getDefaultProductId(
  source?: AdminInventoryDetail | AdminInventoryListItem | null,
): string {
  if (!source) {
    return "";
  }

  return "product" in source ? source.product.id : source.productId;
}

function getDefaultBranchId(source?: AdminInventoryDetail | AdminInventoryListItem | null): string {
  if (!source) {
    return "";
  }

  return "branchLocation" in source ? source.branchLocation.branchId : source.branchId;
}

function getDefaultLocationCode(
  source?: AdminInventoryDetail | AdminInventoryListItem | null,
): AdminInventoryLocationCode | "" {
  if (!source) {
    return "";
  }

  return "branchLocation" in source ? source.branchLocation.locationCode : source.locationCode;
}

function getSourceDescription(
  source?: AdminInventoryDetail | AdminInventoryListItem | null,
): string {
  if (!source) {
    return "Selecciona producto, sucursal y ubicacion desde datos reales del backend.";
  }

  if ("product" in source) {
    return `${source.product.name} - ${source.branchLocation.branchName} - ${source.branchLocation.locationName}`;
  }

  return `${source.productName} - ${source.branchName} - ${source.locationName}`;
}

interface AdminInventoryAdjustmentPanelProps {
  branchOptions: AdminInventoryFilterOption[];
  errorMessage?: string | null;
  initialInventory?: AdminInventoryDetail | AdminInventoryListItem | null;
  isSubmitting?: boolean;
  locationOptions: AdminInventoryFilterOption[];
  onClose: () => void;
  onSubmit: (payload: AdminInventoryAdjustmentPayload) => void;
  productOptions: AdminInventoryFilterOption[];
}

export function AdminInventoryAdjustmentPanel({
  branchOptions,
  errorMessage,
  initialInventory,
  isSubmitting = false,
  locationOptions,
  onClose,
  onSubmit,
  productOptions,
}: AdminInventoryAdjustmentPanelProps) {
  const [adjustmentType, setAdjustmentType] = useState<AdminInventoryAdjustmentType>("INCREASE");
  const [branchId, setBranchId] = useState(
    getDefaultBranchId(initialInventory) || branchOptions[0]?.id || "",
  );
  const [locationCode, setLocationCode] = useState<AdminInventoryLocationCode | "">(
    getDefaultLocationCode(initialInventory) ||
      (locationOptions[0]?.id as AdminInventoryLocationCode | undefined) ||
      "",
  );
  const [notes, setNotes] = useState("");
  const [productId, setProductId] = useState(
    getDefaultProductId(initialInventory) || productOptions[0]?.id || "",
  );
  const [quantity, setQuantity] = useState("");
  const [reason, setReason] = useState("");
  const [localError, setLocalError] = useState<string | null>(null);

  const selectedProductLabel = useMemo(
    () =>
      productOptions.find((option) => option.id === productId)?.label ?? "Producto no seleccionado",
    [productId, productOptions],
  );
  const selectedBranchLabel = useMemo(
    () =>
      branchOptions.find((option) => option.id === branchId)?.label ?? "Sucursal no seleccionada",
    [branchId, branchOptions],
  );

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLocalError(null);

    if (!productId) {
      setLocalError("Selecciona un producto valido.");
      return;
    }
    if (!branchId) {
      setLocalError("Selecciona una sucursal valida.");
      return;
    }
    if (!locationCode) {
      setLocalError("Selecciona una ubicacion de inventario.");
      return;
    }
    if (!quantity || Number(quantity) <= 0) {
      setLocalError("La cantidad debe ser mayor que cero.");
      return;
    }
    if (!reason.trim()) {
      setLocalError("La razon del ajuste es obligatoria.");
      return;
    }

    onSubmit({
      adjustmentType,
      branchId,
      locationCode,
      notes: notes.trim() || null,
      productId,
      quantity,
      reason: reason.trim(),
    });
  }

  return (
    <form
      className="grid min-w-0 gap-3 rounded-[20px] border border-[var(--ui-color-border)] bg-white p-3"
      onSubmit={handleSubmit}
    >
      <div className="flex min-w-0 items-start justify-between gap-3">
        <div className="min-w-0">
          <h3 className="truncate text-base font-semibold text-slate-950">
            Nuevo ajuste de inventario
          </h3>
          <p
            className="truncate text-xs text-slate-500"
            title={getSourceDescription(initialInventory)}
          >
            {getSourceDescription(initialInventory)}
          </p>
        </div>
        <button
          className="rounded-full border border-[var(--ui-color-border)] bg-white px-3 py-1.5 text-xs font-semibold text-slate-600 transition hover:bg-slate-50 focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
          type="button"
          onClick={onClose}
        >
          Cerrar
        </button>
      </div>

      {(localError || errorMessage) && (
        <p className="rounded-[16px] border border-rose-200 bg-[var(--ui-color-danger-soft)] px-3 py-2 text-sm font-semibold text-[var(--ui-color-danger)]">
          {localError ?? errorMessage}
        </p>
      )}

      <div className="grid min-w-0 gap-2 lg:grid-cols-[minmax(14rem,1.15fr)_minmax(12rem,1fr)_minmax(9rem,0.75fr)]">
        <label className="grid min-w-0 gap-1 text-xs font-semibold uppercase tracking-[0.1em] text-slate-500">
          Producto
          <select
            className={`${inputClassName} truncate`}
            disabled={productOptions.length === 0}
            title={selectedProductLabel}
            value={productId}
            onChange={(event) => setProductId(event.target.value)}
          >
            {productOptions.length === 0 ? (
              <option value="">Productos pendientes de API</option>
            ) : null}
            {productOptions.map((option) => (
              <option key={option.id} title={option.label} value={option.id}>
                {option.label}
              </option>
            ))}
          </select>
        </label>

        <label className="grid min-w-0 gap-1 text-xs font-semibold uppercase tracking-[0.1em] text-slate-500">
          Sucursal
          <select
            className={`${inputClassName} truncate`}
            disabled={branchOptions.length === 0}
            title={selectedBranchLabel}
            value={branchId}
            onChange={(event) => setBranchId(event.target.value)}
          >
            {branchOptions.length === 0 ? (
              <option value="">Sucursales pendientes de API</option>
            ) : null}
            {branchOptions.map((option) => (
              <option key={option.id} title={option.label} value={option.id}>
                {option.label}
              </option>
            ))}
          </select>
        </label>

        <label className="grid min-w-0 gap-1 text-xs font-semibold uppercase tracking-[0.1em] text-slate-500">
          Ubicacion
          <select
            className={inputClassName}
            disabled={locationOptions.length === 0}
            value={locationCode}
            onChange={(event) => setLocationCode(event.target.value as AdminInventoryLocationCode)}
          >
            {locationOptions.length === 0 ? (
              <option value="">Ubicaciones pendientes de API</option>
            ) : null}
            {locationOptions.map((option) => (
              <option key={option.id} title={option.label} value={option.id}>
                {option.label}
              </option>
            ))}
          </select>
        </label>
      </div>

      <div className="grid min-w-0 gap-2 lg:grid-cols-[minmax(12rem,1fr)_minmax(8rem,0.55fr)_minmax(14rem,1.2fr)]">
        <label className="grid min-w-0 gap-1 text-xs font-semibold uppercase tracking-[0.1em] text-slate-500">
          Tipo de ajuste
          <select
            className={inputClassName}
            value={adjustmentType}
            onChange={(event) =>
              setAdjustmentType(event.target.value as AdminInventoryAdjustmentType)
            }
          >
            {adjustmentTypeOptions.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </label>

        <label className="grid min-w-0 gap-1 text-xs font-semibold uppercase tracking-[0.1em] text-slate-500">
          Cantidad
          <input
            className={inputClassName}
            min="0.001"
            placeholder="0.000"
            step="0.001"
            type="number"
            value={quantity}
            onChange={(event) => setQuantity(event.target.value)}
          />
        </label>

        <label className="grid min-w-0 gap-1 text-xs font-semibold uppercase tracking-[0.1em] text-slate-500">
          Razon obligatoria
          <input
            className={inputClassName}
            maxLength={160}
            placeholder="Diferencia de conteo, correccion, merma no capturada..."
            value={reason}
            onChange={(event) => setReason(event.target.value)}
          />
        </label>
      </div>

      <label className="grid min-w-0 gap-1 text-xs font-semibold uppercase tracking-[0.1em] text-slate-500">
        Notas
        <textarea
          className="min-h-20 w-full min-w-0 rounded-2xl border border-[var(--ui-color-border)] bg-white px-3 py-2 text-sm font-medium normal-case tracking-normal text-slate-950 outline-none transition placeholder:text-slate-400 focus:border-[var(--ui-color-info)] focus:ring-4 focus:ring-[var(--ui-color-ring)]"
          maxLength={500}
          placeholder="Contexto adicional o evidencia operativa disponible."
          value={notes}
          onChange={(event) => setNotes(event.target.value)}
        />
      </label>

      <p className="rounded-[16px] border border-[var(--ui-color-border)] bg-slate-50 px-3 py-2 text-xs leading-5 text-slate-600">
        El ajuste crea un documento y movimiento auditado. No se edita la existencia historica ni se
        modifica el kardex de forma destructiva.
      </p>

      <div className="flex min-w-0 flex-wrap justify-end gap-2 border-t border-[var(--ui-color-border)] pt-3">
        <button
          className="rounded-2xl border border-[var(--ui-color-border)] bg-white px-4 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-50 focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
          type="button"
          onClick={onClose}
        >
          Cancelar
        </button>
        <AdminActionButton
          capability="inventory.adjust"
          branchIds={[branchId]}
          className="rounded-2xl bg-[var(--ui-color-primary)] px-4 py-2 text-sm font-semibold text-white transition hover:bg-[var(--ui-color-primary-strong)] focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)] disabled:cursor-not-allowed disabled:bg-slate-300 disabled:text-slate-600"
          disabled={isSubmitting}
          type="submit"
        >
          {isSubmitting ? "Guardando" : "Guardar ajuste"}
        </AdminActionButton>
      </div>
    </form>
  );
}
