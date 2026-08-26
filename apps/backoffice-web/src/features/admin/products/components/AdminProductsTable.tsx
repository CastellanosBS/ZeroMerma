import { AdminEmptyState } from "../../components/AdminEmptyState";
import type { AdminProduct, AdminProductBackendContract } from "../types";

function formatStatus(status: AdminProduct["status"]): string {
  return status === "active" ? "Activo" : "Inactivo";
}

function formatCaptureMode(captureMode: AdminProduct["captureMode"]): string {
  return captureMode === "PRODUCT_DIRECT" ? "Producto directo" : "Captura por clase";
}

function formatReadiness(status: AdminProduct["readiness"]["status"]): string {
  const labels: Record<AdminProduct["readiness"]["status"], string> = {
    incomplete: "Incompleto",
    pending_integration: "Integracion parcial",
    ready: "Listo",
    requires_attention: "Requiere atencion",
    unknown: "Sin evaluar",
  };

  return labels[status];
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

function formatDate(value: string | null | undefined): string {
  if (!value) {
    return "Sin fecha";
  }

  return new Intl.DateTimeFormat("es-MX", {
    dateStyle: "medium",
  }).format(new Date(value));
}

function StatusChip({
  children,
  tone = "neutral",
}: {
  children: string;
  tone?: "neutral" | "success" | "warning";
}) {
  const toneClass = {
    neutral: "border-[var(--ui-color-border)] bg-white text-slate-600",
    success: "border-emerald-200 bg-[var(--ui-color-success-soft)] text-[var(--ui-color-success)]",
    warning: "border-amber-200 bg-[var(--ui-color-warning-soft)] text-[var(--ui-color-warning)]",
  }[tone];

  return (
    <span
      className={`max-w-full truncate rounded-full border px-2 py-0.5 text-[0.72rem] font-semibold ${toneClass}`}
      title={children}
    >
      {children}
    </span>
  );
}

interface AdminProductsTableProps {
  backendContract: AdminProductBackendContract;
  errorMessage?: string | null;
  isLoading?: boolean;
  onPageChange: (page: number) => void;
  onSelectProduct: (product: AdminProduct) => void;
  page: number;
  pageSize: number;
  products: AdminProduct[];
  selectedProductId?: string | null;
  total: number;
}

export function AdminProductsTable({
  backendContract,
  errorMessage,
  isLoading = false,
  onPageChange,
  onSelectProduct,
  page,
  pageSize,
  products,
  selectedProductId,
  total,
}: AdminProductsTableProps) {
  const totalPages = Math.max(1, Math.ceil(total / pageSize));
  const canGoPrevious = page > 1;
  const canGoNext = page < totalPages;

  return (
    <section className="flex min-h-0 min-w-0 flex-col overflow-hidden rounded-[20px] border border-[var(--ui-color-border)] bg-white">
      <div className="flex min-w-0 shrink-0 items-center justify-between gap-3 border-b border-[var(--ui-color-border)] px-3 py-2.5">
        <div className="min-w-0">
          <h3 className="truncate text-base font-semibold text-slate-950" title="Catalogo maestro">
            Catalogo maestro
          </h3>
        </div>
        <span className="shrink-0 rounded-full border border-[var(--ui-color-border)] bg-white px-3 py-1 text-xs font-semibold text-slate-600">
          {total} registros
        </span>
      </div>

      <div className="min-h-0 min-w-0 flex-1 overflow-y-auto p-2.5">
        {isLoading ? (
          <AdminEmptyState
            description="Consultando el catalogo administrativo de productos."
            title="Cargando productos"
          />
        ) : errorMessage ? (
          <AdminEmptyState
            description={errorMessage}
            title="No se pudieron cargar los productos"
          />
        ) : products.length > 0 ? (
          <div className="grid min-w-0 gap-1.5">
            {products.map((product) => {
              const isSelected = product.id === selectedProductId;
              const readinessTone =
                product.readiness.status === "ready"
                  ? "success"
                  : product.readiness.status === "pending_integration" || product.readiness.status === "unknown"
                    ? "neutral"
                    : "warning";

              return (
                <button
                  className={[
                    "grid min-w-0 gap-2 rounded-[16px] border px-3 py-2 text-left transition focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)] lg:grid-cols-[minmax(0,1.4fr)_minmax(0,1fr)_minmax(8.25rem,auto)_minmax(6.5rem,auto)]",
                    isSelected
                      ? "border-[var(--ui-color-info)] bg-[var(--ui-color-info-soft)]"
                      : "border-[var(--ui-color-border)] bg-white hover:bg-slate-50",
                  ].join(" ")}
                  key={product.id}
                  title={product.name}
                  type="button"
                  onClick={() => onSelectProduct(product)}
                >
                  <span className="min-w-0">
                    <span className="block truncate text-sm font-semibold text-slate-950">{product.name}</span>
                    <span className="mt-0.5 flex min-w-0 items-center gap-1.5 text-xs text-slate-500">
                      <span className="truncate" title={product.code ?? "Sin codigo"}>
                        {product.code ?? "Sin codigo"}
                      </span>
                      <span aria-hidden="true">-</span>
                      <span className="truncate" title={product.brandName ?? "Sin marca"}>
                        {product.brandName ?? "Sin marca"}
                      </span>
                    </span>
                  </span>

                  <span className="min-w-0">
                    <span className="block truncate text-sm font-semibold text-slate-800" title={product.className ?? "Sin clase"}>
                      {product.className ?? "Sin clase"}
                    </span>
                    <span className="mt-0.5 block truncate text-xs text-slate-500" title={formatCaptureMode(product.captureMode)}>
                      {formatCaptureMode(product.captureMode)}
                    </span>
                  </span>

                  <span className="flex min-w-0 flex-wrap items-start gap-1.5 lg:justify-end">
                    <StatusChip tone={product.status === "active" ? "success" : "neutral"}>
                      {formatStatus(product.status)}
                    </StatusChip>
                    <StatusChip tone={readinessTone}>{formatReadiness(product.readiness.status)}</StatusChip>
                  </span>

                  <span className="min-w-0 text-left lg:text-right">
                    <span className="block truncate text-sm font-semibold text-slate-950" title={formatMoney(product)}>
                      {formatMoney(product)}
                    </span>
                    <span className="mt-0.5 block truncate text-xs text-slate-500" title={product.updatedAt ?? "Sin fecha"}>
                      {formatDate(product.updatedAt)}
                    </span>
                  </span>
                </button>
              );
            })}
          </div>
        ) : (
          <div className="grid gap-2">
            <AdminEmptyState
              description="Aqui se mostrara el catalogo cuando existan productos que coincidan con el alcance y los filtros seleccionados."
              title="Sin productos registrados"
            />
            <p className="rounded-[16px] border border-[var(--ui-color-border)] bg-slate-50 px-3 py-2 text-xs leading-5 text-slate-600">
              Contrato activo: {backendContract.listEndpoint}.
            </p>
          </div>
        )}
      </div>

      <div className="flex min-w-0 shrink-0 flex-wrap items-center justify-between gap-2 border-t border-[var(--ui-color-border)] px-3 py-2 text-xs text-slate-500">
        <span className="truncate">
          Pagina {page} de {totalPages} - {pageSize} por pagina
        </span>
        <div className="flex items-center gap-2">
          <button
            className="rounded-full border border-[var(--ui-color-border)] bg-white px-3 py-1 font-semibold text-slate-700 transition hover:bg-slate-50 focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)] disabled:cursor-not-allowed disabled:bg-slate-100 disabled:text-slate-400"
            disabled={!canGoPrevious}
            type="button"
            onClick={() => onPageChange(page - 1)}
          >
            Anterior
          </button>
          <button
            className="rounded-full border border-[var(--ui-color-border)] bg-white px-3 py-1 font-semibold text-slate-700 transition hover:bg-slate-50 focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)] disabled:cursor-not-allowed disabled:bg-slate-100 disabled:text-slate-400"
            disabled={!canGoNext}
            type="button"
            onClick={() => onPageChange(page + 1)}
          >
            Siguiente
          </button>
        </div>
      </div>
    </section>
  );
}
