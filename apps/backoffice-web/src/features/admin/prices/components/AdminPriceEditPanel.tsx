import type { FormEvent } from "react";
import { useEffect, useState } from "react";

import type { AdminPriceRow, AdminPriceUpdatePayload } from "../types";

function formatOwner(item: AdminPriceRow): string {
  return item.priceOwner === "product_unit_price" ? "Product.unit_price" : "ProductClass.class_capture_unit_price";
}

interface AdminPriceEditPanelProps {
  errorMessage?: string | null;
  isSubmitting?: boolean;
  onClose: () => void;
  onSubmit: (payload: AdminPriceUpdatePayload) => void;
  price: AdminPriceRow;
}

export function AdminPriceEditPanel({
  errorMessage,
  isSubmitting = false,
  onClose,
  onSubmit,
  price,
}: AdminPriceEditPanelProps) {
  const [amount, setAmount] = useState(price.currentPrice ?? "0.00");
  const [formError, setFormError] = useState<string | null>(null);

  useEffect(() => {
    setAmount(price.currentPrice ?? "0.00");
    setFormError(null);
  }, [price.entityId, price.entityType, price.currentPrice]);

  function submitForm(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const numericAmount = Number(amount);
    if (!Number.isFinite(numericAmount) || numericAmount < 0) {
      setFormError("Ingresa un precio valido mayor o igual a cero.");
      return;
    }

    onSubmit({ price: numericAmount.toFixed(2) });
  }

  return (
    <section className="shrink-0 overflow-hidden rounded-[20px] border border-[var(--ui-color-border)] bg-white">
      <div className="flex min-w-0 items-start justify-between gap-3 border-b border-[var(--ui-color-border)] px-4 py-3">
        <div className="min-w-0">
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">Editar precio</p>
          <h3 className="mt-1 truncate text-base font-semibold text-slate-950" title={price.entityName}>
            {price.entityName}
          </h3>
          <p className="mt-1 truncate text-xs text-slate-500" title={formatOwner(price)}>
            Fuente canonica: {formatOwner(price)}
          </p>
        </div>
        <button
          className="rounded-full border border-[var(--ui-color-border)] bg-white px-3 py-1 text-xs font-semibold text-slate-600 transition hover:bg-slate-50 focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
          type="button"
          onClick={onClose}
        >
          Cerrar
        </button>
      </div>

      <form className="grid gap-3 p-4" onSubmit={submitForm}>
        <label className="grid min-w-0 gap-1 text-xs font-semibold uppercase tracking-[0.1em] text-slate-500" htmlFor="admin-price-amount">
          Precio vigente
          <div className="grid grid-cols-[auto_minmax(0,1fr)_auto] items-center overflow-hidden rounded-2xl border border-[var(--ui-color-border)] bg-white focus-within:border-[var(--ui-color-info)] focus-within:ring-4 focus-within:ring-[var(--ui-color-ring)]">
            <span className="px-3 text-sm font-semibold text-slate-500">$</span>
            <input
              className="h-11 min-w-0 border-0 bg-transparent px-2 text-right text-lg font-semibold text-slate-950 outline-none"
              id="admin-price-amount"
              inputMode="decimal"
              min="0"
              step="0.01"
              type="number"
              value={amount}
              onChange={(event) => {
                setAmount(event.target.value);
                setFormError(null);
              }}
            />
            <span className="px-3 text-xs font-semibold text-slate-500">{price.currencyCode}</span>
          </div>
        </label>

        <p className="rounded-[16px] border border-[var(--ui-color-border)] bg-slate-50 px-3 py-2 text-xs leading-5 text-slate-600">
          {price.captureMode === "PRODUCT_DIRECT"
            ? "Este precio se guardara en el producto directo."
            : "Este precio se guardara en la clase CLASS_CAPTURE."}
        </p>

        {formError || errorMessage ? (
          <p className="rounded-[16px] border border-rose-200 bg-[var(--ui-color-danger-soft)] px-3 py-2 text-sm font-semibold text-[var(--ui-color-danger)]">
            {formError ?? errorMessage}
          </p>
        ) : null}

        <div className="flex min-w-0 justify-end gap-2">
          <button
            className="h-10 rounded-2xl border border-[var(--ui-color-border)] bg-white px-4 text-sm font-semibold text-slate-700 transition hover:bg-slate-50 focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
            type="button"
            onClick={onClose}
          >
            Cancelar
          </button>
          <button
            className="h-10 rounded-2xl bg-[var(--ui-color-primary)] px-4 text-sm font-semibold text-white transition hover:bg-[var(--ui-color-primary-strong)] focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)] disabled:cursor-not-allowed disabled:bg-slate-300"
            disabled={isSubmitting}
            type="submit"
          >
            {isSubmitting ? "Guardando..." : "Guardar precio"}
          </button>
        </div>
      </form>
    </section>
  );
}
