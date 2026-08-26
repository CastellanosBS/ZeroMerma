import { AdminEmptyState } from "../../components/AdminEmptyState";
import type {
  AdminCorrectionListItem,
  AdminReturnListItem,
  AdminReturnsCorrectionsTab,
} from "../types";

function formatMoney(value: string, currencyCode = "MXN"): string {
  const numericValue = Number(value);
  if (!Number.isFinite(numericValue)) {
    return `${value} ${currencyCode}`;
  }
  return new Intl.NumberFormat("es-MX", { currency: currencyCode, style: "currency" }).format(numericValue);
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
    COMMITTED: "Confirmado",
  };
  return labels[value] ?? value;
}

function formatDocumentType(value: string): string {
  const labels: Record<string, string> = {
    BRANCH_TRANSFER_SHIPMENT: "Envio",
    COUNTER_TRANSFER: "Mostrador",
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

function statusClass(value: string): string {
  if (value === "COMMITTED") {
    return "border-emerald-200 bg-[var(--ui-color-success-soft)] text-[var(--ui-color-success)]";
  }
  return "border-[var(--ui-color-border)] bg-slate-50 text-slate-600";
}

function netEffectClass(value: string): string {
  if (value === "NEGATIVE") {
    return "border-rose-200 bg-[var(--ui-color-danger-soft)] text-[var(--ui-color-danger)]";
  }
  if (value === "POSITIVE") {
    return "border-emerald-200 bg-[var(--ui-color-success-soft)] text-[var(--ui-color-success)]";
  }
  return "border-[var(--ui-color-border)] bg-slate-50 text-slate-600";
}

interface AdminReturnsCorrectionsTableProps {
  activeTab: AdminReturnsCorrectionsTab;
  corrections: AdminCorrectionListItem[];
  errorMessage?: string | null;
  isLoading?: boolean;
  onCopyFolio: (folio: string) => void;
  onPageChange: (tab: AdminReturnsCorrectionsTab, page: number) => void;
  onSelectCorrection: (item: AdminCorrectionListItem) => void;
  onSelectReturn: (item: AdminReturnListItem) => void;
  page: number;
  pageSize: number;
  returns: AdminReturnListItem[];
  selectedCorrectionId?: string | null;
  selectedReturnId?: string | null;
  total: number;
}

export function AdminReturnsCorrectionsTable({
  activeTab,
  corrections,
  errorMessage,
  isLoading = false,
  onCopyFolio,
  onPageChange,
  onSelectCorrection,
  onSelectReturn,
  page,
  pageSize,
  returns,
  selectedCorrectionId,
  selectedReturnId,
  total,
}: AdminReturnsCorrectionsTableProps) {
  const isReturns = activeTab === "returns";
  const totalPages = Math.max(1, Math.ceil(total / pageSize));
  const canGoPrevious = page > 1;
  const canGoNext = page < totalPages;

  return (
    <section className="flex min-h-0 min-w-0 flex-col overflow-hidden rounded-[20px] border border-[var(--ui-color-border)] bg-white">
      <div className="flex min-w-0 shrink-0 items-center justify-between gap-3 border-b border-[var(--ui-color-border)] px-3 py-2.5">
        <div className="min-w-0">
          <h3 className="truncate text-base font-semibold text-slate-950">
            {isReturns ? "Devoluciones registradas" : "Correcciones registradas"}
          </h3>
          <p className="truncate text-xs text-slate-500">
            {isReturns
              ? "Reembolsos, tickets origen y efecto de caja."
              : "Documento origen, ajuste aplicado y efecto neto."}
          </p>
        </div>
        <span className="shrink-0 rounded-full border border-[var(--ui-color-border)] bg-white px-3 py-1 text-xs font-semibold text-slate-600">
          {total} registros
        </span>
      </div>

      <div className="min-h-0 min-w-0 flex-1 overflow-y-auto p-2.5">
        {isLoading ? (
          <AdminEmptyState
            description="Consultando documentos reales del backend."
            title={isReturns ? "Cargando devoluciones" : "Cargando correcciones"}
          />
        ) : errorMessage ? (
          <AdminEmptyState description={errorMessage} title="No se pudo cargar la informacion" />
        ) : isReturns ? (
          returns.length > 0 ? (
            <div className="grid min-w-0 gap-1.5">
              {returns.map((item) => {
                const isSelected = item.id === selectedReturnId;
                return (
                  <article
                    className={[
                      "grid min-w-0 gap-2 rounded-[16px] border px-3 py-2 transition xl:grid-cols-[minmax(8rem,0.8fr)_minmax(8rem,0.8fr)_minmax(10rem,0.9fr)_minmax(0,0.9fr)_minmax(7rem,0.6fr)_minmax(0,0.75fr)_auto]",
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
                      onClick={() => onSelectReturn(item)}
                    >
                      <span className="block truncate text-sm font-semibold text-slate-950">{item.folio}</span>
                      <span className="block truncate text-xs text-slate-500">{item.returnedLineCount} lineas</span>
                    </button>
                    <button
                      className="min-w-0 text-left focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
                      title={item.originalTicketFolio}
                      type="button"
                      onClick={() => onSelectReturn(item)}
                    >
                      <span className="block truncate text-sm font-semibold text-[var(--ui-color-primary)]">
                        {item.originalTicketFolio}
                      </span>
                      <span className="block truncate text-xs text-slate-500">Ticket origen</span>
                    </button>
                    <button
                      className="min-w-0 text-left focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
                      title={formatDateTime(item.createdAt)}
                      type="button"
                      onClick={() => onSelectReturn(item)}
                    >
                      <span className="block truncate text-sm font-semibold text-slate-950">
                        {formatDateTime(item.createdAt)}
                      </span>
                      <span className="block truncate text-xs text-slate-500">{item.branchName}</span>
                    </button>
                    <button
                      className="min-w-0 text-left focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
                      title={`${item.workstationName} - ${item.operatorName}`}
                      type="button"
                      onClick={() => onSelectReturn(item)}
                    >
                      <span className="block truncate text-sm font-semibold text-slate-950">{item.operatorName}</span>
                      <span className="block truncate text-xs text-slate-500">{item.workstationName}</span>
                    </button>
                    <button
                      className="min-w-0 text-left xl:text-right focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
                      title={formatMoney(item.refundedAmount)}
                      type="button"
                      onClick={() => onSelectReturn(item)}
                    >
                      <span className="block truncate text-sm font-semibold text-slate-950">
                        {formatMoney(item.refundedAmount)}
                      </span>
                      <span className="block truncate text-xs text-slate-500">{item.refundMethod}</span>
                    </button>
                    <button
                      className="min-w-0 text-left focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
                      type="button"
                      onClick={() => onSelectReturn(item)}
                    >
                      <span
                        className={`inline-flex max-w-full rounded-full border px-2.5 py-1 text-xs font-semibold ${statusClass(item.status)}`}
                      >
                        <span className="truncate">{formatStatus(item.status)}</span>
                      </span>
                    </button>
                    <div className="flex shrink-0 items-center justify-end gap-1.5">
                      <button
                        className="rounded-full border border-[var(--ui-color-border)] bg-white px-2.5 py-1 text-xs font-semibold text-slate-700 transition hover:border-[var(--ui-color-info)] hover:text-[var(--ui-color-info)] focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
                        type="button"
                        onClick={() => onSelectReturn(item)}
                      >
                        Ver
                      </button>
                      <button
                        className="rounded-full border border-[var(--ui-color-border)] bg-white px-2.5 py-1 text-xs font-semibold text-slate-700 transition hover:border-[var(--ui-color-info)] hover:text-[var(--ui-color-info)] focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
                        type="button"
                        onClick={() => onCopyFolio(item.folio)}
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
              description="No hay devoluciones para este periodo. Ajusta los filtros o selecciona otro rango de fechas."
              title="Sin devoluciones"
            />
          )
        ) : corrections.length > 0 ? (
          <div className="grid min-w-0 gap-1.5">
            {corrections.map((item) => {
              const isSelected = item.id === selectedCorrectionId;
              return (
                <article
                  className={[
                    "grid min-w-0 gap-2 rounded-[16px] border px-3 py-2 transition xl:grid-cols-[minmax(8rem,0.8fr)_minmax(8rem,0.85fr)_minmax(8rem,0.78fr)_minmax(10rem,0.9fr)_minmax(0,0.95fr)_minmax(7rem,0.6fr)_auto]",
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
                    onClick={() => onSelectCorrection(item)}
                  >
                    <span className="block truncate text-sm font-semibold text-slate-950">{item.folio}</span>
                    <span className="block truncate text-xs text-slate-500">{item.lineCount} lineas</span>
                  </button>
                  <button
                    className="min-w-0 text-left focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
                    title={item.originalDocumentFolio}
                    type="button"
                    onClick={() => onSelectCorrection(item)}
                  >
                    <span className="block truncate text-sm font-semibold text-[var(--ui-color-primary)]">
                      {item.originalDocumentFolio}
                    </span>
                    <span className="block truncate text-xs text-slate-500">
                      {formatDocumentType(item.originalDocumentType)}
                    </span>
                  </button>
                  <button
                    className="min-w-0 text-left focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
                    type="button"
                    onClick={() => onSelectCorrection(item)}
                  >
                    <span
                      className={`inline-flex max-w-full rounded-full border px-2.5 py-1 text-xs font-semibold ${netEffectClass(item.netEffect)}`}
                    >
                      <span className="truncate">{formatNetEffect(item.netEffect)}</span>
                    </span>
                    <span className="mt-1 block truncate text-xs text-slate-500">{item.netEffectQuantity}</span>
                  </button>
                  <button
                    className="min-w-0 text-left focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
                    title={formatDateTime(item.createdAt)}
                    type="button"
                    onClick={() => onSelectCorrection(item)}
                  >
                    <span className="block truncate text-sm font-semibold text-slate-950">
                      {formatDateTime(item.createdAt)}
                    </span>
                    <span className="block truncate text-xs text-slate-500">{item.branchName}</span>
                  </button>
                  <button
                    className="min-w-0 text-left focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
                    title={item.reasonName}
                    type="button"
                    onClick={() => onSelectCorrection(item)}
                  >
                    <span className="block truncate text-sm font-semibold text-slate-950">{item.reasonName}</span>
                    <span className="block truncate text-xs text-slate-500">{item.operatorName}</span>
                  </button>
                  <button
                    className="min-w-0 text-left focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
                    type="button"
                    onClick={() => onSelectCorrection(item)}
                  >
                    <span
                      className={`inline-flex max-w-full rounded-full border px-2.5 py-1 text-xs font-semibold ${statusClass(item.status)}`}
                    >
                      <span className="truncate">{formatStatus(item.status)}</span>
                    </span>
                  </button>
                  <div className="flex shrink-0 items-center justify-end gap-1.5">
                    <button
                      className="rounded-full border border-[var(--ui-color-border)] bg-white px-2.5 py-1 text-xs font-semibold text-slate-700 transition hover:border-[var(--ui-color-info)] hover:text-[var(--ui-color-info)] focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
                      type="button"
                      onClick={() => onSelectCorrection(item)}
                    >
                      Ver
                    </button>
                    <button
                      className="rounded-full border border-[var(--ui-color-border)] bg-white px-2.5 py-1 text-xs font-semibold text-slate-700 transition hover:border-[var(--ui-color-info)] hover:text-[var(--ui-color-info)] focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
                      type="button"
                      onClick={() => onCopyFolio(item.folio)}
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
            description="No hay correcciones registradas para este periodo."
            title="Sin correcciones"
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
            onClick={() => onPageChange(activeTab, page - 1)}
          >
            Anterior
          </button>
          <button
            className="rounded-full border border-[var(--ui-color-border)] bg-white px-3 py-1.5 font-semibold text-slate-700 disabled:cursor-not-allowed disabled:opacity-40"
            disabled={!canGoNext}
            type="button"
            onClick={() => onPageChange(activeTab, page + 1)}
          >
            Siguiente
          </button>
        </div>
      </div>
    </section>
  );
}
