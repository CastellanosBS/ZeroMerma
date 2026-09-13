import { AdminActionButton } from "../../components/AdminActionButton";
import type { FormEvent, ReactNode } from "react";
import { useMemo, useState } from "react";

import type {
  AdminDiscount,
  AdminDiscountFilterOption,
  AdminDiscountSavePayload,
  AdminDiscountScope,
  AdminDiscountStatus,
  AdminDiscountType,
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

function toDateTimeLocal(value: string | null | undefined): string {
  if (!value) {
    return "";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "";
  }
  return date.toISOString().slice(0, 16);
}

function toIsoOrNull(value: string): string | null {
  if (!value.trim()) {
    return null;
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return null;
  }
  return date.toISOString();
}

interface AdminDiscountFormPanelProps {
  brandOptions: AdminDiscountFilterOption[];
  classOptions: AdminDiscountFilterOption[];
  discount?: AdminDiscount | null;
  errorMessage?: string | null;
  isSubmitting: boolean;
  onClose: () => void;
  onSubmit: (payload: AdminDiscountSavePayload) => void;
  productOptions: AdminDiscountFilterOption[];
}

export function AdminDiscountFormPanel({
  brandOptions,
  classOptions,
  discount,
  errorMessage,
  isSubmitting,
  onClose,
  onSubmit,
  productOptions,
}: AdminDiscountFormPanelProps) {
  const isEditing = Boolean(discount);
  const [name, setName] = useState(discount?.name ?? "");
  const [code, setCode] = useState(discount?.code ?? "");
  const [description, setDescription] = useState(discount?.description ?? "");
  const [discountType, setDiscountType] = useState<AdminDiscountType>(
    discount?.discountType ?? "PERCENTAGE",
  );
  const [targetScope, setTargetScope] = useState<AdminDiscountScope>(
    discount?.targetScope ?? "PRODUCT",
  );
  const [targetId, setTargetId] = useState(discount?.targetId ?? "");
  const [brandId, setBrandId] = useState(discount?.brandId ?? "");
  const [value, setValue] = useState(discount?.value ?? "");
  const [currencyCode, setCurrencyCode] = useState(discount?.currencyCode ?? "MXN");
  const [status, setStatus] = useState<AdminDiscountStatus>(discount?.status ?? "INACTIVE");
  const [validFromUtc, setValidFromUtc] = useState(toDateTimeLocal(discount?.validFromUtc));
  const [validToUtc, setValidToUtc] = useState(toDateTimeLocal(discount?.validToUtc));
  const [priority, setPriority] = useState(String(discount?.priority ?? 1000));
  const [isPosEligible, setIsPosEligible] = useState(discount?.isPosEligible ?? true);
  const [clientError, setClientError] = useState<string | null>(null);

  const targetOptions =
    targetScope === "CLASS" ? classOptions : targetScope === "PRODUCT" ? productOptions : [];
  const canSubmit = useMemo(() => {
    const numericValue = Number(value);
    const numericPriority = Number(priority);
    const requiresTarget = targetScope !== "GLOBAL";
    return (
      name.trim().length > 0 &&
      Number.isFinite(numericValue) &&
      numericValue > 0 &&
      (discountType !== "PERCENTAGE" || numericValue <= 100) &&
      Number.isInteger(numericPriority) &&
      numericPriority >= 0 &&
      currencyCode.trim().length === 3 &&
      (!requiresTarget || targetId.length > 0) &&
      !isSubmitting
    );
  }, [currencyCode, discountType, isSubmitting, name, priority, targetId, targetScope, value]);

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setClientError(null);
    const numericValue = Number(value);
    const numericPriority = Number(priority);
    const from = toIsoOrNull(validFromUtc);
    const to = toIsoOrNull(validToUtc);

    if (!Number.isFinite(numericValue) || numericValue <= 0) {
      setClientError("El valor del descuento debe ser mayor a cero.");
      return;
    }
    if (discountType === "PERCENTAGE" && numericValue > 100) {
      setClientError("El porcentaje no puede ser mayor a 100.");
      return;
    }
    if (targetScope !== "GLOBAL" && !targetId) {
      setClientError("Selecciona el producto o clase objetivo.");
      return;
    }
    if (from && to && new Date(from) >= new Date(to)) {
      setClientError("La vigencia debe terminar despues de iniciar.");
      return;
    }
    if (!Number.isInteger(numericPriority) || numericPriority < 0) {
      setClientError("La prioridad debe ser un entero no negativo.");
      return;
    }
    if (!canSubmit) {
      return;
    }

    onSubmit({
      brandId: targetScope === "GLOBAL" ? brandId || null : null,
      code: code.trim() || null,
      currencyCode: currencyCode.trim().toUpperCase(),
      description: description.trim() || null,
      discountType,
      isPosEligible,
      name: name.trim(),
      priority: numericPriority,
      status,
      targetId: targetScope === "GLOBAL" ? null : targetId,
      targetScope,
      validFromUtc: from,
      validToUtc: to,
      value: numericValue.toFixed(4),
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
            Gobierno comercial
          </p>
          <h3
            className="mt-1 truncate text-base font-semibold text-slate-950"
            title={isEditing ? "Editar descuento" : "Nuevo descuento"}
          >
            {isEditing ? "Editar descuento" : "Nuevo descuento"}
          </h3>
          <p className="mt-1 max-w-4xl text-sm leading-5 text-slate-600">
            Define una regla comercial. El precio base se mantiene en Precios; aqui solo vive la
            reduccion.
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
        <Field className="md:col-span-2" id="admin-discount-name" label="Nombre">
          <input
            className={inputClassName}
            id="admin-discount-name"
            placeholder="Nombre del descuento"
            value={name}
            onChange={(event) => setName(event.target.value)}
          />
        </Field>
        <Field id="admin-discount-code" label="Codigo">
          <input
            className={inputClassName}
            id="admin-discount-code"
            placeholder="Opcional"
            value={code}
            onChange={(event) => setCode(event.target.value)}
          />
        </Field>
        <Field id="admin-discount-status" label="Estado">
          <select
            className={inputClassName}
            id="admin-discount-status"
            value={status}
            onChange={(event) => setStatus(event.target.value as AdminDiscountStatus)}
          >
            <option value="ACTIVE">Activo</option>
            <option value="INACTIVE">Inactivo</option>
            <option value="ARCHIVED">Archivado</option>
          </select>
        </Field>
        <Field id="admin-discount-type" label="Tipo">
          <select
            className={inputClassName}
            id="admin-discount-type"
            value={discountType}
            onChange={(event) => setDiscountType(event.target.value as AdminDiscountType)}
          >
            <option value="PERCENTAGE">Porcentaje</option>
            <option value="FIXED_AMOUNT">Monto fijo</option>
          </select>
        </Field>
        <Field id="admin-discount-value" label="Valor">
          <input
            className={inputClassName}
            id="admin-discount-value"
            inputMode="decimal"
            placeholder={discountType === "PERCENTAGE" ? "10.00" : "15.00"}
            value={value}
            onChange={(event) => setValue(event.target.value)}
          />
        </Field>
        <Field id="admin-discount-currency" label="Moneda">
          <input
            className={inputClassName}
            id="admin-discount-currency"
            maxLength={3}
            value={currencyCode}
            onChange={(event) => setCurrencyCode(event.target.value.toUpperCase())}
          />
        </Field>
        <Field id="admin-discount-scope" label="Alcance">
          <select
            className={inputClassName}
            id="admin-discount-scope"
            value={targetScope}
            onChange={(event) => {
              setTargetScope(event.target.value as AdminDiscountScope);
              setTargetId("");
            }}
          >
            <option value="PRODUCT">Producto</option>
            <option value="CLASS">Clase</option>
            <option value="GLOBAL">Global</option>
          </select>
        </Field>
        <Field id="admin-discount-target" label="Objetivo">
          <select
            className={inputClassName}
            disabled={targetScope === "GLOBAL"}
            id="admin-discount-target"
            value={targetScope === "GLOBAL" ? "" : targetId}
            onChange={(event) => setTargetId(event.target.value)}
          >
            <option value="">{targetScope === "GLOBAL" ? "No aplica" : "Seleccionar"}</option>
            {targetOptions.map((option) => (
              <option key={option.id} title={option.label} value={option.id}>
                {option.label}
              </option>
            ))}
          </select>
        </Field>
        <Field id="admin-discount-brand" label="Marca global">
          <select
            className={inputClassName}
            disabled={targetScope !== "GLOBAL"}
            id="admin-discount-brand"
            value={targetScope === "GLOBAL" ? brandId : ""}
            onChange={(event) => setBrandId(event.target.value)}
          >
            <option value="">Todas / no especificada</option>
            {brandOptions.map((option) => (
              <option key={option.id} title={option.label} value={option.id}>
                {option.label}
              </option>
            ))}
          </select>
        </Field>
        <Field id="admin-discount-valid-from" label="Desde">
          <input
            className={inputClassName}
            id="admin-discount-valid-from"
            type="datetime-local"
            value={validFromUtc}
            onChange={(event) => setValidFromUtc(event.target.value)}
          />
        </Field>
        <Field id="admin-discount-valid-to" label="Hasta">
          <input
            className={inputClassName}
            id="admin-discount-valid-to"
            type="datetime-local"
            value={validToUtc}
            onChange={(event) => setValidToUtc(event.target.value)}
          />
        </Field>
        <Field id="admin-discount-priority" label="Prioridad">
          <input
            className={inputClassName}
            id="admin-discount-priority"
            inputMode="numeric"
            value={priority}
            onChange={(event) => setPriority(event.target.value)}
          />
        </Field>
        <Field id="admin-discount-pos" label="Elegible POS">
          <select
            className={inputClassName}
            id="admin-discount-pos"
            value={isPosEligible ? "yes" : "no"}
            onChange={(event) => setIsPosEligible(event.target.value === "yes")}
          >
            <option value="yes">Si</option>
            <option value="no">No</option>
          </select>
        </Field>
        <Field className="md:col-span-2" id="admin-discount-description" label="Descripcion">
          <input
            className={inputClassName}
            id="admin-discount-description"
            placeholder="Opcional"
            value={description}
            onChange={(event) => setDescription(event.target.value)}
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
          Los descuentos reducen el precio base; no editan precios, recetas ni historial de tickets.
        </p>
        <AdminActionButton
          capability="discounts.manage"
          globalOnly
          className="shrink-0 rounded-2xl bg-[var(--ui-color-info)] px-4 py-2 text-sm font-semibold text-white shadow-sm transition hover:brightness-95 focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)] disabled:cursor-not-allowed disabled:bg-slate-300 disabled:text-slate-600"
          disabled={!canSubmit}
          type="submit"
        >
          {isSubmitting ? "Guardando..." : isEditing ? "Guardar cambios" : "Guardar descuento"}
        </AdminActionButton>
      </div>
    </form>
  );
}
