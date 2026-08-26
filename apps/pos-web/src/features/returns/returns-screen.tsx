import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Navigate, useNavigate, useRouterState } from "@tanstack/react-router";
import { useEffect, useMemo, useRef, useState } from "react";

import { useAppShellRightPanel } from "../../components/app-shell-right-panel";
import { OperationalStatus } from "../../components/operational-status";
import { PosInlineValidationMessage } from "../../components/pos-feedback";
import { PosButton, PosStatusBadge } from "../../components/pos-foundations";
import { PosSummaryPanel } from "../../components/pos-module-layout";
import {
  CentralWorkspaceSheet,
  CompactPageHeader,
  KeyValueRow,
  InlineNotice,
  ModuleStateChip,
  ProgressStepper,
  ScrollPane,
  type ProgressStepperStep,
} from "../../components/pos-module-primitives";
import {
  PosFilterBar,
  PosHistoryView,
  PosRecordTable,
  type PosRecordColumn,
} from "../../components/pos-records";
import { MoneyIcon, TrashIcon } from "../../components/pos-icons";
import { appEnv } from "../../env";
import type {
  ReturnFilterOptionView,
  ReturnHistoryListItemView,
  ReturnOriginalSaleDetailResponse,
  ReturnProductOptionView,
  ReturnSaleSearchItemView,
  ReturnScopeView,
  ReturnableSaleLineView,
  SaleReturnDetailResponse,
} from "../../lib/api-contracts";
import { openBrowserPrintWindow } from "../../lib/browser-print";
import {
  formatCompactLocalDateTime,
  formatCurrency,
  formatLocalDateTime,
} from "../../lib/formatters";
import { toOperationalErrorMessage } from "../../lib/http";
import { usePosAuthStore } from "../auth/auth-store";
import { useCurrentCashSessionQuery } from "../cash-session-open/queries";
import {
  parseMoneyToCents,
  sanitizeQuantityInput,
} from "../pos-terminal/model";
import { posInputClass } from "../pos-theme/theme";
import { useStatusMessageStore } from "../status-messages/store";
import {
  addReturnDraftLine,
  buildReturnCommitLines,
  createInitialReturnDraftState,
  formatReturnMoney,
  getReturnDraftBlockingMessages,
  getReturnDraftLineRefundCents,
  getReturnDraftTotalRefundCents,
  incrementReturnDraftLineQuantity,
  removeReturnDraftLine,
  RETURN_DISPOSITION_RESTOCK_BACKROOM,
  RETURN_DISPOSITION_RESTOCK_COUNTER,
  RETURN_DISPOSITION_SEND_TO_WASTE,
  decrementReturnDraftLineQuantity,
  setReturnDraftLineExactProduct,
  setReturnDraftLineQuantityText,
  type ReturnDraftLine,
  type ReturnDraftState,
} from "./model";
import { writeReturnReceiptToPrintWindow } from "./print";
import { commitSaleReturn } from "./returns-api";
import {
  returnSaleDetailQueryKey,
  saleReturnDetailQueryKey,
  returnsBootstrapQueryKey,
  useReturnClassProductsQueries,
  useReturnSaleDetailQuery,
  useSaleReturnDetailQuery,
  useReturnSalesQuery,
  useReturnsHistoryQuery,
  useReturnsBootstrapQuery,
} from "./queries";

const RETURN_SCOPE_OPTIONS_FALLBACK: ReturnScopeView[] = [
  { code: "CURRENT_SHIFT", label: "Turno actual" },
  { code: "TODAY", label: "Hoy" },
  { code: "RECENT", label: "Recientes" },
];

const RETURN_REASON_OPTIONS_FALLBACK = [
  { code: "CUSTOMER_REGRET", label: "Cliente cambio de opinion" },
  { code: "WRONG_ITEM", label: "Producto incorrecto" },
  { code: "QUALITY_ISSUE", label: "Problema de calidad" },
  { code: "DAMAGED_ON_DELIVERY", label: "Danado al entregar" },
  { code: "OTHER", label: "Otro" },
] as const;

const RETURN_REFUND_METHODS_FALLBACK = [
  { code: "CASH", label: "Efectivo", is_enabled: true, availability_note: null },
  {
    code: "CARD",
    label: "Tarjeta",
    is_enabled: false,
    availability_note: "Reverso de tarjeta pendiente de integracion.",
  },
  {
    code: "MIXED",
    label: "Mixto",
    is_enabled: false,
    availability_note: "Reembolso mixto pendiente de integracion.",
  },
] as const;

const RETURN_DISPOSITION_OPTIONS = [
  {
    hint: "Volvera a disponibilidad del mostrador.",
    label: "Regresar a mostrador",
    value: RETURN_DISPOSITION_RESTOCK_COUNTER,
  },
  {
    hint: "Volvera a inventario del fondo.",
    label: "Regresar a fondo",
    value: RETURN_DISPOSITION_RESTOCK_BACKROOM,
  },
  {
    hint: "No volvera a stock.",
    label: "Registrar merma",
    value: RETURN_DISPOSITION_SEND_TO_WASTE,
  },
] as const;

type ReturnsCenterSection = "history" | "lines" | "sales";
type ReturnsUiState =
  | "NO_SALE_SELECTED"
  | "SALE_SELECTED"
  | "DRAFT_IN_PROGRESS"
  | "READY_TO_CONFIRM"
  | "CONFIRMING"
  | "RETURN_CONFIRMED"
  | "RETURN_ERROR";

function createRequestId(scope: string): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return `${scope}-${crypto.randomUUID()}`;
  }

  return `${scope}-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function useDebouncedValue(value: string, delayMs: number): string {
  const [debouncedValue, setDebouncedValue] = useState(value);

  useEffect(() => {
    const timeout = window.setTimeout(() => setDebouncedValue(value), delayMs);
    return () => window.clearTimeout(timeout);
  }, [delayMs, value]);

  return debouncedValue;
}

function formatQuantity(quantity: number | string): string {
  return new Intl.NumberFormat("es-MX", {
    minimumFractionDigits: 0,
    maximumFractionDigits: 3,
  }).format(Number(quantity));
}

function formatRefundCurrency(cents: number): string {
  return formatCurrency(formatReturnMoney(cents));
}

function getReturnableLineCount(saleDetail: ReturnOriginalSaleDetailResponse): number {
  return saleDetail.lines.filter((line) => Number(line.remaining_returnable_quantity) > 0).length;
}

function getReturnableUnitsText(saleDetail: ReturnOriginalSaleDetailResponse): string {
  const total = saleDetail.lines.reduce(
    (sum, line) => sum + Number(line.remaining_returnable_quantity),
    0,
  );
  return formatQuantity(total);
}

function getSaleReturnStatusLabel(status: string): string | null {
  switch (status) {
    case "PARTIALLY_RETURNED":
      return "Devolucion parcial";
    case "FULLY_RETURNED":
      return "Devuelto";
    default:
      return null;
  }
}

function getSaleReturnStatusTone(
  status: string,
): "draft" | "success" | "warning" {
  switch (status) {
    case "PARTIALLY_RETURNED":
      return "warning";
    case "FULLY_RETURNED":
      return "success";
    default:
      return "draft";
  }
}

function getRefundMethodLabel(code: string): string {
  switch (code) {
    case "CASH":
      return "Efectivo";
    case "CARD":
      return "Tarjeta";
    case "MIXED":
      return "Mixto";
    default:
      return code;
  }
}

function getReturnStatusLabel(status: string): string {
  switch (status) {
    case "COMMITTED":
      return "Registrada";
    default:
      return status;
  }
}

function getReturnStatusTone(
  status: string,
): "confirmed" | "draft" | "success" | "warning" {
  switch (status) {
    case "COMMITTED":
      return "confirmed";
    default:
      return "draft";
  }
}


function getReturnUiStateLabel(uiState: ReturnsUiState): string {
  switch (uiState) {
    case "SALE_SELECTED":
      return "Venta seleccionada";
    case "DRAFT_IN_PROGRESS":
      return "Borrador en captura";
    case "READY_TO_CONFIRM":
      return "Listo para confirmar";
    case "CONFIRMING":
      return "Confirmando";
    case "RETURN_CONFIRMED":
      return "Confirmado";
    case "RETURN_ERROR":
      return "Error";
    default:
      return "Sin venta";
  }
}

function getReturnUiStateTone(
  uiState: ReturnsUiState,
): "muted" | "info" | "primary" | "success" | "warning" {
  switch (uiState) {
    case "READY_TO_CONFIRM":
      return "primary";
    case "CONFIRMING":
      return "info";
    case "RETURN_CONFIRMED":
      return "success";
    case "RETURN_ERROR":
      return "warning";
    case "SALE_SELECTED":
    case "DRAFT_IN_PROGRESS":
      return "info";
    default:
      return "muted";
  }
}

function getDraftLineErrorMessage(line: ReturnDraftLine): string | null {
  if (line.quantityMilliUnits <= 0) {
    return "Captura una cantidad valida.";
  }
  if (line.quantityMilliUnits > line.remainingReturnableMilliUnits) {
    return "La cantidad supera el maximo devolvible.";
  }
  if (line.exactProductRequired && line.exactProductId.trim().length === 0) {
    return "Selecciona el producto exacto requerido.";
  }
  if (line.dispositionCode.trim().length === 0) {
    return "Define el destino fisico de la linea.";
  }
  return null;
}

function getReturnableRefundAmount(line: ReturnableSaleLineView): string {
  const refundCents = Math.round(
    Number(line.remaining_returnable_quantity) * Number(line.unit_price) * 100,
  );
  return formatRefundCurrency(refundCents);
}

function applyDefaultReturnDisposition(lines: ReturnDraftLine[]): ReturnDraftLine[] {
  return lines.map((line) =>
    line.dispositionCode.trim().length > 0
      ? line
      : {
          ...line,
          dispositionCode: RETURN_DISPOSITION_RESTOCK_COUNTER,
        },
  );
}

function isSaleOlderThanThreshold(
  confirmedAt: string,
  thresholdDays: number,
  referenceTimestamp: string | null | undefined,
): boolean {
  const saleDate = new Date(confirmedAt);
  if (Number.isNaN(saleDate.getTime())) {
    return false;
  }
  const referenceDate = referenceTimestamp ? new Date(referenceTimestamp) : new Date();
  if (Number.isNaN(referenceDate.getTime())) {
    return false;
  }

  const diffMs = referenceDate.getTime() - saleDate.getTime();
  const diffDays = diffMs / (1000 * 60 * 60 * 24);
  return diffDays >= thresholdDays;
}

function getReturnUiState({
  blockedMessages,
  commitError,
  commitPending,
  draftLines,
  hasSelectedSale,
  lastCommittedReturn,
}: {
  blockedMessages: string[];
  commitError: string | null;
  commitPending: boolean;
  draftLines: ReturnDraftLine[];
  hasSelectedSale: boolean;
  lastCommittedReturn: SaleReturnDetailResponse | null;
}): ReturnsUiState {
  if (commitPending) {
    return "CONFIRMING";
  }

  if (commitError) {
    return "RETURN_ERROR";
  }

  if (lastCommittedReturn) {
    return "RETURN_CONFIRMED";
  }

  if (!hasSelectedSale) {
    return "NO_SALE_SELECTED";
  }

  if (draftLines.length === 0) {
    return "SALE_SELECTED";
  }

  return blockedMessages.length === 0 ? "READY_TO_CONFIRM" : "DRAFT_IN_PROGRESS";
}

function SelectedSaleReferenceBar({
  saleDetail,
}: {
  saleDetail: ReturnOriginalSaleDetailResponse;
}) {
  return (
    <div className="flex min-w-0 flex-wrap items-center justify-between gap-2 rounded-xl border border-[var(--pos-shell-border)] bg-white px-3 py-2">
      <div className="flex min-w-0 items-center gap-2">
        <span className="truncate text-sm font-semibold text-slate-950" title={saleDetail.folio}>
          {saleDetail.folio}
        </span>
        {getSaleReturnStatusLabel(saleDetail.return_status) ? (
          <PosStatusBadge status={getSaleReturnStatusTone(saleDetail.return_status)}>
            {getSaleReturnStatusLabel(saleDetail.return_status)}
          </PosStatusBadge>
        ) : null}
      </div>
      <div className="flex min-w-0 flex-wrap items-center justify-end gap-x-3 gap-y-1 text-xs text-slate-600">
        <span title={formatLocalDateTime(saleDetail.confirmed_at, saleDetail.branch.timezone)}>
          {formatCompactLocalDateTime(saleDetail.confirmed_at, saleDetail.branch.timezone)}
        </span>
        <span className="truncate" title={saleDetail.operator.full_name}>
          {saleDetail.operator.full_name}
        </span>
        <span>{getReturnableLineCount(saleDetail)} lineas</span>
        <span>{getReturnableUnitsText(saleDetail)} disp.</span>
        <span className="font-semibold text-slate-950">{formatCurrency(saleDetail.total_amount)}</span>
      </div>
    </div>
  );
}

function ReturnableLinesTable({
  draftLines,
  lines,
  onDecreaseQuantity,
  onDraftQuantityChange,
  onIncreaseQuantity,
  onRemove,
  onSelect,
  selectedLineId,
}: {
  draftLines: ReturnDraftLine[];
  lines: ReturnableSaleLineView[];
  onDecreaseQuantity: (line: ReturnableSaleLineView) => void;
  onDraftQuantityChange: (line: ReturnableSaleLineView, value: string) => void;
  onIncreaseQuantity: (line: ReturnableSaleLineView) => void;
  onRemove: (originalSaleLineId: string) => void;
  onSelect: (line: ReturnableSaleLineView) => void;
  selectedLineId: string | null;
}) {
  const draftByOriginalLineId = useMemo(
    () => new Map(draftLines.map((line) => [line.originalSaleLineId, line])),
    [draftLines],
  );
  const columns = useMemo<PosRecordColumn<ReturnableSaleLineView>[]>(
    () => [
      {
        header: "Producto",
        key: "article",
        renderCell: (line) => (
          <span className="block truncate font-semibold text-slate-950" title={line.catalog_name_snapshot}>
            {line.catalog_name_snapshot}
          </span>
        ),
        width: "31%",
      },
      {
        align: "right",
        header: "Vendido",
        key: "sold",
        renderCell: (line) => (
          <span className="font-medium text-slate-900">{formatQuantity(line.quantity)}</span>
        ),
        width: "12%",
      },
      {
        align: "right",
        header: "Disponible",
        key: "available",
        renderCell: (line) => (
          <span className="font-medium text-slate-900">
            {formatQuantity(line.remaining_returnable_quantity)}
          </span>
        ),
        width: "13%",
      },
      {
        align: "center",
        header: "A devolver",
        key: "return-quantity",
        renderCell: (line) => {
          const draftLine = draftByOriginalLineId.get(line.id);
          return (
            <div
              className="ml-auto grid max-w-[8.5rem] grid-cols-[1.9rem_minmax(0,1fr)_1.9rem] items-center overflow-hidden rounded-lg border border-[var(--pos-shell-border)] bg-white"
              onClick={(event) => event.stopPropagation()}
            >
              <button
                className="h-8 text-sm font-semibold text-slate-600 hover:bg-[var(--pos-shell-muted)]"
                disabled={!draftLine}
                onClick={() => onDecreaseQuantity(line)}
                type="button"
              >
                -
              </button>
              <input
                aria-label={`Cantidad a devolver de ${line.catalog_name_snapshot}`}
                className="h-8 min-w-0 border-x border-[var(--pos-shell-border)] px-1 text-center text-sm font-semibold text-slate-950 outline-none [font-variant-numeric:tabular-nums]"
                inputMode="decimal"
                onChange={(event) => onDraftQuantityChange(line, sanitizeQuantityInput(event.target.value))}
                onFocus={() => onSelect(line)}
                value={draftLine?.quantityText ?? ""}
              />
              <button
                className="h-8 text-sm font-semibold text-slate-600 hover:bg-[var(--pos-shell-muted)]"
                onClick={() => onIncreaseQuantity(line)}
                type="button"
              >
                +
              </button>
            </div>
          );
        },
        width: "20%",
      },
      {
        align: "right",
        header: "Importe",
        key: "refund",
        renderCell: (line) => {
          const draftLine = draftByOriginalLineId.get(line.id);
          return (
            <span className="font-semibold text-slate-950">
              {draftLine
                ? formatRefundCurrency(getReturnDraftLineRefundCents(draftLine))
                : getReturnableRefundAmount(line)}
            </span>
          );
        },
        width: "14%",
      },
      {
        align: "right",
        header: "",
        key: "remove",
        renderCell: (line) => {
          const draftLine = draftByOriginalLineId.get(line.id);
          return draftLine ? (
            <button
              aria-label={`Quitar ${line.catalog_name_snapshot}`}
              className="ml-auto grid h-8 w-8 place-items-center rounded-full text-[var(--ui-color-danger)] hover:bg-[var(--ui-color-danger-soft)]"
              onClick={(event) => {
                event.stopPropagation();
                onRemove(line.id);
              }}
              type="button"
            >
              <TrashIcon className="h-4 w-4" />
            </button>
          ) : null;
        },
        width: "8%",
      },
    ],
    [
      draftByOriginalLineId,
      onDecreaseQuantity,
      onDraftQuantityChange,
      onIncreaseQuantity,
      onRemove,
      onSelect,
    ],
  );

  return (
    <PosRecordTable
      columns={columns}
      emptyDescription="La venta seleccionada no tiene lineas disponibles para devolver."
      emptyTitle="Sin lineas devolvibles"
      getKey={(line) => line.id}
      onSelect={onSelect}
      records={lines}
      selectedKey={selectedLineId}
      tableAriaLabel="Lineas devolvibles"
    />
  );
}

function ReturnSummaryPanel({
  blockedMessages,
  commitError,
  commitPending,
  draftState,
  exactProductOptions,
  exactProductsError,
  exactProductsLoading,
  highRiskMessages,
  isHighRiskAcknowledgementRequired,
  onCommit,
  onDispositionChangeAll,
  onExactProductChangeSelectedLine,
  onHighRiskAcknowledgedChange,
  onNotesChange,
  onReasonChange,
  onRefundMethodChange,
  onViewHistory,
  reasonOptions,
  refundMethodOptions,
  saleDetail,
  selectedDraftLine,
  selectedLineValidationMessage,
  uiState,
}: {
  blockedMessages: string[];
  commitError: string | null;
  commitPending: boolean;
  draftState: ReturnDraftState;
  exactProductOptions: ReturnProductOptionView[];
  exactProductsError: string | null;
  exactProductsLoading: boolean;
  highRiskMessages: string[];
  isHighRiskAcknowledgementRequired: boolean;
  onCommit: () => void;
  onDispositionChangeAll: (value: string) => void;
  onExactProductChangeSelectedLine: (value: string) => void;
  onHighRiskAcknowledgedChange: (value: boolean) => void;
  onNotesChange: (value: string) => void;
  onReasonChange: (value: string) => void;
  onRefundMethodChange: (value: string) => void;
  onViewHistory: () => void;
  reasonOptions: ReadonlyArray<{ code: string; label: string }>;
  refundMethodOptions: ReadonlyArray<{
    availability_note?: string | null;
    code: string;
    is_enabled: boolean;
    label: string;
  }>;
  saleDetail: ReturnOriginalSaleDetailResponse | null;
  selectedDraftLine: ReturnDraftLine | null;
  selectedLineValidationMessage: string | null;
  uiState: ReturnsUiState;
}) {
  const [isNotesOpen, setNotesOpen] = useState(draftState.notes.trim().length > 0);
  const refundTotalText = formatRefundCurrency(getReturnDraftTotalRefundCents(draftState.lines));
  const currentDispositionCode =
    draftState.lines.find((line) => line.dispositionCode.trim().length > 0)?.dispositionCode ??
    RETURN_DISPOSITION_RESTOCK_COUNTER;
  const selectedRefundMethod = refundMethodOptions.find(
    (method) => method.code === draftState.refundMethodCode,
  );

  useEffect(() => {
    if (draftState.notes.trim().length > 0) {
      setNotesOpen(true);
    }
  }, [draftState.notes]);

  const footer = !saleDetail ? (
    <PosButton onClick={onViewHistory} type="button" variant="neutral">
      Ver historial
    </PosButton>
  ) : (
    <div className="grid gap-2">
      <PosButton
        disabled={blockedMessages.length > 0 || commitPending}
        leadingIcon={<MoneyIcon className="h-4 w-4" />}
        onClick={onCommit}
        type="button"
      >
        {commitPending ? "Registrando..." : "Confirmar devolucion"}
      </PosButton>
      <PosButton onClick={onViewHistory} type="button" variant="neutral">
        Ver historial
      </PosButton>
    </div>
  );

  return (
    <PosSummaryPanel
      description={saleDetail ? "Motivo, reembolso y confirmacion." : "Selecciona una venta para comenzar."}
      footer={footer}
      stateLabel={getReturnUiStateLabel(uiState)}
      stateTone={
        uiState === "RETURN_CONFIRMED"
          ? "success"
          : uiState === "READY_TO_CONFIRM"
            ? "ready"
            : uiState === "RETURN_ERROR"
              ? "warning"
              : "draft"
      }
      title="Devolucion"
    >
      <div className="grid h-full min-h-0 gap-3 overflow-hidden">
        {commitError ? <PosInlineValidationMessage tone="error">{commitError}</PosInlineValidationMessage> : null}

        {!saleDetail ? (
          <div className="rounded-xl border border-dashed border-[var(--pos-shell-border)] bg-[var(--pos-shell-muted)] px-3 py-4 text-sm text-slate-600">
            Selecciona una venta para comenzar.
          </div>
        ) : (
          <>
            <div className="grid gap-1 rounded-xl border border-[var(--pos-shell-border)] bg-[var(--pos-shell-muted)] px-3 py-2.5">
              <KeyValueRow label="Ticket" title={saleDetail.folio} value={saleDetail.folio} />
              <KeyValueRow label="Lineas" value={String(draftState.lines.length)} />
              <KeyValueRow label="Monto a devolver" value={refundTotalText} />
            </div>

            {selectedDraftLine?.exactProductRequired ? (
              <div className="grid gap-2 rounded-xl border border-[var(--pos-shell-border)] bg-white px-3 py-2.5">
                <p className="truncate text-sm font-semibold text-slate-950" title={selectedDraftLine.lineName}>
                  {selectedDraftLine.lineName}
                </p>
                {selectedDraftLine.exactProductRequired ? (
                  <select
                    className={`${posInputClass} h-9 px-2 text-sm`}
                    disabled={exactProductsLoading}
                    onChange={(event) => onExactProductChangeSelectedLine(event.target.value)}
                    value={selectedDraftLine.exactProductId}
                  >
                    <option value="">
                      {exactProductsLoading ? "Cargando productos..." : "Producto exacto"}
                    </option>
                    {exactProductOptions.map((product) => (
                      <option key={product.id} value={product.id}>
                        {product.name}
                      </option>
                    ))}
                  </select>
                ) : null}
                {selectedLineValidationMessage ? (
                  <PosInlineValidationMessage tone="warning">{selectedLineValidationMessage}</PosInlineValidationMessage>
                ) : null}
                {exactProductsError ? (
                  <PosInlineValidationMessage tone="error">{exactProductsError}</PosInlineValidationMessage>
                ) : null}
              </div>
            ) : null}

            <div className="grid gap-2 rounded-xl border border-[var(--pos-shell-border)] bg-white px-3 py-2.5">
              {draftState.lines.length > 0 ? (
                <select
                  aria-label="Destino fisico"
                  className={`${posInputClass} h-9 px-2 text-sm`}
                  onChange={(event) => onDispositionChangeAll(event.target.value)}
                  value={currentDispositionCode}
                >
                  {RETURN_DISPOSITION_OPTIONS.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              ) : null}
              <select
                aria-label="Motivo de devolucion"
                className={`${posInputClass} h-9 px-2 text-sm`}
                onChange={(event) => onReasonChange(event.target.value)}
                value={draftState.reasonCode}
              >
                <option value="">Motivo</option>
                {reasonOptions.map((reason) => (
                  <option key={reason.code} value={reason.code}>
                    {reason.label}
                  </option>
                ))}
              </select>
              <select
                aria-label="Metodo de reembolso"
                className={`${posInputClass} h-9 px-2 text-sm`}
                onChange={(event) => onRefundMethodChange(event.target.value)}
                value={draftState.refundMethodCode}
              >
                <option value="">Metodo de reembolso</option>
                {refundMethodOptions.map((method) => (
                  <option disabled={!method.is_enabled} key={method.code} value={method.code}>
                    {method.label}
                  </option>
                ))}
              </select>
              {selectedRefundMethod?.availability_note ? (
                <PosInlineValidationMessage tone="warning">
                  {selectedRefundMethod.availability_note}
                </PosInlineValidationMessage>
              ) : null}
            </div>

            <div className="rounded-xl border border-[var(--pos-shell-border)] bg-white">
              <button
                className="flex w-full items-center justify-between gap-2 px-3 py-2 text-left text-sm font-semibold text-slate-950"
                onClick={() => setNotesOpen((current) => !current)}
                type="button"
              >
                <span>{draftState.notes.trim().length > 0 ? "Observacion" : "Agregar observacion"}</span>
                <span className="text-xs text-slate-500">{isNotesOpen ? "Ocultar" : "Abrir"}</span>
              </button>
              {isNotesOpen ? (
                <div className="border-t border-[var(--pos-shell-border)] p-3 pt-2">
                  <textarea
                    className={`${posInputClass} min-h-[4.5rem] resize-y px-3 py-2 text-sm`}
                    onChange={(event) => onNotesChange(event.target.value)}
                    placeholder="Observacion opcional"
                    value={draftState.notes}
                  />
                </div>
              ) : null}
            </div>

            {isHighRiskAcknowledgementRequired ? (
              <div className="grid gap-2 rounded-xl border border-[rgba(187,122,22,0.18)] bg-[var(--ui-color-warning-soft)] px-3 py-2.5">
                {highRiskMessages.map((message) => (
                  <PosInlineValidationMessage key={message} tone="warning">
                    {message}
                  </PosInlineValidationMessage>
                ))}
                <label className="flex items-start gap-2 text-sm text-slate-700">
                  <input
                    checked={draftState.highRiskAcknowledged}
                    onChange={(event) => onHighRiskAcknowledgedChange(event.target.checked)}
                    type="checkbox"
                  />
                  <span>Confirmo que la devolucion fue validada.</span>
                </label>
              </div>
            ) : null}

            {blockedMessages.map((message) => (
              <PosInlineValidationMessage key={message} tone="warning">
                {message}
              </PosInlineValidationMessage>
            ))}
          </>
        )}
      </div>
    </PosSummaryPanel>
  );
}

function ReturnHistoryDetailPanel({
  onNewReturn,
  onPrintReceipt,
  onViewTicket,
  returnDetail,
  selectedHistoryRecord,
}: {
  onNewReturn: () => void;
  onPrintReceipt: () => void;
  onViewTicket: () => void;
  returnDetail: SaleReturnDetailResponse | null;
  selectedHistoryRecord: ReturnHistoryListItemView | null;
}) {
  if (!returnDetail) {
    return (
      <PosSummaryPanel
        description="Selecciona una devolucion para ver su detalle."
        footer={
          <PosButton onClick={onNewReturn} type="button" variant="neutral">
            Nueva devolucion
          </PosButton>
        }
        stateLabel="Historial"
        stateTone="draft"
        title="Detalle de devolucion"
      >
        <div className="rounded-xl border border-dashed border-[var(--pos-shell-border)] bg-[var(--pos-shell-muted)] px-3 py-4 text-sm text-slate-600">
          Selecciona una devolucion del historial.
        </div>
      </PosSummaryPanel>
    );
  }

  return (
    <PosSummaryPanel
      description={`Ticket original ${returnDetail.original_sale_folio}`}
      footer={
        <div className="grid gap-2">
          <PosButton onClick={onPrintReceipt} type="button">
            Reimprimir comprobante
          </PosButton>
          <div className="grid grid-cols-2 gap-2">
            <PosButton onClick={onViewTicket} type="button" variant="neutral">
              Ver ticket
            </PosButton>
            <PosButton onClick={onNewReturn} type="button" variant="neutral">
              Nueva devolucion
            </PosButton>
          </div>
        </div>
      }
      stateLabel={getReturnStatusLabel(selectedHistoryRecord?.status ?? "COMMITTED")}
      stateTone={getReturnStatusTone(selectedHistoryRecord?.status ?? "COMMITTED")}
      title="Detalle de devolucion"
    >
      <div className="grid h-full min-h-0 gap-3 overflow-hidden">
        <div className="grid gap-1 rounded-xl border border-[var(--pos-shell-border)] bg-[var(--pos-shell-muted)] px-3 py-2.5">
          <KeyValueRow label="Folio" title={returnDetail.folio} value={returnDetail.folio} />
          <KeyValueRow
            label="Fecha"
            value={formatCompactLocalDateTime(
              returnDetail.created_at_utc,
              returnDetail.branch.timezone,
            )}
          />
          <KeyValueRow label="Cajero" title={returnDetail.created_by.full_name} value={returnDetail.created_by.full_name} />
          <KeyValueRow label="Monto" value={formatCurrency(returnDetail.total_refund_amount)} />
          <KeyValueRow label="Metodo" value={getRefundMethodLabel(returnDetail.refund_method_code)} />
          <KeyValueRow label="Motivo" title={returnDetail.reason_name} value={returnDetail.reason_name} />
        </div>

        <div className="min-h-0 overflow-hidden rounded-xl border border-[var(--pos-shell-border)] bg-white">
          <div className="grid grid-cols-[minmax(0,1fr)_4.25rem_5rem] gap-2 border-b border-[var(--pos-shell-border)] bg-[var(--pos-shell-muted)] px-3 py-2 text-[11px] font-semibold uppercase tracking-[0.08em] text-slate-500">
            <span>Producto</span>
            <span className="text-right">Cant.</span>
            <span className="text-right">Importe</span>
          </div>
          <ScrollPane className="max-h-[18rem] divide-y divide-[var(--pos-shell-border)]">
            {returnDetail.lines.map((line) => (
              <div
                className="grid grid-cols-[minmax(0,1fr)_4.25rem_5rem] items-center gap-2 px-3 py-2"
                key={line.id}
              >
                <span className="truncate text-sm font-semibold text-slate-950" title={line.original_catalog_name_snapshot}>
                  {line.original_catalog_name_snapshot}
                </span>
                <span className="text-right text-sm font-semibold text-slate-700 [font-variant-numeric:tabular-nums]">
                  {formatQuantity(line.returned_quantity)}
                </span>
                <span className="text-right text-sm font-semibold text-slate-950 [font-variant-numeric:tabular-nums]">
                  {formatCurrency(line.refund_line_total_amount)}
                </span>
              </div>
            ))}
          </ScrollPane>
        </div>
      </div>
    </PosSummaryPanel>
  );
}

export function ReturnsScreen() {
  const accessToken = usePosAuthStore((state) => state.accessToken);
  const showError = useStatusMessageStore((state) => state.showError);
  const showSuccess = useStatusMessageStore((state) => state.showSuccess);
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const returnsBootstrapQuery = useReturnsBootstrapQuery();
  const currentCashSessionQuery = useCurrentCashSessionQuery();
  const [selectedScope, setSelectedScope] = useState("CURRENT_SHIFT");
  const [searchText, setSearchText] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [historyScope, setHistoryScope] = useState("CURRENT_SHIFT");
  const [historySearchText, setHistorySearchText] = useState("");
  const [historyDateFrom, setHistoryDateFrom] = useState("");
  const [historyDateTo, setHistoryDateTo] = useState("");
  const [selectedHistoryCreatedByUserId, setSelectedHistoryCreatedByUserId] = useState("");
  const [selectedHistoryReasonCode, setSelectedHistoryReasonCode] = useState("");
  const [selectedHistoryReturnId, setSelectedHistoryReturnId] = useState<string | null>(null);
  const [selectedSaleId, setSelectedSaleId] = useState<string | null>(null);
  const [centerSection, setCenterSection] = useState<ReturnsCenterSection>("sales");
  const [selectedDraftLineId, setSelectedDraftLineId] = useState<string | null>(null);
  const [draftState, setDraftState] = useState<ReturnDraftState>(createInitialReturnDraftState);
  const [lastCommittedReturn, setLastCommittedReturn] = useState<SaleReturnDetailResponse | null>(
    null,
  );
  const [commitError, setCommitError] = useState<string | null>(null);
  const routeSaleId = useRouterState({
    select: (state) => {
      const rawSaleId = (state.location.search as Record<string, unknown> | undefined)?.saleId;
      return typeof rawSaleId === "string" && rawSaleId.length > 0 ? rawSaleId : null;
    },
  });
  const searchInputRef = useRef<HTMLInputElement | null>(null);
  const debouncedSearchText = useDebouncedValue(searchText, 220);
  const historySearchInputRef = useRef<HTMLInputElement | null>(null);
  const debouncedHistorySearchText = useDebouncedValue(historySearchText, 220);

  const returnSalesQuery = useReturnSalesQuery(
    selectedScope,
    debouncedSearchText,
    dateFrom,
    dateTo,
  );
  const returnsHistoryQuery = useReturnsHistoryQuery(
    historyScope,
    debouncedHistorySearchText,
    historyDateFrom,
    historyDateTo,
    selectedHistoryCreatedByUserId,
    selectedHistoryReasonCode,
  );
  const returnSaleDetailQuery = useReturnSaleDetailQuery(selectedSaleId);
  const selectedHistoryReturnQuery = useSaleReturnDetailQuery(selectedHistoryReturnId);
  const selectedSale = returnSaleDetailQuery.data ?? null;
  const selectedHistoryReturn = selectedHistoryReturnQuery.data ?? null;

  useEffect(() => {
    if (!returnsBootstrapQuery.data) {
      return;
    }

    setSelectedScope(returnsBootstrapQuery.data.default_scope);
    setHistoryScope(returnsBootstrapQuery.data.default_scope);
  }, [returnsBootstrapQuery.data]);

  useEffect(() => {
    if (!routeSaleId) {
      return;
    }

    setSelectedScope("RECENT");
    setSearchText("");
    setSelectedSaleId(routeSaleId);
  }, [routeSaleId]);

  useEffect(() => {
    const sales = returnSalesQuery.data?.sales ?? [];
    if (!selectedSaleId) {
      return;
    }

    if (sales.some((sale) => sale.id === selectedSaleId)) {
      return;
    }

    if (routeSaleId && selectedSaleId === routeSaleId) {
      return;
    }

    setSelectedSaleId(null);
  }, [returnSalesQuery.data, routeSaleId, selectedSaleId]);

  useEffect(() => {
    setDraftState(createInitialReturnDraftState());
    setSelectedDraftLineId(null);
    setCommitError(null);
    setLastCommittedReturn(null);
  }, [selectedSaleId]);

  useEffect(() => {
    if (!selectedSaleId) {
      setCenterSection((current) => (current === "history" ? current : "sales"));
      return;
    }

    setCenterSection((current) => (current === "history" ? current : "lines"));
  }, [selectedSaleId]);

  useEffect(() => {
    const historyRecords = returnsHistoryQuery.data?.records ?? [];
    if (historyRecords.length === 0) {
      setSelectedHistoryReturnId(null);
      return;
    }

    if (
      selectedHistoryReturnId &&
      historyRecords.some((record) => record.id === selectedHistoryReturnId)
    ) {
      return;
    }

    if (lastCommittedReturn) {
      const committedRecord = historyRecords.find((record) => record.id === lastCommittedReturn.id);
      if (committedRecord) {
        setSelectedHistoryReturnId(committedRecord.id);
        return;
      }
    }

    setSelectedHistoryReturnId(historyRecords[0]?.id ?? null);
  }, [lastCommittedReturn, returnsHistoryQuery.data, selectedHistoryReturnId]);

  useEffect(() => {
    if (
      selectedDraftLineId &&
      !draftState.lines.some((line) => line.originalSaleLineId === selectedDraftLineId)
    ) {
      setSelectedDraftLineId(draftState.lines[0]?.originalSaleLineId ?? null);
    }
  }, [draftState.lines, selectedDraftLineId]);

  const updateDraftState = (updater: (current: ReturnDraftState) => ReturnDraftState) => {
    setDraftState((current) => updater(current));
    setCommitError(null);
    setLastCommittedReturn(null);
  };

  const classIdsNeedingExactProduct = useMemo(() => {
    const uniqueIds = new Set<string>();
    for (const line of draftState.lines) {
      if (line.exactProductRequired) {
        uniqueIds.add(line.productClassId);
      }
    }
    return [...uniqueIds];
  }, [draftState.lines]);
  const exactProductQueries = useReturnClassProductsQueries(classIdsNeedingExactProduct);

  const exactProductsByClassId = useMemo(
    () =>
      classIdsNeedingExactProduct.reduce<Record<string, ReturnProductOptionView[]>>(
        (result, classId, index) => {
          result[classId] = exactProductQueries[index]?.data?.products ?? [];
          return result;
        },
        {},
      ),
    [classIdsNeedingExactProduct, exactProductQueries],
  );

  const exactProductErrorsByClassId = useMemo(
    () =>
      classIdsNeedingExactProduct.reduce<Record<string, string | null>>(
        (result, classId, index) => {
          const query = exactProductQueries[index];
          result[classId] = query?.error
            ? toOperationalErrorMessage(
                query.error,
                "No fue posible cargar los productos exactos para esta clase.",
              )
            : null;
          return result;
        },
        {},
      ),
    [classIdsNeedingExactProduct, exactProductQueries],
  );

  const selectedDraftLine = useMemo(
    () =>
      selectedDraftLineId
        ? draftState.lines.find((line) => line.originalSaleLineId === selectedDraftLineId) ?? null
        : null,
    [draftState.lines, selectedDraftLineId],
  );

  const selectedDraftLineExactProductOptions = selectedDraftLine
    ? exactProductsByClassId[selectedDraftLine.productClassId] ?? []
    : [];
  const selectedDraftLineExactProductsError = selectedDraftLine
    ? exactProductErrorsByClassId[selectedDraftLine.productClassId] ?? null
    : null;
  const selectedDraftLineExactProductsLoading = selectedDraftLine
    ? classIdsNeedingExactProduct.includes(selectedDraftLine.productClassId) &&
      exactProductQueries[
        classIdsNeedingExactProduct.indexOf(selectedDraftLine.productClassId)
      ]?.isPending === true
    : false;

  const scopeOptions =
    returnsBootstrapQuery.data?.available_scopes.length
      ? returnsBootstrapQuery.data.available_scopes
      : RETURN_SCOPE_OPTIONS_FALLBACK;
  const reasonOptions =
    returnsBootstrapQuery.data?.return_reasons.length
      ? returnsBootstrapQuery.data.return_reasons
      : RETURN_REASON_OPTIONS_FALLBACK;
  const refundMethodOptions =
    returnsBootstrapQuery.data?.refund_methods.length
      ? returnsBootstrapQuery.data.refund_methods
      : RETURN_REFUND_METHODS_FALLBACK;

  useEffect(() => {
    if (!selectedSale || draftState.refundMethodCode.trim().length > 0) {
      return;
    }

    const defaultRefundMethod = refundMethodOptions.find((method) => method.is_enabled)?.code;
    if (!defaultRefundMethod) {
      return;
    }

    setDraftState((current) =>
      current.refundMethodCode.trim().length > 0
        ? current
        : {
            ...current,
            refundMethodCode: defaultRefundMethod,
          },
    );
  }, [draftState.refundMethodCode, refundMethodOptions, selectedSale]);

  const historyScopeOptions =
    returnsHistoryQuery.data?.available_scopes.length
      ? returnsHistoryQuery.data.available_scopes
      : scopeOptions;
  const historyUserOptions: ReturnFilterOptionView[] =
    returnsHistoryQuery.data?.available_users ?? [];
  const historyReasonOptions: ReturnFilterOptionView[] =
    returnsHistoryQuery.data?.available_reasons.length
      ? returnsHistoryQuery.data.available_reasons
      : reasonOptions.map((reason) => ({
          value: reason.code,
          label: reason.label,
        }));
  const sales = returnSalesQuery.data?.sales ?? [];
  const branchTimeZone = returnsBootstrapQuery.data?.branch.timezone ?? "America/Hermosillo";
  const historyRecords = returnsHistoryQuery.data?.records ?? [];
  const returnableLines =
    selectedSale?.lines.filter((line) => Number(line.remaining_returnable_quantity) > 0) ?? [];
  const refundTotalCents = getReturnDraftTotalRefundCents(draftState.lines);
  const highRefundAmountThresholdCents = parseMoneyToCents(
    String(returnsBootstrapQuery.data?.return_controls.high_refund_amount_threshold ?? "0"),
  );
  const oldSaleDaysThreshold =
    returnsBootstrapQuery.data?.return_controls.old_sale_days_threshold ?? 0;
  const isHighAmountReturn =
    highRefundAmountThresholdCents !== null &&
    highRefundAmountThresholdCents > 0 &&
    refundTotalCents >= highRefundAmountThresholdCents;
  const isOldSaleReturn =
    selectedSale !== null &&
    oldSaleDaysThreshold > 0 &&
    isSaleOlderThanThreshold(
      selectedSale.confirmed_at,
      oldSaleDaysThreshold,
      returnsBootstrapQuery.data?.local_timestamp,
    );
  const highRiskMessages = [
    isHighAmountReturn
      ? `El reembolso supera ${formatCurrency(
          returnsBootstrapQuery.data?.return_controls.high_refund_amount_threshold ?? "0.00",
        )}.`
      : null,
    isOldSaleReturn
      ? `La venta supera el umbral de ${oldSaleDaysThreshold} dias y pasara a revision de backoffice.`
      : null,
  ].filter((message): message is string => message !== null);
  const selectedRefundMethod = refundMethodOptions.find(
    (method) => method.code === draftState.refundMethodCode,
  );
  const additionalBlockingMessages = [
    selectedRefundMethod && !selectedRefundMethod.is_enabled
      ? selectedRefundMethod.availability_note ??
        "El metodo de reembolso seleccionado no esta disponible."
      : null,
  ].filter((message): message is string => message !== null);
  const isHighRiskAcknowledgementRequired =
    returnsBootstrapQuery.data?.return_controls.high_risk_requires_acknowledgement === true &&
    highRiskMessages.length > 0;
  const blockingMessages = getReturnDraftBlockingMessages({
    additionalBlockingMessages,
    hasHighRiskAcknowledgement: draftState.highRiskAcknowledged,
    hasSelectedSale: selectedSale !== null,
    highRiskAcknowledgementRequired: isHighRiskAcknowledgementRequired,
    lines: draftState.lines,
    reasonCode: draftState.reasonCode,
    refundMethodCode: draftState.refundMethodCode,
  });
  const uiState = getReturnUiState({
    blockedMessages: blockingMessages,
    commitError,
    commitPending: false,
    draftLines: draftState.lines,
    hasSelectedSale: selectedSale !== null,
    lastCommittedReturn,
  });
  const selectedLineValidationMessage = selectedDraftLine
    ? getDraftLineErrorMessage(selectedDraftLine)
    : null;

  const handleSelectReturnableLine = (line: ReturnableSaleLineView) => {
    try {
      updateDraftState((current) => ({
        ...current,
        lines: applyDefaultReturnDisposition(addReturnDraftLine(current.lines, line)),
      }));
      setSelectedDraftLineId(line.id);
      setCenterSection("lines");
    } catch (error) {
      setCommitError(
        toOperationalErrorMessage(error, "No fue posible preparar la linea para devolucion."),
      );
    }
  };

  const handleReturnableLineQuantityChange = (
    line: ReturnableSaleLineView,
    value: string,
  ) => {
    try {
      updateDraftState((current) => {
        const nextLines = applyDefaultReturnDisposition(addReturnDraftLine(current.lines, line));
        return {
          ...current,
          lines: setReturnDraftLineQuantityText(nextLines, line.id, value),
        };
      });
      setSelectedDraftLineId(line.id);
      setCenterSection("lines");
    } catch (error) {
      setCommitError(
        toOperationalErrorMessage(error, "No fue posible ajustar la cantidad de devolucion."),
      );
    }
  };

  const handleIncrementReturnableLineQuantity = (line: ReturnableSaleLineView) => {
    updateDraftState((current) => ({
      ...current,
      lines: incrementReturnDraftLineQuantity(
        applyDefaultReturnDisposition(addReturnDraftLine(current.lines, line)),
        line.id,
      ),
    }));
    setSelectedDraftLineId(line.id);
  };

  const handleDecrementReturnableLineQuantity = (line: ReturnableSaleLineView) => {
    updateDraftState((current) => ({
      ...current,
      lines: decrementReturnDraftLineQuantity(
        applyDefaultReturnDisposition(addReturnDraftLine(current.lines, line)),
        line.id,
      ),
    }));
    setSelectedDraftLineId(line.id);
  };

  const handleRemoveSelectedDraftLine = (originalSaleLineId: string) => {
    let nextSelectedDraftLineId: string | null = null;
    updateDraftState((current) => {
      const nextLines = removeReturnDraftLine(current.lines, originalSaleLineId);
      nextSelectedDraftLineId = nextLines[0]?.originalSaleLineId ?? null;
      return {
        ...current,
        lines: nextLines,
      };
    });
    setSelectedDraftLineId(nextSelectedDraftLineId);
  };

  const commitMutation = useMutation({
    mutationFn: async () => {
      if (!accessToken || !selectedSaleId) {
        throw new Error("Selecciona una venta antes de registrar la devolucion.");
      }

      return commitSaleReturn({
        accessToken,
        payload: {
          workstation_code: appEnv.VITE_POS_WORKSTATION_CODE,
          original_sale_id: selectedSaleId,
          reason_code: draftState.reasonCode,
          high_risk_acknowledged: draftState.highRiskAcknowledged,
          refund_method_code: draftState.refundMethodCode,
          notes: draftState.notes.trim().length > 0 ? draftState.notes.trim() : undefined,
          lines: buildReturnCommitLines(draftState.lines),
        },
        requestId: createRequestId("sale-return"),
      });
    },
    onSuccess: async (result) => {
      const requiresReview = isHighRiskAcknowledgementRequired;
      setLastCommittedReturn(result);
      setSelectedHistoryReturnId(result.id);
      setDraftState(createInitialReturnDraftState());
      setSelectedDraftLineId(null);
      setCommitError(null);
      setSelectedSaleId(null);
      setCenterSection("history");
      showSuccess(
        requiresReview
          ? `Devolucion registrada. Folio ${result.folio}. Se preparo revision de backoffice.`
          : `Devolucion registrada. Folio ${result.folio}.`,
      );
      await Promise.all([
        queryClient.invalidateQueries({
          queryKey: returnsBootstrapQueryKey(appEnv.VITE_POS_WORKSTATION_CODE),
        }),
        queryClient.invalidateQueries({
          queryKey: ["returns", "sales", appEnv.VITE_POS_WORKSTATION_CODE],
        }),
        queryClient.invalidateQueries({
          queryKey: ["returns", "history", appEnv.VITE_POS_WORKSTATION_CODE],
        }),
        selectedSaleId
          ? queryClient.invalidateQueries({
              queryKey: returnSaleDetailQueryKey(appEnv.VITE_POS_WORKSTATION_CODE, selectedSaleId),
            })
          : Promise.resolve(),
        queryClient.invalidateQueries({
          queryKey: saleReturnDetailQueryKey(appEnv.VITE_POS_WORKSTATION_CODE, result.id),
        }),
        queryClient.invalidateQueries({ queryKey: ["tickets-list"] }),
        queryClient.invalidateQueries({ queryKey: ["ticket-detail"] }),
      ]);
    },
    onError: (error) => {
      const message = toOperationalErrorMessage(
        error,
        "No fue posible registrar la devolucion.",
      );
      setCommitError(message);
      showError(message);
    },
  });

  const draftSummaryPanel = (
    <ReturnSummaryPanel
      blockedMessages={blockingMessages}
      commitError={commitError}
      commitPending={commitMutation.isPending}
      draftState={draftState}
      exactProductOptions={selectedDraftLineExactProductOptions}
      exactProductsError={selectedDraftLineExactProductsError}
      exactProductsLoading={selectedDraftLineExactProductsLoading}
      highRiskMessages={highRiskMessages}
      isHighRiskAcknowledgementRequired={isHighRiskAcknowledgementRequired}
      onCommit={() => {
        void commitMutation.mutateAsync();
      }}
      onDispositionChangeAll={(value) => {
        updateDraftState((current) => ({
          ...current,
          lines: current.lines.map((line) => ({
            ...line,
            dispositionCode: value,
          })),
        }));
      }}
      onExactProductChangeSelectedLine={(productId) => {
        if (!selectedDraftLine) {
          return;
        }

        const selectedProduct =
          selectedDraftLineExactProductOptions.find((product) => product.id === productId) ?? null;
        updateDraftState((current) => ({
          ...current,
          lines: setReturnDraftLineExactProduct(
            current.lines,
            selectedDraftLine.originalSaleLineId,
            productId,
            selectedProduct?.name ?? null,
          ),
        }));
      }}
      onHighRiskAcknowledgedChange={(value) => {
        updateDraftState((current) => ({
          ...current,
          highRiskAcknowledged: value,
        }));
      }}
      onNotesChange={(value) => {
        updateDraftState((current) => ({
          ...current,
          notes: value,
        }));
      }}
      onReasonChange={(value) => {
        updateDraftState((current) => ({
          ...current,
          reasonCode: value,
        }));
      }}
      onRefundMethodChange={(value) => {
        updateDraftState((current) => ({
          ...current,
          refundMethodCode: value,
        }));
      }}
      onViewHistory={() => {
        setCenterSection("history");
        if (lastCommittedReturn) {
          setSelectedHistoryReturnId(lastCommittedReturn.id);
        }
      }}
      reasonOptions={reasonOptions}
      refundMethodOptions={refundMethodOptions}
      saleDetail={selectedSale}
      selectedDraftLine={selectedDraftLine}
      selectedLineValidationMessage={selectedLineValidationMessage}
      uiState={getReturnUiState({
        blockedMessages: blockingMessages,
        commitError,
        commitPending: commitMutation.isPending,
        draftLines: draftState.lines,
        hasSelectedSale: selectedSale !== null,
        lastCommittedReturn,
      })}
    />
  );
  const selectedHistoryRecord =
    returnsHistoryQuery.data?.records.find((record) => record.id === selectedHistoryReturnId) ?? null;

  const handleNewReturn = () => {
    setSelectedSaleId(null);
    setSearchText("");
    setDateFrom("");
    setDateTo("");
    setDraftState(createInitialReturnDraftState());
    setLastCommittedReturn(null);
    setSelectedHistoryReturnId(null);
    setSelectedDraftLineId(null);
    setCenterSection("sales");
    void navigate({ search: {} as never, to: "/devoluciones" });
  };

  const summaryPanel =
    centerSection === "history" ? (
      <ReturnHistoryDetailPanel
        onNewReturn={handleNewReturn}
        onPrintReceipt={() => {
          if (!selectedHistoryReturn) {
            return;
          }

          const printWindow = openBrowserPrintWindow();
          if (!printWindow) {
            showError("No se pudo abrir la ventana de impresion.");
            return;
          }

          writeReturnReceiptToPrintWindow(printWindow, selectedHistoryReturn);
        }}
        onViewTicket={() => {
          if (!selectedHistoryReturn) {
            return;
          }

          void navigate({
            search: { ticketId: selectedHistoryReturn.original_sale_id } as never,
            to: "/tickets",
          });
        }}
        returnDetail={selectedHistoryReturn}
        selectedHistoryRecord={selectedHistoryRecord}
      />
    ) : (
      draftSummaryPanel
    );  useAppShellRightPanel(summaryPanel);

  const isBootstrapPending =
    returnsBootstrapQuery.isPending || currentCashSessionQuery.isPending;

  if (isBootstrapPending) {
    return (
      <OperationalStatus
        description="Consultando la caja activa y las ventas confirmadas para devolver."
        title="Cargando devoluciones"
      />
    );
  }

  if (returnsBootstrapQuery.error) {
    return (
      <OperationalStatus
        action={<PosButton onClick={() => returnsBootstrapQuery.refetch()}>Reintentar</PosButton>}
        description={toOperationalErrorMessage(
          returnsBootstrapQuery.error,
          "Confirma la configuracion de la estacion y el contexto operativo.",
        )}
        title="No fue posible cargar Devoluciones"
      />
    );
  }

  if (currentCashSessionQuery.error) {
    return (
      <OperationalStatus
        action={<PosButton onClick={() => currentCashSessionQuery.refetch()}>Reintentar</PosButton>}
        description={toOperationalErrorMessage(
          currentCashSessionQuery.error,
          "Confirma la conexion con la API y el estado actual de la caja.",
        )}
        title="No fue posible consultar la caja"
      />
    );
  }

  if (!currentCashSessionQuery.data) {
    return <Navigate to="/cash-session/open" />;
  }

  if (currentCashSessionQuery.data.user_id !== returnsBootstrapQuery.data.user.id) {
    return (
      <OperationalStatus
        description="La caja abierta de esta estacion pertenece a otro cajero. Inicia sesion con el operador correcto o espera el relevo."
        title="La caja activa no coincide con este cajero"
      />
    );
  }

  const salesColumns: PosRecordColumn<ReturnSaleSearchItemView>[] = [
    {
      header: "Ticket",
      key: "folio",
      renderCell: (sale) => <span className="font-semibold text-slate-950">{sale.folio}</span>,
      width: "17%",
    },
    {
      header: "Fecha/hora",
      key: "date",
      renderCell: (sale) =>
        formatCompactLocalDateTime(sale.confirmed_at, returnsBootstrapQuery.data.branch.timezone),
      width: "18%",
    },
    {
      header: "Cajero",
      key: "operator",
      renderCell: (sale) => (
        <span className="block truncate" title={sale.operator_full_name}>
          {sale.operator_full_name}
        </span>
      ),
      width: "22%",
    },
    {
      align: "right",
      header: "Total",
      key: "total",
      renderCell: (sale) => formatCurrency(sale.total_amount),
      width: "12%",
    },
    {
      align: "right",
      header: "Disponible",
      key: "available",
      renderCell: (sale) => (
        <span className="font-medium text-slate-950">
          {sale.has_returnable_quantity ? "Si" : "No"}
        </span>
      ),
      width: "13%",
    },
    {
      align: "right",
      header: "Estado",
      key: "status",
      renderCell: (sale) =>
        getSaleReturnStatusLabel(sale.return_status) ? (
          <PosStatusBadge status={getSaleReturnStatusTone(sale.return_status)}>
            {getSaleReturnStatusLabel(sale.return_status)}
          </PosStatusBadge>
        ) : sale.has_returnable_quantity ? (
          <PosStatusBadge status="ready">Devolvible</PosStatusBadge>
        ) : (
          <PosStatusBadge status="blocked">Sin saldo</PosStatusBadge>
        ),
      width: "18%",
    },
  ];

  const salesListPane = (
    <PosHistoryView
      action={
        <PosButton onClick={() => setCenterSection("history")} type="button" variant="neutral">
          Ver historial
        </PosButton>
      }
      className="h-full"
      description="Busca una venta confirmada y selecciona sus productos devolvibles."
      title="Ventas para devolucion"
      toolbar={
        <PosFilterBar
          actions={
            <div className="flex flex-wrap items-end gap-2">
              <label className="grid gap-1 text-xs text-slate-500">
                <span>Desde</span>
                <input
                  className={`${posInputClass} h-10 min-w-[8.5rem] px-3 py-2 text-sm`}
                  onChange={(event) => setDateFrom(event.target.value)}
                  type="date"
                  value={dateFrom}
                />
              </label>
              <label className="grid gap-1 text-xs text-slate-500">
                <span>Hasta</span>
                <input
                  className={`${posInputClass} h-10 min-w-[8.5rem] px-3 py-2 text-sm`}
                  onChange={(event) => setDateTo(event.target.value)}
                  type="date"
                  value={dateTo}
                />
              </label>
            </div>
          }
          chipFilters={scopeOptions.map((scope) => ({
            isActive: selectedScope === scope.code,
            key: scope.code,
            label: scope.label,
            onSelect: () => setSelectedScope(scope.code),
          }))}
          countLabel={
            <ModuleStateChip tone="muted">
              {sales.length} {sales.length === 1 ? "venta" : "ventas"}
            </ModuleStateChip>
          }
          searchInput={{
            ariaLabel: "Buscar venta por folio",
            inputRef: searchInputRef,
            onChange: setSearchText,
            placeholder: "Buscar por folio",
            value: searchText,
          }}
        />
      }
    >
      {returnSalesQuery.error ? (
        <OperationalStatus
          action={<PosButton onClick={() => returnSalesQuery.refetch()}>Reintentar</PosButton>}
          description={toOperationalErrorMessage(
            returnSalesQuery.error,
            "No fue posible consultar las ventas disponibles para devolucion.",
          )}
          title="La busqueda no esta disponible"
        />
      ) : (
        <PosRecordTable
          columns={salesColumns}
          emptyDescription="No hay ventas confirmadas para los filtros actuales."
          emptyTitle="Sin ventas disponibles"
          getKey={(sale) => sale.id}
          loading={returnSalesQuery.isPending}
          loadingTitle="Buscando ventas"
          onSelect={(sale) => {
            setSelectedSaleId(sale.id);
            setCenterSection("lines");
          }}
          records={sales}
          selectedKey={selectedSaleId}
          tableAriaLabel="Ventas disponibles para devolucion"
        />
      )}
    </PosHistoryView>
  );
  const returnDetailPane = (
    <PosHistoryView
      action={
        <div className="flex flex-wrap items-center gap-2">
          <PosButton onClick={() => setCenterSection("sales")} type="button" variant="neutral">
            Volver a ventas
          </PosButton>
          <PosButton onClick={() => setCenterSection("history")} type="button" variant="neutral">
            Ver historial
          </PosButton>
        </div>
      }
      className="h-full"
      description="Ajusta las cantidades directamente en la tabla."
      title="Productos devolvibles"
    >
      {!selectedSaleId ? (
        <div className="rounded-xl border border-dashed border-[var(--pos-shell-border)] bg-[var(--pos-shell-muted)] px-4 py-5 text-sm text-slate-600">
          Selecciona una venta para ver sus productos devolvibles.
        </div>
      ) : returnSaleDetailQuery.isPending ? (
        <OperationalStatus
          description="Cargando la venta original para preparar la devolucion."
          title="Cargando venta"
        />
      ) : returnSaleDetailQuery.error ? (
        <OperationalStatus
          action={<PosButton onClick={() => returnSaleDetailQuery.refetch()}>Reintentar</PosButton>}
          description={toOperationalErrorMessage(
            returnSaleDetailQuery.error,
            "No fue posible cargar la venta seleccionada.",
          )}
          title="Venta no disponible"
        />
      ) : selectedSale ? (
        <div className="grid h-full min-h-0 grid-rows-[auto_auto_minmax(0,1fr)] gap-3">
          <SelectedSaleReferenceBar saleDetail={selectedSale} />

          {!selectedSale.has_returnable_lines ? (
            <InlineNotice tone="warning">Esta venta ya no tiene saldo devolvible.</InlineNotice>
          ) : null}

          <ReturnableLinesTable
            draftLines={draftState.lines}
            lines={returnableLines}
            onDecreaseQuantity={handleDecrementReturnableLineQuantity}
            onDraftQuantityChange={handleReturnableLineQuantityChange}
            onIncreaseQuantity={handleIncrementReturnableLineQuantity}
            onRemove={handleRemoveSelectedDraftLine}
            onSelect={handleSelectReturnableLine}
            selectedLineId={selectedDraftLineId}
          />
        </div>
      ) : (
        <div className="rounded-xl border border-dashed border-[var(--pos-shell-border)] bg-[var(--pos-shell-muted)] px-4 py-5 text-sm text-slate-600">
          Selecciona una venta para ver sus productos devolvibles.
        </div>
      )}
    </PosHistoryView>
  );
  const historyColumns: PosRecordColumn<ReturnHistoryListItemView>[] = [
    {
      header: "Folio devolucion",
      key: "folio",
      renderCell: (record) => (
        <span className="block truncate font-semibold text-slate-950" title={record.folio}>
          {record.folio}
        </span>
      ),
      width: "18%",
    },
    {
      header: "Ticket original",
      key: "ticket",
      renderCell: (record) => (
        <span className="block truncate" title={record.original_sale_folio}>
          {record.original_sale_folio}
        </span>
      ),
      width: "17%",
    },
    {
      header: "Fecha/hora",
      key: "date",
      renderCell: (record) => formatCompactLocalDateTime(record.created_at_utc, branchTimeZone),
      width: "18%",
    },
    {
      header: "Cajero",
      key: "cashier",
      renderCell: (record) => (
        <span className="block truncate" title={record.created_by_user_full_name}>
          {record.created_by_user_full_name}
        </span>
      ),
      width: "22%",
    },
    {
      align: "right",
      header: "Monto devuelto",
      key: "amount",
      renderCell: (record) => formatCurrency(record.total_refund_amount),
      width: "13%",
    },
    {
      align: "right",
      header: "Estado",
      key: "status",
      renderCell: (record) => (
        <PosStatusBadge status={getReturnStatusTone(record.status)}>
          {getReturnStatusLabel(record.status)}
        </PosStatusBadge>
      ),
      width: "12%",
    },
  ];

  const historyPane = (
    <PosHistoryView
      action={
        <PosButton onClick={handleNewReturn} type="button" variant="neutral">
          Nueva devolucion
        </PosButton>
      }
      className="h-full"
      title="Historial de devoluciones"
      toolbar={
        <PosFilterBar
          actions={
            <div className="flex flex-wrap items-end gap-2">
              <label className="grid gap-1 text-xs text-slate-500">
                <span>Desde</span>
                <input
                  className={`${posInputClass} h-10 min-w-[8.5rem] px-3 py-2 text-sm`}
                  onChange={(event) => setHistoryDateFrom(event.target.value)}
                  type="date"
                  value={historyDateFrom}
                />
              </label>
              <label className="grid gap-1 text-xs text-slate-500">
                <span>Hasta</span>
                <input
                  className={`${posInputClass} h-10 min-w-[8.5rem] px-3 py-2 text-sm`}
                  onChange={(event) => setHistoryDateTo(event.target.value)}
                  type="date"
                  value={historyDateTo}
                />
              </label>
            </div>
          }
          chipFilters={historyScopeOptions.map((scope) => ({
            isActive: historyScope === scope.code,
            key: scope.code,
            label: scope.label,
            onSelect: () => setHistoryScope(scope.code),
          }))}
          countLabel={
            <ModuleStateChip tone="muted">
              {historyRecords.length} {historyRecords.length === 1 ? "devolucion" : "devoluciones"}
            </ModuleStateChip>
          }
          searchInput={{
            ariaLabel: "Buscar devolucion",
            inputRef: historySearchInputRef,
            onChange: setHistorySearchText,
            placeholder: "Buscar por folio o ticket",
            value: historySearchText,
          }}
          selectFilters={[
            {
              ariaLabel: "Filtrar historial por usuario",
              key: "history-user",
              onChange: setSelectedHistoryCreatedByUserId,
              options: [
                { label: "Todos los cajeros", value: "" },
                ...historyUserOptions.map((option) => ({
                  label: option.label,
                  value: option.value,
                })),
              ],
              value: selectedHistoryCreatedByUserId,
            },
            {
              ariaLabel: "Filtrar historial por motivo",
              key: "history-reason",
              onChange: setSelectedHistoryReasonCode,
              options: [
                { label: "Todos los motivos", value: "" },
                ...historyReasonOptions.map((option) => ({
                  label: option.label,
                  value: option.value,
                })),
              ],
              value: selectedHistoryReasonCode,
            },
          ]}
        />
      }
    >
      {returnsHistoryQuery.error ? (
        <OperationalStatus
          action={<PosButton onClick={() => returnsHistoryQuery.refetch()}>Reintentar</PosButton>}
          description={toOperationalErrorMessage(
            returnsHistoryQuery.error,
            "No fue posible consultar el historial de devoluciones.",
          )}
          title="Historial no disponible"
        />
      ) : (
        <PosRecordTable
          columns={historyColumns}
          emptyDescription="No hay devoluciones registradas para este filtro."
          emptyTitle="Sin historial"
          getKey={(record) => record.id}
          loading={returnsHistoryQuery.isPending}
          loadingTitle="Consultando devoluciones"
          onSelect={(record) => setSelectedHistoryReturnId(record.id)}
          records={historyRecords}
          selectedKey={selectedHistoryReturnId}
          tableAriaLabel="Historial de devoluciones"
        />
      )}
    </PosHistoryView>
  );
  const returnProgressStep =
    selectedSale === null
      ? 1
      : draftState.lines.length === 0
        ? 2
        : blockingMessages.length > 0
          ? 3
          : 4;
  const returnProgressSteps: ProgressStepperStep[] = [
    {
      id: "sale",
      label: "Venta",
      state: selectedSale === null ? "current" : "completed",
    },
    {
      id: "lines",
      label: "Lineas",
      state:
        selectedSale === null
          ? "blocked"
          : draftState.lines.length === 0
            ? "current"
            : "completed",
    },
    {
      id: "refund",
      label: "Reembolso",
      state:
        selectedSale === null || draftState.lines.length === 0
          ? "blocked"
          : blockingMessages.length > 0
            ? "current"
            : "completed",
    },
    {
      id: "confirm",
      label: "Confirmacion",
      state:
        selectedSale !== null && draftState.lines.length > 0 && blockingMessages.length === 0
          ? "current"
          : "upcoming",
    },
  ];
  return (
    <>
      <CentralWorkspaceSheet
        className="lg:h-full"
        contentClassName="min-h-0 overflow-hidden p-3"
        header={
          <CompactPageHeader
            secondaryChips={
              selectedSale ? (
                <ModuleStateChip tone="primary">Venta {selectedSale.folio}</ModuleStateChip>
              ) : null
            }
            stateChip={
              <ModuleStateChip tone={getReturnUiStateTone(uiState)}>
                {getReturnUiStateLabel(uiState)}
              </ModuleStateChip>
            }
            title={centerSection === "history" ? "Historial de devoluciones" : "Devoluciones"}
          >
            {centerSection === "history" ? null : (
              <ProgressStepper
                currentStep={returnProgressStep}
                steps={returnProgressSteps}
                variant="workflow"
              />
            )}
          </CompactPageHeader>
        }
      >
        {centerSection === "history" ? (
          historyPane
        ) : centerSection === "lines" ? (
          returnDetailPane
        ) : (
          salesListPane
        )}
      </CentralWorkspaceSheet>
    </>
  );
}
