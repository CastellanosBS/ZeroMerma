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
  OperationDocumentSummaryPanel,
  OperationHistoryList,
  type OperationDocumentMetric,
  type OperationHistoryRecord,
  type OperationLineSummaryItem,
} from "../../components/operation-documents";
import { OperationalStatus } from "../../components/operational-status";
import { PosSummaryPanel } from "../../components/pos-module-layout";
import {
  PosFilterBar,
  PosHistoryView,
  PosRecordTable,
  type PosRecordColumn,
} from "../../components/pos-records";
import {
  CentralWorkspaceSheet,
  FlowGuide,
  InlineNotice,
  ModuleStateChip,
  CompactPageHeader,
  SearchField,
  ScrollPane,
} from "../../components/pos-module-primitives";
import {
  ArrowLeftIcon,
  ChevronRightIcon,
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

function LineComparisonHeader() {
  return (
    <div className="grid grid-cols-[minmax(0,1.4fr)_5rem_6.5rem_6rem_minmax(7rem,0.8fr)] gap-3 border-b border-[var(--pos-shell-border)] bg-[var(--pos-shell-muted)] px-3 py-2 text-[11px] font-semibold uppercase tracking-[0.08em] text-slate-500">
      <span>Producto</span>
      <span className="text-right">Enviada</span>
      <span className="text-right">Recibida</span>
      <span className="text-right">Diferencia</span>
      <span>Motivo</span>
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
        "grid min-h-12 grid-cols-[minmax(0,1.4fr)_5rem_6.5rem_6rem_minmax(7rem,0.8fr)] items-center gap-3 border-t border-[var(--pos-shell-border)] px-3 py-2 first:border-t-0",
        hasVariance && "bg-[var(--ui-color-warning-soft)]/35",
      )}
    >
      <span
        className="min-w-0 truncate text-sm font-semibold text-slate-950"
        title={`${line.productName} - ${line.productClassName} / ${line.productCode}`}
      >
        {line.productName}
      </span>
      <span className="text-right text-sm font-semibold text-slate-950 [font-variant-numeric:tabular-nums]">
        {line.expectedQuantityText}
      </span>
      <input
        aria-label={`Cantidad recibida de ${line.productName}`}
        className={cn(
          "h-9 rounded-lg px-2 text-right text-sm font-semibold shadow-sm [font-variant-numeric:tabular-nums]",
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
      <span
        className={cn(
          "text-right text-sm font-semibold [font-variant-numeric:tabular-nums]",
          hasVariance ? "text-[var(--ui-color-warning)]" : "text-slate-400",
        )}
      >
        {hasVariance ? differenceSummary : EMPTY_VALUE_TEXT}
      </span>
      {hasVariance ? (
        <input
          aria-label={`Motivo de diferencia de ${line.productName}`}
          className={cn("h-9 rounded-lg px-2 text-sm shadow-sm", posInputClass)}
          list={`variance-reasons-${line.shipmentLineId}`}
          onChange={(event) =>
            onVarianceReasonChange(line.shipmentLineId, event.target.value)
          }
          placeholder="Motivo"
          value={line.varianceReason}
        />
      ) : (
        <span className="truncate text-sm text-slate-400">{EMPTY_VALUE_TEXT}</span>
      )}
      <datalist id={`variance-reasons-${line.shipmentLineId}`}>
        {VARIANCE_REASON_SUGGESTIONS.map((reason) => (
          <option key={reason} value={reason} />
        ))}
      </datalist>
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
  differenceTotalText,
  expectedUnitsText,
  isCommitPending,
  isNotesExpanded,
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
  differenceTotalText: string;
  expectedUnitsText: string;
  isCommitPending: boolean;
  isNotesExpanded: boolean;
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
  const showBlockingNotice = detail !== null && commitBlockedReason !== null;

  return (
    <PosSummaryPanel
      description="Resumen operativo"
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
          {detail ? (
            <div className="grid gap-2 rounded-lg border border-[var(--pos-shell-border)] bg-[var(--pos-shell-muted)]/70 px-3 py-2 text-sm">
              <ReceiptSummaryRow label="Origen" value={detail.shipment.source_branch_name} />
              <ReceiptSummaryRow label="Folio" value={detail.shipment_summary.folio} />
              <ReceiptSummaryRow label="Total esperado" value={expectedUnitsText} />
              <ReceiptSummaryRow label="Total recibido" value={receivedUnitsText} />
              <ReceiptSummaryRow
                label="Diferencia"
                tone={varianceLineCount > 0 ? "warning" : "default"}
                value={differenceTotalText}
              />
            </div>
          ) : (
            <div className="rounded-lg border border-dashed border-[var(--pos-shell-border)] bg-white px-3 py-4 text-sm text-slate-600">
              {uiState === "NO_PENDING_SHIPMENTS"
                ? "No hay envios pendientes para esta sucursal."
                : "Selecciona o escanea un envio pendiente."}
            </div>
          )}

          {showBlockingNotice ? (
            <InlineNotice tone="warning">{commitBlockedReason}</InlineNotice>
          ) : null}
        </div>

        <div className="rounded-lg border border-[var(--pos-shell-border)] bg-white">
          <button
            aria-expanded={isNotesExpanded}
            className="flex w-full items-center justify-between gap-3 px-3 py-2 text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--pos-ring)]"
            disabled={detail === null || isCommitPending}
            onClick={onToggleNotes}
            type="button"
          >
            <span className="truncate text-sm font-semibold text-slate-900">
              {notes.trim().length > 0 ? "Observacion agregada" : "Agregar observacion"}
            </span>
            <ChevronRightIcon
              className={cn(
                "h-4 w-4 text-slate-400 transition",
                isNotesExpanded && "rotate-90",
              )}
            />
          </button>
          {isNotesExpanded ? (
            <div className="border-t border-[var(--pos-shell-border)] px-3 pb-3 pt-2">
              <textarea
                aria-label="Notas de recepcion"
                className={cn("min-h-16 rounded-lg px-3 py-2 text-sm shadow-sm", posInputClass)}
                disabled={detail === null || isCommitPending}
                onChange={(event) => onNotesChange(event.target.value)}
                placeholder="Observacion opcional"
                value={notes}
              />
            </div>
          ) : null}
        </div>

        <div className="min-h-0" />

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
            {centerView === "history" ? "Volver a pendientes" : "Ver historial"}
          </Button>
          {detail ? (
            <Button
              className={cn("h-10", posOutlineButtonClass)}
              disabled={isCommitPending}
              onClick={onClearSelection}
              type="button"
              variant="outline"
            >
              Volver a pendientes
            </Button>
          ) : null}
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

function ReceiptSummaryRow({
  label,
  tone = "default",
  value,
}: {
  label: string;
  tone?: "default" | "warning";
  value: string;
}) {
  return (
    <div className="flex items-center justify-between gap-3">
      <span className="font-medium text-slate-600">{label}</span>
      <span
        className={cn(
          "min-w-0 truncate text-right font-semibold [font-variant-numeric:tabular-nums]",
          tone === "warning" ? "text-[var(--ui-color-warning)]" : "text-slate-950",
        )}
        title={value}
      >
        {value}
      </span>
    </div>
  );
}

function ReceiptDetailSurface({
  detail,
  focusToken,
  isLoading,
  isReceivable,
  lines,
  onBackToPending,
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
  onBackToPending: () => void;
  queryError: unknown;
  timezone: string;
  onReceivedQuantityChange: (shipmentLineId: string, quantityText: string) => void;
  onVarianceReasonChange: (shipmentLineId: string, varianceReason: string) => void;
  varianceLineCount: number;
}) {
  if (isLoading) {
    return (
      <OperationalStatus
        description="Consultando productos y cantidades enviadas."
        title="Cargando envio"
      />
    );
  }

  if (queryError) {
    return (
      <OperationalStatus
        description={toTransferReceiptErrorMessage(
          queryError,
          "Confirma que el envio siga pendiente y disponible para esta sucursal.",
        )}
        title="Envio no disponible"
      />
    );
  }

  if (!detail) {
    return (
      <div className="grid h-full min-h-0 place-items-center rounded-xl border border-dashed border-[var(--pos-shell-border)] bg-white px-4 py-6 text-center">
        <div className="grid max-w-md gap-1.5">
          <p className="text-base font-semibold text-slate-950">Selecciona un envio pendiente.</p>
          <p className="text-sm leading-6 text-slate-600">
            Elige el envio correcto para comenzar la recepcion.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="grid h-full min-h-0 grid-rows-[auto_minmax(0,1fr)] gap-3">
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-[var(--pos-shell-border)] bg-white px-3 py-2.5">
        <div className="min-w-0">
          <p className="pos-label-text">Detalle del envio</p>
          <h2 className="truncate text-base font-semibold text-slate-950">
            {detail.shipment_summary.folio}
          </h2>
          <p className="mt-0.5 truncate text-sm text-slate-600">
            {detail.shipment.source_branch_name} -&gt;{" "}
            {detail.shipment.destination_branch_name ?? EMPTY_VALUE_TEXT}
          </p>
        </div>
        <div className="flex shrink-0 items-center gap-2">
          <span className="pos-chip" data-tone={getTransferStatusTone(detail.shipment.status)}>
            {getTransferStatusLabel(detail.shipment.status)}
          </span>
          <Button
            className={cn("h-9 px-3", posOutlineButtonClass)}
            onClick={onBackToPending}
            type="button"
            variant="outline"
          >
            <ArrowLeftIcon className="h-4 w-4" />
            Volver a pendientes
          </Button>
        </div>
      </div>

      <div className="grid min-h-0 grid-rows-[auto_minmax(0,1fr)] overflow-hidden rounded-xl border border-[var(--pos-shell-border)] bg-white">
        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-[var(--pos-shell-border)] px-3 py-2">
          <div className="min-w-0">
            <h3 className="text-sm font-semibold text-slate-950">Productos enviados</h3>
            <p className="truncate text-xs text-slate-500">
              Enviado{" "}
              {formatCompactLocalDateTime(
                detail.shipment.committed_at_utc ?? detail.shipment.created_at_utc,
                timezone,
              )}
            </p>
          </div>
          <div className="flex items-center gap-2">
            {varianceLineCount > 0 ? (
              <span className="pos-chip" data-tone="warning">
                {varianceLineCount} con diferencia
              </span>
            ) : null}
            {!isReceivable ? (
              <span className="pos-chip" data-tone="warning">
                No disponible
              </span>
            ) : null}
          </div>
        </div>
        <ScrollPane className="h-full">
          <div className="min-w-[42rem]">
          <LineComparisonHeader />
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
        </ScrollPane>
      </div>
    </div>
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
      setLastReceivedTransfer(null);
      setSelectedHistoryTransferId(detail.shipment.id);
      setCommitErrorMessage(null);
      setIsConfirmDialogOpen(false);
      clearSelection();
      setCenterView("history");
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
  const pendingTransferColumns = useMemo<PosRecordColumn<PendingInboundTransferView>[]>(
    () => [
      {
        header: "Folio",
        key: "folio",
        renderCell: (shipment) => (
          <span className="font-semibold text-slate-950">{shipment.folio}</span>
        ),
        width: "18%",
      },
      {
        header: "Origen",
        key: "source",
        renderCell: (shipment) => (
          <span className="block truncate" title={shipment.source_branch_name}>
            {shipment.source_branch_name}
          </span>
        ),
        width: "25%",
      },
      {
        header: "Enviado",
        key: "sent",
        renderCell: (shipment) =>
          formatCompactLocalDateTime(
            shipment.committed_at_utc ?? shipment.created_at_utc,
            activeTimezone,
          ),
        width: "20%",
      },
      {
        align: "right",
        header: "Lineas",
        key: "lines",
        renderCell: (shipment) => shipment.line_count,
        width: "10%",
      },
      {
        align: "right",
        header: "Unidades",
        key: "units",
        renderCell: (shipment) =>
          formatQuantityFromMilliUnits(Number(shipment.expected_total_quantity) * 1000),
        width: "14%",
      },
      {
        align: "right",
        header: "Estado",
        key: "status",
        renderCell: () => (
          <span className="pos-chip" data-tone="pending">
            Pendiente
          </span>
        ),
        width: "13%",
      },
    ],
    [activeTimezone],
  );

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
              label: "Volver a pendientes",
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
    ) : (
      <ReceiptSummaryPanel
        centerView={centerView}
        commitBlockedReason={commitBlockedReason}
        commitErrorMessage={commitErrorMessage}
        detail={selectedDetail}
        differenceTotalText={differenceTotalText}
        expectedUnitsText={expectedUnitsText}
        isCommitPending={commitMutation.isPending}
        isNotesExpanded={isNotesExpanded}
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
              title={centerView === "history" ? "Historial de recepciones" : "Recibir envio"}
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
                  Volver a pendientes
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
          ) : selectedTransferId !== null ? (
            <ReceiptDetailSurface
              detail={selectedDetail}
              focusToken={selectedTransferId}
              isLoading={transferDetailQuery.isPending}
              isReceivable={selectedDetailReceivable}
              lines={receiptLines}
              onBackToPending={clearSelection}
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
              queryError={transferDetailQuery.error}
              timezone={activeTimezone}
              varianceLineCount={varianceLineCount}
            />
          ) : (
            <div className="grid h-full min-h-0 grid-rows-[auto_minmax(0,1fr)] gap-3">
              <div className="grid gap-3 rounded-xl border border-[var(--pos-shell-border)] bg-white px-3 py-2.5 xl:grid-cols-[minmax(18rem,24rem)_minmax(0,1fr)] xl:items-center">
                <div className="flex min-w-0 items-center gap-2">
                  <SearchField
                    ariaLabel="Escanear folio de envio"
                    className="min-w-0 flex-1"
                    inputClassName={cn("h-10 rounded-lg text-sm shadow-sm", posInputClass)}
                    inputRef={pendingScannerInputRef}
                    onChange={setPendingScannerText}
                    onKeyDown={(event) => {
                      if (event.key === "Enter" || event.key === "NumpadEnter") {
                        event.preventDefault();
                        handlePendingShipmentScanSubmit();
                      }
                    }}
                    placeholder="Escanear o escribir folio"
                    value={pendingScannerText}
                  />
                  <Button
                    className={cn("h-10 shrink-0 px-3", posOutlineButtonClass)}
                    disabled={pendingScannerText.trim().length === 0}
                    onClick={handlePendingShipmentScanSubmit}
                    type="button"
                    variant="outline"
                  >
                    Abrir
                  </Button>
                </div>
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

              <div className="min-h-0 overflow-hidden rounded-xl border border-[var(--pos-shell-border)] bg-white">
                <PosRecordTable
                  columns={pendingTransferColumns}
                  emptyDescription="No hay envios pendientes para los filtros actuales."
                  emptyTitle="Sin pendientes"
                  getKey={(shipment) => shipment.id}
                  onSelect={(shipment) => {
                    setSelectedTransferId(shipment.id);
                    setLastReceivedTransfer(null);
                    setCommitErrorMessage(null);
                  }}
                  records={filteredPendingTransfers}
                  selectedKey={selectedTransferId}
                  tableAriaLabel="Envios pendientes"
                />
              </div>
            </div>
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

