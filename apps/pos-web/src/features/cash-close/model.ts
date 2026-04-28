import type {
  CashClosePreviewResponse,
  CashClosePaymentMethodCatalogView,
  CashClosePreviewRequest,
  OperationsCatalogClassView,
  OperationsCatalogProductView,
} from "../../lib/api-contracts";
import {
  formatQuantityFromMilliUnits,
  parseQuantityToMilliUnits,
  sanitizeQuantityInput,
} from "../pos-terminal/model";

export const CLOSE_SECTION_CONTEXT = "CONTEXT";
export const CLOSE_SECTION_FINANCIAL = "FINANCIAL";
export const CLOSE_SECTION_PHYSICAL = "PHYSICAL";
export const CLOSE_SECTION_RECONCILIATION = "RECONCILIATION";
export const CLOSE_SECTION_REVIEW = "REVIEW";
export const CLOSE_PHYSICAL_STATE_CLASS_SELECTION = "CLASS_SELECTION";
export const CLOSE_PHYSICAL_STATE_PRODUCT_SELECTION = "PRODUCT_SELECTION";
export const CLOSE_PHYSICAL_STATE_QUANTITY_CAPTURE = "QUANTITY_CAPTURE";

export type CashCloseSection =
  | typeof CLOSE_SECTION_CONTEXT
  | typeof CLOSE_SECTION_FINANCIAL
  | typeof CLOSE_SECTION_PHYSICAL
  | typeof CLOSE_SECTION_RECONCILIATION
  | typeof CLOSE_SECTION_REVIEW;

export type CashClosePhysicalControlState =
  | typeof CLOSE_PHYSICAL_STATE_CLASS_SELECTION
  | typeof CLOSE_PHYSICAL_STATE_PRODUCT_SELECTION
  | typeof CLOSE_PHYSICAL_STATE_QUANTITY_CAPTURE;

export interface CashClosePendingCountSelection {
  productClass: OperationsCatalogClassView;
  product: OperationsCatalogProductView | null;
  quantityText: string;
}

export interface CashCloseCountedProductLine {
  key: string;
  productClassCode: string;
  productClassId: string;
  productClassName: string;
  productCode: string;
  productId: string;
  productName: string;
  quantityMilliUnits: number;
  quantityText: string;
}

export interface CashCloseDraftState {
  countedPaymentAmounts: Record<string, string>;
  countedProductDraftLines: CashCloseCountedProductLine[];
  physicalControlState: CashClosePhysicalControlState;
  physicalPendingSelection: CashClosePendingCountSelection | null;
  physicalSearchText: string;
}

interface SyncCashCloseDraftInput {
  paymentMethodCatalog: CashClosePaymentMethodCatalogView[];
}

export interface CashCloseDisplayPaymentMethodRow {
  countedAmountCents: number;
  countedAmountText: string;
  isExpectedSupported: boolean;
  key: string;
}

export type CashCloseUiState =
  | "LOADING_CONTEXT"
  | "CONTEXT_REVIEW"
  | "FINANCIAL_COUNTING"
  | "PHYSICAL_COUNTING"
  | "RECONCILING"
  | "REVIEW_AND_CLOSE"
  | "HAS_WARNINGS"
  | "HAS_HARD_BLOCKERS"
  | "READY_TO_CLOSE"
  | "CLOSING"
  | "CLOSED"
  | "ERROR";

export type CashCloseFindingSeverity = "INFO" | "WARNING" | "BLOCKER";
export type CashCloseCountValueState = "PENDING" | "CAPTURED";

export function createInitialCashCloseDraftState(): CashCloseDraftState {
  return {
    countedPaymentAmounts: {},
    countedProductDraftLines: [],
    physicalControlState: CLOSE_PHYSICAL_STATE_CLASS_SELECTION,
    physicalPendingSelection: null,
    physicalSearchText: "",
  };
}

export function sanitizeMoneyInput(value: string): string {
  return sanitizeScaledDecimalInput(value, 2);
}

export function sanitizeCloseQuantityInput(value: string): string {
  return sanitizeQuantityInput(value);
}

export function setCashClosePhysicalSearchText(
  state: CashCloseDraftState,
  searchText: string,
): CashCloseDraftState {
  return {
    ...state,
    physicalSearchText: searchText,
  };
}

export function selectClassForCashCloseCount(
  state: CashCloseDraftState,
  productClass: OperationsCatalogClassView,
): CashCloseDraftState {
  return {
    ...state,
    physicalControlState: CLOSE_PHYSICAL_STATE_PRODUCT_SELECTION,
    physicalPendingSelection: {
      productClass,
      product: null,
      quantityText: "",
    },
    physicalSearchText: "",
  };
}

export function selectProductForCashCloseCount(
  state: CashCloseDraftState,
  product: OperationsCatalogProductView,
): CashCloseDraftState {
  if (state.physicalPendingSelection === null) {
    throw new Error("Selecciona una clase antes de elegir un producto.");
  }

  return {
    ...state,
    physicalControlState: CLOSE_PHYSICAL_STATE_QUANTITY_CAPTURE,
    physicalPendingSelection: {
      ...state.physicalPendingSelection,
      product,
      quantityText: state.physicalPendingSelection.quantityText,
    },
    physicalSearchText: "",
  };
}

export function goBackFromCashClosePhysicalState(
  state: CashCloseDraftState,
): CashCloseDraftState {
  if (state.physicalControlState === CLOSE_PHYSICAL_STATE_PRODUCT_SELECTION) {
    return {
      ...state,
      physicalControlState: CLOSE_PHYSICAL_STATE_CLASS_SELECTION,
      physicalPendingSelection: null,
      physicalSearchText: "",
    };
  }

  if (state.physicalControlState === CLOSE_PHYSICAL_STATE_QUANTITY_CAPTURE) {
    return {
      ...state,
      physicalControlState: CLOSE_PHYSICAL_STATE_PRODUCT_SELECTION,
      physicalPendingSelection:
        state.physicalPendingSelection === null
          ? null
          : {
              ...state.physicalPendingSelection,
              product: null,
              quantityText: "",
            },
      physicalSearchText: "",
    };
  }

  return state;
}

export function setCashClosePendingQuantityText(
  state: CashCloseDraftState,
  quantityText: string,
): CashCloseDraftState {
  if (state.physicalPendingSelection === null) {
    return state;
  }

  return {
    ...state,
    physicalPendingSelection: {
      ...state.physicalPendingSelection,
      quantityText: sanitizeCloseQuantityInput(quantityText),
    },
  };
}

export function addCashClosePendingCountLine(
  state: CashCloseDraftState,
): CashCloseDraftState {
  if (
    state.physicalPendingSelection === null ||
    state.physicalPendingSelection.product === null
  ) {
    throw new Error("Selecciona el producto exacto antes de agregar la linea.");
  }

  const quantityMilliUnits = parseQuantityToMilliUnits(
    state.physicalPendingSelection.quantityText,
  );
  if (quantityMilliUnits === null || quantityMilliUnits <= 0) {
    throw new Error("Captura una cantidad mayor que cero.");
  }

  const nextLine = buildCashCloseCountedProductLine(
    state.physicalPendingSelection,
    quantityMilliUnits,
  );
  const existingLine = state.countedProductDraftLines.find(
    (line) => line.key === nextLine.key,
  );
  const nextLines = existingLine
    ? state.countedProductDraftLines.map((line) =>
        line.key === nextLine.key
          ? updateCashCloseCountedLineQuantity(
              line,
              line.quantityMilliUnits + nextLine.quantityMilliUnits,
            )
          : line,
      )
    : [...state.countedProductDraftLines, nextLine];

  return {
    ...state,
    countedProductDraftLines: nextLines,
    physicalControlState: CLOSE_PHYSICAL_STATE_CLASS_SELECTION,
    physicalPendingSelection: null,
    physicalSearchText: "",
  };
}

export function updateCashCloseCountedLineQuantity(
  line: CashCloseCountedProductLine,
  quantityMilliUnits: number,
): CashCloseCountedProductLine {
  return {
    ...line,
    quantityMilliUnits,
    quantityText: formatQuantityFromMilliUnits(quantityMilliUnits),
  };
}

export function removeCashCloseCountedLine(
  lines: CashCloseCountedProductLine[],
  lineKey: string,
): CashCloseCountedProductLine[] {
  return lines.filter((line) => line.key !== lineKey);
}

export function getCountedProductQuantityMap(
  lines: CashCloseCountedProductLine[],
): Record<string, string> {
  return Object.fromEntries(
    lines.map((line) => [line.productId, line.quantityText]),
  );
}

export function syncCashCloseDraftState(
  currentState: CashCloseDraftState,
  input: SyncCashCloseDraftInput,
): CashCloseDraftState {
  const nextState: CashCloseDraftState = {
    countedPaymentAmounts: { ...currentState.countedPaymentAmounts },
    countedProductDraftLines: [...currentState.countedProductDraftLines],
    physicalControlState: currentState.physicalControlState,
    physicalPendingSelection: currentState.physicalPendingSelection,
    physicalSearchText: currentState.physicalSearchText,
  };

  for (const paymentMethod of input.paymentMethodCatalog) {
    nextState.countedPaymentAmounts[paymentMethod.payment_method_code] ??= "";
  }

  return nextState;
}

export function buildCashClosePreviewRequest(
  workstationCode: string,
  draftState: Pick<
    CashCloseDraftState,
    "countedPaymentAmounts" | "countedProductDraftLines"
  >,
): CashClosePreviewRequest {
  const countedProductQuantities = getCountedProductQuantityMap(
    draftState.countedProductDraftLines,
  );

  return {
    workstation_code: workstationCode,
    counted_payment_methods: Object.entries(draftState.countedPaymentAmounts)
      .map(([paymentMethodCode, countedAmountText]) => ({
        countedAmountCents: parseScaledDecimalToUnits(countedAmountText, 2),
        paymentMethodCode,
      }))
      .filter(
        (
          row,
        ): row is {
          countedAmountCents: number;
          paymentMethodCode: string;
        } => row.countedAmountCents !== null,
      )
      .map((row) => ({
        payment_method_code: row.paymentMethodCode,
        counted_amount: formatMoneyFromCents(row.countedAmountCents),
      })),
    counted_product_lines: Object.entries(countedProductQuantities)
      .map(([productId, quantityText]) => ({
        productId,
        quantityUnits: parseScaledDecimalToUnits(quantityText, 3),
      }))
      .filter(
        (
          row,
        ): row is {
          productId: string;
          quantityUnits: number;
        } => row.quantityUnits !== null,
      )
      .map((row) => ({
        product_id: row.productId,
        counted_quantity: formatQuantityFromMilliUnits(row.quantityUnits),
      })),
  };
}

export function getDraftPaymentMethodRows(
  paymentMethodCatalog: CashClosePaymentMethodCatalogView[],
  countedPaymentAmounts: Record<string, string>,
): CashCloseDisplayPaymentMethodRow[] {
  return paymentMethodCatalog.map((paymentMethod) => ({
    countedAmountCents:
      parseScaledDecimalToUnits(countedPaymentAmounts[paymentMethod.payment_method_code] ?? "", 2) ??
      0,
    countedAmountText: countedPaymentAmounts[paymentMethod.payment_method_code] ?? "",
    isExpectedSupported: paymentMethod.is_expected_supported,
    key: paymentMethod.payment_method_code,
  }));
}

export function getCashCloseCountValueState(value: string): CashCloseCountValueState {
  return value.trim().length === 0 ? "PENDING" : "CAPTURED";
}

export function hasCashCloseExpectedPaymentCounts(
  paymentMethodCatalog: CashClosePaymentMethodCatalogView[],
  countedPaymentAmounts: Record<string, string>,
): boolean {
  const expectedPaymentMethods = paymentMethodCatalog.filter(
    (paymentMethod) => paymentMethod.is_expected_supported,
  );

  if (expectedPaymentMethods.length === 0) {
    return false;
  }

  return expectedPaymentMethods.every(
    (paymentMethod) =>
      getCashCloseCountValueState(
        countedPaymentAmounts[paymentMethod.payment_method_code] ?? "",
      ) === "CAPTURED",
  );
}

export function hasCashClosePhysicalCounts(draftState: CashCloseDraftState): boolean {
  return draftState.countedProductDraftLines.length > 0;
}

export function getCashCloseBlockingReason({
  draftState,
  hasOpenCashSession,
  paymentMethodCatalog,
  previewResult,
}: {
  draftState: CashCloseDraftState;
  hasOpenCashSession: boolean;
  paymentMethodCatalog: CashClosePaymentMethodCatalogView[];
  previewResult: Pick<CashClosePreviewResponse, "blockers"> | null;
}): string | null {
  if (!hasOpenCashSession) {
    return "No hay una sesion abierta para cerrar.";
  }

  if (!hasCashCloseExpectedPaymentCounts(paymentMethodCatalog, draftState.countedPaymentAmounts)) {
    return "Falta capturar efectivo contado.";
  }

  if (!hasCashClosePhysicalCounts(draftState)) {
    return "Falta conteo fisico.";
  }

  return previewResult?.blockers[0]?.message ?? null;
}

export function getCashCloseUiState({
  activeSection,
  draftState,
  hasClosedSuccessfully,
  hasOpenCashSession,
  hasSubmitError,
  isClosing,
  isLoadingContext,
  isPreviewPending,
  paymentMethodCatalog,
  previewResult,
}: {
  activeSection: CashCloseSection;
  draftState: CashCloseDraftState;
  hasClosedSuccessfully: boolean;
  hasOpenCashSession: boolean;
  hasSubmitError: boolean;
  isClosing: boolean;
  isLoadingContext: boolean;
  isPreviewPending: boolean;
  paymentMethodCatalog: CashClosePaymentMethodCatalogView[];
  previewResult: Pick<
    CashClosePreviewResponse,
    "blockers" | "reconciliation_status" | "warnings"
  > | null;
}): CashCloseUiState {
  if (isLoadingContext) {
    return "LOADING_CONTEXT";
  }

  if (hasSubmitError) {
    return "ERROR";
  }

  if (isClosing) {
    return "CLOSING";
  }

  if (hasClosedSuccessfully) {
    return "CLOSED";
  }

  if (!hasOpenCashSession) {
    return "CONTEXT_REVIEW";
  }

  if (activeSection === CLOSE_SECTION_CONTEXT) {
    return "CONTEXT_REVIEW";
  }

  if (activeSection === CLOSE_SECTION_FINANCIAL) {
    return "FINANCIAL_COUNTING";
  }

  if (activeSection === CLOSE_SECTION_PHYSICAL) {
    return "PHYSICAL_COUNTING";
  }

  if (activeSection === CLOSE_SECTION_RECONCILIATION && isPreviewPending) {
    return "RECONCILING";
  }

  if (previewResult?.blockers.length) {
    return "HAS_HARD_BLOCKERS";
  }

  if (
    previewResult?.reconciliation_status === "READY" &&
    previewResult.warnings.length === 0 &&
    hasCashCloseExpectedPaymentCounts(paymentMethodCatalog, draftState.countedPaymentAmounts) &&
    hasCashClosePhysicalCounts(draftState)
  ) {
    return "READY_TO_CLOSE";
  }

  if (previewResult?.warnings.length) {
    return "HAS_WARNINGS";
  }

  return "REVIEW_AND_CLOSE";
}

export function getDraftCountedCashCents(
  countedPaymentAmounts: Record<string, string>,
): number {
  return parseScaledDecimalToUnits(countedPaymentAmounts.CASH ?? "", 2) ?? 0;
}

export function getDraftCountedTotalCents(
  countedPaymentAmounts: Record<string, string>,
): number {
  return Object.values(countedPaymentAmounts).reduce((total, amountText) => {
    return total + (parseScaledDecimalToUnits(amountText, 2) ?? 0);
  }, 0);
}

export function getCountedProductRowCount(draftState: CashCloseDraftState): number {
  return draftState.countedProductDraftLines.length;
}

export function getCountedProductTotalQuantityText(
  draftState: CashCloseDraftState,
): string {
  const totalMilliUnits = draftState.countedProductDraftLines.reduce(
    (runningTotal, line) => runningTotal + line.quantityMilliUnits,
    0,
  );

  return formatQuantityFromMilliUnits(totalMilliUnits);
}

export function absoluteDecimalString(value: string): string {
  return value.startsWith("-") ? value.slice(1) : value;
}

export function parseScaledDecimalToUnits(
  value: string,
  decimalPlaces: number,
): number | null {
  const normalizedValue = value.trim();
  if (normalizedValue.length === 0) {
    return null;
  }

  if (!/^\d+(\.\d+)?$/.test(normalizedValue)) {
    return null;
  }

  const [wholePart, decimalPart = ""] = normalizedValue.split(".");
  if (decimalPart.length > decimalPlaces) {
    return null;
  }

  const paddedDecimalPart = decimalPart.padEnd(decimalPlaces, "0");
  return (
    Number.parseInt(wholePart, 10) * 10 ** decimalPlaces +
    Number.parseInt(paddedDecimalPart, 10)
  );
}

function sanitizeScaledDecimalInput(value: string, decimalPlaces: number): string {
  let normalized = "";
  let hasDecimalSeparator = false;

  for (const character of value) {
    if (character >= "0" && character <= "9") {
      const currentDecimalPartLength = normalized.includes(".")
        ? normalized.split(".")[1]?.length ?? 0
        : 0;
      if (!hasDecimalSeparator || currentDecimalPartLength < decimalPlaces) {
        normalized += character;
      }
      continue;
    }

    if (character === "." && !hasDecimalSeparator) {
      hasDecimalSeparator = true;
      normalized += ".";
    }
  }

  return normalized;
}

function formatMoneyFromCents(cents: number): string {
  const wholePart = Math.floor(cents / 100);
  const decimalPart = String(cents % 100).padStart(2, "0");
  return `${wholePart}.${decimalPart}`;
}

function buildCashCloseCountedProductLine(
  pendingSelection: CashClosePendingCountSelection,
  quantityMilliUnits: number,
): CashCloseCountedProductLine {
  if (pendingSelection.product === null) {
    throw new Error("Selecciona el producto exacto antes de agregar la linea.");
  }

  return {
    key: pendingSelection.product.id,
    productClassCode: pendingSelection.productClass.code,
    productClassId: pendingSelection.productClass.id,
    productClassName: pendingSelection.productClass.name,
    productCode: pendingSelection.product.code,
    productId: pendingSelection.product.id,
    productName: pendingSelection.product.name,
    quantityMilliUnits,
    quantityText: formatQuantityFromMilliUnits(quantityMilliUnits),
  };
}
