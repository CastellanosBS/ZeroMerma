import { AdminEmptyState } from "../../components/AdminEmptyState";
import type { AdminReconciliationListItem } from "../types";

function formatMoney(value: string | null | undefined): string {
  if (!value) {
    return "N/A";
  }
  const numericValue = Number(value);
  if (!Number.isFinite(numericValue)) {
    return `${value} MXN`;
  }
  return new Intl.NumberFormat("es-MX", { currency: "MXN", style: "currency" }).format(
    numericValue,
  );
}

function formatDateTime(value: string | null | undefined): string {
  if (!value) {
    return "Pendiente";
  }
  return new Intl.DateTimeFormat("es-MX", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function statusLabel(value: string): string {
  const labels: Record<string, string> = {
    IN_REVIEW: "En revision",
    PENDING: "Pendiente",
    RECONCILED: "Conciliada",
    VOIDED: "Anulada",
  };
  return labels[value] ?? value;
}

function sourceLabel(value: string): string {
  const labels: Record<string, string> = {
    CASH_CUT: "Corte de caja",
    CORRECTION: "Correccion",
    DEPOSIT: "Deposito",
    OPERATIONAL_PAYMENT: "Pago operativo",
    PAYMENT_SETTLEMENT: "Pago terminal",
    RETURN_REFUND: "Devolucion",
  };
  return labels[value] ?? value;
}

function statusClass(value: string): string {
  if (value === "RECONCILED") {
    return "border-emerald-200 bg-[var(--ui-color-success-soft)] text-[var(--ui-color-success)]";
  }
  if (value === "VOIDED") {
    return "border-slate-200 bg-slate-100 text-slate-500";
  }
  return "border-amber-200 bg-[var(--ui-color-warning-soft)] text-[var(--ui-color-warning)]";
}

function differenceClass(value: string): string {
  const numericValue = Number(value);
  if (numericValue > 0) {
    return "text-[var(--ui-color-success)]";
  }
  if (numericValue < 0) {
    return "text-[var(--ui-color-danger)]";
  }
  return "text-slate-950";
}

interface AdminReconciliationTableProps {
  errorMessage?: string | null;
  isLoading?: boolean;
  onCopyFolio: (item: AdminReconciliationListItem) => void;
  onPageChange: (page: number) => void;
  onResolve: (item: AdminReconciliationListItem) => void;
  onSelectReconciliation: (item: AdminReconciliationListItem) => void;
  page: number;
  pageSize: number;
  reconciliations: AdminReconciliationListItem[];
  selectedReconciliationId?: string | null;
  total: number;
}

export function AdminReconciliationTable({
  errorMessage,
  isLoading = false,
  onCopyFolio,
  onPageChange,
  onResolve,
  onSelectReconciliation,
  page,
  pageSize,
  reconciliations,
  selectedReconciliationId,
  total,
}: AdminReconciliationTableProps) {
  const totalPages = Math.max(1, Math.ceil(total / pageSize));
  const canGoPrevious = page > 1;
  const canGoNext = page < totalPages;

  return (
    <section className="flex min-h-0 min-w-0 flex-col overflow-hidden rounded-[20px] border border-[var(--ui-color-border)] bg-white">
      <div className="flex min-w-0 shrink-0 items-center justify-between gap-3 border-b border-[var(--ui-color-border)] px-3 py-2.5">
        <div className="min-w-0">
          <h3 className="truncate text-base font-semibold text-slate-950">Conciliaciones</h3>
          <p className="truncate text-xs text-slate-500">
            Folio, origen, metodo, esperado, reportado, diferencia, estado y evidencia.
          </p>
        </div>
        <span className="shrink-0 rounded-full border border-[var(--ui-color-border)] bg-white px-3 py-1 text-xs font-semibold text-slate-600">
          {total} registros
        </span>
      </div>

      <div className="min-h-0 min-w-0 flex-1 overflow-y-auto p-2.5">
        {isLoading ? (
          <AdminEmptyState
            description="Consultando conciliaciones financieras persistidas."
            title="Cargando conciliaciones"
          />
        ) : errorMessage ? (
          <AdminEmptyState
            description={errorMessage}
            title="No se pudieron cargar las conciliaciones"
          />
        ) : reconciliations.length > 0 ? (
          <div className="grid min-w-0 gap-1.5">
            {reconciliations.map((item) => {
              const isSelected = item.id === selectedReconciliationId;
              return (
                <article
                  className={[
                    "grid min-w-0 gap-2 rounded-[16px] border px-3 py-2 transition xl:grid-cols-[minmax(7rem,0.7fr)_minmax(8rem,0.7fr)_minmax(0,1fr)_minmax(0,0.85fr)_repeat(3,minmax(6.5rem,0.55fr))_minmax(6rem,0.5fr)_auto]",
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
                    onClick={() => onSelectReconciliation(item)}
                  >
                    <span className="block truncate text-sm font-semibold text-slate-950">
                      {item.folio}
                    </span>
                    <span className="mt-0.5 block truncate text-xs text-slate-500">
                      {formatDateTime(item.occurredAt)}
                    </span>
                  </button>

                  <button
                    className="min-w-0 text-left focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
                    type="button"
                    onClick={() => onSelectReconciliation(item)}
                  >
                    <span className="block truncate text-sm font-semibold text-slate-950">
                      {sourceLabel(item.sourceType)}
                    </span>
                    <span className="mt-0.5 block truncate text-xs text-slate-500">
                      {item.sourceReference}
                    </span>
                  </button>

                  <button
                    className="min-w-0 text-left focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
                    type="button"
                    onClick={() => onSelectReconciliation(item)}
                  >
                    <span className="block truncate text-sm font-semibold text-slate-950">
                      {item.branchName}
                    </span>
                    <span className="mt-0.5 block truncate text-xs text-slate-500">
                      {item.workstationName}
                    </span>
                  </button>

                  <button
                    className="min-w-0 text-left focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
                    type="button"
                    onClick={() => onSelectReconciliation(item)}
                  >
                    <span className="block truncate text-sm font-semibold text-slate-950">
                      {item.operatorName}
                    </span>
                    <span className="mt-0.5 block truncate text-xs text-slate-500">
                      {item.paymentMethod}
                    </span>
                  </button>

                  <button
                    className="min-w-0 text-left xl:text-right focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
                    type="button"
                    onClick={() => onSelectReconciliation(item)}
                  >
                    <span className="block truncate text-sm font-semibold text-slate-950">
                      {formatMoney(item.expectedAmount)}
                    </span>
                    <span className="mt-0.5 block truncate text-xs text-slate-500">Esperado</span>
                  </button>

                  <button
                    className="min-w-0 text-left xl:text-right focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
                    type="button"
                    onClick={() => onSelectReconciliation(item)}
                  >
                    <span className="block truncate text-sm font-semibold text-slate-950">
                      {formatMoney(item.actualAmount)}
                    </span>
                    <span className="mt-0.5 block truncate text-xs text-slate-500">Reportado</span>
                  </button>

                  <button
                    className="min-w-0 text-left xl:text-right focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
                    type="button"
                    onClick={() => onSelectReconciliation(item)}
                  >
                    <span
                      className={`block truncate text-sm font-semibold ${differenceClass(
                        item.differenceAmount,
                      )}`}
                    >
                      {formatMoney(item.differenceAmount)}
                    </span>
                    <span className="mt-0.5 block truncate text-xs text-slate-500">Diferencia</span>
                  </button>

                  <div className="flex min-w-0 items-center gap-1.5">
                    <span
                      className={`inline-flex min-w-0 rounded-full border px-2.5 py-1 text-xs font-semibold ${statusClass(item.status)}`}
                      title={statusLabel(item.status)}
                    >
                      <span className="truncate">{statusLabel(item.status)}</span>
                    </span>
                    <span
                      className="inline-flex min-w-0 rounded-full border border-[var(--ui-color-border)] bg-slate-50 px-2.5 py-1 text-xs font-semibold text-slate-600"
                      title={item.hasEvidence ? "Con evidencia" : "Sin evidencia"}
                    >
                      {item.hasEvidence ? "Evidencia" : "Sin evidencia"}
                    </span>
                  </div>

                  <div className="flex min-w-0 items-center justify-end gap-1.5">
                    <button
                      className="rounded-full border border-[var(--ui-color-border)] bg-white px-2.5 py-1 text-xs font-semibold text-slate-700 transition hover:border-[var(--ui-color-info)] hover:text-[var(--ui-color-info)] focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
                      type="button"
                      onClick={() => onSelectReconciliation(item)}
                    >
                      Ver
                    </button>
                    <button
                      className="rounded-full border border-[var(--ui-color-border)] bg-white px-2.5 py-1 text-xs font-semibold text-slate-700 transition hover:border-[var(--ui-color-info)] hover:text-[var(--ui-color-info)] focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)] disabled:cursor-not-allowed disabled:opacity-40"
                      disabled={item.status === "RECONCILED"}
                      type="button"
                      onClick={() => onResolve(item)}
                    >
                      Resolver
                    </button>
                    <button
                      className="rounded-full border border-[var(--ui-color-border)] bg-white px-2.5 py-1 text-xs font-semibold text-slate-700 transition hover:border-[var(--ui-color-info)] hover:text-[var(--ui-color-info)] focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
                      type="button"
                      onClick={() => onCopyFolio(item)}
                    >
                      Copiar
                    </button>
                  </div>
                </article>
              );
            })}
          </div>
        ) : (
          <AdminEmptyState
            description="No hay conciliaciones para los filtros seleccionados."
            title="Sin conciliaciones"
          />
        )}
      </div>

      <div className="flex shrink-0 items-center justify-between gap-3 border-t border-[var(--ui-color-border)] px-3 py-2 text-xs text-slate-500">
        <span>
          Pagina {page} de {totalPages}
        </span>
        <div className="flex items-center gap-2">
          <button
            className="rounded-full border border-[var(--ui-color-border)] bg-white px-3 py-1.5 font-semibold text-slate-700 disabled:cursor-not-allowed disabled:opacity-40"
            disabled={!canGoPrevious}
            type="button"
            onClick={() => onPageChange(page - 1)}
          >
            Anterior
          </button>
          <button
            className="rounded-full border border-[var(--ui-color-border)] bg-white px-3 py-1.5 font-semibold text-slate-700 disabled:cursor-not-allowed disabled:opacity-40"
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
