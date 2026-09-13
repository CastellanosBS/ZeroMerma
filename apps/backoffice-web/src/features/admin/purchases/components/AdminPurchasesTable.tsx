import { AdminActionButton } from "../../components/AdminActionButton";
import { AdminEmptyState } from "../../components/AdminEmptyState";
import type {
  AdminPurchaseBackendContract,
  AdminPurchaseListItem,
  AdminPurchaseStatus,
  AdminPurchaseType,
  AdminPurchaseWarningSeverity,
} from "../types";

function formatDate(value: string | null | undefined): string {
  if (!value) {
    return "Sin registro";
  }
  return new Intl.DateTimeFormat("es-MX", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function formatStatus(status: AdminPurchaseStatus): string {
  const labels: Record<AdminPurchaseStatus, string> = {
    CANCELLED: "Cancelada",
    DRAFT: "Borrador",
    ORDERED: "Pendiente",
    PARTIALLY_RECEIVED: "Parcial",
    RECEIVED: "Recibida",
  };
  return labels[status];
}

function formatType(type: AdminPurchaseType): string {
  return type === "DIRECT_ENTRY" ? "Entrada directa" : "Compra";
}

function statusTone(status: AdminPurchaseStatus): "critical" | "neutral" | "success" | "warning" {
  if (status === "CANCELLED") {
    return "neutral";
  }
  if (status === "RECEIVED") {
    return "success";
  }
  if (status === "DRAFT" || status === "ORDERED" || status === "PARTIALLY_RECEIVED") {
    return "warning";
  }
  return "neutral";
}

function warningTone(severity: AdminPurchaseWarningSeverity | null | undefined) {
  if (severity === "critical") {
    return "critical";
  }
  if (severity === "warning") {
    return "warning";
  }
  return "neutral";
}

function StatusChip({
  children,
  tone = "neutral",
}: {
  children: string;
  tone?: "critical" | "neutral" | "success" | "warning";
}) {
  const toneClass = {
    critical: "border-rose-200 bg-[var(--ui-color-danger-soft)] text-[var(--ui-color-danger)]",
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

interface AdminPurchasesTableProps {
  backendContract: AdminPurchaseBackendContract;
  errorMessage?: string | null;
  isLoading?: boolean;
  isSubmitting?: boolean;
  onCancel: (item: AdminPurchaseListItem) => void;
  onConfirm: (item: AdminPurchaseListItem) => void;
  onOpenBranch: (branchId: string) => void;
  onOpenSupplier: (supplierId: string) => void;
  onPageChange: (page: number) => void;
  onReceive: (item: AdminPurchaseListItem) => void;
  onSelectPurchase: (item: AdminPurchaseListItem) => void;
  page: number;
  pageSize: number;
  purchases: AdminPurchaseListItem[];
  selectedPurchaseId?: string | null;
  total: number;
}

export function AdminPurchasesTable({
  backendContract,
  errorMessage,
  isLoading = false,
  isSubmitting = false,
  onCancel,
  onConfirm,
  onOpenBranch,
  onOpenSupplier,
  onPageChange,
  onReceive,
  onSelectPurchase,
  page,
  pageSize,
  purchases,
  selectedPurchaseId,
  total,
}: AdminPurchasesTableProps) {
  const totalPages = Math.max(1, Math.ceil(total / pageSize));
  const canGoPrevious = page > 1;
  const canGoNext = page < totalPages;

  return (
    <section className="flex min-h-0 min-w-0 flex-col overflow-hidden rounded-[20px] border border-[var(--ui-color-border)] bg-white">
      <div className="flex min-w-0 shrink-0 items-center justify-between gap-3 border-b border-[var(--ui-color-border)] px-3 py-2.5">
        <div className="min-w-0">
          <h3
            className="truncate text-base font-semibold text-slate-950"
            title="Compras y entradas"
          >
            Compras y entradas
          </h3>
          <p className="truncate text-xs text-slate-500">
            Recepciones auditadas con proveedor, sucursal, costo e impacto de inventario.
          </p>
        </div>
        <span className="shrink-0 rounded-full border border-[var(--ui-color-border)] bg-white px-3 py-1 text-xs font-semibold text-slate-600">
          {total} documentos
        </span>
      </div>

      <div className="min-h-0 min-w-0 flex-1 overflow-y-auto p-2.5">
        {isLoading ? (
          <AdminEmptyState
            description="Consultando compras y entradas del backend."
            title="Cargando compras"
          />
        ) : errorMessage ? (
          <AdminEmptyState description={errorMessage} title="No se pudieron cargar compras" />
        ) : purchases.length > 0 ? (
          <div className="grid min-w-0 gap-1.5">
            {purchases.map((item) => {
              const isSelected = item.id === selectedPurchaseId;
              const warningLabel =
                item.warnings.length > 0 ? `${item.warnings.length} alertas` : "Sin alertas";

              return (
                <article
                  className={[
                    "grid min-w-0 gap-2 rounded-[16px] border px-3 py-2 transition xl:grid-cols-[minmax(9rem,0.8fr)_minmax(0,1fr)_minmax(0,0.85fr)_minmax(8rem,0.72fr)_minmax(8rem,0.7fr)_auto]",
                    isSelected
                      ? "border-[var(--ui-color-info)] bg-[var(--ui-color-info-soft)]"
                      : "border-[var(--ui-color-border)] bg-white hover:bg-slate-50",
                  ].join(" ")}
                  key={item.id}
                >
                  <button
                    className="min-w-0 text-left focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
                    title={item.folio}
                    type="button"
                    onClick={() => onSelectPurchase(item)}
                  >
                    <span className="block truncate font-mono text-sm font-semibold text-slate-950">
                      {item.folio}
                    </span>
                    <span className="mt-0.5 block truncate text-xs text-slate-500">
                      {formatType(item.documentType)}
                    </span>
                  </button>

                  <button
                    className="min-w-0 text-left focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
                    title={item.supplierName}
                    type="button"
                    onClick={() => onSelectPurchase(item)}
                  >
                    <span className="block truncate text-sm font-semibold text-slate-950">
                      {item.supplierName}
                    </span>
                    <span className="mt-0.5 block truncate text-xs text-slate-500">
                      {item.externalDocumentNumber ?? "Sin documento externo"}
                    </span>
                  </button>

                  <button
                    className="min-w-0 text-left focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
                    title={item.branchName}
                    type="button"
                    onClick={() => onSelectPurchase(item)}
                  >
                    <span className="block truncate text-sm font-semibold text-slate-800">
                      {item.branchName}
                    </span>
                    <span className="mt-0.5 block truncate text-xs text-slate-500">
                      {formatDate(item.documentDate)}
                    </span>
                  </button>

                  <button
                    className="min-w-0 text-left xl:text-right focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
                    title={`${item.lineCount} lineas, ${item.receivedUnitCount} recibidas`}
                    type="button"
                    onClick={() => onSelectPurchase(item)}
                  >
                    <span className="block truncate text-sm font-semibold text-slate-950">
                      {item.receivedUnitCount}
                    </span>
                    <span className="mt-0.5 block truncate text-xs text-slate-500">
                      {item.lineCount} lineas
                    </span>
                  </button>

                  <button
                    className="min-w-0 text-left xl:text-right focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
                    title={item.totalAmount}
                    type="button"
                    onClick={() => onSelectPurchase(item)}
                  >
                    <span className="block truncate text-sm font-semibold text-slate-950">
                      {item.totalAmount}
                    </span>
                    <span className="mt-0.5 block truncate text-xs text-slate-500">Monto</span>
                  </button>

                  <div className="flex min-w-0 flex-col gap-1.5 xl:items-end">
                    <div className="flex min-w-0 flex-wrap gap-1.5 xl:justify-end">
                      <StatusChip tone={statusTone(item.status)}>
                        {formatStatus(item.status)}
                      </StatusChip>
                      <StatusChip tone={warningTone(item.warningState)}>{warningLabel}</StatusChip>
                      {item.hasDiscrepancy ? (
                        <StatusChip tone="critical">Discrepancia</StatusChip>
                      ) : null}
                    </div>
                    <div className="flex min-w-0 flex-wrap gap-1.5 text-xs xl:justify-end">
                      {item.status === "DRAFT" ? (
                        <AdminActionButton
                          capability="purchases.confirm"
                          branchIds={[item.branchId]}
                          className="rounded-full border border-[var(--ui-color-border)] bg-white px-2 py-1 font-semibold text-slate-600 transition hover:bg-slate-50 focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)] disabled:cursor-not-allowed disabled:bg-slate-100 disabled:text-slate-400"
                          disabled={isSubmitting}
                          type="button"
                          onClick={() => onConfirm(item)}
                        >
                          Confirmar
                        </AdminActionButton>
                      ) : null}
                      {item.status === "DRAFT" ||
                      item.status === "ORDERED" ||
                      item.status === "PARTIALLY_RECEIVED" ? (
                        <AdminActionButton
                          capability="purchases.receive"
                          branchIds={[item.branchId]}
                          className="rounded-full border border-[var(--ui-color-border)] bg-white px-2 py-1 font-semibold text-slate-600 transition hover:bg-slate-50 focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)] disabled:cursor-not-allowed disabled:bg-slate-100 disabled:text-slate-400"
                          disabled={isSubmitting}
                          type="button"
                          onClick={() => onReceive(item)}
                        >
                          Recibir
                        </AdminActionButton>
                      ) : null}
                      {item.status === "DRAFT" || item.status === "ORDERED" ? (
                        <AdminActionButton
                          capability="purchases.cancel"
                          branchIds={[item.branchId]}
                          className="rounded-full border border-[var(--ui-color-border)] bg-white px-2 py-1 font-semibold text-slate-600 transition hover:bg-slate-50 focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)] disabled:cursor-not-allowed disabled:bg-slate-100 disabled:text-slate-400"
                          disabled={isSubmitting}
                          type="button"
                          onClick={() => onCancel(item)}
                        >
                          Cancelar
                        </AdminActionButton>
                      ) : null}
                      <button
                        className="rounded-full border border-[var(--ui-color-border)] bg-white px-2 py-1 font-semibold text-slate-600 transition hover:bg-slate-50 focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
                        type="button"
                        onClick={() => onOpenSupplier(item.supplierId)}
                      >
                        Proveedor
                      </button>
                      <button
                        className="rounded-full border border-[var(--ui-color-border)] bg-white px-2 py-1 font-semibold text-slate-600 transition hover:bg-slate-50 focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
                        type="button"
                        onClick={() => onOpenBranch(item.branchId)}
                      >
                        Sucursal
                      </button>
                    </div>
                  </div>
                </article>
              );
            })}
          </div>
        ) : (
          <div className="grid gap-2">
            <AdminEmptyState
              description="No hay compras o entradas para los filtros seleccionados."
              title="Sin compras registradas"
            />
            <p className="rounded-[16px] border border-[var(--ui-color-border)] bg-slate-50 px-3 py-2 text-xs leading-5 text-slate-600">
              Contrato activo: {backendContract.listEndpoint}. Las entradas aparecen cuando se
              guardan documentos de compra o recepciones directas en el backend.
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
