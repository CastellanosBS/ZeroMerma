import { AdminActionButton } from "../../components/AdminActionButton";
import type { FormEvent, ReactNode } from "react";
import { useEffect, useMemo, useState } from "react";

import type {
  AdminProductCreatePayload,
  AdminProductFilterOption,
  AdminProductStatus,
} from "../types";

const inputClassName =
  "h-10 w-full min-w-0 rounded-2xl border border-[var(--ui-color-border)] bg-white px-3 text-sm font-medium text-slate-950 outline-none transition placeholder:text-slate-400 focus:border-[var(--ui-color-info)] focus:ring-4 focus:ring-[var(--ui-color-ring)] disabled:cursor-not-allowed disabled:bg-slate-100 disabled:text-slate-500";

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

interface AdminProductCreationPanelProps {
  classOptions: AdminProductFilterOption[];
  errorMessage?: string | null;
  isSubmitting: boolean;
  onClose: () => void;
  onSubmit: (payload: AdminProductCreatePayload) => void;
}

export function AdminProductCreationPanel({
  classOptions,
  errorMessage,
  isSubmitting,
  onClose,
  onSubmit,
}: AdminProductCreationPanelProps) {
  const [code, setCode] = useState("");
  const [name, setName] = useState("");
  const [productClassId, setProductClassId] = useState(classOptions[0]?.id ?? "");
  const [quickName, setQuickName] = useState("");
  const [searchAliases, setSearchAliases] = useState("");
  const [status, setStatus] = useState<AdminProductStatus>("active");
  const [unitPrice, setUnitPrice] = useState("");
  const canSubmit = useMemo(
    () =>
      classOptions.length > 0 &&
      code.trim().length > 0 &&
      name.trim().length > 0 &&
      productClassId.length > 0 &&
      unitPrice.trim().length > 0 &&
      !isSubmitting,
    [classOptions.length, code, isSubmitting, name, productClassId, unitPrice],
  );

  useEffect(() => {
    if (productClassId || !classOptions[0]) {
      return;
    }

    setProductClassId(classOptions[0].id);
  }, [classOptions, productClassId]);

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!canSubmit) {
      return;
    }

    onSubmit({
      code: code.trim(),
      name: name.trim(),
      productClassId,
      quickName: quickName.trim() || null,
      searchAliases: searchAliases.trim() || null,
      status,
      unitPrice: unitPrice.trim(),
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
            Captura administrativa
          </p>
          <h3
            className="mt-1 truncate text-base font-semibold text-slate-950"
            title="Nuevo producto"
          >
            Nuevo producto
          </h3>
          <p className="mt-1 max-w-4xl text-sm leading-5 text-slate-600">
            Crea un producto real en el catálogo. El modo de captura se deriva de la clase
            seleccionada.
          </p>
        </div>
        <button
          className="shrink-0 rounded-2xl border border-[var(--ui-color-border)] bg-white px-3 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-50 focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
          disabled={isSubmitting}
          type="button"
          onClick={onClose}
        >
          Cerrar captura
        </button>
      </div>

      <div className="mt-4 grid min-w-0 gap-3 md:grid-cols-2 xl:grid-cols-4">
        <Field className="md:col-span-2" id="admin-new-product-name" label="Nombre">
          <input
            className={inputClassName}
            id="admin-new-product-name"
            placeholder="Nombre del producto"
            value={name}
            onChange={(event) => setName(event.target.value)}
          />
        </Field>
        <Field id="admin-new-product-code" label="Código / SKU">
          <input
            className={inputClassName}
            id="admin-new-product-code"
            placeholder="Código interno"
            value={code}
            onChange={(event) => setCode(event.target.value)}
          />
        </Field>
        <Field id="admin-new-product-price" label="Precio base">
          <input
            className={inputClassName}
            id="admin-new-product-price"
            inputMode="decimal"
            placeholder="0.00"
            value={unitPrice}
            onChange={(event) => setUnitPrice(event.target.value)}
          />
        </Field>
        <Field id="admin-new-product-class" label="Clase / categoría">
          <select
            className={inputClassName}
            disabled={classOptions.length === 0}
            id="admin-new-product-class"
            value={productClassId}
            onChange={(event) => setProductClassId(event.target.value)}
          >
            {classOptions.length === 0 ? <option value="">Clases pendientes de API</option> : null}
            {classOptions.map((option) => (
              <option key={option.id} title={option.label} value={option.id}>
                {option.label}
              </option>
            ))}
          </select>
        </Field>
        <Field id="admin-new-product-status" label="Estado inicial">
          <select
            className={inputClassName}
            id="admin-new-product-status"
            value={status}
            onChange={(event) => setStatus(event.target.value as AdminProductStatus)}
          >
            <option value="active">Activo</option>
            <option value="inactive">Inactivo</option>
          </select>
        </Field>
        <Field id="admin-new-product-quick-name" label="Nombre corto">
          <input
            className={inputClassName}
            id="admin-new-product-quick-name"
            placeholder="Opcional"
            value={quickName}
            onChange={(event) => setQuickName(event.target.value)}
          />
        </Field>
        <Field className="md:col-span-2" id="admin-new-product-aliases" label="Alias de búsqueda">
          <input
            className={inputClassName}
            id="admin-new-product-aliases"
            placeholder="Opcional"
            value={searchAliases}
            onChange={(event) => setSearchAliases(event.target.value)}
          />
        </Field>
      </div>

      {errorMessage ? (
        <p className="mt-3 rounded-[16px] border border-rose-200 bg-[var(--ui-color-danger-soft)] px-3 py-2 text-sm font-semibold text-[var(--ui-color-danger)]">
          {errorMessage}
        </p>
      ) : null}

      <div className="mt-4 flex min-w-0 flex-wrap items-center justify-between gap-3 border-t border-[var(--ui-color-border)] pt-3">
        <p className="min-w-0 text-sm leading-5 text-slate-600">
          Disponibilidad por sucursal, recetas, costos e inventario se configuran en módulos
          relacionados cuando sus contratos estén listos.
        </p>
        <AdminActionButton
          capability="catalog.manage"
          globalOnly
          className="shrink-0 rounded-2xl bg-[var(--ui-color-info)] px-4 py-2 text-sm font-semibold text-white shadow-sm transition hover:brightness-95 focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)] disabled:cursor-not-allowed disabled:bg-slate-300 disabled:text-slate-600"
          disabled={!canSubmit}
          type="submit"
        >
          {isSubmitting ? "Guardando..." : "Guardar producto"}
        </AdminActionButton>
      </div>
    </form>
  );
}
