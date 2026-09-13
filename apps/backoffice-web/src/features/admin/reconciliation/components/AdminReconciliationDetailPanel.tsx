import { AdminActionButton } from "../../components/AdminActionButton";
import { AdminEmptyState } from "../../components/AdminEmptyState";
import type {
  AdminReconciliationDetail,
  AdminReconciliationListItem,
  AdminReconciliationRelatedDocument,
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

function directionLabel(value: string): string {
  const labels: Record<string, string> = {
    EXACT: "Exacta",
    OVERAGE: "Sobrante",
    SHORTAGE: "Faltante",
  };
  return labels[value] ?? value;
}

function directionBadgeClass(value: string): string {
  if (value === "OVERAGE") {
    return "border-emerald-200 bg-[var(--ui-color-success-soft)] text-[var(--ui-color-success)]";
  }
  if (value === "SHORTAGE") {
    return "border-rose-200 bg-[var(--ui-color-danger-soft)] text-[var(--ui-color-danger)]";
  }
  return "border-slate-200 bg-slate-50 text-slate-700";
}

function FieldRow({ label, value, title }: { label: string; title?: string; value: string }) {
  return (
    <div className="grid min-w-0 grid-cols-[8.75rem_minmax(0,1fr)] gap-2 text-sm">
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

function RelatedDocumentRow({ document }: { document: AdminReconciliationRelatedDocument }) {
  const content = (
    <>
      <div className="flex min-w-0 items-center justify-between gap-2">
        <span className="truncate font-semibold text-slate-950">{document.folio}</span>
        <span className="shrink-0 text-xs font-semibold text-slate-500">{document.status}</span>
      </div>
      <p className="mt-1 truncate text-xs text-slate-500">
        {document.documentType}
        {document.amount ? ` - ${formatMoney(document.amount)}` : ""}
        {document.occurredAt ? ` - ${formatDateTime(document.occurredAt)}` : ""}
      </p>
    </>
  );

  if (document.routeHint) {
    return (
      <a
        className="block rounded-[14px] border border-[var(--ui-color-border)] bg-slate-50 px-3 py-2 text-sm transition hover:border-[var(--ui-color-info)]"
        href={document.routeHint}
      >
        {content}
      </a>
    );
  }

  return (
    <div className="rounded-[14px] border border-[var(--ui-color-border)] bg-slate-50 px-3 py-2 text-sm">
      {content}
    </div>
  );
}

interface AdminReconciliationDetailPanelProps {
  detail: AdminReconciliationDetail | null;
  errorMessage?: string | null;
  isLoading?: boolean;
  onCopyFolio: (folio: string) => void;
  onResolve: (item: AdminReconciliationListItem) => void;
  selectedReconciliation: AdminReconciliationListItem | null;
}

export function AdminReconciliationDetailPanel({
  detail,
  errorMessage,
  isLoading = false,
  onCopyFolio,
  onResolve,
  selectedReconciliation,
}: AdminReconciliationDetailPanelProps) {
  if (!selectedReconciliation) {
    return (
      <aside className="flex min-h-0 min-w-0 flex-col overflow-hidden rounded-[20px] border border-[var(--ui-color-border)] bg-white">
        <div className="border-b border-[var(--ui-color-border)] px-4 py-3">
          <p className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">
            Detalle
          </p>
          <h3 className="mt-1 text-lg font-semibold text-slate-950">
            Sin conciliacion seleccionada
          </h3>
        </div>
        <div className="min-h-0 flex-1 p-4">
          <AdminEmptyState
            description="Selecciona una conciliacion para revisar diferencia, documentos relacionados y resolucion."
            title="Selecciona una conciliacion"
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
            {selectedReconciliation.folio}
          </h3>
        </div>
        <div className="min-h-0 flex-1 p-4">
          <AdminEmptyState
            description="Consultando contexto financiero, origen y resolucion."
            title="Cargando conciliacion"
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
            {selectedReconciliation.folio}
          </h3>
        </div>
        <div className="min-h-0 flex-1 p-4">
          <AdminEmptyState
            description={errorMessage ?? "No se pudo cargar el detalle de la conciliacion."}
            title="Detalle no disponible"
          />
        </div>
      </aside>
    );
  }

  return (
    <aside className="flex min-h-0 min-w-0 flex-col overflow-hidden rounded-[20px] border border-[var(--ui-color-border)] bg-white">
      <div className="shrink-0 border-b border-[var(--ui-color-border)] px-4 py-3">
        <div className="flex min-w-0 items-start justify-between gap-3">
          <div className="min-w-0">
            <p className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">
              Conciliacion
            </p>
            <h3 className="mt-1 truncate text-lg font-semibold text-slate-950">
              {detail.overview.folio}
            </h3>
          </div>
          <span className="rounded-full border border-[var(--ui-color-border)] bg-slate-50 px-3 py-1 text-xs font-semibold text-slate-600">
            {statusLabel(detail.overview.status)}
          </span>
        </div>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto p-3">
        <section className="rounded-[18px] border border-[var(--ui-color-border)] bg-white p-3">
          <SectionTitle title="Resumen" />
          <div className="mt-3 grid gap-1.5">
            <FieldRow label="Sucursal" value={detail.overview.branchName} />
            <FieldRow label="Caja" value={detail.overview.workstationName} />
            <FieldRow label="Responsable" value={detail.overview.operatorName} />
            <FieldRow label="Origen" value={sourceLabel(detail.overview.sourceType)} />
            <FieldRow label="Documento" value={detail.overview.sourceReference} />
            <FieldRow label="Metodo" value={detail.overview.paymentMethod} />
            <FieldRow label="Creada" value={formatDateTime(detail.overview.createdAt)} />
            <FieldRow label="Resuelta" value={formatDateTime(detail.overview.resolvedAt)} />
          </div>
        </section>

        <section className="mt-3 rounded-[18px] border border-[var(--ui-color-border)] bg-slate-50/90 p-3">
          <div className="flex min-w-0 items-center justify-between gap-2">
            <p className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">
              Diferencia
            </p>
            <span
              className={`rounded-full border px-3 py-1 text-xs font-semibold ${directionBadgeClass(
                detail.differenceBreakdown.direction,
              )}`}
            >
              {directionLabel(detail.differenceBreakdown.direction)}
            </span>
          </div>
          <div className="mt-3 grid gap-2 rounded-[16px] border border-[var(--ui-color-border)] bg-white p-3">
            <FieldRow
              label="Esperado"
              value={formatMoney(detail.differenceBreakdown.expectedAmount)}
            />
            <FieldRow
              label="Reportado"
              value={formatMoney(detail.differenceBreakdown.actualAmount)}
            />
            <FieldRow
              label="Diferencia"
              value={formatMoney(detail.differenceBreakdown.differenceAmount)}
            />
            <FieldRow label="Tolerancia" value={detail.differenceBreakdown.toleranceStatus} />
          </div>
          {detail.differenceBreakdown.toleranceNote ? (
            <p className="mt-2 rounded-[14px] border border-amber-200 bg-[var(--ui-color-warning-soft)] px-3 py-2 text-sm font-semibold text-[var(--ui-color-warning)]">
              {detail.differenceBreakdown.toleranceNote}
            </p>
          ) : null}
        </section>

        <section className="mt-3 rounded-[18px] border border-[var(--ui-color-border)] bg-white p-3">
          <SectionTitle title="Documento origen" />
          <div className="mt-3 grid gap-1.5">
            <FieldRow label="Origen" value={sourceLabel(detail.sourceDocumentContext.sourceType)} />
            <FieldRow label="Referencia" value={detail.sourceDocumentContext.sourceReference} />
            <FieldRow
              label="Apertura"
              value={formatDateTime(detail.sourceDocumentContext.openedAt)}
            />
            <FieldRow
              label="Cierre"
              value={formatDateTime(detail.sourceDocumentContext.closedAt)}
            />
            <FieldRow
              label="Esperado"
              value={formatMoney(detail.sourceDocumentContext.expectedCashAmount)}
            />
            <FieldRow
              label="Contado"
              value={formatMoney(detail.sourceDocumentContext.countedCashAmount)}
            />
          </div>
          {detail.sourceDocumentContext.note ? (
            <p className="mt-2 rounded-[14px] border border-[var(--ui-color-border)] bg-slate-50 px-3 py-2 text-sm text-slate-600">
              {detail.sourceDocumentContext.note}
            </p>
          ) : null}
        </section>

        <section className="mt-3 rounded-[18px] border border-[var(--ui-color-border)] bg-white p-3">
          <SectionTitle title="Explicacion" />
          <div className="mt-3 grid gap-1.5">
            <FieldRow label="Motivo" value={detail.explanationReason.reasonLabel ?? "Sin motivo"} />
            <FieldRow
              label="Responsable"
              value={detail.explanationReason.responsibleUserName ?? "Sin responsable"}
            />
            <FieldRow label="Fecha" value={formatDateTime(detail.explanationReason.timestamp)} />
          </div>
          <p className="mt-2 rounded-[14px] border border-[var(--ui-color-border)] bg-slate-50 px-3 py-2 text-sm text-slate-600">
            {detail.explanationReason.notes ?? "Sin notas registradas."}
          </p>
        </section>

        <section className="mt-3 rounded-[18px] border border-[var(--ui-color-border)] bg-white p-3">
          <SectionTitle count={detail.evidence.files.length} title="Evidencia" />
          <p className="mt-3 rounded-[14px] border border-dashed border-[var(--ui-color-border)] px-3 py-3 text-sm text-slate-600">
            {detail.evidence.hasEvidence
              ? (detail.evidence.evidenceNote ?? "Evidencia registrada sin adjuntos.")
              : detail.evidence.emptyState}
          </p>
          {detail.availableActions.note ? (
            <p className="mt-2 text-xs font-semibold text-slate-500">
              {detail.availableActions.note}
            </p>
          ) : null}
        </section>

        <section className="mt-3 rounded-[18px] border border-[var(--ui-color-border)] bg-white p-3">
          <SectionTitle count={detail.relatedDocuments.length} title="Documentos relacionados" />
          <div className="mt-3 grid gap-1.5">
            {detail.relatedDocuments.length > 0 ? (
              detail.relatedDocuments.map((document) => (
                <RelatedDocumentRow
                  document={document}
                  key={`${document.documentType}-${document.id}`}
                />
              ))
            ) : (
              <p className="rounded-[14px] border border-dashed border-[var(--ui-color-border)] px-3 py-3 text-sm text-slate-600">
                Esta conciliacion no tiene documentos relacionados.
              </p>
            )}
          </div>
        </section>

        <section className="mt-3 rounded-[18px] border border-[var(--ui-color-border)] bg-white p-3">
          <SectionTitle title="Resolucion" />
          <div className="mt-3 grid gap-1.5">
            <FieldRow label="Estado" value={statusLabel(detail.resolution.status)} />
            <FieldRow
              label="Motivo final"
              value={detail.resolution.resolutionReason ?? "Pendiente"}
            />
            <FieldRow
              label="Resuelto por"
              value={detail.resolution.resolvedByUserName ?? "Pendiente"}
            />
            <FieldRow label="Fecha" value={formatDateTime(detail.resolution.resolvedAt)} />
          </div>
          <p className="mt-2 rounded-[14px] border border-[var(--ui-color-border)] bg-slate-50 px-3 py-2 text-sm text-slate-600">
            {detail.resolution.finalNotes ?? "La diferencia aun requiere explicacion final."}
          </p>
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
        <AdminActionButton
          capability="cash_finance.manage"
          branchIds={[detail.overview.branchId]}
          className="h-10 rounded-2xl border border-[var(--ui-color-border)] bg-white px-3 text-sm font-semibold text-slate-700 transition hover:border-[var(--ui-color-info)] hover:text-[var(--ui-color-info)] focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)] disabled:cursor-not-allowed disabled:opacity-40"
          disabled={!detail.availableActions.canResolve}
          type="button"
          onClick={() => onResolve(detail.overview)}
        >
          Resolver
        </AdminActionButton>
        <button
          className="h-10 rounded-2xl border border-[var(--ui-color-border)] bg-white px-3 text-sm font-semibold text-slate-500 disabled:cursor-not-allowed disabled:opacity-50"
          disabled
          title="Exportacion pendiente de endpoint backend"
          type="button"
        >
          Exportar
        </button>
      </div>
    </aside>
  );
}
