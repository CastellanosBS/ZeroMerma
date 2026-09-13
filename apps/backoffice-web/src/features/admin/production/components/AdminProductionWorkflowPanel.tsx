import { AdminActionButton } from "../../components/AdminActionButton";
import { hasEffectiveCapability, type PermissionCode } from "../../../auth/authorization";
import { useBackofficeAuthorization } from "../../../auth/authorization-context";
import { useMemo, useState } from "react";
import type { FormEvent } from "react";

import type {
  AdminProductionCompletePayload,
  AdminProductionCreatePayload,
  AdminProductionDetail,
  AdminProductionFilterOption,
  AdminProductionUpdatePayload,
} from "../types";

const inputClassName =
  "h-10 w-full min-w-0 rounded-2xl border border-[var(--ui-color-border)] bg-white px-3 text-sm font-medium text-slate-950 outline-none transition placeholder:text-slate-400 focus:border-[var(--ui-color-info)] focus:ring-4 focus:ring-[var(--ui-color-ring)] disabled:cursor-not-allowed disabled:bg-slate-100 disabled:text-slate-500";

type WorkflowMode = "cancel" | "complete" | "create" | "edit" | "start";

interface AdminProductionWorkflowPanelProps {
  branchOptions: AdminProductionFilterOption[];
  errorMessage?: string | null;
  isSubmitting?: boolean;
  mode: WorkflowMode;
  onCancelProduction: (reason: string | null) => void;
  onClose: () => void;
  onComplete: (payload: AdminProductionCompletePayload) => void;
  onCreate: (payload: AdminProductionCreatePayload, startNow: boolean) => void;
  onStart: (notes: string | null) => void;
  onUpdate: (payload: AdminProductionUpdatePayload) => void;
  productOptions: AdminProductionFilterOption[];
  production?: AdminProductionDetail | null;
  recipeOptions: AdminProductionFilterOption[];
}

function getTitle(mode: WorkflowMode): string {
  const labels: Record<WorkflowMode, string> = {
    cancel: "Cancelar produccion",
    complete: "Completar produccion",
    create: "Nueva produccion",
    edit: "Editar borrador",
    start: "Iniciar produccion",
  };
  return labels[mode];
}

function getDescription(mode: WorkflowMode, production?: AdminProductionDetail | null): string {
  if (mode === "create") {
    return "Crea un lote persistido antes de iniciar o afectar inventario.";
  }
  if (mode === "edit") {
    return production
      ? `${production.overview.folio} - solo disponible en borrador.`
      : "Solo disponible en borrador.";
  }
  if (mode === "start") {
    return production
      ? `${production.overview.folio} validara insumos antes de iniciar.`
      : "Valida insumos antes de iniciar.";
  }
  if (mode === "complete") {
    return production
      ? `${production.overview.folio} consumira insumos y generara salida terminada.`
      : "Cierre auditable.";
  }
  return production
    ? `${production.overview.folio} quedara cancelada si backend lo permite.`
    : "Cancelacion controlada.";
}

export function AdminProductionWorkflowPanel({
  branchOptions: allBranchOptions,
  errorMessage,
  isSubmitting = false,
  mode,
  onCancelProduction,
  onClose,
  onComplete,
  onCreate,
  onStart,
  onUpdate,
  productOptions,
  production,
  recipeOptions,
}: AdminProductionWorkflowPanelProps) {
  const actor = useBackofficeAuthorization();
  const actionCapability: PermissionCode =
    mode === "cancel"
      ? "production.cancel"
      : mode === "start" || mode === "complete"
        ? "production.execute"
        : "production.manage";
  const branchOptions = useMemo(
    () =>
      allBranchOptions.filter((option) =>
        hasEffectiveCapability(actor, actionCapability, [option.id]),
      ),
    [actor, actionCapability, allBranchOptions],
  );
  const [actualOutputQty, setActualOutputQty] = useState(
    production?.overview.plannedOutputQty ?? "",
  );
  const [branchId, setBranchId] = useState(
    production?.overview.branchId || branchOptions[0]?.id || "",
  );
  const [localError, setLocalError] = useState<string | null>(null);
  const [notes, setNotes] = useState(production?.overview.notes ?? "");
  const [plannedAt, setPlannedAt] = useState(production?.overview.plannedAt?.slice(0, 16) ?? "");
  const [plannedOutputQty, setPlannedOutputQty] = useState(
    production?.overview.plannedOutputQty ?? "",
  );
  const [productId, setProductId] = useState(
    production?.productRecipe.productId || productOptions[0]?.id || "",
  );
  const [reason, setReason] = useState("");
  const [recipeId, setRecipeId] = useState(production?.productRecipe.recipeId || "");
  const [varianceReason, setVarianceReason] = useState(production?.overview.varianceReason ?? "");

  const selectedBranchLabel = useMemo(
    () =>
      branchOptions.find((option) => option.id === branchId)?.label ?? "Sucursal no seleccionada",
    [branchOptions, branchId],
  );
  const selectedProductLabel = useMemo(
    () =>
      productOptions.find((option) => option.id === productId)?.label ?? "Producto no seleccionado",
    [productOptions, productId],
  );

  function validateDraft(): boolean {
    if (!branchId) {
      setLocalError("Selecciona una sucursal.");
      return false;
    }
    if (!productId) {
      setLocalError("Selecciona un producto terminado.");
      return false;
    }
    if (!plannedOutputQty || Number(plannedOutputQty) <= 0) {
      setLocalError("La cantidad planeada debe ser mayor que cero.");
      return false;
    }
    return true;
  }

  function validateCompletion(): boolean {
    if (!actualOutputQty || Number(actualOutputQty) < 0) {
      setLocalError("La cantidad producida debe ser cero o mayor.");
      return false;
    }
    const planned = Number(production?.overview.plannedOutputQty ?? 0);
    const actual = Number(actualOutputQty);
    if ((actual === 0 || actual !== planned) && !varianceReason.trim()) {
      setLocalError("Captura una razon cuando la salida es cero o difiere de lo planeado.");
      return false;
    }
    return true;
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!hasEffectiveCapability(actor, actionCapability, [branchId])) return;
    setLocalError(null);

    if (mode === "create" || mode === "edit") {
      if (!validateDraft()) {
        return;
      }
      const payload = {
        notes: notes.trim() || null,
        plannedAt: plannedAt ? new Date(plannedAt).toISOString() : null,
        plannedOutputQty,
        productId,
        recipeId: recipeId || null,
      };
      if (mode === "edit") {
        onUpdate(payload);
        return;
      }
      onCreate({ ...payload, branchId }, false);
      return;
    }

    if (mode === "start") {
      onStart(notes.trim() || null);
      return;
    }

    if (mode === "complete") {
      if (!validateCompletion()) {
        return;
      }
      onComplete({
        actualOutputQty,
        notes: notes.trim() || null,
        varianceReason: varianceReason.trim() || null,
      });
      return;
    }

    onCancelProduction(reason.trim() || null);
  }

  function handleCreateAndStart() {
    if (
      !hasEffectiveCapability(actor, "production.manage", [branchId]) ||
      !hasEffectiveCapability(actor, "production.execute", [branchId])
    )
      return;
    setLocalError(null);
    if (!validateDraft()) {
      return;
    }
    onCreate(
      {
        branchId,
        notes: notes.trim() || null,
        plannedAt: plannedAt ? new Date(plannedAt).toISOString() : null,
        plannedOutputQty,
        productId,
        recipeId: recipeId || null,
      },
      true,
    );
  }

  return (
    <form
      className="grid min-w-0 gap-3 rounded-[20px] border border-[var(--ui-color-border)] bg-white p-3"
      onSubmit={handleSubmit}
    >
      <div className="flex min-w-0 items-start justify-between gap-3">
        <div className="min-w-0">
          <h3 className="truncate text-base font-semibold text-slate-950">{getTitle(mode)}</h3>
          <p className="truncate text-xs text-slate-500" title={getDescription(mode, production)}>
            {getDescription(mode, production)}
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

      {mode === "create" || mode === "edit" ? (
        <div className="grid min-w-0 gap-2 lg:grid-cols-4">
          <label className="grid min-w-0 gap-1 text-xs font-semibold uppercase tracking-[0.1em] text-slate-500">
            Sucursal
            <select
              className={`${inputClassName} truncate`}
              disabled={branchOptions.length === 0 || mode === "edit"}
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
          <label className="grid min-w-0 gap-1 text-xs font-semibold uppercase tracking-[0.1em] text-slate-500 lg:col-span-2">
            Producto terminado
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
            Cantidad
            <input
              className={inputClassName}
              min="0.001"
              placeholder="0.000"
              step="0.001"
              type="number"
              value={plannedOutputQty}
              onChange={(event) => setPlannedOutputQty(event.target.value)}
            />
          </label>
          <label className="grid min-w-0 gap-1 text-xs font-semibold uppercase tracking-[0.1em] text-slate-500 lg:col-span-2">
            Receta activa
            <select
              className={`${inputClassName} truncate`}
              value={recipeId}
              onChange={(event) => setRecipeId(event.target.value)}
            >
              <option value="">Usar receta activa del producto</option>
              {recipeOptions.map((option) => (
                <option key={option.id} title={option.label} value={option.id}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>
          <label className="grid min-w-0 gap-1 text-xs font-semibold uppercase tracking-[0.1em] text-slate-500 lg:col-span-2">
            Fecha planeada
            <input
              className={inputClassName}
              type="datetime-local"
              value={plannedAt}
              onChange={(event) => setPlannedAt(event.target.value)}
            />
          </label>
        </div>
      ) : null}

      {mode === "complete" ? (
        <div className="grid min-w-0 gap-2 lg:grid-cols-2">
          <label className="grid min-w-0 gap-1 text-xs font-semibold uppercase tracking-[0.1em] text-slate-500">
            Salida real
            <input
              className={inputClassName}
              min="0"
              placeholder="0.000"
              step="0.001"
              type="number"
              value={actualOutputQty}
              onChange={(event) => setActualOutputQty(event.target.value)}
            />
          </label>
          <label className="grid min-w-0 gap-1 text-xs font-semibold uppercase tracking-[0.1em] text-slate-500">
            Razon de variacion
            <input
              className={inputClassName}
              maxLength={180}
              placeholder="Obligatoria si difiere de lo planeado"
              value={varianceReason}
              onChange={(event) => setVarianceReason(event.target.value)}
            />
          </label>
        </div>
      ) : null}

      {production && (mode === "start" || mode === "complete") ? (
        <div className="grid gap-2 rounded-[18px] border border-[var(--ui-color-border)] bg-slate-50 p-2.5">
          <span className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">
            Insumos y advertencias
          </span>
          <div className="grid gap-1.5 md:grid-cols-2 xl:grid-cols-3">
            {production.plannedInputs.map((line) => (
              <div
                className="rounded-[14px] border border-[var(--ui-color-border)] bg-white px-3 py-2 text-xs"
                key={line.inputProductId}
              >
                <span
                  className="block truncate font-semibold text-slate-950"
                  title={line.inputProductName}
                >
                  {line.inputProductName}
                </span>
                <span className="block truncate text-slate-500">
                  Req. {line.requiredQty} / Disp. {line.availableQty ?? "N/D"} / Falt.{" "}
                  {line.shortageQty ?? "0.000"}
                </span>
              </div>
            ))}
          </div>
        </div>
      ) : null}

      {mode === "cancel" ? (
        <label className="grid min-w-0 gap-1 text-xs font-semibold uppercase tracking-[0.1em] text-slate-500">
          Motivo / notas
          <textarea
            className="min-h-20 w-full min-w-0 rounded-2xl border border-[var(--ui-color-border)] bg-white px-3 py-2 text-sm font-medium normal-case tracking-normal text-slate-950 outline-none transition placeholder:text-slate-400 focus:border-[var(--ui-color-info)] focus:ring-4 focus:ring-[var(--ui-color-ring)]"
            maxLength={500}
            placeholder="Contexto de cancelacion si aplica."
            value={reason}
            onChange={(event) => setReason(event.target.value)}
          />
        </label>
      ) : null}

      {mode !== "cancel" ? (
        <label className="grid min-w-0 gap-1 text-xs font-semibold uppercase tracking-[0.1em] text-slate-500">
          Notas
          <textarea
            className="min-h-20 w-full min-w-0 rounded-2xl border border-[var(--ui-color-border)] bg-white px-3 py-2 text-sm font-medium normal-case tracking-normal text-slate-950 outline-none transition placeholder:text-slate-400 focus:border-[var(--ui-color-info)] focus:ring-4 focus:ring-[var(--ui-color-ring)]"
            maxLength={500}
            placeholder="Contexto operativo, turno, horno, responsable o evidencia disponible."
            value={notes}
            onChange={(event) => setNotes(event.target.value)}
          />
        </label>
      ) : null}

      <p className="rounded-[16px] border border-[var(--ui-color-border)] bg-slate-50 px-3 py-2 text-xs leading-5 text-slate-600">
        Produccion consume insumos y genera producto terminado solo cuando el backend confirma el
        cierre del lote.
      </p>

      <div className="flex min-w-0 flex-wrap justify-end gap-2 border-t border-[var(--ui-color-border)] pt-3">
        <button
          className="rounded-2xl border border-[var(--ui-color-border)] bg-white px-4 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-50 focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
          type="button"
          onClick={onClose}
        >
          Cerrar
        </button>
        {mode === "create" ? (
          <AdminActionButton
            capability="production.manage"
            additionalCapabilities={["production.execute"]}
            branchIds={[branchId]}
            className="rounded-2xl border border-[var(--ui-color-border)] bg-white px-4 py-2 text-sm font-semibold text-[var(--ui-color-info)] transition hover:bg-[var(--ui-color-surface-tint)] focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)] disabled:cursor-not-allowed disabled:bg-slate-100 disabled:text-slate-400"
            disabled={isSubmitting}
            type="button"
            onClick={handleCreateAndStart}
          >
            Guardar e iniciar
          </AdminActionButton>
        ) : null}
        <AdminActionButton
          capability={actionCapability}
          branchIds={[branchId]}
          className="rounded-2xl bg-[var(--ui-color-primary)] px-4 py-2 text-sm font-semibold text-white transition hover:bg-[var(--ui-color-primary-strong)] focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)] disabled:cursor-not-allowed disabled:bg-slate-300 disabled:text-slate-600"
          disabled={isSubmitting}
          type="submit"
        >
          {isSubmitting
            ? "Guardando"
            : mode === "create"
              ? "Guardar borrador"
              : mode === "edit"
                ? "Guardar cambios"
                : mode === "start"
                  ? "Iniciar produccion"
                  : mode === "complete"
                    ? "Completar produccion"
                    : "Cancelar produccion"}
        </AdminActionButton>
      </div>
    </form>
  );
}
