import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Navigate } from "@tanstack/react-router";
import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type FocusEvent,
} from "react";

import { useAppShellRightPanel } from "../../components/app-shell-right-panel";
import {
  OperationConfirmationDialog,
  OperationDocumentResult,
  OperationDocumentSummaryPanel,
  OperationHistoryList,
  OperationLineSummary,
  type OperationDocumentMetric,
  type OperationHistoryRecord,
  type OperationLineSummaryItem,
} from "../../components/operation-documents";
import { OperationalStatus } from "../../components/operational-status";
import { PosBlockerPanel } from "../../components/pos-feedback";
import { PosSummaryPanel } from "../../components/pos-module-layout";
import {
  PosFilterBar,
  PosHistoryView,
  PosRecordList,
} from "../../components/pos-records";
import { PosScannerInput } from "../../components/pos-scanner-input";
import {
  CentralWorkspaceSheet,
  FlowGuide,
  InlineNotice,
  ListDetailColumn,
  ModuleStateChip,
  CompactPageHeader,
  ResponsivePaneLayout,
  ScrollPane,
} from "../../components/pos-module-primitives";
import {
  ArrowLeftIcon,
  ChevronRightIcon,
  ClipboardIcon,
  PrinterIcon,
  RotateCcwIcon,
} from "../../components/pos-icons";
import { Button } from "../../components/ui/button";
import type {
  OperationDocumentView,
  OperationHistoryFilterOptionView,
  OperationHistoryScopeView,
  PendingInboundTransferView,
  TransferDetailResponse,
  TransferReceiptHistoryResponse,
} from "../../lib/api-contracts";
import { getDocumentActionAvailability } from "../../lib/document-actions";
import { formatCompactLocalDateTime, formatLocalDateTime } from "../../lib/formatters";
import { toOperationalErrorMessage } from "../../lib/http";
import { matchesScannerValue, normalizeScannerText, parseShipmentScannerValue } from "../../lib/scanner";
import { cn } from "../../lib/utils";
import { usePosAuthStore } from "../auth/auth-store";
import { useCurrentCashSessionQuery } from "../cash-session-open/queries";
import { useOperationsBootstrapQuery } from "../operations/queries";
import { formatQuantityFromMilliUnits } from "../pos-terminal/model";
import {
  posInputClass,
  posOutlineButtonClass,
  posPrimaryButtonClass,
} from "../pos-theme/theme";
import { useStatusMessageStore } from "../status-messages/store";
import {
  buildTransferReceiveLines,
  createTransferReceiptDraftState,
  getTransferReceiptCommitBlockedReason,
  getTransferReceiptDifferenceTotalMilli,
  getTransferReceiptExpectedTotalMilli,
  getTransferReceiptLineVarianceMilli,
  getTransferReceiptReceivedTotalMilli,
  getTransferReceiptUiState,
  getTransferReceiptVarianceLineCount,
  hasTransferReceiptLineVariance,
  hasTransferReceiptMissingQuantities,
  hasTransferReceiptMissingVarianceReason,
  type TransferReceiptLineDraft,
  type TransferReceiptUiState,
  updateTransferReceiptLineQuantity,
  updateTransferReceiptLineVarianceReason,
} from "./model";
import {
  pendingInboundTransfersQueryKey,
  transferDetailQueryKey,
  transferReceiptHistoryQueryKey,
  usePendingInboundTransfersQuery,
  useTransferDetailQuery,
  useTransferReceiptHistoryQuery,
} from "./queries";
import { receiveTransfer } from "./transfers-api";

const VARIANCE_REASON_SUGGESTIONS = ["Faltante", "Dañado", "Sobrante", "Error de surtido"] as const;
const EMPTY_VALUE_TEXT = String.fromCharCode(8212);
type TransferReceiptCenterView = "history" | "pending";

function useDebouncedValue(value: string, delayMs: number): string {
  const [debouncedValue, setDebouncedValue] = useState(value);

  useEffect(() => {
    const timeout = window.setTimeout(() => setDebouncedValue(value), delayMs);
    return () => window.clearTimeout(timeout);
  }, [delayMs, value]);

  return debouncedValue;
}

function getTransferStatusLabel(status: string): string {
  if (status === "RECEIVED") {
    return "Recibido";
  }

  if (status === "RECEIVED_WITH_VARIANCE") {
    return "Recibido con diferencia";
  }

  return "En transito";
}

function getTransferStatusTone(status: string): "info" | "success" | "warning" {
  if (status === "RECEIVED") {
    return "success";
  }

  if (status === "RECEIVED_WITH_VARIANCE") {
    return "warning";
  }

  return "info";
}

function getTransferStatusBadgeTone(
  status: string,
): "confirmed" | "pending" | "success" | "warning" {
  if (status === "RECEIVED") {
    return "success";
  }

  if (status === "RECEIVED_WITH_VARIANCE") {
    return "warning";
  }

  return "pending";
}

function getReceiptUiStateLabel(uiState: TransferReceiptUiState): string {
  switch (uiState) {
    case "CAPTURING_RECEIVED_QUANTITIES":
    case "SHIPMENT_SELECTED":
      return "Capturando";
    case "WITH_VARIANCES":
      return "Con diferencias";
    case "READY_TO_CONFIRM":
      return "Listo para confirmar";
    case "CONFIRMING":
      return "Confirmando...";
    case "RECEIPT_CONFIRMED":
      return "Confirmado";
    case "RECEIPT_ERROR":
      return "Error";
    default:
      return "Sin seleccion";
  }
}

function getReceiptUiStateTone(
  uiState: TransferReceiptUiState,
): "muted" | "primary" | "success" | "warning" {
  switch (uiState) {
    case "CAPTURING_RECEIVED_QUANTITIES":
    case "SHIPMENT_SELECTED":
    case "READY_TO_CONFIRM":
    case "CONFIRMING":
      return "primary";
    case "WITH_VARIANCES":
    case "RECEIPT_ERROR":
      return "warning";
    case "RECEIPT_CONFIRMED":
      return "success";
    default:
      return "muted";
  }
}

function getReceiptStateChipTone(
  centerView: TransferReceiptCenterView,
  uiState: TransferReceiptUiState,
): "info" | "muted" | "primary" | "success" | "warning" {
  if (centerView === "history") {
    return "info";
  }

  return getReceiptUiStateTone(uiState);
}

function toTransferReceiptErrorMessage(
  error: unknown,
  fallbackMessage: string,
): string {
  const message = toOperationalErrorMessage(error, fallbackMessage);

  if (message === "Transfer shipment was not found.") {
    return "El envio seleccionado ya no esta disponible.";
  }

  if (message === "Transfer shipment is no longer pending receipt.") {
    return "Este envio ya no esta pendiente de recepcion.";
  }

  if (message === "Transfer shipment is not destined to the current branch.") {
    return "Este envio no corresponde a la sucursal actual.";
  }

  if (
    message === "Transfer receipt lines must match the pending shipment lines exactly."
  ) {
    return "Las lineas ya no coinciden con el envio pendiente. Vuelve a abrir el detalle.";
  }

  if (
    message === "Transfer receipt expected quantities must match the pending shipment."
  ) {
    return "Las cantidades esperadas ya no coinciden con el envio pendiente.";
  }

  if (
    message ===
    "Variance reason is required when the received quantity differs from the shipment."
  ) {
    return "Cada linea con diferencia necesita un motivo antes de confirmar la recepcion.";
  }

  if (message === "Transfer receipt invariants were violated by a concurrent request.") {
    return "La recepcion cambio mientras la confirmabas. Vuelve a revisar el envio.";
  }

  return message;
}

function isTransferReceivable(detail: TransferDetailResponse | null): boolean {
  return (
    detail !== null &&
    detail.receipt === null &&
    detail.shipment.status === "IN_TRANSIT"
  );
}

function formatLineCountLabel(lineCount: number): string {
  return `${lineCount} lineas`;
}

function formatDifferenceLabel(varianceMilli: number): string {
  if (varianceMilli === 0) {
    return "0";
  }

  const absoluteValue = formatQuantityFromMilliUnits(Math.abs(varianceMilli));
  return varianceMilli > 0 ? `+${absoluteValue}` : `-${absoluteValue}`;
}

function formatDifferenceSummary(varianceMilli: number): string {
  const absoluteValue = formatQuantityFromMilliUnits(Math.abs(varianceMilli));

  if (varianceMilli === 0) {
    return "Coincide";
  }

  return varianceMilli > 0 ? `Sobran ${absoluteValue}` : `Faltan ${absoluteValue}`;
}

function buildReceiptDraftLineSummaryItems(
  lines: TransferReceiptLineDraft[],
): OperationLineSummaryItem[] {
  return lines.map((line) => {
    const varianceMilli = getTransferReceiptLineVarianceMilli(line);
    const hasVariance = hasTransferReceiptLineVariance(line);

    return {
      key: line.shipmentLineId,
      quantityText: line.receivedQuantityText,
      secondaryText: `${line.productClassName} / ${line.productCode}`,
      statusLabel: hasVariance ? "Con diferencia" : "Exacta",
      statusTone: hasVariance ? "warning" : "confirmed",
      title: line.productName,
      trailingNote: hasVariance
        ? line.varianceReason.trim() || formatDifferenceSummary(varianceMilli)
        : `Esperado ${line.expectedQuantityText}`,
    };
  });
}

function buildTransferDocumentLineSummaryItems(
  document: OperationDocumentView,
): OperationLineSummaryItem[] {
  return document.lines.map((line) => {
    const expectedText = formatQuantityFromMilliUnits(
      Number(line.expected_quantity ?? line.quantity) * 1000,
    );
    const receivedText =
      line.received_quantity !== null
        ? formatQuantityFromMilliUnits(Number(line.received_quantity) * 1000)
        : null;
    const hasVariance =
      line.received_quantity !== null &&
      Number(line.received_quantity) !== Number(line.expected_quantity ?? line.quantity);

    return {
      key: line.id,
      quantityText: receivedText ?? expectedText,
      secondaryText: `${line.product_class_name_snapshot} / ${line.product_code_snapshot}`,
      statusLabel: hasVariance ? "Con diferencia" : "Exacta",
      statusTone: hasVariance ? "warning" : "confirmed",
      title: line.product_name_snapshot,
      trailingNote: hasVariance
        ? line.variance_reason ?? `Esperado ${expectedText}`
        : `Esperado ${expectedText}`,
    };
  });
}

function buildReceiptMetrics({
  differenceLineCount,
  differenceTotalText,
  expectedUnitsText,
  lineCount,
  receivedUnitsText,
}: {
  differenceLineCount: number;
  differenceTotalText: string;
  expectedUnitsText: string;
  lineCount: number;
  receivedUnitsText: string;
}): OperationDocumentMetric[] {
  return [
    { key: "line-count", label: "Lineas", value: String(lineCount) },
    { key: "expected", label: "Esperado", value: expectedUnitsText },
    { key: "received", label: "Recibido", value: receivedUnitsText },
    {
      key: "difference",
      label: "Diferencia",
      tone: differenceLineCount > 0 ? "warning" : "success",
      value: differenceTotalText,
    },
  ];
}

function buildReceiptHistoryRecords(
  history: TransferReceiptHistoryResponse | undefined,
  timeZone: string,
  searchText: string,
): OperationHistoryRecord[] {
  const normalizedSearch = searchText.trim().toLowerCase();

  return (history?.records ?? [])
    .filter((record) => {
      if (normalizedSearch.length === 0) {
        return true;
      }

      const haystack = [
        record.folio,
        record.source_branch_code,
        record.source_branch_name,
        record.created_by_user_full_name,
      ]
        .filter(Boolean)
        .join(" ")
        .toLowerCase();

      return haystack.includes(normalizedSearch);
    })
    .map((record) => ({
      documentTypeLabel: "Recepcion de envio",
      folio: record.folio,
      id: record.id,
      locationLabel: `${record.source_branch_name} / ${record.workstation_name}`,
      metrics: [
        { key: "line-count", label: "Lineas", value: String(record.line_count) },
        {
          key: "units",
          label: "Recibido",
          value: formatQuantityFromMilliUnits(Number(record.total_quantity) * 1000),
        },
      ],
      primaryTimestampLabel: "Confirmado",
      primaryTimestampValue: record.committed_at_utc
        ? formatCompactLocalDateTime(record.committed_at_utc, timeZone)
        : undefined,
      secondaryTimestampLabel: "Creado",
      secondaryTimestampValue: formatCompactLocalDateTime(
        record.created_at_utc,
        timeZone,
      ),
      statusLabel: getTransferStatusLabel(record.status),
      statusTone: getTransferStatusBadgeTone(record.status),
      subtitle: record.source_branch_name,
      title: record.source_branch_name,
      userLabel: record.created_by_user_full_name,
    }));
}

function MovementBanner({
  destinationLabel,
  originLabel,
}: {
  destinationLabel?: string | null;
  originLabel: string;
}) {
  const destinationText =
    typeof destinationLabel === "string" && destinationLabel.trim().length > 0
      ? destinationLabel
      : EMPTY_VALUE_TEXT;

  return (
    <div
      aria-label="Movimiento del envio"
      className="inline-flex max-w-full items-center gap-2 rounded-[10px] border border-[var(--pos-shell-border)] bg-[var(--pos-shell-muted)] px-3 py-1.5"
      role="note"
    >
      <span
        className="max-w-[14rem] min-w-0 truncate whitespace-nowrap text-sm font-semibold text-slate-950"
        title={originLabel}
      >
        {originLabel}
      </span>
      <span aria-hidden="true" className="text-sm font-semibold text-slate-400">
        -&gt;
      </span>
      <span
        className="max-w-[14rem] min-w-0 truncate whitespace-nowrap text-sm font-semibold text-[var(--pos-primary)]"
        title={destinationText}
      >
        {destinationText}
      </span>
    </div>
  );
}

function SummaryCell({
  label,
  tone = "default",
  value,
}: {
  label: string;
  tone?: "default" | "warning";
  value: string;
}) {
  return (
    <div
      className={cn(
        "min-w-0 rounded-xl border px-3 py-2.5",
        tone === "warning"
          ? "border-[var(--ui-color-warning-soft)] bg-[var(--ui-color-warning-soft)]"
          : "border-[var(--pos-shell-border)] bg-white",
      )}
    >
      <p className="pos-label-text">{label}</p>
      <p
        className="mt-1 truncate whitespace-nowrap text-sm font-semibold text-slate-950"
        title={value}
      >
        {value}
      </p>
    </div>
  );
}

function PendingInboundRecord({
  shipment,
  timezone,
}: {
  shipment: PendingInboundTransferView;
  timezone: string;
}) {
  return (
    <div className="grid gap-2">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p
            className="truncate text-sm font-semibold text-slate-950"
            title={shipment.folio}
          >
            {shipment.folio}
          </p>
          <p
            className="mt-0.5 truncate text-sm text-slate-700"
            title={`${shipment.source_branch_name} (${shipment.source_branch_code})`}
          >
            {shipment.source_branch_name}
          </p>
        </div>
        <span
          className="pos-chip shrink-0"
          data-tone="pending"
        >
          Pendiente
        </span>
      </div>

      <div className="grid gap-1 text-xs text-slate-500">
        <p>
          <span className="font-medium text-slate-700">Origen:</span>{" "}
          {shipment.source_branch_code}
        </p>
        <p>
          <span className="font-medium text-slate-700">Enviado:</span>{" "}
          {formatCompactLocalDateTime(
            shipment.committed_at_utc ?? shipment.created_at_utc,
            timezone,
          )}
        </p>
        <div className="flex flex-wrap gap-2">
          <span className="rounded-full border border-[var(--pos-shell-border)] bg-[var(--pos-shell-muted)] px-2.5 py-1 font-medium text-slate-600">
            {shipment.line_count} lineas
          </span>
          <span className="rounded-full border border-[var(--pos-shell-border)] bg-[var(--pos-shell-muted)] px-2.5 py-1 font-medium text-slate-600">
            {formatQuantityFromMilliUnits(Number(shipment.expected_total_quantity) * 1000)} uds
          </span>
        </div>
      </div>
    </div>
  );
}

function LineComparisonHeader() {
  return (
    <div className="hidden grid-cols-[minmax(0,1.6fr)_5.5rem_7.5rem_7rem] gap-3 border-b border-[var(--pos-shell-border)] px-3 pb-2 text-[11px] font-semibold uppercase tracking-[0.08em] text-slate-500 md:grid">
      <span>Producto</span>
      <span className="text-right">Esperado</span>
      <span className="text-right">Recibido</span>
      <span className="text-right">Delta</span>
    </div>
  );
}

function ReceiptLineRow({
  focusToken,
  isPrimaryControl,
  line,
  onReceivedQuantityChange,
  onVarianceReasonChange,
}: {
  focusToken: string | null;
  isPrimaryControl: boolean;
  line: TransferReceiptLineDraft;
  onReceivedQuantityChange: (shipmentLineId: string, quantityText: string) => void;
  onVarianceReasonChange: (shipmentLineId: string, varianceReason: string) => void;
}) {
  const inputRef = useRef<HTMLInputElement>(null);
  const didSelectRef = useRef(false);
  const hasVariance = hasTransferReceiptLineVariance(line);
  const varianceMilli = getTransferReceiptLineVarianceMilli(line);
  const differenceText = formatDifferenceLabel(varianceMilli);
  const differenceSummary = formatDifferenceSummary(varianceMilli);

  useEffect(() => {
    didSelectRef.current = false;

    if (!isPrimaryControl) {
      return;
    }

    inputRef.current?.focus({ preventScroll: true });
    requestAnimationFrame(() => {
      if (!inputRef.current) {
        return;
      }

      inputRef.current.select();
      didSelectRef.current = true;
    });
  }, [focusToken, isPrimaryControl]);

  const handleInputFocus = useCallback((event: FocusEvent<HTMLInputElement>) => {
    if (didSelectRef.current) {
      return;
    }

    const input = event.currentTarget;
    requestAnimationFrame(() => {
      input.select();
      didSelectRef.current = true;
    });
  }, []);

  return (
    <div
      className={cn(
        "rounded-xl border px-3 py-3",
        hasVariance
          ? "border-[var(--ui-color-warning-soft)] bg-[var(--ui-color-warning-soft)]/45"
          : "border-[var(--pos-shell-border)] bg-white",
      )}
    >
      <div className="grid gap-3 md:grid-cols-[minmax(0,1.6fr)_5.5rem_7.5rem_7rem]">
        <div className="min-w-0">
          <p
            className="truncate text-sm font-semibold text-slate-950"
            title={line.productName}
          >
            {line.productName}
          </p>
          <p
            className="mt-1 truncate text-xs text-slate-500"
            title={`${line.productClassName} / ${line.productCode}`}
          >
            {line.productClassName} / {line.productCode}
          </p>
        </div>

        <div className="text-right">
          <p className="pos-label-text md:hidden">Esperado</p>
          <p className="mt-1 text-base font-semibold text-slate-950 [font-variant-numeric:tabular-nums] md:mt-0">
            {line.expectedQuantityText}
          </p>
        </div>

        <label className="grid gap-1">
          <span className="pos-label-text text-slate-800 md:hidden">Recibido</span>
          <input
            aria-label={`Cantidad recibida de ${line.productName}`}
            className={cn(
              "h-11 rounded-xl px-3 text-right text-lg font-semibold tracking-tight shadow-sm [font-variant-numeric:tabular-nums]",
              posInputClass,
            )}
            inputMode="decimal"
            onChange={(event) =>
              onReceivedQuantityChange(line.shipmentLineId, event.target.value)
            }
            onFocus={handleInputFocus}
            ref={inputRef}
            value={line.receivedQuantityText}
          />
        </label>

        <div className="text-right">
          <p className="pos-label-text md:hidden">Delta</p>
          <span
            className={cn(
              "inline-flex min-w-[5rem] justify-center rounded-full border px-2.5 py-1 text-sm font-semibold [font-variant-numeric:tabular-nums]",
              hasVariance
                ? "border-[var(--ui-color-warning-soft)] bg-[var(--ui-color-warning-soft)] text-[var(--ui-color-warning)]"
                : "border-[var(--ui-color-success-soft)] bg-[var(--ui-color-success-soft)] text-[var(--ui-color-success)]",
            )}
          >
            {differenceText}
          </span>
          <p
            className={cn(
              "mt-1 text-xs font-medium",
              hasVariance ? "text-[var(--ui-color-warning)]" : "text-[var(--ui-color-success)]",
            )}
          >
            {differenceSummary}
          </p>
        </div>
      </div>

      {hasVariance ? (
        <div className="mt-3 grid gap-2 border-t border-[var(--ui-color-warning-soft)] pt-3">
          <div className="flex flex-wrap gap-1.5">
            {VARIANCE_REASON_SUGGESTIONS.map((reason) => {
              const isActive = line.varianceReason.trim() === reason;

              return (
                <button
                  className={cn(
                    "rounded-full border px-2.5 py-1 text-xs font-medium transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--pos-ring)]",
                    isActive
                      ? "border-[var(--pos-primary)] bg-white text-[var(--pos-primary)]"
                      : "border-[var(--pos-shell-border)] bg-white text-slate-700 hover:border-[var(--pos-primary)]",
                  )}
                  key={reason}
                  onClick={() => onVarianceReasonChange(line.shipmentLineId, reason)}
                  type="button"
                >
                  {reason}
                </button>
              );
            })}
          </div>

          <input
            aria-label={`Motivo de diferencia de ${line.productName}`}
            className={cn("h-10 rounded-lg px-3 text-sm shadow-sm", posInputClass)}
            onChange={(event) =>
              onVarianceReasonChange(line.shipmentLineId, event.target.value)
            }
            placeholder="Motivo de la diferencia"
            value={line.varianceReason}
          />
        </div>
      ) : null}
    </div>
  );
}

function ReceiptConfirmDialog({
  detail,
  differenceTotalText,
  expectedUnitsText,
  isOpen,
  isPending,
  lineCount,
  lines,
  onCancel,
  onConfirm,
  receivedUnitsText,
  varianceLineCount,
}: {
  detail: TransferDetailResponse | null;
  differenceTotalText: string;
  expectedUnitsText: string;
  isOpen: boolean;
  isPending: boolean;
  lineCount: number;
  lines: OperationLineSummaryItem[];
  onCancel: () => void;
  onConfirm: () => void;
  receivedUnitsText: string;
  varianceLineCount: number;
}) {
  if (!isOpen || detail === null) {
    return null;
  }

  const hasVariances = varianceLineCount > 0;

  return (
    <OperationConfirmationDialog
      confirmationTone={hasVariances ? "warning" : undefined}
      context={{
        branchName: detail.shipment.destination_branch_name,
        userName: detail.shipment.created_by_user_full_name,
        workstationName: detail.shipment.workstation_name,
      }}
      description={
        hasVariances
          ? "Las lineas con diferencia se confirmaran con su motivo y el envio quedara cerrado con variaciones."
          : "La recepcion quedara confirmada y el envio se cerrara sin diferencias."
      }
      isOpen={isOpen}
      isPending={isPending}
      kind="branchReceipt"
      lines={lines}
      metrics={[
        ...buildReceiptMetrics({
          differenceLineCount: varianceLineCount,
          differenceTotalText,
          expectedUnitsText,
          lineCount,
          receivedUnitsText,
        }),
        {
          key: "impact",
          label: "Impacto",
          value: hasVariances ? "Se registraran diferencias" : "Recepcion exacta",
        },
      ]}
      onCancel={onCancel}
      onConfirm={onConfirm}
      referenceLabel="Envio"
      referenceValue={detail.shipment_summary.folio}
      title="Confirmar recepcion"
    />
  );
}

function ReceiptSummaryPanel({
  centerView,
  commitBlockedReason,
  commitErrorMessage,
  detail,
  detailTimezone,
  differenceTotalText,
  expectedUnitsText,
  isCommitPending,
  isNotesExpanded,
  lastReceivedTransfer,
  lineSummaryItems,
  notes,
  onClearSelection,
  onCommit,
  onHistoryToggle,
  onNotesChange,
  onToggleNotes,
  receivedUnitsText,
  uiState,
  varianceLineCount,
}: {
  centerView: TransferReceiptCenterView;
  commitBlockedReason: string | null;
  commitErrorMessage: string | null;
  detail: TransferDetailResponse | null;
  detailTimezone: string;
  differenceTotalText: string;
  expectedUnitsText: string;
  isCommitPending: boolean;
  isNotesExpanded: boolean;
  lastReceivedTransfer: TransferDetailResponse | null;
  lineSummaryItems: OperationLineSummaryItem[];
  notes: string;
  onClearSelection: () => void;
  onCommit: () => void;
  onHistoryToggle: () => void;
  onNotesChange: (value: string) => void;
  onToggleNotes: () => void;
  receivedUnitsText: string;
  uiState: TransferReceiptUiState;
  varianceLineCount: number;
}) {
  const activeDetail = detail ?? lastReceivedTransfer;
  const summaryLineCount =
    detail?.shipment.lines.length ??
    lastReceivedTransfer?.shipment.lines.length ??
    lineSummaryItems.length;
  const blockers =
    commitBlockedReason === null
      ? []
      : [
          {
            key: "receipt-blocker",
            message: commitBlockedReason,
            tone: "warning" as const,
          },
        ];

  return (
    <PosSummaryPanel
      description="Resumen operativo de la recepcion en curso."
      stateLabel={getReceiptUiStateLabel(uiState)}
      stateTone={
        uiState === "WITH_VARIANCES" || uiState === "RECEIPT_ERROR"
          ? "warning"
          : uiState === "RECEIPT_CONFIRMED"
            ? "success"
            : uiState === "NO_PENDING_SHIPMENTS"
              ? "draft"
              : "pending"
      }
      title="Recepcion en captura"
    >
      <div className="grid h-full min-h-0 grid-rows-[auto_auto_minmax(0,1fr)_auto] gap-3">
        <div className="grid gap-2">
          {commitErrorMessage ? <InlineNotice tone="error">{commitErrorMessage}</InlineNotice> : null}
          <div className="grid gap-2.5 rounded-xl border border-[var(--pos-shell-border)] bg-[var(--pos-shell-muted)]/80 px-3 py-3">
            <div className="flex flex-wrap items-center gap-2">
              <MovementBanner
                destinationLabel={activeDetail?.shipment.destination_branch_name ?? null}
                originLabel={activeDetail?.shipment.source_branch_name ?? "Origen pendiente"}
              />
              {activeDetail ? (
                <span
                  className="pos-chip"
                  data-tone={getTransferStatusTone(activeDetail.shipment.status)}
                >
                  {getTransferStatusLabel(activeDetail.shipment.status)}
                </span>
              ) : null}
            </div>

            {activeDetail ? (
              <div className="grid gap-2 md:grid-cols-2">
                <SummaryCell label="Folio" value={activeDetail.shipment_summary.folio} />
                <SummaryCell
                  label="Destino"
                  value={activeDetail.shipment.destination_branch_name ?? EMPTY_VALUE_TEXT}
                />
                <SummaryCell label="Origen" value={activeDetail.shipment.source_branch_name} />
                <SummaryCell
                  label="Fecha"
                  value={formatLocalDateTime(
                    activeDetail.shipment.committed_at_utc ??
                      activeDetail.shipment.created_at_utc,
                    detailTimezone,
                  )}
                />
              </div>
            ) : (
              <p className="text-sm leading-6 text-slate-600">
                {uiState === "NO_PENDING_SHIPMENTS"
                  ? "No hay envios pendientes para esta sucursal."
                  : "Selecciona un envio pendiente."}
              </p>
            )}
          </div>

          <div className="grid grid-cols-2 gap-2">
            <SummaryCell label="Esperado" value={expectedUnitsText} />
            <SummaryCell label="Recibido" value={receivedUnitsText} />
            <SummaryCell
              label="Diferencia"
              tone={varianceLineCount > 0 ? "warning" : "default"}
              value={differenceTotalText}
            />
            <SummaryCell
              label="Lineas"
              tone={varianceLineCount > 0 ? "warning" : "default"}
              value={formatLineCountLabel(summaryLineCount)}
            />
          </div>

          <PosBlockerPanel blockers={blockers} title="Bloqueos" />
        </div>

        <div className="rounded-xl border border-[var(--pos-shell-border)] bg-[var(--pos-shell-muted)]/80">
          <button
            aria-expanded={isNotesExpanded}
            className="flex w-full items-center justify-between gap-3 px-3 py-2.5 text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--pos-ring)]"
            disabled={detail === null || isCommitPending}
            onClick={onToggleNotes}
            type="button"
          >
            <span className="text-sm font-semibold text-slate-900">Notas (opcional)</span>
            <ChevronRightIcon
              className={cn(
                "h-4 w-4 text-slate-400 transition",
                isNotesExpanded && "rotate-90",
              )}
            />
          </button>
          {isNotesExpanded ? (
            <div className="border-t border-[var(--pos-shell-border)] px-3 pb-3 pt-2.5">
              <textarea
                aria-label="Notas de recepcion"
                className={cn(
                  "min-h-20 rounded-lg px-3 py-2 text-sm shadow-sm",
                  posInputClass,
                )}
                disabled={detail === null || isCommitPending}
                onChange={(event) => onNotesChange(event.target.value)}
                placeholder="Notas operativas"
                value={notes}
              />
            </div>
          ) : null}
        </div>

        <ScrollPane className="min-h-0 pr-1">
          <OperationLineSummary
            emptyMessage="Selecciona un envio pendiente para comenzar."
            lines={lineSummaryItems}
            title="Captura de recepcion"
          />
        </ScrollPane>

        <div className="grid gap-2 border-t border-[var(--pos-shell-border)] pt-2">
          <Button
            className={cn(
              "h-10",
              centerView === "history"
                ? "border-[var(--pos-primary)] bg-[var(--pos-primary-soft)] text-[var(--pos-primary)] shadow-sm hover:border-[var(--pos-primary)] hover:bg-[var(--pos-primary-soft)]"
                : posOutlineButtonClass,
            )}
            onClick={onHistoryToggle}
            type="button"
            variant="outline"
          >
            {centerView === "history" ? "Pendientes" : "Ver historial"}
          </Button>
          <Button
            className={cn("h-10", posOutlineButtonClass)}
            disabled={detail === null || isCommitPending}
            onClick={onClearSelection}
            type="button"
            variant="outline"
          >
            Volver a pendientes
          </Button>
          <Button
            className={cn("h-11", posPrimaryButtonClass)}
            disabled={commitBlockedReason !== null || isCommitPending}
            onClick={onCommit}
            type="button"
          >
            {isCommitPending ? "Confirmando..." : "Confirmar recepcion"}
          </Button>
        </div>
      </div>
    </PosSummaryPanel>
  );
}

function ReceiptDetailSurface({
  detail,
  focusToken,
  isLoading,
  isReceivable,
  lines,
  pendingShipmentCount,
  queryError,
  timezone,
  onReceivedQuantityChange,
  onVarianceReasonChange,
  varianceLineCount,
}: {
  detail: TransferDetailResponse | null;
  focusToken: string | null;
  isLoading: boolean;
  isReceivable: boolean;
  lines: TransferReceiptLineDraft[];
  pendingShipmentCount: number;
  queryError: unknown;
  timezone: string;
  onReceivedQuantityChange: (shipmentLineId: string, quantityText: string) => void;
  onVarianceReasonChange: (shipmentLineId: string, varianceReason: string) => void;
  varianceLineCount: number;
}) {
  if (isLoading) {
    return (
      <ListDetailColumn contentClassName="min-h-0 overflow-hidden" title="Detalle del envio">
        <OperationalStatus
          description="Consultando lineas, cantidades esperadas y estado actual del envio."
          title="Cargando envio"
        />
      </ListDetailColumn>
    );
  }

  if (queryError) {
    return (
      <ListDetailColumn contentClassName="min-h-0 overflow-hidden" title="Detalle del envio">
        <OperationalStatus
          description={toTransferReceiptErrorMessage(
            queryError,
            "Confirma que el envio siga pendiente y disponible para esta sucursal.",
          )}
          title="Envio no disponible"
        />
      </ListDetailColumn>
    );
  }

  if (!detail) {
    return (
      <ListDetailColumn contentClassName="min-h-0 overflow-hidden" title="Detalle del envio">
        <div className="grid h-full min-h-0 place-items-center rounded-xl border border-dashed border-[var(--pos-shell-border)] bg-[var(--pos-shell-muted)] px-4 py-6 text-center">
          <div className="grid max-w-md gap-1.5">
            <p className="text-base font-semibold text-slate-950">
              {pendingShipmentCount === 0
                ? "No hay envios pendientes para esta sucursal."
                : "Selecciona un envio pendiente."}
            </p>
            <p className="text-sm leading-6 text-slate-600">
              {pendingShipmentCount === 0
                ? "Cuando llegue un envio en transito, aparecera aqui."
                : "Elige el envio correcto para comenzar la recepcion."}
            </p>
          </div>
        </div>
      </ListDetailColumn>
    );
  }

  return (
    <ListDetailColumn
      contentClassName="min-h-0 overflow-hidden"
      title={detail.shipment_summary.folio}
    >
      <div className="grid h-full min-h-0 grid-rows-[auto_minmax(0,1fr)] gap-2.5">
        <div className="grid gap-2.5">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div className="min-w-0">
              <MovementBanner
                destinationLabel={detail.shipment.destination_branch_name}
                originLabel={detail.shipment.source_branch_name}
              />
            </div>

            <span
              className="pos-chip shrink-0"
              data-tone={getTransferStatusTone(detail.shipment.status)}
            >
              {getTransferStatusLabel(detail.shipment.status)}
            </span>
          </div>

          <div className="grid gap-2 md:grid-cols-4">
            <SummaryCell label="Origen" value={detail.shipment.source_branch_name} />
            <SummaryCell
              label="Destino"
              value={detail.shipment.destination_branch_name ?? EMPTY_VALUE_TEXT}
            />
            <SummaryCell
              label="Fecha"
              value={formatLocalDateTime(
                detail.shipment.committed_at_utc ?? detail.shipment.created_at_utc,
                timezone,
              )}
            />
            <SummaryCell label="Estado" value={getTransferStatusLabel(detail.shipment.status)} />
          </div>

          {detail.shipment.notes?.trim() ? (
            <details className="rounded-xl border border-[var(--pos-shell-border)] bg-white px-3 py-2.5">
              <summary className="cursor-pointer text-sm font-semibold text-slate-900">
                Notas del envio
              </summary>
              <p className="mt-2 text-sm leading-6 text-slate-700">{detail.shipment.notes}</p>
            </details>
          ) : null}

          {!isReceivable ? (
            <InlineNotice tone="warning">
              Este envio ya no esta disponible para recepcion. Revisa su estado actual antes de
              continuar.
            </InlineNotice>
          ) : null}

          {varianceLineCount > 0 ? (
            <InlineNotice tone="warning">
              Hay diferencias capturadas. Documenta el motivo en cada linea antes de confirmar.
            </InlineNotice>
          ) : null}
        </div>

        <div className="grid min-h-0 grid-rows-[auto_minmax(0,1fr)] gap-2.5 rounded-xl border border-[var(--pos-shell-border)] bg-[var(--pos-shell-surface)] p-3">
          <LineComparisonHeader />
          <div className="min-h-0 overflow-y-auto pr-1">
            <div className="grid gap-2.5">
              {lines.map((line, index) => (
                <ReceiptLineRow
                  focusToken={focusToken}
                  isPrimaryControl={index === 0}
                  key={line.shipmentLineId}
                  line={line}
                  onReceivedQuantityChange={onReceivedQuantityChange}
                  onVarianceReasonChange={onVarianceReasonChange}
                />
              ))}
            </div>
          </div>
        </div>
      </div>
    </ListDetailColumn>
  );
}

export function TransferReceiptScreen() {
  const accessToken = usePosAuthStore((state) => state.accessToken);
  const queryClient = useQueryClient();
  const showError = useStatusMessageStore((state) => state.showError);
  const showSuccess = useStatusMessageStore((state) => state.showSuccess);
  const pendingScannerInputRef = useRef<HTMLInputElement>(null);

  const [selectedTransferId, setSelectedTransferId] = useState<string | null>(null);
  const [receiptLines, setReceiptLines] = useState<TransferReceiptLineDraft[]>([]);
  const [notes, setNotes] = useState("");
  const [lastReceivedTransfer, setLastReceivedTransfer] =
    useState<TransferDetailResponse | null>(null);
  const [isConfirmDialogOpen, setIsConfirmDialogOpen] = useState(false);
  const [isNotesExpanded, setIsNotesExpanded] = useState(false);
  const [commitErrorMessage, setCommitErrorMessage] = useState<string | null>(null);
  const [centerView, setCenterView] = useState<TransferReceiptCenterView>("pending");
  const [selectedHistoryTransferId, setSelectedHistoryTransferId] =
    useState<string | null>(null);
  const [pendingSearchText, setPendingSearchText] = useState("");
  const [pendingScannerText, setPendingScannerText] = useState("");
  const [pendingScannerFolio, setPendingScannerFolio] = useState<string | null>(null);
  const [pendingOriginBranchId, setPendingOriginBranchId] = useState("ALL");
  const [historySearchText, setHistorySearchText] = useState("");
  const [historyScope, setHistoryScope] = useState("CURRENT_SHIFT");
  const [historySourceBranchId, setHistorySourceBranchId] = useState("ALL");
  const [historyStatus, setHistoryStatus] = useState("ALL");

  const operationsBootstrapQuery = useOperationsBootstrapQuery();
  const currentCashSessionQuery = useCurrentCashSessionQuery();
  const pendingInboundTransfersQuery = usePendingInboundTransfersQuery();
  const transferDetailQuery = useTransferDetailQuery(
    centerView === "pending" ? selectedTransferId : null,
  );
  const receiptHistoryQuery = useTransferReceiptHistoryQuery(
    {
      scope: historyScope,
      sourceBranchId:
        historySourceBranchId !== "ALL" ? historySourceBranchId : undefined,
      status: historyStatus !== "ALL" ? historyStatus : undefined,
    },
    centerView === "history",
  );
  const selectedHistoryTransferQuery = useTransferDetailQuery(
    centerView === "history" ? selectedHistoryTransferId : null,
  );

  const clearSelection = useCallback(() => {
    setSelectedTransferId(null);
    setReceiptLines([]);
    setNotes("");
    setIsNotesExpanded(false);
    setCommitErrorMessage(null);
  }, []);

  useEffect(() => {
    const transferDetail = transferDetailQuery.data;
    if (transferDetail === undefined) {
      return;
    }

    if (transferDetail === null) {
      setReceiptLines([]);
      setNotes("");
      setIsNotesExpanded(false);
      setCommitErrorMessage(null);
      return;
    }

    const draftState = createTransferReceiptDraftState(transferDetail.shipment);
    setReceiptLines(draftState.lines);
    setNotes("");
    setIsNotesExpanded(false);
    setCommitErrorMessage(null);
  }, [transferDetailQuery.data]);

  useEffect(() => {
    function handleKeyboard(event: KeyboardEvent) {
      if (event.key !== "Escape") {
        return;
      }

      if (isConfirmDialogOpen) {
        event.preventDefault();
        setIsConfirmDialogOpen(false);
        return;
      }

      if (centerView === "history") {
        event.preventDefault();
        setCenterView("pending");
        return;
      }

      if (selectedTransferId !== null) {
        event.preventDefault();
        clearSelection();
      }
    }

    window.addEventListener("keydown", handleKeyboard);
    return () => window.removeEventListener("keydown", handleKeyboard);
  }, [centerView, clearSelection, isConfirmDialogOpen, selectedTransferId]);

  const commitMutation = useMutation({
    mutationFn: async () => {
      if (
        accessToken === null ||
        operationsBootstrapQuery.data === undefined ||
        selectedTransferId === null
      ) {
        throw new Error(
          "Se requiere autenticacion, contexto de estacion y un envio seleccionado.",
        );
      }

      return receiveTransfer(accessToken, selectedTransferId, {
        workstation_code: operationsBootstrapQuery.data.workstation.code,
        lines: buildTransferReceiveLines(receiptLines),
        notes: notes.trim().length > 0 ? notes.trim() : null,
      });
    },
    onSuccess: async (detail) => {
      setLastReceivedTransfer(detail);
      setSelectedHistoryTransferId(detail.shipment.id);
      setCommitErrorMessage(null);
      setIsConfirmDialogOpen(false);
      clearSelection();
      showSuccess(`Recepcion registrada. Folio ${detail.receipt_summary?.folio ?? "REC"}.`);

      await Promise.all([
        queryClient.invalidateQueries({
          queryKey: pendingInboundTransfersQueryKey(
            operationsBootstrapQuery.data!.workstation.code,
          ),
        }),
        queryClient.invalidateQueries({
          queryKey: transferDetailQueryKey(
            operationsBootstrapQuery.data!.workstation.code,
            detail.shipment.id,
          ),
        }),
        queryClient.invalidateQueries({
          queryKey: transferReceiptHistoryQueryKey(
            operationsBootstrapQuery.data!.workstation.code,
            {
              scope: historyScope,
              sourceBranchId:
                historySourceBranchId !== "ALL"
                  ? historySourceBranchId
                  : undefined,
              status: historyStatus !== "ALL" ? historyStatus : undefined,
            },
          ),
        }),
      ]);
    },
  });

  const pendingTransfers = useMemo(
    () => pendingInboundTransfersQuery.data?.transfers ?? [],
    [pendingInboundTransfersQuery.data],
  );
  const selectedDetail = transferDetailQuery.data ?? null;
  const selectedDetailReceivable = isTransferReceivable(selectedDetail);
  const expectedTotalMilli = getTransferReceiptExpectedTotalMilli(receiptLines);
  const receivedTotalMilli = getTransferReceiptReceivedTotalMilli(receiptLines);
  const differenceTotalMilli = getTransferReceiptDifferenceTotalMilli(receiptLines);
  const varianceLineCount = getTransferReceiptVarianceLineCount(receiptLines);
  const expectedUnitsText = formatQuantityFromMilliUnits(expectedTotalMilli);
  const receivedUnitsText = formatQuantityFromMilliUnits(receivedTotalMilli);
  const differenceTotalText = formatDifferenceLabel(differenceTotalMilli);
  const hasMissingQuantities = hasTransferReceiptMissingQuantities(receiptLines);
  const hasMissingVarianceReason = hasTransferReceiptMissingVarianceReason(receiptLines);
  const hasLineMismatch =
    selectedDetail !== null && selectedDetail.shipment.lines.length !== receiptLines.length;
  const transferQueryMessage =
    transferDetailQuery.error !== null
      ? toTransferReceiptErrorMessage(
          transferDetailQuery.error,
          "Confirma que el envio siga pendiente y disponible para esta sucursal.",
        )
      : null;
  const commitBlockedReason = getTransferReceiptCommitBlockedReason({
    hasLineMismatch,
    hasMissingQuantities,
    hasMissingVarianceReason,
    hasSelectedTransfer: selectedTransferId !== null,
    isReceivable: selectedDetailReceivable,
    pendingShipmentCount: pendingTransfers.length,
  });
  const uiState = getTransferReceiptUiState({
    hasConfirmedReceipt: lastReceivedTransfer !== null,
    hasError: transferQueryMessage !== null || commitErrorMessage !== null,
    hasLoadedLines: receiptLines.length > 0,
    hasSelectedTransfer: selectedTransferId !== null,
    hasVariance: varianceLineCount > 0,
    isConfirmPending: commitMutation.isPending,
    pendingShipmentCount: pendingTransfers.length,
    requiresQuantityCapture: hasMissingQuantities,
  });
  const activeTimezone = operationsBootstrapQuery.data?.branch.timezone ?? "UTC";
  const selectedHistoryDetail = selectedHistoryTransferQuery.data ?? null;
  const debouncedPendingSearch = useDebouncedValue(pendingSearchText, 160);
  const pendingOriginOptions = useMemo(() => {
    const seen = new Map<string, string>();
    for (const transfer of pendingTransfers) {
      if (!seen.has(transfer.source_branch_id)) {
        seen.set(transfer.source_branch_id, transfer.source_branch_name);
      }
    }

    return Array.from(seen, ([value, label]) => ({ label, value })).sort(
      (left, right) => left.label.localeCompare(right.label),
    );
  }, [pendingTransfers]);
  const filteredPendingTransfers = useMemo(() => {
    const normalizedSearch = debouncedPendingSearch.trim().toLowerCase();

    return pendingTransfers.filter((transfer) => {
      if (
        pendingOriginBranchId !== "ALL" &&
        transfer.source_branch_id !== pendingOriginBranchId
      ) {
        return false;
      }

      if (normalizedSearch.length === 0) {
        return true;
      }

      const haystack = [
        transfer.folio,
        transfer.source_branch_code,
        transfer.source_branch_name,
      ]
        .join(" ")
        .toLowerCase();

      return haystack.includes(normalizedSearch);
    });
  }, [debouncedPendingSearch, pendingOriginBranchId, pendingTransfers]);

  useEffect(() => {
    if (pendingScannerFolio === null) {
      return;
    }

    const exactMatch = filteredPendingTransfers.find((transfer) =>
      matchesScannerValue(transfer.folio, pendingScannerFolio),
    );

    if (exactMatch) {
      setSelectedTransferId(exactMatch.id);
      setLastReceivedTransfer(null);
      setCommitErrorMessage(null);
      setPendingScannerFolio(null);
      return;
    }

    if (filteredPendingTransfers.length === 1) {
      setSelectedTransferId(filteredPendingTransfers[0]!.id);
      setLastReceivedTransfer(null);
      setCommitErrorMessage(null);
      setPendingScannerFolio(null);
    }
  }, [filteredPendingTransfers, pendingScannerFolio]);

  const historyRecords = useMemo(
    () =>
      buildReceiptHistoryRecords(
        receiptHistoryQuery.data,
        activeTimezone,
        historySearchText,
      ),
    [activeTimezone, historySearchText, receiptHistoryQuery.data],
  );
  const lineSummaryItems = useMemo(
    () => buildReceiptDraftLineSummaryItems(receiptLines),
    [receiptLines],
  );

  function handlePendingShipmentScanSubmit() {
    const scannedValue =
      parseShipmentScannerValue(pendingScannerText) ?? normalizeScannerText(pendingScannerText);

    if (scannedValue.length === 0) {
      return;
    }

    setPendingScannerText("");
    setPendingScannerFolio(scannedValue);
    setPendingSearchText(scannedValue);
  }

  const rightPanel =
    operationsBootstrapQuery.isPending ||
    currentCashSessionQuery.isPending ||
    pendingInboundTransfersQuery.isPending ||
    !currentCashSessionQuery.data ||
    operationsBootstrapQuery.error ||
    currentCashSessionQuery.error ||
    pendingInboundTransfersQuery.error ? null : centerView === "history" ? (
      selectedHistoryTransferQuery.isPending ? (
        <PosSummaryPanel
          description="Resumen operativo de la recepcion seleccionada."
          stateLabel="Cargando"
          stateTone="pending"
          title="Historial de recepciones"
        >
          <OperationalStatus
            description="Consultando el detalle de la recepcion."
            title="Cargando recepcion"
          />
        </PosSummaryPanel>
      ) : selectedHistoryTransferQuery.error ? (
        <PosSummaryPanel
          description="Resumen operativo de la recepcion seleccionada."
          stateLabel="Error"
          stateTone="warning"
          title="Historial de recepciones"
        >
          <OperationalStatus
            description={toTransferReceiptErrorMessage(
              selectedHistoryTransferQuery.error,
              "No se pudo consultar el detalle del historial.",
            )}
            title="Detalle no disponible"
          />
        </PosSummaryPanel>
      ) : selectedHistoryDetail?.receipt && selectedHistoryDetail.receipt_summary ? (
        <OperationDocumentSummaryPanel
          actions={[
            {
              key: "history-back",
              label: "Recibir envio",
              leadingIcon: <ArrowLeftIcon className="h-4 w-4" />,
              onSelect: () => setCenterView("pending"),
              variant: "neutral",
            },
          ]}
          auditSummary={selectedHistoryDetail.receipt.audit_summary}
          context={{
            branchName:
              selectedHistoryDetail.receipt.destination_branch_name ??
              operationsBootstrapQuery.data.branch.name,
            userName: selectedHistoryDetail.receipt.created_by_user_full_name,
            workstationName: selectedHistoryDetail.receipt.workstation_name,
          }}
          description={`Origen ${selectedHistoryDetail.receipt.source_branch_name}`}
          kind="branchReceipt"
          lines={buildTransferDocumentLineSummaryItems(selectedHistoryDetail.receipt)}
          metrics={buildReceiptMetrics({
            differenceLineCount:
              selectedHistoryDetail.receipt_summary.quantity_summary.variance_line_count,
            differenceTotalText: formatDifferenceLabel(
              Math.round(
                (Number(
                  selectedHistoryDetail.receipt_summary.quantity_summary.received_total_quantity ??
                    "0",
                ) -
                  Number(
                    selectedHistoryDetail.receipt_summary.quantity_summary.expected_total_quantity,
                  )) *
                  1000,
              ),
            ),
            expectedUnitsText: formatQuantityFromMilliUnits(
              Number(
                selectedHistoryDetail.receipt_summary.quantity_summary.expected_total_quantity,
              ) * 1000,
            ),
            lineCount:
              selectedHistoryDetail.receipt_summary.quantity_summary.line_count,
            receivedUnitsText: formatQuantityFromMilliUnits(
              Number(
                selectedHistoryDetail.receipt_summary.quantity_summary.received_total_quantity ??
                  "0",
              ) * 1000,
            ),
          })}
          referenceValue={selectedHistoryDetail.receipt_summary.folio}
          stateLabel={getTransferStatusLabel(selectedHistoryDetail.receipt.status)}
          stateTone={getTransferStatusBadgeTone(selectedHistoryDetail.receipt.status)}
          timeZone={activeTimezone}
          timestamps={{
            committedAtLabel: "Confirmado",
            committedAtValue: selectedHistoryDetail.receipt.committed_at_utc
              ? formatLocalDateTime(
                  selectedHistoryDetail.receipt.committed_at_utc,
                  activeTimezone,
                )
              : null,
            createdAtLabel: "Creado",
            createdAtValue: formatLocalDateTime(
              selectedHistoryDetail.receipt.created_at_utc,
              activeTimezone,
            ),
          }}
          title="Recepcion seleccionada"
        />
      ) : (
        <PosSummaryPanel
          description="Selecciona una recepcion para ver su resumen."
          stateLabel="Historial"
          stateTone="pending"
          title="Historial de recepciones"
        >
          <div className="grid h-full place-items-center rounded-xl border border-dashed border-[var(--pos-shell-border)] bg-[var(--pos-shell-muted)] px-4 py-6 text-center">
            <div className="grid max-w-sm gap-1.5">
              <p className="text-base font-semibold text-slate-950">
                Selecciona una recepcion.
              </p>
              <p className="text-sm leading-6 text-slate-600">
                El panel derecho mostrara folio, cantidades y contexto operativo.
              </p>
            </div>
          </div>
        </PosSummaryPanel>
      )
    ) : lastReceivedTransfer?.receipt && lastReceivedTransfer.receipt_summary ? (
      <OperationDocumentResult
        actions={[
          {
            availabilityNote:
              getDocumentActionAvailability("branchReceiptDocument").print.unavailableReason,
            disabled: !getDocumentActionAvailability("branchReceiptDocument").print.isAvailable,
            kind: "print",
            key: "receipt-print-disabled",
            label: getDocumentActionAvailability("branchReceiptDocument").print.label,
            leadingIcon: <PrinterIcon className="h-4 w-4" />,
            onSelect: () => undefined,
            variant: "neutral",
          },
          {
            key: "receipt-view-history",
            label: "Ver historial",
            leadingIcon: <RotateCcwIcon className="h-4 w-4" />,
            onSelect: () => {
              setCenterView("history");
              setSelectedHistoryTransferId(lastReceivedTransfer.shipment.id);
            },
            variant: "secondary",
          },
          {
            key: "receipt-new",
            label: "Nueva recepcion",
            leadingIcon: <ClipboardIcon className="h-4 w-4" />,
            onSelect: () => setLastReceivedTransfer(null),
            variant: "primary",
          },
        ]}
        auditSummary={lastReceivedTransfer.receipt.audit_summary}
        context={{
          branchName:
            lastReceivedTransfer.receipt.destination_branch_name ??
            operationsBootstrapQuery.data.branch.name,
          userName: lastReceivedTransfer.receipt.created_by_user_full_name,
          workstationName: lastReceivedTransfer.receipt.workstation_name,
        }}
        description={
          lastReceivedTransfer.receipt_summary.quantity_summary.has_variance
            ? "La recepcion quedo registrada con diferencias y motivos capturados."
            : "La recepcion quedo confirmada y el envio ya no aparece como pendiente."
        }
        kind="branchReceipt"
        metrics={buildReceiptMetrics({
          differenceLineCount:
            lastReceivedTransfer.receipt_summary.quantity_summary.variance_line_count,
          differenceTotalText: formatDifferenceLabel(
            Math.round(
              (Number(
                lastReceivedTransfer.receipt_summary.quantity_summary.received_total_quantity ??
                  "0",
              ) -
                Number(
                  lastReceivedTransfer.receipt_summary.quantity_summary.expected_total_quantity,
                )) * 1000,
            ),
          ),
          expectedUnitsText: formatQuantityFromMilliUnits(
            Number(
              lastReceivedTransfer.receipt_summary.quantity_summary.expected_total_quantity,
            ) * 1000,
          ),
          lineCount: lastReceivedTransfer.receipt_summary.quantity_summary.line_count,
          receivedUnitsText: formatQuantityFromMilliUnits(
            Number(
              lastReceivedTransfer.receipt_summary.quantity_summary.received_total_quantity ??
                "0",
            ) * 1000,
          ),
        })}
        referenceValue={lastReceivedTransfer.receipt_summary.folio}
        timeZone={activeTimezone}
        timestamps={{
          committedAtLabel: "Confirmado",
          committedAtValue: lastReceivedTransfer.receipt.committed_at_utc
            ? formatLocalDateTime(
                lastReceivedTransfer.receipt.committed_at_utc,
                activeTimezone,
              )
            : null,
          createdAtLabel: "Creado",
          createdAtValue: formatLocalDateTime(
            lastReceivedTransfer.receipt.created_at_utc,
            activeTimezone,
          ),
        }}
      />
    ) : (
      <ReceiptSummaryPanel
        centerView={centerView}
        commitBlockedReason={commitBlockedReason}
        commitErrorMessage={commitErrorMessage}
        detail={selectedDetail}
        detailTimezone={activeTimezone}
        differenceTotalText={differenceTotalText}
        expectedUnitsText={expectedUnitsText}
        isCommitPending={commitMutation.isPending}
        isNotesExpanded={isNotesExpanded}
        lastReceivedTransfer={lastReceivedTransfer}
        lineSummaryItems={lineSummaryItems}
        notes={notes}
        onClearSelection={clearSelection}
        onCommit={() => {
          if (commitBlockedReason === null && !commitMutation.isPending) {
            setCommitErrorMessage(null);
            setIsConfirmDialogOpen(true);
          }
        }}
        onHistoryToggle={() =>
          setCenterView((state) => (state === "history" ? "pending" : "history"))
        }
        onNotesChange={(value) => {
          if (commitErrorMessage !== null) {
            setCommitErrorMessage(null);
          }
          if (lastReceivedTransfer !== null) {
            setLastReceivedTransfer(null);
          }
          setNotes(value);
        }}
        onToggleNotes={() => setIsNotesExpanded((state) => !state)}
        receivedUnitsText={receivedUnitsText}
        uiState={uiState}
        varianceLineCount={varianceLineCount}
      />
    );
  useAppShellRightPanel(rightPanel);

  if (
    operationsBootstrapQuery.isPending ||
    currentCashSessionQuery.isPending ||
    pendingInboundTransfersQuery.isPending
  ) {
    return (
      <OperationalStatus
        description="Consultando los envios pendientes de esta sucursal."
        title="Cargando Recibir envio"
      />
    );
  }

  if (operationsBootstrapQuery.error) {
    return (
      <OperationalStatus
        action={<Button onClick={() => operationsBootstrapQuery.refetch()}>Reintentar</Button>}
        description={toOperationalErrorMessage(
          operationsBootstrapQuery.error,
          "Confirma la configuracion de la estacion y los datos operativos iniciales.",
        )}
        title="Recibir envio no esta disponible"
      />
    );
  }

  if (currentCashSessionQuery.error) {
    return (
      <OperationalStatus
        action={<Button onClick={() => currentCashSessionQuery.refetch()}>Reintentar</Button>}
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

  if (pendingInboundTransfersQuery.error) {
    return (
      <OperationalStatus
        action={<Button onClick={() => pendingInboundTransfersQuery.refetch()}>Reintentar</Button>}
        description={toTransferReceiptErrorMessage(
          pendingInboundTransfersQuery.error,
          "Confirma la conexion con la API y el estado de los envios pendientes.",
        )}
        title="No fue posible consultar los envios pendientes"
      />
    );
  }

  return (
    <>
      <div className="grid gap-3 lg:h-full lg:grid-rows-[minmax(0,1fr)_auto]">
        <CentralWorkspaceSheet
          className="lg:h-full"
          contentClassName="min-h-0 overflow-hidden px-3 pb-3 pt-2"
          header={
            <CompactPageHeader
              secondaryChips={
                <ModuleStateChip
                  tone={centerView === "history" ? "info" : selectedTransferId ? "primary" : "muted"}
                >
                  {centerView === "history"
                    ? `${historyRecords.length} recepciones`
                    : selectedTransferId === null
                      ? `${filteredPendingTransfers.length} pendientes`
                      : `Folio ${selectedDetail?.shipment_summary.folio ?? "..."}`}
                </ModuleStateChip>
              }
              stateChip={
                <ModuleStateChip tone={getReceiptStateChipTone(centerView, uiState)}>
                  {centerView === "history" ? "Historial" : getReceiptUiStateLabel(uiState)}
                </ModuleStateChip>
              }
              title="Recibir envio"
            >
              {centerView === "pending" ? (
                <FlowGuide
                  activeStepKey={
                    selectedTransferId === null
                      ? "pending"
                      : isTransferReceivable(selectedDetail)
                        ? "receipt"
                        : "confirm"
                  }
                  steps={[
                    {
                      key: "pending",
                      label: "Pendientes",
                      state: selectedTransferId ? "completed" : "current",
                    },
                    {
                      key: "receipt",
                      label: "Recepcion",
                      state: selectedTransferId ? "current" : "upcoming",
                    },
                    {
                      key: "confirm",
                      label: "Confirmacion",
                      state:
                        selectedTransferId === null
                          ? "blocked"
                          : hasTransferReceiptMissingQuantities(receiptLines)
                            ? "upcoming"
                            : "current",
                    },
                  ]}
                  variant="compact"
                />
              ) : null}
            </CompactPageHeader>
          }
        >
          {centerView === "history" ? (
            <PosHistoryView
              action={
                <Button
                  className={cn("h-10 px-3", posOutlineButtonClass)}
                  onClick={() => setCenterView("pending")}
                  type="button"
                  variant="outline"
                >
                  <ArrowLeftIcon className="h-4 w-4" />
                  Recibir envio
                </Button>
              }
              description="Consulta las recepciones confirmadas para esta estacion y filtra por turno, origen o estado."
              title="Historial de recepciones"
              toolbar={
                <PosFilterBar
                  chipFilters={(
                    receiptHistoryQuery.data?.available_scopes ?? [
                      { code: "CURRENT_SHIFT", label: "Turno actual" },
                      { code: "TODAY", label: "Hoy" },
                      { code: "RECENT", label: "Recientes" },
                    ]
                  ).map((scope: OperationHistoryScopeView) => ({
                    isActive: historyScope === scope.code,
                    key: scope.code,
                    label: scope.label,
                    onSelect: () => setHistoryScope(scope.code),
                  }))}
                  countLabel={
                    <span className="pos-chip" data-tone="muted">
                      {historyRecords.length} registros
                    </span>
                  }
                  searchInput={{
                    ariaLabel: "Buscar recepcion por folio u origen",
                    onChange: setHistorySearchText,
                    placeholder: "Buscar por folio u origen",
                    value: historySearchText,
                  }}
                  selectFilters={[
                    {
                      ariaLabel: "Filtrar historial por origen",
                      key: "history-source",
                      onChange: setHistorySourceBranchId,
                      options: [
                        { label: "Todos los origenes", value: "ALL" },
                        ...(receiptHistoryQuery.data?.available_source_branches ?? []).map(
                          (option: OperationHistoryFilterOptionView) => ({
                            label: option.label,
                            value: option.value,
                          }),
                        ),
                      ],
                      value: historySourceBranchId,
                    },
                    {
                      ariaLabel: "Filtrar historial por estado",
                      key: "history-status",
                      onChange: setHistoryStatus,
                      options: [
                        { label: "Todos los estados", value: "ALL" },
                        ...(receiptHistoryQuery.data?.available_statuses ?? []).map(
                          (option: OperationHistoryFilterOptionView) => ({
                            label: option.label,
                            value: option.value,
                          }),
                        ),
                      ],
                      value: historyStatus,
                    },
                  ]}
                  title="Recepciones confirmadas"
                />
              }
            >
              {receiptHistoryQuery.error ? (
                <OperationalStatus
                  action={
                    <Button
                      className={posPrimaryButtonClass}
                      onClick={() => void receiptHistoryQuery.refetch()}
                    >
                      Reintentar
                    </Button>
                  }
                  description={toOperationalErrorMessage(
                    receiptHistoryQuery.error,
                    "No fue posible consultar el historial de recepciones.",
                  )}
                  title="El historial no esta disponible"
                />
              ) : (
                <OperationHistoryList
                  emptyDescription="Aun no hay recepciones confirmadas para los filtros seleccionados."
                  loading={receiptHistoryQuery.isPending}
                  onSelect={(record) => setSelectedHistoryTransferId(record.id)}
                  records={historyRecords}
                  selectedRecordId={selectedHistoryTransferId}
                />
              )}
            </PosHistoryView>
          ) : (
            <ResponsivePaneLayout
              className="h-full gap-2.5"
              detail={
                <ReceiptDetailSurface
                  detail={selectedDetail}
                  focusToken={selectedTransferId}
                  isLoading={selectedTransferId !== null && transferDetailQuery.isPending}
                  isReceivable={selectedDetailReceivable}
                  lines={receiptLines}
                  onReceivedQuantityChange={(shipmentLineId, quantityText) => {
                    if (commitErrorMessage !== null) {
                      setCommitErrorMessage(null);
                    }
                    if (lastReceivedTransfer !== null) {
                      setLastReceivedTransfer(null);
                    }
                    setReceiptLines((state) =>
                      updateTransferReceiptLineQuantity(state, shipmentLineId, quantityText),
                    );
                  }}
                  onVarianceReasonChange={(shipmentLineId, varianceReason) => {
                    if (commitErrorMessage !== null) {
                      setCommitErrorMessage(null);
                    }
                    if (lastReceivedTransfer !== null) {
                      setLastReceivedTransfer(null);
                    }
                    setReceiptLines((state) =>
                      updateTransferReceiptLineVarianceReason(
                        state,
                        shipmentLineId,
                        varianceReason,
                      ),
                    );
                  }}
                  pendingShipmentCount={filteredPendingTransfers.length}
                  queryError={transferDetailQuery.error}
                  timezone={activeTimezone}
                  varianceLineCount={varianceLineCount}
                />
              }
              list={
                <ListDetailColumn
                  contentClassName="min-h-0 overflow-hidden"
                  title="Pendientes"
                  tone="muted"
                >
                  <div className="grid h-full min-h-0 grid-rows-[auto_minmax(0,1fr)] gap-3">
                    <div className="grid gap-3">
                      <PosScannerInput
                        ariaLabel="Escanear folio de envio"
                        inputRef={pendingScannerInputRef}
                        modeLabel="Escaneo de envio"
                        onChange={setPendingScannerText}
                        onSubmit={handlePendingShipmentScanSubmit}
                        placeholder="Escanear folio de envio"
                        submitLabel="Abrir envio"
                        value={pendingScannerText}
                      />
                      <PosFilterBar
                        countLabel={
                          <span className="pos-chip" data-tone="muted">
                            {filteredPendingTransfers.length} visibles
                          </span>
                        }
                        searchInput={{
                          ariaLabel: "Buscar envio pendiente",
                          onChange: (value) => {
                            setPendingScannerFolio(null);
                            setPendingSearchText(value);
                          },
                          placeholder: "Buscar por folio u origen",
                          value: pendingSearchText,
                        }}
                        selectFilters={[
                          {
                            ariaLabel: "Filtrar pendientes por origen",
                            key: "pending-origin",
                            onChange: setPendingOriginBranchId,
                            options: [
                              { label: "Todos los origenes", value: "ALL" },
                              ...pendingOriginOptions,
                            ],
                            value: pendingOriginBranchId,
                          },
                        ]}
                        title="Envios pendientes"
                      />
                    </div>

                    <div className="min-h-0 overflow-hidden pr-1">
                      <PosRecordList
                        emptyDescription="No hay envios pendientes para los filtros actuales."
                        emptyTitle="Sin pendientes"
                        getKey={(shipment) => shipment.id}
                        onSelect={(shipment) => {
                          setSelectedTransferId(shipment.id);
                          setLastReceivedTransfer(null);
                          setCommitErrorMessage(null);
                        }}
                        records={filteredPendingTransfers}
                        renderContent={(shipment) => (
                          <PendingInboundRecord
                            shipment={shipment}
                            timezone={activeTimezone}
                          />
                        )}
                        selectedKey={selectedTransferId}
                      />
                    </div>
                  </div>
                </ListDetailColumn>
              }
            />
          )}
        </CentralWorkspaceSheet>

        <section className="rounded-xl border border-[var(--pos-shell-border)] bg-[var(--pos-shell-surface)] px-4 py-3 shadow-sm lg:hidden">
          <div className="flex items-center justify-between gap-3">
            <div>
              <p className="text-sm font-medium text-slate-900">Recibir envio</p>
              <p className="text-sm text-slate-600">
                {centerView === "history"
                  ? `${historyRecords.length} recepciones visibles.`
                  : selectedTransferId === null
                    ? `${filteredPendingTransfers.length} envios pendientes.`
                  : `${receivedUnitsText} unidades capturadas.`}
              </p>
            </div>
            <span className="pos-chip" data-tone="primary">
              {centerView === "history"
                ? historyRecords.length
                : selectedTransferId === null
                  ? filteredPendingTransfers.length
                  : receiptLines.length}
            </span>
          </div>
        </section>
      </div>

      <ReceiptConfirmDialog
        detail={selectedDetail}
        differenceTotalText={differenceTotalText}
        expectedUnitsText={expectedUnitsText}
        isOpen={isConfirmDialogOpen}
        isPending={commitMutation.isPending}
        lineCount={receiptLines.length}
        lines={lineSummaryItems}
        onCancel={() => setIsConfirmDialogOpen(false)}
        onConfirm={() => {
          commitMutation.reset();
          setCommitErrorMessage(null);
          void commitMutation.mutateAsync().catch((error) => {
            const nextMessage = toTransferReceiptErrorMessage(
              error,
              "No se pudo registrar la recepcion. Intenta de nuevo.",
            );
            setIsConfirmDialogOpen(false);
            setCommitErrorMessage(nextMessage);
            showError(nextMessage);
          });
        }}
        receivedUnitsText={receivedUnitsText}
        varianceLineCount={varianceLineCount}
      />
    </>
  );
}

