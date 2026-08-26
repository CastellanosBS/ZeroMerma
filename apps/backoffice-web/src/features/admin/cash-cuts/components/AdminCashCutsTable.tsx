import { AdminEmptyState } from "../../components/AdminEmptyState";
import type { AdminCashCutListItem } from "../types";

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

function formatDateTime(value: string | null): string {
  if (!value) {
    return "Pendiente";
  }
  return new Intl.DateTimeFormat("es-MX", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function formatStatus(value: string): string {
  const labels: Record<string, string> = {
    CLOSED: "Cerrado",
    CLOSED_WITH_DIFFERENCE: "Con diferencia",
    OPEN: "Caja abierta",
    PENDING_CLOSE: "Pendiente",
  };
  return labels[value] ?? value;
}

function statusClass(value: string): string {
  if (value === "CLOSED_WITH_DIFFERENCE") {
    return "border-rose-200 bg-[var(--ui-color-danger-soft)] text-[var(--ui-color-danger)]";
  }
  if (value === "OPEN" || value === "PENDING_CLOSE") {
    return "border-amber-200 bg-[var(--ui-color-warning-soft)] text-[var(--ui-color-warning)]";
  }
  return "border-emerald-200 bg-[var(--ui-color-success-soft)] text-[var(--ui-color-success)]";
}

function differenceClass(value: string | null): string {
  const numericValue = Number(value ?? "0");
  if (numericValue > 0) {
    return "text-[var(--ui-color-success)]";
  }
  if (numericValue < 0) {
    return "text-[var(--ui-color-danger)]";
  }
  return "text-slate-950";
}

interface AdminCashCutsTableProps {
  cashCuts: AdminCashCutListItem[];
  errorMessage?: string | null;
  isLoading?: boolean;
  onCopyFolio: (item: AdminCashCutListItem) => void;
  onPageChange: (page: number) => void;
  onSelectCashCut: (item: AdminCashCutListItem) => void;
  page: number;
  pageSize: number;
  selectedCashSessionId?: string | null;
  total: number;
}

export function AdminCashCutsTable({
  cashCuts,
  errorMessage,
  isLoading = false,
  onCopyFolio,
  onPageChange,
  onSelectCashCut,
  page,
  pageSize,
  selectedCashSessionId,
  total,
}: AdminCashCutsTableProps) {
  const totalPages = Math.max(1, Math.ceil(total / pageSize));
  const canGoPrevious = page > 1;
  const canGoNext = page < totalPages;

  return (
    <section className="flex min-h-0 min-w-0 flex-col overflow-hidden rounded-[20px] border border-[var(--ui-color-border)] bg-white">
      <div className="flex min-w-0 shrink-0 items-center justify-between gap-3 border-b border-[var(--ui-color-border)] px-3 py-2.5">
        <div className="min-w-0">
          <h3 className="truncate text-base font-semibold text-slate-950" title="Cortes de caja">
            Cortes de caja
          </h3>
          <p className="truncate text-xs text-slate-500">
            Sesiones POS, cierre, esperado, contado, diferencia y documentos relacionados.
          </p>
        </div>
        <span className="shrink-0 rounded-full border border-[var(--ui-color-border)] bg-white px-3 py-1 text-xs font-semibold text-slate-600">
          {total} registros
        </span>
      </div>

      <div className="min-h-0 min-w-0 flex-1 overflow-y-auto p-2.5">
        {isLoading ? (
          <AdminEmptyState
            description="Consultando cortes persistidos del backend."
            title="Cargando cortes"
          />
        ) : errorMessage ? (
          <AdminEmptyState description={errorMessage} title="No se pudieron cargar los cortes" />
        ) : cashCuts.length > 0 ? (
          <div className="grid min-w-0 gap-1.5">
            {cashCuts.map((item) => {
              const isSelected = item.cashSessionId === selectedCashSessionId;
              return (
                <article
                  className={[
                    "grid min-w-0 gap-2 rounded-[16px] border px-3 py-2 transition xl:grid-cols-[minmax(7rem,0.75fr)_minmax(8.5rem,0.8fr)_minmax(0,1fr)_minmax(0,0.9fr)_repeat(5,minmax(6.5rem,0.55fr))_auto]",
                    isSelected
                      ? "border-[var(--ui-color-info)] bg-[var(--ui-color-info-soft)]"
                      : "border-[var(--ui-color-border)] bg-white hover:bg-slate-50",
                  ].join(" ")}
                  key={item.cashSessionId}
                >
                  <button
                    className="min-w-0 text-left focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
                    title={item.folio}
                    type="button"
                    onClick={() => onSelectCashCut(item)}
                  >
                    <span className="block truncate text-sm font-semibold text-slate-950">
                      {item.folio}
                    </span>
                    <span className="mt-0.5 block truncate text-xs text-slate-500">
                      {formatDateTime(item.closedAt)}
                    </span>
                  </button>

                  <button
                    className="min-w-0 text-left focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
                    title={formatDateTime(item.openedAt)}
                    type="button"
                    onClick={() => onSelectCashCut(item)}
                  >
                    <span className="block truncate text-sm font-semibold text-slate-800">
                      {formatDateTime(item.openedAt)}
                    </span>
                    <span className="mt-0.5 block truncate text-xs text-slate-500">Apertura</span>
                  </button>

                  <button
                    className="min-w-0 text-left focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
                    title={`${item.branchName} - ${item.workstationName}`}
                    type="button"
                    onClick={() => onSelectCashCut(item)}
                  >
                    <span className="block truncate text-sm font-semibold text-slate-950">
                      {item.branchName}
                    </span>
                    <span className="mt-0.5 block truncate text-xs text-slate-500">
                      {item.workstationName} - {item.workstationCode}
                    </span>
                  </button>

                  <button
                    className="min-w-0 text-left focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
                    title={item.cashierName}
                    type="button"
                    onClick={() => onSelectCashCut(item)}
                  >
                    <span className="block truncate text-sm font-semibold text-slate-950">
                      {item.cashierName}
                    </span>
                    <span className="mt-0.5 block truncate text-xs text-slate-500">
                      {item.paymentMethodsSummary}
                    </span>
                  </button>

                  <button
                    className="min-w-0 text-left xl:text-right focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
                    title={formatMoney(item.totalSalesAmount)}
                    type="button"
                    onClick={() => onSelectCashCut(item)}
                  >
                    <span className="block truncate text-sm font-semibold text-slate-950">
                      {formatMoney(item.totalSalesAmount)}
                    </span>
                    <span className="mt-0.5 block truncate text-xs text-slate-500">Ventas</span>
                  </button>

                  <button
                    className="min-w-0 text-left xl:text-right focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
                    title={formatMoney(item.openingAmount)}
                    type="button"
                    onClick={() => onSelectCashCut(item)}
                  >
                    <span className="block truncate text-sm font-semibold text-slate-950">
                      {formatMoney(item.openingAmount)}
                    </span>
                    <span className="mt-0.5 block truncate text-xs text-slate-500">Inicial</span>
                  </button>

                  <button
                    className="min-w-0 text-left xl:text-right focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
                    title={formatMoney(item.expectedCashAmount)}
                    type="button"
                    onClick={() => onSelectCashCut(item)}
                  >
                    <span className="block truncate text-sm font-semibold text-slate-950">
                      {formatMoney(item.expectedCashAmount)}
                    </span>
                    <span className="mt-0.5 block truncate text-xs text-slate-500">Esperado</span>
                  </button>

                  <button
                    className="min-w-0 text-left xl:text-right focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
                    title={formatMoney(item.countedCashAmount)}
                    type="button"
                    onClick={() => onSelectCashCut(item)}
                  >
                    <span className="block truncate text-sm font-semibold text-slate-950">
                      {formatMoney(item.countedCashAmount)}
                    </span>
                    <span className="mt-0.5 block truncate text-xs text-slate-500">Contado</span>
                  </button>

                  <button
                    className="min-w-0 text-left xl:text-right focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
                    title={formatMoney(item.differenceAmount)}
                    type="button"
                    onClick={() => onSelectCashCut(item)}
                  >
                    <span
                      className={`block truncate text-sm font-semibold ${differenceClass(item.differenceAmount)}`}
                    >
                      {formatMoney(item.differenceAmount)}
                    </span>
                    <span className="mt-0.5 block truncate text-xs text-slate-500">Diferencia</span>
                  </button>

                  <div className="flex min-w-0 items-center justify-end gap-1.5">
                    <span
                      className={`inline-flex min-w-0 rounded-full border px-2.5 py-1 text-xs font-semibold ${statusClass(item.status)}`}
                      title={formatStatus(item.status)}
                    >
                      <span className="truncate">{formatStatus(item.status)}</span>
                    </span>
                    <button
                      className="rounded-full border border-[var(--ui-color-border)] bg-white px-2.5 py-1 text-xs font-semibold text-slate-700 transition hover:border-[var(--ui-color-info)] hover:text-[var(--ui-color-info)] focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
                      type="button"
                      onClick={() => onSelectCashCut(item)}
                    >
                      Ver
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
            description="No hay cortes de caja para los filtros seleccionados."
            title="Sin cortes en la consulta"
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
