import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Navigate, useNavigate } from "@tanstack/react-router";
import {
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
  PosConfirmationDialog,
  PosInlineValidationMessage,
  PosLoadingState,
} from "../../components/pos-feedback";
import { PosPaymentInputCard, PosPaymentValueCard } from "../../components/pos-payment-controls";
import {
  CentralWorkspaceSheet,
  CompactPageHeader,
  FlowGuide,
  ModuleStateChip,
  RightPanelBlock,
  ScrollPane,
  SearchField,
} from "../../components/pos-module-primitives";
import {
  ArrowLeftIcon,
  CheckCircleIcon,
  MoneyIcon,
  PackageIcon,
} from "../../components/pos-icons";
import { Button } from "../../components/ui/button";
import { appEnv } from "../../env";
import type {
  CashCloseDetailResponse,
  CashCloseIssueView,
  CashClosePaymentMethodRowView,
  CashClosePreviewResponse,
} from "../../lib/api-contracts";
import { formatCurrency } from "../../lib/formatters";
import { toOperationalErrorMessage } from "../../lib/http";
import {
  getSelectionShortcutIndex,
  getSelectionShortcutLabel,
  isEditableTarget,
} from "../../lib/keyboard-shortcuts";
import { cn } from "../../lib/utils";
import { usePosAuthStore } from "../auth/auth-store";
import { sortOperationalClasses, sortOperationalProducts } from "../operations/model";
import { useOperationsCatalogQuery, useOperationsClassProductsQuery } from "../operations/queries";
import { useRovingFocusGrid } from "../pos-shell/keyboard";
import { usePosTerminalStore } from "../pos-terminal/store";
import { posInputClass, posOutlineButtonClass, posPrimaryButtonClass } from "../pos-theme/theme";
import { useStatusMessageStore } from "../status-messages/store";
import { commitCashClose, previewCashClose } from "./cash-close-api";
import { useCashCloseBootstrapQuery, useCashCloseSummaryQuery } from "./queries";
import {
  CLOSE_PHYSICAL_STATE_CLASS_SELECTION,
  CLOSE_PHYSICAL_STATE_PRODUCT_SELECTION,
  CLOSE_PHYSICAL_STATE_QUANTITY_CAPTURE,
  addCashClosePendingCountLine,
  buildCashClosePreviewRequest,
  createInitialCashCloseDraftState,
  getCashCloseCountValueState,
  getDraftCountedTotalCents,
  goBackFromCashClosePhysicalState,
  hasCashClosePhysicalCounts,
  removeCashCloseCountedLine,
  sanitizeCashCloseObservation,
  sanitizeMoneyInput,
  selectClassForCashCloseCount,
  selectProductForCashCloseCount,
  setCashClosePendingQuantityText,
  setCashClosePhysicalSearchText,
  syncCashCloseDraftState,
  updateCashCloseCountedLineQuantity,
  type CashCloseDraftState,
} from "./model";
import {
  canAttemptCashCloseSubmit,
  finalizeSuccessfulCashClose,
  submitCashCloseAttempt,
} from "./submit";

const CLOSE_COUNT_CATALOG_MODULE = "COUNTER_TRANSFER";

type CashCloseScreenStage = "counting" | "review";

const PAYMENT_METHOD_LABELS: Record<string, string> = {
  CARD: "Tarjeta",
  CASH: "Efectivo",
  MIXED: "Mixto",
};

function useDebouncedValue(value: string, delayMs: number): string {
  const [debouncedValue, setDebouncedValue] = useState(value);

  useEffect(() => {
    const timeoutId = window.setTimeout(() => setDebouncedValue(value), delayMs);
    return () => window.clearTimeout(timeoutId);
  }, [delayMs, value]);

  return debouncedValue;
}

function isSubmitKey(event: Pick<KeyboardEvent | ReactKeyboardEvent, "key">): boolean {
  return event.key === "Enter" || event.key === "NumpadEnter";
}

function formatLocalDateTime(value: string | null | undefined): string {
  if (!value) {
    return "--";
  }

  return new Intl.DateTimeFormat("es-MX", {
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    month: "short",
  }).format(new Date(value));
}

function formatPaymentMethodLabel(paymentMethodCode: string): string {
  return PAYMENT_METHOD_LABELS[paymentMethodCode] ?? paymentMethodCode;
}

function formatMaybeCurrency(value: string | number | null | undefined): string {
  if (value === null || value === undefined) {
    return "--";
  }

  return formatCurrency(Number(value));
}

function getCloseState({
  completedCloseDetail,
  isClosing,
  livePreviewIssueCount,
  livePreviewPending,
  missingCash,
  missingPhysicalCount,
}: {
  completedCloseDetail: CashCloseDetailResponse | null;
  isClosing: boolean;
  livePreviewIssueCount: number;
  livePreviewPending: boolean;
  missingCash: boolean;
  missingPhysicalCount: boolean;
}): { label: string; tone: "danger" | "muted" | "primary" | "success" | "warning" } {
  if (completedCloseDetail) {
    return { label: "Cerrado", tone: "success" };
  }

  if (isClosing) {
    return { label: "Cerrando", tone: "primary" };
  }

  if (missingCash || missingPhysicalCount) {
    return { label: "Pendiente", tone: "warning" };
  }

  if (livePreviewPending) {
    return { label: "Calculando", tone: "primary" };
  }

  if (livePreviewIssueCount > 0) {
    return { label: "Revisar", tone: "danger" };
  }

  return { label: "Listo", tone: "success" };
}

function getPaymentRowsForDisplay(
  rows: CashClosePaymentMethodRowView[] | undefined,
): CashClosePaymentMethodRowView[] {
  return (rows ?? [])
    .filter((row) => row.payment_method_code !== "CASH")
    .filter((row) => row.payment_method_code !== "CARD")
    .filter((row) => row.expected_amount !== null && row.expected_amount !== undefined)
    .sort((left, right) => left.display_order - right.display_order);
}

function CountedProductRow({
  line,
  onDecrement,
  onIncrement,
  onRemove,
}: {
  line: CashCloseDraftState["countedProductDraftLines"][number];
  onDecrement: () => void;
  onIncrement: () => void;
  onRemove: () => void;
}) {
  return (
    <CapturedProductLineRow
      name={line.productName}
      onDecrement={onDecrement}
      onIncrement={onIncrement}
      onRemove={onRemove}
      quantityText={line.quantityText}
    />
  );
}

function CountedProductsReviewTable({
  canEdit,
  counterEmptyConfirmed,
  lines,
  onEditCount,
}: {
  canEdit: boolean;
  counterEmptyConfirmed: boolean;
  lines: CashCloseDraftState["countedProductDraftLines"];
  onEditCount: () => void;
}) {
  return (
    <section className="grid gap-3">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="text-base font-semibold text-slate-950">Productos contados</h2>
        {canEdit ? (
          <Button
            className={cn("h-9 px-3", posOutlineButtonClass)}
            onClick={onEditCount}
            type="button"
          >
            Editar conteo
          </Button>
        ) : null}
      </div>

      <div className="overflow-hidden rounded-xl border border-[var(--pos-shell-border)] bg-white shadow-sm">
        <table className="w-full table-fixed text-sm">
          <colgroup>
            <col className="w-[48%]" />
            <col className="w-[34%]" />
            <col className="w-[18%]" />
          </colgroup>
          <thead className="bg-[var(--pos-shell-muted)] text-[11px] font-semibold uppercase tracking-[0.08em] text-slate-500">
            <tr>
              <th className="px-3 py-2 text-left">Producto</th>
              <th className="px-3 py-2 text-left">Clase</th>
              <th className="px-3 py-2 text-right">Cantidad</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[var(--pos-shell-border)]">
            {lines.length === 0 ? (
              <tr>
                <td className="px-3 py-4 text-sm text-slate-600" colSpan={3}>
                  {counterEmptyConfirmed
                    ? "Mostrador vacío: 0 piezas de pan contadas."
                    : "Sin productos contados."}
                </td>
              </tr>
            ) : (
              lines.map((line) => (
                <tr key={line.key}>
                  <td
                    className="truncate px-3 py-2 font-semibold text-slate-950"
                    title={line.productName}
                  >
                    {line.productName}
                  </td>
                  <td className="truncate px-3 py-2 text-slate-600" title={line.productClassName}>
                    {line.productClassName}
                  </td>
                  <td className="px-3 py-2 text-right font-semibold text-slate-950 [font-variant-numeric:tabular-nums]">
                    {line.quantityText}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function CountingRightPanel({
  canConfirm,
  countedLines,
  isClosing,
  onCloseWithoutCount,
  onConfirmCount,
  onDecrementLine,
  onIncrementLine,
  onRemoveLine,
}: {
  canConfirm: boolean;
  countedLines: CashCloseDraftState["countedProductDraftLines"];
  isClosing: boolean;
  onCloseWithoutCount: () => void;
  onConfirmCount: () => void;
  onDecrementLine: (lineKey: string) => void;
  onIncrementLine: (lineKey: string) => void;
  onRemoveLine: (lineKey: string) => void;
}) {
  return (
    <div className="pos-shell-panel grid h-full min-h-0 grid-rows-[auto_minmax(0,1fr)_auto] gap-[var(--pos-section-gap)] p-[var(--pos-shell-workstation-padding)]">
      <RightPanelBlock title="Contar productos" />

      <ScrollPane className="grid content-start gap-[var(--pos-section-gap)] pr-1">
        <PosInlineValidationMessage tone="info">
          Si no quedó pan en mostrador, registra el conteo físico en cero.
        </PosInlineValidationMessage>

        <RightPanelBlock title="Conteo guardado" tone="muted">
          <CapturedProductLineList>
            {countedLines.length === 0 ? (
              <div className="px-3 py-3 text-sm text-slate-600">Sin conteos guardados.</div>
            ) : (
              countedLines.map((line) => (
                <CountedProductRow
                  key={line.key}
                  line={line}
                  onDecrement={() => onDecrementLine(line.key)}
                  onIncrement={() => onIncrementLine(line.key)}
                  onRemove={() => onRemoveLine(line.key)}
                />
              ))
            )}
          </CapturedProductLineList>
        </RightPanelBlock>
      </ScrollPane>

      <div className="grid gap-2 border-t border-[var(--pos-shell-border)] pt-3">
        <Button
          className={cn("h-12 w-full text-base", posPrimaryButtonClass)}
          disabled={!canConfirm || isClosing}
          onClick={onConfirmCount}
          type="button"
        >
          Cerrar con conteo
        </Button>
        <Button
          className={cn("h-10 w-full", posOutlineButtonClass)}
          disabled={isClosing}
          onClick={onCloseWithoutCount}
          type="button"
        >
          No sobró pan
        </Button>
        {!canConfirm ? (
          <p className="text-sm leading-5 text-slate-600">
            Agrega productos si sobró pan, o registra mostrador vacío para pasar al conteo
            monetario.
          </p>
        ) : null}
      </div>
    </div>
  );
}

function ReadOnlyAmountRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between gap-3 rounded-lg border border-[var(--pos-shell-border)] bg-white px-3 py-2 text-sm">
      <span className="min-w-0 text-slate-600">{label}</span>
      <span className="shrink-0 font-semibold text-slate-950 [font-variant-numeric:tabular-nums]">
        {value}
      </span>
    </div>
  );
}

function ClosingRightPanel({
  canSubmit,
  cashDifferenceText,
  countedCardText,
  countedCashInputRef,
  countedCashText,
  expectedCashText,
  firstBlockingIssue,
  isClosed,
  isClosing,
  livePreviewErrorMessage,
  observationText,
  onCashChange,
  onCashKeyDown,
  onCardChange,
  onCardKeyDown,
  onCloseShift,
  onObservationChange,
  onOpenNextShift,
  openedAtText,
  openingAmountText,
  otherPaymentRows,
  submitDisabledReason,
  submitErrorMessage,
  totalCashInText,
  totalCashOutText,
}: {
  canSubmit: boolean;
  cashDifferenceText: string;
  countedCardText: string;
  countedCashInputRef: Ref<HTMLInputElement>;
  countedCashText: string;
  expectedCashText: string;
  firstBlockingIssue: CashCloseIssueView | null;
  isClosed: boolean;
  isClosing: boolean;
  livePreviewErrorMessage: string | null;
  observationText: string;
  onCashChange: (value: string) => void;
  onCashKeyDown: (event: ReactKeyboardEvent<HTMLInputElement>) => void;
  onCardChange: (value: string) => void;
  onCardKeyDown: (event: ReactKeyboardEvent<HTMLInputElement>) => void;
  onCloseShift: () => void;
  onObservationChange: (value: string) => void;
  onOpenNextShift: () => void;
  openedAtText: string;
  openingAmountText: string;
  otherPaymentRows: CashClosePaymentMethodRowView[];
  submitDisabledReason: string | null;
  submitErrorMessage: string | null;
  totalCashInText: string;
  totalCashOutText: string;
}) {
  const hasObservation = observationText.trim().length > 0;
  const [isObservationOpen, setIsObservationOpen] = useState(hasObservation);
  const differenceAmount = Number(cashDifferenceText.replace(/[^0-9.-]+/g, ""));
  const differenceTone =
    cashDifferenceText === "--" ? "default" : differenceAmount === 0 ? "success" : "pending";

  useEffect(() => {
    if (hasObservation) {
      setIsObservationOpen(true);
    }
  }, [hasObservation]);

  return (
    <div className="pos-shell-panel grid h-full min-h-0 grid-rows-[auto_minmax(0,1fr)_auto] gap-[var(--pos-section-gap)] p-[var(--pos-shell-workstation-padding)]">
      <RightPanelBlock
        action={
          <span className="pos-chip" data-tone={isClosed ? "success" : "primary"}>
            {isClosed ? "Cerrado" : "Cierre"}
          </span>
        }
        title="Cierre de turno"
      />

      <ScrollPane className="grid content-start gap-[var(--pos-section-gap)] pr-1">
        <RightPanelBlock title="Sesion" tone="muted">
          <div className="grid gap-2">
            <ReadOnlyAmountRow label="Apertura" value={openingAmountText} />
            <ReadOnlyAmountRow label="Entradas" value={totalCashInText} />
            <ReadOnlyAmountRow label="Salidas" value={totalCashOutText} />
            <ReadOnlyAmountRow label="Abierto" value={openedAtText} />
          </div>
        </RightPanelBlock>

        <div className="grid gap-2">
          <PosPaymentInputCard icon={<MoneyIcon className="h-5 w-5" />} label="Efectivo">
            <input
              aria-label="Efectivo"
              className={cn(
                "h-11 w-full rounded-xl px-3 text-right text-[1.35rem] font-semibold leading-none tracking-tight [font-variant-numeric:tabular-nums]",
                posInputClass,
                "border-[var(--pos-primary)] ring-2 ring-[var(--pos-ring)]",
              )}
              disabled={isClosed || isClosing}
              inputMode="decimal"
              onChange={(event) => onCashChange(event.target.value)}
              onFocus={(event) => event.currentTarget.select()}
              onKeyDown={onCashKeyDown}
              placeholder="0.00"
              ref={countedCashInputRef}
              value={countedCashText}
            />
          </PosPaymentInputCard>
          <PosPaymentInputCard icon={<MoneyIcon className="h-5 w-5" />} label="Tarjeta">
            <input
              aria-label="Tarjeta"
              className={cn(
                "h-11 w-full rounded-xl px-3 text-right text-[1.35rem] font-semibold leading-none tracking-tight [font-variant-numeric:tabular-nums]",
                posInputClass,
                "border-[var(--pos-primary)] ring-2 ring-[var(--pos-ring)]",
              )}
              disabled={isClosed || isClosing}
              inputMode="decimal"
              onChange={(event) => onCardChange(event.target.value)}
              onFocus={(event) => event.currentTarget.select()}
              onKeyDown={onCardKeyDown}
              placeholder="0.00"
              value={countedCardText}
            />
          </PosPaymentInputCard>
          <PosPaymentValueCard
            icon={<MoneyIcon className="h-5 w-5" />}
            label="Esperado"
            tone="fixed"
            value={expectedCashText}
          />
          <PosPaymentValueCard
            icon={<CheckCircleIcon className="h-5 w-5" />}
            label="Diferencia"
            tone={differenceTone}
            value={cashDifferenceText}
          />
        </div>

        {otherPaymentRows.length > 0 ? (
          <RightPanelBlock title="Otros pagos" tone="muted">
            <div className="grid gap-2">
              {otherPaymentRows.map((row) => (
                <ReadOnlyAmountRow
                  key={row.payment_method_code}
                  label={formatPaymentMethodLabel(row.payment_method_code)}
                  value={formatMaybeCurrency(row.expected_amount)}
                />
              ))}
            </div>
          </RightPanelBlock>
        ) : null}

        <div className="grid gap-2">
          <button
            className="flex h-9 items-center justify-between rounded-lg border border-[var(--pos-shell-border)] bg-white px-3 text-left text-sm font-semibold text-slate-900 transition hover:bg-[var(--pos-shell-muted)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--pos-ring)]"
            disabled={isClosed || isClosing}
            onClick={() => setIsObservationOpen((currentValue) => !currentValue)}
            type="button"
          >
            <span>{isObservationOpen ? "Ocultar observación" : "Agregar observación"}</span>
            {hasObservation && !isObservationOpen ? (
              <span className="text-xs font-medium text-[var(--pos-primary)]">
                Observación guardada
              </span>
            ) : null}
          </button>

          {isObservationOpen ? (
            <textarea
              aria-label="Observación del cierre"
              className={cn(
                "min-h-16 resize-none rounded-xl px-3 py-2 text-sm leading-5",
                posInputClass,
              )}
              disabled={isClosed || isClosing}
              maxLength={240}
              onChange={(event) => onObservationChange(event.target.value)}
              placeholder="Opcional"
              value={observationText}
            />
          ) : null}
        </div>

        {submitErrorMessage ? (
          <PosInlineValidationMessage tone="error">{submitErrorMessage}</PosInlineValidationMessage>
        ) : null}
        {livePreviewErrorMessage ? (
          <PosInlineValidationMessage tone="error">
            {livePreviewErrorMessage}
          </PosInlineValidationMessage>
        ) : null}
        {firstBlockingIssue ? (
          <PosInlineValidationMessage tone="warning">
            {firstBlockingIssue.message}
          </PosInlineValidationMessage>
        ) : null}
      </ScrollPane>

      <div className="grid gap-2 border-t border-[var(--pos-shell-border)] pt-3">
        <Button
          className={cn("h-12 w-full text-base", posPrimaryButtonClass)}
          disabled={isClosed ? false : !canSubmit}
          onClick={isClosed ? onOpenNextShift : onCloseShift}
          type="button"
        >
          {isClosed ? "Abrir nuevo turno" : isClosing ? "Cerrando..." : "Cerrar turno"}
        </Button>
        {submitDisabledReason && !isClosed ? (
          <p className="text-sm leading-5 text-slate-600">{submitDisabledReason}</p>
        ) : null}
      </div>
    </div>
  );
}

export function CashCloseScreen() {
  const accessToken = usePosAuthStore((state) => state.accessToken);
  const clearSession = usePosAuthStore((state) => state.clearSession);
  const resetPosTerminal = usePosTerminalStore((state) => state.reset);
  const showError = useStatusMessageStore((state) => state.showError);
  const showSuccess = useStatusMessageStore((state) => state.showSuccess);
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const bootstrapQuery = useCashCloseBootstrapQuery();
  const [draftState, setDraftState] = useState<CashCloseDraftState>(
    createInitialCashCloseDraftState(),
  );
  const [closeStage, setCloseStage] = useState<CashCloseScreenStage>("counting");
  const [validationResult, setValidationResult] = useState<CashCloseDetailResponse | null>(null);
  const [livePreviewResult, setLivePreviewResult] = useState<CashClosePreviewResponse | null>(null);
  const [isLivePreviewPending, setIsLivePreviewPending] = useState(false);
  const [livePreviewErrorMessage, setLivePreviewErrorMessage] = useState<string | null>(null);
  const [submitErrorMessage, setSubmitErrorMessage] = useState<string | null>(null);
  const [isCloseWithoutCountDialogOpen, setIsCloseWithoutCountDialogOpen] = useState(false);
  const [counterEmptyConfirmed, setCounterEmptyConfirmed] = useState(false);
  const [completedCloseDetail, setCompletedCloseDetail] = useState<CashCloseDetailResponse | null>(
    null,
  );
  const quantityInputRef = useRef<HTMLInputElement>(null);
  const cashInputRef = useRef<HTMLInputElement>(null);
  const searchInputRef = useRef<HTMLInputElement>(null);
  const lastAutoFocusedGridKeyRef = useRef<string | null>(null);
  const livePreviewRequestRef = useRef(0);
  const currentOpenCashSession = bootstrapQuery.data?.current_open_cash_session ?? null;
  const summaryQuery = useCashCloseSummaryQuery(currentOpenCashSession !== null);
  const debouncedSearchText = useDebouncedValue(draftState.physicalSearchText, 180);
  const catalogQuery = useOperationsCatalogQuery(
    CLOSE_COUNT_CATALOG_MODULE,
    draftState.physicalControlState === CLOSE_PHYSICAL_STATE_CLASS_SELECTION
      ? debouncedSearchText
      : "",
  );
  const classProductsQuery = useOperationsClassProductsQuery(
    CLOSE_COUNT_CATALOG_MODULE,
    draftState.physicalPendingSelection?.productClass.id ?? null,
    draftState.physicalControlState === CLOSE_PHYSICAL_STATE_PRODUCT_SELECTION
      ? debouncedSearchText
      : "",
  );
  const updateDraftState = useCallback(
    (updater: (currentState: CashCloseDraftState) => CashCloseDraftState) => {
      setDraftState((currentState) => updater(currentState));
      setCompletedCloseDetail(null);
      setSubmitErrorMessage(null);
      setLivePreviewErrorMessage(null);
    },
    [],
  );

  const sortedClasses = useMemo(
    () => sortOperationalClasses(catalogQuery.data?.classes ?? []),
    [catalogQuery.data?.classes],
  );
  const sortedProducts = useMemo(
    () => sortOperationalProducts(classProductsQuery.data?.products ?? []),
    [classProductsQuery.data?.products],
  );
  const classGridFocus = useRovingFocusGrid({
    itemCount: sortedClasses.length,
    onActivate: (index) => {
      const productClass = sortedClasses[index];
      if (productClass) {
        updateDraftState((state) => selectClassForCashCloseCount(state, productClass));
      }
    },
  });
  const productGridFocus = useRovingFocusGrid({
    itemCount: sortedProducts.length,
    onActivate: (index) => {
      const product = sortedProducts[index];
      if (product) {
        updateDraftState((state) => selectProductForCashCloseCount(state, product));
      }
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
  const quantitySelection =
    draftState.physicalControlState === CLOSE_PHYSICAL_STATE_QUANTITY_CAPTURE
      ? draftState.physicalPendingSelection
      : null;
  const quantityProduct = quantitySelection?.product ?? null;
  const countedCashInputText = draftState.countedPaymentAmounts.CASH ?? "";
  const countedCardInputText = draftState.countedPaymentAmounts.CARD ?? "";
  const countedCashState = getCashCloseCountValueState(countedCashInputText);
  const countedCardState = getCashCloseCountValueState(countedCardInputText);
  const countedTotalCents = getDraftCountedTotalCents(draftState.countedPaymentAmounts);
  const hasFinancialCount = countedCashState === "CAPTURED" || countedCardState === "CAPTURED";
  const countedFinancialDisplayText = hasFinancialCount
    ? formatCurrency(countedTotalCents / 100)
    : "Pendiente";
  const hasPhysicalCounts = hasCashClosePhysicalCounts(draftState);
  const countedPaymentAmounts = draftState.countedPaymentAmounts;
  const countedProductDraftLines = draftState.countedProductDraftLines;
  const observationText = draftState.observationText;
  const previewPayload = useMemo(
    () =>
      buildCashClosePreviewRequest(
        appEnv.VITE_POS_WORKSTATION_CODE,
        {
          countedPaymentAmounts,
          countedProductDraftLines,
          observationText,
        },
        { counterEmptyConfirmed },
      ),
    [counterEmptyConfirmed, countedPaymentAmounts, countedProductDraftLines, observationText],
  );
  const expectedCashText =
    livePreviewResult?.expected_cash_amount !== undefined
      ? formatCurrency(Number(livePreviewResult.expected_cash_amount))
      : summaryQuery.data
        ? formatCurrency(summaryQuery.data.expected_cash_amount)
        : "--";
  const expectedCashCents =
    livePreviewResult?.expected_cash_amount !== undefined
      ? Math.round(Number(livePreviewResult.expected_cash_amount) * 100)
      : summaryQuery.data
        ? Math.round(Number(summaryQuery.data.expected_cash_amount) * 100)
        : null;
  const cashDifferenceText =
    expectedCashCents !== null
      ? formatCurrency((countedTotalCents - expectedCashCents) / 100)
      : "--";
  const openingAmountText = summaryQuery.data
    ? formatCurrency(summaryQuery.data.opening_amount)
    : "--";
  const totalCashInText = summaryQuery.data
    ? formatCurrency(summaryQuery.data.total_cash_in)
    : "--";
  const totalCashOutText = summaryQuery.data
    ? formatCurrency(summaryQuery.data.total_cash_out)
    : "--";
  const openedAtText = formatLocalDateTime(
    currentOpenCashSession?.opened_at ? String(currentOpenCashSession.opened_at) : null,
  );
  const liveBlockers = livePreviewResult?.blockers ?? [];
  const relevantLiveBlockers = liveBlockers.filter(
    (issue) =>
      issue.code !== "MISSING_COUNTED_PAYMENT_TOTALS" &&
      issue.code !== "MISSING_COUNTED_CLOSING_STOCK",
  );
  const firstBlockingIssue = relevantLiveBlockers[0] ?? null;
  const otherPaymentRows = getPaymentRowsForDisplay(livePreviewResult?.payment_method_rows);
  const isCountingStage = closeStage === "counting";
  const isReviewStage = closeStage === "review";
  const isSelectionLoading =
    isCountingStage &&
    ((draftState.physicalControlState === CLOSE_PHYSICAL_STATE_CLASS_SELECTION &&
      catalogQuery.isPending) ||
      (draftState.physicalControlState === CLOSE_PHYSICAL_STATE_PRODUCT_SELECTION &&
        classProductsQuery.isPending));
  const selectionLoadError =
    draftState.physicalControlState === CLOSE_PHYSICAL_STATE_PRODUCT_SELECTION
      ? classProductsQuery.error
      : catalogQuery.error;
  const showBackAction =
    (isCountingStage &&
      draftState.physicalControlState === CLOSE_PHYSICAL_STATE_PRODUCT_SELECTION) ||
    (isCountingStage && draftState.physicalControlState === CLOSE_PHYSICAL_STATE_QUANTITY_CAPTURE);
  const showSearch =
    (isCountingStage && draftState.physicalControlState === CLOSE_PHYSICAL_STATE_CLASS_SELECTION) ||
    (isCountingStage && draftState.physicalControlState === CLOSE_PHYSICAL_STATE_PRODUCT_SELECTION);
  const activeGridKey = useMemo(() => {
    if (closeStage !== "counting") {
      return null;
    }

    if (draftState.physicalControlState === CLOSE_PHYSICAL_STATE_CLASS_SELECTION) {
      return "classes";
    }

    if (
      draftState.physicalControlState === CLOSE_PHYSICAL_STATE_PRODUCT_SELECTION &&
      draftState.physicalPendingSelection !== null
    ) {
      return `products:${draftState.physicalPendingSelection.productClass.id}`;
    }

    return null;
  }, [closeStage, draftState.physicalControlState, draftState.physicalPendingSelection]);
  const submitDisabledReason =
    completedCloseDetail !== null
      ? null
      : currentOpenCashSession === null
        ? "No hay una caja abierta para cerrar."
        : !hasFinancialCount
          ? "Captura efectivo o tarjeta."
          : !counterEmptyConfirmed && !hasPhysicalCounts
            ? "Agrega al menos un conteo de producto."
            : firstBlockingIssue
              ? firstBlockingIssue.message
              : null;
  const canSubmit =
    submitDisabledReason === null &&
    canAttemptCashCloseSubmit({
      accessToken,
      hasOpenCashSession: currentOpenCashSession !== null,
      isCommitPending: false,
    });

  useEffect(() => {
    if (!bootstrapQuery.data) {
      return;
    }

    setDraftState((currentState) =>
      syncCashCloseDraftState(currentState, {
        paymentMethodCatalog: bootstrapQuery.data.payment_method_catalog,
      }),
    );
  }, [bootstrapQuery.data]);

  useEffect(() => {
    if (
      closeStage !== "counting" ||
      draftState.physicalControlState !== CLOSE_PHYSICAL_STATE_QUANTITY_CAPTURE
    ) {
      return;
    }

    quantityInputRef.current?.focus();
    quantityInputRef.current?.select();
  }, [closeStage, draftState.physicalControlState, draftState.physicalPendingSelection]);

  useEffect(() => {
    if (activeGridKey === null) {
      lastAutoFocusedGridKeyRef.current = null;
    }
  }, [activeGridKey]);

  useEffect(() => {
    if (isSelectionLoading || selectionLoadError || activeGridKey === null) {
      return;
    }

    if (lastAutoFocusedGridKeyRef.current === activeGridKey) {
      return;
    }

    if (
      draftState.physicalControlState === CLOSE_PHYSICAL_STATE_CLASS_SELECTION &&
      sortedClasses.length > 0
    ) {
      lastAutoFocusedGridKeyRef.current = activeGridKey;
      focusClassIndex(0);
      return;
    }

    if (
      draftState.physicalControlState === CLOSE_PHYSICAL_STATE_PRODUCT_SELECTION &&
      sortedProducts.length > 0
    ) {
      lastAutoFocusedGridKeyRef.current = activeGridKey;
      focusProductIndex(0);
    }
  }, [
    activeGridKey,
    draftState.physicalControlState,
    focusClassIndex,
    focusProductIndex,
    isSelectionLoading,
    selectionLoadError,
    sortedClasses.length,
    sortedProducts.length,
  ]);

  useEffect(() => {
    if (accessToken === null || currentOpenCashSession === null) {
      setIsLivePreviewPending(false);
      setLivePreviewResult(null);
      return;
    }

    const currentRequestId = livePreviewRequestRef.current + 1;
    livePreviewRequestRef.current = currentRequestId;
    setIsLivePreviewPending(true);

    const timeoutId = window.setTimeout(() => {
      void previewCashClose(accessToken, previewPayload)
        .then((previewResult) => {
          if (livePreviewRequestRef.current !== currentRequestId) {
            return;
          }

          setLivePreviewResult(previewResult);
          setIsLivePreviewPending(false);
          setLivePreviewErrorMessage(null);
        })
        .catch((error) => {
          if (livePreviewRequestRef.current !== currentRequestId) {
            return;
          }

          setIsLivePreviewPending(false);
          setLivePreviewErrorMessage(
            toOperationalErrorMessage(error, "No pudimos calcular el cierre con el conteo actual."),
          );
        });
    }, 320);

    return () => window.clearTimeout(timeoutId);
  }, [accessToken, currentOpenCashSession, previewPayload]);

  useEffect(() => {
    function handleKeyboard(event: KeyboardEvent) {
      if (closeStage !== "counting") {
        return;
      }

      if (event.key === "Escape") {
        if (
          draftState.physicalControlState === CLOSE_PHYSICAL_STATE_PRODUCT_SELECTION ||
          draftState.physicalControlState === CLOSE_PHYSICAL_STATE_QUANTITY_CAPTURE
        ) {
          event.preventDefault();
          updateDraftState((state) => goBackFromCashClosePhysicalState(state));
          return;
        }

        if (
          draftState.physicalControlState === CLOSE_PHYSICAL_STATE_CLASS_SELECTION &&
          draftState.physicalSearchText.trim().length > 0 &&
          !isEditableTarget(event.target)
        ) {
          event.preventDefault();
          updateDraftState((state) => setCashClosePhysicalSearchText(state, ""));
        }

        return;
      }

      if (isEditableTarget(event.target)) {
        return;
      }

      const shortcutIndex = getSelectionShortcutIndex(event.key);
      if (shortcutIndex === null) {
        return;
      }

      if (draftState.physicalControlState === CLOSE_PHYSICAL_STATE_CLASS_SELECTION) {
        const productClass = sortedClasses[shortcutIndex];
        if (productClass) {
          event.preventDefault();
          updateDraftState((state) => selectClassForCashCloseCount(state, productClass));
        }
        return;
      }

      if (draftState.physicalControlState === CLOSE_PHYSICAL_STATE_PRODUCT_SELECTION) {
        const product = sortedProducts[shortcutIndex];
        if (product) {
          event.preventDefault();
          updateDraftState((state) => selectProductForCashCloseCount(state, product));
        }
      }
    }

    window.addEventListener("keydown", handleKeyboard);
    return () => window.removeEventListener("keydown", handleKeyboard);
  }, [
    closeStage,
    draftState.physicalControlState,
    draftState.physicalSearchText,
    sortedClasses,
    sortedProducts,
    updateDraftState,
  ]);

  const closeMutation = useMutation({
    mutationFn: (payload: ReturnType<typeof buildCashClosePreviewRequest>) =>
      submitCashCloseAttempt({
        commit: (validatedPayload) => commitCashClose(accessToken!, validatedPayload),
        payload,
        preview: (validatedPayload) => previewCashClose(accessToken!, validatedPayload),
      }),
    onSuccess: async (result) => {
      setLivePreviewResult(result.preview);

      if (!result.detail) {
        const message =
          result.preview.blockers[0]?.message ??
          "El backend pidio revisar el cierre antes de confirmar.";
        setValidationResult(null);
        setCompletedCloseDetail(null);
        setSubmitErrorMessage(message);
        showError(message);
        return;
      }

      setValidationResult(null);
      setCompletedCloseDetail(null);
      setSubmitErrorMessage(null);
      setIsCloseWithoutCountDialogOpen(false);
      showSuccess("Turno cerrado correctamente");
      await finalizeSuccessfulCashClose({
        clearQueryCache: () => queryClient.clear(),
        clearSession,
        navigateToLogin: () => navigate({ to: "/login" }),
        resetPosTerminal,
      });
    },
    onError: (error) => {
      const message = toOperationalErrorMessage(
        error,
        "No se pudo cerrar el turno. Intenta nuevamente.",
      );
      setValidationResult(null);
      setCompletedCloseDetail(null);
      setSubmitErrorMessage(message);
      showError(message);
    },
  });

  const effectiveCloseState = getCloseState({
    completedCloseDetail,
    isClosing: closeMutation.isPending,
    livePreviewIssueCount: relevantLiveBlockers.length,
    livePreviewPending: isLivePreviewPending,
    missingCash: !hasFinancialCount,
    missingPhysicalCount: !counterEmptyConfirmed && !hasPhysicalCounts,
  });

  const handleAddCount = useCallback(() => {
    try {
      updateDraftState((state) => addCashClosePendingCountLine(state));
    } catch (error) {
      setSubmitErrorMessage(
        toOperationalErrorMessage(error, "Captura una cantidad valida antes de guardar."),
      );
    }
  }, [updateDraftState]);

  const handleConfirmCount = useCallback(() => {
    if (!hasPhysicalCounts) {
      setSubmitErrorMessage("Agrega al menos un conteo de producto.");
      return;
    }

    setCounterEmptyConfirmed(false);
    setSubmitErrorMessage(null);
    setCloseStage("review");
    window.setTimeout(() => {
      cashInputRef.current?.focus();
      cashInputRef.current?.select();
    }, 0);
  }, [hasPhysicalCounts]);

  const handleEditCount = useCallback(() => {
    setCounterEmptyConfirmed(false);
    setCloseStage("counting");
    window.setTimeout(() => {
      searchInputRef.current?.focus();
      searchInputRef.current?.select();
    }, 0);
  }, []);

  const handleDecrementCountedLine = useCallback(
    (lineKey: string) => {
      updateDraftState((state) => {
        const currentLine = state.countedProductDraftLines.find(
          (draftLine) => draftLine.key === lineKey,
        );
        if (!currentLine) {
          return state;
        }

        const nextQuantity = currentLine.quantityMilliUnits - 1000;
        return {
          ...state,
          countedProductDraftLines:
            nextQuantity <= 0
              ? removeCashCloseCountedLine(state.countedProductDraftLines, lineKey)
              : state.countedProductDraftLines.map((draftLine) =>
                  draftLine.key === lineKey
                    ? updateCashCloseCountedLineQuantity(draftLine, nextQuantity)
                    : draftLine,
                ),
        };
      });
    },
    [updateDraftState],
  );

  const handleIncrementCountedLine = useCallback(
    (lineKey: string) => {
      updateDraftState((state) => ({
        ...state,
        countedProductDraftLines: state.countedProductDraftLines.map((draftLine) =>
          draftLine.key === lineKey
            ? updateCashCloseCountedLineQuantity(draftLine, draftLine.quantityMilliUnits + 1000)
            : draftLine,
        ),
      }));
    },
    [updateDraftState],
  );

  const handleRemoveCountedLine = useCallback(
    (lineKey: string) => {
      updateDraftState((state) => ({
        ...state,
        countedProductDraftLines: removeCashCloseCountedLine(
          state.countedProductDraftLines,
          lineKey,
        ),
      }));
    },
    [updateDraftState],
  );

  const handleCloseShift = useCallback(() => {
    if (closeStage !== "review" || !canSubmit || closeMutation.isPending) {
      return;
    }

    setSubmitErrorMessage(null);
    if (counterEmptyConfirmed) {
      setIsCloseWithoutCountDialogOpen(true);
      return;
    }

    closeMutation.mutate(previewPayload);
  }, [canSubmit, counterEmptyConfirmed, closeMutation, closeStage, previewPayload]);

  const handleRequestCloseWithoutCount = useCallback(() => {
    if (closeMutation.isPending || currentOpenCashSession === null) {
      return;
    }

    setCounterEmptyConfirmed(true);
    setSubmitErrorMessage(null);
    setCloseStage("review");
    window.setTimeout(() => {
      cashInputRef.current?.focus();
      cashInputRef.current?.select();
    }, 0);
  }, [closeMutation.isPending, currentOpenCashSession]);

  const handleCloseWithoutCount = useCallback(() => {
    if (closeMutation.isPending || currentOpenCashSession === null || !canSubmit) {
      return;
    }

    setSubmitErrorMessage(null);
    closeMutation.mutate(previewPayload);
  }, [canSubmit, closeMutation, currentOpenCashSession, previewPayload]);

  const handleOpenNextShift = useCallback(() => {
    resetPosTerminal();
    queryClient.clear();
    void navigate({ to: "/cash-session/open" });
  }, [navigate, queryClient, resetPosTerminal]);

  const handleCashKeyDown = useCallback((event: ReactKeyboardEvent<HTMLInputElement>) => {
    if (!isSubmitKey(event)) {
      return;
    }

    event.preventDefault();
    searchInputRef.current?.focus();
    searchInputRef.current?.select();
  }, []);

  const rightPanel =
    closeStage === "counting" && completedCloseDetail === null ? (
      <CountingRightPanel
        canConfirm={hasPhysicalCounts}
        countedLines={draftState.countedProductDraftLines}
        isClosing={closeMutation.isPending}
        onCloseWithoutCount={handleRequestCloseWithoutCount}
        onConfirmCount={handleConfirmCount}
        onDecrementLine={handleDecrementCountedLine}
        onIncrementLine={handleIncrementCountedLine}
        onRemoveLine={handleRemoveCountedLine}
      />
    ) : (
      <ClosingRightPanel
        canSubmit={isReviewStage && canSubmit && !closeMutation.isPending}
        cashDifferenceText={cashDifferenceText}
        countedCardText={countedCardInputText}
        countedCashInputRef={cashInputRef}
        countedCashText={countedCashInputText}
        expectedCashText={
          validationResult?.expected_cash_amount !== undefined
            ? formatCurrency(Number(validationResult.expected_cash_amount))
            : expectedCashText
        }
        firstBlockingIssue={firstBlockingIssue}
        isClosed={completedCloseDetail !== null}
        isClosing={closeMutation.isPending}
        livePreviewErrorMessage={livePreviewErrorMessage}
        observationText={draftState.observationText}
        onCashChange={(value) =>
          updateDraftState((state) => ({
            ...state,
            countedPaymentAmounts: {
              ...state.countedPaymentAmounts,
              CASH: sanitizeMoneyInput(value),
            },
          }))
        }
        onCashKeyDown={handleCashKeyDown}
        onCardChange={(value) =>
          updateDraftState((state) => ({
            ...state,
            countedPaymentAmounts: {
              ...state.countedPaymentAmounts,
              CARD: sanitizeMoneyInput(value),
            },
          }))
        }
        onCardKeyDown={handleCashKeyDown}
        onCloseShift={handleCloseShift}
        onObservationChange={(value) =>
          updateDraftState((state) => ({
            ...state,
            observationText: sanitizeCashCloseObservation(value),
          }))
        }
        onOpenNextShift={handleOpenNextShift}
        openedAtText={openedAtText}
        openingAmountText={openingAmountText}
        otherPaymentRows={otherPaymentRows}
        submitDisabledReason={submitDisabledReason}
        submitErrorMessage={submitErrorMessage}
        totalCashInText={totalCashInText}
        totalCashOutText={totalCashOutText}
      />
    );

  useAppShellRightPanel(rightPanel);

  if (accessToken === null) {
    return <Navigate to="/login" />;
  }

  if (bootstrapQuery.isPending) {
    return (
      <PosLoadingState
        description="Preparando el cierre del turno actual."
        title="Cargando cierre"
      />
    );
  }

  if (bootstrapQuery.isError || !bootstrapQuery.data) {
    return (
      <PosErrorState
        action={
          <Button onClick={() => void bootstrapQuery.refetch()} type="button">
            Reintentar
          </Button>
        }
        description={toOperationalErrorMessage(
          bootstrapQuery.error,
          "No fue posible cargar el cierre.",
        )}
        title="No pudimos abrir el cierre"
      />
    );
  }

  if (currentOpenCashSession === null) {
    return (
      <PosErrorState
        action={
          <Button
            className={posPrimaryButtonClass}
            onClick={() => void navigate({ to: "/cash-session/open" })}
            type="button"
          >
            Ir a apertura
          </Button>
        }
        description="No hay una caja abierta para cerrar."
        title="No hay turno abierto"
      />
    );
  }

  return (
    <>
      <div className="grid gap-2.5 lg:h-full">
        <CentralWorkspaceSheet
          className="lg:h-full"
          contentClassName="min-h-0 overflow-y-auto px-3 pb-3 pt-2"
          header={
            <CompactPageHeader
              secondaryChips={
                isReviewStage ? (
                  <ModuleStateChip tone="muted">{countedFinancialDisplayText}</ModuleStateChip>
                ) : undefined
              }
              stateChip={
                <ModuleStateChip tone={isCountingStage ? "primary" : effectiveCloseState.tone}>
                  {isCountingStage ? "Conteo" : effectiveCloseState.label}
                </ModuleStateChip>
              }
              title="Cierre de turno"
            >
              <FlowGuide
                activeStepKey={closeStage}
                steps={[
                  {
                    icon: <PackageIcon className="h-3.5 w-3.5" />,
                    key: "counting",
                    label: "Contar productos",
                  },
                  {
                    icon: <MoneyIcon className="h-3.5 w-3.5" />,
                    key: "review",
                    label: "Cierre",
                  },
                ]}
                variant="process"
              />
            </CompactPageHeader>
          }
          toolbar={
            showBackAction || showSearch ? (
              <div className="flex min-w-0 flex-wrap items-center justify-between gap-3">
                <div className="flex min-w-0 items-center gap-3">
                  {showBackAction ? (
                    <Button
                      aria-label="Regresar"
                      className={cn("h-10 px-3", posOutlineButtonClass)}
                      onClick={() =>
                        updateDraftState((state) => goBackFromCashClosePhysicalState(state))
                      }
                      title="Regresar"
                      type="button"
                    >
                      <ArrowLeftIcon className="h-4 w-4" />
                    </Button>
                  ) : null}
                </div>

                {showSearch ? (
                  <SearchField
                    ariaLabel="Buscar en cierre"
                    className="w-full max-w-sm"
                    inputClassName={cn("h-9 rounded-lg text-sm shadow-sm", posInputClass)}
                    inputRef={searchInputRef}
                    onChange={(value) =>
                      updateDraftState((state) => setCashClosePhysicalSearchText(state, value))
                    }
                    placeholder={
                      draftState.physicalControlState === CLOSE_PHYSICAL_STATE_PRODUCT_SELECTION
                        ? "Filtrar producto"
                        : "Filtrar clase"
                    }
                    value={draftState.physicalSearchText}
                  />
                ) : null}
              </div>
            ) : undefined
          }
          toolbarClassName="py-2"
        >
          {isReviewStage ? (
            <CountedProductsReviewTable
              canEdit={completedCloseDetail === null && !closeMutation.isPending}
              lines={draftState.countedProductDraftLines}
              onEditCount={handleEditCount}
              counterEmptyConfirmed={counterEmptyConfirmed}
            />
          ) : null}

          {isCountingStage && isSelectionLoading ? (
            <div className="rounded-xl border border-[var(--pos-shell-border)] bg-[var(--pos-shell-muted)] px-4 py-8 text-center text-sm text-slate-600">
              Cargando catalogo
            </div>
          ) : null}

          {isCountingStage && !isSelectionLoading && selectionLoadError ? (
            <PosErrorState
              action={
                <Button
                  className={posPrimaryButtonClass}
                  onClick={() =>
                    draftState.physicalControlState === CLOSE_PHYSICAL_STATE_PRODUCT_SELECTION
                      ? void classProductsQuery.refetch()
                      : void catalogQuery.refetch()
                  }
                  type="button"
                >
                  Reintentar
                </Button>
              }
              description={toOperationalErrorMessage(
                selectionLoadError,
                "No pudimos cargar el catalogo.",
              )}
              title="Catalogo no disponible"
            />
          ) : null}

          {isCountingStage &&
          !isSelectionLoading &&
          !selectionLoadError &&
          draftState.physicalControlState === CLOSE_PHYSICAL_STATE_CLASS_SELECTION ? (
            sortedClasses.length > 0 ? (
              <div className="grid gap-2.5">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <p className="text-xs font-medium text-slate-500">
                    Enter: seleccionar | Esc: limpiar busqueda
                  </p>
                </div>
                <div className="grid gap-2.5 sm:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4">
                  {sortedClasses.map((productClass, index) => {
                    const itemProps = getClassItemProps(index);

                    return (
                      <CatalogSelectionCard
                        buttonRef={itemProps.ref}
                        code={productClass.code}
                        isActive={classActiveIndex === index}
                        key={productClass.id}
                        name={productClass.name}
                        onCardFocus={itemProps.onFocus}
                        onCardKeyDown={itemProps.onKeyDown}
                        onSelect={() =>
                          updateDraftState((state) =>
                            selectClassForCashCloseCount(state, productClass),
                          )
                        }
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
              <div className="rounded-xl border border-dashed border-[var(--pos-shell-border)] bg-[var(--pos-shell-muted)] px-4 py-8 text-center text-sm text-slate-600">
                No hay clases para la busqueda actual.
              </div>
            )
          ) : null}

          {isCountingStage &&
          !isSelectionLoading &&
          !selectionLoadError &&
          draftState.physicalControlState === CLOSE_PHYSICAL_STATE_PRODUCT_SELECTION ? (
            sortedProducts.length > 0 ? (
              <div className="grid gap-2.5">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="flex flex-wrap items-center gap-2 text-xs text-slate-500">
                    <span className="font-medium text-slate-700">
                      {draftState.physicalPendingSelection?.productClass.name}
                    </span>
                  </div>
                  <p className="text-xs font-medium text-slate-500">
                    Enter: seleccionar | Esc: volver
                  </p>
                </div>
                <div className="grid gap-2.5 sm:grid-cols-2 xl:grid-cols-3">
                  {sortedProducts.map((product, index) => {
                    const itemProps = getProductItemProps(index);

                    return (
                      <CatalogSelectionCard
                        buttonRef={itemProps.ref}
                        code={product.code}
                        isActive={productActiveIndex === index}
                        key={product.id}
                        name={product.name}
                        onCardFocus={itemProps.onFocus}
                        onCardKeyDown={itemProps.onKeyDown}
                        onSelect={() =>
                          updateDraftState((state) =>
                            selectProductForCashCloseCount(state, product),
                          )
                        }
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
              <div className="rounded-xl border border-dashed border-[var(--pos-shell-border)] bg-[var(--pos-shell-muted)] px-4 py-8 text-center text-sm text-slate-600">
                No hay productos para esta busqueda.
              </div>
            )
          ) : null}

          {isCountingStage &&
          draftState.physicalControlState === CLOSE_PHYSICAL_STATE_QUANTITY_CAPTURE &&
          quantitySelection &&
          quantityProduct ? (
            <div className="w-full max-w-5xl justify-self-center rounded-xl border border-[var(--pos-shell-border)] bg-white p-3 shadow-sm">
              <div className="grid gap-3 lg:grid-cols-[12rem_minmax(0,1fr)]">
                <CatalogVisual
                  className="min-h-[11.5rem]"
                  code={quantityProduct.code}
                  name={quantityProduct.name}
                />

                <div className="grid gap-2.5">
                  <div>
                    <div className="flex flex-wrap items-center gap-2">
                      <p className="text-base font-semibold text-slate-950">
                        {quantityProduct.name}
                      </p>
                      <span className="pos-chip" data-tone="muted">
                        {quantitySelection.productClass.name}
                      </span>
                    </div>
                  </div>

                  <div className="grid gap-2">
                    <input
                      aria-label={`Cantidad contada de ${quantityProduct.name}`}
                      className={cn(
                        "h-16 rounded-xl px-4 text-[2.25rem] font-semibold tracking-tight shadow-sm",
                        posInputClass,
                      )}
                      inputMode="decimal"
                      onChange={(event) =>
                        updateDraftState((state) =>
                          setCashClosePendingQuantityText(state, event.target.value),
                        )
                      }
                      onKeyDown={(event) => {
                        if (isSubmitKey(event)) {
                          event.preventDefault();
                          handleAddCount();
                          return;
                        }

                        if (event.key === "Escape") {
                          event.preventDefault();
                          updateDraftState((state) => goBackFromCashClosePhysicalState(state));
                          return;
                        }

                        if (event.key === "Delete") {
                          event.preventDefault();
                          updateDraftState((state) => setCashClosePendingQuantityText(state, ""));
                        }
                      }}
                      placeholder="0"
                      ref={quantityInputRef}
                      value={quantitySelection.quantityText}
                    />

                    <div className="flex flex-wrap items-center gap-2">
                      {["1", "2", "3", "6", "12"].map((preset) => (
                        <Button
                          className={cn("h-10 min-w-12 px-3", posOutlineButtonClass)}
                          key={preset}
                          onClick={() =>
                            updateDraftState((state) =>
                              setCashClosePendingQuantityText(state, preset),
                            )
                          }
                          type="button"
                        >
                          {preset}
                        </Button>
                      ))}
                    </div>

                    <div className="flex flex-wrap items-center justify-end gap-3">
                      <Button
                        className={cn("h-10 px-4", posPrimaryButtonClass)}
                        disabled={quantitySelection.quantityText.trim().length === 0}
                        onClick={handleAddCount}
                        type="button"
                      >
                        Guardar conteo
                      </Button>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          ) : null}
        </CentralWorkspaceSheet>
      </div>
      <PosConfirmationDialog
        confirmation={{
          cancelLabel: "Cancelar",
          confirmLabel: "Cerrar con mostrador vacío",
          description:
            "El turno se cerrará con el conteo monetario capturado y el conteo físico de pan registrado en cero piezas. Usa esta opción solo si no quedó pan en mostrador.",
          title: "Cerrar turno con mostrador vacío",
          tone: "warning",
        }}
        isOpen={isCloseWithoutCountDialogOpen}
        isPending={closeMutation.isPending}
        onCancel={() => setIsCloseWithoutCountDialogOpen(false)}
        onConfirm={handleCloseWithoutCount}
      />
    </>
  );
}
