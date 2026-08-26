import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Navigate } from "@tanstack/react-router";
import {
  Fragment,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type KeyboardEvent as ReactKeyboardEvent,
  type Ref,
} from "react";

import { useAppShellRightPanel } from "../../components/app-shell-right-panel";
import { CapturedProductLineList, CapturedProductLineRow } from "../../components/captured-product-lines";
import { CatalogSelectionCard } from "../../components/catalog-selection-card";
import { CatalogVisual } from "../../components/catalog-visual";
import {
  PosErrorState,
  PosInlineValidationMessage,
  PosLoadingState,
} from "../../components/pos-feedback";
import {
  CentralWorkspaceSheet,
  CompactPageHeader,
  ModuleStateChip,
  RightPanelBlock,
  ScrollPane,
  SearchField,
} from "../../components/pos-module-primitives";
import {
  ArrowLeftIcon,
  CheckCircleIcon,
  ChevronRightIcon,
  HashIcon,
  PackageIcon,
  RotateCcwIcon,
  StoreIcon,
} from "../../components/pos-icons";
import { Button } from "../../components/ui/button";
import { appEnv } from "../../env";
import type {
  CashCloseCounterClassAvailabilityView,
  CashCloseReconciliationProductView,
  CashCloseReconciliationResponse,
  CorrectionDocumentView,
  CorrectionReasonView,
  CounterTransferCommitRequest,
  OperationDocumentView,
  OperationHistoryResponse,
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
import {
  cashCloseReconciliationQueryKey,
  useCashCloseReconciliationQuery,
} from "../cash-close/queries";
import { useCurrentCashSessionQuery } from "../cash-session-open/queries";
import { commitCorrection } from "../corrections/corrections-api";
import {
  correctionTargetDetailQueryKey,
  correctionsBootstrapQueryKey,
  useCorrectionsBootstrapQuery,
} from "../corrections/queries";
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
  addPendingSelectionLine,
  buildOperationCommitLines,
  CONTROL_STATE_CLASS_SELECTION,
  CONTROL_STATE_PRODUCT_SELECTION,
  CONTROL_STATE_QUANTITY_CAPTURE,
  createInitialOperationDraftState,
  decrementPendingOperationQuantity,
  getOperationLineCount,
  getOperationTotalUnitsMilli,
  goBackFromOperationalState,
  incrementPendingOperationQuantity,
  type OperationDraftState,
  type OperationLine,
  removeOperationLine,
  selectClassForOperation,
  selectProductForOperation,
  setPendingQuantityText,
  sortOperationalClasses,
  sortOperationalProducts,
  updateOperationLineQuantity,
} from "./model";
import { commitCounterTransfer } from "./operations-api";
import {
  operationDocumentQueryKey,
  operationHistoryQueryKey,
  useOperationDocumentQuery,
  useOperationHistoryQuery,
  useOperationsBootstrapQuery,
  useOperationsCatalogQuery,
  useOperationsClassProductsQuery,
} from "./queries";

const COUNTER_TRANSFER_MODULE = "COUNTER_TRANSFER";
const NOTE_MAX_LENGTH = 240;
const CORRECTION_REASON_WRONG_DESTINATION = "WRONG_DESTINATION";
type CounterTransferView = "capture" | "history";
type HistoryDetailMode = "adjustment" | "detail";
type HistoryDaypartFilter = "ALL" | "MORNING" | "AFTERNOON" | "NIGHT";

const HISTORY_DAYPART_FILTERS: Array<Exclude<HistoryDaypartFilter, "ALL">> = [
  "MORNING",
  "AFTERNOON",
  "NIGHT",
];

type CounterTransferAdjustmentDraftLine = {
  lineId: string;
  originalQuantityMilliUnits: number;
  originalQuantityText: string;
  productId: string;
  productName: string;
  quantityText: string;
};

type CounterTransferAdjustmentDraft = {
  highImpactAcknowledged: boolean;
  lines: CounterTransferAdjustmentDraftLine[];
  reasonCode: string;
};

function useDebouncedValue(value: string, delayMs: number): string {
  const [debouncedValue, setDebouncedValue] = useState(value);

  useEffect(() => {
    const timeout = window.setTimeout(() => setDebouncedValue(value), delayMs);
    return () => window.clearTimeout(timeout);
  }, [delayMs, value]);

  return debouncedValue;
}

function isNumpadSubmitKey(event: ReactKeyboardEvent<HTMLInputElement>) {
  return event.key === "Enter" || event.key === "NumpadEnter";
}

function createRequestId(scope: string): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return `${scope}-${crypto.randomUUID()}`;
  }

  return `${scope}-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function getTransferStateLabel(lineCount: number, isCommitPending: boolean): string {
  if (isCommitPending) {
    return "Registrando";
  }

  return lineCount > 0 ? "Listo" : "Sin productos";
}

function getTransferStateTone(
  lineCount: number,
  isCommitPending: boolean,
): "muted" | "primary" | "success" {
  if (isCommitPending) {
    return "primary";
  }

  return lineCount > 0 ? "success" : "muted";
}

function getActiveStep(state: OperationDraftState): string {
  if (state.controlState === CONTROL_STATE_PRODUCT_SELECTION) {
    return "product";
  }

  if (state.controlState === CONTROL_STATE_QUANTITY_CAPTURE) {
    return "quantity";
  }

  return "class";
}

function getHistoryScopeLabel(scope: string): string {
  switch (scope) {
    case "ALL":
      return "Todos";
    case "CURRENT_SHIFT":
      return "Turno";
    case "TODAY":
      return "Hoy";
    case "RECENT":
      return "Recientes";
    default:
      return scope;
  }
}

function getHistoryStatusLabel(status: string): string {
  if (status === "COMMITTED") {
    return "Confirmado";
  }

  return status;
}

function getHistoryDaypartLabel(daypart: HistoryDaypartFilter): string {
  switch (daypart) {
    case "MORNING":
      return "Mañana";
    case "AFTERNOON":
      return "Tarde";
    case "NIGHT":
      return "Noche";
    default:
      return "Todo";
  }
}

function getHistoryRecordTimestamp(
  record: OperationHistoryResponse["records"][number],
): string {
  return record.committed_at_utc ?? record.created_at_utc;
}

function getLocalHourFromTimestamp(timestamp: string, timeZone: string): number | null {
  const date = new Date(timestamp);
  if (Number.isNaN(date.getTime())) {
    return null;
  }

  const hourPart = new Intl.DateTimeFormat("en-US", {
    hour: "2-digit",
    hour12: false,
    timeZone,
  })
    .formatToParts(date)
    .find((part) => part.type === "hour");
  const parsedHour = Number(hourPart?.value);

  return Number.isFinite(parsedHour) ? parsedHour % 24 : null;
}

function getHistoryRecordDaypart(
  record: OperationHistoryResponse["records"][number],
  timeZone: string,
): HistoryDaypartFilter | null {
  const localHour = getLocalHourFromTimestamp(getHistoryRecordTimestamp(record), timeZone);
  if (localHour === null) {
    return null;
  }

  if (localHour < 12) {
    return "MORNING";
  }

  if (localHour < 19) {
    return "AFTERNOON";
  }

  return "NIGHT";
}

function getHistoryRecordUnits(record: OperationHistoryResponse["records"][number]): string {
  return formatQuantityFromMilliUnits(Number(record.total_quantity) * 1000);
}

function getDocumentTotalUnits(document: OperationDocumentView): string {
  return formatQuantityFromMilliUnits(
    document.lines.reduce((sum, line) => sum + Number(line.quantity) * 1000, 0),
  );
}

function getDefaultCorrectionReasonCode(reasons: CorrectionReasonView[]): string {
  return (
    reasons.find((reason) => reason.code === "WRONG_QUANTITY")?.code ??
    reasons.find((reason) => reason.code !== CORRECTION_REASON_WRONG_DESTINATION)?.code ??
    ""
  );
}

function createAdjustmentDraft(
  document: OperationDocumentView | null,
  reasons: CorrectionReasonView[],
): CounterTransferAdjustmentDraft {
  return {
    highImpactAcknowledged: false,
    lines:
      document?.lines.map((line) => {
        const originalQuantityMilliUnits = Math.round(Number(line.quantity) * 1000);
        const originalQuantityText = formatQuantityFromMilliUnits(originalQuantityMilliUnits);

        return {
          lineId: line.id,
          originalQuantityMilliUnits,
          originalQuantityText,
          productId: line.product_id,
          productName: line.product_name_snapshot,
          quantityText: originalQuantityText,
        };
      }) ?? [],
    reasonCode: getDefaultCorrectionReasonCode(reasons),
  };
}

function parseInlineAdjustmentQuantityToMilliUnits(quantityText: string): number | null {
  const normalizedQuantityText = quantityText.trim();
  if (!/^\d+(\.\d*)?$/.test(normalizedQuantityText)) {
    return null;
  }

  const [wholePart, decimalPart = ""] = normalizedQuantityText.split(".");
  if (decimalPart.length > 3) {
    return null;
  }

  return Number.parseInt(wholePart, 10) * 1000 + Number.parseInt(decimalPart.padEnd(3, "0"), 10);
}

function getAdjustmentLineDeltaMilliUnits(line: CounterTransferAdjustmentDraftLine): number | null {
  if (line.quantityText.trim().length === 0) {
    return null;
  }

  const quantityMilliUnits = parseInlineAdjustmentQuantityToMilliUnits(line.quantityText);
  if (quantityMilliUnits === null || quantityMilliUnits < 0) {
    return null;
  }

  return quantityMilliUnits - line.originalQuantityMilliUnits;
}

function formatSignedQuantityForApi(quantityMilliUnits: number): string {
  const sign = quantityMilliUnits < 0 ? "-" : "";
  return `${sign}${formatQuantityFromMilliUnits(Math.abs(quantityMilliUnits))}`;
}

function formatSignedQuantityForDisplay(quantityMilliUnits: number): string {
  const sign = quantityMilliUnits > 0 ? "+" : quantityMilliUnits < 0 ? "-" : "";
  return `${sign}${formatQuantityFromMilliUnits(Math.abs(quantityMilliUnits))}`;
}

function getAdjustmentDraftActiveLines(draft: CounterTransferAdjustmentDraft) {
  return draft.lines
    .map((line) => ({
      line,
      deltaQuantityMilliUnits: getAdjustmentLineDeltaMilliUnits(line),
    }))
    .filter(
      (
        item,
      ): item is {
        deltaQuantityMilliUnits: number;
        line: CounterTransferAdjustmentDraftLine;
      } => item.deltaQuantityMilliUnits !== null,
    );
}

function getAdjustmentDraftChangedLines(draft: CounterTransferAdjustmentDraft) {
  return getAdjustmentDraftActiveLines(draft).filter(
    (item) => item.deltaQuantityMilliUnits !== 0,
  );
}

function getAdjustmentDraftInvalidLineCount(draft: CounterTransferAdjustmentDraft): number {
  return draft.lines.filter((line) => getAdjustmentLineDeltaMilliUnits(line) === null).length;
}

function getAdjustmentTotalMagnitudeMilliUnits(draft: CounterTransferAdjustmentDraft): number {
  return getAdjustmentDraftChangedLines(draft).reduce(
    (sum, item) => sum + Math.abs(item.deltaQuantityMilliUnits),
    0,
  );
}

function updateLineQuantity(
  lines: OperationLine[],
  lineKey: string,
  quantityMilliUnits: number,
): OperationLine[] {
  return lines.map((line) =>
    line.key === lineKey ? updateOperationLineQuantity(line, quantityMilliUnits) : line,
  );
}

export function CounterTransferScreen() {
  const accessToken = usePosAuthStore((state) => state.accessToken);
  const showError = useStatusMessageStore((state) => state.showError);
  const showSuccess = useStatusMessageStore((state) => state.showSuccess);
  const showWarning = useStatusMessageStore((state) => state.showWarning);
  const queryClient = useQueryClient();
  const operationsBootstrapQuery = useOperationsBootstrapQuery();
  const currentCashSessionQuery = useCurrentCashSessionQuery();
  const correctionsBootstrapQuery = useCorrectionsBootstrapQuery();
  const [draftState, setDraftState] = useState(createInitialOperationDraftState);
  const [notes, setNotes] = useState("");
  const [selectionErrorMessage, setSelectionErrorMessage] = useState<string | null>(null);
  const [commitErrorMessage, setCommitErrorMessage] = useState<string | null>(null);
  const [lastCommittedDocument, setLastCommittedDocument] =
    useState<OperationDocumentView | null>(null);
  const [currentView, setCurrentView] = useState<CounterTransferView>("capture");
  const [historyScope, setHistoryScope] = useState("CURRENT_SHIFT");
  const [historyCashierId, setHistoryCashierId] = useState("ALL");
  const [historyDaypart, setHistoryDaypart] = useState<HistoryDaypartFilter>("ALL");
  const [selectedHistoryDocumentId, setSelectedHistoryDocumentId] = useState<string | null>(null);
  const [historyDetailMode, setHistoryDetailMode] = useState<HistoryDetailMode>("detail");
  const [isCaptureCounterStateOpen, setIsCaptureCounterStateOpen] = useState(false);
  const [adjustmentDraft, setAdjustmentDraft] = useState<CounterTransferAdjustmentDraft>(() =>
    createAdjustmentDraft(null, []),
  );
  const [adjustmentErrorMessage, setAdjustmentErrorMessage] = useState<string | null>(null);
  const [lastCommittedCorrection, setLastCommittedCorrection] =
    useState<CorrectionDocumentView | null>(null);
  const quantityInputRef = useRef<HTMLInputElement>(null);
  const searchInputRef = useRef<HTMLInputElement>(null);
  const lastAutoFocusedGridKeyRef = useRef<string | null>(null);
  const debouncedSearchText = useDebouncedValue(draftState.searchText, 180);

  const catalogQuery = useOperationsCatalogQuery(
    COUNTER_TRANSFER_MODULE,
    draftState.controlState === CONTROL_STATE_CLASS_SELECTION ? debouncedSearchText : "",
  );
  const classProductsQuery = useOperationsClassProductsQuery(
    COUNTER_TRANSFER_MODULE,
    draftState.pendingSelection?.productClass.id ?? null,
    draftState.controlState === CONTROL_STATE_PRODUCT_SELECTION ? debouncedSearchText : "",
  );
  const historyFilters = useMemo(
    () => ({
      createdByUserId: historyCashierId === "ALL" ? undefined : historyCashierId,
      scope: historyScope,
    }),
    [historyCashierId, historyScope],
  );
  const historyQuery = useOperationHistoryQuery(
    "COUNTER_TRANSFER",
    historyFilters,
    currentView === "history",
  );
  const selectedHistoryDocumentQuery = useOperationDocumentQuery(
    currentView === "history" ? selectedHistoryDocumentId : null,
  );
  const counterAvailabilityQuery = useCashCloseReconciliationQuery(
    currentView === "history" || isCaptureCounterStateOpen,
  );

  const sortedClasses = useMemo(
    () => sortOperationalClasses(catalogQuery.data?.classes ?? []),
    [catalogQuery.data?.classes],
  );
  const sortedProducts = useMemo(
    () => sortOperationalProducts(classProductsQuery.data?.products ?? []),
    [classProductsQuery.data?.products],
  );

  const lineCount = getOperationLineCount(draftState.lines);
  const totalUnitsMilli = getOperationTotalUnitsMilli(draftState.lines);
  const totalUnitsText = formatQuantityFromMilliUnits(totalUnitsMilli);
  const correctionReasons = useMemo(
    () =>
      (correctionsBootstrapQuery.data?.correction_reasons ?? []).filter(
        (reason) => reason.code !== CORRECTION_REASON_WRONG_DESTINATION,
      ),
    [correctionsBootstrapQuery.data?.correction_reasons],
  );
  const adjustmentActiveLines = useMemo(
    () => getAdjustmentDraftChangedLines(adjustmentDraft),
    [adjustmentDraft],
  );
  const adjustmentInvalidLineCount = useMemo(
    () => getAdjustmentDraftInvalidLineCount(adjustmentDraft),
    [adjustmentDraft],
  );
  const adjustmentTotalMagnitudeMilliUnits = useMemo(
    () => getAdjustmentTotalMagnitudeMilliUnits(adjustmentDraft),
    [adjustmentDraft],
  );
  const correctionHighImpactThresholdMilliUnits =
    parseQuantityToMilliUnits(
      String(
        correctionsBootstrapQuery.data?.correction_controls.high_impact_quantity_threshold ?? "0",
      ),
    ) ?? 0;
  const isAdjustmentHighImpact =
    correctionHighImpactThresholdMilliUnits > 0 &&
    adjustmentTotalMagnitudeMilliUnits >= correctionHighImpactThresholdMilliUnits;
  function updateDraftState(updater: (state: OperationDraftState) => OperationDraftState) {
    setDraftState((state) => updater(state));
    setLastCommittedDocument(null);
    setCommitErrorMessage(null);
  }

  const commitMutation = useMutation({
    mutationFn: async () => {
      if (accessToken === null || operationsBootstrapQuery.data === undefined) {
        throw new Error("No hay contexto operativo para registrar el movimiento.");
      }

      const payload: CounterTransferCommitRequest = {
        lines: buildOperationCommitLines(draftState.lines),
        notes: notes.trim().length > 0 ? notes.trim() : null,
        workstation_code: operationsBootstrapQuery.data.workstation.code,
      };

      return commitCounterTransfer(accessToken, payload);
    },
    onError: (error) => {
      const message = toOperationalErrorMessage(
        error,
        "No fue posible registrar el movimiento a mostrador.",
      );
      setCommitErrorMessage(message);
      showError(message);
    },
    onSuccess: (document) => {
      setDraftState(createInitialOperationDraftState());
      setNotes("");
      setSelectionErrorMessage(null);
      setCommitErrorMessage(null);
      setLastCommittedDocument(document);
      showSuccess(`Movimiento a mostrador registrado. Folio ${document.folio}.`);
      void queryClient.invalidateQueries({
        queryKey: operationHistoryQueryKey(appEnv.VITE_POS_WORKSTATION_CODE, "COUNTER_TRANSFER", {
          scope: "CURRENT_SHIFT",
        }),
      });
      void queryClient.invalidateQueries({
        queryKey: operationDocumentQueryKey(appEnv.VITE_POS_WORKSTATION_CODE, document.id),
      });
      void queryClient.invalidateQueries({
        queryKey: cashCloseReconciliationQueryKey(appEnv.VITE_POS_WORKSTATION_CODE),
      });
    },
  });

  const adjustmentMutation = useMutation({
    mutationFn: async () => {
      const selectedDocument = selectedHistoryDocumentQuery.data;
      if (!accessToken || !selectedDocument) {
        throw new Error("Selecciona un movimiento antes de aplicar un ajuste.");
      }

      if (adjustmentDraft.reasonCode.trim().length === 0) {
        throw new Error("No fue posible cargar el motivo de ajuste.");
      }

      if (adjustmentActiveLines.length === 0) {
        throw new Error("No hay cambios para guardar.");
      }

      if (adjustmentInvalidLineCount > 0) {
        throw new Error("Revisa las cantidades del ajuste.");
      }

      if (isAdjustmentHighImpact && !adjustmentDraft.highImpactAcknowledged) {
        throw new Error("Confirma el ajuste de alto impacto antes de registrarlo.");
      }

      return commitCorrection({
        accessToken,
        payload: {
          high_impact_acknowledged: adjustmentDraft.highImpactAcknowledged,
          lines: adjustmentActiveLines.map(({ deltaQuantityMilliUnits, line }) => ({
            delta_quantity: formatSignedQuantityForApi(deltaQuantityMilliUnits),
            product_id: line.productId,
            target_line_id: line.lineId,
          })),
          reason_code: adjustmentDraft.reasonCode,
          target_document_id: selectedDocument.id,
          workstation_code: appEnv.VITE_POS_WORKSTATION_CODE,
        },
        requestId: createRequestId("counter-transfer-adjustment"),
      });
    },
    onError: (error) => {
      const message = toOperationalErrorMessage(error, "No fue posible registrar el ajuste.");
      setAdjustmentErrorMessage(message);
      showError(message);
    },
    onSuccess: async (correction) => {
      setLastCommittedCorrection(correction);
      setHistoryDetailMode("detail");
      setAdjustmentDraft(createAdjustmentDraft(selectedHistoryDocumentQuery.data ?? null, correctionReasons));
      setAdjustmentErrorMessage(null);
      showSuccess(`Ajuste ${correction.folio} registrado correctamente.`);
      await Promise.all([
        queryClient.invalidateQueries({
          queryKey: correctionsBootstrapQueryKey(appEnv.VITE_POS_WORKSTATION_CODE),
        }),
        queryClient.invalidateQueries({
          queryKey: ["corrections", "history", appEnv.VITE_POS_WORKSTATION_CODE],
        }),
        queryClient.invalidateQueries({
          queryKey: ["corrections", "search", appEnv.VITE_POS_WORKSTATION_CODE],
        }),
        selectedHistoryDocumentId
          ? queryClient.invalidateQueries({
              queryKey: correctionTargetDetailQueryKey(
                appEnv.VITE_POS_WORKSTATION_CODE,
                selectedHistoryDocumentId,
              ),
            })
          : Promise.resolve(),
        selectedHistoryDocumentId
          ? queryClient.invalidateQueries({
              queryKey: operationDocumentQueryKey(
                appEnv.VITE_POS_WORKSTATION_CODE,
                selectedHistoryDocumentId,
              ),
            })
          : Promise.resolve(),
        queryClient.invalidateQueries({
          queryKey: operationHistoryQueryKey(
            appEnv.VITE_POS_WORKSTATION_CODE,
            "COUNTER_TRANSFER",
            historyFilters,
          ),
        }),
        queryClient.invalidateQueries({
          queryKey: cashCloseReconciliationQueryKey(appEnv.VITE_POS_WORKSTATION_CODE),
        }),
      ]);
    },
  });

  const isSelectionLoading =
    (draftState.controlState === CONTROL_STATE_CLASS_SELECTION && catalogQuery.isPending) ||
    (draftState.controlState === CONTROL_STATE_PRODUCT_SELECTION && classProductsQuery.isPending);
  const selectionLoadError =
    draftState.controlState === CONTROL_STATE_PRODUCT_SELECTION
      ? classProductsQuery.error
      : catalogQuery.error;
  const showStageBackAction =
    draftState.controlState === CONTROL_STATE_PRODUCT_SELECTION ||
    draftState.controlState === CONTROL_STATE_QUANTITY_CAPTURE;
  const showSearch = draftState.controlState !== CONTROL_STATE_QUANTITY_CAPTURE;
  const activeGridKey = useMemo(() => {
    if (draftState.controlState === CONTROL_STATE_CLASS_SELECTION) {
      return "classes";
    }

    if (
      draftState.controlState === CONTROL_STATE_PRODUCT_SELECTION &&
      draftState.pendingSelection !== null
    ) {
      return `products:${draftState.pendingSelection.productClass.id}`;
    }

    return null;
  }, [draftState.controlState, draftState.pendingSelection]);

  const classGridFocus = useRovingFocusGrid({
    itemCount: sortedClasses.length,
    onActivate: (index) => {
      const productClass = sortedClasses[index];
      if (productClass) {
        updateDraftState((state) => selectClassForOperation(state, productClass));
        setSelectionErrorMessage(null);
      }
    },
  });
  const {
    activeIndex: classActiveIndex,
    focusIndex: focusClassIndex,
    getItemProps: getClassItemProps,
  } = classGridFocus;
  const productGridFocus = useRovingFocusGrid({
    itemCount: sortedProducts.length,
    onActivate: (index) => {
      const product = sortedProducts[index];
      if (product) {
        updateDraftState((state) => selectProductForOperation(state, product));
        setSelectionErrorMessage(null);
      }
    },
  });
  const {
    activeIndex: productActiveIndex,
    focusIndex: focusProductIndex,
    getItemProps: getProductItemProps,
  } = productGridFocus;

  const commitMutationIsPending = commitMutation.isPending;
  const canSubmit =
    accessToken !== null &&
    operationsBootstrapQuery.data !== undefined &&
    lineCount > 0 &&
    !commitMutationIsPending;

  const handleAddLine = useCallback(() => {
    if (
      draftState.pendingSelection !== null &&
      !hasCapturedQuantity(draftState.pendingSelection.quantityText)
    ) {
      setSelectionErrorMessage("Captura una cantidad mayor que cero.");
      return;
    }

    try {
      updateDraftState((state) => addPendingSelectionLine(state));
      setSelectionErrorMessage(null);
    } catch (error) {
      setSelectionErrorMessage(
        toOperationalErrorMessage(
          error,
          "Confirma el producto y la cantidad antes de agregar.",
        ),
      );
    }
  }, [draftState.pendingSelection]);

  const handleCommit = useCallback(() => {
    if (lineCount === 0) {
      showWarning("Agrega al menos un producto para pasar a mostrador.");
      return;
    }

    if (!canSubmit) {
      return;
    }

    setCommitErrorMessage(null);
    commitMutation.mutate();
  }, [canSubmit, commitMutation, lineCount, showWarning]);

  const handleLineQuantityChange = useCallback((lineKey: string, quantityMilliUnits: number) => {
    if (quantityMilliUnits <= 0) {
      showWarning("Captura una cantidad mayor que cero.");
      return;
    }

    updateDraftState((state) => ({
      ...state,
      lines: updateLineQuantity(state.lines, lineKey, quantityMilliUnits),
    }));
  }, [showWarning]);

  const handleLineRemove = useCallback((lineKey: string) => {
    updateDraftState((state) => ({
      ...state,
      lines: removeOperationLine(state.lines, lineKey),
    }));
  }, []);

  const handleLineIncrement = useCallback((line: OperationLine) => {
    handleLineQuantityChange(line.key, line.quantityMilliUnits + 1000);
  }, [handleLineQuantityChange]);

  const handleLineDecrement = useCallback((line: OperationLine) => {
    const nextQuantity = line.quantityMilliUnits - 1000;
    if (nextQuantity <= 0) {
      handleLineRemove(line.key);
      return;
    }

    handleLineQuantityChange(line.key, nextQuantity);
  }, [handleLineQuantityChange, handleLineRemove]);

  const openHistory = useCallback(() => {
    setHistoryScope("CURRENT_SHIFT");
    setHistoryCashierId("ALL");
    setHistoryDaypart("ALL");
    setSelectedHistoryDocumentId(null);
    setCurrentView("history");
  }, []);

  const closeHistory = useCallback(() => {
    setCurrentView("capture");
  }, []);

  const handleHistoryScopeChange = useCallback((scope: string) => {
    setHistoryScope(scope);
    setSelectedHistoryDocumentId(null);
    setHistoryDetailMode("detail");
    setAdjustmentErrorMessage(null);
  }, []);

  const handleHistoryCashierChange = useCallback((cashierId: string) => {
    setHistoryCashierId(cashierId);
    setSelectedHistoryDocumentId(null);
    setHistoryDetailMode("detail");
    setAdjustmentErrorMessage(null);
  }, []);

  const handleHistoryDaypartChange = useCallback((daypart: HistoryDaypartFilter) => {
    setHistoryDaypart((currentDaypart) => (currentDaypart === daypart ? "ALL" : daypart));
    setSelectedHistoryDocumentId(null);
    setHistoryDetailMode("detail");
    setAdjustmentErrorMessage(null);
  }, []);

  const handleHistoryRecordSelect = useCallback((recordId: string) => {
    setSelectedHistoryDocumentId(recordId);
    setHistoryDetailMode("detail");
    setAdjustmentErrorMessage(null);
    setLastCommittedCorrection(null);
  }, []);

  const handleStartHistoryAdjustment = useCallback(() => {
    setAdjustmentDraft(
      createAdjustmentDraft(selectedHistoryDocumentQuery.data ?? null, correctionReasons),
    );
    setAdjustmentErrorMessage(null);
    setLastCommittedCorrection(null);
    setHistoryDetailMode("adjustment");
  }, [correctionReasons, selectedHistoryDocumentQuery.data]);

  const handleCancelHistoryAdjustment = useCallback(() => {
    setAdjustmentDraft(
      createAdjustmentDraft(selectedHistoryDocumentQuery.data ?? null, correctionReasons),
    );
    setAdjustmentErrorMessage(null);
    setHistoryDetailMode("detail");
  }, [correctionReasons, selectedHistoryDocumentQuery.data]);

  useEffect(() => {
    if (draftState.controlState !== CONTROL_STATE_QUANTITY_CAPTURE) {
      return;
    }

    quantityInputRef.current?.focus();
    quantityInputRef.current?.select();
  }, [draftState.controlState, draftState.pendingSelection?.product?.id]);

  useEffect(() => {
    if (activeGridKey === null) {
      lastAutoFocusedGridKeyRef.current = null;
      return;
    }

    if (isSelectionLoading || selectionLoadError) {
      return;
    }

    if (lastAutoFocusedGridKeyRef.current === activeGridKey) {
      return;
    }

    if (draftState.controlState === CONTROL_STATE_CLASS_SELECTION && sortedClasses.length > 0) {
      lastAutoFocusedGridKeyRef.current = activeGridKey;
      focusClassIndex(0);
      return;
    }

    if (draftState.controlState === CONTROL_STATE_PRODUCT_SELECTION && sortedProducts.length > 0) {
      lastAutoFocusedGridKeyRef.current = activeGridKey;
      focusProductIndex(0);
    }
  }, [
    activeGridKey,
    draftState.controlState,
    focusClassIndex,
    focusProductIndex,
    isSelectionLoading,
    selectionLoadError,
    sortedClasses.length,
    sortedProducts.length,
  ]);

  useEffect(() => {
    if (currentView !== "history") {
      return;
    }

    const records = historyQuery.data?.records ?? [];
    if (
      selectedHistoryDocumentId !== null &&
      !records.some((record) => record.id === selectedHistoryDocumentId)
    ) {
      setSelectedHistoryDocumentId(null);
      setHistoryDetailMode("detail");
      setAdjustmentErrorMessage(null);
      return;
    }
  }, [currentView, historyQuery.data?.records, selectedHistoryDocumentId]);

  useEffect(() => {
    function handleKeyboard(event: KeyboardEvent) {
      if (currentView === "history") {
        if (event.key === "Escape" && !isEditableTarget(event.target)) {
          event.preventDefault();
          if (historyDetailMode === "adjustment") {
            handleCancelHistoryAdjustment();
            return;
          }

          if (selectedHistoryDocumentId !== null) {
            setSelectedHistoryDocumentId(null);
            return;
          }

          closeHistory();
        }
        return;
      }

      if (event.ctrlKey && event.key === "Enter") {
        event.preventDefault();
        handleCommit();
        return;
      }

      if (!isEditableTarget(event.target)) {
        if ((event.ctrlKey && event.key.toLowerCase() === "f") || event.key === "/") {
          if (showSearch) {
            event.preventDefault();
            searchInputRef.current?.focus();
            searchInputRef.current?.select();
          }
          return;
        }

        if (event.key === "Escape") {
          if (draftState.controlState !== CONTROL_STATE_CLASS_SELECTION) {
            event.preventDefault();
            updateDraftState(goBackFromOperationalState);
            setSelectionErrorMessage(null);
          } else if (draftState.searchText.length > 0) {
            event.preventDefault();
            updateDraftState((state) => ({ ...state, searchText: "" }));
          }
          return;
        }

        const shortcutIndex = getSelectionShortcutIndex(event.key);
        if (shortcutIndex === null) {
          return;
        }

        if (draftState.controlState === CONTROL_STATE_CLASS_SELECTION) {
          const productClass = sortedClasses[shortcutIndex];
          if (productClass) {
            event.preventDefault();
            updateDraftState((state) => selectClassForOperation(state, productClass));
            setSelectionErrorMessage(null);
          }
          return;
        }

        if (draftState.controlState === CONTROL_STATE_PRODUCT_SELECTION) {
          const product = sortedProducts[shortcutIndex];
          if (product) {
            event.preventDefault();
            updateDraftState((state) => selectProductForOperation(state, product));
            setSelectionErrorMessage(null);
          }
        }
      }
    }

    window.addEventListener("keydown", handleKeyboard);
    return () => window.removeEventListener("keydown", handleKeyboard);
  }, [
    closeHistory,
    currentView,
    draftState.controlState,
    draftState.searchText.length,
    handleCancelHistoryAdjustment,
    handleCommit,
    historyDetailMode,
    selectedHistoryDocumentId,
    showSearch,
    sortedClasses,
    sortedProducts,
  ]);

  const rightPanelContent =
    operationsBootstrapQuery.data &&
    currentCashSessionQuery.data &&
    currentView === "history" &&
    selectedHistoryDocumentId !== null ? (
      <CounterTransferHistoryDetailRightPanel
        adjustmentDraft={adjustmentDraft}
        adjustmentErrorMessage={adjustmentErrorMessage}
        adjustmentInvalidLineCount={adjustmentInvalidLineCount}
        adjustmentMode={historyDetailMode === "adjustment"}
        adjustmentSaveDisabled={
          adjustmentMutation.isPending ||
          correctionsBootstrapQuery.isPending ||
          correctionReasons.length === 0 ||
          adjustmentDraft.reasonCode.trim().length === 0 ||
          adjustmentActiveLines.length === 0 ||
          adjustmentInvalidLineCount > 0 ||
          (isAdjustmentHighImpact && !adjustmentDraft.highImpactAcknowledged)
        }
        document={selectedHistoryDocumentQuery.data ?? null}
        error={selectedHistoryDocumentQuery.error}
        isAdjustmentHighImpact={isAdjustmentHighImpact}
        isLoading={selectedHistoryDocumentQuery.isPending}
        isSavingAdjustment={adjustmentMutation.isPending}
        lastCommittedCorrection={lastCommittedCorrection}
        onAdjustmentDraftChange={setAdjustmentDraft}
        onCancelAdjustment={handleCancelHistoryAdjustment}
        onRetry={() => void selectedHistoryDocumentQuery.refetch()}
        onSaveAdjustment={() => adjustmentMutation.mutate()}
        onShowCounterState={() => {
          setSelectedHistoryDocumentId(null);
          setHistoryDetailMode("detail");
          setAdjustmentErrorMessage(null);
        }}
        onStartAdjustment={handleStartHistoryAdjustment}
        timeZone={operationsBootstrapQuery.data.branch.timezone}
      />
    ) : operationsBootstrapQuery.data && currentCashSessionQuery.data && currentView === "history" ? (
      <CounterTransferCounterStateRightPanel
        counterAvailabilityQuery={counterAvailabilityQuery}
        onBackToCapture={closeHistory}
      />
    ) : operationsBootstrapQuery.data && currentCashSessionQuery.data ? (
      <CounterTransferRightPanel
        canSubmit={canSubmit}
        commitErrorMessage={commitErrorMessage}
        isSubmitting={commitMutationIsPending}
        isCounterStateOpen={isCaptureCounterStateOpen}
        lastCommittedDocument={lastCommittedDocument}
        lines={draftState.lines}
        notes={notes}
        counterAvailabilityQuery={counterAvailabilityQuery}
        onCommit={handleCommit}
        onLineDecrement={handleLineDecrement}
        onLineIncrement={handleLineIncrement}
        onLineQuantityChange={handleLineQuantityChange}
        onLineRemove={handleLineRemove}
        onNotesChange={(value) => {
          setNotes(value.slice(0, NOTE_MAX_LENGTH));
          setLastCommittedDocument(null);
        }}
        onOpenHistory={openHistory}
        onQuantityInvalid={(message) => showWarning(message)}
        onToggleCounterState={() => setIsCaptureCounterStateOpen((current) => !current)}
      />
    ) : null;
  useAppShellRightPanel(rightPanelContent);

  if (operationsBootstrapQuery.isPending || currentCashSessionQuery.isPending) {
    return (
      <PosLoadingState
        description="Consultando el contexto operativo de esta estacion."
        title="Cargando mostrador"
      />
    );
  }

  if (operationsBootstrapQuery.error) {
    return (
      <PosErrorState
        action={
          <Button className={posPrimaryButtonClass} onClick={() => operationsBootstrapQuery.refetch()}>
            Reintentar
          </Button>
        }
        description={toOperationalErrorMessage(
          operationsBootstrapQuery.error,
          "Confirma la estacion POS y el catalogo operativo.",
        )}
        title="Pasar a mostrador no esta disponible"
      />
    );
  }

  if (currentCashSessionQuery.error) {
    return (
      <PosErrorState
        action={
          <Button className={posPrimaryButtonClass} onClick={() => currentCashSessionQuery.refetch()}>
            Reintentar
          </Button>
        }
        description={toOperationalErrorMessage(
          currentCashSessionQuery.error,
          "Confirma el estado actual de caja.",
        )}
        title="No fue posible consultar la caja"
      />
    );
  }

  if (!currentCashSessionQuery.data) {
    return <Navigate to="/cash-session/open" />;
  }

  return (
    <div className="grid gap-2.5 lg:h-full lg:grid-rows-[minmax(0,1fr)]">
      {currentView === "history" ? (
        <CounterTransferHistoryWorkspace
          historyQuery={historyQuery}
          historyCashierId={historyCashierId}
          historyDaypart={historyDaypart}
          historyScope={historyScope}
          onBackToCapture={closeHistory}
          onCashierChange={handleHistoryCashierChange}
          onDaypartChange={handleHistoryDaypartChange}
          onRecordSelect={handleHistoryRecordSelect}
          onScopeChange={handleHistoryScopeChange}
          selectedRecordId={selectedHistoryDocumentId}
          timeZone={operationsBootstrapQuery.data.branch.timezone}
        />
      ) : (
        <CentralWorkspaceSheet
        className="lg:h-full"
        contentClassName="min-h-0 overflow-y-auto px-3 pb-3 pt-2"
        header={
          <CompactPageHeader
            activeStep={getActiveStep(draftState)}
            flowSteps={[
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
            ]}
            flowVariant="process"
            secondaryChips={
              lineCount > 0 ? (
                <ModuleStateChip tone="primary">{totalUnitsText} unidades</ModuleStateChip>
              ) : null
            }
            stateChip={
              <ModuleStateChip tone={getTransferStateTone(lineCount, commitMutationIsPending)}>
                {getTransferStateLabel(lineCount, commitMutationIsPending)}
              </ModuleStateChip>
            }
            title="Pasar a mostrador"
          />
        }
        toolbar={
          showStageBackAction || showSearch ? (
            <div className="flex min-w-0 flex-wrap items-center justify-between gap-3">
              <div className="flex min-w-0 items-center gap-2">
                {showStageBackAction ? (
                  <Button
                    aria-label="Regresar"
                    className={cn("h-10 px-3", posOutlineButtonClass)}
                    onClick={() => {
                      updateDraftState(goBackFromOperationalState);
                      setSelectionErrorMessage(null);
                    }}
                    title="Regresar"
                    type="button"
                  >
                    <ArrowLeftIcon className="h-4 w-4" />
                  </Button>
                ) : null}
              </div>

              {showSearch ? (
                <div className="flex min-w-0 flex-1 justify-end">
                  <SearchField
                    ariaLabel="Buscar en mostrador"
                    className="w-full max-w-sm"
                    inputClassName={cn("h-9 rounded-lg text-sm shadow-sm", posInputClass)}
                    inputRef={searchInputRef}
                    onChange={(value) => {
                      updateDraftState((state) => ({ ...state, searchText: value }));
                      setSelectionErrorMessage(null);
                    }}
                    placeholder={
                      draftState.controlState === CONTROL_STATE_PRODUCT_SELECTION
                        ? "Filtrar producto"
                        : "Filtrar clase"
                    }
                    value={draftState.searchText}
                  />
                </div>
              ) : null}
            </div>
          ) : undefined
        }
        toolbarClassName="py-2"
      >
        {isSelectionLoading ? (
          <PosLoadingState description="Cargando catalogo operativo." title="Cargando seleccion" />
        ) : null}

        {!isSelectionLoading && selectionLoadError ? (
          <PosErrorState
            action={
              <Button
                className={posPrimaryButtonClass}
                onClick={() =>
                  draftState.controlState === CONTROL_STATE_PRODUCT_SELECTION
                    ? classProductsQuery.refetch()
                    : catalogQuery.refetch()
                }
                type="button"
              >
                Reintentar
              </Button>
            }
            description={toOperationalErrorMessage(
              selectionLoadError,
              "Confirma la disponibilidad del catalogo.",
            )}
            title="La seleccion no esta disponible"
          />
        ) : null}

        {selectionErrorMessage && draftState.controlState !== CONTROL_STATE_QUANTITY_CAPTURE ? (
          <div className="mb-2">
            <PosInlineValidationMessage tone="error">{selectionErrorMessage}</PosInlineValidationMessage>
          </div>
        ) : null}

        {!isSelectionLoading &&
        !selectionLoadError &&
        draftState.controlState === CONTROL_STATE_CLASS_SELECTION ? (
          sortedClasses.length > 0 ? (
            <div className="grid gap-2.5">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <p className="text-xs font-medium text-slate-500">
                  Numero: seleccionar clase / Enter: seleccionar / Esc: limpiar busqueda
                </p>
              </div>
              <div className="grid gap-2.5 sm:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4">
                {sortedClasses.map((productClass, index) => {
                  const itemProps = getClassItemProps(index);

                  return (
                    <CatalogSelectionCard
                      buttonRef={itemProps.ref as Ref<HTMLButtonElement>}
                      code={productClass.code}
                      isActive={classActiveIndex === index}
                      key={productClass.id}
                      name={productClass.name}
                      onCardFocus={itemProps.onFocus}
                      onCardKeyDown={itemProps.onKeyDown}
                      onSelect={() => {
                        updateDraftState((state) => selectClassForOperation(state, productClass));
                        setSelectionErrorMessage(null);
                      }}
                      priceText={null}
                      shortcutLabel={getSelectionShortcutLabel(index)}
                      tabIndex={itemProps.tabIndex}
                      variant="pos"
                    />
                  );
                })}
              </div>
            </div>
          ) : (
            <SelectionEmptyState text="No hay clases para esta busqueda." />
          )
        ) : null}

        {!isSelectionLoading &&
        !selectionLoadError &&
        draftState.controlState === CONTROL_STATE_PRODUCT_SELECTION ? (
          sortedProducts.length > 0 ? (
            <div className="grid gap-2.5">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="flex min-w-0 flex-wrap items-center gap-2 text-xs text-slate-500">
                  <span className="font-medium text-slate-700">
                    {draftState.pendingSelection?.productClass.name}
                  </span>
                </div>
                <p className="text-xs font-medium text-slate-500">
                  Numero: seleccionar producto / Esc: volver
                </p>
              </div>
              <div className="grid gap-2.5 sm:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4">
                {sortedProducts.map((product, index) => {
                  const itemProps = getProductItemProps(index);

                  return (
                    <CatalogSelectionCard
                      buttonRef={itemProps.ref as Ref<HTMLButtonElement>}
                      code={product.code}
                      isActive={productActiveIndex === index}
                      key={product.id}
                      name={product.name}
                      onCardFocus={itemProps.onFocus}
                      onCardKeyDown={itemProps.onKeyDown}
                      onSelect={() => {
                        updateDraftState((state) => selectProductForOperation(state, product));
                        setSelectionErrorMessage(null);
                      }}
                      priceText={null}
                      shortcutLabel={getSelectionShortcutLabel(index)}
                      tabIndex={itemProps.tabIndex}
                      variant="pos"
                    />
                  );
                })}
              </div>
            </div>
          ) : (
            <SelectionEmptyState text="No hay productos para esta busqueda." />
          )
        ) : null}

        {draftState.controlState === CONTROL_STATE_QUANTITY_CAPTURE &&
        draftState.pendingSelection?.product ? (
          <QuantityCapturePanel
            inputRef={quantityInputRef}
            onAdd={handleAddLine}
            onBack={() => {
              updateDraftState(goBackFromOperationalState);
              setSelectionErrorMessage(null);
            }}
            onDecrement={() => updateDraftState(decrementPendingOperationQuantity)}
            onIncrement={() => updateDraftState(incrementPendingOperationQuantity)}
            onQuantityChange={(value) =>
              updateDraftState((state) => setPendingQuantityText(state, value))
            }
            productClassName={draftState.pendingSelection.productClass.name}
            productCode={draftState.pendingSelection.product.code}
            productName={draftState.pendingSelection.product.name}
            quantityText={draftState.pendingSelection.quantityText}
            selectionErrorMessage={selectionErrorMessage}
            setQuantity={(value) =>
              updateDraftState((state) => setPendingQuantityText(state, value))
            }
          />
        ) : null}
      </CentralWorkspaceSheet>
      )}
    </div>
  );
}

function SelectionEmptyState({ text }: { text: string }) {
  return (
    <div className="rounded-xl border border-dashed border-[var(--pos-shell-border)] bg-[var(--pos-shell-muted)] px-4 py-8 text-center text-sm text-slate-600">
      {text}
    </div>
  );
}

function QuantityCapturePanel({
  inputRef,
  onAdd,
  onBack,
  onDecrement,
  onIncrement,
  onQuantityChange,
  productClassName,
  productCode,
  productName,
  quantityText,
  selectionErrorMessage,
  setQuantity,
}: {
  inputRef: Ref<HTMLInputElement>;
  onAdd: () => void;
  onBack: () => void;
  onDecrement: () => void;
  onIncrement: () => void;
  onQuantityChange: (value: string) => void;
  productClassName: string;
  productCode: string;
  productName: string;
  quantityText: string;
  selectionErrorMessage: string | null;
  setQuantity: (value: string) => void;
}) {
  const quantityPresets = ["1", "2", "3", "6", "12"];
  const isQuantityReady = hasCapturedQuantity(quantityText);

  return (
    <div className="w-full max-w-5xl justify-self-center rounded-xl border border-[var(--pos-shell-border)] bg-white p-3 shadow-sm">
      <div className="grid gap-3 lg:grid-cols-[12rem_minmax(0,1fr)]">
        <CatalogVisual className="min-h-[11.5rem]" code={productCode} name={productName} />

        <div className="grid gap-2.5">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div className="min-w-0">
              <p className="truncate text-base font-semibold text-slate-950">{productName}</p>
              <p className="mt-1 text-sm text-slate-600">{productClassName}</p>
            </div>
          </div>

          <div className="grid gap-2">
            <input
              aria-label="Cantidad"
              className={cn(
                "h-16 rounded-xl px-4 text-[2.25rem] font-semibold shadow-sm",
                posInputClass,
              )}
              inputMode="decimal"
              onChange={(event) => onQuantityChange(event.target.value)}
              onKeyDown={(event) => {
                if (isNumpadSubmitKey(event)) {
                  event.preventDefault();
                  onAdd();
                }

                if (event.key === "Escape") {
                  event.preventDefault();
                  onBack();
                }

                if (event.key === "Delete") {
                  event.preventDefault();
                  setQuantity("");
                }
              }}
              placeholder="0"
              ref={inputRef}
              value={quantityText}
            />

            <div className="flex flex-wrap items-center gap-2">
              <Button className={cn("h-10 px-3", posOutlineButtonClass)} onClick={onDecrement} type="button">
                -1
              </Button>
              <Button className={cn("h-10 px-3", posOutlineButtonClass)} onClick={onIncrement} type="button">
                +1
              </Button>
              {quantityPresets.map((preset) => (
                <Button
                  className={cn("h-10 min-w-12 px-3", posOutlineButtonClass)}
                  key={preset}
                  onClick={() => setQuantity(preset)}
                  type="button"
                >
                  {preset}
                </Button>
              ))}
            </div>

            <div className="flex flex-wrap items-center justify-end gap-3">
              <Button
                className={cn("h-10 px-4", posPrimaryButtonClass)}
                disabled={!isQuantityReady}
                onClick={onAdd}
                type="button"
              >
                Agregar al traspaso
              </Button>
            </div>

            {selectionErrorMessage ? (
              <PosInlineValidationMessage tone="error">{selectionErrorMessage}</PosInlineValidationMessage>
            ) : null}
          </div>
        </div>
      </div>
    </div>
  );
}

function CounterTransferRightPanel({
  canSubmit,
  commitErrorMessage,
  counterAvailabilityQuery,
  isSubmitting,
  isCounterStateOpen,
  lastCommittedDocument,
  lines,
  notes,
  onCommit,
  onLineDecrement,
  onLineIncrement,
  onLineQuantityChange,
  onLineRemove,
  onNotesChange,
  onOpenHistory,
  onQuantityInvalid,
  onToggleCounterState,
}: {
  canSubmit: boolean;
  commitErrorMessage: string | null;
  counterAvailabilityQuery: {
    data?: CashCloseReconciliationResponse;
    error: unknown;
    isPending: boolean;
    refetch: () => unknown;
  };
  isSubmitting: boolean;
  isCounterStateOpen: boolean;
  lastCommittedDocument: OperationDocumentView | null;
  lines: OperationLine[];
  notes: string;
  onCommit: () => void;
  onLineDecrement: (line: OperationLine) => void;
  onLineIncrement: (line: OperationLine) => void;
  onLineQuantityChange: (lineKey: string, quantityMilliUnits: number) => void;
  onLineRemove: (lineKey: string) => void;
  onNotesChange: (value: string) => void;
  onOpenHistory: () => void;
  onQuantityInvalid: (message: string) => void;
  onToggleCounterState: () => void;
}) {
  const [isObservationOpen, setIsObservationOpen] = useState(() => notes.trim().length > 0);
  const hasObservation = notes.trim().length > 0;

  useEffect(() => {
    if (!hasObservation) {
      setIsObservationOpen(false);
    }
  }, [hasObservation]);

  return (
    <aside className="pos-shell-panel grid h-full min-h-0 grid-rows-[auto_minmax(0,1fr)_auto] gap-3 px-3.5 py-3">
      <div className="flex min-w-0 items-start justify-between gap-3">
        <div className="min-w-0">
          <h2 className="truncate text-[1.05rem] font-semibold tracking-tight text-slate-950">
            Pasar a mostrador
          </h2>
          <p className="mt-1 text-sm font-medium text-slate-600">Destino: Mostrador</p>
        </div>
        <ModuleStateChip tone={lines.length > 0 ? "primary" : "muted"}>
          {lines.length} {lines.length === 1 ? "linea" : "lineas"}
        </ModuleStateChip>
      </div>

      <ScrollPane className="min-h-0">
        <div className="grid gap-3">
          <RightPanelBlock title="Productos">
            {lines.length > 0 ? (
              <CapturedProductLineList>
                {lines.map((line) => (
                  <TransferSummaryLineRow
                    key={line.key}
                    line={line}
                    onDecrement={() => onLineDecrement(line)}
                    onIncrement={() => onLineIncrement(line)}
                    onQuantityChange={(quantityMilliUnits) =>
                      onLineQuantityChange(line.key, quantityMilliUnits)
                    }
                    onQuantityInvalid={onQuantityInvalid}
                    onRemove={() => onLineRemove(line.key)}
                  />
                ))}
              </CapturedProductLineList>
            ) : (
              <div className="rounded-lg border border-dashed border-[var(--pos-shell-border)] bg-white px-3 py-5 text-center text-sm font-medium text-slate-500">
                Sin productos seleccionados.
              </div>
            )}
          </RightPanelBlock>

          <CounterStateDisclosure
            counterAvailabilityQuery={counterAvailabilityQuery}
            isOpen={isCounterStateOpen}
            onToggle={onToggleCounterState}
          />

          <RightPanelBlock title="Observación" tone="muted">
            <button
              className="flex w-full items-center justify-between gap-3 rounded-lg border border-[var(--pos-shell-border)] bg-white px-3 py-2 text-left text-sm font-semibold text-slate-950 transition hover:bg-[var(--pos-shell-muted)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--pos-ring)]"
              onClick={() => setIsObservationOpen((current) => !current)}
              type="button"
            >
              <span className="min-w-0 truncate">
                {isObservationOpen ? "Ocultar observación" : "Agregar observación"}
              </span>
              {hasObservation ? (
                <span className="pos-chip shrink-0" data-tone="muted">
                  Con texto
                </span>
              ) : null}
            </button>
            {isObservationOpen ? (
              <textarea
                aria-label="Observación del movimiento"
                className={cn(
                  "mt-2 min-h-16 w-full resize-none rounded-lg px-3 py-2 text-sm",
                  posInputClass,
                )}
                maxLength={NOTE_MAX_LENGTH}
                onChange={(event) => onNotesChange(event.target.value)}
                placeholder="Opcional"
                value={notes}
              />
            ) : null}
          </RightPanelBlock>

          {commitErrorMessage ? (
            <PosInlineValidationMessage tone="error">{commitErrorMessage}</PosInlineValidationMessage>
          ) : null}

          {lastCommittedDocument ? (
            <div className="flex items-center gap-2 rounded-lg border border-[rgba(18,122,90,0.16)] bg-[var(--ui-color-success-soft)] px-3 py-2 text-sm font-medium text-[var(--ui-color-success)]">
              <CheckCircleIcon className="h-4 w-4 shrink-0" />
              <span className="min-w-0 truncate">Ultimo movimiento: {lastCommittedDocument.folio}</span>
            </div>
          ) : null}
        </div>
      </ScrollPane>

      <div className="grid gap-2">
        <Button
          className={cn("h-10 w-full px-4", posOutlineButtonClass)}
          onClick={onOpenHistory}
          type="button"
        >
          <RotateCcwIcon className="h-4 w-4" />
          Historial
        </Button>
        <Button
          className={cn("h-12 w-full px-4 text-base", posPrimaryButtonClass)}
          disabled={!canSubmit}
          onClick={onCommit}
          type="button"
        >
          {isSubmitting ? "Registrando..." : "Pasar a Mostrador"}
        </Button>
      </div>
    </aside>
  );
}

function CounterTransferHistoryWorkspace({
  historyCashierId,
  historyDaypart,
  historyQuery,
  historyScope,
  onBackToCapture,
  onCashierChange,
  onDaypartChange,
  onRecordSelect,
  onScopeChange,
  selectedRecordId,
  timeZone,
}: {
  historyCashierId: string;
  historyDaypart: HistoryDaypartFilter;
  historyQuery: {
    data?: OperationHistoryResponse;
    error: unknown;
    isPending: boolean;
    refetch: () => unknown;
  };
  historyScope: string;
  onBackToCapture: () => void;
  onCashierChange: (cashierId: string) => void;
  onDaypartChange: (daypart: HistoryDaypartFilter) => void;
  onRecordSelect: (recordId: string) => void;
  onScopeChange: (scope: string) => void;
  selectedRecordId: string | null;
  timeZone: string;
}) {
  const allRecords = historyQuery.data?.records ?? [];
  const records =
    historyDaypart === "ALL"
      ? allRecords
      : allRecords.filter(
          (record) => getHistoryRecordDaypart(record, timeZone) === historyDaypart,
        );
  const availableCashiers = historyQuery.data?.available_users ?? [];
  const availableScopes =
    historyQuery.data?.available_scopes && historyQuery.data.available_scopes.length > 0
      ? historyQuery.data.available_scopes
      : [
          { code: "ALL", label: "Todos" },
          { code: "CURRENT_SHIFT", label: "Turno" },
          { code: "TODAY", label: "Hoy" },
          { code: "RECENT", label: "Recientes" },
        ];

  return (
    <CentralWorkspaceSheet
      className="lg:h-full"
      contentClassName="min-h-0 overflow-hidden px-3 pb-3 pt-2"
      header={
        <CompactPageHeader
          secondaryChips={
            <ModuleStateChip tone="muted">{records.length} folios</ModuleStateChip>
          }
          stateChip={<ModuleStateChip tone="primary">Historial</ModuleStateChip>}
          title="Historial a mostrador"
        />
      }
      toolbar={
        <div className="flex min-w-0 flex-wrap items-center justify-between gap-3">
          <div className="flex min-w-0 flex-wrap items-center gap-2">
            <Button
              className={cn("h-10 px-3", posOutlineButtonClass)}
              onClick={onBackToCapture}
              type="button"
            >
              <ArrowLeftIcon className="h-4 w-4" />
              Captura
            </Button>
            {availableScopes.map((scope) => (
              <Button
                className={cn(
                  "h-10 px-3 text-sm",
                  scope.code === historyScope ? posPrimaryButtonClass : posOutlineButtonClass,
                )}
                key={scope.code}
                onClick={() => onScopeChange(scope.code)}
                type="button"
              >
                {getHistoryScopeLabel(scope.code)}
              </Button>
            ))}
            {HISTORY_DAYPART_FILTERS.map((daypart) => (
              <Button
                aria-pressed={historyDaypart === daypart}
                className={cn(
                  "h-10 px-3 text-sm",
                  historyDaypart === daypart ? posPrimaryButtonClass : posOutlineButtonClass,
                )}
                key={daypart}
                onClick={() => onDaypartChange(daypart)}
                type="button"
              >
                {getHistoryDaypartLabel(daypart)}
              </Button>
            ))}
          </div>
          <div className="flex min-w-0 flex-wrap items-center gap-2">
            <select
              aria-label="Filtrar por cajero"
              className={cn("h-10 min-w-[12rem] rounded-lg px-3 text-sm font-medium", posInputClass)}
              onChange={(event) => onCashierChange(event.target.value)}
              value={historyCashierId}
            >
              <option value="ALL">Todos los cajeros</option>
              {availableCashiers.map((cashier) => (
                <option key={cashier.value} value={cashier.value}>
                  {cashier.label}
                </option>
              ))}
            </select>
            <Button
              className={cn("h-10 px-3 text-sm", posOutlineButtonClass)}
              onClick={() => void historyQuery.refetch()}
              type="button"
            >
              Actualizar
            </Button>
          </div>
        </div>
      }
      toolbarClassName="py-2"
    >
      <div className="grid h-full min-h-0">
        {historyQuery.isPending ? (
          <PosLoadingState description="Consultando movimientos." title="Cargando historial" />
        ) : historyQuery.error ? (
          <PosErrorState
            action={
              <Button
                className={posPrimaryButtonClass}
                onClick={() => void historyQuery.refetch()}
                type="button"
              >
                Reintentar
              </Button>
            }
            description={toOperationalErrorMessage(
              historyQuery.error,
              "No fue posible consultar el historial.",
            )}
            title="Historial no disponible"
          />
        ) : (
          <CounterTransferHistoryTable
            onRecordSelect={onRecordSelect}
            records={records}
            selectedRecordId={selectedRecordId}
            timeZone={timeZone}
          />
        )}
      </div>
    </CentralWorkspaceSheet>
  );
}

function CounterTransferHistoryTable({
  onRecordSelect,
  records,
  selectedRecordId,
  timeZone,
}: {
  onRecordSelect: (recordId: string) => void;
  records: OperationHistoryResponse["records"];
  selectedRecordId: string | null;
  timeZone: string;
}) {
  function focusRelativeRow(row: HTMLTableRowElement, offset: number) {
    const rows = Array.from(
      row.parentElement?.querySelectorAll<HTMLTableRowElement>("[data-history-row-index]") ?? [],
    );
    const currentIndex = rows.indexOf(row);
    const nextRow = rows[currentIndex + offset];
    nextRow?.focus();
  }

  function handleRowKeyDown(
    event: ReactKeyboardEvent<HTMLTableRowElement>,
    recordId: string,
  ) {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      onRecordSelect(recordId);
      return;
    }

    if (event.key === "ArrowDown") {
      event.preventDefault();
      focusRelativeRow(event.currentTarget, 1);
      return;
    }

    if (event.key === "ArrowUp") {
      event.preventDefault();
      focusRelativeRow(event.currentTarget, -1);
    }
  }

  return (
    <div className="min-h-0 overflow-hidden rounded-xl border border-[var(--pos-shell-border)] bg-white shadow-sm">
      <div className="h-full min-h-0 overflow-auto">
        <table
          aria-label="Historial de movimientos a mostrador"
          className="w-full min-w-[650px] table-fixed text-left text-sm"
        >
          <colgroup>
            <col className="w-[8.5rem]" />
            <col className="w-[9.25rem]" />
            <col className="w-[18rem]" />
            <col className="w-[5.75rem]" />
            <col className="w-[7.25rem]" />
          </colgroup>
          <thead className="sticky top-0 z-10 border-b border-[var(--pos-shell-border)] bg-[var(--pos-shell-muted)] text-[11px] font-semibold uppercase tracking-[0.08em] text-slate-500">
            <tr>
              <th className="px-3 py-2.5">Folio</th>
              <th className="px-3 py-2.5">Fecha/hora</th>
              <th className="px-3 py-2.5">Cajero</th>
              <th className="px-3 py-2.5 text-right">Unidades</th>
              <th className="px-3 py-2.5">Estado</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[var(--pos-shell-border)]">
            {records.length === 0 ? (
              <tr>
                <td
                  className="px-3 py-8 text-center text-sm font-medium text-slate-500"
                  colSpan={5}
                >
                  No hay movimientos para este filtro.
                </td>
              </tr>
            ) : (
              records.map((record, index) => {
                const isSelected = record.id === selectedRecordId;

                return (
                  <tr
                    aria-label={`Seleccionar movimiento ${record.folio}`}
                    aria-selected={isSelected}
                    className={cn(
                      "cursor-pointer transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-[var(--pos-ring)]",
                      isSelected
                        ? "bg-[var(--pos-primary-soft)] shadow-[inset_3px_0_0_var(--pos-primary)]"
                        : "hover:bg-slate-50",
                    )}
                    data-history-row-index={index}
                    key={record.id}
                    onClick={() => onRecordSelect(record.id)}
                    onKeyDown={(event) => handleRowKeyDown(event, record.id)}
                    role="button"
                    tabIndex={0}
                  >
                    <td className="px-3 py-2.5">
                      <span className="block truncate font-semibold text-slate-950">
                        {record.folio}
                      </span>
                    </td>
                    <td className="px-3 py-2.5 text-xs font-medium text-slate-600">
                      {formatCompactLocalDateTime(getHistoryRecordTimestamp(record), timeZone)}
                    </td>
                    <td className="px-3 py-2.5">
                      <span className="block truncate font-medium text-slate-700">
                        {record.created_by_user_full_name}
                      </span>
                    </td>
                    <td className="px-3 py-2.5 text-right font-semibold text-slate-950 [font-variant-numeric:tabular-nums]">
                      {getHistoryRecordUnits(record)}
                    </td>
                    <td className="px-3 py-2.5">
                      <span className="pos-chip whitespace-nowrap" data-tone="muted">
                        {getHistoryStatusLabel(record.status)}
                      </span>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function CounterTransferHistoryDetailRightPanel({
  adjustmentDraft,
  adjustmentErrorMessage,
  adjustmentInvalidLineCount,
  adjustmentMode,
  adjustmentSaveDisabled,
  document,
  error,
  isAdjustmentHighImpact,
  isLoading,
  isSavingAdjustment,
  lastCommittedCorrection,
  onAdjustmentDraftChange,
  onCancelAdjustment,
  onRetry,
  onSaveAdjustment,
  onShowCounterState,
  onStartAdjustment,
  timeZone,
}: {
  adjustmentDraft: CounterTransferAdjustmentDraft;
  adjustmentErrorMessage: string | null;
  adjustmentInvalidLineCount: number;
  adjustmentMode: boolean;
  adjustmentSaveDisabled: boolean;
  document: OperationDocumentView | null;
  error: unknown;
  isAdjustmentHighImpact: boolean;
  isLoading: boolean;
  isSavingAdjustment: boolean;
  lastCommittedCorrection: CorrectionDocumentView | null;
  onAdjustmentDraftChange: (draft: CounterTransferAdjustmentDraft) => void;
  onCancelAdjustment: () => void;
  onRetry: () => void;
  onSaveAdjustment: () => void;
  onShowCounterState: () => void;
  onStartAdjustment: () => void;
  timeZone: string;
}) {
  return (
    <aside className="pos-shell-panel grid h-full min-h-0 grid-rows-[auto_minmax(0,1fr)_auto] gap-3 px-3.5 py-3">
      <div className="flex min-w-0 items-start justify-between gap-3">
        <div className="min-w-0">
          <h2 className="truncate text-[1.05rem] font-semibold tracking-tight text-slate-950">
            Detalle de movimiento
          </h2>
          <p className="mt-1 truncate text-sm font-medium text-slate-600">
            {document?.folio ?? "Pasar a mostrador"}
          </p>
        </div>
        {document ? (
          <ModuleStateChip tone="primary">{getHistoryStatusLabel(document.status)}</ModuleStateChip>
        ) : null}
      </div>

      <ScrollPane className="min-h-0">
        {isLoading ? (
          <PosLoadingState description="Consultando el movimiento." title="Cargando detalle" />
        ) : error ? (
          <PosErrorState
            action={
              <Button className={posPrimaryButtonClass} onClick={onRetry} type="button">
                Reintentar
              </Button>
            }
            description={toOperationalErrorMessage(
              error,
              "No fue posible consultar el movimiento seleccionado.",
            )}
            title="Movimiento no disponible"
          />
        ) : document ? (
          <CounterTransferMovementDetail
            adjustmentDraft={adjustmentDraft}
            adjustmentErrorMessage={adjustmentErrorMessage}
            adjustmentInvalidLineCount={adjustmentInvalidLineCount}
            adjustmentMode={adjustmentMode}
            document={document}
            isAdjustmentHighImpact={isAdjustmentHighImpact}
            lastCommittedCorrection={lastCommittedCorrection}
            onAdjustmentDraftChange={onAdjustmentDraftChange}
            timeZone={timeZone}
          />
        ) : (
          <div className="rounded-lg border border-dashed border-[var(--pos-shell-border)] bg-white px-3 py-8 text-center text-sm font-medium text-slate-500">
            Movimiento no disponible.
          </div>
        )}
      </ScrollPane>

      <div className="grid gap-2">
        {adjustmentMode ? (
          <>
            <Button
              className={cn("h-11 w-full px-4", posPrimaryButtonClass)}
              disabled={adjustmentSaveDisabled}
              onClick={onSaveAdjustment}
              type="button"
            >
              {isSavingAdjustment ? "Registrando..." : "Guardar ajuste"}
            </Button>
            <Button
              className={cn("h-10 w-full px-4", posOutlineButtonClass)}
              disabled={isSavingAdjustment}
              onClick={onCancelAdjustment}
              type="button"
            >
              Cancelar
            </Button>
          </>
        ) : (
          <>
            <Button
              className={cn("h-11 w-full px-4", posPrimaryButtonClass)}
              disabled={!document}
              onClick={onStartAdjustment}
              type="button"
            >
              Aplicar ajuste
            </Button>
            <Button
              className={cn("h-10 w-full px-4", posOutlineButtonClass)}
              onClick={onShowCounterState}
              type="button"
            >
              Mostrar mostrador actual
            </Button>
          </>
        )}
      </div>
    </aside>
  );
}

function CounterTransferMovementDetail({
  adjustmentDraft,
  adjustmentErrorMessage,
  adjustmentInvalidLineCount,
  adjustmentMode,
  document,
  isAdjustmentHighImpact,
  lastCommittedCorrection,
  onAdjustmentDraftChange,
  timeZone,
}: {
  adjustmentDraft: CounterTransferAdjustmentDraft;
  adjustmentErrorMessage: string | null;
  adjustmentInvalidLineCount: number;
  adjustmentMode: boolean;
  document: OperationDocumentView;
  isAdjustmentHighImpact: boolean;
  lastCommittedCorrection: CorrectionDocumentView | null;
  onAdjustmentDraftChange: (draft: CounterTransferAdjustmentDraft) => void;
  timeZone: string;
}) {
  const changedLineCount = getAdjustmentDraftChangedLines(adjustmentDraft).length;
  const hasNoAdjustmentChanges =
    adjustmentMode && adjustmentInvalidLineCount === 0 && changedLineCount === 0;
  const totalUnitsText = adjustmentMode
    ? formatQuantityFromMilliUnits(
        document.lines.reduce((sum, line) => {
          const draftLine = adjustmentDraft.lines.find((item) => item.lineId === line.id);
          const parsedQuantity = draftLine
            ? parseInlineAdjustmentQuantityToMilliUnits(draftLine.quantityText)
            : null;

          return sum + (parsedQuantity ?? Math.round(Number(line.quantity) * 1000));
        }, 0),
      )
    : getDocumentTotalUnits(document);

  return (
    <div className="grid gap-3">
      <RightPanelBlock title="Movimiento">
        <div className="grid gap-2 text-sm">
          <MovementDetailRow label="Folio" value={document.folio} />
          <MovementDetailRow
            label="Fecha/hora"
            value={formatCompactLocalDateTime(
              document.committed_at_utc ?? document.created_at_utc,
              timeZone,
            )}
          />
          <MovementDetailRow label="Cajero" value={document.created_by_user_full_name} />
          <MovementDetailRow label="Estacion" value={document.workstation_name} />
          <MovementDetailRow label="Lineas" value={String(document.lines.length)} />
          <MovementDetailRow label="Unidades" value={totalUnitsText} />
        </div>
      </RightPanelBlock>

      <RightPanelBlock title="Productos">
        <div className="overflow-hidden rounded-lg border border-[var(--pos-shell-border)] bg-white">
          {document.lines.map((line) => {
            const draftLine = adjustmentDraft.lines.find((item) => item.lineId === line.id);
            return (
              <CounterTransferMovementProductRow
                adjustmentMode={adjustmentMode}
                draftLine={draftLine}
                key={line.id}
                line={line}
                onDraftLineChange={(nextLine) =>
                  onAdjustmentDraftChange({
                    ...adjustmentDraft,
                    lines: adjustmentDraft.lines.map((item) =>
                      item.lineId === nextLine.lineId ? nextLine : item,
                    ),
                  })
                }
              />
            );
          })}
        </div>
      </RightPanelBlock>

      {adjustmentMode && hasNoAdjustmentChanges ? (
        <PosInlineValidationMessage tone="warning">
          No hay cambios para guardar.
        </PosInlineValidationMessage>
      ) : null}

      {adjustmentInvalidLineCount > 0 ? (
        <PosInlineValidationMessage tone="error">
          Revisa las cantidades capturadas.
        </PosInlineValidationMessage>
      ) : null}

      {isAdjustmentHighImpact ? (
        <label className="flex items-center gap-2 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm font-medium text-amber-800">
          <input
            checked={adjustmentDraft.highImpactAcknowledged}
            className="h-4 w-4"
            onChange={(event) =>
              onAdjustmentDraftChange({
                ...adjustmentDraft,
                highImpactAcknowledged: event.target.checked,
              })
            }
            type="checkbox"
          />
          Confirmo ajuste de alto impacto.
        </label>
      ) : null}

      {adjustmentErrorMessage ? (
        <PosInlineValidationMessage tone="error">{adjustmentErrorMessage}</PosInlineValidationMessage>
      ) : null}

      {lastCommittedCorrection ? (
        <div className="flex items-center gap-2 rounded-lg border border-[rgba(18,122,90,0.16)] bg-[var(--ui-color-success-soft)] px-3 py-2 text-sm font-medium text-[var(--ui-color-success)]">
          <CheckCircleIcon className="h-4 w-4 shrink-0" />
          <span className="min-w-0 truncate">Ajuste registrado: {lastCommittedCorrection.folio}</span>
        </div>
      ) : null}
    </div>
  );
}

function CounterTransferMovementProductRow({
  adjustmentMode,
  draftLine,
  line,
  onDraftLineChange,
}: {
  adjustmentMode: boolean;
  draftLine: CounterTransferAdjustmentDraftLine | undefined;
  line: OperationDocumentView["lines"][number];
  onDraftLineChange: (line: CounterTransferAdjustmentDraftLine) => void;
}) {
  const originalQuantityText = formatQuantityFromMilliUnits(Number(line.quantity) * 1000);
  const deltaQuantityMilliUnits = draftLine ? getAdjustmentLineDeltaMilliUnits(draftLine) : null;
  const isInvalid = adjustmentMode && draftLine !== undefined && deltaQuantityMilliUnits === null;
  const deltaText =
    deltaQuantityMilliUnits === null || deltaQuantityMilliUnits === 0
      ? ""
      : formatSignedQuantityForDisplay(deltaQuantityMilliUnits);

  return (
    <div
      className={cn(
        "grid items-center gap-2 border-t border-[var(--pos-shell-border)] px-3 py-2 first:border-t-0",
        adjustmentMode
          ? "grid-cols-[minmax(0,1fr)_4.5rem_2.5rem]"
          : "grid-cols-[minmax(0,1fr)_auto]",
      )}
    >
      <span
        className="block min-w-0 truncate text-sm font-semibold text-slate-950"
        title={line.product_name_snapshot}
      >
        {line.product_name_snapshot}
      </span>
      {adjustmentMode && draftLine ? (
        <input
          aria-label={`Cantidad corregida de ${line.product_name_snapshot}`}
          className={cn(
            "h-8 min-w-0 rounded-lg px-2 text-right text-sm font-semibold [font-variant-numeric:tabular-nums]",
            posInputClass,
            isInvalid && "border-[var(--ui-color-danger)]",
          )}
          inputMode="decimal"
          maxLength={12}
          onChange={(event) =>
            onDraftLineChange({
              ...draftLine,
              quantityText: sanitizeQuantityInput(event.target.value),
            })
          }
          title={`Original: ${draftLine.originalQuantityText}`}
          value={draftLine.quantityText}
        />
      ) : (
        <span className="text-right text-sm font-semibold text-slate-950 [font-variant-numeric:tabular-nums]">
          {originalQuantityText}
        </span>
      )}
      {adjustmentMode ? (
        <span
          className={cn(
            "truncate text-right text-xs font-semibold [font-variant-numeric:tabular-nums]",
            deltaQuantityMilliUnits === null
              ? "text-[var(--ui-color-danger)]"
              : deltaQuantityMilliUnits > 0
                ? "text-[var(--ui-color-success)]"
                : deltaQuantityMilliUnits < 0
                  ? "text-[var(--ui-color-danger)]"
                  : "text-slate-400",
          )}
          title={deltaText ? `Diferencia ${deltaText}` : "Sin cambio"}
        >
          {deltaText}
        </span>
      ) : null}
    </div>
  );
}

function MovementDetailRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between gap-3">
      <span className="font-medium text-slate-600">{label}</span>
      <span className="min-w-0 truncate text-right font-semibold text-slate-950" title={value}>
        {value}
      </span>
    </div>
  );
}

type CounterStateProductLine = {
  key: string;
  name: string;
  quantityText: string;
  statusText: string;
  status: string;
};

type CounterStateClassGroup = {
  key: string;
  metadataText: string;
  name: string;
  products: CounterStateProductLine[];
  quantityText: string;
  quantityWithStatus: string;
  status: string;
};

function parseApiQuantity(quantity: string | null | undefined): number {
  const parsedQuantity = Number(quantity ?? "0");
  return Number.isFinite(parsedQuantity) ? parsedQuantity : 0;
}

function hasApiQuantity(quantity: string | null | undefined): boolean {
  return Math.abs(parseApiQuantity(quantity)) > 0;
}

function formatApiQuantity(quantity: string | null | undefined): string {
  return formatQuantityFromMilliUnits(parseApiQuantity(quantity) * 1000);
}

function getCounterProductQuantity(product: CashCloseReconciliationProductView): string {
  return product.final_expected_quantity ?? product.expected_quantity_before_deferred_attr;
}

function getCounterProductStatus(
  product: CashCloseReconciliationProductView,
  hasDeferredClassCapture: boolean,
): string {
  if (product.final_expected_quantity !== null && product.final_expected_quantity !== undefined) {
    return "Confirmado";
  }

  return hasDeferredClassCapture ? "Estimado" : "Confirmado";
}

function buildCounterStateProductLines(
  products: CashCloseReconciliationProductView[],
  hasDeferredClassCapture: boolean,
): CounterStateProductLine[] {
  return products
    .filter((product) => hasApiQuantity(getCounterProductQuantity(product)))
    .map((product) => ({
      key: `product:${product.product_id}`,
      name: product.product_name,
      quantityText: formatApiQuantity(getCounterProductQuantity(product)),
      statusText: getCounterProductStatus(product, hasDeferredClassCapture).toLowerCase(),
      status: getCounterProductStatus(product, hasDeferredClassCapture),
    }));
}

function buildCounterStateGroups(data: CashCloseReconciliationResponse): CounterStateClassGroup[] {
  const productsByClassId = new Map<string, CashCloseReconciliationProductView[]>();

  for (const product of data.relevant_products) {
    const products = productsByClassId.get(product.product_class_id) ?? [];
    products.push(product);
    productsByClassId.set(product.product_class_id, products);
  }

  const classRowsById = new Map(
    data.counter_class_availability.map((classRow) => [
      classRow.product_class_id,
      classRow,
    ]),
  );
  const groupedClassRows = data.counter_class_availability
    .filter((classRow) => {
      const classProducts = productsByClassId.get(classRow.product_class_id) ?? [];
      return (
        hasApiQuantity(classRow.available_quantity) ||
        hasApiQuantity(classRow.pending_class_capture_quantity) ||
        hasApiQuantity(classRow.expected_quantity_before_deferred_attr) ||
        classProducts.some((product) => hasApiQuantity(getCounterProductQuantity(product)))
      );
    })
    .map((classRow: CashCloseCounterClassAvailabilityView) => {
      const hasDeferredClassCapture = hasApiQuantity(classRow.pending_class_capture_quantity);
      const confirmedQuantity = parseApiQuantity(classRow.available_quantity);
      const deferredQuantity = parseApiQuantity(classRow.pending_class_capture_quantity);
      const operativeQuantity = confirmedQuantity + deferredQuantity;
      const formattedConfirmedQuantity = formatQuantityFromMilliUnits(confirmedQuantity * 1000);
      const formattedDeferredQuantity = formatQuantityFromMilliUnits(deferredQuantity * 1000);
      const formattedOperativeQuantity = formatQuantityFromMilliUnits(operativeQuantity * 1000);

      return {
        key: `class:${classRow.product_class_id}`,
        metadataText: hasDeferredClassCapture
          ? `${formattedConfirmedQuantity} confirmado / ${formattedDeferredQuantity} diferido`
          : `${formattedConfirmedQuantity} confirmado`,
        name: classRow.product_class_name,
        products: buildCounterStateProductLines(
          productsByClassId.get(classRow.product_class_id) ?? [],
          hasDeferredClassCapture,
        ),
        quantityText: formattedOperativeQuantity,
        quantityWithStatus: `${formattedOperativeQuantity} ${
          hasDeferredClassCapture ? "aprox." : "confirmado"
        }`,
        status: hasDeferredClassCapture ? "Aprox." : "Confirmado",
      };
    });

  const orphanGroups = Array.from(productsByClassId.entries())
    .filter(([classId]) => !classRowsById.has(classId))
    .map(([, products]) => {
      const quantity = products.reduce(
        (sum, product) => sum + parseApiQuantity(getCounterProductQuantity(product)),
        0,
      );
      const firstProduct = products[0];

      return {
        key: `class:${firstProduct.product_class_id}`,
        metadataText: `${formatQuantityFromMilliUnits(quantity * 1000)} confirmado`,
        name: firstProduct.product_class_name,
        products: buildCounterStateProductLines(products, false),
        quantityText: formatQuantityFromMilliUnits(quantity * 1000),
        quantityWithStatus: `${formatQuantityFromMilliUnits(quantity * 1000)} confirmado`,
        status: "Confirmado",
      };
    });

  return [...groupedClassRows, ...orphanGroups];
}

function CounterStateInventoryTable({
  emptyMessage = "Sin saldo operativo en mostrador.",
  groups,
}: {
  emptyMessage?: string;
  groups: CounterStateClassGroup[];
}) {
  const [expandedGroupKeys, setExpandedGroupKeys] = useState<Set<string>>(() => new Set());

  function toggleGroup(groupKey: string) {
    setExpandedGroupKeys((currentKeys) => {
      const nextKeys = new Set(currentKeys);
      if (nextKeys.has(groupKey)) {
        nextKeys.delete(groupKey);
      } else {
        nextKeys.add(groupKey);
      }
      return nextKeys;
    });
  }

  function handleGroupRowKeyDown(
    event: ReactKeyboardEvent<HTMLTableRowElement>,
    groupKey: string,
  ) {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      toggleGroup(groupKey);
    }
  }

  return (
    <div className="overflow-hidden rounded-lg border border-[var(--pos-shell-border)] bg-white shadow-sm">
      <table aria-label="Estado actual del mostrador" className="w-full table-fixed text-left text-sm">
        <thead className="border-b border-[var(--pos-shell-border)] bg-[var(--pos-shell-muted)] text-[10px] font-semibold uppercase tracking-[0.08em] text-slate-500">
          <tr>
            <th className="px-2.5 py-2">Clase / producto</th>
            <th className="w-[6.75rem] px-2.5 py-2 text-right">Cantidad</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-[var(--pos-shell-border)]">
          {groups.length === 0 ? (
            <tr>
              <td className="px-3 py-6 text-center text-sm font-medium text-slate-500" colSpan={2}>
                {emptyMessage}
              </td>
            </tr>
          ) : (
            groups.map((group) => {
              const isExpanded = expandedGroupKeys.has(group.key);
              return (
                <Fragment key={group.key}>
                  <tr
                    aria-expanded={isExpanded}
                    aria-label={`${isExpanded ? "Contraer" : "Expandir"} ${group.name}`}
                    className="cursor-pointer bg-slate-50 transition hover:bg-slate-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-[var(--pos-ring)]"
                    onClick={() => toggleGroup(group.key)}
                    onKeyDown={(event) => handleGroupRowKeyDown(event, group.key)}
                    role="button"
                    tabIndex={0}
                  >
                    <td className="min-w-0 px-2.5 py-2">
                      <div className="grid min-w-0 grid-cols-[1rem_minmax(0,1fr)] items-center gap-1.5">
                        <ChevronRightIcon
                          className={cn(
                            "h-3.5 w-3.5 text-slate-500 transition-transform",
                            isExpanded && "rotate-90",
                          )}
                        />
                        <span
                          className="block min-w-0 truncate text-sm font-semibold text-slate-950"
                          title={`${group.name} - ${group.metadataText}`}
                        >
                          {group.name}
                        </span>
                      </div>
                    </td>
                    <td
                      className="px-2.5 py-2 text-right font-semibold text-slate-950 [font-variant-numeric:tabular-nums]"
                      title={group.quantityWithStatus}
                    >
                      <span>{group.quantityText}</span>{" "}
                      <span className="text-[11px] font-medium text-slate-500">
                        {group.status === "Aprox." ? "aprox." : "confirmado"}
                      </span>
                    </td>
                  </tr>
                  {isExpanded
                    ? group.products.map((product) => (
                        <tr className="bg-white" key={product.key}>
                          <td className="min-w-0 px-2.5 py-1.5 pl-8">
                            <span
                              className="block truncate text-sm font-medium text-slate-700"
                              title={product.name}
                            >
                              {product.name}
                            </span>
                          </td>
                          <td
                            className="px-2.5 py-1.5 text-right font-medium text-slate-800 [font-variant-numeric:tabular-nums]"
                            title={`${product.quantityText} ${product.statusText}`}
                          >
                            <span>{product.quantityText}</span>{" "}
                            <span className="text-[11px] font-medium text-slate-500">
                              {product.statusText}
                            </span>
                          </td>
                        </tr>
                      ))
                    : null}
                </Fragment>
              );
            })
          )}
        </tbody>
      </table>
    </div>
  );
}

function CounterStateDisclosure({
  counterAvailabilityQuery,
  isOpen,
  onToggle,
}: {
  counterAvailabilityQuery: {
    data?: CashCloseReconciliationResponse;
    error: unknown;
    isPending: boolean;
    refetch: () => unknown;
  };
  isOpen: boolean;
  onToggle: () => void;
}) {
  const counterStateGroups = useMemo(
    () =>
      counterAvailabilityQuery.data ? buildCounterStateGroups(counterAvailabilityQuery.data) : [],
    [counterAvailabilityQuery.data],
  );
  const pendingClassCapture = counterAvailabilityQuery.data?.pending_class_capture;
  const pendingClassCaptureText = pendingClassCapture?.has_pending_class_capture
    ? formatApiQuantity(pendingClassCapture.pending_class_capture_total_quantity)
    : "0";

  return (
    <RightPanelBlock
      action={
        <ModuleStateChip tone={isOpen ? "primary" : "muted"}>
          {isOpen ? "Visible" : "Oculto"}
        </ModuleStateChip>
      }
      contentClassName="grid gap-2"
      title="Mostrador actual"
      tone="muted"
    >
      <button
        aria-controls="counter-transfer-current-counter"
        aria-expanded={isOpen}
        className="flex w-full items-center justify-between gap-3 rounded-lg border border-[var(--pos-shell-border)] bg-white px-3 py-2.5 text-left transition hover:border-[var(--pos-primary)] hover:bg-[var(--pos-primary-soft)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--pos-ring)]"
        onClick={onToggle}
        type="button"
      >
        <span className="grid min-w-0 gap-0.5">
          <span className="truncate text-sm font-semibold text-slate-950">
            {isOpen ? "Ocultar mostrador actual" : "Mostrar mostrador actual"}
          </span>
          <span className="truncate text-xs font-medium text-slate-500">
            Revisa saldos esperados sin salir de captura.
          </span>
        </span>
        <ChevronRightIcon
          className={cn(
            "h-4 w-4 shrink-0 text-[var(--pos-primary)] transition-transform",
            isOpen && "rotate-90",
          )}
        />
      </button>

      {isOpen ? (
        <div id="counter-transfer-current-counter" className="grid gap-2">
          {counterAvailabilityQuery.isPending ? (
            <div className="rounded-lg border border-[var(--pos-shell-border)] bg-white px-3 py-4 text-sm font-medium text-slate-500">
              Consultando mostrador.
            </div>
          ) : counterAvailabilityQuery.error ? (
            <div className="grid gap-2 rounded-lg border border-[rgba(180,35,24,0.16)] bg-[var(--ui-color-danger-soft)] px-3 py-3 text-sm font-medium text-[var(--ui-color-danger)]">
              <span>
                {toOperationalErrorMessage(
                  counterAvailabilityQuery.error,
                  "No fue posible consultar el estado del mostrador.",
                )}
              </span>
              <Button
                className={cn("h-8 justify-self-start px-3 text-xs", posOutlineButtonClass)}
                onClick={() => void counterAvailabilityQuery.refetch()}
                type="button"
              >
                Reintentar
              </Button>
            </div>
          ) : (
            <>
              <div className="flex flex-wrap items-center gap-2">
                <span className="pos-chip" data-tone="muted">
                  {counterStateGroups.length} clases
                </span>
                <span
                  className="pos-chip"
                  data-tone={pendingClassCapture?.has_pending_class_capture ? "warning" : "muted"}
                >
                  Diferido {pendingClassCaptureText}
                </span>
              </div>
              <CounterStateInventoryTable groups={counterStateGroups} />
            </>
          )}
        </div>
      ) : null}
    </RightPanelBlock>
  );
}

function CounterTransferCounterStateRightPanel({
  counterAvailabilityQuery,
  onBackToCapture,
}: {
  counterAvailabilityQuery: {
    data?: CashCloseReconciliationResponse;
    error: unknown;
    isPending: boolean;
    refetch: () => unknown;
  };
  onBackToCapture: () => void;
}) {
  const counterStateGroups = useMemo(
    () =>
      counterAvailabilityQuery.data ? buildCounterStateGroups(counterAvailabilityQuery.data) : [],
    [counterAvailabilityQuery.data],
  );
  const pendingClassCapture = counterAvailabilityQuery.data?.pending_class_capture;
  const pendingClassCaptureText = pendingClassCapture?.has_pending_class_capture
    ? formatApiQuantity(pendingClassCapture.pending_class_capture_total_quantity)
    : "0";

  return (
    <aside className="pos-shell-panel grid h-full min-h-0 grid-rows-[auto_auto_minmax(0,1fr)_auto] gap-3 px-3.5 py-3">
      <div className="min-w-0">
        <h2 className="truncate text-[1.05rem] font-semibold tracking-tight text-slate-950">
          Mostrador actual
        </h2>
        <p className="mt-1 text-sm font-medium text-slate-600">Consulta operativa</p>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <span className="pos-chip" data-tone="muted">
          {counterStateGroups.length} clases
        </span>
        <span
          className="pos-chip"
          data-tone={pendingClassCapture?.has_pending_class_capture ? "warning" : "muted"}
        >
          Diferido {pendingClassCaptureText}
        </span>
      </div>

      <ScrollPane className="min-h-0">
        {counterAvailabilityQuery.isPending ? (
          <PosLoadingState description="Consultando mostrador." title="Cargando estado" />
        ) : counterAvailabilityQuery.error ? (
          <PosErrorState
            action={
              <Button
                className={posPrimaryButtonClass}
                onClick={() => void counterAvailabilityQuery.refetch()}
                type="button"
              >
                Reintentar
              </Button>
            }
            description={toOperationalErrorMessage(
              counterAvailabilityQuery.error,
              "No fue posible consultar el estado del mostrador.",
            )}
            title="Mostrador no disponible"
          />
        ) : (
          <CounterStateInventoryTable groups={counterStateGroups} />
        )}
      </ScrollPane>

      <Button
        className={cn("h-11 w-full px-4", posOutlineButtonClass)}
        onClick={onBackToCapture}
        type="button"
      >
        <ArrowLeftIcon className="h-4 w-4" />
        Volver a captura
      </Button>
    </aside>
  );
}

function TransferSummaryLineRow({
  line,
  onDecrement,
  onIncrement,
  onQuantityChange,
  onQuantityInvalid,
  onRemove,
}: {
  line: OperationLine;
  onDecrement: () => void;
  onIncrement: () => void;
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

  function commitQuantity() {
    const normalizedQuantityText = sanitizeQuantityInput(quantityText);
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

  return (
    <CapturedProductLineRow
      inputRef={isEditing ? inputRef : null}
      name={line.productName}
      onBeginQuantityEdit={() => setIsEditing(true)}
      onCancelQuantityEdit={cancelQuantityEdit}
      onCommitQuantity={commitQuantity}
      onDecrement={() => {
        cancelQuantityEdit();
        onDecrement();
      }}
      onIncrement={() => {
        cancelQuantityEdit();
        onIncrement();
      }}
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
