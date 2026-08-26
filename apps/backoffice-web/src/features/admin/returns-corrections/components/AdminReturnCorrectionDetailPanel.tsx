import { AdminEmptyState } from "../../components/AdminEmptyState";
import type {
  AdminCorrectionDetail,
  AdminCorrectionListItem,
  AdminReturnDetail,
  AdminReturnListItem,
  AdminReturnsCorrectionsTab,
} from "../types";

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

function formatDocumentType(value: string): string {
  const labels: Record<string, string> = {
    BRANCH_TRANSFER_SHIPMENT: "Envio a sucursal",
    COUNTER_TRANSFER: "Paso a mostrador",
    WASTE_RECORD: "Merma",
  };
  return labels[value] ?? value;
}

function formatNetEffect(value: string): string {
  const labels: Record<string, string> = {
    NEGATIVE: "Negativo",
    NEUTRAL: "Neutral",
    POSITIVE: "Positivo",
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

function DetailLink({ href, label }: { href: string | null | undefined; label: string }) {
  if (!href) {
    return null;
  }

  return (
    <a
      className="inline-flex h-8 items-center justify-center rounded-full border border-[var(--ui-color-border)] bg-white px-3 text-xs font-semibold text-slate-700 transition hover:border-[var(--ui-color-info)] hover:text-[var(--ui-color-info)] focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
      href={href}
    >
      {label}
    </a>
  );
}

interface AdminReturnCorrectionDetailPanelProps {
  activeTab: AdminReturnsCorrectionsTab;
  correctionDetail: AdminCorrectionDetail | null;
  detailErrorMessage?: string | null;
  isLoading?: boolean;
  returnDetail: AdminReturnDetail | null;
  selectedCorrection: AdminCorrectionListItem | null;
  selectedReturn: AdminReturnListItem | null;
}

export function AdminReturnCorrectionDetailPanel({
  activeTab,
  correctionDetail,
  detailErrorMessage,
  isLoading = false,
  returnDetail,
  selectedCorrection,
  selectedReturn,
}: AdminReturnCorrectionDetailPanelProps) {
  const selected = activeTab === "returns" ? selectedReturn : selectedCorrection;

  if (!selected) {
    return (
      <aside className="flex min-h-0 min-w-0 flex-col overflow-hidden rounded-[20px] border border-[var(--ui-color-border)] bg-white">
        <div className="border-b border-[var(--ui-color-border)] px-4 py-3">
          <p className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">Detalle</p>
          <h3 className="mt-1 text-lg font-semibold text-slate-950">Sin documento seleccionado</h3>
        </div>
        <div className="min-h-0 flex-1 p-4">
          <AdminEmptyState
            description="Selecciona un documento para revisar su detalle, impacto y documentos relacionados."
            title="Selecciona un documento"
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
          <h3 className="mt-1 truncate text-lg font-semibold text-slate-950">{selected.folio}</h3>
        </div>
        <div className="min-h-0 flex-1 p-4">
          <AdminEmptyState description="Consultando detalle real del backend." title="Cargando documento" />
        </div>
      </aside>
    );
  }

  if (detailErrorMessage || (activeTab === "returns" ? !returnDetail : !correctionDetail)) {
    return (
      <aside className="flex min-h-0 min-w-0 flex-col overflow-hidden rounded-[20px] border border-[var(--ui-color-border)] bg-white">
        <div className="border-b border-[var(--ui-color-border)] px-4 py-3">
          <p className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">Detalle</p>
          <h3 className="mt-1 truncate text-lg font-semibold text-slate-950">{selected.folio}</h3>
        </div>
        <div className="min-h-0 flex-1 p-4">
          <AdminEmptyState
            description={detailErrorMessage ?? "No se pudo cargar el detalle del documento."}
            title="Detalle no disponible"
          />
        </div>
      </aside>
    );
  }

  if (activeTab === "returns" && returnDetail) {
    return <ReturnDetailContent detail={returnDetail} />;
  }

  if (activeTab === "corrections" && correctionDetail) {
    return <CorrectionDetailContent detail={correctionDetail} />;
  }

  return null;
}

function ReturnDetailContent({ detail }: { detail: AdminReturnDetail }) {
  return (
    <aside className="flex min-h-0 min-w-0 flex-col overflow-hidden rounded-[20px] border border-[var(--ui-color-border)] bg-white">
      <div className="shrink-0 border-b border-[var(--ui-color-border)] px-4 py-3">
        <div className="flex min-w-0 items-start justify-between gap-3">
          <div className="min-w-0">
            <p className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">Devolucion</p>
            <h3 className="mt-1 truncate text-lg font-semibold text-slate-950" title={detail.overview.folio}>
              {detail.overview.folio}
            </h3>
          </div>
          <span className="rounded-full border border-emerald-200 bg-[var(--ui-color-success-soft)] px-3 py-1 text-xs font-semibold text-[var(--ui-color-success)]">
            {detail.overview.status}
          </span>
        </div>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto p-3">
        <section className="rounded-[18px] border border-[var(--ui-color-border)] bg-slate-50/80 p-3">
          <div className="flex items-center justify-between gap-3">
            <span className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">Reembolso</span>
            <strong className="text-xl font-semibold text-slate-950">
              {formatMoney(detail.refundImpact.refundAmount, detail.refundImpact.currencyCode)}
            </strong>
          </div>
          <div className="mt-3 grid gap-1.5">
            <FieldRow label="Metodo" value={detail.refundImpact.refundMethod} />
            <FieldRow label="Caja" value={detail.overview.workstationName} />
            <FieldRow label="Sesion" value={detail.refundImpact.cashSessionId} />
            <FieldRow label="Movimiento" value={detail.refundImpact.linkedCashMovementId ?? "No disponible"} />
          </div>
        </section>

        <section className="mt-3 rounded-[18px] border border-[var(--ui-color-border)] bg-white p-3">
          <div className="flex items-center justify-between gap-2">
            <p className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">Ticket origen</p>
            <DetailLink href="/admin/ventas" label="Abrir ventas" />
          </div>
          <div className="mt-3 grid gap-1.5">
            <FieldRow label="Folio" value={detail.originalTicket.folio} />
            <FieldRow label="Fecha" value={formatDateTime(detail.originalTicket.saleDate)} />
            <FieldRow label="Total" value={formatMoney(detail.originalTicket.totalAmount)} />
            <FieldRow label="Pago" value={detail.originalTicket.paymentMethodsLabel} />
            <FieldRow label="Cajero" value={detail.originalTicket.cashierName} />
          </div>
        </section>

        <section className="mt-3 rounded-[18px] border border-[var(--ui-color-border)] bg-white p-3">
          <p className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">Motivo y contexto</p>
          <div className="mt-3 grid gap-1.5">
            <FieldRow label="Motivo" value={detail.overview.reasonName} />
            <FieldRow label="Operador" value={detail.overview.operatorName} />
            <FieldRow label="Sucursal" value={detail.overview.branchName} />
            <FieldRow label="Fecha" value={formatDateTime(detail.overview.createdAt)} />
          </div>
          {detail.overview.notes ? (
            <p className="mt-3 rounded-[14px] border border-[var(--ui-color-border)] bg-slate-50 px-3 py-2 text-sm text-slate-700">
              {detail.overview.notes}
            </p>
          ) : null}
        </section>

        <section className="mt-3 rounded-[18px] border border-[var(--ui-color-border)] bg-white p-3">
          <div className="flex items-center justify-between gap-2">
            <p className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">Lineas devueltas</p>
            <span className="rounded-full border border-[var(--ui-color-border)] bg-white px-2.5 py-1 text-xs font-semibold text-slate-600">
              {detail.returnedLines.length} lineas
            </span>
          </div>
          <div className="mt-3 grid gap-1.5">
            {detail.returnedLines.map((line) => (
              <div
                className="grid min-w-0 grid-cols-[minmax(0,1fr)_4.5rem_5.5rem] items-center gap-2 rounded-[14px] border border-[var(--ui-color-border)] bg-slate-50 px-3 py-2 text-sm"
                key={line.id}
              >
                <div className="min-w-0">
                  <p className="truncate font-semibold text-slate-950" title={line.productName}>
                    {line.productName}
                  </p>
                  <p className="truncate text-xs text-slate-500" title={line.dispositionCode}>
                    {line.productCode} - {line.dispositionCode}
                  </p>
                </div>
                <span className="text-right font-semibold text-slate-700">{line.returnedQuantity}</span>
                <span className="text-right font-semibold text-slate-950">{formatMoney(line.refundAmount)}</span>
              </div>
            ))}
          </div>
        </section>

        <section className="mt-3 rounded-[18px] border border-[var(--ui-color-border)] bg-white p-3">
          <p className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">Documentos relacionados</p>
          <div className="mt-3 grid gap-1.5">
            {detail.relatedDocuments.length > 0 ? (
              detail.relatedDocuments.map((document) => (
                <div className="rounded-[14px] border border-[var(--ui-color-border)] bg-slate-50 px-3 py-2 text-sm" key={document.id}>
                  <div className="flex min-w-0 items-center justify-between gap-2">
                    <span className="truncate font-semibold text-slate-950">{document.folio}</span>
                    <span className="shrink-0 text-xs font-semibold text-slate-500">{document.documentType}</span>
                  </div>
                  <DetailLink href={document.routeHint} label="Abrir modulo" />
                </div>
              ))
            ) : (
              <p className="rounded-[14px] border border-dashed border-[var(--ui-color-border)] px-3 py-3 text-sm text-slate-600">
                Esta devolucion no tiene documentos relacionados.
              </p>
            )}
          </div>
        </section>
      </div>

      <div className="shrink-0 border-t border-[var(--ui-color-border)] p-3">
        <p className="rounded-[16px] border border-[var(--ui-color-border)] bg-slate-50 px-3 py-2 text-xs font-semibold text-slate-600">
          {detail.availableActions.creationNote}
        </p>
      </div>
    </aside>
  );
}

function CorrectionDetailContent({ detail }: { detail: AdminCorrectionDetail }) {
  return (
    <aside className="flex min-h-0 min-w-0 flex-col overflow-hidden rounded-[20px] border border-[var(--ui-color-border)] bg-white">
      <div className="shrink-0 border-b border-[var(--ui-color-border)] px-4 py-3">
        <div className="flex min-w-0 items-start justify-between gap-3">
          <div className="min-w-0">
            <p className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">Correccion</p>
            <h3 className="mt-1 truncate text-lg font-semibold text-slate-950" title={detail.overview.folio}>
              {detail.overview.folio}
            </h3>
          </div>
          <span className="rounded-full border border-[var(--ui-color-border)] bg-slate-50 px-3 py-1 text-xs font-semibold text-slate-600">
            {formatNetEffect(detail.overview.netEffect)}
          </span>
        </div>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto p-3">
        <section className="rounded-[18px] border border-[var(--ui-color-border)] bg-slate-50/80 p-3">
          <div className="flex items-center justify-between gap-3">
            <span className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">Efecto neto</span>
            <strong className="text-xl font-semibold text-slate-950">{detail.netEffect.totalUnitsAffected}</strong>
          </div>
          <div className="mt-3 grid gap-1.5">
            <FieldRow label="Inventario" value={detail.netEffect.inventoryEffect} />
            <FieldRow label="Caja" value={detail.netEffect.cashEffect} />
            <FieldRow label="Tipo" value={formatNetEffect(detail.netEffect.netEffect)} />
          </div>
        </section>

        <section className="mt-3 rounded-[18px] border border-[var(--ui-color-border)] bg-white p-3">
          <div className="flex items-center justify-between gap-2">
            <p className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">Documento origen</p>
            <DetailLink href={detail.originalDocument.routeHint} label="Abrir origen" />
          </div>
          <div className="mt-3 grid gap-1.5">
            <FieldRow label="Folio" value={detail.originalDocument.folio} />
            <FieldRow label="Tipo" value={formatDocumentType(detail.originalDocument.documentType)} />
            <FieldRow label="Fecha" value={formatDateTime(detail.originalDocument.occurredAt)} />
            <FieldRow label="Operador" value={detail.originalDocument.operatorName} />
            <FieldRow label="Sucursal" value={detail.originalDocument.branchName} />
          </div>
        </section>

        <section className="mt-3 rounded-[18px] border border-[var(--ui-color-border)] bg-white p-3">
          <p className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">Motivo</p>
          <div className="mt-3 grid gap-1.5">
            <FieldRow label="Motivo" value={detail.reasonNotes.reasonName} />
            <FieldRow label="Operador" value={detail.overview.operatorName} />
            <FieldRow label="Fecha" value={formatDateTime(detail.overview.createdAt)} />
          </div>
          {detail.reasonNotes.notes ? (
            <p className="mt-3 rounded-[14px] border border-[var(--ui-color-border)] bg-slate-50 px-3 py-2 text-sm text-slate-700">
              {detail.reasonNotes.notes}
            </p>
          ) : null}
        </section>

        <section className="mt-3 rounded-[18px] border border-[var(--ui-color-border)] bg-white p-3">
          <div className="flex items-center justify-between gap-2">
            <p className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">Antes / despues</p>
            <span className="rounded-full border border-[var(--ui-color-border)] bg-white px-2.5 py-1 text-xs font-semibold text-slate-600">
              {detail.affectedLines.length} lineas
            </span>
          </div>
          <div className="mt-3 grid gap-1.5">
            {detail.affectedLines.length > 0 ? (
              detail.affectedLines.map((line) => (
                <div
                  className="grid min-w-0 grid-cols-[minmax(0,1fr)_4.5rem_4.5rem_4.5rem] items-center gap-2 rounded-[14px] border border-[var(--ui-color-border)] bg-slate-50 px-3 py-2 text-sm"
                  key={line.id}
                >
                  <div className="min-w-0">
                    <p className="truncate font-semibold text-slate-950" title={line.productName}>
                      {line.productName}
                    </p>
                    <p className="truncate text-xs text-slate-500">{line.productCode}</p>
                  </div>
                  <span className="text-right text-xs font-semibold text-slate-500">
                    {line.originalQuantity ?? "N/A"}
                  </span>
                  <span className="text-right text-xs font-semibold text-slate-950">
                    {line.correctedQuantity ?? "N/A"}
                  </span>
                  <span className="text-right text-xs font-semibold text-[var(--ui-color-primary)]">
                    {line.differenceQuantity}
                  </span>
                </div>
              ))
            ) : (
              <p className="rounded-[14px] border border-dashed border-[var(--ui-color-border)] px-3 py-3 text-sm text-slate-600">
                Esta correccion ajusto el destino del documento sin cambiar lineas.
              </p>
            )}
          </div>
        </section>

        <section className="mt-3 rounded-[18px] border border-[var(--ui-color-border)] bg-white p-3">
          <p className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">Documentos relacionados</p>
          <div className="mt-3 grid gap-1.5">
            {detail.relatedDocuments.length > 0 ? (
              detail.relatedDocuments.map((document) => (
                <div className="rounded-[14px] border border-[var(--ui-color-border)] bg-slate-50 px-3 py-2 text-sm" key={document.id}>
                  <div className="flex min-w-0 items-center justify-between gap-2">
                    <span className="truncate font-semibold text-slate-950">{document.folio}</span>
                    <span className="shrink-0 text-xs font-semibold text-slate-500">{formatDocumentType(document.documentType)}</span>
                  </div>
                  <DetailLink href={document.routeHint} label="Abrir modulo" />
                </div>
              ))
            ) : (
              <p className="rounded-[14px] border border-dashed border-[var(--ui-color-border)] px-3 py-3 text-sm text-slate-600">
                Este documento no tiene relaciones adicionales.
              </p>
            )}
          </div>
        </section>
      </div>

      <div className="shrink-0 border-t border-[var(--ui-color-border)] p-3">
        <p className="rounded-[16px] border border-[var(--ui-color-border)] bg-slate-50 px-3 py-2 text-xs font-semibold text-slate-600">
          {detail.availableActions.creationNote}
        </p>
      </div>
    </aside>
  );
}
