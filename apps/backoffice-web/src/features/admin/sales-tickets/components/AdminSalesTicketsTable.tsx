import { AdminEmptyState } from "../../components/AdminEmptyState";
import type {
  AdminSalesTicketBackendContract,
  AdminSalesTicketListItem,
} from "../types";

function formatMoney(value: string, currencyCode: string): string {
  const numericValue = Number(value);
  if (!Number.isFinite(numericValue)) {
    return `${value} ${currencyCode}`;
  }
  return new Intl.NumberFormat("es-MX", { currency: currencyCode, style: "currency" }).format(numericValue);
}

function formatDateTime(value: string): string {
  return new Intl.DateTimeFormat("es-MX", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function formatStatus(value: string): string {
  const labels: Record<string, string> = {
    CONFIRMED: "Confirmado",
    FULLY_RETURNED: "Devuelto",
    PARTIALLY_RETURNED: "Dev. parcial",
  };
  return labels[value] ?? value;
}

function statusClass(value: string): string {
  if (value === "FULLY_RETURNED") {
    return "border-rose-200 bg-[var(--ui-color-danger-soft)] text-[var(--ui-color-danger)]";
  }
  if (value === "PARTIALLY_RETURNED") {
    return "border-amber-200 bg-[var(--ui-color-warning-soft)] text-[var(--ui-color-warning)]";
  }
  return "border-emerald-200 bg-[var(--ui-color-success-soft)] text-[var(--ui-color-success)]";
}

interface AdminSalesTicketsTableProps {
  backendContract: AdminSalesTicketBackendContract;
  errorMessage?: string | null;
  isLoading?: boolean;
  onCopyFolio: (item: AdminSalesTicketListItem) => void;
  onPageChange: (page: number) => void;
  onReprint: (item: AdminSalesTicketListItem) => void;
  onSelectTicket: (item: AdminSalesTicketListItem) => void;
  page: number;
  pageSize: number;
  selectedTicketId?: string | null;
  tickets: AdminSalesTicketListItem[];
  total: number;
}

export function AdminSalesTicketsTable({
  backendContract,
  errorMessage,
  isLoading = false,
  onCopyFolio,
  onPageChange,
  onReprint,
  onSelectTicket,
  page,
  pageSize,
  selectedTicketId,
  tickets,
  total,
}: AdminSalesTicketsTableProps) {
  const totalPages = Math.max(1, Math.ceil(total / pageSize));
  const canGoPrevious = page > 1;
  const canGoNext = page < totalPages;

  return (
    <section className="flex min-h-0 min-w-0 flex-col overflow-hidden rounded-[20px] border border-[var(--ui-color-border)] bg-white">
      <div className="flex min-w-0 shrink-0 items-center justify-between gap-3 border-b border-[var(--ui-color-border)] px-3 py-2.5">
        <div className="min-w-0">
          <h3 className="truncate text-base font-semibold text-slate-950" title="Tickets emitidos">
            Tickets emitidos
          </h3>
          <p className="truncate text-xs text-slate-500">
            Ventas confirmadas por POS, pagos, caja y documentos relacionados.
          </p>
        </div>
        <span className="shrink-0 rounded-full border border-[var(--ui-color-border)] bg-white px-3 py-1 text-xs font-semibold text-slate-600">
          {total} registros
        </span>
      </div>

      <div className="min-h-0 min-w-0 flex-1 overflow-y-auto p-2.5">
        {isLoading ? (
          <AdminEmptyState description="Consultando ventas reales del backend." title="Cargando tickets" />
        ) : errorMessage ? (
          <AdminEmptyState description={errorMessage} title="No se pudieron cargar los tickets" />
        ) : tickets.length > 0 ? (
          <div className="grid min-w-0 gap-1.5">
            {tickets.map((item) => {
              const isSelected = item.id === selectedTicketId;
              return (
                <article
                  className={[
                    "grid min-w-0 gap-2 rounded-[16px] border px-3 py-2 transition xl:grid-cols-[minmax(8rem,0.9fr)_minmax(9rem,0.85fr)_minmax(0,1.15fr)_minmax(0,0.9fr)_minmax(7rem,0.6fr)_minmax(7rem,0.6fr)_auto]",
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
                    onClick={() => onSelectTicket(item)}
                  >
                    <span className="block truncate text-sm font-semibold text-slate-950">{item.folio}</span>
                    <span className="mt-0.5 block truncate text-xs text-slate-500">{item.itemCount} lineas</span>
                  </button>

                  <button
                    className="min-w-0 text-left focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
                    title={formatDateTime(item.occurredAt)}
                    type="button"
                    onClick={() => onSelectTicket(item)}
                  >
                    <span className="block truncate text-sm font-semibold text-slate-800">
                      {formatDateTime(item.occurredAt)}
                    </span>
                    <span className="mt-0.5 block truncate text-xs text-slate-500">{item.unitCount} unidades</span>
                  </button>

                  <button
                    className="min-w-0 text-left focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
                    title={`${item.branchName} - ${item.workstationName}`}
                    type="button"
                    onClick={() => onSelectTicket(item)}
                  >
                    <span className="block truncate text-sm font-semibold text-slate-950">{item.branchName}</span>
                    <span className="mt-0.5 block truncate text-xs text-slate-500">
                      {item.workstationName} · {item.workstationCode}
                    </span>
                  </button>

                  <button
                    className="min-w-0 text-left focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
                    title={item.cashierName}
                    type="button"
                    onClick={() => onSelectTicket(item)}
                  >
                    <span className="block truncate text-sm font-semibold text-slate-950">{item.cashierName}</span>
                    <span className="mt-0.5 block truncate text-xs text-slate-500">{item.paymentMethodsLabel}</span>
                  </button>

                  <button
                    className="min-w-0 text-left xl:text-right focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
                    title={formatMoney(item.totalAmount, item.currencyCode)}
                    type="button"
                    onClick={() => onSelectTicket(item)}
                  >
                    <span className="block truncate text-sm font-semibold text-slate-950">
                      {formatMoney(item.totalAmount, item.currencyCode)}
                    </span>
                    <span className="mt-0.5 block truncate text-xs text-slate-500">{item.currencyCode}</span>
                  </button>

                  <button
                    className="min-w-0 text-left xl:text-right focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
                    type="button"
                    onClick={() => onSelectTicket(item)}
                  >
                    <span
                      className={`inline-flex max-w-full rounded-full border px-2.5 py-1 text-xs font-semibold ${statusClass(item.status)}`}
                      title={formatStatus(item.status)}
                    >
                      <span className="truncate">{formatStatus(item.status)}</span>
                    </span>
                  </button>

                  <div className="flex shrink-0 items-center justify-end gap-1.5">
                    <button
                      className="rounded-full border border-[var(--ui-color-border)] bg-white px-2.5 py-1 text-xs font-semibold text-slate-700 transition hover:border-[var(--ui-color-info)] hover:text-[var(--ui-color-info)] focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
                      type="button"
                      onClick={() => onSelectTicket(item)}
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
                    {backendContract.reprintEndpoint ? (
                      <button
                        className="rounded-full border border-[var(--ui-color-border)] bg-white px-2.5 py-1 text-xs font-semibold text-slate-700 transition hover:border-[var(--ui-color-info)] hover:text-[var(--ui-color-info)] focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
                        type="button"
                        onClick={() => onReprint(item)}
                      >
                        Reimprimir
                      </button>
                    ) : null}
                  </div>
                </article>
              );
            })}
          </div>
        ) : (
          <AdminEmptyState
            description="No hay ventas para este periodo. Ajusta los filtros o selecciona otro rango de fechas."
            title="Sin ventas en la consulta"
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
