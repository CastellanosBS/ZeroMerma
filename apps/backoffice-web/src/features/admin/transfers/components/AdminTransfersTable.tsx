import { AdminActionButton } from "../../components/AdminActionButton";
import { AdminEmptyState } from "../../components/AdminEmptyState";
import type {
  AdminTransferBackendContract,
  AdminTransferListItem,
  AdminTransferStatus,
  AdminTransferWarningSeverity,
} from "../types";

function formatStatus(status: AdminTransferStatus): string {
  const labels: Record<AdminTransferStatus, string> = {
    CANCELLED: "Cancelada",
    DRAFT: "Borrador",
    IN_TRANSIT: "En transito",
    RECEIVED: "Recibida",
    RECEIVED_WITH_VARIANCE: "Recibida con diferencia",
  };

  return labels[status];
}

function formatDate(value: string | null | undefined): string {
  if (!value) {
    return "Pendiente";
  }

  return new Intl.DateTimeFormat("es-MX", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function statusTone(status: AdminTransferStatus): "critical" | "neutral" | "success" | "warning" {
  if (status === "CANCELLED" || status === "RECEIVED_WITH_VARIANCE") {
    return "critical";
  }
  if (status === "DRAFT" || status === "IN_TRANSIT") {
    return "warning";
  }
  return "success";
}

function warningTone(severity: AdminTransferWarningSeverity | null | undefined) {
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

interface AdminTransfersTableProps {
  backendContract: AdminTransferBackendContract;
  errorMessage?: string | null;
  isLoading?: boolean;
  isSubmitting?: boolean;
  onCancel: (item: AdminTransferListItem) => void;
  onDispatch: (item: AdminTransferListItem) => void;
  onOpenBranch: (branchId: string) => void;
  onPageChange: (page: number) => void;
  onReceive: (item: AdminTransferListItem) => void;
  onSelectTransfer: (item: AdminTransferListItem) => void;
  page: number;
  pageSize: number;
  selectedTransferId?: string | null;
  total: number;
  transfers: AdminTransferListItem[];
}

export function AdminTransfersTable({
  backendContract,
  errorMessage,
  isLoading = false,
  isSubmitting = false,
  onCancel,
  onDispatch,
  onOpenBranch,
  onPageChange,
  onReceive,
  onSelectTransfer,
  page,
  pageSize,
  selectedTransferId,
  total,
  transfers,
}: AdminTransfersTableProps) {
  const totalPages = Math.max(1, Math.ceil(total / pageSize));
  const canGoPrevious = page > 1;
  const canGoNext = page < totalPages;

  return (
    <section className="flex min-h-0 min-w-0 flex-col overflow-hidden rounded-[20px] border border-[var(--ui-color-border)] bg-white">
      <div className="flex min-w-0 shrink-0 items-center justify-between gap-3 border-b border-[var(--ui-color-border)] px-3 py-2.5">
        <div className="min-w-0">
          <h3
            className="truncate text-base font-semibold text-slate-950"
            title="Transferencias multisucursal"
          >
            Transferencias multisucursal
          </h3>
          <p className="truncate text-xs text-slate-500">
            Envios, recepciones, diferencias y trazabilidad entre sucursales.
          </p>
        </div>
        <span className="shrink-0 rounded-full border border-[var(--ui-color-border)] bg-white px-3 py-1 text-xs font-semibold text-slate-600">
          {total} registros
        </span>
      </div>

      <div className="min-h-0 min-w-0 flex-1 overflow-y-auto p-2.5">
        {isLoading ? (
          <AdminEmptyState
            description="Consultando transferencias reales del backend."
            title="Cargando transferencias"
          />
        ) : errorMessage ? (
          <AdminEmptyState description={errorMessage} title="No se pudo cargar transferencias" />
        ) : transfers.length > 0 ? (
          <div className="grid min-w-0 gap-1.5">
            {transfers.map((item) => {
              const isSelected = item.id === selectedTransferId;
              const warningLabel =
                item.warnings.length > 0 ? `${item.warnings.length} alertas` : "Sin alertas";

              return (
                <article
                  className={[
                    "grid min-w-0 gap-2 rounded-[16px] border px-3 py-2 transition xl:grid-cols-[minmax(8rem,0.65fr)_minmax(0,1fr)_minmax(0,1fr)_minmax(8rem,0.75fr)_minmax(7rem,0.55fr)_auto]",
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
                    onClick={() => onSelectTransfer(item)}
                  >
                    <span className="block truncate font-mono text-sm font-semibold text-slate-950">
                      {item.folio}
                    </span>
                    <span className="mt-0.5 block truncate text-xs text-slate-500">
                      {formatDate(item.createdAt)}
                    </span>
                  </button>

                  <button
                    className="min-w-0 text-left focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
                    title={`${item.originBranchName} - ${item.originBranchCode}`}
                    type="button"
                    onClick={() => onSelectTransfer(item)}
                  >
                    <span className="block truncate text-sm font-semibold text-slate-900">
                      {item.originBranchName}
                    </span>
                    <span className="mt-0.5 block truncate text-xs text-slate-500">
                      Origen {item.originBranchCode}
                    </span>
                  </button>

                  <button
                    className="min-w-0 text-left focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
                    title={`${item.destinationBranchName} - ${item.destinationBranchCode}`}
                    type="button"
                    onClick={() => onSelectTransfer(item)}
                  >
                    <span className="block truncate text-sm font-semibold text-slate-900">
                      {item.destinationBranchName}
                    </span>
                    <span className="mt-0.5 block truncate text-xs text-slate-500">
                      Destino {item.destinationBranchCode}
                    </span>
                  </button>

                  <button
                    className="min-w-0 text-left focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
                    title={`Envio: ${formatDate(item.dispatchedAt)}. Recepcion: ${formatDate(item.receivedAt)}`}
                    type="button"
                    onClick={() => onSelectTransfer(item)}
                  >
                    <span className="block truncate text-sm font-semibold text-slate-900">
                      {formatDate(item.dispatchedAt)}
                    </span>
                    <span className="mt-0.5 block truncate text-xs text-slate-500">
                      Recepcion {formatDate(item.receivedAt)}
                    </span>
                  </button>

                  <button
                    className="min-w-0 text-left xl:text-right focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
                    title={`${item.lineCount} lineas - ${item.sentUnitCount} enviadas - ${item.receivedUnitCount ?? "0"} recibidas`}
                    type="button"
                    onClick={() => onSelectTransfer(item)}
                  >
                    <span className="block truncate text-sm font-semibold text-slate-950">
                      {item.lineCount} lineas
                    </span>
                    <span className="mt-0.5 block truncate text-xs text-slate-500">
                      {item.sentUnitCount} / {item.receivedUnitCount ?? "0"}
                    </span>
                  </button>

                  <div className="flex min-w-0 flex-col gap-1.5 xl:items-end">
                    <div className="flex min-w-0 flex-wrap gap-1.5 xl:justify-end">
                      <StatusChip tone={statusTone(item.status)}>
                        {formatStatus(item.status)}
                      </StatusChip>
                      {item.hasDiscrepancy ? (
                        <StatusChip tone="critical">Con discrepancia</StatusChip>
                      ) : null}
                      <StatusChip tone={warningTone(item.warningState)}>{warningLabel}</StatusChip>
                    </div>
                    <div className="flex min-w-0 flex-wrap gap-1.5 text-xs xl:justify-end">
                      <button
                        className="rounded-full border border-[var(--ui-color-border)] bg-white px-2 py-1 font-semibold text-slate-600 transition hover:bg-slate-50 focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
                        type="button"
                        onClick={() => onOpenBranch(item.originBranchId)}
                      >
                        Origen
                      </button>
                      <button
                        className="rounded-full border border-[var(--ui-color-border)] bg-white px-2 py-1 font-semibold text-slate-600 transition hover:bg-slate-50 focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
                        type="button"
                        onClick={() => onOpenBranch(item.destinationBranchId)}
                      >
                        Destino
                      </button>
                      {item.status === "DRAFT" ? (
                        <AdminActionButton
                          capability="transfers.execute"
                          branchIds={[item.originBranchId, item.destinationBranchId]}
                          className="rounded-full border border-[var(--ui-color-border)] bg-white px-2 py-1 font-semibold text-[var(--ui-color-info)] transition hover:bg-[var(--ui-color-surface-tint)] focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)] disabled:cursor-not-allowed disabled:bg-slate-100 disabled:text-slate-400"
                          disabled={isSubmitting}
                          type="button"
                          onClick={() => onDispatch(item)}
                        >
                          Enviar
                        </AdminActionButton>
                      ) : null}
                      {item.status === "IN_TRANSIT" ? (
                        <AdminActionButton
                          capability="transfers.execute"
                          branchIds={[item.originBranchId, item.destinationBranchId]}
                          className="rounded-full border border-[var(--ui-color-border)] bg-white px-2 py-1 font-semibold text-[var(--ui-color-info)] transition hover:bg-[var(--ui-color-surface-tint)] focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)] disabled:cursor-not-allowed disabled:bg-slate-100 disabled:text-slate-400"
                          disabled={isSubmitting}
                          type="button"
                          onClick={() => onReceive(item)}
                        >
                          Recibir
                        </AdminActionButton>
                      ) : null}
                      {item.status === "DRAFT" ? (
                        <AdminActionButton
                          capability="transfers.cancel"
                          branchIds={[item.originBranchId, item.destinationBranchId]}
                          className="rounded-full border border-[var(--ui-color-border)] bg-white px-2 py-1 font-semibold text-slate-600 transition hover:bg-slate-50 focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)] disabled:cursor-not-allowed disabled:bg-slate-100 disabled:text-slate-400"
                          disabled={isSubmitting}
                          type="button"
                          onClick={() => onCancel(item)}
                        >
                          Cancelar
                        </AdminActionButton>
                      ) : null}
                    </div>
                  </div>
                </article>
              );
            })}
          </div>
        ) : (
          <div className="grid gap-2">
            <AdminEmptyState
              description="No hay transferencias para los filtros seleccionados."
              title="Sin transferencias"
            />
            <p className="rounded-[16px] border border-[var(--ui-color-border)] bg-slate-50 px-3 py-2 text-xs leading-5 text-slate-600">
              Contrato activo: {backendContract.listEndpoint}. Las transferencias aparecen cuando
              existen documentos persistidos en backend.
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
