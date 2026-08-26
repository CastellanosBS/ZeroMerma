import type { FormEvent, ReactNode } from "react";
import { useEffect, useMemo, useState } from "react";

import type {
  AdminProductClass,
  AdminProductClassCaptureMode,
  AdminProductClassCreatePayload,
  AdminProductClassFilterOption,
  AdminProductClassStatus,
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

interface AdminClassFormPanelProps {
  brandOptions: AdminProductClassFilterOption[];
  classItem?: AdminProductClass | null;
  errorMessage?: string | null;
  isSubmitting: boolean;
  onClose: () => void;
  onSubmit: (payload: AdminProductClassCreatePayload) => void;
}

export function AdminClassFormPanel({
  brandOptions,
  classItem,
  errorMessage,
  isSubmitting,
  onClose,
  onSubmit,
}: AdminClassFormPanelProps) {
  const isEditing = Boolean(classItem);
  const [brandId, setBrandId] = useState(classItem?.brandId ?? brandOptions[0]?.id ?? "");
  const [code, setCode] = useState(classItem?.code ?? "");
  const [name, setName] = useState(classItem?.name ?? "");
  const [quickName, setQuickName] = useState(classItem?.quickName ?? "");
  const [searchAliases, setSearchAliases] = useState(classItem?.searchAliases ?? "");
  const [captureMode, setCaptureMode] = useState<AdminProductClassCaptureMode>(
    classItem?.captureModeDefault ?? "PRODUCT_DIRECT",
  );
  const [classCaptureUnitPrice, setClassCaptureUnitPrice] = useState(
    classItem?.classCaptureUnitPrice ?? "",
  );
  const [currencyCode, setCurrencyCode] = useState(classItem?.currencyCode ?? "MXN");
  const [displayOrder, setDisplayOrder] = useState(String(classItem?.displayOrder ?? 1000));
  const [status, setStatus] = useState<AdminProductClassStatus>(classItem?.status ?? "active");
  const [isSellable, setIsSellable] = useState(classItem?.isSellable ?? true);
  const [clientError, setClientError] = useState<string | null>(null);

  useEffect(() => {
    if (brandId || !brandOptions[0]) {
      return;
    }

    setBrandId(brandOptions[0].id);
  }, [brandId, brandOptions]);

  useEffect(() => {
    if (captureMode === "PRODUCT_DIRECT") {
      setClassCaptureUnitPrice("");
    }
  }, [captureMode]);

  const canSubmit = useMemo(() => {
    const parsedOrder = Number(displayOrder);
    const hasValidOrder = Number.isInteger(parsedOrder) && parsedOrder >= 0;
    const hasValidPrice =
      captureMode === "PRODUCT_DIRECT" ||
      (classCaptureUnitPrice.trim().length > 0 && Number(classCaptureUnitPrice) >= 0);

    return (
      brandOptions.length > 0 &&
      brandId.length > 0 &&
      code.trim().length > 0 &&
      name.trim().length > 0 &&
      currencyCode.trim().length === 3 &&
      hasValidOrder &&
      hasValidPrice &&
      !isSubmitting
    );
  }, [
    brandId,
    brandOptions.length,
    captureMode,
    classCaptureUnitPrice,
    code,
    currencyCode,
    displayOrder,
    isSubmitting,
    name,
  ]);

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setClientError(null);

    if (captureMode === "CLASS_CAPTURE" && classCaptureUnitPrice.trim().length === 0) {
      setClientError("El precio de clase es obligatorio para CLASS_CAPTURE.");
      return;
    }

    if (captureMode === "PRODUCT_DIRECT" && classCaptureUnitPrice.trim().length > 0) {
      setClientError("PRODUCT_DIRECT no usa precio de clase.");
      return;
    }

    const parsedOrder = Number(displayOrder);
    if (!Number.isInteger(parsedOrder) || parsedOrder < 0) {
      setClientError("El orden debe ser un entero no negativo.");
      return;
    }

    if (!canSubmit) {
      return;
    }

    onSubmit({
      brandId,
      captureModeDefault: captureMode,
      classCaptureUnitPrice: captureMode === "CLASS_CAPTURE" ? classCaptureUnitPrice.trim() : null,
      code: code.trim(),
      currencyCode: currencyCode.trim().toUpperCase(),
      displayOrder: parsedOrder,
      isSellable,
      name: name.trim(),
      quickName: quickName.trim() || null,
      searchAliases: searchAliases.trim() || null,
      status,
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
            Gobierno de catalogo
          </p>
          <h3 className="mt-1 truncate text-base font-semibold text-slate-950" title={isEditing ? "Editar clase" : "Nueva clase"}>
            {isEditing ? "Editar clase" : "Nueva clase"}
          </h3>
          <p className="mt-1 max-w-4xl text-sm leading-5 text-slate-600">
            Define identidad, modo de captura POS, precio de clase cuando aplica y visibilidad operativa.
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
        <Field className="md:col-span-2" id="admin-class-name" label="Nombre">
          <input
            className={inputClassName}
            id="admin-class-name"
            placeholder="Nombre de la clase"
            value={name}
            onChange={(event) => setName(event.target.value)}
          />
        </Field>
        <Field id="admin-class-code" label="Codigo">
          <input
            className={inputClassName}
            id="admin-class-code"
            placeholder="Codigo unico"
            value={code}
            onChange={(event) => setCode(event.target.value)}
          />
        </Field>
        <Field id="admin-class-brand" label="Marca">
          <select
            className={inputClassName}
            disabled={brandOptions.length === 0}
            id="admin-class-brand"
            value={brandId}
            onChange={(event) => setBrandId(event.target.value)}
          >
            {brandOptions.length === 0 ? <option value="">Marcas pendientes de API</option> : null}
            {brandOptions.map((option) => (
              <option key={option.id} title={option.label} value={option.id}>
                {option.label}
              </option>
            ))}
          </select>
        </Field>
        <Field id="admin-class-capture-mode" label="Modo POS">
          <select
            className={inputClassName}
            id="admin-class-capture-mode"
            value={captureMode}
            onChange={(event) => setCaptureMode(event.target.value as AdminProductClassCaptureMode)}
          >
            <option value="PRODUCT_DIRECT">Producto directo</option>
            <option value="CLASS_CAPTURE">Captura por clase</option>
          </select>
        </Field>
        <Field id="admin-class-price" label="Precio de clase">
          <input
            className={inputClassName}
            disabled={captureMode === "PRODUCT_DIRECT"}
            id="admin-class-price"
            inputMode="decimal"
            placeholder={captureMode === "PRODUCT_DIRECT" ? "No aplica" : "0.00"}
            value={classCaptureUnitPrice}
            onChange={(event) => setClassCaptureUnitPrice(event.target.value)}
          />
        </Field>
        <Field id="admin-class-currency" label="Moneda">
          <input
            className={inputClassName}
            id="admin-class-currency"
            maxLength={3}
            value={currencyCode}
            onChange={(event) => setCurrencyCode(event.target.value.toUpperCase())}
          />
        </Field>
        <Field id="admin-class-display-order" label="Orden">
          <input
            className={inputClassName}
            id="admin-class-display-order"
            inputMode="numeric"
            value={displayOrder}
            onChange={(event) => setDisplayOrder(event.target.value)}
          />
        </Field>
        <Field id="admin-class-status" label="Estado">
          <select
            className={inputClassName}
            id="admin-class-status"
            value={status}
            onChange={(event) => setStatus(event.target.value as AdminProductClassStatus)}
          >
            <option value="active">Activa</option>
            <option value="inactive">Inactiva</option>
          </select>
        </Field>
        <Field id="admin-class-sellable" label="Vendible">
          <select
            className={inputClassName}
            id="admin-class-sellable"
            value={isSellable ? "yes" : "no"}
            onChange={(event) => setIsSellable(event.target.value === "yes")}
          >
            <option value="yes">Vendible</option>
            <option value="no">No vendible</option>
          </select>
        </Field>
        <Field id="admin-class-quick-name" label="Nombre corto">
          <input
            className={inputClassName}
            id="admin-class-quick-name"
            placeholder="Opcional"
            value={quickName}
            onChange={(event) => setQuickName(event.target.value)}
          />
        </Field>
        <Field className="md:col-span-2" id="admin-class-aliases" label="Alias de busqueda">
          <input
            className={inputClassName}
            id="admin-class-aliases"
            placeholder="Opcional"
            value={searchAliases}
            onChange={(event) => setSearchAliases(event.target.value)}
          />
        </Field>
      </div>

      {clientError || errorMessage ? (
        <p className="mt-3 rounded-[16px] border border-rose-200 bg-[var(--ui-color-danger-soft)] px-3 py-2 text-sm font-semibold text-[var(--ui-color-danger)]">
          {clientError ?? errorMessage}
        </p>
      ) : null}

      <div className="mt-4 flex min-w-0 flex-wrap items-center justify-between gap-3 border-t border-[var(--ui-color-border)] pt-3">
        <p className="min-w-0 text-sm leading-5 text-slate-600">
          Los productos vinculados se administran en Productos. Recetas, costos y listas de precio viven en sus modulos.
        </p>
        <button
          className="shrink-0 rounded-2xl bg-[var(--ui-color-info)] px-4 py-2 text-sm font-semibold text-white shadow-sm transition hover:brightness-95 focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)] disabled:cursor-not-allowed disabled:bg-slate-300 disabled:text-slate-600"
          disabled={!canSubmit}
          type="submit"
        >
          {isSubmitting ? "Guardando..." : isEditing ? "Guardar cambios" : "Guardar clase"}
        </button>
      </div>
    </form>
  );
}
