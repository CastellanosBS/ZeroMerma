import { AdminActionButton } from "../../components/AdminActionButton";
import type { AdminPriceDetail, AdminPriceRow } from "../types";

function formatMoney(value: string | null | undefined, currencyCode: string): string {
  if (!value) {
    return "Pendiente";
  }

  const numericValue = Number(value);
  if (!Number.isFinite(numericValue)) {
    return `${value} ${currencyCode}`;
  }

  return new Intl.NumberFormat("es-MX", {
    currency: currencyCode,
    style: "currency",
  }).format(numericValue);
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

function formatOwner(item: AdminPriceRow): string {
  return item.priceOwner === "product_unit_price"
    ? "Product unit_price"
    : "Class class_capture_unit_price";
}

function formatCaptureMode(item: AdminPriceRow): string {
  return item.captureMode === "PRODUCT_DIRECT" ? "PRODUCT_DIRECT" : "CLASS_CAPTURE";
}

function marginText(item: AdminPriceRow): string {
  if (!item.marginPercent) {
    return "No aplica";
  }

  return `${Number(item.marginPercent).toFixed(1)}%`;
}

interface AdminPriceDetailPanelProps {
  detail?: AdminPriceDetail | null;
  errorMessage?: string | null;
  isLoading?: boolean;
  onEditPrice: (item: AdminPriceRow) => void;
}

export function AdminPriceDetailPanel({
  detail,
  errorMessage,
  isLoading = false,
  onEditPrice,
}: AdminPriceDetailPanelProps) {
  const item = detail?.price ?? null;

  return (
    <aside className="flex min-h-0 min-w-0 flex-col overflow-hidden rounded-[20px] border border-[var(--ui-color-border)] bg-slate-50/80">
      <div className="shrink-0 border-b border-[var(--ui-color-border)] px-3 py-2.5">
        <p className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">Detalle</p>
        <h3
          className="mt-1 truncate text-base font-semibold text-slate-950"
          title={item?.entityName ?? "Sin precio seleccionado"}
        >
          {item ? item.entityName : "Sin precio seleccionado"}
        </h3>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto p-3">
        {isLoading ? (
          <article className="rounded-[16px] border border-[var(--ui-color-border)] bg-white p-3">
            <p className="text-sm font-semibold text-slate-950">Cargando detalle</p>
            <p className="mt-1 text-sm leading-5 text-slate-600">
              Consultando propietario y salud comercial.
            </p>
          </article>
        ) : errorMessage ? (
          <article className="rounded-[16px] border border-rose-200 bg-[var(--ui-color-danger-soft)] p-3">
            <p className="text-sm font-semibold text-[var(--ui-color-danger)]">
              No se pudo cargar el detalle
            </p>
            <p className="mt-1 text-sm leading-5 text-slate-700">{errorMessage}</p>
          </article>
        ) : item ? (
          <div className="grid min-w-0 gap-3">
            <section className="min-w-0 rounded-[16px] border border-[var(--ui-color-border)] bg-white px-3">
              <Field
                label="Entidad"
                value={`${item.entityCode} - ${item.entityType === "product" ? "Producto" : "Clase"}`}
              />
              <Field label="Clase" value={item.className} />
              <Field label="Modo de captura" value={formatCaptureMode(item)} />
              <Field label="Estado" value={item.status === "active" ? "Activo" : "Inactivo"} />
            </section>

            <section className="rounded-[16px] border border-[var(--ui-color-border)] bg-white p-3">
              <div className="flex min-w-0 items-center justify-between gap-2">
                <p className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">
                  Precio vigente
                </p>
                <AdminActionButton
                  globalOnly
                  capability="pricing.manage"
                  className="rounded-full border border-[var(--ui-color-border)] bg-white px-2.5 py-1 text-xs font-semibold text-[var(--ui-color-info)]"
                  type="button"
                  onClick={() => onEditPrice(item)}
                >
                  Editar
                </AdminActionButton>
              </div>
              <p className="mt-2 text-2xl font-semibold text-slate-950">
                {formatMoney(item.currentPrice, item.currencyCode)}
              </p>
              <p className="mt-1 text-xs leading-5 text-slate-600">
                Fuente: {formatOwner(item)}. La edicion se guarda en el propietario real del precio.
              </p>
            </section>

            <section className="rounded-[16px] border border-[var(--ui-color-border)] bg-white p-3">
              <p className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">
                Comparacion costo/precio
              </p>
              <div className="mt-2 grid grid-cols-2 gap-2 text-sm">
                <div className="rounded-[14px] bg-slate-100 px-3 py-2">
                  <p className="text-xs font-semibold text-slate-500">Costo estandar</p>
                  <p className="font-semibold text-slate-950">
                    {formatMoney(item.standardCost, item.currencyCode)}
                  </p>
                </div>
                <div className="rounded-[14px] bg-slate-100 px-3 py-2">
                  <p className="text-xs font-semibold text-slate-500">Margen</p>
                  <p className="font-semibold text-slate-950">{marginText(item)}</p>
                </div>
              </div>
            </section>

            <section className="rounded-[16px] border border-[var(--ui-color-border)] bg-white p-3">
              <p className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">
                Advertencias
              </p>
              {item.warnings.messages.length > 0 ? (
                <ul className="mt-2 grid gap-1.5 text-sm leading-5 text-slate-700">
                  {item.warnings.messages.map((message) => (
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
                  href={item.entityType === "product" ? `/admin/productos` : `/admin/categorias`}
                >
                  Abrir {item.entityType === "product" ? "Productos" : "Categorias / clases"}
                </a>
                <a
                  className="rounded-[14px] border border-[var(--ui-color-border)] bg-slate-50 px-3 py-2 font-semibold text-slate-700"
                  href={
                    item.relatedProductId
                      ? `/admin/recetas-costos?product_id=${item.relatedProductId}`
                      : "/admin/recetas-costos"
                  }
                >
                  Revisar recetas y costos
                </a>
              </div>
            </section>

            <section className="rounded-[16px] border border-[var(--ui-color-border)] bg-white p-3">
              <p className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">
                Historial
              </p>
              <p className="mt-1 text-sm leading-5 text-slate-600">
                {detail?.historyNote ??
                  "El historial se consulta desde auditoria cuando este disponible."}
              </p>
            </section>
          </div>
        ) : (
          <article className="rounded-[16px] border border-dashed border-[var(--ui-color-border)] bg-white p-4">
            <p className="text-sm font-semibold text-slate-950">Sin precio seleccionado</p>
            <p className="mt-1 text-sm leading-5 text-slate-600">
              Selecciona una fila para revisar propietario del precio, margen, advertencias y
              acciones.
            </p>
          </article>
        )}
      </div>
    </aside>
  );
}
