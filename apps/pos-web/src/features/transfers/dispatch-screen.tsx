import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Navigate } from "@tanstack/react-router";
import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ButtonHTMLAttributes,
  type ReactNode,
  type Ref,
} from "react";

import { useAppShellRightPanel } from "../../components/app-shell-right-panel";
import { CatalogSelectionCard } from "../../components/catalog-selection-card";
import { CatalogVisual } from "../../components/catalog-visual";
import {
  OperationConfirmationDialog,
  OperationDocumentResult,
  OperationDocumentSummaryPanel,
  OperationHistoryList,
  type OperationDocumentAction,
  type OperationHistoryRecord,
  type OperationLineSummaryItem,
} from "../../components/operation-documents";
import { OperationalStatus } from "../../components/operational-status";
import { PosContextBanner, PosModuleLayout, PosSummaryPanel } from "../../components/pos-module-layout";
import { PosFilterBar, PosHistoryView, PosRecordList } from "../../components/pos-records";
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
  PrinterIcon,
  RotateCcwIcon,
  StoreIcon,
  TrashIcon,
  TruckIcon,
  XIcon,
} from "../../components/pos-icons";
import { Button } from "../../components/ui/button";
import type {
  OperationHistoryFilterOptionView,
  OperationHistoryScopeView,
  TransferDestinationBranchView,
  TransferDetailResponse,
  TransferDispatchCommitRequest,
  TransferDispatchHistoryResponse,
} from "../../lib/api-contracts";
import { getDocumentActionAvailability } from "../../lib/document-actions";
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
  type OperationDraftState,
  type OperationLine,
} from "../operations/model";
import {
  useOperationsBootstrapQuery,
  useOperationsCatalogQuery,
  useOperationsClassProductsQuery,
} from "../operations/queries";
import { useRovingFocusGrid } from "../pos-shell/keyboard";
import { formatQuantityFromMilliUnits, hasCapturedQuantity } from "../pos-terminal/model";
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

function buildDraftLineSummaryItems(lines: OperationLine[]): OperationLineSummaryItem[] {
  return lines.map((line) => ({
    key: line.key,
    quantityText: line.quantityText,
    title: line.productName,
  }));
}

function buildTransferLineSummaryItems(
  transfer: TransferDetailResponse["shipment"],
): OperationLineSummaryItem[] {
  return transfer.lines.map((line) => ({
    key: line.id,
    quantityText: formatQuantityFromMilliUnits(Number(line.quantity) * 1000),
    secondaryText: line.product_class_name_snapshot,
    title: line.product_name_snapshot,
  }));
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
      : EMPTY_DESTINATION_TEXT;

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

function SelectionCard({
  badge,
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
  badge?: ReactNode;
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
      badge={badge}
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
  onRemove,
}: {
  disabled?: boolean;
  line: OperationLine;
  onRemove: () => void;
}) {
  return (
    <div className="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-2.5 border-t border-[var(--pos-shell-border)] px-3 py-2.5 first:border-t-0">
      <div className="min-w-0">
        <p
          className="break-words text-sm font-medium leading-5 text-slate-950"
          title={`${line.productName} x${line.quantityText}`}
        >
          {line.productName}{" "}
          <span className="whitespace-nowrap text-slate-600 [font-variant-numeric:tabular-nums]">
            x{line.quantityText}
          </span>
        </p>
      </div>
      <button
        aria-label={`Eliminar ${line.productName}`}
        className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md text-[var(--ui-color-danger)] transition hover:bg-[var(--ui-color-danger-soft)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--pos-ring)] disabled:pointer-events-none disabled:opacity-45"
        disabled={disabled}
        onClick={onRemove}
        type="button"
      >
        <TrashIcon className="h-4 w-4" />
      </button>
    </div>
  );
}

function DestinationRecord({
  branch,
  isSelected,
  originLabel,
}: {
  branch: TransferDestinationBranchView;
  isSelected: boolean;
  originLabel: string;
}) {
  return (
    <div className="grid gap-2">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="truncate text-sm font-semibold text-slate-950" title={branch.name}>
            {branch.name}
          </p>
          <p className="mt-0.5 text-xs font-medium uppercase tracking-[0.08em] text-slate-500">
            {branch.code}
          </p>
        </div>
        {isSelected ? (
          <span className="pos-chip" data-tone="primary">
            Seleccionada
          </span>
        ) : null}
      </div>
      <p className="text-sm text-slate-600">Ruta sugerida: {originLabel} -&gt; {branch.name}</p>
    </div>
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
  onClear,
  onCommit,
  onHistory,
  onNotesChange,
  onRemoveLine,
  onToggleNotes,
  originBranchLabel,
  routeLabel,
  totalUnitsText,
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
  onClear: () => void;
  onCommit: () => void;
  onHistory: () => void;
  onNotesChange: (value: string) => void;
  onRemoveLine: (lineKey: string) => void;
  onToggleNotes: () => void;
  originBranchLabel: string;
  routeLabel: string;
  totalUnitsText: string;
  uiState: TransferDispatchUiState;
}) {
  const lineCount = getOperationLineCount(lines);
  const emptyStateMessage = hasDestination
    ? "Agrega al menos una linea."
    : "Selecciona una sucursal destino en el panel central.";

  return (
    <PosSummaryPanel
      description="Resumen operativo del envio en construccion."
      stateLabel={getDispatchStatusLabel({ hasDestination, uiState })}
      stateTone={getDispatchStatusTone({ hasDestination, uiState })}
      title="Borrador de envio"
    >
      <div className="grid h-full min-h-0 grid-rows-[auto_auto_auto_minmax(0,1fr)] gap-3">
        <div className="grid gap-2">
          {commitErrorMessage ? <InlineNotice tone="error">{commitErrorMessage}</InlineNotice> : null}
          <div className="rounded-xl border border-[var(--pos-shell-border)] bg-[var(--pos-shell-muted)]/80 px-3 py-3">
            <p className="pos-label-text">Ruta sugerida</p>
            <div className="mt-2">
              <MovementBanner destinationLabel={destinationLabel} originLabel={originBranchLabel} />
            </div>
            <p className="mt-2 text-sm text-slate-600">
              {hasDestination
                ? routeLabel
                : "Selecciona una sucursal destino para habilitar el envio."}
            </p>
          </div>

          <div className="grid grid-cols-2 gap-2">
            <div className="rounded-xl border border-[var(--pos-shell-border)] bg-white px-3 py-2">
              <p className="pos-label-text">Lineas</p>
              <p className="mt-1 text-lg font-semibold text-slate-950 [font-variant-numeric:tabular-nums]">
                {lineCount}
              </p>
            </div>
            <div className="rounded-xl border border-[var(--pos-financial-border)] bg-[var(--pos-financial-bg)] px-3 py-2">
              <p className="pos-label-text">Unidades</p>
              <p className="mt-1 text-lg font-semibold text-slate-950 [font-variant-numeric:tabular-nums]">
                {totalUnitsText}
              </p>
            </div>
          </div>

          {commitBlockedReason ? <InlineNotice tone="warning">{commitBlockedReason}</InlineNotice> : null}
        </div>

        <div className="rounded-xl border border-[var(--pos-shell-border)] bg-white">
          <button
            aria-expanded={isNotesExpanded}
            className="flex w-full items-center justify-between gap-3 px-3 py-2.5 text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--pos-ring)]"
            disabled={isCommitPending}
            onClick={onToggleNotes}
            type="button"
          >
            <span className="text-sm font-semibold text-slate-900">Notas (opcional)</span>
            <ArrowLeftIcon
              className={cn("h-4 w-4 rotate-180 text-slate-400 transition", isNotesExpanded && "rotate-90")}
            />
          </button>
          {isNotesExpanded ? (
            <div className="border-t border-[var(--pos-shell-border)] px-3 pb-3 pt-2.5">
              <textarea
                className={cn("min-h-20 rounded-lg px-3 py-2 text-sm shadow-sm", posInputClass)}
                disabled={isCommitPending}
                onChange={(event) => onNotesChange(event.target.value)}
                placeholder="Notas operativas"
                value={notes}
              />
            </div>
          ) : null}
        </div>

        <RightPanelBlock className="grid min-h-0 overflow-hidden" title="Lineas capturadas" tone="muted">
          {lines.length === 0 ? (
            <div className="rounded-xl border border-dashed border-[var(--pos-shell-border)] bg-white px-4 py-5 text-sm text-slate-600">
              {emptyStateMessage}
            </div>
          ) : (
            <ScrollPane className="h-full pr-1">
              {lines.map((line) => (
                <DispatchLineRow
                  disabled={isCommitPending}
                  key={line.key}
                  line={line}
                  onRemove={() => onRemoveLine(line.key)}
                />
              ))}
            </ScrollPane>
          )}
        </RightPanelBlock>

        <div className="grid gap-2 border-t border-[var(--pos-shell-border)] pt-2">
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
            {isHistoryViewActive ? "Captura de envio" : "Ver historial"}
          </Button>
          <Button
            className={cn("h-10", posOutlineButtonClass)}
            disabled={lineCount === 0 || isCommitPending}
            onClick={onClear}
            type="button"
            variant="outline"
          >
            Vaciar envio
          </Button>
          <Button
            className={cn("h-11", posPrimaryButtonClass)}
            disabled={commitBlockedReason !== null || isCommitPending}
            onClick={onCommit}
            type="button"
          >
            {isCommitPending ? "Registrando..." : "Registrar envio"}
          </Button>
        </div>
      </div>
    </PosSummaryPanel>
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
  const [destinationSearchText, setDestinationSearchText] = useState("");
  const [notes, setNotes] = useState("");
  const [selectionErrorMessage, setSelectionErrorMessage] = useState<string | null>(null);
  const [commitErrorMessage, setCommitErrorMessage] = useState<string | null>(null);
  const [lastCommittedTransfer, setLastCommittedTransfer] = useState<TransferDetailResponse | null>(
    null,
  );
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
      setLastCommittedTransfer(detail);
      setDraftState(createInitialOperationDraftState());
      setSelectionErrorMessage(null);
      setCommitErrorMessage(null);
      setNotes("");
      setIsNotesExpanded(false);
      setCenterView("capture");
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

      setLastCommittedTransfer(null);
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

      setLastCommittedTransfer(null);
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
  const filteredDestinationBranches = useMemo(() => {
    const branches = operationsBootstrapQuery.data?.destination_branches ?? [];
    const normalizedQuery = destinationSearchText.trim().toLowerCase();

    if (normalizedQuery.length === 0) {
      return branches;
    }

    return branches.filter((branch) => {
      const nameMatches = branch.name.toLowerCase().includes(normalizedQuery);
      const codeMatches = branch.code.toLowerCase().includes(normalizedQuery);
      return nameMatches || codeMatches;
    });
  }, [destinationSearchText, operationsBootstrapQuery.data?.destination_branches]);
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
    hasCommittedTransfer: lastCommittedTransfer !== null,
    hasDestination,
    isCaptureInProgress: draftState.controlState !== CONTROL_STATE_CLASS_SELECTION,
    isCommitPending: commitMutation.isPending,
    isValidationReady,
    lineCount,
  });
  const showSearch =
    centerView === "capture" && displayControlState !== CONTROL_STATE_QUANTITY_CAPTURE;
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
          setLastCommittedTransfer(null);
          setDraftState((state) => selectClassForOperation(state, productClass));
        }
        return;
      }

      if (displayControlState === CONTROL_STATE_PRODUCT_SELECTION) {
        const product = sortedProducts[shortcutIndex];
        if (product) {
          event.preventDefault();
          setLastCommittedTransfer(null);
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

  const clearDraft = useCallback(() => {
    if (draftState.lines.length > 0 && !window.confirm("Vaciar el borrador actual del envio?")) {
      return;
    }

    setDraftState(createInitialOperationDraftState());
    setLastCommittedTransfer(null);
    setSelectionErrorMessage(null);
    setCommitErrorMessage(null);
    setNotes("");
    setIsNotesExpanded(false);
    setCenterView("capture");
  }, [draftState.lines.length]);

  const handleDestinationChange = useCallback((nextBranchId: string) => {
    setDestinationBranchId(nextBranchId);
    setLastCommittedTransfer(null);
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
      setLastCommittedTransfer(null);
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
  const shipmentDocumentAvailability = getDocumentActionAvailability("branchShipmentDocument");

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
        <OperationDocumentSummaryPanel
          actions={[
              {
                key: "back-to-capture",
                label: "Enviar a sucursal",
                leadingIcon: <RotateCcwIcon className="h-4 w-4" />,
                onSelect: () => setCenterView("capture"),
                variant: "primary",
              },
              {
                availabilityNote: shipmentDocumentAvailability.print.unavailableReason,
                disabled: !shipmentDocumentAvailability.print.isAvailable,
                kind: "print",
                key: "print-history",
                label: shipmentDocumentAvailability.print.label,
                leadingIcon: <PrinterIcon className="h-4 w-4" />,
                onSelect: () => undefined,
                variant: "neutral",
            },
          ]}
          auditSummary={selectedHistoryTransfer.shipment.audit_summary}
          context={{
            branchName: selectedHistoryTransfer.shipment.source_branch_name,
            userName: selectedHistoryTransfer.shipment.created_by_user_full_name,
            workstationName: selectedHistoryTransfer.shipment.workstation_name,
            }}
            description="Detalle del envio seleccionado."
            kind="branchShipment"
            lines={buildTransferLineSummaryItems(selectedHistoryTransfer.shipment)}
            metrics={[
              {
                key: "destination-branch",
                label: "Destino",
                value: selectedHistoryTransfer.shipment.destination_branch_name ?? EMPTY_DESTINATION_TEXT,
              },
              {
                key: "route",
                label: "Ruta",
                value: getRouteSuggestionLabel(
                  selectedHistoryTransfer.shipment.source_branch_name,
                  selectedHistoryTransfer.shipment.destination_branch_name,
                ),
              },
              {
                key: "line-count",
                label: "Lineas",
                value: String(selectedHistoryTransfer.shipment.lines.length),
              },
              {
                key: "units",
                label: "Unidades",
                tone: "financial",
                value: formatQuantityFromMilliUnits(
                  selectedHistoryTransfer.shipment.lines.reduce(
                    (total, line) => total + Number(line.quantity) * 1000,
                    0,
                  ),
                ),
              },
            ]}
            notices={
              selectedHistoryTransfer.receipt_summary ? (
                <InlineNotice
                  tone={
                    selectedHistoryTransfer.receipt_summary.status === "RECEIVED_WITH_VARIANCE"
                      ? "warning"
                      : "success"
                  }
                >
                  Recepcion vinculada: {selectedHistoryTransfer.receipt_summary.folio}.
                </InlineNotice>
              ) : undefined
            }
          referenceValue={selectedHistoryTransfer.shipment_summary.folio}
          stateLabel={getTransferDocumentStatusLabel(selectedHistoryTransfer.shipment.status)}
          stateTone={getTransferDocumentStatusTone(selectedHistoryTransfer.shipment.status)}
          timeZone={operationsBootstrapQuery.data?.branch.timezone ?? "America/Hermosillo"}
          timestamps={{
              committedAtValue: selectedHistoryTransfer.shipment.committed_at_utc
                ? formatCompactLocalDateTime(
                    selectedHistoryTransfer.shipment.committed_at_utc,
                    operationsBootstrapQuery.data?.branch.timezone ?? "America/Hermosillo",
                  )
                : null,
              createdAtValue: formatCompactLocalDateTime(
                selectedHistoryTransfer.shipment.created_at_utc,
                operationsBootstrapQuery.data?.branch.timezone ?? "America/Hermosillo",
              ),
            }}
            title="Envio seleccionado"
          />
        );
      }

      return (
        <PosSummaryPanel
          description="Selecciona un envio del historial para revisar su folio y trazabilidad."
            stateLabel={historyQuery.isPending || isSelectedHistoryTransferPending ? "Consultando" : "Sin seleccion"}
            stateTone={historyQuery.isPending || isSelectedHistoryTransferPending ? "pending" : "draft"}
          title="Historial de envios"
        >
          <div className="flex h-full items-center justify-center px-3 text-center">
            <p className="text-sm leading-6 text-slate-600">
              Elige un envio del historial para ver destino, lineas y estado logístico.
            </p>
          </div>
        </PosSummaryPanel>
      );
    }

    if (lastCommittedTransfer !== null) {
      const resultActions: OperationDocumentAction[] = [
        {
          availabilityNote: shipmentDocumentAvailability.print.unavailableReason,
          disabled: !shipmentDocumentAvailability.print.isAvailable,
          kind: "print",
          key: "print",
          label: shipmentDocumentAvailability.print.label,
          leadingIcon: <PrinterIcon className="h-4 w-4" />,
          onSelect: () => undefined,
          variant: "neutral",
        },
        {
          key: "history",
          label: "Ver historial",
          leadingIcon: <RotateCcwIcon className="h-4 w-4" />,
          onSelect: () => {
            setSelectedHistoryTransferId(lastCommittedTransfer.shipment.id);
            setCenterView("history");
          },
          variant: "neutral",
        },
        {
          key: "new-shipment",
          label: "Nuevo envio",
          leadingIcon: <ClipboardIcon className="h-4 w-4" />,
          onSelect: () => {
            setLastCommittedTransfer(null);
            setCenterView("capture");
          },
          variant: "primary",
        },
      ];

      return (
        <OperationDocumentResult
          actions={resultActions}
          auditSummary={lastCommittedTransfer.shipment.audit_summary}
          context={{
            branchName: lastCommittedTransfer.shipment.source_branch_name,
            userName: lastCommittedTransfer.shipment.created_by_user_full_name,
            workstationName: lastCommittedTransfer.shipment.workstation_name,
          }}
          description="El envio ya quedo confirmado. Puedes continuar con un nuevo documento o revisar el historial."
          kind="branchShipment"
          metrics={[
            {
              key: "destination-branch",
              label: "Destino",
              value: lastCommittedTransfer.shipment.destination_branch_name ?? EMPTY_DESTINATION_TEXT,
            },
            {
              key: "route",
              label: "Ruta",
              value: getRouteSuggestionLabel(
                lastCommittedTransfer.shipment.source_branch_name,
                lastCommittedTransfer.shipment.destination_branch_name,
              ),
            },
            {
              key: "line-count",
              label: "Lineas",
              value: String(lastCommittedTransfer.shipment.lines.length),
            },
            {
              key: "units",
              label: "Unidades",
              tone: "financial",
              value: formatQuantityFromMilliUnits(
                lastCommittedTransfer.shipment.lines.reduce(
                  (total, line) => total + Number(line.quantity) * 1000,
                  0,
                ),
              ),
            },
          ]}
          referenceValue={lastCommittedTransfer.shipment_summary.folio}
          timeZone={operationsBootstrapQuery.data?.branch.timezone ?? "America/Hermosillo"}
          timestamps={{
            committedAtValue: lastCommittedTransfer.shipment.committed_at_utc
              ? formatCompactLocalDateTime(
                  lastCommittedTransfer.shipment.committed_at_utc,
                  operationsBootstrapQuery.data?.branch.timezone ?? "America/Hermosillo",
                )
              : null,
            createdAtValue: formatCompactLocalDateTime(
              lastCommittedTransfer.shipment.created_at_utc,
              operationsBootstrapQuery.data?.branch.timezone ?? "America/Hermosillo",
            ),
          }}
        />
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
        onClear={clearDraft}
        onCommit={() => {
          if (commitBlockedReason === null && !commitMutation.isPending) {
            setIsConfirmDialogOpen(true);
          }
        }}
        onHistory={openHistoryView}
        onNotesChange={(value) => {
          setLastCommittedTransfer(null);
          setNotes(value);
          if (value.trim().length > 0) {
            setIsNotesExpanded(true);
          }
        }}
        onRemoveLine={(lineKey) => {
          setLastCommittedTransfer(null);
          setDraftState((state) => ({
            ...state,
            lines: removeOperationLine(state.lines, lineKey),
          }));
        }}
        onToggleNotes={() => setIsNotesExpanded((current) => !current)}
        originBranchLabel={originBranchLabel}
        routeLabel={routeSuggestionLabel}
        totalUnitsText={totalUnitsText}
        uiState={uiState}
      />
    );
  }, [
    centerView,
    clearDraft,
    commitBlockedReason,
    commitErrorMessage,
    commitMutation.isPending,
    destinationLabel,
    draftState.lines,
    hasDestination,
    historyQuery.isPending,
    isNotesExpanded,
    lastCommittedTransfer,
    notes,
    openHistoryView,
    operationsBootstrapQuery.data?.branch.timezone,
    originBranchLabel,
    routeSuggestionLabel,
    selectedHistoryTransfer,
    selectedHistoryTransferQuery.error,
    isSelectedHistoryTransferPending,
    shipmentDocumentAvailability.print.isAvailable,
    shipmentDocumentAvailability.print.label,
    shipmentDocumentAvailability.print.unavailableReason,
    totalUnitsText,
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
      title="Enviar a sucursal"
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
              label: "Resumen",
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
              if (lastCommittedTransfer !== null) {
                setLastCommittedTransfer(null);
              }
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
      <OperationConfirmationDialog
        confirmLabel="Confirmar envio"
        context={{
          branchName: operationsBootstrapQuery.data.branch.name,
          userName: operationsBootstrapQuery.data.user.full_name,
          workstationName: operationsBootstrapQuery.data.workstation.name,
        }}
        description="Revisa destino, ruta y lineas antes de confirmar la salida desde fondo."
        isOpen={isConfirmDialogOpen}
        isPending={commitMutation.isPending}
        kind="branchShipment"
        lines={buildDraftLineSummaryItems(draftState.lines)}
        metrics={[
          {
            key: "destination-branch",
            label: "Destino",
            value: destinationLabel,
          },
          {
            key: "route",
            label: "Ruta",
            value: routeSuggestionLabel,
          },
          {
            key: "line-count",
            label: "Lineas",
            value: String(lineCount),
          },
          {
            key: "units",
            label: "Unidades",
            tone: "financial",
            value: totalUnitsText,
          },
          {
            key: "inventory-impact",
            label: "Impacto",
            value: "Fondo -> En transito",
          },
        ]}
        onCancel={() => setIsConfirmDialogOpen(false)}
        onConfirm={() => {
          void handleConfirmCommit();
        }}
        title="Confirmar envio a sucursal"
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
              action={
                <Button
                  className={cn("h-10 px-3", posOutlineButtonClass)}
                  onClick={() => setCenterView("capture")}
                  type="button"
                  variant="outline"
                >
                  <ArrowLeftIcon className="h-4 w-4" />
                  Enviar a sucursal
                </Button>
              }
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
              <PosContextBanner
                description="Selecciona la sucursal destino y agrega productos exactos para preparar el documento de salida desde fondo."
                title={`Fondo -> ${selectedDestinationBranch?.name ?? "Sucursal destino"}`}
              />

              <div
                className="mt-3 grid gap-3 rounded-xl border border-[var(--pos-shell-border)] bg-white px-3.5 py-3.5"
                data-transfer-destination-selector="true"
              >
                <div className="grid gap-1">
                  <p className="pos-label-text">Destino operativo</p>
                  <h2 className="text-sm font-semibold text-slate-950">
                    Selecciona la sucursal destino
                  </h2>
                  <p className="text-sm text-slate-600">
                    Busca por nombre o codigo y confirma la ruta antes de capturar productos.
                  </p>
                </div>

                <div className="grid gap-3 xl:grid-cols-[minmax(16rem,20rem)_minmax(0,1fr)] xl:items-end">
                  <SearchField
                    ariaLabel="Buscar sucursal destino"
                    className="w-full"
                    disabled={commitMutation.isPending}
                    inputClassName={cn("h-10 rounded-lg text-sm shadow-sm", posInputClass)}
                    onChange={setDestinationSearchText}
                    placeholder="Buscar sucursal destino"
                    value={destinationSearchText}
                  />
                  <div className="grid gap-2">
                    <p className="pos-label-text">Ruta sugerida</p>
                    <MovementBanner
                      destinationLabel={selectedDestinationBranch?.name ?? null}
                      originLabel={originBranchLabel}
                    />
                  </div>
                </div>

                <div className="grid gap-2">
                  <p className="text-xs font-medium uppercase tracking-[0.08em] text-slate-500">
                    Flechas: navegar · Enter: seleccionar
                  </p>
                  <PosRecordList
                    className="max-h-[13rem]"
                    emptyDescription="No hay sucursales destino para esta busqueda."
                    emptyTitle="Sin sucursales"
                    getKey={(branch) => branch.id}
                    onSelect={(branch) => {
                      if (commitMutation.isPending) {
                        return;
                      }
                      handleDestinationChange(branch.id);
                    }}
                    records={filteredDestinationBranches}
                    renderContent={(branch, state) => (
                      <DestinationRecord
                        branch={branch}
                        isSelected={state.isSelected}
                        originLabel={originBranchLabel}
                      />
                    )}
                    selectedKey={destinationBranchId || null}
                  />
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
                  <p className="text-xs font-medium uppercase tracking-[0.08em] text-slate-500">
                    Flechas: navegar · Enter: seleccionar · Esc: volver
                  </p>
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
                                setLastCommittedTransfer(null);
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
                  <p className="text-xs font-medium uppercase tracking-[0.08em] text-slate-500">
                    Flechas: navegar · Enter: seleccionar · Esc: volver
                  </p>
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
                              badge={
                                <span className="pos-chip" data-tone="muted">
                                  Producto exacto
                                </span>
                              }
                              buttonRef={itemProps.ref}
                              code={product.code}
                              isActive={productActiveIndex === index}
                              isDisabled={!hasDestination || commitMutation.isPending}
                              isPrimaryControl={index === 0}
                              key={product.id}
                              onCardFocus={itemProps.onFocus}
                              onCardKeyDown={itemProps.onKeyDown}
                              onSelect={() => {
                                setLastCommittedTransfer(null);
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
                <div className="mt-3 w-full max-w-5xl justify-self-center rounded-xl border border-[var(--pos-shell-border)] bg-white p-3.5 shadow-sm">
                  <div className="grid gap-4 lg:grid-cols-[11rem_minmax(0,1fr)]">
                    <CatalogVisual
                      className="min-h-[10.5rem]"
                      code={quantityProduct.code}
                      name={quantityProduct.name}
                    />

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
                </div>
              ) : null}
            </>
          )}
        </CentralWorkspaceSheet>
      </PosModuleLayout>
    </>
  );
}
