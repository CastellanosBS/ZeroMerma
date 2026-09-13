import { AdminActionButton } from "../../components/AdminActionButton";
import type { AdminDiscount } from "../types";

function formatMoney(value: string | null | undefined, currencyCode: string): string {
  if (!value) {
    return "N/A";
  }
  const numericValue = Number(value);
  if (!Number.isFinite(numericValue)) {
    return `${value} ${currencyCode}`;
  }
  return new Intl.NumberFormat("es-MX", { currency: currencyCode, style: "currency" }).format(
    numericValue,
  );
}

function formatValue(item: AdminDiscount): string {
  if (item.discountType === "PERCENTAGE") {
    return `${Number(item.value).toFixed(2)}%`;
  }
  return formatMoney(item.value, item.currencyCode);
}

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div className="min-w-0 border-b border-[var(--ui-color-border)] py-2 last:border-b-0">
      <p
        className="truncate text-[0.68rem] font-semibold uppercase tracking-[0.12em] text-slate-500"
        title={label}
      >
        {label}
      </p>
      <p className="mt-0.5 truncate text-sm font-semibold text-slate-950" title={value}>
        {value}
      </p>
    </div>
  );
}

function scopeLabel(item: AdminDiscount): string {
  if (item.targetScope === "PRODUCT") {
    return "Producto";
  }
  if (item.targetScope === "CLASS") {
    return "Clase";
  }
  return "Global";
}

function validityLabel(item: AdminDiscount): string {
  const labels = {
    current: "Vigente",
    expired: "Expirada",
    not_scheduled: "Sin calendario",
    upcoming: "Proxima",
  } as const;
  return labels[item.validityStatus];
}

interface AdminDiscountDetailPanelProps {
  discount?: AdminDiscount | null;
  errorMessage?: string | null;
  isLoading?: boolean;
  onEdit: (item: AdminDiscount) => void;
}

export function AdminDiscountDetailPanel({
  discount,
  errorMessage,
  isLoading = false,
  onEdit,
}: AdminDiscountDetailPanelProps) {
  return (
    <aside className="flex min-h-0 min-w-0 flex-col overflow-hidden rounded-[20px] border border-[var(--ui-color-border)] bg-slate-50/80">
      <div className="shrink-0 border-b border-[var(--ui-color-border)] px-3 py-2.5">
        <p className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">Detalle</p>
        <h3
          className="mt-1 truncate text-base font-semibold text-slate-950"
          title={discount?.name ?? "Sin descuento seleccionado"}
        >
          {discount ? discount.name : "Sin descuento seleccionado"}
        </h3>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto p-3">
        {isLoading ? (
          <article className="rounded-[16px] border border-[var(--ui-color-border)] bg-white p-3">
            <p className="text-sm font-semibold text-slate-950">Cargando detalle</p>
            <p className="mt-1 text-sm leading-5 text-slate-600">
              Consultando alcance y advertencias.
            </p>
          </article>
        ) : errorMessage ? (
          <article className="rounded-[16px] border border-rose-200 bg-[var(--ui-color-danger-soft)] p-3">
            <p className="text-sm font-semibold text-[var(--ui-color-danger)]">
              No se pudo cargar el detalle
            </p>
            <p className="mt-1 text-sm leading-5 text-slate-700">{errorMessage}</p>
          </article>
        ) : discount ? (
          <div className="grid min-w-0 gap-3">
            <section className="min-w-0 rounded-[16px] border border-[var(--ui-color-border)] bg-white px-3">
              <Field label="Codigo" value={discount.code ?? "Sin codigo"} />
              <Field
                label="Estado"
                value={
                  discount.status === "ACTIVE"
                    ? "Activo"
                    : discount.status === "INACTIVE"
                      ? "Inactivo"
                      : "Archivado"
                }
              />
              <Field label="Marca" value={discount.brandName ?? "Todas / no especificada"} />
              <Field label="Elegible POS" value={discount.isPosEligible ? "Si" : "No"} />
            </section>

            <section className="rounded-[16px] border border-[var(--ui-color-border)] bg-white p-3">
              <div className="flex min-w-0 items-center justify-between gap-2">
                <p className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">
                  Calculo
                </p>
                <AdminActionButton
                  globalOnly
                  capability="discounts.manage"
                  className="rounded-full border border-[var(--ui-color-border)] bg-white px-2.5 py-1 text-xs font-semibold text-[var(--ui-color-info)]"
                  type="button"
                  onClick={() => onEdit(discount)}
                >
                  Editar
                </AdminActionButton>
              </div>
              <p className="mt-2 text-2xl font-semibold text-slate-950">{formatValue(discount)}</p>
              <p className="mt-1 text-xs leading-5 text-slate-600">
                Precio base {formatMoney(discount.basePrice, discount.currencyCode)}. Resultado
                estimado {formatMoney(discount.previewPrice, discount.currencyCode)}.
              </p>
            </section>

            <section className="min-w-0 rounded-[16px] border border-[var(--ui-color-border)] bg-white px-3">
              <Field label="Alcance" value={scopeLabel(discount)} />
              <Field label="Objetivo" value={discount.targetName ?? "Alcance global"} />
              <Field label="Clase relacionada" value={discount.targetClassName ?? "No aplica"} />
              <Field label="Estado del objetivo" value={discount.targetStatus ?? "No aplica"} />
            </section>

            <section className="rounded-[16px] border border-[var(--ui-color-border)] bg-white p-3">
              <p className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">
                Vigencia
              </p>
              <div className="mt-2 grid grid-cols-2 gap-2 text-sm">
                <div className="rounded-[14px] bg-slate-100 px-3 py-2">
                  <p className="text-xs font-semibold text-slate-500">Estado</p>
                  <p className="font-semibold text-slate-950">{validityLabel(discount)}</p>
                </div>
                <div className="rounded-[14px] bg-slate-100 px-3 py-2">
                  <p className="text-xs font-semibold text-slate-500">Prioridad</p>
                  <p className="font-semibold text-slate-950">{discount.priority}</p>
                </div>
              </div>
              <p className="mt-2 text-xs leading-5 text-slate-600">
                {discount.validFromUtc ?? "Sin inicio"} - {discount.validToUtc ?? "Sin fin"}
              </p>
            </section>

            <section className="rounded-[16px] border border-[var(--ui-color-border)] bg-white p-3">
              <p className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">
                Advertencias
              </p>
              {discount.warnings.messages.length > 0 ? (
                <ul className="mt-2 grid gap-1.5 text-sm leading-5 text-slate-700">
                  {discount.warnings.messages.map((message) => (
                    <li
                      className="rounded-[14px] border border-amber-200 bg-[var(--ui-color-warning-soft)] px-3 py-2"
                      key={message}
                    >
                      {message}
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="mt-1 text-sm leading-5 text-slate-600">
                  Sin advertencias comerciales.
                </p>
              )}
            </section>

            <section className="rounded-[16px] border border-[var(--ui-color-border)] bg-white p-3">
              <p className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">
                Contexto relacionado
              </p>
              <div className="mt-2 grid gap-1.5 text-sm">
                <a
                  className="rounded-[14px] border border-[var(--ui-color-border)] bg-slate-50 px-3 py-2 font-semibold text-[var(--ui-color-info)]"
                  href={
                    discount.targetScope === "PRODUCT" ? "/admin/productos" : "/admin/categorias"
                  }
                >
                  Abrir {discount.targetScope === "PRODUCT" ? "Productos" : "Categorias / clases"}
                </a>
                <a
                  className="rounded-[14px] border border-[var(--ui-color-border)] bg-slate-50 px-3 py-2 font-semibold text-slate-700"
                  href="/admin/precios"
                >
                  Revisar precio base
                </a>
              </div>
            </section>
          </div>
        ) : (
          <article className="rounded-[16px] border border-dashed border-[var(--ui-color-border)] bg-white p-4">
            <p className="text-sm font-semibold text-slate-950">Sin descuento seleccionado</p>
            <p className="mt-1 text-sm leading-5 text-slate-600">
              Selecciona una fila para revisar calculo, alcance, vigencia, advertencias y contexto.
            </p>
          </article>
        )}
      </div>
    </aside>
  );
}
