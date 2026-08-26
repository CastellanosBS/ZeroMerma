import { AdminEmptyState } from "../../components/AdminEmptyState";
import type {
  AdminCashCutDetail,
  AdminCashCutListItem,
  AdminCashCutOperationalPaymentItem,
  AdminCashCutRefundItem,
  AdminCashCutTicketItem,
} from "../types";

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

function formatStatus(value: string): string {
  const labels: Record<string, string> = {
    CLOSED: "Cerrado",
    CLOSED_WITH_DIFFERENCE: "Cerrado con diferencia",
    OPEN: "Caja abierta",
    PENDING_CLOSE: "Pendiente de cierre",
  };
  return labels[value] ?? value;
}

function differenceTitle(value: string): string {
  const labels: Record<string, string> = {
    EXACT: "Exacto",
    OVER: "Sobrante",
    SHORT: "Faltante",
    UNRESOLVED: "Sin conteo",
  };
  return labels[value] ?? value;
}

function differenceBadgeClass(value: string): string {
  if (value === "OVER") {
    return "border-emerald-200 bg-[var(--ui-color-success-soft)] text-[var(--ui-color-success)]";
  }
  if (value === "SHORT") {
    return "border-rose-200 bg-[var(--ui-color-danger-soft)] text-[var(--ui-color-danger)]";
  }
  if (value === "UNRESOLVED") {
    return "border-amber-200 bg-[var(--ui-color-warning-soft)] text-[var(--ui-color-warning)]";
  }
  return "border-slate-200 bg-slate-50 text-slate-700";
}

function FieldRow({ label, value, title }: { label: string; title?: string; value: string }) {
  return (
    <div className="grid min-w-0 grid-cols-[8.5rem_minmax(0,1fr)] gap-2 text-sm">
      <span className="truncate text-slate-500">{label}</span>
      <span className="truncate text-right font-semibold text-slate-950" title={title ?? value}>
        {value}
      </span>
    </div>
  );
}

function SectionTitle({ count, title }: { count?: number; title: string }) {
  return (
    <div className="flex min-w-0 items-center justify-between gap-2">
      <p className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">{title}</p>
      {typeof count === "number" ? (
        <span className="rounded-full border border-[var(--ui-color-border)] bg-white px-2.5 py-1 text-xs font-semibold text-slate-600">
          {count}
        </span>
      ) : null}
    </div>
  );
}

function TicketRow({ ticket }: { ticket: AdminCashCutTicketItem }) {
  return (
    <div className="grid min-w-0 grid-cols-[minmax(0,1fr)_6.5rem] gap-2 rounded-[14px] border border-[var(--ui-color-border)] bg-slate-50 px-3 py-2 text-sm">
      <div className="min-w-0">
        <p className="truncate font-semibold text-slate-950" title={ticket.folio}>
          {ticket.folio}
        </p>
        <p className="truncate text-xs text-slate-500">
          {formatDateTime(ticket.occurredAt)} - {ticket.paymentMethodSummary}
        </p>
      </div>
      <span className="text-right font-semibold text-slate-950">
        {formatMoney(ticket.totalAmount)}
      </span>
    </div>
  );
}

function RefundRow({ refund }: { refund: AdminCashCutRefundItem }) {
  return (
    <div className="rounded-[14px] border border-[var(--ui-color-border)] bg-slate-50 px-3 py-2 text-sm">
      <div className="flex min-w-0 items-center justify-between gap-2">
        <span className="truncate font-semibold text-slate-950">{refund.folio}</span>
        <span className="shrink-0 font-semibold text-[var(--ui-color-danger)]">
          {formatMoney(refund.amount)}
        </span>
      </div>
      <p className="mt-1 truncate text-xs text-slate-500">
        {refund.originalTicketFolio} - {refund.reasonName} - {formatDateTime(refund.occurredAt)}
      </p>
    </div>
  );
}

function OperationalPaymentRow({ payment }: { payment: AdminCashCutOperationalPaymentItem }) {
  return (
    <div className="rounded-[14px] border border-[var(--ui-color-border)] bg-slate-50 px-3 py-2 text-sm">
      <div className="flex min-w-0 items-center justify-between gap-2">
        <span className="truncate font-semibold text-slate-950">{payment.folio}</span>
        <span className="shrink-0 font-semibold text-slate-950">{formatMoney(payment.amount)}</span>
      </div>
      <p className="mt-1 truncate text-xs text-slate-500">
        {payment.categoryName ?? payment.categoryCode ?? "Sin categoria"} -{" "}
        {payment.paymentMethodCode} - {payment.operatorName}
      </p>
    </div>
  );
}

interface AdminCashCutDetailPanelProps {
  detail: AdminCashCutDetail | null;
  errorMessage?: string | null;
  isLoading?: boolean;
  onCopyFolio: (folio: string) => void;
  selectedCashCut: AdminCashCutListItem | null;
}

export function AdminCashCutDetailPanel({
  detail,
  errorMessage,
  isLoading = false,
  onCopyFolio,
  selectedCashCut,
}: AdminCashCutDetailPanelProps) {
  if (!selectedCashCut) {
    return (
      <aside className="flex min-h-0 min-w-0 flex-col overflow-hidden rounded-[20px] border border-[var(--ui-color-border)] bg-white">
        <div className="border-b border-[var(--ui-color-border)] px-4 py-3">
          <p className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">
            Detalle
          </p>
          <h3 className="mt-1 text-lg font-semibold text-slate-950">Sin corte seleccionado</h3>
        </div>
        <div className="min-h-0 flex-1 p-4">
          <AdminEmptyState
            description="Selecciona un corte para revisar ventas, pagos, diferencias y documentos relacionados."
            title="Selecciona un corte"
          />
        </div>
      </aside>
    );
  }

  if (isLoading) {
    return (
      <aside className="flex min-h-0 min-w-0 flex-col overflow-hidden rounded-[20px] border border-[var(--ui-color-border)] bg-white">
        <div className="border-b border-[var(--ui-color-border)] px-4 py-3">
          <p className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">
            Detalle
          </p>
          <h3 className="mt-1 truncate text-lg font-semibold text-slate-950">
            {selectedCashCut.folio}
          </h3>
        </div>
        <div className="min-h-0 flex-1 p-4">
          <AdminEmptyState
            description="Consultando venta, pagos y cierre."
            title="Cargando corte"
          />
        </div>
      </aside>
    );
  }

  if (errorMessage || !detail) {
    return (
      <aside className="flex min-h-0 min-w-0 flex-col overflow-hidden rounded-[20px] border border-[var(--ui-color-border)] bg-white">
        <div className="border-b border-[var(--ui-color-border)] px-4 py-3">
          <p className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">
            Detalle
          </p>
          <h3 className="mt-1 truncate text-lg font-semibold text-slate-950">
            {selectedCashCut.folio}
          </h3>
        </div>
        <div className="min-h-0 flex-1 p-4">
          <AdminEmptyState
            description={errorMessage ?? "No se pudo cargar el detalle del corte."}
            title="Detalle no disponible"
          />
        </div>
      </aside>
    );
  }

  const difference = detail.expectedVsCounted;

  return (
    <aside className="flex min-h-0 min-w-0 flex-col overflow-hidden rounded-[20px] border border-[var(--ui-color-border)] bg-white">
      <div className="shrink-0 border-b border-[var(--ui-color-border)] px-4 py-3">
        <div className="flex min-w-0 items-start justify-between gap-3">
          <div className="min-w-0">
            <p className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">
              Corte
            </p>
            <h3
              className="mt-1 truncate text-lg font-semibold text-slate-950"
              title={detail.overview.folio}
            >
              {detail.overview.folio}
            </h3>
          </div>
          <span className="rounded-full border border-[var(--ui-color-border)] bg-slate-50 px-3 py-1 text-xs font-semibold text-slate-600">
            {formatStatus(detail.overview.status)}
          </span>
        </div>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto p-3">
        <section className="rounded-[18px] border border-[var(--ui-color-border)] bg-white p-3">
          <SectionTitle title="Resumen" />
          <div className="mt-3 grid gap-1.5">
            <FieldRow
              label="Sucursal"
              value={`${detail.overview.branchName} (${detail.overview.branchCode})`}
            />
            <FieldRow
              label="Caja"
              value={`${detail.overview.workstationName} (${detail.overview.workstationCode})`}
            />
            <FieldRow label="Cajero" value={detail.overview.cashierName} />
            <FieldRow label="Apertura" value={formatDateTime(detail.overview.openedAt)} />
            <FieldRow label="Cierre" value={formatDateTime(detail.overview.closedAt)} />
            <FieldRow
              label="Duracion"
              value={
                detail.overview.totalDurationMinutes == null
                  ? "Caja abierta"
                  : `${detail.overview.totalDurationMinutes} min`
              }
            />
          </div>
        </section>

        <section className="mt-3 rounded-[18px] border border-[var(--ui-color-border)] bg-slate-50/90 p-3">
          <div className="flex min-w-0 items-center justify-between gap-2">
            <p className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">
              Esperado vs contado
            </p>
            <span
              className={`rounded-full border px-3 py-1 text-xs font-semibold ${differenceBadgeClass(
                difference.differenceState,
              )}`}
            >
              {differenceTitle(difference.differenceState)}
            </span>
          </div>
          <div className="mt-3 grid gap-2 rounded-[16px] border border-[var(--ui-color-border)] bg-white p-3">
            <FieldRow label="Monto inicial" value={formatMoney(difference.openingAmount)} />
            <FieldRow label="Ventas efectivo" value={formatMoney(difference.cashSalesAmount)} />
            <FieldRow label="Devoluciones" value={formatMoney(difference.cashRefundsAmount)} />
            <FieldRow
              label="Pagos op."
              value={formatMoney(difference.cashOperationalPaymentsAmount)}
            />
            <FieldRow
              label="Descuentos op."
              value={formatMoney(difference.cashOperationalDiscountsAmount)}
            />
            <FieldRow label="Esperado" value={formatMoney(difference.expectedCashAmount)} />
            <FieldRow label="Contado" value={formatMoney(difference.countedCashAmount)} />
            <FieldRow label="Diferencia" value={formatMoney(difference.differenceAmount)} />
          </div>
          {difference.note ? (
            <p className="mt-2 rounded-[14px] border border-amber-200 bg-[var(--ui-color-warning-soft)] px-3 py-2 text-sm font-semibold text-[var(--ui-color-warning)]">
              {difference.note}
            </p>
          ) : null}
        </section>

        <section className="mt-3 rounded-[18px] border border-[var(--ui-color-border)] bg-white p-3">
          <SectionTitle count={detail.paymentBreakdown.length} title="Metodos de pago" />
          <div className="mt-3 grid gap-1.5">
            {detail.paymentBreakdown.map((row) => (
              <div
                className="grid grid-cols-[minmax(0,1fr)_5.5rem_5.5rem_5.5rem] gap-2 rounded-[14px] border border-[var(--ui-color-border)] bg-slate-50 px-3 py-2 text-sm"
                key={row.paymentMethodCode}
              >
                <span className="truncate font-semibold text-slate-950">
                  {row.paymentMethodCode}
                </span>
                <span className="text-right text-slate-600">{formatMoney(row.salesAmount)}</span>
                <span className="text-right text-slate-600">{formatMoney(row.refundAmount)}</span>
                <span className="text-right font-semibold text-slate-950">
                  {formatMoney(row.netAmount)}
                </span>
                <span className="text-xs text-slate-500">
                  Esperado {formatMoney(row.expectedAmount)}
                </span>
                <span className="text-right text-xs text-slate-500">
                  Contado {formatMoney(row.countedAmount)}
                </span>
                <span className="text-right text-xs text-slate-500">
                  Var. {formatMoney(row.varianceAmount)}
                </span>
                <span className="text-right text-xs text-slate-500">{row.currencyCode}</span>
              </div>
            ))}
          </div>
        </section>

        <section className="mt-3 rounded-[18px] border border-[var(--ui-color-border)] bg-white p-3">
          <SectionTitle count={detail.includedTickets.length} title="Tickets incluidos" />
          <div className="mt-3 grid max-h-72 gap-1.5 overflow-y-auto pr-1">
            {detail.includedTickets.length > 0 ? (
              detail.includedTickets.map((ticket) => (
                <TicketRow key={ticket.ticketId} ticket={ticket} />
              ))
            ) : (
              <p className="rounded-[14px] border border-dashed border-[var(--ui-color-border)] px-3 py-3 text-sm text-slate-600">
                Este corte no tiene tickets asociados.
              </p>
            )}
          </div>
        </section>

        <section className="mt-3 rounded-[18px] border border-[var(--ui-color-border)] bg-white p-3">
          <SectionTitle count={detail.returnsRefunds.length} title="Devoluciones" />
          <div className="mt-3 grid gap-1.5">
            {detail.returnsRefunds.length > 0 ? (
              detail.returnsRefunds.map((refund) => <RefundRow key={refund.id} refund={refund} />)
            ) : (
              <p className="rounded-[14px] border border-dashed border-[var(--ui-color-border)] px-3 py-3 text-sm text-slate-600">
                Este corte no tiene devoluciones asociadas.
              </p>
            )}
          </div>
        </section>

        <section className="mt-3 rounded-[18px] border border-[var(--ui-color-border)] bg-white p-3">
          <SectionTitle count={detail.operationalPayments.length} title="Pagos operativos" />
          <div className="mt-3 grid gap-1.5">
            {detail.operationalPayments.length > 0 ? (
              detail.operationalPayments.map((payment) => (
                <OperationalPaymentRow key={payment.id} payment={payment} />
              ))
            ) : (
              <p className="rounded-[14px] border border-dashed border-[var(--ui-color-border)] px-3 py-3 text-sm text-slate-600">
                Este corte no tiene pagos operativos asociados.
              </p>
            )}
          </div>
        </section>

        <section className="mt-3 rounded-[18px] border border-[var(--ui-color-border)] bg-white p-3">
          <SectionTitle
            count={detail.correctionsAdjustments.length}
            title="Correcciones / ajustes"
          />
          <div className="mt-3 grid gap-1.5">
            {detail.correctionsAdjustments.length > 0 ? (
              detail.correctionsAdjustments.map((document) => (
                <div
                  className="rounded-[14px] border border-[var(--ui-color-border)] bg-slate-50 px-3 py-2 text-sm"
                  key={document.id}
                >
                  <div className="flex min-w-0 items-center justify-between gap-2">
                    <span className="truncate font-semibold text-slate-950">{document.folio}</span>
                    <span className="shrink-0 text-xs font-semibold text-slate-500">
                      {document.documentType}
                    </span>
                  </div>
                  <p className="mt-1 truncate text-xs text-slate-500">
                    {document.operatorName ?? "Sin operador"} -{" "}
                    {formatDateTime(document.occurredAt)}
                  </p>
                </div>
              ))
            ) : (
              <p className="rounded-[14px] border border-dashed border-[var(--ui-color-border)] px-3 py-3 text-sm text-slate-600">
                Este corte no tiene correcciones asociadas.
              </p>
            )}
          </div>
        </section>

        <section className="mt-3 rounded-[18px] border border-[var(--ui-color-border)] bg-white p-3">
          <SectionTitle title="Conteo por denominacion" />
          {detail.denominationCount.isSupported ? (
            <div className="mt-3 grid gap-1.5">
              {detail.denominationCount.lines.map((line) => (
                <FieldRow
                  key={line.denomination}
                  label={formatMoney(line.denomination)}
                  value={`${line.quantity} - ${formatMoney(line.subtotal)}`}
                />
              ))}
            </div>
          ) : (
            <p className="mt-3 rounded-[14px] border border-dashed border-[var(--ui-color-border)] px-3 py-3 text-sm text-slate-600">
              {detail.denominationCount.note ?? "Conteo por denominacion no disponible."}
            </p>
          )}
        </section>

        <section className="mt-3 rounded-[18px] border border-[var(--ui-color-border)] bg-white p-3">
          <SectionTitle title="Conciliacion y auditoria" />
          <div className="mt-3 grid gap-1.5">
            <FieldRow label="Conciliacion" value={detail.reconciliationStatus.status} />
            <FieldRow
              label="Documento"
              value={detail.reconciliationStatus.relatedDocumentId ?? "N/A"}
            />
            {detail.auditTimeline.map((event) => (
              <div
                className="rounded-[14px] border border-[var(--ui-color-border)] bg-slate-50 px-3 py-2 text-sm"
                key={`${event.eventCode}-${event.occurredAt}`}
              >
                <div className="flex min-w-0 items-center justify-between gap-2">
                  <span className="truncate font-semibold text-slate-950">{event.label}</span>
                  <span className="shrink-0 text-xs text-slate-500">
                    {formatDateTime(event.occurredAt)}
                  </span>
                </div>
                <p className="mt-1 truncate text-xs text-slate-500">
                  {event.actorName ?? "Sistema"} {event.summary ? `- ${event.summary}` : ""}
                </p>
              </div>
            ))}
          </div>
        </section>

        <section className="mt-3 rounded-[18px] border border-[var(--ui-color-border)] bg-white p-3">
          <SectionTitle count={detail.relatedDocuments.length} title="Documentos relacionados" />
          <div className="mt-3 grid gap-1.5">
            {detail.relatedDocuments.length > 0 ? (
              detail.relatedDocuments.map((document) => (
                <div
                  className="rounded-[14px] border border-[var(--ui-color-border)] bg-slate-50 px-3 py-2 text-sm"
                  key={`${document.documentType}-${document.id}`}
                >
                  <div className="flex min-w-0 items-center justify-between gap-2">
                    <span className="truncate font-semibold text-slate-950">{document.folio}</span>
                    <span className="shrink-0 text-xs font-semibold text-slate-500">
                      {document.status}
                    </span>
                  </div>
                  <p className="mt-1 truncate text-xs text-slate-500">
                    {document.documentType}
                    {document.amount ? ` - ${formatMoney(document.amount)}` : ""}
                  </p>
                </div>
              ))
            ) : (
              <p className="rounded-[14px] border border-dashed border-[var(--ui-color-border)] px-3 py-3 text-sm text-slate-600">
                Este corte no tiene documentos relacionados.
              </p>
            )}
          </div>
        </section>
      </div>

      <div className="grid shrink-0 grid-cols-3 gap-2 border-t border-[var(--ui-color-border)] p-3">
        <button
          className="h-10 rounded-2xl border border-[var(--ui-color-border)] bg-white px-3 text-sm font-semibold text-slate-700 transition hover:border-[var(--ui-color-info)] hover:text-[var(--ui-color-info)] focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
          type="button"
          onClick={() => onCopyFolio(detail.overview.folio)}
        >
          Copiar folio
        </button>
        <button
          className="h-10 rounded-2xl border border-[var(--ui-color-border)] bg-white px-3 text-sm font-semibold text-slate-500 disabled:cursor-not-allowed disabled:opacity-50"
          disabled
          title="Exportacion de reporte pendiente de endpoint backend"
          type="button"
        >
          Exportar
        </button>
        <button
          className="h-10 rounded-2xl border border-[var(--ui-color-border)] bg-white px-3 text-sm font-semibold text-slate-500 disabled:cursor-not-allowed disabled:opacity-50"
          disabled
          title="Reporte imprimible pendiente de endpoint backend"
          type="button"
        >
          Imprimir
        </button>
      </div>
    </aside>
  );
}
