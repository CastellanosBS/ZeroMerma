import { AdminEmptyState } from "../../components/AdminEmptyState";
import type { AdminSalesTicketDetail, AdminSalesTicketListItem } from "../types";

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
    NOT_RETURNED: "Sin devolucion",
    PARTIALLY_RETURNED: "Devolucion parcial",
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

interface AdminSalesTicketDetailPanelProps {
  detail: AdminSalesTicketDetail | null;
  errorMessage?: string | null;
  isLoading?: boolean;
  onCopyFolio: (folio: string) => void;
  selectedTicket: AdminSalesTicketListItem | null;
}

export function AdminSalesTicketDetailPanel({
  detail,
  errorMessage,
  isLoading = false,
  onCopyFolio,
  selectedTicket,
}: AdminSalesTicketDetailPanelProps) {
  if (!selectedTicket) {
    return (
      <aside className="flex min-h-0 min-w-0 flex-col overflow-hidden rounded-[20px] border border-[var(--ui-color-border)] bg-white">
        <div className="border-b border-[var(--ui-color-border)] px-4 py-3">
          <p className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">Detalle</p>
          <h3 className="mt-1 text-lg font-semibold text-slate-950">Sin ticket seleccionado</h3>
        </div>
        <div className="min-h-0 flex-1 p-4">
          <AdminEmptyState
            description="Selecciona un ticket para revisar su detalle, pagos y documentos relacionados."
            title="Selecciona un ticket"
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
          <h3 className="mt-1 truncate text-lg font-semibold text-slate-950">{selectedTicket.folio}</h3>
        </div>
        <div className="min-h-0 flex-1 p-4">
          <AdminEmptyState description="Consultando lineas, pagos y contexto operativo." title="Cargando ticket" />
        </div>
      </aside>
    );
  }

  if (errorMessage || !detail) {
    return (
      <aside className="flex min-h-0 min-w-0 flex-col overflow-hidden rounded-[20px] border border-[var(--ui-color-border)] bg-white">
        <div className="border-b border-[var(--ui-color-border)] px-4 py-3">
          <p className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">Detalle</p>
          <h3 className="mt-1 truncate text-lg font-semibold text-slate-950">{selectedTicket.folio}</h3>
        </div>
        <div className="min-h-0 flex-1 p-4">
          <AdminEmptyState
            description={errorMessage ?? "No se pudo cargar el detalle del ticket."}
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
            <p className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">Ticket</p>
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
              {formatMoney(detail.overview.totalAmount, currencyCode)}
            </strong>
          </div>
          <div className="mt-3 grid gap-1.5">
            <FieldRow label="Subtotal" value={formatMoney(detail.overview.subtotalAmount, currencyCode)} />
            <FieldRow label="Pagado" value={formatMoney(detail.overview.paidAmount, currencyCode)} />
            <FieldRow label="Cambio" value={formatMoney(detail.overview.changeAmount, currencyCode)} />
            <FieldRow label="Devuelto" value={formatMoney(detail.overview.returnedAmount, currencyCode)} />
            <FieldRow label="Fecha" value={formatDateTime(detail.overview.confirmedAt)} />
          </div>
        </section>

        <section className="mt-3 rounded-[18px] border border-[var(--ui-color-border)] bg-white p-3">
          <p className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">Contexto operativo</p>
          <div className="mt-3 grid gap-1.5">
            <FieldRow label="Sucursal" value={detail.operationalContext.branchName} />
            <FieldRow
              label="Caja"
              value={`${detail.operationalContext.workstationName} (${detail.operationalContext.workstationCode})`}
            />
            <FieldRow label="Cajero" value={detail.operationalContext.cashierName} />
            <FieldRow label="Turno" value={detail.operationalContext.cashSessionId} />
            <FieldRow label="Venta" value={detail.operationalContext.saleId} />
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
                  <p className="truncate font-semibold text-slate-950" title={line.catalogName}>
                    {line.catalogName}
                  </p>
                  <p className="truncate text-xs text-slate-500" title={line.captureMode}>
                    {line.catalogCode} · {line.captureMode}
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
            {detail.payments.map((payment) => (
              <div
                className="grid grid-cols-[minmax(0,1fr)_6rem] gap-2 rounded-[14px] border border-[var(--ui-color-border)] bg-slate-50 px-3 py-2 text-sm"
                key={payment.id}
              >
                <span className="truncate font-semibold text-slate-950">{payment.paymentMethodCode}</span>
                <span className="text-right font-semibold text-slate-950">
                  {formatMoney(payment.appliedAmount, payment.currencyCode)}
                </span>
                <span className="text-xs text-slate-500">Recibido {formatMoney(payment.tenderedAmount, payment.currencyCode)}</span>
                <span className="text-right text-xs text-slate-500">Cambio {formatMoney(payment.changeAmount, payment.currencyCode)}</span>
              </div>
            ))}
          </div>
        </section>

        <section className="mt-3 rounded-[18px] border border-[var(--ui-color-border)] bg-white p-3">
          <p className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">Documentos relacionados</p>
          <div className="mt-3 grid gap-1.5">
            {detail.relatedDocuments.length > 0 ? (
              detail.relatedDocuments.map((document) => (
                <div
                  className="rounded-[14px] border border-[var(--ui-color-border)] bg-slate-50 px-3 py-2 text-sm"
                  key={document.id}
                >
                  <div className="flex min-w-0 items-center justify-between gap-2">
                    <span className="truncate font-semibold text-slate-950">{document.folio}</span>
                    <span className="shrink-0 text-xs font-semibold text-slate-500">{document.status}</span>
                  </div>
                  <p className="mt-1 text-xs text-slate-500">
                    {document.documentType === "return" ? "Devolucion" : document.documentType}
                    {document.amount ? ` · ${formatMoney(document.amount, currencyCode)}` : ""}
                  </p>
                </div>
              ))
            ) : (
              <p className="rounded-[14px] border border-dashed border-[var(--ui-color-border)] px-3 py-3 text-sm text-slate-600">
                Este ticket no tiene devoluciones ni correcciones relacionadas.
              </p>
            )}
          </div>
        </section>
      </div>

      <div className="grid shrink-0 grid-cols-2 gap-2 border-t border-[var(--ui-color-border)] p-3">
        <button
          className="h-10 rounded-2xl border border-[var(--ui-color-border)] bg-white px-3 text-sm font-semibold text-slate-700 transition hover:border-[var(--ui-color-info)] hover:text-[var(--ui-color-info)] focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
          type="button"
          onClick={() => onCopyFolio(detail.overview.folio)}
        >
          Copiar folio
        </button>
        <button
          className="h-10 cursor-not-allowed rounded-2xl bg-slate-300 px-3 text-sm font-semibold text-white"
          disabled
          title="Reimpresion no disponible en Backoffice"
          type="button"
        >
          Reimprimir
        </button>
      </div>
    </aside>
  );
}
