import type {
  CreateCustomerOrderAdvancePaymentRequest,
  CreateCustomerOrderItemRequest,
  DeliverCustomerOrderSettlementPaymentRequest,
  OrdersCatalogClassView,
  OrdersCatalogProductView,
} from "../../lib/api-contracts";
import {
  CARD_PAYMENT_METHOD_CODE,
  CASH_PAYMENT_METHOD_CODE,
  MIXED_PAYMENT_METHOD_CODE,
  formatMoneyFromCents,
  formatQuantityFromMilliUnits,
  parseMoneyToCents,
  parseQuantityToMilliUnits,
  sanitizeMoneyInput,
  sanitizeQuantityInput,
} from "../pos-terminal/model";

export const CONTROL_STATE_CLASS_SELECTION = "CLASS_SELECTION";
export const CONTROL_STATE_PRODUCT_SELECTION = "PRODUCT_SELECTION";
export const CONTROL_STATE_QUANTITY_CAPTURE = "QUANTITY_CAPTURE";

export type OrderCreateControlState =
  | typeof CONTROL_STATE_CLASS_SELECTION
  | typeof CONTROL_STATE_PRODUCT_SELECTION
  | typeof CONTROL_STATE_QUANTITY_CAPTURE;

export interface OrderPendingSelection {
  productClass: OrdersCatalogClassView;
  product: OrdersCatalogProductView | null;
  quantityText: string;
}

export interface OrderDraftLine {
  key: string;
  productClassCode: string;
  productClassId: string;
  productClassName: string;
  productCode: string;
  productId: string;
  productName: string;
  quantityMilliUnits: number;
  quantityText: string;
  unitPriceCents: number;
  unitPriceText: string;
}

export interface OrderCreateDraftState {
  controlState: OrderCreateControlState;
  lines: OrderDraftLine[];
  pendingSelection: OrderPendingSelection | null;
  searchText: string;
}

export type OrderCreateUiState =
  | "DRAFT_EMPTY"
  | "DETAILS_PENDING"
  | "PRODUCTS_PENDING"
  | "SUMMARY_PENDING"
  | "READY_TO_SAVE"
  | "SAVING";

export function createInitialOrderCreateDraftState(): OrderCreateDraftState {
  return {
    controlState: CONTROL_STATE_CLASS_SELECTION,
    lines: [],
    pendingSelection: null,
    searchText: "",
  };
}

export function sortOrdersCatalogClasses(
  classes: OrdersCatalogClassView[],
): OrdersCatalogClassView[] {
  return [...classes].sort((left, right) => {
    const displayOrderDifference = left.display_order - right.display_order;
    if (displayOrderDifference !== 0) {
      return displayOrderDifference;
    }

    return left.name.localeCompare(right.name);
  });
}

export function sortOrdersCatalogProducts(
  products: OrdersCatalogProductView[],
): OrdersCatalogProductView[] {
  return [...products].sort((left, right) => {
    const displayOrderDifference = left.display_order - right.display_order;
    if (displayOrderDifference !== 0) {
      return displayOrderDifference;
    }

    return left.name.localeCompare(right.name);
  });
}

export function selectClassForOrder(
  state: OrderCreateDraftState,
  productClass: OrdersCatalogClassView,
): OrderCreateDraftState {
  return {
    ...state,
    controlState: CONTROL_STATE_PRODUCT_SELECTION,
    pendingSelection: {
      productClass,
      product: null,
      quantityText: "",
    },
    searchText: "",
  };
}

export function selectProductForOrder(
  state: OrderCreateDraftState,
  product: OrdersCatalogProductView,
): OrderCreateDraftState {
  if (state.pendingSelection === null) {
    throw new Error("Selecciona una clase antes de elegir un producto.");
  }

  return {
    ...state,
    controlState: CONTROL_STATE_QUANTITY_CAPTURE,
    pendingSelection: {
      ...state.pendingSelection,
      product,
      quantityText: "",
    },
    searchText: "",
  };
}

export function goBackFromOrderControlState(state: OrderCreateDraftState): OrderCreateDraftState {
  if (state.controlState === CONTROL_STATE_PRODUCT_SELECTION) {
    return {
      ...state,
      controlState: CONTROL_STATE_CLASS_SELECTION,
      pendingSelection: null,
      searchText: "",
    };
  }

  if (state.controlState === CONTROL_STATE_QUANTITY_CAPTURE) {
    return {
      ...state,
      controlState: CONTROL_STATE_PRODUCT_SELECTION,
      pendingSelection:
        state.pendingSelection === null
          ? null
          : {
              ...state.pendingSelection,
              product: null,
              quantityText: "",
            },
      searchText: "",
    };
  }

  return state;
}

export function setPendingQuantityText(
  state: OrderCreateDraftState,
  quantityText: string,
): OrderCreateDraftState {
  if (state.pendingSelection === null) {
    return state;
  }

  return {
    ...state,
    pendingSelection: {
      ...state.pendingSelection,
      quantityText: sanitizeQuantityInput(quantityText),
    },
  };
}

export function addPendingSelectionLine(state: OrderCreateDraftState): OrderCreateDraftState {
  if (state.pendingSelection === null || state.pendingSelection.product === null) {
    throw new Error("Selecciona el producto exacto antes de agregar la linea.");
  }

  const quantityMilliUnits = parseQuantityToMilliUnits(state.pendingSelection.quantityText);
  if (quantityMilliUnits === null || quantityMilliUnits <= 0) {
    throw new Error("Captura una cantidad mayor que cero.");
  }

  const nextLine = buildDraftLine(state.pendingSelection, quantityMilliUnits);
  const existingLine = state.lines.find((line) => line.key === nextLine.key);
  const nextLines = existingLine
    ? state.lines.map((line) =>
        line.key === nextLine.key
          ? updateOrderLineQuantity(line, line.quantityMilliUnits + nextLine.quantityMilliUnits)
          : line,
      )
    : [...state.lines, nextLine];

  return {
    ...state,
    controlState: CONTROL_STATE_CLASS_SELECTION,
    lines: nextLines,
    pendingSelection: null,
    searchText: "",
  };
}

export function updateOrderLineQuantity(
  line: OrderDraftLine,
  quantityMilliUnits: number,
): OrderDraftLine {
  return {
    ...line,
    quantityMilliUnits,
    quantityText: formatQuantityFromMilliUnits(quantityMilliUnits),
  };
}

export function removeOrderLine(lines: OrderDraftLine[], lineKey: string): OrderDraftLine[] {
  return lines.filter((line) => line.key !== lineKey);
}

export function getOrderLineCount(lines: OrderDraftLine[]): number {
  return lines.length;
}

export function getOrderTotalUnitsMilli(lines: OrderDraftLine[]): number {
  return lines.reduce((sum, line) => sum + line.quantityMilliUnits, 0);
}

export function getOrderSubtotalCents(lines: OrderDraftLine[]): number {
  return lines.reduce((sum, line) => sum + getOrderLineTotalCents(line), 0);
}

export function getOrderLineTotalCents(line: OrderDraftLine): number {
  return Math.round((line.quantityMilliUnits * line.unitPriceCents) / 1000);
}

export function getAdvanceAmountCents(advanceAmountText: string): number {
  return parseMoneyToCents(sanitizeMoneyInput(advanceAmountText)) ?? 0;
}

export function getOrderAdvanceAmountCents({
  advanceAmountText,
  mixedCardAmountText,
  mixedCashAmountText,
  paymentMethodCode,
}: {
  advanceAmountText: string;
  mixedCardAmountText: string;
  mixedCashAmountText: string;
  paymentMethodCode: string;
}): number {
  if (paymentMethodCode === MIXED_PAYMENT_METHOD_CODE) {
    return (
      (parseMoneyToCents(sanitizeMoneyInput(mixedCashAmountText)) ?? 0) +
      (parseMoneyToCents(sanitizeMoneyInput(mixedCardAmountText)) ?? 0)
    );
  }

  return getAdvanceAmountCents(advanceAmountText);
}

export function buildCreateOrderAdvancePayments({
  advanceAmountText,
  mixedCardAmountText,
  mixedCashAmountText,
  paymentMethodCode,
}: {
  advanceAmountText: string;
  mixedCardAmountText: string;
  mixedCashAmountText: string;
  paymentMethodCode: string;
}): CreateCustomerOrderAdvancePaymentRequest[] {
  if (paymentMethodCode === MIXED_PAYMENT_METHOD_CODE) {
    const payments: CreateCustomerOrderAdvancePaymentRequest[] = [];
    const cashAmountCents = parseMoneyToCents(sanitizeMoneyInput(mixedCashAmountText)) ?? 0;
    const cardAmountCents = parseMoneyToCents(sanitizeMoneyInput(mixedCardAmountText)) ?? 0;

    if (cashAmountCents > 0) {
      payments.push({
        amount: formatMoneyFromCents(cashAmountCents),
        payment_method_code: CASH_PAYMENT_METHOD_CODE,
      });
    }

    if (cardAmountCents > 0) {
      payments.push({
        amount: formatMoneyFromCents(cardAmountCents),
        payment_method_code: CARD_PAYMENT_METHOD_CODE,
      });
    }

    return payments;
  }

  const advanceAmountCents = getAdvanceAmountCents(advanceAmountText);
  if (advanceAmountCents <= 0 || paymentMethodCode.trim().length === 0) {
    return [];
  }

  // Direct advance methods are recorded canonically from advance_amount +
  // advance_payment_method_code. The breakdown payload is reserved for mixed only.
  return [];
}

export function buildDeliverOrderSettlementPayments({
  mixedCardAmountText,
  mixedCashAmountText,
  paymentMethodCode,
}: {
  mixedCardAmountText: string;
  mixedCashAmountText: string;
  paymentMethodCode: string;
}): DeliverCustomerOrderSettlementPaymentRequest[] {
  if (paymentMethodCode !== MIXED_PAYMENT_METHOD_CODE) {
    return [];
  }

  const payments: DeliverCustomerOrderSettlementPaymentRequest[] = [];
  const cashAmountCents = parseMoneyToCents(sanitizeMoneyInput(mixedCashAmountText)) ?? 0;
  const cardAmountCents = parseMoneyToCents(sanitizeMoneyInput(mixedCardAmountText)) ?? 0;

  if (cashAmountCents > 0) {
    payments.push({
      amount: formatMoneyFromCents(cashAmountCents),
      payment_method_code: CASH_PAYMENT_METHOD_CODE,
    });
  }

  if (cardAmountCents > 0) {
    payments.push({
      amount: formatMoneyFromCents(cardAmountCents),
      payment_method_code: CARD_PAYMENT_METHOD_CODE,
    });
  }

  return payments;
}

export function getRemainingBalanceCents(
  lines: OrderDraftLine[],
  advanceAmountCents: number,
): number {
  return Math.max(getOrderSubtotalCents(lines) - advanceAmountCents, 0);
}

export function getOrderAdvanceValidationMessage({
  advanceAmountText,
  advancePaymentMethodCode,
  mixedCardAmountText,
  mixedCashAmountText,
  hasNegativeAdvanceAttempt = false,
  lines,
}: {
  advanceAmountText: string;
  advancePaymentMethodCode: string;
  mixedCardAmountText: string;
  mixedCashAmountText: string;
  hasNegativeAdvanceAttempt?: boolean;
  lines: OrderDraftLine[];
}): string | null {
  if (hasNegativeAdvanceAttempt) {
    return "El anticipo no puede ser negativo.";
  }

  const subtotalCents = getOrderSubtotalCents(lines);
  const advanceCents = getOrderAdvanceAmountCents({
    advanceAmountText,
    mixedCardAmountText,
    mixedCashAmountText,
    paymentMethodCode: advancePaymentMethodCode,
  });

  if (advanceCents > subtotalCents) {
    return "El anticipo no puede exceder el total.";
  }

  if (advanceCents > 0 && advancePaymentMethodCode.trim().length === 0) {
    return "Selecciona el metodo del anticipo.";
  }

  if (advancePaymentMethodCode === MIXED_PAYMENT_METHOD_CODE && advanceCents > 0) {
    const payments = buildCreateOrderAdvancePayments({
      advanceAmountText,
      mixedCardAmountText,
      mixedCashAmountText,
      paymentMethodCode: advancePaymentMethodCode,
    });
    if (payments.length !== 2) {
      return "Captura efectivo y tarjeta para el anticipo mixto.";
    }
  }

  return null;
}

export function getOrderCreateBlockingMessage({
  advanceAmountText,
  advancePaymentMethodCode,
  customerName,
  customerPhone,
  mixedCardAmountText,
  mixedCashAmountText,
  hasNegativeAdvanceAttempt = false,
  lines,
  requestedForInput,
}: {
  advanceAmountText: string;
  advancePaymentMethodCode: string;
  customerName: string;
  customerPhone: string;
  mixedCardAmountText: string;
  mixedCashAmountText: string;
  hasNegativeAdvanceAttempt?: boolean;
  lines: OrderDraftLine[];
  requestedForInput: string;
}): string | null {
  if (customerName.trim().length === 0) {
    return "Captura el cliente antes de guardar.";
  }

  if (customerPhone.trim().length === 0) {
    return "Captura el telefono antes de guardar.";
  }

  if (requestedForInput.trim().length === 0) {
    return "Captura la fecha de recoleccion antes de guardar.";
  }

  if (lines.length === 0) {
    return "Agrega al menos un producto para continuar.";
  }

  return getOrderAdvanceValidationMessage({
    advanceAmountText,
    advancePaymentMethodCode,
    mixedCardAmountText,
    mixedCashAmountText,
    hasNegativeAdvanceAttempt,
    lines,
  });
}

export function getOrderCreateChecklistMessages({
  advanceAmountText,
  advancePaymentMethodCode,
  customerName,
  customerPhone,
  mixedCardAmountText,
  mixedCashAmountText,
  hasNegativeAdvanceAttempt = false,
  lines,
  requestedForInput,
}: {
  advanceAmountText: string;
  advancePaymentMethodCode: string;
  customerName: string;
  customerPhone: string;
  mixedCardAmountText: string;
  mixedCashAmountText: string;
  hasNegativeAdvanceAttempt?: boolean;
  lines: OrderDraftLine[];
  requestedForInput: string;
}): string[] {
  const messages: string[] = [];

  if (customerName.trim().length === 0) {
    messages.push("Falta cliente.");
  }

  if (customerPhone.trim().length === 0) {
    messages.push("Falta telefono.");
  }

  if (requestedForInput.trim().length === 0) {
    messages.push("Falta fecha de recoleccion.");
  }

  if (lines.length === 0) {
    messages.push("Agrega al menos una linea.");
  }

  const advanceMessage = getOrderAdvanceValidationMessage({
    advanceAmountText,
    advancePaymentMethodCode,
    mixedCardAmountText,
    mixedCashAmountText,
    hasNegativeAdvanceAttempt,
    lines,
  });
  if (advanceMessage) {
    messages.push(advanceMessage);
  }

  return messages;
}

export function getOrderCreateUiState({
  customerName,
  customerPhone,
  hasBlockingMessage,
  isSaving,
  lineCount,
  requestedForInput,
}: {
  customerName: string;
  customerPhone: string;
  hasBlockingMessage: boolean;
  isSaving: boolean;
  lineCount: number;
  requestedForInput: string;
}): OrderCreateUiState {
  if (isSaving) {
    return "SAVING";
  }

  if (
    customerName.trim().length === 0 &&
    customerPhone.trim().length === 0 &&
    requestedForInput.trim().length === 0 &&
    lineCount === 0
  ) {
    return "DRAFT_EMPTY";
  }

  if (
    customerName.trim().length === 0 ||
    customerPhone.trim().length === 0 ||
    requestedForInput.trim().length === 0
  ) {
    return "DETAILS_PENDING";
  }

  if (lineCount === 0) {
    return "PRODUCTS_PENDING";
  }

  if (hasBlockingMessage) {
    return "SUMMARY_PENDING";
  }

  return "READY_TO_SAVE";
}

export function buildCreateOrderItems(lines: OrderDraftLine[]): CreateCustomerOrderItemRequest[] {
  if (lines.length === 0) {
    throw new Error("Agrega al menos un producto antes de guardar el pedido.");
  }

  return lines.map((line) => ({
    product_id: line.productId,
    quantity: formatQuantityFromMilliUnits(line.quantityMilliUnits),
  }));
}

export function formatAdvanceAmount(advanceAmountText: string): string {
  return formatMoneyFromCents(getAdvanceAmountCents(advanceAmountText));
}

function buildDraftLine(
  pendingSelection: OrderPendingSelection,
  quantityMilliUnits: number,
): OrderDraftLine {
  if (pendingSelection.product === null) {
    throw new Error("Selecciona el producto exacto antes de agregar la linea.");
  }

  const unitPriceCents = parseMoneyToCents(String(pendingSelection.product.unit_price));
  if (unitPriceCents === null) {
    throw new Error("No fue posible interpretar el precio del producto.");
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
    unitPriceCents,
    unitPriceText: formatMoneyFromCents(unitPriceCents),
  };
}
