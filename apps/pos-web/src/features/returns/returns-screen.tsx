import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Navigate, useNavigate, useRouterState } from "@tanstack/react-router";
import { useEffect, useMemo, useRef, useState } from "react";

import { useAppShellRightPanel } from "../../components/app-shell-right-panel";
import {
  OperationConfirmationDialog,
  OperationDocumentSummaryPanel,
  OperationDocumentResult,
  OperationHistoryList,
  type OperationHistoryRecord,
  type OperationDocumentAction,
  type OperationDocumentMetric,
  type OperationLineSummaryItem,
} from "../../components/operation-documents";
import { OperationalStatus } from "../../components/operational-status";
import {
  PosEmptyState,
  PosInlineValidationMessage,
} from "../../components/pos-feedback";
import { PosButton, PosFieldLabel, PosStatusBadge } from "../../components/pos-foundations";
import { PosSummaryPanel } from "../../components/pos-module-layout";
import {
  CentralWorkspaceSheet,
  CompactPageHeader,
  FlowGuide,
  InlineNotice,
  ListDetailColumn,
  ModuleStateChip,
  ResponsivePaneLayout,
} from "../../components/pos-module-primitives";
import {
  PosFilterBar,
  PosHistoryView,
  PosRecordDetailPanel,
  PosRecordList,
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
import { getCustomerCommunicationActionState } from "../../lib/customer-communication";
import { getDocumentActionAvailability } from "../../lib/document-actions";
import {
  formatCompactLocalDateTime,
  formatCurrency,
  formatLocalDateTime,
} from "../../lib/formatters";
import { toOperationalErrorMessage } from "../../lib/http";
import { usePosAuthStore } from "../auth/auth-store";
import { useCurrentCashSessionQuery } from "../cash-session-open/queries";
import {
  formatQuantityFromMilliUnits,
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
  getReturnLineCount,
  getReturnTotalUnitsMilli,
  removeReturnDraftLine,
  RETURN_DISPOSITION_RESTOCK_BACKROOM,
  RETURN_DISPOSITION_RESTOCK_COUNTER,
  RETURN_DISPOSITION_SEND_TO_WASTE,
  setReturnDraftLineDisposition,
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

const RETURN_PROCESS_STEPS = [
  { key: "sale", label: "Venta" },
  { key: "lines", label: "Lineas" },
  { key: "refund", label: "Reembolso" },
  { key: "confirm", label: "Confirmacion" },
] as const;

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

function getDispositionLabel(code: string): string {
  return RETURN_DISPOSITION_OPTIONS.find((option) => option.value === code)?.label ?? "Pendiente";
}

function getDispositionHint(code: string): string {
  return (
    RETURN_DISPOSITION_OPTIONS.find((option) => option.value === code)?.hint ??
    "Selecciona el destino fisico de la linea."
  );
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

function buildCommittedReturnLineSummaryItems(
  lines: SaleReturnDetailResponse["lines"],
): OperationLineSummaryItem[] {
  return lines.map((line) => ({
    amountText: formatCurrency(line.refund_line_total_amount),
    key: line.id,
    quantityText: formatQuantity(line.returned_quantity),
    secondaryText: line.returned_product_name_snapshot,
    title: line.original_catalog_name_snapshot,
    trailingNote: getDispositionLabel(line.disposition_code),
  }));
}

function buildReturnDocumentMetrics(
  returnDetail: SaleReturnDetailResponse,
): OperationDocumentMetric[] {
  return [
    {
      key: "refund-total",
      label: "Total reembolsado",
      tone: "financial",
      value: formatCurrency(returnDetail.total_refund_amount),
    },
    {
      key: "refund-method",
      label: "Metodo",
      value: getRefundMethodLabel(returnDetail.refund_method_code),
    },
    {
      key: "line-count",
      label: "Lineas",
      value: String(returnDetail.lines.length),
    },
  ];
}

function buildReturnsHistoryRecords(
  records: ReturnHistoryListItemView[],
  timeZone: string,
): OperationHistoryRecord[] {
  return records.map((record) => ({
    documentTypeLabel: "Devolucion",
    folio: record.folio,
    id: record.id,
    locationLabel: `${record.branch_name} / ${record.workstation_name}`,
    metrics: [
      {
        key: `${record.id}:refund`,
        label: "Reembolso",
        tone: "financial",
        value: formatCurrency(record.total_refund_amount),
      },
      {
        key: `${record.id}:lines`,
        label: "Lineas",
        value: String(record.line_count),
      },
    ],
    primaryTimestampLabel: "Registrada",
    primaryTimestampValue: formatCompactLocalDateTime(record.created_at_utc, timeZone),
    statusLabel: getReturnStatusLabel(record.status),
    statusTone: getReturnStatusTone(record.status),
    subtitle: `Venta ${record.original_sale_folio} · ${getRefundMethodLabel(record.refund_method_code)}`,
    title: record.reason_name,
    userLabel: record.created_by_user_full_name,
  }));
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

function getDispositionSummary(lines: ReturnDraftLine[]): string | null {
  if (lines.length === 0) {
    return null;
  }

  const counts = new Map<string, number>();
  for (const line of lines) {
    const label = getDispositionLabel(line.dispositionCode);
    counts.set(label, (counts.get(label) ?? 0) + 1);
  }

  return [...counts.entries()]
    .map(
      ([label, count]) =>
        `${count} ${count === 1 ? "linea" : "lineas"} a ${label.toLowerCase()}`,
    )
    .join(" | ");
}

function getReasonLabel(
  code: string,
  reasonOptions: ReadonlyArray<{ code: string; label: string }>,
): string {
  return reasonOptions.find((reason) => reason.code === code)?.label ?? code;
}

function isSaleOlderThanThreshold(confirmedAt: string, thresholdDays: number): boolean {
  const saleDate = new Date(confirmedAt);
  if (Number.isNaN(saleDate.getTime())) {
    return false;
  }

  const diffMs = Date.now() - saleDate.getTime();
  const diffDays = diffMs / (1000 * 60 * 60 * 24);
  return diffDays >= thresholdDays;
}

function buildReturnDraftLineSummary(lines: ReturnDraftLine[]): OperationLineSummaryItem[] {
  return lines.map((line) => ({
    amountText: formatRefundCurrency(getReturnDraftLineRefundCents(line)),
    key: line.originalSaleLineId,
    quantityText: formatQuantityFromMilliUnits(line.quantityMilliUnits),
    secondaryText: line.exactProductName ?? line.fixedProductName ?? line.productClassName,
    title: line.lineName,
    trailingNote: getDispositionLabel(line.dispositionCode),
  }));
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

function getActiveProcessStepKey(
  centerSection: ReturnsCenterSection,
  draftLines: ReturnDraftLine[],
  lastCommittedReturn: SaleReturnDetailResponse | null,
  uiState: ReturnsUiState,
): string {
  if (centerSection === "history") {
    return "confirm";
  }

  if (
    uiState === "CONFIRMING" ||
    uiState === "READY_TO_CONFIRM" ||
    lastCommittedReturn
  ) {
    return "confirm";
  }

  if (draftLines.length > 0) {
    return "refund";
  }

  return centerSection === "lines" ? "lines" : "sale";
}

function ReturnSaleCard({
  isSelected,
  sale,
  timeZone,
}: {
  isSelected: boolean;
  sale: ReturnSaleSearchItemView;
  timeZone: string;
}) {
  return (
    <div className="grid gap-2">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <p className="truncate text-sm font-semibold text-slate-950">{sale.folio}</p>
            {getSaleReturnStatusLabel(sale.return_status) ? (
              <PosStatusBadge status={getSaleReturnStatusTone(sale.return_status)}>
                {getSaleReturnStatusLabel(sale.return_status)}
              </PosStatusBadge>
            ) : null}
          </div>
          <p className="mt-1 text-xs text-slate-500">
            {formatCompactLocalDateTime(sale.confirmed_at, timeZone)}
          </p>
          <p className="mt-1 truncate text-xs font-medium text-slate-700">
            {sale.operator_full_name}
          </p>
        </div>

        <div className="text-right">
          <p className="text-sm font-semibold text-slate-950">
            {formatCurrency(sale.total_amount)}
          </p>
          <p className="mt-1 text-xs text-slate-500">
            {sale.has_returnable_quantity ? "Con saldo devolvible" : "Sin saldo devolvible"}
          </p>
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-2 text-[11px] text-slate-500">
        <span>{sale.item_count} lineas</span>
        <span aria-hidden="true">|</span>
        <span>{formatQuantity(sale.total_quantity)} unidades</span>
        {sale.return_count > 0 ? (
          <>
            <span aria-hidden="true">|</span>
            <span>Devuelto {formatCurrency(sale.returned_amount)}</span>
          </>
        ) : null}
        {isSelected ? (
          <>
            <span aria-hidden="true">|</span>
            <span className="font-semibold text-slate-700">Seleccionada</span>
          </>
        ) : null}
      </div>
    </div>
  );
}

function SelectedSaleReferenceBar({
  saleDetail,
}: {
  saleDetail: ReturnOriginalSaleDetailResponse;
}) {
  return (
    <div className="rounded-xl border border-[var(--pos-shell-border)] bg-white px-4 py-3">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <p className="text-sm font-semibold text-slate-950">{saleDetail.folio}</p>
            {getSaleReturnStatusLabel(saleDetail.return_status) ? (
              <PosStatusBadge status={getSaleReturnStatusTone(saleDetail.return_status)}>
                {getSaleReturnStatusLabel(saleDetail.return_status)}
              </PosStatusBadge>
            ) : null}
          </div>
          <p className="mt-1 text-sm text-slate-600">
            {formatLocalDateTime(saleDetail.confirmed_at, saleDetail.branch.timezone)}
          </p>
          <p className="mt-1 text-xs text-slate-500">
            {saleDetail.branch.name} | {saleDetail.workstation.name} | {saleDetail.operator.full_name}
          </p>
        </div>

        <div className="flex flex-wrap items-center justify-end gap-x-4 gap-y-1 text-sm text-slate-600">
          <span>
            Lineas con saldo{" "}
            <span className="font-semibold text-slate-950">
              {getReturnableLineCount(saleDetail)}
            </span>
          </span>
          <span>
            Disponible{" "}
            <span className="font-semibold text-slate-950">
              {getReturnableUnitsText(saleDetail)}
            </span>
          </span>
          <span>
            Devuelto{" "}
            <span className="font-semibold text-slate-950">
              {formatCurrency(saleDetail.returned_amount)}
            </span>
          </span>
          <span className="text-base font-semibold text-slate-950">
            {formatCurrency(saleDetail.total_amount)}
          </span>
        </div>
      </div>
    </div>
  );
}

function ReturnableLinesTable({
  lines,
  onSelect,
  selectedLineId,
}: {
  lines: ReturnableSaleLineView[];
  onSelect: (line: ReturnableSaleLineView) => void;
  selectedLineId: string | null;
}) {
  const columns = useMemo<PosRecordColumn<ReturnableSaleLineView>[]>(
    () => [
      {
        header: "#",
        key: "sequence",
        renderCell: (line) => <span className="text-slate-600">{line.sequence}</span>,
        width: "4rem",
      },
      {
        header: "Articulo",
        key: "article",
        renderCell: (line) => (
          <div className="min-w-0">
            <p className="truncate font-semibold text-slate-950">
              {line.catalog_name_snapshot}
            </p>
            <p className="mt-0.5 truncate text-xs text-slate-500">
              {line.product_name ?? line.product_class_name}
              {line.requires_exact_product_selection ? " | Requiere producto exacto" : ""}
            </p>
          </div>
        ),
      },
      {
        align: "right",
        header: "Vendido",
        key: "sold",
        renderCell: (line) => (
          <span className="font-medium text-slate-900">{formatQuantity(line.quantity)}</span>
        ),
        width: "6rem",
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
        width: "7rem",
      },
      {
        align: "right",
        header: "Devuelto",
        key: "returned",
        renderCell: (line) => (
          <span className="text-slate-600">
            {formatQuantity(line.already_returned_quantity)}
          </span>
        ),
        width: "6rem",
      },
      {
        align: "right",
        header: "Reembolso",
        key: "refund",
        renderCell: (line) => (
          <span className="font-semibold text-slate-950">
            {getReturnableRefundAmount(line)}
          </span>
        ),
        width: "8rem",
      },
    ],
    [],
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
  lastCommittedReturn,
  lastCommittedReturnRequiresReview,
  onCommit,
  onDispositionChangeSelectedLine,
  onExactProductChangeSelectedLine,
  onHighRiskAcknowledgedChange,
  onNewReturn,
  onNotesChange,
  onPrintReceipt,
  onQuantityChangeSelectedLine,
  onReasonChange,
  onRefundMethodChange,
  onRemoveSelectedLine,
  onViewHistory,
  onViewTicket,
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
  lastCommittedReturn: SaleReturnDetailResponse | null;
  lastCommittedReturnRequiresReview: boolean;
  onCommit: () => void;
  onDispositionChangeSelectedLine: (value: string) => void;
  onExactProductChangeSelectedLine: (value: string) => void;
  onHighRiskAcknowledgedChange: (value: boolean) => void;
  onNewReturn: () => void;
  onNotesChange: (value: string) => void;
  onPrintReceipt: () => void;
  onQuantityChangeSelectedLine: (value: string) => void;
  onReasonChange: (value: string) => void;
  onRefundMethodChange: (value: string) => void;
  onRemoveSelectedLine: () => void;
  onViewHistory: () => void;
  onViewTicket: () => void;
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
  const quantityInputRef = useRef<HTMLInputElement | null>(null);
  const refundTotalText = formatRefundCurrency(
    getReturnDraftTotalRefundCents(draftState.lines),
  );
  const selectedDraftLineKey = selectedDraftLine?.originalSaleLineId ?? null;
  const selectedRefundMethod = refundMethodOptions.find(
    (method) => method.code === draftState.refundMethodCode,
  );

  useEffect(() => {
    if (!selectedDraftLineKey) {
      return;
    }

    quantityInputRef.current?.focus();
    quantityInputRef.current?.select();
  }, [selectedDraftLineKey]);

  if (lastCommittedReturn) {
    const returnDocumentAvailability = getDocumentActionAvailability("returnReceipt");
    const sendReceiptByEmailAction = getCustomerCommunicationActionState({
      channel: "email",
      intent: "returnReceipt",
    });
    const sendReceiptBySmsAction = getCustomerCommunicationActionState({
      channel: "sms",
      intent: "returnReceipt",
    });
    const resultActions: OperationDocumentAction[] = [
      {
        kind: "print",
        key: "print-return-receipt",
        label: returnDocumentAvailability.print.label,
        onSelect: onPrintReceipt,
        availabilityNote: returnDocumentAvailability.print.unavailableReason,
      },
      {
        key: "view-history",
        label: "Ver historial",
        onSelect: onViewHistory,
        variant: "neutral",
      },
      {
        key: "view-original-ticket",
        label: "Ver ticket",
        onSelect: onViewTicket,
        variant: "neutral",
      },
      {
        availabilityNote: sendReceiptByEmailAction.disabledReason,
        disabled: sendReceiptByEmailAction.disabled,
        key: "send-return-receipt-email",
        label: sendReceiptByEmailAction.label,
        onSelect: () => undefined,
        placement: "menu",
        variant: "ghost",
      },
      {
        availabilityNote: sendReceiptBySmsAction.disabledReason,
        disabled: sendReceiptBySmsAction.disabled,
        key: "send-return-receipt-sms",
        label: sendReceiptBySmsAction.label,
        onSelect: () => undefined,
        placement: "menu",
        variant: "ghost",
      },
      {
        key: "new-return",
        label: "Nueva devolucion",
        onSelect: onNewReturn,
        variant: "neutral",
      },
    ];
    const resultMetrics = buildReturnDocumentMetrics(lastCommittedReturn);

    return (
      <OperationDocumentResult
        actions={resultActions}
        auditSummary={lastCommittedReturn.audit_summary}
        context={{
          branchName: lastCommittedReturn.branch.name,
          userName: lastCommittedReturn.created_by.full_name,
          workstationName: lastCommittedReturn.workstation.name,
        }}
        description={
          lastCommittedReturnRequiresReview
            ? "La devolucion se registro y se preparo una revision de backoffice."
            : "La devolucion quedo registrada y el ticket original ya refleja el nuevo estado."
        }
        kind="return"
        metrics={resultMetrics}
        referenceValue={lastCommittedReturn.folio}
        timeZone={lastCommittedReturn.branch.timezone}
        timestamps={{
          committedAtValue: formatCompactLocalDateTime(
            lastCommittedReturn.created_at_utc,
            lastCommittedReturn.branch.timezone,
          ),
        }}
      />
    );
  }

  return (
    <PosSummaryPanel
      description={
        saleDetail
          ? "Captura la devolucion con el menor numero de pasos posible."
          : "Selecciona una venta para comenzar."
      }
      footer={
        <PosButton
          disabled={blockedMessages.length > 0 || commitPending}
          leadingIcon={<MoneyIcon className="h-4 w-4" />}
          onClick={onCommit}
        >
          {commitPending ? "Registrando devolucion..." : "Confirmar devolucion"}
        </PosButton>
      }
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
      <div className="grid h-full min-h-0 gap-3 overflow-y-auto">
        {commitError ? (
          <PosInlineValidationMessage tone="error">{commitError}</PosInlineValidationMessage>
        ) : null}

        {!saleDetail ? (
          <PosEmptyState
            description="Selecciona una venta original para preparar la devolucion."
            title="Sin venta seleccionada"
          />
        ) : (
          <>
            <div className="grid gap-2 rounded-xl border border-[var(--pos-shell-border)] bg-[var(--pos-shell-muted)] px-3 py-3">
              <p className="pos-label-text">Venta original</p>
              <p className="truncate text-sm font-semibold text-slate-950">{saleDetail.folio}</p>
              <div className="grid gap-1 text-sm text-slate-600">
                <div className="flex items-center justify-between gap-3">
                  <span>Fecha</span>
                  <span className="text-right font-medium text-slate-950">
                    {formatLocalDateTime(saleDetail.confirmed_at, saleDetail.branch.timezone)}
                  </span>
                </div>
                <div className="flex items-center justify-between gap-3">
                  <span>Saldo devolvible</span>
                  <span className="text-right font-semibold text-slate-950">
                    {getReturnableUnitsText(saleDetail)}
                  </span>
                </div>
                <div className="flex items-center justify-between gap-3">
                  <span>Reembolso estimado</span>
                  <span className="text-right font-semibold text-slate-950">{refundTotalText}</span>
                </div>
              </div>
            </div>

            {selectedDraftLine ? (
              <div className="grid gap-3 rounded-xl border border-[var(--pos-shell-border)] bg-white px-3 py-3">
                <div className="grid gap-1">
                  <p className="pos-label-text">Linea seleccionada</p>
                  <p className="truncate text-sm font-semibold text-slate-950">
                    {selectedDraftLine.lineName}
                  </p>
                  <p className="truncate text-xs text-slate-500">
                    {selectedDraftLine.exactProductName ??
                      selectedDraftLine.fixedProductName ??
                      selectedDraftLine.productClassName}
                  </p>
                </div>

                <PosFieldLabel helper="Captura con teclado numerico." required>
                  Cantidad a devolver
                </PosFieldLabel>
                <input
                  className={posInputClass}
                  inputMode="decimal"
                  onChange={(event) =>
                    onQuantityChangeSelectedLine(sanitizeQuantityInput(event.target.value))
                  }
                  ref={quantityInputRef}
                  value={selectedDraftLine.quantityText}
                />

                <PosFieldLabel helper={getDispositionHint(selectedDraftLine.dispositionCode)} required>
                  Destino fisico
                </PosFieldLabel>
                <select
                  className={posInputClass}
                  onChange={(event) => onDispositionChangeSelectedLine(event.target.value)}
                  value={selectedDraftLine.dispositionCode}
                >
                  <option value="">Selecciona destino</option>
                  {RETURN_DISPOSITION_OPTIONS.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>

                {selectedDraftLine.exactProductRequired ? (
                  <>
                    <PosFieldLabel helper="Confirma el producto exacto para esta linea." required>
                      Producto exacto
                    </PosFieldLabel>
                    <select
                      className={posInputClass}
                      disabled={exactProductsLoading}
                      onChange={(event) => onExactProductChangeSelectedLine(event.target.value)}
                      value={selectedDraftLine.exactProductId}
                    >
                      <option value="">
                        {exactProductsLoading ? "Cargando productos..." : "Selecciona un producto"}
                      </option>
                      {exactProductOptions.map((product) => (
                        <option key={product.id} value={product.id}>
                          {product.name}
                        </option>
                      ))}
                    </select>
                  </>
                ) : null}

                <div className="flex items-center justify-end">
                  <PosButton
                    leadingIcon={<TrashIcon className="h-4 w-4" />}
                    onClick={onRemoveSelectedLine}
                    variant="neutral"
                  >
                    Quitar linea
                  </PosButton>
                </div>
              </div>
            ) : (
              <PosEmptyState
                description="Selecciona una linea de la tabla central para capturar la devolucion."
                title="Sin linea seleccionada"
              />
            )}

            <div className="grid gap-2 rounded-xl border border-[var(--pos-shell-border)] bg-white px-3 py-3">
              <PosFieldLabel required>Motivo</PosFieldLabel>
              <select
                className={posInputClass}
                onChange={(event) => onReasonChange(event.target.value)}
                value={draftState.reasonCode}
              >
                <option value="">Selecciona motivo</option>
                {reasonOptions.map((reason) => (
                  <option key={reason.code} value={reason.code}>
                    {reason.label}
                  </option>
                ))}
              </select>
            </div>

            <div className="grid gap-2 rounded-xl border border-[var(--pos-shell-border)] bg-white px-3 py-3">
              <p className="pos-label-text">Metodo de reembolso</p>
              <div className="grid gap-2">
                {refundMethodOptions.map((method) => {
                  const isSelected = draftState.refundMethodCode === method.code;
                  return (
                    <button
                      aria-pressed={isSelected}
                      className={[
                        "rounded-lg border px-3 py-2 text-left transition",
                        method.is_enabled
                          ? isSelected
                            ? "border-[var(--pos-primary)] bg-[var(--pos-primary-soft)]"
                            : "border-[var(--pos-shell-border)] bg-white hover:border-[var(--pos-primary)]"
                          : "cursor-not-allowed border-[var(--pos-shell-border)] bg-[var(--pos-shell-muted)] text-slate-400",
                      ].join(" ")}
                      disabled={!method.is_enabled}
                      key={method.code}
                      onClick={() => onRefundMethodChange(method.code)}
                      type="button"
                    >
                      <div className="flex items-center justify-between gap-3">
                        <span className="font-medium">{method.label}</span>
                        {isSelected ? <PosStatusBadge status="ready">Seleccionado</PosStatusBadge> : null}
                      </div>
                      {method.availability_note ? (
                        <p className="mt-1 text-xs text-slate-500">{method.availability_note}</p>
                      ) : null}
                    </button>
                  );
                })}
              </div>
              {selectedRefundMethod?.availability_note ? (
                <PosInlineValidationMessage tone="warning">
                  {selectedRefundMethod.availability_note}
                </PosInlineValidationMessage>
              ) : null}
            </div>

            <div className="grid gap-2 rounded-xl border border-[var(--pos-shell-border)] bg-white px-3 py-3">
              <PosFieldLabel helper="Describe el contexto de la devolucion.">
                Notas
              </PosFieldLabel>
              <textarea
                className={`${posInputClass} min-h-[5.5rem] resize-y px-3 py-2`}
                onChange={(event) => onNotesChange(event.target.value)}
                placeholder="Agrega una nota operativa si aplica."
                value={draftState.notes}
              />
            </div>

            {isHighRiskAcknowledgementRequired ? (
              <div className="grid gap-2 rounded-xl border border-[rgba(187,122,22,0.18)] bg-[var(--ui-color-warning-soft)] px-3 py-3">
                <p className="pos-label-text">Validacion adicional</p>
                <div className="grid gap-1.5">
                  {highRiskMessages.map((message) => (
                    <PosInlineValidationMessage key={message} tone="warning">
                      {message}
                    </PosInlineValidationMessage>
                  ))}
                </div>
                <label className="flex items-start gap-2 text-sm text-slate-700">
                  <input
                    checked={draftState.highRiskAcknowledged}
                    onChange={(event) => onHighRiskAcknowledgedChange(event.target.checked)}
                    type="checkbox"
                  />
                  <span>Confirmo que la devolucion fue validada y puede pasar a revision de backoffice.</span>
                </label>
              </div>
            ) : null}

            <div className="grid gap-2 rounded-xl border border-[var(--pos-shell-border)] bg-[var(--pos-shell-muted)] px-3 py-3">
              <div className="flex items-center justify-between gap-3 text-sm">
                <span className="font-medium text-slate-600">Lineas</span>
                <span className="font-semibold text-slate-950">{getReturnLineCount(draftState.lines)}</span>
              </div>
              <div className="flex items-center justify-between gap-3 text-sm">
                <span className="font-medium text-slate-600">Unidades</span>
                <span className="font-semibold text-slate-950">
                  {formatQuantityFromMilliUnits(getReturnTotalUnitsMilli(draftState.lines))}
                </span>
              </div>
              <div className="flex items-center justify-between gap-3 text-sm">
                <span className="font-medium text-slate-600">Total</span>
                <span className="font-semibold text-slate-950">{refundTotalText}</span>
              </div>
            </div>

            {selectedLineValidationMessage ? (
              <PosInlineValidationMessage tone="warning">
                {selectedLineValidationMessage}
              </PosInlineValidationMessage>
            ) : null}
            {exactProductsError ? (
              <PosInlineValidationMessage tone="error">{exactProductsError}</PosInlineValidationMessage>
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
  const [lastCommittedReturnRequiresReview, setLastCommittedReturnRequiresReview] =
    useState(false);
  const [commitError, setCommitError] = useState<string | null>(null);
  const [isConfirmDialogOpen, setConfirmDialogOpen] = useState(false);
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
    setLastCommittedReturnRequiresReview(false);
    setConfirmDialogOpen(false);
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
    setLastCommittedReturnRequiresReview(false);
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
  const historyRecords = buildReturnsHistoryRecords(
    returnsHistoryQuery.data?.records ?? [],
    branchTimeZone,
  );
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
    isSaleOlderThanThreshold(selectedSale.confirmed_at, oldSaleDaysThreshold);
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
  const processStepKey = getActiveProcessStepKey(
    centerSection,
    draftState.lines,
    lastCommittedReturn,
    uiState,
  );
  const selectedLineValidationMessage = selectedDraftLine
    ? getDraftLineErrorMessage(selectedDraftLine)
    : null;

  const handleSelectReturnableLine = (line: ReturnableSaleLineView) => {
    try {
      updateDraftState((current) => ({
        ...current,
        lines: addReturnDraftLine(current.lines, line),
      }));
      setSelectedDraftLineId(line.id);
      setCenterSection("lines");
    } catch (error) {
      setCommitError(
        toOperationalErrorMessage(error, "No fue posible preparar la linea para devolucion."),
      );
    }
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
      setLastCommittedReturnRequiresReview(requiresReview);
      setSelectedHistoryReturnId(result.id);
      setDraftState(createInitialReturnDraftState());
      setSelectedDraftLineId(null);
      setCommitError(null);
      setConfirmDialogOpen(false);
      setCenterSection("lines");
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
      setConfirmDialogOpen(false);
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
      lastCommittedReturn={lastCommittedReturn}
      lastCommittedReturnRequiresReview={lastCommittedReturnRequiresReview}
      onCommit={() => setConfirmDialogOpen(true)}
      onDispositionChangeSelectedLine={(value) => {
        if (!selectedDraftLine) {
          return;
        }

        updateDraftState((current) => ({
          ...current,
          lines: setReturnDraftLineDisposition(
            current.lines,
            selectedDraftLine.originalSaleLineId,
            value,
          ),
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
      onNewReturn={() => {
        setSelectedSaleId(null);
        setSearchText("");
        setDateFrom("");
        setDateTo("");
        setDraftState(createInitialReturnDraftState());
        setLastCommittedReturn(null);
        setLastCommittedReturnRequiresReview(false);
        setSelectedHistoryReturnId(null);
        setSelectedDraftLineId(null);
        setCenterSection("sales");
        void navigate({ search: {} as never, to: "/devoluciones" });
      }}
      onNotesChange={(value) => {
        updateDraftState((current) => ({
          ...current,
          notes: value,
        }));
      }}
      onPrintReceipt={() => {
        if (!lastCommittedReturn) {
          return;
        }

        const printWindow = openBrowserPrintWindow();
        if (!printWindow) {
          showError("No se pudo abrir la ventana de impresion.");
          return;
        }

        writeReturnReceiptToPrintWindow(printWindow, lastCommittedReturn);
      }}
      onQuantityChangeSelectedLine={(value) => {
        if (!selectedDraftLine) {
          return;
        }

        updateDraftState((current) => ({
          ...current,
          lines: setReturnDraftLineQuantityText(
            current.lines,
            selectedDraftLine.originalSaleLineId,
            value,
          ),
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
      onRemoveSelectedLine={() => {
        if (!selectedDraftLine) {
          return;
        }

        handleRemoveSelectedDraftLine(selectedDraftLine.originalSaleLineId);
      }}
      onViewHistory={() => {
        setCenterSection("history");
        if (lastCommittedReturn) {
          setSelectedHistoryReturnId(lastCommittedReturn.id);
        }
      }}
      onViewTicket={() => {
        const ticketId = lastCommittedReturn?.original_sale_id ?? selectedSaleId;
        if (!ticketId) {
          return;
        }

        void navigate({
          search: { ticketId } as never,
          to: "/tickets",
        });
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
  const historySendReceiptByEmailAction = getCustomerCommunicationActionState({
    channel: "email",
    intent: "returnReceipt",
  });
  const historySendReceiptBySmsAction = getCustomerCommunicationActionState({
    channel: "sms",
    intent: "returnReceipt",
  });

  const summaryPanel =
    centerSection === "history" ? (
      selectedHistoryReturn ? (
        <OperationDocumentSummaryPanel
          actions={[
            {
              kind: "print",
              key: "print-history-return",
              label: getDocumentActionAvailability("returnReceipt").print.label,
              onSelect: () => {
                const printWindow = openBrowserPrintWindow();
                if (!printWindow) {
                  showError("No se pudo abrir la ventana de impresion.");
                  return;
                }

                writeReturnReceiptToPrintWindow(printWindow, selectedHistoryReturn);
              },
              availabilityNote: getDocumentActionAvailability("returnReceipt").print.unavailableReason,
            },
            {
              key: "view-history-ticket",
              label: "Ver ticket",
              onSelect: () => {
                void navigate({
                  search: { ticketId: selectedHistoryReturn.original_sale_id } as never,
                  to: "/tickets",
                });
              },
              variant: "neutral",
            },
            {
              availabilityNote: historySendReceiptByEmailAction.disabledReason,
              disabled: historySendReceiptByEmailAction.disabled,
              key: "history-send-return-email",
              label: historySendReceiptByEmailAction.label,
              onSelect: () => undefined,
              placement: "menu",
              variant: "ghost",
            },
            {
              availabilityNote: historySendReceiptBySmsAction.disabledReason,
              disabled: historySendReceiptBySmsAction.disabled,
              key: "history-send-return-sms",
              label: historySendReceiptBySmsAction.label,
              onSelect: () => undefined,
              placement: "menu",
              variant: "ghost",
            },
          ]}
          auditSummary={selectedHistoryReturn.audit_summary}
          blockers={[]}
          context={{
            branchName: selectedHistoryReturn.branch.name,
            userName: selectedHistoryReturn.created_by.full_name,
            workstationName: selectedHistoryReturn.workstation.name,
          }}
          description={`Venta original ${selectedHistoryReturn.original_sale_folio}`}
          kind="return"
          lines={buildCommittedReturnLineSummaryItems(selectedHistoryReturn.lines)}
          metrics={buildReturnDocumentMetrics(selectedHistoryReturn)}
          referenceValue={selectedHistoryReturn.folio}
          stateLabel={getReturnStatusLabel(selectedHistoryRecord?.status ?? "COMMITTED")}
          stateTone={getReturnStatusTone(selectedHistoryRecord?.status ?? "COMMITTED")}
          timeZone={selectedHistoryReturn.branch.timezone}
          timestamps={{
            committedAtValue: formatCompactLocalDateTime(
              selectedHistoryReturn.created_at_utc,
              selectedHistoryReturn.branch.timezone,
            ),
            createdAtValue: formatCompactLocalDateTime(
              selectedHistoryReturn.created_at_utc,
              selectedHistoryReturn.branch.timezone,
            ),
          }}
          title="Detalle de la devolucion"
        />
      ) : (
        <PosEmptyState
          description="Selecciona una devolucion registrada para revisar su auditoria y sus lineas."
          title="Sin devolucion seleccionada"
        />
      )
    ) : (
      draftSummaryPanel
    );
  useAppShellRightPanel(summaryPanel);

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

  const salesListPane = (
    <ListDetailColumn
      contentClassName="min-h-0"
      description="Busca por folio o acota por rango de fechas."
      title="Ventas confirmadas"
      toolbar={
        <PosFilterBar
          actions={
            <div className="flex flex-wrap items-center gap-2">
              <label className="grid gap-1 text-xs text-slate-500">
                <span>Desde</span>
                <input
                  className={`${posInputClass} h-10 min-w-[9rem] px-3 py-2 text-sm`}
                  onChange={(event) => setDateFrom(event.target.value)}
                  type="date"
                  value={dateFrom}
                />
              </label>
              <label className="grid gap-1 text-xs text-slate-500">
                <span>Hasta</span>
                <input
                  className={`${posInputClass} h-10 min-w-[9rem] px-3 py-2 text-sm`}
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
          title="Ventas disponibles"
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
        <PosRecordList
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
          renderContent={(sale, state) => (
            <ReturnSaleCard
              isSelected={state.isSelected}
              sale={sale}
              timeZone={returnsBootstrapQuery.data.branch.timezone}
            />
          )}
          selectedKey={selectedSaleId}
        />
      )}
    </ListDetailColumn>
  );

  const returnDetailPane = (
    <ListDetailColumn
      contentClassName="min-h-0 overflow-hidden"
      description="Selecciona una linea y construye la devolucion desde el panel derecho."
      title="Lineas devolvibles"
    >
      {!selectedSaleId ? (
        <PosEmptyState
          description="Selecciona una venta original para revisar sus lineas devolvibles."
          title="Sin venta seleccionada"
        />
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
            lines={returnableLines}
            onSelect={handleSelectReturnableLine}
            selectedLineId={selectedDraftLineId}
          />
        </div>
      ) : (
        <PosEmptyState
          description="Selecciona una venta original."
          title="Sin venta seleccionada"
        />
      )}
    </ListDetailColumn>
  );

  const historyPane = (
    <PosHistoryView
      action={
        <PosButton
          onClick={() => setCenterSection(selectedSaleId ? "lines" : "sales")}
          variant="neutral"
        >
          {selectedSaleId ? "Volver a la venta" : "Volver a consulta"}
        </PosButton>
      }
      description="Consulta devoluciones registradas sin exponer metadatos internos."
      title="Historial de devoluciones"
      toolbar={
        <PosFilterBar
          actions={
            <div className="flex flex-wrap items-center gap-2">
              <label className="grid gap-1 text-xs text-slate-500">
                <span>Desde</span>
                <input
                  className={`${posInputClass} h-10 min-w-[9rem] px-3 py-2 text-sm`}
                  onChange={(event) => setHistoryDateFrom(event.target.value)}
                  type="date"
                  value={historyDateFrom}
                />
              </label>
              <label className="grid gap-1 text-xs text-slate-500">
                <span>Hasta</span>
                <input
                  className={`${posInputClass} h-10 min-w-[9rem] px-3 py-2 text-sm`}
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
            placeholder: "Buscar por folio, venta o motivo",
            value: historySearchText,
          }}
          selectFilters={[
            {
              ariaLabel: "Filtrar historial por usuario",
              key: "history-user",
              onChange: setSelectedHistoryCreatedByUserId,
              options: [
                { label: "Todos los usuarios", value: "" },
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
          title="Consulta"
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
        <div className="grid h-full min-h-0 gap-3 xl:grid-cols-[minmax(18rem,22rem)_minmax(0,1fr)]">
          <OperationHistoryList
            emptyDescription="No hay devoluciones registradas para este filtro."
            loading={returnsHistoryQuery.isPending}
            loadingTitle="Consultando devoluciones"
            onSelect={(record) => setSelectedHistoryReturnId(record.id)}
            records={historyRecords}
            selectedRecordId={selectedHistoryReturnId}
          />
          <PosRecordDetailPanel
            badge={
              selectedHistoryRecord ? (
                <ModuleStateChip tone="success">
                  {getReturnStatusLabel(selectedHistoryRecord.status)}
                </ModuleStateChip>
              ) : undefined
            }
            description={
              selectedHistoryRecord
                ? `Venta original ${selectedHistoryRecord.original_sale_folio}`
                : "Selecciona una devolucion para revisar su trazabilidad."
            }
            title={
              selectedHistoryReturn
                ? selectedHistoryReturn.folio
                : "Sin devolucion seleccionada"
            }
          >
            {selectedHistoryReturnQuery.isPending ? (
              <OperationalStatus
                description="Cargando la devolucion seleccionada."
                title="Cargando detalle"
              />
            ) : selectedHistoryReturnQuery.error ? (
              <OperationalStatus
                action={
                  <PosButton onClick={() => selectedHistoryReturnQuery.refetch()}>
                    Reintentar
                  </PosButton>
                }
                description={toOperationalErrorMessage(
                  selectedHistoryReturnQuery.error,
                  "No fue posible cargar la devolucion seleccionada.",
                )}
                title="Detalle no disponible"
              />
            ) : selectedHistoryReturn ? (
              <OperationDocumentSummaryPanel
                actions={[
                  {
                    kind: "print",
                    key: "history-print-return",
                    label: getDocumentActionAvailability("returnReceipt").print.label,
                    onSelect: () => {
                      const printWindow = openBrowserPrintWindow();
                      if (!printWindow) {
                        showError("No se pudo abrir la ventana de impresion.");
                        return;
                      }

                      writeReturnReceiptToPrintWindow(printWindow, selectedHistoryReturn);
                    },
                    availabilityNote:
                      getDocumentActionAvailability("returnReceipt").print.unavailableReason,
                  },
                  {
                    key: "history-view-ticket",
                    label: "Ver ticket",
                    onSelect: () => {
                      void navigate({
                        search: { ticketId: selectedHistoryReturn.original_sale_id } as never,
                        to: "/tickets",
                      });
                    },
                    variant: "neutral",
                  },
                  {
                    availabilityNote: historySendReceiptByEmailAction.disabledReason,
                    disabled: historySendReceiptByEmailAction.disabled,
                    key: "history-detail-send-return-email",
                    label: historySendReceiptByEmailAction.label,
                    onSelect: () => undefined,
                    placement: "menu",
                    variant: "ghost",
                  },
                  {
                    availabilityNote: historySendReceiptBySmsAction.disabledReason,
                    disabled: historySendReceiptBySmsAction.disabled,
                    key: "history-detail-send-return-sms",
                    label: historySendReceiptBySmsAction.label,
                    onSelect: () => undefined,
                    placement: "menu",
                    variant: "ghost",
                  },
                ]}
                auditSummary={selectedHistoryReturn.audit_summary}
                blockers={[]}
                context={{
                  branchName: selectedHistoryReturn.branch.name,
                  userName: selectedHistoryReturn.created_by.full_name,
                  workstationName: selectedHistoryReturn.workstation.name,
                }}
                description={selectedHistoryReturn.reason_name}
                kind="return"
                lines={buildCommittedReturnLineSummaryItems(selectedHistoryReturn.lines)}
                metrics={buildReturnDocumentMetrics(selectedHistoryReturn)}
                notices={
                  <InlineNotice tone="info">
                    Venta original {selectedHistoryReturn.original_sale_folio}
                  </InlineNotice>
                }
                referenceValue={selectedHistoryReturn.folio}
                stateLabel={getReturnStatusLabel(selectedHistoryRecord?.status ?? "COMMITTED")}
                stateTone={getReturnStatusTone(selectedHistoryRecord?.status ?? "COMMITTED")}
                timeZone={selectedHistoryReturn.branch.timezone}
                timestamps={{
                  committedAtValue: formatCompactLocalDateTime(
                    selectedHistoryReturn.created_at_utc,
                    selectedHistoryReturn.branch.timezone,
                  ),
                  createdAtValue: formatCompactLocalDateTime(
                    selectedHistoryReturn.created_at_utc,
                    selectedHistoryReturn.branch.timezone,
                  ),
                }}
                title="Detalle de la devolucion"
              />
            ) : (
              <PosEmptyState
                description="Selecciona una devolucion registrada para revisar su resumen auditado."
                title="Sin devolucion seleccionada"
              />
            )}
          </PosRecordDetailPanel>
        </div>
      )}
      </PosHistoryView>
  );

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
            title="Devoluciones"
          >
            <FlowGuide
              activeStepKey={processStepKey}
              steps={[...RETURN_PROCESS_STEPS]}
              variant="process"
            />
          </CompactPageHeader>
        }
      >
        {centerSection === "history" ? (
          historyPane
        ) : (
          <ResponsivePaneLayout
            className="h-full gap-2.5"
            detail={returnDetailPane}
            detailClassName="min-h-0"
            list={salesListPane}
            listClassName="min-h-0"
          />
        )}
      </CentralWorkspaceSheet>

      <OperationConfirmationDialog
        actionsTitle="Lineas a devolver"
        confirmLabel={commitMutation.isPending ? "Confirmando..." : "Confirmar devolucion"}
        context={
          selectedSale
            ? {
                branchName: returnsBootstrapQuery.data.branch.name,
                userName: returnsBootstrapQuery.data.user.full_name,
                workstationName: returnsBootstrapQuery.data.workstation.name,
              }
            : undefined
        }
        description={
          selectedSale
            ? `Motivo: ${getReasonLabel(draftState.reasonCode, reasonOptions)} | Metodo: ${getRefundMethodLabel(draftState.refundMethodCode)}.`
            : undefined
        }
        isOpen={isConfirmDialogOpen}
        isPending={commitMutation.isPending}
        kind="return"
        lines={buildReturnDraftLineSummary(draftState.lines)}
        metrics={[
          {
            key: "refund-total",
            label: "Total reembolsado",
            tone: "financial",
            value: formatRefundCurrency(refundTotalCents),
          },
          {
            key: "refund-method",
            label: "Metodo",
            value: getRefundMethodLabel(draftState.refundMethodCode),
          },
          {
            key: "line-count",
            label: "Lineas",
            value: String(getReturnLineCount(draftState.lines)),
          },
          {
            key: "unit-count",
            label: "Unidades",
            value: formatQuantityFromMilliUnits(getReturnTotalUnitsMilli(draftState.lines)),
          },
          ...(getDispositionSummary(draftState.lines)
            ? [
                {
                  key: "disposition-summary",
                  label: "Destino fisico",
                  value: getDispositionSummary(draftState.lines) ?? "",
                },
              ]
            : []),
          ...highRiskMessages.map((message, index) => ({
            key: `high-risk-${index}`,
            label: "Revision",
            tone: "warning" as const,
            value: message,
          })),
        ]}
        onCancel={() => setConfirmDialogOpen(false)}
        onConfirm={() => {
          void commitMutation.mutateAsync();
        }}
        referenceLabel="Venta original"
        referenceValue={selectedSale?.folio ?? null}
        title="Confirmar devolucion"
      />
    </>
  );
}
