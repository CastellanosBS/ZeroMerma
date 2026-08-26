import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Navigate } from "@tanstack/react-router";
import {
  DialogBody,
  DialogFooter,
  DialogHeader,
  DialogSurface,
} from "@zeromerma/ui";
import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ButtonHTMLAttributes,
  type Ref,
} from "react";

import { useAppShellRightPanel } from "../../components/app-shell-right-panel";
import { CapturedProductLineList, CapturedProductLineRow } from "../../components/captured-product-lines";
import { CatalogSelectionCard } from "../../components/catalog-selection-card";
import {
  OperationHistoryList,
  type OperationHistoryRecord,
} from "../../components/operation-documents";
import { OperationalStatus } from "../../components/operational-status";
import { PosModuleLayout, PosSummaryPanel } from "../../components/pos-module-layout";
import { PosFilterBar, PosHistoryView } from "../../components/pos-records";
import {
  CentralWorkspaceSheet,
  CompactPageHeader,
  FlowGuide,
  InlineNotice,
  ModuleStateChip,
  RightPanelBlock,
  ScrollPane,
  SearchField,
} from "../../components/pos-module-primitives";
import {
  ArrowLeftIcon,
  ClipboardIcon,
  HashIcon,
  PackageIcon,
  StoreIcon,
  TruckIcon,
  XIcon,
} from "../../components/pos-icons";
import { Button } from "../../components/ui/button";
import type {
  OperationHistoryFilterOptionView,
  OperationHistoryScopeView,
  TransferDetailResponse,
  TransferDispatchCommitRequest,
  TransferDispatchHistoryResponse,
} from "../../lib/api-contracts";
import { formatCompactLocalDateTime } from "../../lib/formatters";
import {
  getSelectionShortcutIndex,
  getSelectionShortcutLabel,
  isEditableTarget,
} from "../../lib/keyboard-shortcuts";
import { toOperationalErrorMessage } from "../../lib/http";
import { cn } from "../../lib/utils";
import { usePosAuthStore } from "../auth/auth-store";
import { useCurrentCashSessionQuery } from "../cash-session-open/queries";
import {
  addPendingSelectionLine,
  buildOperationCommitLines,
  CONTROL_STATE_CLASS_SELECTION,
  CONTROL_STATE_PRODUCT_SELECTION,
  CONTROL_STATE_QUANTITY_CAPTURE,
  createInitialOperationDraftState,
  decrementPendingOperationQuantity,
  getOperationLineCount,
  getOperationPendingCaptureTargetKey,
  getOperationTotalUnitsMilli,
  goBackFromOperationalState,
  incrementPendingOperationQuantity,
  removeOperationLine,
  selectClassForOperation,
  selectProductForOperation,
  setPendingQuantityText,
  sortOperationalClasses,
  sortOperationalProducts,
  updateOperationLineQuantity,
  type OperationDraftState,
  type OperationLine,
} from "../operations/model";
import {
  useOperationsBootstrapQuery,
  useOperationsCatalogQuery,
  useOperationsClassProductsQuery,
} from "../operations/queries";
import { useRovingFocusGrid } from "../pos-shell/keyboard";
import {
  formatQuantityFromMilliUnits,
  hasCapturedQuantity,
  parseQuantityToMilliUnits,
  sanitizeQuantityInput,
} from "../pos-terminal/model";
import { posInputClass, posOutlineButtonClass, posPrimaryButtonClass } from "../pos-theme/theme";
import { useStatusMessageStore } from "../status-messages/store";
import {
  getTransferDispatchUiState,
  hasTransferDispatchDestination,
  type TransferDispatchUiState,
} from "./model";
import {
  useTransferDetailQuery,
  useTransferDispatchHistoryQuery,
} from "./queries";
import { commitTransferDispatch } from "./transfers-api";

const TRANSFER_DISPATCH_MODULE_KEY = "BRANCH_TRANSFER_SHIPMENT";
const EMPTY_DESTINATION_TEXT = String.fromCharCode(8212);

type TransferDispatchCenterView = "capture" | "history";

function useDebouncedValue(value: string, delayMs: number): string {
  const [debouncedValue, setDebouncedValue] = useState(value);

  useEffect(() => {
    const timeout = window.setTimeout(() => setDebouncedValue(value), delayMs);
    return () => window.clearTimeout(timeout);
  }, [delayMs, value]);

  return debouncedValue;
}

function formatLineCountLabel(lineCount: number): string {
  return `${lineCount} lineas`;
}

function getDispatchStatusLabel({
  hasDestination,
  uiState,
}: {
  hasDestination: boolean;
  uiState: TransferDispatchUiState;
}): string {
  if (!hasDestination) {
    return "Pendiente destino";
  }

  switch (uiState) {
    case "NO_LINES_YET":
      return "Sin productos";
    case "DOCUMENT_BUILDING":
      return "En captura";
    case "READY_TO_COMMIT":
      return "Listo para registrar";
    case "COMMITTING":
      return "Registrando";
    case "COMMITTED_SUCCESS":
      return "Registrado";
    default:
      return "Sin productos";
  }
}

function getDispatchStatusTone({
  hasDestination,
  uiState,
}: {
  hasDestination: boolean;
  uiState: TransferDispatchUiState;
}): "draft" | "pending" | "ready" | "success" | "warning" {
  if (!hasDestination) {
    return "warning";
  }

  switch (uiState) {
    case "DOCUMENT_BUILDING":
    case "COMMITTING":
      return "pending";
    case "READY_TO_COMMIT":
      return "ready";
    case "COMMITTED_SUCCESS":
      return "success";
    default:
      return "draft";
  }
}

function getDispatchStateChipTone({
  centerView,
  hasDestination,
  uiState,
}: {
  centerView: TransferDispatchCenterView;
  hasDestination: boolean;
  uiState: TransferDispatchUiState;
}): "info" | "muted" | "primary" | "success" | "warning" {
  if (centerView === "history") {
    return "info";
  }

  if (!hasDestination) {
    return "warning";
  }

  switch (uiState) {
    case "READY_TO_COMMIT":
    case "DOCUMENT_BUILDING":
    case "COMMITTING":
      return "primary";
    case "COMMITTED_SUCCESS":
      return "success";
    default:
      return "muted";
  }
}

function getDispatchCommitBlockedReason({
  controlState,
  hasDestination,
  lineCount,
}: {
  controlState: OperationDraftState["controlState"];
  hasDestination: boolean;
  lineCount: number;
}): string | null {
  if (!hasDestination) {
    return "Selecciona una sucursal destino.";
  }

  if (lineCount === 0) {
    return "Agrega al menos una linea.";
  }

  if (controlState !== CONTROL_STATE_CLASS_SELECTION) {
    return "Termina la captura actual antes de registrar.";
  }

  return null;
}

function getTransferDocumentStatusLabel(status: string): string {
  switch (status) {
    case "IN_TRANSIT":
      return "En transito";
    case "RECEIVED":
      return "Recibido";
    case "RECEIVED_WITH_VARIANCE":
      return "Recibido con diferencia";
    case "CANCELLED":
      return "Cancelado";
    default:
      return status;
  }
}

function getTransferDocumentStatusTone(status: string) {
  switch (status) {
    case "IN_TRANSIT":
      return "pending" as const;
    case "RECEIVED":
      return "success" as const;
    case "RECEIVED_WITH_VARIANCE":
      return "warning" as const;
    case "CANCELLED":
      return "error" as const;
    default:
      return "draft" as const;
  }
}

function getTransferDocumentStatusChipTone(status: string) {
  switch (status) {
    case "IN_TRANSIT":
      return "warning" as const;
    case "RECEIVED":
      return "success" as const;
    case "RECEIVED_WITH_VARIANCE":
      return "warning" as const;
    case "CANCELLED":
      return "danger" as const;
    default:
      return "muted" as const;
  }
}

function getRouteSuggestionLabel(
  originLabel: string,
  destinationLabel?: string | null,
): string {
  if (typeof destinationLabel === "string" && destinationLabel.trim().length > 0) {
    return `${originLabel} -> ${destinationLabel}`;
  }

  return "Ruta pendiente";
}

function toTransferDispatchErrorMessage(error: unknown): string {
  const fallbackMessage = "No se pudo registrar el envio. Intenta de nuevo.";
  const message = toOperationalErrorMessage(error, fallbackMessage);

  if (message === "Destination branch must differ from the current branch.") {
    return "Selecciona una sucursal destino distinta a la actual.";
  }

  if (message === "Destination branch was not found.") {
    return "La sucursal destino ya no esta disponible.";
  }

  if (message === "Transfer dispatch invariants were violated by a concurrent request.") {
    return "El envio cambio mientras lo registrabas. Revisa el borrador e intenta de nuevo.";
  }

  return message;
}

function buildTransferHistoryRecords(
  history: TransferDispatchHistoryResponse | undefined,
  timeZone: string,
): OperationHistoryRecord[] {
  return (history?.records ?? []).map(
    (record: TransferDispatchHistoryResponse["records"][number]) => ({
      documentTypeLabel: "Envio a sucursal",
      folio: record.folio,
      id: record.id,
      locationLabel: `${record.source_branch_name} / ${record.workstation_name}`,
      metrics: [
        {
          key: "line-count",
          label: "Lineas",
          value: String(record.line_count),
        },
        {
          key: "units",
          label: "Unidades",
          value: formatQuantityFromMilliUnits(Number(record.total_quantity) * 1000),
        },
      ],
      primaryTimestampLabel: "Confirmado",
      primaryTimestampValue: record.committed_at_utc
        ? formatCompactLocalDateTime(record.committed_at_utc, timeZone)
        : undefined,
      secondaryTimestampLabel: "Creado",
      secondaryTimestampValue: formatCompactLocalDateTime(record.created_at_utc, timeZone),
      statusLabel: getTransferDocumentStatusLabel(record.status),
      statusTone: getTransferDocumentStatusTone(record.status),
      subtitle: `${record.source_branch_name} -> ${record.destination_branch_name ?? "Destino"}`,
      title: record.destination_branch_name ?? "Sucursal destino",
      userLabel: record.created_by_user_full_name,
    }),
  );
}

function SelectionCard({
  buttonRef,
  code,
  isActive,
  isDisabled = false,
  isPrimaryControl,
  onCardFocus,
  onCardKeyDown,
  onSelect,
  shortcutLabel,
  tabIndex,
  title,
}: {
  buttonRef?: Ref<HTMLButtonElement>;
  code: string;
  isActive: boolean;
  isDisabled?: boolean;
  isPrimaryControl: boolean;
  onCardFocus?: ButtonHTMLAttributes<HTMLButtonElement>["onFocus"];
  onCardKeyDown?: ButtonHTMLAttributes<HTMLButtonElement>["onKeyDown"];
  onSelect: () => void;
  shortcutLabel: string | null;
  tabIndex?: number;
  title: string;
}) {
  return (
    <CatalogSelectionCard
      buttonRef={buttonRef}
      code={code}
      isActive={isActive}
      isDisabled={isDisabled}
      isPrimaryControl={isPrimaryControl}
      name={title}
      onCardFocus={onCardFocus}
      onCardKeyDown={onCardKeyDown}
      onSelect={onSelect}
      shortcutLabel={shortcutLabel}
      tabIndex={tabIndex}
      variant="pos"
    />
  );
}

function DispatchLineRow({
  disabled = false,
  line,
  onQuantityChange,
  onQuantityInvalid,
  onRemove,
}: {
  disabled?: boolean;
  line: OperationLine;
  onQuantityChange: (quantityMilliUnits: number) => void;
  onQuantityInvalid: (message: string) => void;
  onRemove: () => void;
}) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [isEditing, setIsEditing] = useState(false);
  const [quantityText, setQuantityText] = useState(line.quantityText);

  useEffect(() => {
    if (!isEditing) {
      setQuantityText(line.quantityText);
    }
  }, [isEditing, line.quantityText]);

  useEffect(() => {
    if (!isEditing) {
      return;
    }

    inputRef.current?.focus();
    inputRef.current?.select();
  }, [isEditing]);

  function commitQuantity(nextQuantityText = quantityText) {
    const normalizedQuantityText = sanitizeQuantityInput(nextQuantityText);
    const quantityMilliUnits = parseQuantityToMilliUnits(normalizedQuantityText);
    if (quantityMilliUnits === null || quantityMilliUnits <= 0) {
      setQuantityText(line.quantityText);
      setIsEditing(false);
      onQuantityInvalid("Captura una cantidad mayor que cero.");
      return;
    }

    setQuantityText(formatQuantityFromMilliUnits(quantityMilliUnits));
    setIsEditing(false);
    onQuantityChange(quantityMilliUnits);
  }

  function cancelQuantityEdit() {
    setQuantityText(line.quantityText);
    setIsEditing(false);
  }

  function adjustQuantity(deltaMilliUnits: number) {
    const currentQuantityMilliUnits = parseQuantityToMilliUnits(quantityText) ?? line.quantityMilliUnits;
    const nextQuantityMilliUnits = currentQuantityMilliUnits + deltaMilliUnits;
    if (nextQuantityMilliUnits <= 0) {
      onQuantityInvalid("La cantidad debe ser mayor que cero.");
      return;
    }

    commitQuantity(formatQuantityFromMilliUnits(nextQuantityMilliUnits));
  }

  return (
    <CapturedProductLineRow
      disabled={disabled}
      inputRef={isEditing ? inputRef : null}
      name={line.productName}
      onBeginQuantityEdit={() => setIsEditing(true)}
      onCancelQuantityEdit={cancelQuantityEdit}
      onCommitQuantity={() => commitQuantity()}
      onDecrement={() => adjustQuantity(-1000)}
      onIncrement={() => adjustQuantity(1000)}
      onQuantityChange={(value) => setQuantityText(sanitizeQuantityInput(value))}
      onRemove={() => {
        cancelQuantityEdit();
        onRemove();
      }}
      quantityMode={isEditing ? "input" : "display"}
      quantityText={isEditing ? quantityText : line.quantityText}
    />
  );
}

function getTransferShipmentTotalUnitsText(transfer: TransferDetailResponse["shipment"]): string {
  return formatQuantityFromMilliUnits(
    transfer.lines.reduce((total, line) => total + Number(line.quantity) * 1000, 0),
  );
}

function TransferDispatchSummaryPanel({
  commitBlockedReason,
  commitErrorMessage,
  destinationLabel,
  hasDestination,
  isCommitPending,
  isHistoryViewActive,
  isNotesExpanded,
  lines,
  notes,
  onCommit,
  onHistory,
  onLineQuantityInvalid,
  onNotesChange,
  onRemoveLine,
  onToggleNotes,
  onUpdateLineQuantity,
  originBranchLabel,
  routeLabel,
  uiState,
}: {
  commitBlockedReason: string | null;
  commitErrorMessage: string | null;
  destinationLabel: string;
  hasDestination: boolean;
  isCommitPending: boolean;
  isHistoryViewActive: boolean;
  isNotesExpanded: boolean;
  lines: OperationLine[];
  notes: string;
  onCommit: () => void;
  onHistory: () => void;
  onLineQuantityInvalid: (message: string) => void;
  onNotesChange: (value: string) => void;
  onRemoveLine: (lineKey: string) => void;
  onToggleNotes: () => void;
  onUpdateLineQuantity: (lineKey: string, quantityMilliUnits: number) => void;
  originBranchLabel: string;
  routeLabel: string;
  uiState: TransferDispatchUiState;
}) {
  const emptyStateMessage = hasDestination
    ? "Agrega al menos una linea."
    : "Selecciona una sucursal destino en el panel central.";

  return (
    <PosSummaryPanel
      stateLabel={getDispatchStatusLabel({ hasDestination, uiState })}
      stateTone={getDispatchStatusTone({ hasDestination, uiState })}
      title="Borrador de envio"
    >
      <div className="grid h-full min-h-0 grid-rows-[auto_minmax(0,1fr)_auto] gap-3">
        <div className="grid gap-2">
          {commitErrorMessage ? <InlineNotice tone="error">{commitErrorMessage}</InlineNotice> : null}
          <div className="grid gap-1.5 rounded-lg border border-[var(--pos-shell-border)] bg-[var(--pos-shell-muted)]/70 px-3 py-2 text-sm">
            <div className="flex items-center justify-between gap-3">
              <span className="font-medium text-slate-600">Origen</span>
              <span className="min-w-0 truncate text-right font-semibold text-slate-950" title={originBranchLabel}>
                {originBranchLabel}
              </span>
            </div>
            <div className="flex items-center justify-between gap-3">
              <span className="font-medium text-slate-600">Destino</span>
              <span
                className="min-w-0 truncate text-right font-semibold text-[var(--pos-primary)]"
                title={destinationLabel}
              >
                {destinationLabel}
              </span>
            </div>
            {hasDestination ? (
              <span className="sr-only" title={routeLabel}>
                {routeLabel}
              </span>
            ) : null}
          </div>

          {commitBlockedReason ? <InlineNotice tone="warning">{commitBlockedReason}</InlineNotice> : null}
        </div>

        <RightPanelBlock
          className="grid min-h-0 grid-rows-[auto_minmax(0,1fr)] overflow-hidden"
          contentClassName="h-full min-h-0 overflow-hidden"
          title="Productos"
          tone="muted"
        >
          {lines.length === 0 ? (
            <div className="rounded-lg border border-dashed border-[var(--pos-shell-border)] bg-white px-3 py-4 text-sm text-slate-600">
              {emptyStateMessage}
            </div>
          ) : (
            <ScrollPane className="h-full pr-1">
              <CapturedProductLineList className="grid content-start">
                {lines.map((line) => (
                  <DispatchLineRow
                    disabled={isCommitPending}
                    key={line.key}
                    line={line}
                    onQuantityChange={(quantityMilliUnits) =>
                      onUpdateLineQuantity(line.key, quantityMilliUnits)
                    }
                    onQuantityInvalid={onLineQuantityInvalid}
                    onRemove={() => onRemoveLine(line.key)}
                  />
                ))}
              </CapturedProductLineList>
            </ScrollPane>
          )}
        </RightPanelBlock>

        <div className="grid gap-2 border-t border-[var(--pos-shell-border)] pt-2">
          <div className="rounded-lg border border-[var(--pos-shell-border)] bg-white">
            <button
              aria-expanded={isNotesExpanded}
              className="flex w-full items-center justify-between gap-3 px-3 py-2 text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--pos-ring)]"
              disabled={isCommitPending}
              onClick={onToggleNotes}
              type="button"
            >
              <span className="truncate text-sm font-semibold text-slate-900">
                {notes.trim().length > 0 ? "Observacion agregada" : "Agregar observacion"}
              </span>
              <ArrowLeftIcon
                className={cn(
                  "h-4 w-4 rotate-180 text-slate-400 transition",
                  isNotesExpanded && "rotate-90",
                )}
              />
            </button>
            {isNotesExpanded ? (
              <div className="border-t border-[var(--pos-shell-border)] px-3 pb-3 pt-2">
                <textarea
                  className={cn("min-h-16 rounded-lg px-3 py-2 text-sm shadow-sm", posInputClass)}
                  disabled={isCommitPending}
                  onChange={(event) => onNotesChange(event.target.value)}
                  placeholder="Observacion opcional"
                  value={notes}
                />
              </div>
            ) : null}
          </div>
          <Button
            className={cn(
              "h-10",
              isHistoryViewActive
                ? "border-[var(--pos-primary)] bg-[var(--pos-primary-soft)] text-[var(--pos-primary)] shadow-sm hover:border-[var(--pos-primary)] hover:bg-[var(--pos-primary-soft)]"
                : posOutlineButtonClass,
            )}
            onClick={onHistory}
            type="button"
            variant="outline"
          >
            {isHistoryViewActive ? "Captura" : "Historial"}
          </Button>
          <Button
            className={cn("h-11", posPrimaryButtonClass)}
            disabled={commitBlockedReason !== null || isCommitPending}
            onClick={onCommit}
            type="button"
          >
            {isCommitPending ? "Registrando..." : "Confirmar envio"}
          </Button>
        </div>
      </div>
    </PosSummaryPanel>
  );
}

function TransferDispatchConfirmationDialog({
  destinationLabel,
  isOpen,
  isPending,
  lineCount,
  lines,
  onCancel,
  onConfirm,
  operatorLabel,
  originBranchLabel,
  routeLabel,
  stationLabel,
  totalUnitsText,
}: {
  destinationLabel: string;
  isOpen: boolean;
  isPending: boolean;
  lineCount: number;
  lines: OperationLine[];
  onCancel: () => void;
  onConfirm: () => void;
  operatorLabel: string;
  originBranchLabel: string;
  routeLabel: string;
  stationLabel: string;
  totalUnitsText: string;
}) {
  if (!isOpen) {
    return null;
  }

  const summaryItems = [
    { key: "origin", label: "Sucursal", value: originBranchLabel },
    { key: "station", label: "Estacion", value: stationLabel },
    { key: "operator", label: "Operador", value: operatorLabel },
    { key: "destination", label: "Destino", value: destinationLabel },
    { key: "lines", label: "Lineas", value: String(lineCount) },
    { key: "units", label: "Unidades", value: totalUnitsText },
  ];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/25 p-4">
      <DialogSurface className="w-full max-w-2xl">
        <DialogHeader>
          <div className="min-w-0">
            <p className="pos-label-text">Revision final</p>
            <h2 className="mt-1 text-lg font-semibold text-slate-950">
              Confirmar envio a sucursal
            </h2>
            <p className="mt-1 truncate text-sm font-medium text-slate-600" title={routeLabel}>
              {routeLabel}
            </p>
          </div>
          <span className="pos-chip" data-tone="warning">
            Confirmacion
          </span>
        </DialogHeader>

        <DialogBody className="grid gap-3">
          <div className="flex flex-wrap gap-2">
            {summaryItems.map((item) => (
              <span
                className="inline-flex max-w-full items-center gap-1.5 rounded-full border border-[var(--pos-shell-border)] bg-[var(--pos-shell-muted)] px-2.5 py-1 text-xs"
                key={item.key}
                title={`${item.label}: ${item.value}`}
              >
                <span className="font-medium text-slate-500">{item.label}</span>
                <span className="max-w-[11rem] truncate font-semibold text-slate-950">
                  {item.value}
                </span>
              </span>
            ))}
          </div>

          <div className="overflow-hidden rounded-lg border border-[var(--pos-shell-border)] bg-white">
            <table className="w-full table-fixed text-sm" aria-label="Productos del envio">
              <thead className="border-b border-[var(--pos-shell-border)] bg-[var(--pos-shell-muted)] text-[10px] font-semibold uppercase tracking-[0.08em] text-slate-500">
                <tr>
                  <th className="px-3 py-2 text-left">Producto</th>
                  <th className="w-24 px-3 py-2 text-right">Cantidad</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[var(--pos-shell-border)]">
                {lines.map((line) => (
                  <tr key={line.key}>
                    <td className="min-w-0 px-3 py-2">
                      <span className="block truncate font-medium text-slate-950" title={line.productName}>
                        {line.productName}
                      </span>
                    </td>
                    <td className="px-3 py-2 text-right font-semibold text-slate-950 [font-variant-numeric:tabular-nums]">
                      {line.quantityText}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </DialogBody>

        <DialogFooter>
          <Button
            className={posOutlineButtonClass}
            disabled={isPending}
            onClick={onCancel}
            type="button"
            variant="outline"
          >
            Cancelar
          </Button>
          <Button
            className={posPrimaryButtonClass}
            disabled={isPending}
            onClick={onConfirm}
            type="button"
          >
            {isPending ? "Confirmando..." : "Confirmar envio"}
          </Button>
        </DialogFooter>
      </DialogSurface>
    </div>
  );
}

function TransferDispatchHistoryDetailPanel({
  onBackToCapture,
  timeZone,
  transferDetail,
}: {
  onBackToCapture: () => void;
  timeZone: string;
  transferDetail: TransferDetailResponse;
}) {
  const shipment = transferDetail.shipment;
  const routeLabel = getRouteSuggestionLabel(
    shipment.source_branch_name,
    shipment.destination_branch_name,
  );
  const totalUnitsText = getTransferShipmentTotalUnitsText(shipment);

  return (
    <aside className="pos-shell-panel grid h-full min-h-0 grid-rows-[auto_minmax(0,1fr)_auto] gap-3 px-3.5 py-3">
      <div className="flex min-w-0 items-start justify-between gap-3">
        <div className="min-w-0">
          <h2 className="truncate text-[1.05rem] font-semibold tracking-tight text-slate-950">
            Envio seleccionado
          </h2>
          <p className="mt-1 truncate text-sm font-medium text-slate-600">
            {shipment.folio}
          </p>
        </div>
        <ModuleStateChip tone={getTransferDocumentStatusChipTone(shipment.status)}>
          {getTransferDocumentStatusLabel(shipment.status)}
        </ModuleStateChip>
      </div>

      <ScrollPane className="min-h-0">
        <div className="grid gap-3">
          <RightPanelBlock title="Movimiento">
            <div className="grid gap-2 text-sm">
              <TransferDetailRow label="Folio" value={shipment.folio} />
              <TransferDetailRow
                label="Fecha/hora"
                value={formatCompactLocalDateTime(
                  shipment.committed_at_utc ?? shipment.created_at_utc,
                  timeZone,
                )}
              />
              <TransferDetailRow label="Operador" value={shipment.created_by_user_full_name} />
              <TransferDetailRow label="Estacion" value={shipment.workstation_name} />
              <TransferDetailRow label="Origen" value={shipment.source_branch_name} />
              <TransferDetailRow
                label="Destino"
                value={shipment.destination_branch_name ?? EMPTY_DESTINATION_TEXT}
              />
              <TransferDetailRow label="Ruta" value={routeLabel} />
              <TransferDetailRow label="Lineas" value={String(shipment.lines.length)} />
              <TransferDetailRow label="Unidades" value={totalUnitsText} />
            </div>
          </RightPanelBlock>

          {transferDetail.receipt_summary ? (
            <InlineNotice
              tone={
                transferDetail.receipt_summary.status === "RECEIVED_WITH_VARIANCE"
                  ? "warning"
                  : "success"
              }
            >
              Recepcion vinculada: {transferDetail.receipt_summary.folio}.
            </InlineNotice>
          ) : null}

          <RightPanelBlock title="Productos">
            {shipment.lines.length === 0 ? (
              <div className="rounded-lg border border-dashed border-[var(--pos-shell-border)] bg-white px-3 py-3 text-sm text-slate-600">
                Sin lineas registradas.
              </div>
            ) : (
              <div className="overflow-hidden rounded-lg border border-[var(--pos-shell-border)] bg-white">
                {shipment.lines.map((line) => (
                  <div
                    className="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-3 border-t border-[var(--pos-shell-border)] px-3 py-2 first:border-t-0"
                    key={line.id}
                  >
                    <span
                      className="block min-w-0 truncate text-sm font-semibold text-slate-950"
                      title={line.product_name_snapshot}
                    >
                      {line.product_name_snapshot}
                    </span>
                    <span className="text-right text-sm font-semibold text-slate-950 [font-variant-numeric:tabular-nums]">
                      {formatQuantityFromMilliUnits(Number(line.quantity) * 1000)}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </RightPanelBlock>
        </div>
      </ScrollPane>

      <div className="grid gap-2">
        <Button
          className={cn("h-10 w-full", posOutlineButtonClass)}
          onClick={onBackToCapture}
          type="button"
          variant="outline"
        >
          <ArrowLeftIcon className="h-4 w-4" />
          Volver a captura
        </Button>
      </div>
    </aside>
  );
}

function TransferDetailRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between gap-3">
      <span className="font-medium text-slate-600">{label}</span>
      <span className="min-w-0 truncate text-right font-semibold text-slate-950" title={value}>
        {value}
      </span>
    </div>
  );
}

export function TransferDispatchScreen() {
  const queryClient = useQueryClient();
  const accessToken = usePosAuthStore((state) => state.accessToken);
  const showError = useStatusMessageStore((state) => state.showError);
  const showSuccess = useStatusMessageStore((state) => state.showSuccess);
  const quantityInputRef = useRef<HTMLInputElement>(null);
  const searchInputRef = useRef<HTMLInputElement>(null);
  const quantityFocusTargetRef = useRef<string | null>(null);
  const lastGridFocusKeyRef = useRef<string | null>(null);

  const [draftState, setDraftState] = useState(createInitialOperationDraftState());
  const [destinationBranchId, setDestinationBranchId] = useState("");
  const [notes, setNotes] = useState("");
  const [selectionErrorMessage, setSelectionErrorMessage] = useState<string | null>(null);
  const [commitErrorMessage, setCommitErrorMessage] = useState<string | null>(null);
  const [isNotesExpanded, setIsNotesExpanded] = useState(false);
  const [isConfirmDialogOpen, setIsConfirmDialogOpen] = useState(false);
  const [centerView, setCenterView] = useState<TransferDispatchCenterView>("capture");
  const [selectedHistoryTransferId, setSelectedHistoryTransferId] = useState<string | null>(null);
  const [historyScope, setHistoryScope] = useState("CURRENT_SHIFT");
  const [historyUserId, setHistoryUserId] = useState<string>("ALL");
  const [historyDestinationId, setHistoryDestinationId] = useState<string>("ALL");

  const operationsBootstrapQuery = useOperationsBootstrapQuery();
  const currentCashSessionQuery = useCurrentCashSessionQuery();
  const debouncedSearchText = useDebouncedValue(draftState.searchText, 180);

  const hasDestination = hasTransferDispatchDestination(destinationBranchId);
  const displayControlState =
    centerView === "history"
      ? CONTROL_STATE_CLASS_SELECTION
      : hasDestination
        ? draftState.controlState
        : CONTROL_STATE_CLASS_SELECTION;

  const catalogQuery = useOperationsCatalogQuery(
    TRANSFER_DISPATCH_MODULE_KEY,
    hasDestination && centerView === "capture" && displayControlState === CONTROL_STATE_CLASS_SELECTION
      ? debouncedSearchText
      : "",
  );
  const classProductsQuery = useOperationsClassProductsQuery(
    TRANSFER_DISPATCH_MODULE_KEY,
    hasDestination ? draftState.pendingSelection?.productClass.id ?? null : null,
    hasDestination && centerView === "capture" && displayControlState === CONTROL_STATE_PRODUCT_SELECTION
      ? debouncedSearchText
      : "",
  );

  const historyQuery = useTransferDispatchHistoryQuery(
    {
      createdByUserId: historyUserId !== "ALL" ? historyUserId : undefined,
      destinationBranchId:
        historyDestinationId !== "ALL" ? historyDestinationId : undefined,
      scope: historyScope,
    },
    centerView === "history",
  );
  const selectedHistoryTransferQuery = useTransferDetailQuery(
    centerView === "history" ? selectedHistoryTransferId : null,
  );

  const sortedClasses = useMemo(
    () => sortOperationalClasses(catalogQuery.data?.classes ?? []),
    [catalogQuery.data?.classes],
  );
  const sortedProducts = useMemo(
    () => sortOperationalProducts(classProductsQuery.data?.products ?? []),
    [classProductsQuery.data?.products],
  );

  const commitMutation = useMutation({
    mutationFn: async () => {
      if (accessToken === null || operationsBootstrapQuery.data === undefined) {
        throw new Error("Se requiere autenticacion y contexto de estacion.");
      }

      if (!hasTransferDispatchDestination(destinationBranchId)) {
        throw new Error("Selecciona una sucursal destino.");
      }

      const payload: TransferDispatchCommitRequest = {
        destination_branch_id: destinationBranchId,
        lines: buildOperationCommitLines(draftState.lines),
        notes: notes.trim().length > 0 ? notes.trim() : null,
        workstation_code: operationsBootstrapQuery.data.workstation.code,
      };

      return commitTransferDispatch(accessToken, payload);
    },
    onSuccess: (detail) => {
      setDraftState(createInitialOperationDraftState());
      setSelectionErrorMessage(null);
      setCommitErrorMessage(null);
      setNotes("");
      setIsNotesExpanded(false);
      setCenterView("history");
      setSelectedHistoryTransferId(detail.shipment.id);
      void queryClient.invalidateQueries({ queryKey: ["transfer-dispatch-history"] });
      showSuccess(`Envio registrado. Folio ${detail.shipment_summary.folio}.`);
    },
  });

  const classGridFocus = useRovingFocusGrid({
    itemCount: sortedClasses.length,
    onActivate: (index) => {
      const productClass = sortedClasses[index];
      if (!productClass || centerView === "history" || !hasDestination || commitMutation.isPending) {
        return;
      }

        setCommitErrorMessage(null);
      setDraftState((state) => selectClassForOperation(state, productClass));
    },
  });
  const productGridFocus = useRovingFocusGrid({
    itemCount: sortedProducts.length,
    onActivate: (index) => {
      const product = sortedProducts[index];
      if (!product || centerView === "history" || !hasDestination || commitMutation.isPending) {
        return;
      }

        setCommitErrorMessage(null);
      setDraftState((state) => selectProductForOperation(state, product));
    },
  });

  const {
    activeIndex: classActiveIndex,
    focusIndex: focusClassIndex,
    getItemProps: getClassItemProps,
  } = classGridFocus;
  const {
    activeIndex: productActiveIndex,
    focusIndex: focusProductIndex,
    getItemProps: getProductItemProps,
  } = productGridFocus;

  const selectedDestinationBranch =
    operationsBootstrapQuery.data?.destination_branches.find(
      (branch) => branch.id === destinationBranchId,
    ) ?? null;
  const destinationLabel = selectedDestinationBranch?.name ?? EMPTY_DESTINATION_TEXT;
  const originBranchLabel = operationsBootstrapQuery.data?.branch.name ?? "Sucursal actual";
  const routeSuggestionLabel = getRouteSuggestionLabel(
    originBranchLabel,
    selectedDestinationBranch?.name ?? null,
  );
  const lineCount = getOperationLineCount(draftState.lines);
  const totalUnitsText = formatQuantityFromMilliUnits(
    getOperationTotalUnitsMilli(draftState.lines),
  );
  const quantityCaptureTargetKey =
    centerView === "capture" && displayControlState === CONTROL_STATE_QUANTITY_CAPTURE
      ? getOperationPendingCaptureTargetKey(draftState.pendingSelection)
      : null;
  const isValidationReady =
    hasDestination &&
    lineCount > 0 &&
    draftState.controlState === CONTROL_STATE_CLASS_SELECTION;
  const commitBlockedReason = getDispatchCommitBlockedReason({
    controlState: draftState.controlState,
    hasDestination,
    lineCount,
  });
  const uiState = getTransferDispatchUiState({
    hasCommittedTransfer: false,
    hasDestination,
    isCaptureInProgress: draftState.controlState !== CONTROL_STATE_CLASS_SELECTION,
    isCommitPending: commitMutation.isPending,
    isValidationReady,
    lineCount,
  });
  const showSearch =
    centerView === "capture" &&
    displayControlState !== CONTROL_STATE_QUANTITY_CAPTURE;
  const isSelectionLoading =
    centerView === "capture" &&
    ((displayControlState === CONTROL_STATE_CLASS_SELECTION && catalogQuery.isPending) ||
      (displayControlState === CONTROL_STATE_PRODUCT_SELECTION && classProductsQuery.isPending));
  const selectionQueryError =
    displayControlState === CONTROL_STATE_PRODUCT_SELECTION
      ? classProductsQuery.error
      : catalogQuery.error;
  const quantitySelection =
    centerView === "capture" &&
    displayControlState === CONTROL_STATE_QUANTITY_CAPTURE &&
    draftState.pendingSelection !== null
      ? draftState.pendingSelection
      : null;
  const quantityProduct = quantitySelection?.product ?? null;
  const isQuantityReady =
    quantitySelection !== null && hasCapturedQuantity(quantitySelection.quantityText);
  const historyRecords = useMemo(
    () =>
      buildTransferHistoryRecords(
        historyQuery.data,
        operationsBootstrapQuery.data?.branch.timezone ?? "America/Hermosillo",
      ),
    [historyQuery.data, operationsBootstrapQuery.data?.branch.timezone],
  );
  const selectedHistoryTransfer = selectedHistoryTransferQuery.data ?? null;
  const isSelectedHistoryTransferPending =
    centerView === "history" &&
    selectedHistoryTransferId !== null &&
    selectedHistoryTransfer === null &&
    selectedHistoryTransferQuery.error === null &&
    selectedHistoryTransferQuery.isPending;

  useEffect(() => {
    setSelectionErrorMessage(null);
  }, [displayControlState, hasDestination, quantityCaptureTargetKey]);

  useEffect(() => {
    setCommitErrorMessage(null);
  }, [destinationBranchId, draftState.lines, notes]);

  useEffect(() => {
    if (!quantityCaptureTargetKey) {
      quantityFocusTargetRef.current = null;
      return;
    }

    if (quantityFocusTargetRef.current === quantityCaptureTargetKey) {
      return;
    }

    quantityFocusTargetRef.current = quantityCaptureTargetKey;
    quantityInputRef.current?.focus();
    quantityInputRef.current?.select();
  }, [quantityCaptureTargetKey]);

  const activeGridKey = useMemo(() => {
    if (centerView !== "capture" || !hasDestination) {
      return null;
    }

    if (displayControlState === CONTROL_STATE_CLASS_SELECTION) {
      return "classes";
    }

    if (displayControlState === CONTROL_STATE_PRODUCT_SELECTION) {
      return "products";
    }

    return null;
  }, [centerView, displayControlState, hasDestination]);

  useEffect(() => {
    if (activeGridKey === null) {
      lastGridFocusKeyRef.current = null;
      return;
    }

    if (lastGridFocusKeyRef.current === activeGridKey) {
      return;
    }

    if (displayControlState === CONTROL_STATE_CLASS_SELECTION && sortedClasses.length > 0) {
      lastGridFocusKeyRef.current = activeGridKey;
      focusClassIndex(0);
      return;
    }

    if (displayControlState === CONTROL_STATE_PRODUCT_SELECTION && sortedProducts.length > 0) {
      lastGridFocusKeyRef.current = activeGridKey;
      focusProductIndex(0);
    }
  }, [
    activeGridKey,
    displayControlState,
    focusClassIndex,
    focusProductIndex,
    sortedClasses.length,
    sortedProducts.length,
  ]);

  useEffect(() => {
    if (centerView !== "history" || selectedHistoryTransferId !== null) {
      return;
    }

    const firstRecord = historyQuery.data?.records[0];
    if (firstRecord) {
      setSelectedHistoryTransferId(firstRecord.id);
    }
  }, [centerView, historyQuery.data?.records, selectedHistoryTransferId]);

  useEffect(() => {
    function handleKeyboard(event: KeyboardEvent) {
      if (!isEditableTarget(event.target)) {
        if ((event.ctrlKey && event.key.toLowerCase() === "f") || event.key === "/") {
          if (showSearch && !commitMutation.isPending) {
            event.preventDefault();
            searchInputRef.current?.focus();
            searchInputRef.current?.select();
          }
          return;
        }
      }

      if (event.key === "Escape") {
        if (isConfirmDialogOpen) {
          event.preventDefault();
          setIsConfirmDialogOpen(false);
          return;
        }

        if (centerView === "history") {
          event.preventDefault();
          setCenterView("capture");
          return;
        }

        if (
          !commitMutation.isPending &&
          (displayControlState === CONTROL_STATE_PRODUCT_SELECTION ||
            displayControlState === CONTROL_STATE_QUANTITY_CAPTURE)
        ) {
          event.preventDefault();
          setDraftState((state) => goBackFromOperationalState(state));
          return;
        }

        if (!commitMutation.isPending && draftState.searchText.trim().length > 0) {
          event.preventDefault();
          setDraftState((state) => ({
            ...state,
            searchText: "",
          }));
        }

        return;
      }

      if (
        isEditableTarget(event.target) ||
        !hasDestination ||
        commitMutation.isPending ||
        centerView === "history"
      ) {
        return;
      }

      if (
        event.target instanceof Element &&
        event.target.closest("[data-transfer-destination-selector='true']")
      ) {
        return;
      }

      const shortcutIndex = getSelectionShortcutIndex(event.key);
      if (shortcutIndex === null) {
        return;
      }

      if (displayControlState === CONTROL_STATE_CLASS_SELECTION) {
        const productClass = sortedClasses[shortcutIndex];
        if (productClass) {
          event.preventDefault();
          setDraftState((state) => selectClassForOperation(state, productClass));
        }
        return;
      }

      if (displayControlState === CONTROL_STATE_PRODUCT_SELECTION) {
        const product = sortedProducts[shortcutIndex];
        if (product) {
          event.preventDefault();
          setDraftState((state) => selectProductForOperation(state, product));
        }
      }
    }

    window.addEventListener("keydown", handleKeyboard);
    return () => window.removeEventListener("keydown", handleKeyboard);
  }, [
    centerView,
    commitMutation.isPending,
    displayControlState,
    draftState.searchText,
    hasDestination,
    isConfirmDialogOpen,
    showSearch,
    sortedClasses,
    sortedProducts,
  ]);

  const handleDestinationChange = useCallback((nextBranchId: string) => {
    setDestinationBranchId(nextBranchId);
    setCommitErrorMessage(null);
    setSelectionErrorMessage(null);
    setDraftState((state) => ({
      ...state,
      controlState: CONTROL_STATE_CLASS_SELECTION,
      pendingSelection: null,
      searchText: "",
    }));
  }, []);

  const handleAddLine = useCallback(() => {
    if (!hasDestination) {
      setSelectionErrorMessage("Selecciona una sucursal destino para comenzar.");
      return;
    }

    try {
      setDraftState((state) => addPendingSelectionLine(state));
      setCommitErrorMessage(null);
      setSelectionErrorMessage(null);
    } catch (error) {
      setSelectionErrorMessage(
        toOperationalErrorMessage(
          error,
          "Confirma el producto exacto y la cantidad antes de agregar la linea.",
        ),
      );
    }
  }, [hasDestination]);

  const handleConfirmCommit = useCallback(async () => {
    if (commitBlockedReason !== null) {
      return;
    }

    setIsConfirmDialogOpen(false);
    commitMutation.reset();

    try {
      await commitMutation.mutateAsync();
    } catch (error) {
      const message = toTransferDispatchErrorMessage(error);
      setCommitErrorMessage(message);
      showError(message);
    }
  }, [commitBlockedReason, commitMutation, showError]);

  const openHistoryView = useCallback(() => {
    setCenterView((current) => (current === "history" ? "capture" : "history"));
  }, []);

  const summaryPanel = useMemo(() => {
    if (centerView === "history") {
      if (selectedHistoryTransferQuery.error) {
        return (
          <PosSummaryPanel
            description="No fue posible consultar el envio seleccionado."
            stateLabel="Error"
            stateTone="error"
            title="Historial de envios"
          >
            <div className="grid h-full place-items-center px-3 text-center">
              <p className="text-sm leading-6 text-slate-600">
                Reintenta desde el listado para recuperar el detalle operativo.
              </p>
            </div>
          </PosSummaryPanel>
        );
      }

      if (selectedHistoryTransfer !== null) {
        return (
          <TransferDispatchHistoryDetailPanel
            onBackToCapture={() => setCenterView("capture")}
            timeZone={operationsBootstrapQuery.data?.branch.timezone ?? "America/Hermosillo"}
            transferDetail={selectedHistoryTransfer}
          />
        );
      }

      return (
        <PosSummaryPanel
          description="Selecciona un envio del historial para revisar su folio y trazabilidad."
          footer={
            <Button
              className={cn("h-10 w-full", posOutlineButtonClass)}
              onClick={() => setCenterView("capture")}
              type="button"
              variant="outline"
            >
              Volver a captura
            </Button>
          }
          stateLabel={historyQuery.isPending || isSelectedHistoryTransferPending ? "Consultando" : "Sin seleccion"}
          stateTone={historyQuery.isPending || isSelectedHistoryTransferPending ? "pending" : "draft"}
          title="Historial de envios"
        >
          <div className="flex h-full items-center justify-center px-3 text-center">
            <p className="text-sm leading-6 text-slate-600">
              Elige un envio del historial para ver destino, lineas y estado logistico.
            </p>
          </div>
        </PosSummaryPanel>
      );
    }

    return (
      <TransferDispatchSummaryPanel
        commitBlockedReason={commitBlockedReason}
        commitErrorMessage={commitErrorMessage}
        destinationLabel={destinationLabel}
        hasDestination={hasDestination}
        isCommitPending={commitMutation.isPending}
        isHistoryViewActive={false}
        isNotesExpanded={isNotesExpanded}
        lines={draftState.lines}
        notes={notes}
        onCommit={() => {
          if (commitBlockedReason === null && !commitMutation.isPending) {
            setIsConfirmDialogOpen(true);
          }
        }}
        onHistory={openHistoryView}
        onLineQuantityInvalid={(message) => setCommitErrorMessage(message)}
        onNotesChange={(value) => {
          setNotes(value);
          if (value.trim().length > 0) {
            setIsNotesExpanded(true);
          }
        }}
        onRemoveLine={(lineKey) => {
          setDraftState((state) => ({
            ...state,
            lines: removeOperationLine(state.lines, lineKey),
          }));
        }}
        onToggleNotes={() => setIsNotesExpanded((current) => !current)}
        onUpdateLineQuantity={(lineKey, quantityMilliUnits) => {
          setCommitErrorMessage(null);
          setDraftState((state) => ({
            ...state,
            lines: state.lines.map((line) =>
              line.key === lineKey ? updateOperationLineQuantity(line, quantityMilliUnits) : line,
            ),
          }));
        }}
        originBranchLabel={originBranchLabel}
        routeLabel={routeSuggestionLabel}
        uiState={uiState}
      />
    );
  }, [
    centerView,
    commitBlockedReason,
    commitErrorMessage,
    commitMutation.isPending,
    destinationLabel,
    draftState.lines,
    hasDestination,
    historyQuery.isPending,
    isNotesExpanded,
    notes,
    openHistoryView,
    operationsBootstrapQuery.data?.branch.timezone,
    originBranchLabel,
    routeSuggestionLabel,
    selectedHistoryTransfer,
    selectedHistoryTransferQuery.error,
    isSelectedHistoryTransferPending,
    uiState,
  ]);
  useAppShellRightPanel(summaryPanel);

  if (operationsBootstrapQuery.isPending || currentCashSessionQuery.isPending) {
    return (
      <OperationalStatus
        description="Consultando el contexto operativo del envio."
        title="Cargando envio a sucursal"
      />
    );
  }

  if (operationsBootstrapQuery.error) {
    return (
      <OperationalStatus
        action={<Button onClick={() => operationsBootstrapQuery.refetch()}>Reintentar</Button>}
        description={toOperationalErrorMessage(
          operationsBootstrapQuery.error,
          "Confirma la configuracion de la estacion y el catalogo operativo.",
        )}
        title="Enviar a sucursal no esta disponible"
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

  const flowActiveStepKey =
    centerView === "history"
      ? "summary"
      : !hasDestination
        ? "destination"
        : displayControlState === CONTROL_STATE_PRODUCT_SELECTION
          ? "product"
          : displayControlState === CONTROL_STATE_QUANTITY_CAPTURE
            ? "quantity"
            : lineCount > 0
              ? "summary"
              : "class";

  const pageHeader = (
    <CompactPageHeader
      secondaryChips={
        <ModuleStateChip
          tone={
            centerView === "history"
              ? "info"
              : hasDestination
                ? "primary"
                : "muted"
          }
        >
          {centerView === "history" ? "Historial de envios" : routeSuggestionLabel}
        </ModuleStateChip>
      }
      stateChip={
        <ModuleStateChip
          tone={getDispatchStateChipTone({
            centerView,
            hasDestination,
            uiState,
          })}
        >
          {centerView === "history" ? "Consulta" : getDispatchStatusLabel({ hasDestination, uiState })}
        </ModuleStateChip>
      }
      title={centerView === "history" ? "Historial de envios" : "Enviar a sucursal"}
    >
      {centerView === "capture" ? (
        <FlowGuide
          activeStepKey={flowActiveStepKey}
          steps={[
            {
              icon: <TruckIcon className="h-3.5 w-3.5" />,
              key: "destination",
              label: "Destino",
            },
            {
              icon: <StoreIcon className="h-3.5 w-3.5" />,
              key: "class",
              label: "Clase",
            },
            {
              icon: <PackageIcon className="h-3.5 w-3.5" />,
              key: "product",
              label: "Producto",
            },
            {
              icon: <HashIcon className="h-3.5 w-3.5" />,
              key: "quantity",
              label: "Cantidad",
            },
            {
              icon: <ClipboardIcon className="h-3.5 w-3.5" />,
              key: "summary",
              label: "Revisar",
            },
          ]}
          variant="process"
        />
      ) : null}
    </CompactPageHeader>
  );

  const stageToolbar =
    centerView === "capture" &&
    (displayControlState !== CONTROL_STATE_CLASS_SELECTION || showSearch) ? (
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex min-w-0 items-start gap-3">
          {displayControlState !== CONTROL_STATE_CLASS_SELECTION ? (
            <Button
              aria-label="Regresar"
              className={cn("h-10 px-3", posOutlineButtonClass)}
              disabled={commitMutation.isPending}
              onClick={() => setDraftState((state) => goBackFromOperationalState(state))}
              title="Regresar"
              type="button"
              variant="outline"
            >
              <ArrowLeftIcon className="h-4 w-4" />
            </Button>
          ) : null}
        </div>

        {showSearch ? (
          <SearchField
            ariaLabel="Buscar catalogo para envio"
            className="w-full max-w-sm"
            disabled={!hasDestination || commitMutation.isPending}
            inputClassName={cn("h-9 rounded-lg text-sm shadow-sm", posInputClass)}
            inputRef={searchInputRef}
            onChange={(value) => {
              setDraftState((state) => ({
                ...state,
                searchText: value,
              }));
            }}
            placeholder={
              displayControlState === CONTROL_STATE_PRODUCT_SELECTION
                ? "Filtrar producto"
                : "Filtrar clase"
            }
            value={draftState.searchText}
          />
        ) : null}
      </div>
    ) : undefined;

  return (
    <>
      <TransferDispatchConfirmationDialog
        destinationLabel={destinationLabel}
        isOpen={isConfirmDialogOpen}
        isPending={commitMutation.isPending}
        lineCount={lineCount}
        lines={draftState.lines}
        onCancel={() => setIsConfirmDialogOpen(false)}
        onConfirm={() => {
          void handleConfirmCommit();
        }}
        operatorLabel={operationsBootstrapQuery.data.user.full_name}
        originBranchLabel={operationsBootstrapQuery.data.branch.name}
        routeLabel={routeSuggestionLabel}
        stationLabel={operationsBootstrapQuery.data.workstation.name}
        totalUnitsText={totalUnitsText}
      />

      <PosModuleLayout
        mobileSummary={
          <section className="rounded-xl border border-[var(--pos-shell-border)] bg-[var(--pos-shell-surface)] px-4 py-3 shadow-sm">
            <div className="flex items-center justify-between gap-3">
              <div>
                <p className="text-sm font-medium text-slate-900">Borrador de envio</p>
                <p className="text-sm text-slate-600">
                  {lineCount === 0
                    ? "Selecciona destino y agrega productos exactos para comenzar."
                    : `${totalUnitsText} unidades listas para registrar.`}
                </p>
              </div>
              <span className="pos-chip" data-tone="primary">
                {formatLineCountLabel(lineCount)}
              </span>
            </div>
          </section>
        }
      >
        <CentralWorkspaceSheet
          className="lg:h-full"
          contentClassName="min-h-0 overflow-y-auto px-3 pb-3 pt-2"
          header={pageHeader}
          toolbar={stageToolbar}
          toolbarClassName="py-2"
        >
          {centerView === "history" ? (
            <PosHistoryView
              description="Consulta los envios confirmados para esta estacion y filtra por turno, operador o destino."
              title="Historial de envios"
              toolbar={
                <PosFilterBar
                  chipFilters={(
                    historyQuery.data?.available_scopes ?? [
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
                      {historyQuery.data?.records.length ?? 0} registros
                    </span>
                  }
                  selectFilters={[
                    {
                      ariaLabel: "Filtrar historial por operador",
                      key: "history-user",
                      onChange: setHistoryUserId,
                      options: [
                        { label: "Todos los operadores", value: "ALL" },
                        ...(historyQuery.data?.available_users ?? []).map(
                          (option: OperationHistoryFilterOptionView) => ({
                            label: option.label,
                            value: option.value,
                          }),
                        ),
                      ],
                      value: historyUserId,
                    },
                    {
                      ariaLabel: "Filtrar historial por destino",
                      key: "history-destination",
                      onChange: setHistoryDestinationId,
                      options: [
                        { label: "Todos los destinos", value: "ALL" },
                        ...(historyQuery.data?.available_destination_branches ?? []).map(
                          (option: OperationHistoryFilterOptionView) => ({
                            label: option.label,
                            value: option.value,
                          }),
                        ),
                      ],
                      value: historyDestinationId,
                    },
                  ]}
                  title="Envios confirmados"
                />
              }
            >
              {historyQuery.error ? (
                <OperationalStatus
                  action={
                    <Button
                      className={posPrimaryButtonClass}
                      onClick={() => void historyQuery.refetch()}
                    >
                      Reintentar
                    </Button>
                  }
                  description={toOperationalErrorMessage(
                    historyQuery.error,
                    "No fue posible consultar el historial de envios.",
                  )}
                  title="El historial no esta disponible"
                />
              ) : (
                <OperationHistoryList
                  emptyDescription="Aun no hay envios confirmados para los filtros seleccionados."
                  loading={historyQuery.isPending}
                  onSelect={(record) => setSelectedHistoryTransferId(record.id)}
                  records={historyRecords}
                  selectedRecordId={selectedHistoryTransferId}
                />
              )}
            </PosHistoryView>
          ) : (
            <>
              <div
                className="grid gap-2 rounded-xl border border-[var(--pos-shell-border)] bg-white px-3 py-2.5 lg:grid-cols-[auto_minmax(14rem,20rem)_minmax(0,1fr)] lg:items-center"
                data-transfer-destination-selector="true"
              >
                <label
                  className="pos-label-text whitespace-nowrap"
                  htmlFor="transfer-destination-branch"
                >
                  Sucursal destino
                </label>
                <select
                  className={cn("h-10 rounded-lg px-3 text-sm shadow-sm", posInputClass)}
                  disabled={commitMutation.isPending}
                  id="transfer-destination-branch"
                  onChange={(event) => handleDestinationChange(event.target.value)}
                  value={destinationBranchId}
                >
                  <option value="">Seleccionar destino</option>
                  {(operationsBootstrapQuery.data?.destination_branches ?? []).map((branch) => (
                    <option key={branch.id} value={branch.id}>
                      {branch.name}
                    </option>
                  ))}
                </select>
                <div className="min-w-0">
                  <p
                    className={cn(
                      "truncate text-sm font-semibold",
                      hasDestination ? "text-slate-950" : "text-slate-500",
                    )}
                    title={routeSuggestionLabel}
                  >
                    {hasDestination ? routeSuggestionLabel : "Selecciona destino para capturar productos"}
                  </p>
                </div>
              </div>

              {isSelectionLoading ? (
                <OperationalStatus
                  description="Cargando el catalogo operativo actual."
                  title="Cargando seleccion"
                />
              ) : null}

              {!isSelectionLoading && selectionQueryError ? (
                <OperationalStatus
                  action={
                    <Button
                      className={posPrimaryButtonClass}
                      onClick={() =>
                        displayControlState === CONTROL_STATE_PRODUCT_SELECTION
                          ? classProductsQuery.refetch()
                          : catalogQuery.refetch()
                      }
                    >
                      Reintentar
                    </Button>
                  }
                  description={toOperationalErrorMessage(
                    selectionQueryError,
                    "Confirma el contexto de la estacion y la disponibilidad del catalogo operativo.",
                  )}
                  title="La seleccion no esta disponible"
                />
              ) : null}

              {!isSelectionLoading &&
              !selectionQueryError &&
              displayControlState === CONTROL_STATE_CLASS_SELECTION ? (
                <div className="mt-3 grid gap-2.5">
                  <div className="relative min-h-[14rem]">
                    <div
                      className={cn(
                        "grid gap-3 sm:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4",
                        (!hasDestination || commitMutation.isPending) &&
                          "pointer-events-none select-none opacity-55",
                      )}
                    >
                      {sortedClasses.length > 0 ? (
                        sortedClasses.map((productClass, index) => {
                          const itemProps = getClassItemProps(index);

                          return (
                            <SelectionCard
                              buttonRef={itemProps.ref}
                              code={productClass.code}
                              isActive={classActiveIndex === index}
                              isDisabled={!hasDestination || commitMutation.isPending}
                              isPrimaryControl={index === 0}
                              key={productClass.id}
                              onCardFocus={itemProps.onFocus}
                              onCardKeyDown={itemProps.onKeyDown}
                              onSelect={() => {
                                setDraftState((state) =>
                                  selectClassForOperation(state, productClass),
                                );
                              }}
                              shortcutLabel={getSelectionShortcutLabel(index)}
                              tabIndex={itemProps.tabIndex}
                              title={productClass.name}
                            />
                          );
                        })
                      ) : (
                        <div className="rounded-xl border border-dashed border-[var(--pos-shell-border)] bg-[var(--pos-shell-muted)] px-4 py-8 text-sm text-slate-600 sm:col-span-2 xl:col-span-3 2xl:col-span-4">
                          No hay clases para la busqueda actual.
                        </div>
                      )}
                    </div>

                    {!hasDestination ? (
                      <div className="absolute inset-0 z-10 flex items-center justify-center rounded-xl border border-dashed border-[var(--pos-shell-border)] bg-white/78 px-6 text-center shadow-sm backdrop-blur-[1px]">
                        <p className="max-w-sm text-sm font-medium leading-6 text-slate-700">
                          Selecciona una sucursal destino para comenzar.
                        </p>
                      </div>
                    ) : null}
                  </div>
                </div>
              ) : null}

              {!isSelectionLoading &&
              !selectionQueryError &&
              displayControlState === CONTROL_STATE_PRODUCT_SELECTION ? (
                <div className="mt-3 grid gap-2.5">
                  <div className="relative min-h-[14rem]">
                    <div
                      className={cn(
                        "grid gap-3 sm:grid-cols-2 xl:grid-cols-3",
                        (!hasDestination || commitMutation.isPending) &&
                          "pointer-events-none select-none opacity-55",
                      )}
                    >
                      {sortedProducts.length > 0 ? (
                        sortedProducts.map((product, index) => {
                          const itemProps = getProductItemProps(index);

                          return (
                            <SelectionCard
                              buttonRef={itemProps.ref}
                              code={product.code}
                              isActive={productActiveIndex === index}
                              isDisabled={!hasDestination || commitMutation.isPending}
                              isPrimaryControl={index === 0}
                              key={product.id}
                              onCardFocus={itemProps.onFocus}
                              onCardKeyDown={itemProps.onKeyDown}
                              onSelect={() => {
                                setDraftState((state) =>
                                  selectProductForOperation(state, product),
                                );
                              }}
                              shortcutLabel={getSelectionShortcutLabel(index)}
                              tabIndex={itemProps.tabIndex}
                              title={product.name}
                            />
                          );
                        })
                      ) : (
                        <div className="rounded-xl border border-dashed border-[var(--pos-shell-border)] bg-[var(--pos-shell-muted)] px-4 py-8 text-sm text-slate-600 sm:col-span-2 xl:col-span-3">
                          No hay productos para esta busqueda.
                        </div>
                      )}
                    </div>

                    {!hasDestination ? (
                      <div className="absolute inset-0 z-10 flex items-center justify-center rounded-xl border border-dashed border-[var(--pos-shell-border)] bg-white/78 px-6 text-center shadow-sm backdrop-blur-[1px]">
                        <p className="max-w-sm text-sm font-medium leading-6 text-slate-700">
                          Selecciona una sucursal destino para comenzar.
                        </p>
                      </div>
                    ) : null}
                  </div>
                </div>
              ) : null}

              {quantitySelection !== null && quantityProduct !== null ? (
                <div className="mt-3 w-full max-w-3xl justify-self-center rounded-xl border border-[var(--pos-shell-border)] bg-white p-3.5 shadow-sm">
                  <div className="grid gap-3">
                      <div className="flex flex-wrap items-start justify-between gap-3">
                        <div className="min-w-0">
                          <div className="flex flex-wrap items-center gap-2">
                            <p className="truncate text-base font-semibold text-slate-950">
                              {quantityProduct.name}
                            </p>
                            {!isQuantityReady ? (
                              <span className="pos-chip" data-tone="warning">
                                Pendiente
                              </span>
                            ) : null}
                          </div>
                          <p className="mt-1 truncate text-sm text-slate-600">
                            {quantitySelection.productClass.name}
                          </p>
                        </div>

                        <Button
                          aria-label="Regresar"
                          className={cn("h-10 px-3", posOutlineButtonClass)}
                          disabled={commitMutation.isPending}
                          onClick={() => setDraftState((state) => goBackFromOperationalState(state))}
                          title="Regresar"
                          type="button"
                          variant="outline"
                        >
                          <ArrowLeftIcon className="h-4 w-4" />
                        </Button>
                      </div>

                      <div className="grid gap-3 justify-items-center">
                        <input
                          aria-label="Cantidad"
                          className={cn(
                            "h-16 w-full max-w-[12rem] rounded-xl px-4 text-center text-[2.25rem] font-semibold tracking-tight shadow-sm",
                            posInputClass,
                          )}
                          inputMode="decimal"
                          onChange={(event) =>
                            setDraftState((state) =>
                              setPendingQuantityText(state, event.target.value),
                            )
                          }
                          onKeyDown={(event) => {
                            if (event.key === "Enter" || event.key === "NumpadEnter") {
                              event.preventDefault();
                              handleAddLine();
                            }

                            if (event.key === "Escape") {
                              event.preventDefault();
                              setDraftState((state) => goBackFromOperationalState(state));
                            }
                          }}
                          placeholder="0"
                          ref={quantityInputRef}
                          value={quantitySelection.quantityText}
                        />

                        <div className="flex flex-wrap items-center justify-center gap-2">
                          <Button
                            className={cn("h-10 px-3", posOutlineButtonClass)}
                            disabled={commitMutation.isPending}
                            onClick={() =>
                              setDraftState((state) => decrementPendingOperationQuantity(state))
                            }
                            type="button"
                            variant="outline"
                          >
                            -1
                          </Button>
                          <Button
                            className={cn("h-10 px-3", posOutlineButtonClass)}
                            disabled={commitMutation.isPending}
                            onClick={() =>
                              setDraftState((state) => incrementPendingOperationQuantity(state))
                            }
                            type="button"
                            variant="outline"
                          >
                            +1
                          </Button>
                          <span className="pos-kbd-chip">Enter Agrega</span>
                          <span className="pos-kbd-chip">Esc Regresa</span>
                        </div>

                        <div className="flex w-full flex-wrap items-center justify-end gap-3">
                          <Button
                            className={cn("h-10 px-5", posPrimaryButtonClass)}
                            disabled={!hasDestination || !isQuantityReady || commitMutation.isPending}
                            onClick={handleAddLine}
                            type="button"
                          >
                            Agregar linea
                          </Button>
                        </div>

                        {selectionErrorMessage ? (
                          <InlineNotice
                            action={
                              <button
                                aria-label="Cerrar error"
                                className="flex h-8 w-8 items-center justify-center rounded-full text-[var(--ui-color-danger)] transition hover:bg-[var(--ui-color-danger-soft)]"
                                onClick={() => setSelectionErrorMessage(null)}
                                type="button"
                              >
                                <XIcon className="h-4 w-4" />
                              </button>
                            }
                            tone="error"
                          >
                            {selectionErrorMessage}
                          </InlineNotice>
                        ) : null}
                      </div>
                  </div>
                </div>
              ) : null}
            </>
          )}
        </CentralWorkspaceSheet>
      </PosModuleLayout>
    </>
  );
}
