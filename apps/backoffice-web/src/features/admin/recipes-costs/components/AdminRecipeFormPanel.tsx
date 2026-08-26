import type { FormEvent, ReactNode } from "react";
import { useMemo, useState } from "react";

import type {
  AdminRecipeCostProduct,
  AdminRecipeCreatePayload,
  AdminRecipeFilterOption,
} from "../types";

const inputClassName =
  "h-10 w-full min-w-0 rounded-2xl border border-[var(--ui-color-border)] bg-white px-3 text-sm font-medium text-slate-950 outline-none transition placeholder:text-slate-400 focus:border-[var(--ui-color-info)] focus:ring-4 focus:ring-[var(--ui-color-ring)] disabled:cursor-not-allowed disabled:bg-slate-100 disabled:text-slate-500";

interface DraftInput {
  inputProductId: string;
  quantity: string;
}

function Field({
  children,
  className = "",
  id,
  label,
}: {
  children: ReactNode;
  className?: string;
  id: string;
  label: string;
}) {
  return (
    <label
      className={`grid min-w-0 gap-1 text-xs font-semibold uppercase tracking-[0.1em] text-slate-500 ${className}`}
      htmlFor={id}
      title={label}
    >
      <span className="truncate">{label}</span>
      {children}
    </label>
  );
}

interface AdminRecipeFormPanelProps {
  errorMessage?: string | null;
  isSubmitting: boolean;
  onClose: () => void;
  onSubmit: (payload: AdminRecipeCreatePayload) => void;
  product: AdminRecipeCostProduct | null;
  rawMaterialOptions: AdminRecipeFilterOption[];
}

export function AdminRecipeFormPanel({
  errorMessage,
  isSubmitting,
  onClose,
  onSubmit,
  product,
  rawMaterialOptions,
}: AdminRecipeFormPanelProps) {
  const [versionName, setVersionName] = useState("");
  const [yieldQty, setYieldQty] = useState("");
  const [yieldUom, setYieldUom] = useState(product?.unitOfMeasure ?? "piece");
  const [activate, setActivate] = useState(true);
  const [inputs, setInputs] = useState<DraftInput[]>([
    { inputProductId: rawMaterialOptions[0]?.id ?? "", quantity: "" },
  ]);
  const [clientError, setClientError] = useState<string | null>(null);

  const canSubmit = useMemo(() => {
    const uniqueInputs = new Set(inputs.map((input) => input.inputProductId).filter(Boolean));
    return (
      Boolean(product) &&
      yieldQty.trim().length > 0 &&
      Number(yieldQty) > 0 &&
      inputs.length > 0 &&
      inputs.every((input) => input.inputProductId && Number(input.quantity) > 0) &&
      uniqueInputs.size === inputs.length &&
      !isSubmitting
    );
  }, [inputs, isSubmitting, product, yieldQty]);

  function updateInput(index: number, patch: Partial<DraftInput>) {
    setInputs((current) =>
      current.map((input, inputIndex) => (inputIndex === index ? { ...input, ...patch } : input)),
    );
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setClientError(null);

    if (!product) {
      setClientError("Selecciona un producto terminado.");
      return;
    }
    if (Number(yieldQty) <= 0) {
      setClientError("El rendimiento debe ser mayor a cero.");
      return;
    }
    if (inputs.length === 0) {
      setClientError("La receta requiere al menos un insumo.");
      return;
    }
    const inputIds = inputs.map((input) => input.inputProductId);
    if (new Set(inputIds).size !== inputIds.length) {
      setClientError("La receta no puede repetir insumos.");
      return;
    }
    if (!canSubmit) {
      return;
    }

    onSubmit({
      activate,
      inputs: inputs.map((input) => ({
        inputProductId: input.inputProductId,
        quantity: input.quantity,
      })),
      productId: product.productId,
      versionName: versionName.trim() || null,
      yieldQty: yieldQty.trim(),
      yieldUom: yieldUom.trim() || product.unitOfMeasure,
    });
  }

  return (
    <form
      className="min-w-0 overflow-hidden rounded-[22px] border border-[var(--ui-color-border)] bg-slate-50/80 p-4"
      onSubmit={handleSubmit}
    >
      <div className="flex min-w-0 flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">
            Definicion tecnica
          </p>
          <h3 className="mt-1 truncate text-base font-semibold text-slate-950" title={product?.productName ?? "Nueva receta"}>
            Nueva receta{product ? ` - ${product.productName}` : ""}
          </h3>
          <p className="mt-1 max-w-4xl text-sm leading-5 text-slate-600">
            Define rendimiento e insumos RAW_MATERIAL. El costo se calcula en backend con costo estandar de insumos.
          </p>
        </div>
        <button
          className="shrink-0 rounded-2xl border border-[var(--ui-color-border)] bg-white px-3 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-50 focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
          disabled={isSubmitting}
          type="button"
          onClick={onClose}
        >
          Cerrar
        </button>
      </div>

      <div className="mt-4 grid min-w-0 gap-3 md:grid-cols-2 xl:grid-cols-4">
        <Field className="md:col-span-2" id="admin-recipe-version-name" label="Version">
          <input
            className={inputClassName}
            id="admin-recipe-version-name"
            placeholder="Ej. Base 2026"
            value={versionName}
            onChange={(event) => setVersionName(event.target.value)}
          />
        </Field>
        <Field id="admin-recipe-yield" label="Rendimiento">
          <input
            className={inputClassName}
            id="admin-recipe-yield"
            inputMode="decimal"
            placeholder="0.000"
            value={yieldQty}
            onChange={(event) => setYieldQty(event.target.value)}
          />
        </Field>
        <Field id="admin-recipe-yield-uom" label="Unidad rendimiento">
          <input
            className={inputClassName}
            id="admin-recipe-yield-uom"
            value={yieldUom}
            onChange={(event) => setYieldUom(event.target.value)}
          />
        </Field>
        <Field id="admin-recipe-activate" label="Guardar como">
          <select
            className={inputClassName}
            id="admin-recipe-activate"
            value={activate ? "active" : "draft"}
            onChange={(event) => setActivate(event.target.value === "active")}
          >
            <option value="active">Receta activa</option>
            <option value="draft">Version inactiva</option>
          </select>
        </Field>
      </div>

      <section className="mt-4 rounded-[18px] border border-[var(--ui-color-border)] bg-white p-3">
        <div className="flex min-w-0 flex-wrap items-center justify-between gap-2">
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">Insumos</p>
          <button
            className="rounded-full border border-[var(--ui-color-border)] bg-white px-3 py-1 text-xs font-semibold text-[var(--ui-color-info)] disabled:cursor-not-allowed disabled:bg-slate-100 disabled:text-slate-400"
            disabled={rawMaterialOptions.length === 0}
            type="button"
            onClick={() => setInputs((current) => [...current, { inputProductId: rawMaterialOptions[0]?.id ?? "", quantity: "" }])}
          >
            Agregar insumo
          </button>
        </div>

        {rawMaterialOptions.length === 0 ? (
          <p className="mt-2 rounded-[14px] border border-dashed border-[var(--ui-color-border)] bg-slate-50 px-3 py-2 text-sm text-slate-600">
            No hay materias primas RAW_MATERIAL disponibles para construir recetas.
          </p>
        ) : (
          <div className="mt-2 grid gap-2">
            {inputs.map((input, index) => (
              <div className="grid min-w-0 gap-2 md:grid-cols-[minmax(0,1fr)_8rem_auto]" key={index}>
                <select
                  className={inputClassName}
                  value={input.inputProductId}
                  onChange={(event) => updateInput(index, { inputProductId: event.target.value })}
                >
                  {rawMaterialOptions.map((option) => (
                    <option key={option.id} title={option.label} value={option.id}>
                      {option.label}
                    </option>
                  ))}
                </select>
                <input
                  className={inputClassName}
                  inputMode="decimal"
                  placeholder="Cantidad"
                  value={input.quantity}
                  onChange={(event) => updateInput(index, { quantity: event.target.value })}
                />
                <button
                  className="h-10 rounded-2xl border border-[var(--ui-color-border)] bg-white px-3 text-sm font-semibold text-slate-600"
                  type="button"
                  onClick={() => setInputs((current) => current.filter((_, inputIndex) => inputIndex !== index))}
                >
                  Quitar
                </button>
              </div>
            ))}
          </div>
        )}
      </section>

      {clientError || errorMessage ? (
        <p className="mt-3 rounded-[16px] border border-rose-200 bg-[var(--ui-color-danger-soft)] px-3 py-2 text-sm font-semibold text-[var(--ui-color-danger)]">
          {clientError ?? errorMessage}
        </p>
      ) : null}

      <div className="mt-4 flex min-w-0 flex-wrap items-center justify-between gap-3 border-t border-[var(--ui-color-border)] pt-3">
        <p className="min-w-0 text-sm leading-5 text-slate-600">
          No se modifica el costo estandar del producto al guardar; esa accion es explicita desde el detalle.
        </p>
        <button
          className="shrink-0 rounded-2xl bg-[var(--ui-color-info)] px-4 py-2 text-sm font-semibold text-white shadow-sm transition hover:brightness-95 focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)] disabled:cursor-not-allowed disabled:bg-slate-300 disabled:text-slate-600"
          disabled={!canSubmit}
          type="submit"
        >
          {isSubmitting ? "Guardando..." : "Guardar receta"}
        </button>
      </div>
    </form>
  );
}
