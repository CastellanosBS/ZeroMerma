import type { AdminProduct, AdminProductReadinessStatus } from "../types";

const actionLabels = [
  "Editar",
  "Disponibilidad",
  "Precios",
  "Recetas/costos",
  "Auditoria",
];

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div className="min-w-0 border-b border-[var(--ui-color-border)] py-2 last:border-b-0">
      <p className="truncate text-[0.68rem] font-semibold uppercase tracking-[0.12em] text-slate-500" title={label}>
        {label}
      </p>
      <p className="mt-0.5 truncate text-sm font-semibold text-slate-950" title={value}>
        {value}
      </p>
    </div>
  );
}

function formatReadiness(value: AdminProductReadinessStatus): string {
  const labels: Record<AdminProductReadinessStatus, string> = {
    incomplete: "Incompleto",
    pending_integration: "Integracion parcial",
    ready: "Listo",
    requires_attention: "Requiere atencion",
    unknown: "Sin evaluar",
  };

  return labels[value];
}

function formatCaptureMode(product: AdminProduct): string {
  return product.captureMode === "PRODUCT_DIRECT" ? "Producto directo" : "Captura por clase";
}

function formatMoney(product: AdminProduct): string {
  const value = Number(product.unitPrice);

  if (!Number.isFinite(value)) {
    return `${product.unitPrice} ${product.currencyCode}`;
  }

  return new Intl.NumberFormat("es-MX", {
    currency: product.currencyCode,
    style: "currency",
  }).format(value);
}

interface AdminProductsDetailPanelProps {
  errorMessage?: string | null;
  isLoading?: boolean;
  product?: AdminProduct | null;
}

export function AdminProductsDetailPanel({
  errorMessage,
  isLoading = false,
  product,
}: AdminProductsDetailPanelProps) {
  return (
    <aside className="flex min-h-0 min-w-0 flex-col overflow-hidden rounded-[20px] border border-[var(--ui-color-border)] bg-slate-50/80">
      <div className="shrink-0 border-b border-[var(--ui-color-border)] px-3 py-2.5">
        <p className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">Detalle</p>
        <h3 className="mt-1 truncate text-base font-semibold text-slate-950" title={product?.name ?? "Sin producto seleccionado"}>
          {product ? product.name : "Sin producto seleccionado"}
        </h3>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto p-3">
        {isLoading ? (
          <article className="rounded-[16px] border border-[var(--ui-color-border)] bg-white p-3">
            <p className="text-sm font-semibold text-slate-950">Cargando detalle</p>
            <p className="mt-1 text-sm leading-5 text-slate-600">Consultando el producto seleccionado.</p>
          </article>
        ) : errorMessage ? (
          <article className="rounded-[16px] border border-rose-200 bg-[var(--ui-color-danger-soft)] p-3">
            <p className="text-sm font-semibold text-[var(--ui-color-danger)]">No se pudo cargar el detalle</p>
            <p className="mt-1 text-sm leading-5 text-slate-700">{errorMessage}</p>
          </article>
        ) : product ? (
          <div className="grid min-w-0 gap-3">
            <section className="min-w-0 rounded-[16px] border border-[var(--ui-color-border)] bg-white px-3">
              <Field label="Marca" value={product.brandName ?? "Sin marca"} />
              <Field label="Codigo" value={product.code ?? "Pendiente"} />
              <Field label="Estado" value={product.status === "active" ? "Activo" : "Inactivo"} />
              <Field label="Clase / modo" value={`${product.className ?? "Pendiente"} - ${formatCaptureMode(product)}`} />
              <Field label="Precio base" value={formatMoney(product)} />
            </section>

            <section className="rounded-[16px] border border-[var(--ui-color-border)] bg-white p-3">
              <p className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">Preparacion</p>
              <p className="mt-1 text-sm font-semibold text-slate-950">{formatReadiness(product.readiness.status)}</p>
              {product.readiness.missingRequirements.length > 0 ? (
                <ul className="mt-2 space-y-1 text-sm leading-5 text-slate-600">
                  {product.readiness.missingRequirements.map((requirement) => (
                    <li className="truncate" key={requirement} title={requirement}>
                      {requirement}
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="mt-1 text-sm leading-5 text-slate-600">Sin requisitos faltantes.</p>
              )}
            </section>

            <section className="grid min-w-0 gap-1.5 rounded-[16px] border border-[var(--ui-color-border)] bg-white p-3">
              <p className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">Vinculos</p>
              <div className="grid min-w-0 grid-cols-2 gap-1.5 text-xs">
                <span className="rounded-full bg-slate-100 px-2 py-1" title="Precio">
                  Precio: {formatReadiness(product.readiness.related.price)}
                </span>
                <span className="rounded-full bg-slate-100 px-2 py-1" title="Disponibilidad">
                  Sucursales: {formatReadiness(product.readiness.related.branchAvailability)}
                </span>
                <span className="rounded-full bg-slate-100 px-2 py-1" title="Inventario">
                  Inventario: {formatReadiness(product.readiness.related.inventory)}
                </span>
                <span className="rounded-full bg-slate-100 px-2 py-1" title="Receta">
                  Receta: {formatReadiness(product.readiness.related.recipe)}
                </span>
              </div>
            </section>

            <section className="rounded-[16px] border border-[var(--ui-color-border)] bg-white p-3">
              <p className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">Acciones</p>
              <div className="mt-2 flex flex-wrap gap-1.5">
                {actionLabels.map((label) => (
                  <button
                    className="h-8 rounded-full border border-[var(--ui-color-border)] bg-slate-100 px-3 text-xs font-semibold text-slate-500"
                    disabled
                    key={label}
                    title="Accion pendiente de endpoint administrativo especifico"
                    type="button"
                  >
                    {label}
                  </button>
                ))}
              </div>
            </section>
          </div>
        ) : (
          <article className="rounded-[16px] border border-dashed border-[var(--ui-color-border)] bg-white p-4">
            <p className="text-sm font-semibold text-slate-950">Sin producto seleccionado</p>
            <p className="mt-1 text-sm leading-5 text-slate-600">
              Selecciona un producto para ver detalle y acciones.
            </p>
          </article>
        )}
      </div>
    </aside>
  );
}
