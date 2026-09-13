import { AdminActionButton } from "../../components/AdminActionButton";
import { AdminEmptyState } from "../../components/AdminEmptyState";
import type { AdminOrderListItem } from "../types";

function formatMoney(value: string, currencyCode: string): string {
  const numericValue = Number(value);
  if (!Number.isFinite(numericValue)) {
    return `${value} ${currencyCode}`;
  }
  return new Intl.NumberFormat("es-MX", { currency: currencyCode, style: "currency" }).format(
    numericValue,
  );
}

function formatDateTime(value: string | null): string {
  if (!value) {
    return "Sin fecha";
  }
  return new Intl.DateTimeFormat("es-MX", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function formatStatus(value: string): string {
  const labels: Record<string, string> = {
    CANCELED: "Cancelado",
    DELIVERED: "Entregado",
    PENDING: "Pendiente",
    READY: "Listo",
  };
  return labels[value] ?? value;
}

function statusClass(value: string): string {
  if (value === "CANCELED") {
    return "border-rose-200 bg-[var(--ui-color-danger-soft)] text-[var(--ui-color-danger)]";
  }
  if (value === "DELIVERED") {
    return "border-emerald-200 bg-[var(--ui-color-success-soft)] text-[var(--ui-color-success)]";
  }
  if (value === "READY") {
    return "border-sky-200 bg-[var(--ui-color-info-soft)] text-[var(--ui-color-info)]";
  }
  return "border-amber-200 bg-[var(--ui-color-warning-soft)] text-[var(--ui-color-warning)]";
}

function formatPaymentState(value: string): string {
  const labels: Record<string, string> = {
    BALANCE_PENDING: "Con saldo",
    CANCELED: "Cancelado",
    NO_DEPOSIT: "Sin anticipo",
    PAID: "Pagado",
    PARTIAL_DEPOSIT: "Anticipo parcial",
  };
  return labels[value] ?? value;
}

interface AdminOrdersTableProps {
  errorMessage?: string | null;
  isLoading?: boolean;
  onCancel: (item: AdminOrderListItem) => void;
  onDeliver: (item: AdminOrderListItem) => void;
  onMarkReady: (item: AdminOrderListItem) => void;
  onPageChange: (page: number) => void;
  onSelectOrder: (item: AdminOrderListItem) => void;
  orders: AdminOrderListItem[];
  page: number;
  pageSize: number;
  selectedOrderId?: string | null;
  total: number;
}

export function AdminOrdersTable({
  errorMessage,
  isLoading = false,
  onCancel,
  onDeliver,
  onMarkReady,
  onPageChange,
  onSelectOrder,
  orders,
  page,
  pageSize,
  selectedOrderId,
  total,
}: AdminOrdersTableProps) {
  const totalPages = Math.max(1, Math.ceil(total / pageSize));
  const canGoPrevious = page > 1;
  const canGoNext = page < totalPages;

  return (
    <section className="flex min-h-0 min-w-0 flex-col overflow-hidden rounded-[20px] border border-[var(--ui-color-border)] bg-white">
      <div className="flex min-w-0 shrink-0 items-center justify-between gap-3 border-b border-[var(--ui-color-border)] px-3 py-2.5">
        <div className="min-w-0">
          <h3
            className="truncate text-base font-semibold text-slate-950"
            title="Pedidos registrados"
          >
            Pedidos registrados
          </h3>
          <p className="truncate text-xs text-slate-500">
            Entregas, anticipos, saldos y estado operativo del pedido.
          </p>
        </div>
        <span className="shrink-0 rounded-full border border-[var(--ui-color-border)] bg-white px-3 py-1 text-xs font-semibold text-slate-600">
          {total} registros
        </span>
      </div>

      <div className="min-h-0 min-w-0 flex-1 overflow-y-auto p-2.5">
        {isLoading ? (
          <AdminEmptyState
            description="Consultando pedidos reales del backend."
            title="Cargando pedidos"
          />
        ) : errorMessage ? (
          <AdminEmptyState description={errorMessage} title="No se pudieron cargar los pedidos" />
        ) : orders.length > 0 ? (
          <div className="grid min-w-0 gap-1.5">
            {orders.map((item) => {
              const isSelected = item.id === selectedOrderId;
              const canMarkReady = item.status === "PENDING";
              const canDeliver =
                item.status === "READY" && Number(item.remainingBalanceAmount) === 0;
              const canCancel =
                (item.status === "PENDING" || item.status === "READY") &&
                !item.cancellationRefundEligible;
              return (
                <article
                  className={[
                    "grid min-w-0 gap-2 rounded-[16px] border px-3 py-2 transition xl:grid-cols-[minmax(8rem,0.8fr)_minmax(0,1fr)_minmax(10rem,0.95fr)_minmax(6.8rem,0.55fr)_minmax(8rem,0.62fr)_minmax(8rem,0.62fr)_minmax(0,0.85fr)_auto]",
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
                    onClick={() => onSelectOrder(item)}
                  >
                    <span className="block truncate text-sm font-semibold text-slate-950">
                      {item.folio}
                    </span>
                    <span className="mt-0.5 block truncate text-xs text-slate-500">
                      {item.lineCount} lineas
                    </span>
                  </button>

                  <button
                    className="min-w-0 text-left focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
                    title={`${item.customerName}${item.customerPhone ? ` - ${item.customerPhone}` : ""}`}
                    type="button"
                    onClick={() => onSelectOrder(item)}
                  >
                    <span className="block truncate text-sm font-semibold text-slate-950">
                      {item.customerName}
                    </span>
                    <span className="mt-0.5 block truncate text-xs text-slate-500">
                      {item.customerPhone ?? "Sin telefono"}
                    </span>
                  </button>

                  <button
                    className="min-w-0 text-left focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
                    title={formatDateTime(item.requestedForAt)}
                    type="button"
                    onClick={() => onSelectOrder(item)}
                  >
                    <span className="block truncate text-sm font-semibold text-[var(--ui-color-primary)]">
                      {formatDateTime(item.requestedForAt)}
                    </span>
                    <span className="mt-0.5 block truncate text-xs text-slate-500">
                      {item.branchName}
                    </span>
                  </button>

                  <button
                    className="min-w-0 text-left focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
                    type="button"
                    onClick={() => onSelectOrder(item)}
                  >
                    <span
                      className={`inline-flex max-w-full rounded-full border px-2.5 py-1 text-xs font-semibold ${statusClass(item.status)}`}
                      title={formatStatus(item.status)}
                    >
                      <span className="truncate">{formatStatus(item.status)}</span>
                    </span>
                    <span className="mt-1 block truncate text-xs text-slate-500">
                      {formatPaymentState(item.paymentState)}
                    </span>
                  </button>

                  <button
                    className="min-w-0 text-left xl:text-right focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
                    title={formatMoney(item.totalAmount, item.currencyCode)}
                    type="button"
                    onClick={() => onSelectOrder(item)}
                  >
                    <span className="block truncate text-sm font-semibold text-slate-950">
                      {formatMoney(item.totalAmount, item.currencyCode)}
                    </span>
                    <span className="mt-0.5 block truncate text-xs text-slate-500">Total</span>
                  </button>

                  <button
                    className="min-w-0 text-left xl:text-right focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
                    title={formatMoney(item.remainingBalanceAmount, item.currencyCode)}
                    type="button"
                    onClick={() => onSelectOrder(item)}
                  >
                    <span className="block truncate text-sm font-semibold text-slate-950">
                      {formatMoney(item.remainingBalanceAmount, item.currencyCode)}
                    </span>
                    <span className="mt-0.5 block truncate text-xs text-slate-500">Saldo</span>
                  </button>

                  <button
                    className="min-w-0 text-left focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
                    title={`${item.workstationName} - ${item.createdByUserFullName}`}
                    type="button"
                    onClick={() => onSelectOrder(item)}
                  >
                    <span className="block truncate text-sm font-semibold text-slate-950">
                      {item.workstationName}
                    </span>
                    <span className="mt-0.5 block truncate text-xs text-slate-500">
                      {item.createdByUserFullName}
                    </span>
                  </button>

                  <div className="flex shrink-0 items-center justify-end gap-1.5">
                    <button
                      className="rounded-full border border-[var(--ui-color-border)] bg-white px-2.5 py-1 text-xs font-semibold text-slate-700 transition hover:border-[var(--ui-color-info)] hover:text-[var(--ui-color-info)] focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
                      type="button"
                      onClick={() => onSelectOrder(item)}
                    >
                      Ver
                    </button>
                    {canMarkReady ? (
                      <AdminActionButton
                        capability="orders.manage"
                        branchIds={[item.branchId]}
                        className="rounded-full border border-sky-200 bg-[var(--ui-color-info-soft)] px-2.5 py-1 text-xs font-semibold text-[var(--ui-color-info)] transition hover:border-sky-300 focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
                        type="button"
                        onClick={() => onMarkReady(item)}
                      >
                        Listo
                      </AdminActionButton>
                    ) : null}
                    {canDeliver ? (
                      <AdminActionButton
                        capability="orders.manage"
                        branchIds={[item.branchId]}
                        className="rounded-full border border-emerald-200 bg-[var(--ui-color-success-soft)] px-2.5 py-1 text-xs font-semibold text-[var(--ui-color-success)] transition hover:border-emerald-300 focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
                        type="button"
                        onClick={() => onDeliver(item)}
                      >
                        Entregar
                      </AdminActionButton>
                    ) : null}
                    {canCancel ? (
                      <AdminActionButton
                        capability="orders.cancel"
                        branchIds={[item.branchId]}
                        className="rounded-full border border-rose-200 bg-white px-2.5 py-1 text-xs font-semibold text-[var(--ui-color-danger)] transition hover:bg-[var(--ui-color-danger-soft)] focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
                        type="button"
                        onClick={() => onCancel(item)}
                      >
                        Cancelar
                      </AdminActionButton>
                    ) : null}
                  </div>
                </article>
              );
            })}
          </div>
        ) : (
          <AdminEmptyState
            description="No hay pedidos para este periodo. Crea un nuevo pedido desde la operacion o ajusta los filtros."
            title="Sin pedidos en la consulta"
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
