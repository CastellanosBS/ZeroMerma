import { AdminEmptyState } from "../../components/AdminEmptyState";
import type { AdminOrderDetail, AdminOrderListItem } from "../types";

function formatMoney(value: string | null | undefined, currencyCode = "MXN"): string {
  if (!value) {
    return "N/A";
  }
  const numericValue = Number(value);
  if (!Number.isFinite(numericValue)) {
    return `${value} ${currencyCode}`;
  }
  return new Intl.NumberFormat("es-MX", { currency: currencyCode, style: "currency" }).format(numericValue);
}

function formatDateTime(value: string | null | undefined): string {
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

function formatPaymentType(value: string): string {
  const labels: Record<string, string> = {
    ADVANCE: "Anticipo",
    REFUND: "Reembolso",
    SETTLEMENT: "Liquidacion",
  };
  return labels[value] ?? value;
}

function FieldRow({ label, value, title }: { label: string; title?: string; value: string }) {
  return (
    <div className="grid min-w-0 grid-cols-[7rem_minmax(0,1fr)] gap-2 text-sm">
      <span className="truncate text-slate-500">{label}</span>
      <span className="truncate text-right font-semibold text-slate-950" title={title ?? value}>
        {value}
      </span>
    </div>
  );
}

interface AdminOrderDetailPanelProps {
  detail: AdminOrderDetail | null;
  errorMessage?: string | null;
  isLoading?: boolean;
  onCancel: (item: AdminOrderDetail) => void;
  onDeliver: (item: AdminOrderDetail) => void;
  onMarkReady: (item: AdminOrderDetail) => void;
  selectedOrder: AdminOrderListItem | null;
}

export function AdminOrderDetailPanel({
  detail,
  errorMessage,
  isLoading = false,
  onCancel,
  onDeliver,
  onMarkReady,
  selectedOrder,
}: AdminOrderDetailPanelProps) {
  if (!selectedOrder) {
    return (
      <aside className="flex min-h-0 min-w-0 flex-col overflow-hidden rounded-[20px] border border-[var(--ui-color-border)] bg-white">
        <div className="border-b border-[var(--ui-color-border)] px-4 py-3">
          <p className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">Detalle</p>
          <h3 className="mt-1 text-lg font-semibold text-slate-950">Sin pedido seleccionado</h3>
        </div>
        <div className="min-h-0 flex-1 p-4">
          <AdminEmptyState
            description="Selecciona un pedido para revisar productos, pagos y estado de entrega."
            title="Selecciona un pedido"
          />
        </div>
      </aside>
    );
  }

  if (isLoading) {
    return (
      <aside className="flex min-h-0 min-w-0 flex-col overflow-hidden rounded-[20px] border border-[var(--ui-color-border)] bg-white">
        <div className="border-b border-[var(--ui-color-border)] px-4 py-3">
          <p className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">Detalle</p>
          <h3 className="mt-1 truncate text-lg font-semibold text-slate-950">{selectedOrder.folio}</h3>
        </div>
        <div className="min-h-0 flex-1 p-4">
          <AdminEmptyState description="Consultando productos, pagos y timeline." title="Cargando pedido" />
        </div>
      </aside>
    );
  }

  if (errorMessage || !detail) {
    return (
      <aside className="flex min-h-0 min-w-0 flex-col overflow-hidden rounded-[20px] border border-[var(--ui-color-border)] bg-white">
        <div className="border-b border-[var(--ui-color-border)] px-4 py-3">
          <p className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">Detalle</p>
          <h3 className="mt-1 truncate text-lg font-semibold text-slate-950">{selectedOrder.folio}</h3>
        </div>
        <div className="min-h-0 flex-1 p-4">
          <AdminEmptyState
            description={errorMessage ?? "No se pudo cargar el detalle del pedido."}
            title="Detalle no disponible"
          />
        </div>
      </aside>
    );
  }

  const currencyCode = detail.overview.currencyCode;

  return (
    <aside className="flex min-h-0 min-w-0 flex-col overflow-hidden rounded-[20px] border border-[var(--ui-color-border)] bg-white">
      <div className="shrink-0 border-b border-[var(--ui-color-border)] px-4 py-3">
        <div className="flex min-w-0 items-start justify-between gap-3">
          <div className="min-w-0">
            <p className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">Pedido</p>
            <h3 className="mt-1 truncate text-lg font-semibold text-slate-950" title={detail.overview.folio}>
              {detail.overview.folio}
            </h3>
          </div>
          <span className="rounded-full border border-[var(--ui-color-border)] bg-slate-50 px-3 py-1 text-xs font-semibold text-slate-600">
            {formatStatus(detail.overview.status)}
          </span>
        </div>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto p-3">
        <section className="rounded-[18px] border border-[var(--ui-color-border)] bg-slate-50/80 p-3">
          <div className="flex items-center justify-between gap-3">
            <span className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">Resumen</span>
            <strong className="text-xl font-semibold text-slate-950">
              {formatMoney(detail.overview.remainingBalanceAmount, currencyCode)}
            </strong>
          </div>
          <div className="mt-3 grid gap-1.5">
            <FieldRow label="Entrega" value={formatDateTime(detail.overview.requestedForAt)} />
            <FieldRow label="Total" value={formatMoney(detail.overview.totalAmount, currencyCode)} />
            <FieldRow label="Anticipo" value={formatMoney(detail.overview.advanceAmount, currencyCode)} />
            <FieldRow label="Saldo" value={formatMoney(detail.overview.remainingBalanceAmount, currencyCode)} />
            <FieldRow
              label="Reembolso"
              value={formatMoney(detail.overview.cancellationRefundAmount, currencyCode)}
            />
          </div>
          {detail.availableActions.financialActionNote ? (
            <p className="mt-3 rounded-[14px] border border-amber-200 bg-[var(--ui-color-warning-soft)] px-3 py-2 text-xs font-semibold text-[var(--ui-color-warning)]">
              {detail.availableActions.financialActionNote}
            </p>
          ) : null}
        </section>

        <section className="mt-3 rounded-[18px] border border-[var(--ui-color-border)] bg-white p-3">
          <p className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">Cliente</p>
          <div className="mt-3 grid gap-1.5">
            <FieldRow label="Nombre" value={detail.customer.name} />
            <FieldRow label="Telefono" value={detail.customer.phone ?? "Sin telefono"} />
            <FieldRow label="Notas" value={detail.customer.notes ?? "Sin notas"} />
          </div>
        </section>

        <section className="mt-3 rounded-[18px] border border-[var(--ui-color-border)] bg-white p-3">
          <p className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">Contexto operativo</p>
          <div className="mt-3 grid gap-1.5">
            <FieldRow label="Sucursal" value={detail.overview.branchName} />
            <FieldRow
              label="Caja"
              value={`${detail.operationalContext.workstationName ?? "N/A"} (${detail.operationalContext.workstationCode ?? "N/A"})`}
            />
            <FieldRow label="Creado por" value={detail.operationalContext.createdByUserFullName ?? "N/A"} />
            <FieldRow label="Turno" value={detail.operationalContext.activeCashSessionId ?? "N/A"} />
          </div>
        </section>

        <section className="mt-3 rounded-[18px] border border-[var(--ui-color-border)] bg-white p-3">
          <div className="flex items-center justify-between gap-2">
            <p className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">Productos</p>
            <span className="rounded-full border border-[var(--ui-color-border)] bg-white px-2.5 py-1 text-xs font-semibold text-slate-600">
              {detail.lines.length} lineas
            </span>
          </div>
          <div className="mt-3 grid gap-1.5">
            {detail.lines.map((line) => (
              <div
                className="grid min-w-0 grid-cols-[minmax(0,1fr)_4.5rem_5.5rem] items-center gap-2 rounded-[14px] border border-[var(--ui-color-border)] bg-slate-50 px-3 py-2 text-sm"
                key={line.id}
              >
                <div className="min-w-0">
                  <p className="truncate font-semibold text-slate-950" title={line.productName}>
                    {line.productName}
                  </p>
                  <p className="truncate text-xs text-slate-500" title={line.productClassName}>
                    {line.productCode} - {line.productClassName}
                  </p>
                </div>
                <span className="text-right font-semibold text-slate-700">{line.quantity}</span>
                <span className="text-right font-semibold text-slate-950">
                  {formatMoney(line.lineTotalAmount, currencyCode)}
                </span>
              </div>
            ))}
          </div>
        </section>

        <section className="mt-3 rounded-[18px] border border-[var(--ui-color-border)] bg-white p-3">
          <p className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">Pagos</p>
          <div className="mt-3 grid gap-1.5">
            {detail.payments.length > 0 ? (
              detail.payments.map((payment) => (
                <div
                  className="grid grid-cols-[minmax(0,1fr)_6rem] gap-2 rounded-[14px] border border-[var(--ui-color-border)] bg-slate-50 px-3 py-2 text-sm"
                  key={payment.id}
                >
                  <span className="truncate font-semibold text-slate-950">
                    {formatPaymentType(payment.paymentType)} - {payment.paymentMethodCode}
                  </span>
                  <span className="text-right font-semibold text-slate-950">
                    {formatMoney(payment.amount, payment.currencyCode)}
                  </span>
                  <span className="truncate text-xs text-slate-500">{payment.recordedByUserFullName}</span>
                  <span className="text-right text-xs text-slate-500">{formatDateTime(payment.recordedAtUtc)}</span>
                </div>
              ))
            ) : (
              <p className="rounded-[14px] border border-dashed border-[var(--ui-color-border)] px-3 py-3 text-sm text-slate-600">
                Este pedido no tiene pagos registrados.
              </p>
            )}
          </div>
        </section>

        <section className="mt-3 rounded-[18px] border border-[var(--ui-color-border)] bg-white p-3">
          <p className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">Timeline</p>
          <div className="mt-3 grid gap-1.5">
            {detail.timeline.map((event) => (
              <div className="rounded-[14px] border border-[var(--ui-color-border)] bg-slate-50 px-3 py-2 text-sm" key={event.key}>
                <div className="flex min-w-0 items-center justify-between gap-2">
                  <span className="truncate font-semibold text-slate-950">{event.label}</span>
                  <span className="shrink-0 text-xs text-slate-500">{formatDateTime(event.occurredAt)}</span>
                </div>
                {event.description ? <p className="mt-1 truncate text-xs text-slate-500">{event.description}</p> : null}
              </div>
            ))}
          </div>
        </section>

        <section className="mt-3 rounded-[18px] border border-[var(--ui-color-border)] bg-white p-3">
          <p className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">Documentos relacionados</p>
          <div className="mt-3">
            {detail.relatedDocuments.length > 0 ? (
              <div className="grid gap-1.5">
                {detail.relatedDocuments.map((document) => (
                  <div className="rounded-[14px] border border-[var(--ui-color-border)] bg-slate-50 px-3 py-2 text-sm" key={document.id}>
                    <div className="flex min-w-0 items-center justify-between gap-2">
                      <span className="truncate font-semibold text-slate-950">{document.folio}</span>
                      <span className="shrink-0 text-xs font-semibold text-slate-500">{document.status}</span>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="rounded-[14px] border border-dashed border-[var(--ui-color-border)] px-3 py-3 text-sm text-slate-600">
                Este pedido no tiene documentos relacionados.
              </p>
            )}
          </div>
        </section>
      </div>

      <div className="grid shrink-0 grid-cols-3 gap-2 border-t border-[var(--ui-color-border)] p-3">
        <button
          className="h-10 rounded-2xl border border-[var(--ui-color-border)] bg-white px-3 text-xs font-semibold text-slate-700 transition hover:border-[var(--ui-color-info)] hover:text-[var(--ui-color-info)] focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)] disabled:cursor-not-allowed disabled:opacity-45"
          disabled={!detail.availableActions.canMarkReady}
          type="button"
          onClick={() => onMarkReady(detail)}
        >
          Marcar listo
        </button>
        <button
          className="h-10 rounded-2xl bg-[var(--ui-color-primary)] px-3 text-xs font-semibold text-white transition hover:bg-[var(--ui-color-primary-strong)] focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)] disabled:cursor-not-allowed disabled:bg-slate-300 disabled:text-slate-600"
          disabled={!detail.availableActions.canDeliver}
          type="button"
          onClick={() => onDeliver(detail)}
        >
          Entregar
        </button>
        <button
          className="h-10 rounded-2xl border border-rose-200 bg-white px-3 text-xs font-semibold text-[var(--ui-color-danger)] transition hover:bg-[var(--ui-color-danger-soft)] focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)] disabled:cursor-not-allowed disabled:opacity-45"
          disabled={!detail.availableActions.canCancel}
          type="button"
          onClick={() => onCancel(detail)}
        >
          Cancelar
        </button>
      </div>
    </aside>
  );
}
