import { AdminActionButton } from "../../components/AdminActionButton";
import type { AdminProductClass, AdminProductClassReadinessStatus } from "../types";

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

function formatCaptureMode(item: AdminProductClass): string {
  return item.captureModeDefault === "PRODUCT_DIRECT" ? "Producto directo" : "Captura por clase";
}

function formatReadiness(value: AdminProductClassReadinessStatus): string {
  const labels: Record<AdminProductClassReadinessStatus, string> = {
    incomplete: "Incompleta",
    pending_integration: "Integracion parcial",
    ready: "Lista para operar",
    requires_attention: "Requiere revision",
    unknown: "Sin evaluar",
  };

  return labels[value];
}

function formatMoney(value: string | null | undefined, currencyCode: string): string {
  if (!value) {
    return "No aplica";
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

interface AdminClassesDetailPanelProps {
  classItem?: AdminProductClass | null;
  errorMessage?: string | null;
  isLoading?: boolean;
  onEdit?: (item: AdminProductClass) => void;
}

export function AdminClassesDetailPanel({
  classItem,
  errorMessage,
  isLoading = false,
  onEdit,
}: AdminClassesDetailPanelProps) {
  return (
    <aside className="flex min-h-0 min-w-0 flex-col overflow-hidden rounded-[20px] border border-[var(--ui-color-border)] bg-slate-50/80">
      <div className="shrink-0 border-b border-[var(--ui-color-border)] px-3 py-2.5">
        <p className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">Detalle</p>
        <h3
          className="mt-1 truncate text-base font-semibold text-slate-950"
          title={classItem?.name ?? "Sin clase seleccionada"}
        >
          {classItem ? classItem.name : "Sin clase seleccionada"}
        </h3>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto p-3">
        {isLoading ? (
          <article className="rounded-[16px] border border-[var(--ui-color-border)] bg-white p-3">
            <p className="text-sm font-semibold text-slate-950">Cargando detalle</p>
            <p className="mt-1 text-sm leading-5 text-slate-600">
              Consultando la clase seleccionada.
            </p>
          </article>
        ) : errorMessage ? (
          <article className="rounded-[16px] border border-rose-200 bg-[var(--ui-color-danger-soft)] p-3">
            <p className="text-sm font-semibold text-[var(--ui-color-danger)]">
              No se pudo cargar el detalle
            </p>
            <p className="mt-1 text-sm leading-5 text-slate-700">{errorMessage}</p>
          </article>
        ) : classItem ? (
          <div className="grid min-w-0 gap-3">
            <section className="min-w-0 rounded-[16px] border border-[var(--ui-color-border)] bg-white px-3">
              <Field label="Marca" value={classItem.brandName} />
              <Field label="Codigo" value={classItem.code} />
              <Field label="Nombre corto" value={classItem.quickName ?? "Pendiente"} />
              <Field label="Alias de busqueda" value={classItem.searchAliases ?? "Pendiente"} />
            </section>

            <section className="min-w-0 rounded-[16px] border border-[var(--ui-color-border)] bg-white px-3">
              <Field label="Modo POS" value={formatCaptureMode(classItem)} />
              <Field
                label="Precio de clase"
                value={formatMoney(classItem.classCaptureUnitPrice, classItem.currencyCode)}
              />
              <Field label="Orden" value={String(classItem.displayOrder)} />
              <Field
                label="Visibilidad"
                value={`${classItem.status === "active" ? "Activa" : "Inactiva"} - ${
                  classItem.isSellable ? "Vendible" : "No vendible"
                }`}
              />
            </section>

            <section className="rounded-[16px] border border-[var(--ui-color-border)] bg-white p-3">
              <div className="flex min-w-0 items-center justify-between gap-2">
                <p className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">
                  Productos
                </p>
                <a
                  className="shrink-0 rounded-full border border-[var(--ui-color-border)] bg-white px-2.5 py-1 text-xs font-semibold text-[var(--ui-color-info)] transition hover:bg-[var(--ui-color-surface-tint)] focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
                  href={`/admin/productos?class_id=${classItem.id}`}
                >
                  Abrir productos
                </a>
              </div>
              <p className="mt-1 text-sm font-semibold text-slate-950">
                {classItem.productCount} productos asociados
              </p>
              <p className="text-xs text-slate-500">
                {classItem.activeProductCount} activos - {classItem.inactiveProductCount} inactivos
              </p>
              {classItem.linkedProducts.length > 0 ? (
                <div className="mt-2 grid gap-1.5">
                  {classItem.linkedProducts.map((product) => (
                    <div
                      className="flex min-w-0 items-center justify-between gap-2 rounded-[14px] border border-[var(--ui-color-border)] bg-slate-50 px-2 py-1.5 text-xs"
                      key={product.id}
                    >
                      <span
                        className="min-w-0 truncate font-semibold text-slate-800"
                        title={product.name}
                      >
                        {product.name}
                      </span>
                      <span className="shrink-0 text-slate-500">
                        {product.status === "active" ? "Activo" : "Inactivo"}
                      </span>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="mt-2 rounded-[14px] border border-dashed border-[var(--ui-color-border)] bg-slate-50 px-3 py-2 text-sm text-slate-600">
                  Esta clase todavia no tiene productos vinculados.
                </p>
              )}
            </section>

            <section className="rounded-[16px] border border-[var(--ui-color-border)] bg-white p-3">
              <p className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">
                Salud operativa
              </p>
              <p className="mt-1 text-sm font-semibold text-slate-950">
                {formatReadiness(classItem.readiness)}
              </p>
              {classItem.warnings.messages.length > 0 ? (
                <ul className="mt-2 grid gap-1.5 text-sm leading-5 text-slate-700">
                  {classItem.warnings.messages.map((message) => (
                    <li
                      className="rounded-[14px] border border-amber-200 bg-[var(--ui-color-warning-soft)] px-3 py-2"
                      key={message}
                      title={message}
                    >
                      {message}
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="mt-1 text-sm leading-5 text-slate-600">
                  Sin advertencias de configuracion.
                </p>
              )}
            </section>

            <section className="rounded-[16px] border border-[var(--ui-color-border)] bg-white p-3">
              <p className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">
                Historial
              </p>
              <p className="mt-1 text-sm leading-5 text-slate-600">
                Auditoria disponible en backend para cambios de catalogo. La vista de historial
                detallado queda preparada para el endpoint administrativo de auditoria.
              </p>
            </section>

            {onEdit ? (
              <AdminActionButton
                globalOnly
                capability="catalog.manage"
                className="h-10 rounded-2xl bg-[var(--ui-color-primary)] px-4 text-sm font-semibold text-white shadow-sm transition hover:bg-[var(--ui-color-primary-strong)] focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
                type="button"
                onClick={() => onEdit(classItem)}
              >
                Editar clase
              </AdminActionButton>
            ) : null}
          </div>
        ) : (
          <article className="rounded-[16px] border border-dashed border-[var(--ui-color-border)] bg-white p-4">
            <p className="text-sm font-semibold text-slate-950">Sin clase seleccionada</p>
            <p className="mt-1 text-sm leading-5 text-slate-600">
              Selecciona una clase para revisar comportamiento POS, productos vinculados y
              advertencias.
            </p>
          </article>
        )}
      </div>
    </aside>
  );
}
