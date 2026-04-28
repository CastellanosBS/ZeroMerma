import type {
  ConfirmSaleLineRequest,
  ConfirmSalePaymentRequest,
  ConfirmSaleRequest,
  PosCatalogClassView,
  PosCatalogProductView,
  SaleDetailView,
} from "../../lib/api-contracts";

export const CLASS_CAPTURE_MODE = "CLASS_CAPTURE";
export const PRODUCT_DIRECT_MODE = "PRODUCT_DIRECT";
export const CASH_PAYMENT_METHOD_CODE = "CASH";
export const CARD_PAYMENT_METHOD_CODE = "CARD";
export const MIXED_PAYMENT_METHOD_CODE = "MIXED";
export const PRIMARY_POS_PAYMENT_METHOD_CODES = [
  CASH_PAYMENT_METHOD_CODE,
  CARD_PAYMENT_METHOD_CODE,
] as const;

export const CONTROL_STATE_CLASS_SELECTION = "CLASS_SELECTION";
export const CONTROL_STATE_PRODUCT_SELECTION = "PRODUCT_SELECTION";
export const CONTROL_STATE_QUANTITY_CAPTURE = "QUANTITY_CAPTURE";
export const CONTROL_STATE_PAYMENT_CAPTURE = "PAYMENT_CAPTURE";

export type PosControlState =
  | typeof CONTROL_STATE_CLASS_SELECTION
  | typeof CONTROL_STATE_PRODUCT_SELECTION
  | typeof CONTROL_STATE_QUANTITY_CAPTURE
  | typeof CONTROL_STATE_PAYMENT_CAPTURE;

export type PosPaymentMethodCode =
  | typeof CASH_PAYMENT_METHOD_CODE
  | typeof CARD_PAYMENT_METHOD_CODE
  | typeof MIXED_PAYMENT_METHOD_CODE;

export type PosSplitPaymentMethodCode =
  | typeof CASH_PAYMENT_METHOD_CODE
  | typeof CARD_PAYMENT_METHOD_CODE;

export interface PendingSelection {
  captureMode: string;
  editingLine: PosCartLine | null;
  productClass: PosCatalogClassView;
  product: PosCatalogProductView | null;
  quantityText: string;
}

export interface PosCartLine {
  captureMode: string;
  catalogCodeSnapshot: string;
  catalogNameSnapshot: string;
  currencyCode: string;
  key: string;
  productClassCode: string;
  productClassId: string | null;
  productClassName: string;
  productCode: string | null;
  productId: string | null;
  productName: string | null;
  quantityMilliUnits: number;
  quantityText: string;
  unitPriceCents: number;
  unitPriceText: string;
}

export interface PosTerminalSnapshot {
  cartLines: PosCartLine[];
  controlState: PosControlState;
  lastCompletedSale: SaleDetailView | null;
  pendingSelection: PendingSelection | null;
  searchText: string;
}

export interface PosMixedPaymentLegDraft {
  amountText: string;
  methodCode: PosSplitPaymentMethodCode;
}

export interface PosPaymentDraft {
  cashReceivedText: string;
  mixedConfirmedLegs?: PosMixedPaymentLegDraft[];
  paymentMethodCode: PosPaymentMethodCode;
}

export interface PosPaymentComputation {
  capturedAmountCents: number;
  cashTenderedAmountCents: number;
  changeAmountCents: number;
  hasInvalidNonCashOverage: boolean;
  nonCashTenderedAmountCents: number;
  remainingAmountCents: number;
}

export interface PosCheckoutPaymentControl {
  code: PosPaymentMethodCode;
  kind: "direct" | "split";
  label: string;
}

export type PosCheckoutSummaryMetricKey = "TOTAL" | "RECEIVED" | "RESULT";
export type PosWorkObjectState =
  | "TICKET_EMPTY"
  | "TICKET_BUILDING"
  | "READY_TO_PAY"
  | "PAYING"
  | "SALE_CONFIRMED";

export function getPrimaryPosPaymentMethodCodes(): PosPaymentMethodCode[] {
  return [...PRIMARY_POS_PAYMENT_METHOD_CODES];
}

export function isSplitPaymentMethodCode(
  paymentMethodCode: PosPaymentMethodCode,
): boolean {
  return paymentMethodCode === MIXED_PAYMENT_METHOD_CODE;
}

export function usesReceivedAmountInput(
  paymentMethodCode: PosPaymentMethodCode,
): boolean {
  return (
    paymentMethodCode === CASH_PAYMENT_METHOD_CODE ||
    paymentMethodCode === MIXED_PAYMENT_METHOD_CODE
  );
}

export function getPosCheckoutPaymentControlRows(): PosCheckoutPaymentControl[][] {
  return [
    [
      {
        code: CASH_PAYMENT_METHOD_CODE,
        kind: "direct",
        label: "Efectivo",
      },
      {
        code: CARD_PAYMENT_METHOD_CODE,
        kind: "direct",
        label: "Tarjeta",
      },
    ],
    [
      {
        code: MIXED_PAYMENT_METHOD_CODE,
        kind: "split",
        label: "Cobro mixto",
      },
    ],
  ];
}

export function getPosCheckoutSummaryMetricRows(): PosCheckoutSummaryMetricKey[][] {
  return [["TOTAL", "RECEIVED"], ["RESULT"]];
}

export function hasCapturedQuantity(quantityText: string): boolean {
  const quantityMilliUnits = parseQuantityToMilliUnits(quantityText);
  return quantityMilliUnits !== null && quantityMilliUnits > 0;
}

export function getPendingCaptureTargetKey(
  pendingSelection: PendingSelection | null,
): string | null {
  if (pendingSelection === null) {
    return null;
  }

  if (pendingSelection.captureMode === PRODUCT_DIRECT_MODE) {
    return `product:${pendingSelection.product?.id ?? pendingSelection.productClass.id}`;
  }

  return `class:${pendingSelection.productClass.id}`;
}

export function getPosWorkObjectState({
  cartLineCount,
  hasCompletedSale,
  isCommitPending,
  isPaymentCaptureActive,
  isPaymentReady,
}: {
  cartLineCount: number;
  hasCompletedSale: boolean;
  isCommitPending: boolean;
  isPaymentCaptureActive: boolean;
  isPaymentReady: boolean;
}): PosWorkObjectState {
  if (isCommitPending) {
    return "PAYING";
  }

  if (hasCompletedSale && cartLineCount === 0) {
    return "SALE_CONFIRMED";
  }

  if (cartLineCount === 0) {
    return "TICKET_EMPTY";
  }

  if (isPaymentCaptureActive && isPaymentReady) {
    return "READY_TO_PAY";
  }

  return "TICKET_BUILDING";
}

export function createInitialPosTerminalState(): PosTerminalSnapshot {
  return {
    cartLines: [],
    controlState: CONTROL_STATE_CLASS_SELECTION,
    lastCompletedSale: null,
    pendingSelection: null,
    searchText: "",
  };
}

export function sanitizeQuantityInput(value: string): string {
  return sanitizeDecimalInput(value, 3);
}

export function sanitizeMoneyInput(value: string): string {
  return sanitizeDecimalInput(value, 2);
}

export function parseQuantityToMilliUnits(quantityText: string): number | null {
  return parseFixedDecimalToUnits(quantityText, 3);
}

export function parseMoneyToCents(value: string): number | null {
  return parseFixedDecimalToUnits(value, 2);
}

export function formatQuantityFromMilliUnits(value: number): string {
  return formatFixedDecimalFromUnits(value, 3);
}

export function formatMoneyFromCents(value: number): string {
  return formatFixedDecimalFromUnits(value, 2);
}

export function getLineTotalCents(line: PosCartLine): number {
  return Math.round((line.quantityMilliUnits * line.unitPriceCents) / 1000);
}

export function getCartTotalCents(lines: PosCartLine[]): number {
  return lines.reduce((sum, line) => sum + getLineTotalCents(line), 0);
}

export function getCartLineCount(lines: PosCartLine[]): number {
  return lines.length;
}

export function sortCatalogClasses(classes: PosCatalogClassView[]): PosCatalogClassView[] {
  return [...classes].sort((left, right) => {
    const modeDifference =
      getCaptureModeSortOrder(left.capture_mode_default) -
      getCaptureModeSortOrder(right.capture_mode_default);
    if (modeDifference !== 0) {
      return modeDifference;
    }

    const displayOrderDifference = left.display_order - right.display_order;
    if (displayOrderDifference !== 0) {
      return displayOrderDifference;
    }

    return left.name.localeCompare(right.name);
  });
}

export function sortCatalogProducts(products: PosCatalogProductView[]): PosCatalogProductView[] {
  return [...products].sort((left, right) => {
    const displayOrderDifference = left.display_order - right.display_order;
    if (displayOrderDifference !== 0) {
      return displayOrderDifference;
    }

    return left.name.localeCompare(right.name);
  });
}

export function beginSelectionFromClass(
  state: PosTerminalSnapshot,
  productClass: PosCatalogClassView,
): PosTerminalSnapshot {
  const nextPendingSelection: PendingSelection = {
    captureMode: productClass.capture_mode_default,
    editingLine: null,
    productClass,
    product: null,
    quantityText: "",
  };

  if (productClass.capture_mode_default === PRODUCT_DIRECT_MODE) {
    return {
      ...state,
      controlState: CONTROL_STATE_PRODUCT_SELECTION,
      lastCompletedSale: null,
      pendingSelection: nextPendingSelection,
      searchText: "",
    };
  }

  return {
    ...state,
    controlState: CONTROL_STATE_QUANTITY_CAPTURE,
    lastCompletedSale: null,
    pendingSelection: nextPendingSelection,
    searchText: "",
  };
}

export function selectProductForPending(
  state: PosTerminalSnapshot,
  product: PosCatalogProductView,
): PosTerminalSnapshot {
  if (state.pendingSelection === null) {
    throw new Error("Selecciona una clase antes de elegir un producto.");
  }

  return {
    ...state,
    controlState: CONTROL_STATE_QUANTITY_CAPTURE,
    pendingSelection: {
      ...state.pendingSelection,
      editingLine: null,
      product,
      quantityText: "",
    },
    searchText: "",
  };
}

export function beginEditingCartLine(
  state: PosTerminalSnapshot,
  lineKey: string,
): PosTerminalSnapshot {
  const line = state.cartLines.find((entry) => entry.key === lineKey);
  if (!line) {
    return state;
  }

  const productClass: PosCatalogClassView = {
    capture_mode_default: line.captureMode,
    class_capture_unit_price:
      line.captureMode === CLASS_CAPTURE_MODE ? line.unitPriceText : null,
    code: line.productClassCode,
    currency_code: line.currencyCode,
    display_order: 0,
    id: line.productClassId ?? line.key,
    name: line.productClassName,
    product_count: 0,
    quick_name: line.productClassName,
  };
  const product =
    line.captureMode === PRODUCT_DIRECT_MODE && line.productId !== null
      ? ({
          code: line.productCode ?? line.catalogCodeSnapshot,
          currency_code: line.currencyCode,
          display_order: 0,
          id: line.productId,
          name: line.productName ?? line.catalogNameSnapshot,
          quick_name: line.productName ?? line.catalogNameSnapshot,
          unit_price: line.unitPriceText,
        } satisfies PosCatalogProductView)
      : null;

  return {
    ...state,
    cartLines: state.cartLines.filter((entry) => entry.key !== lineKey),
    controlState: CONTROL_STATE_QUANTITY_CAPTURE,
    lastCompletedSale: null,
    pendingSelection: {
      captureMode: line.captureMode,
      editingLine: line,
      product,
      productClass,
      quantityText: line.quantityText,
    },
    searchText: "",
  };
}

export function goBackFromControlState(state: PosTerminalSnapshot): PosTerminalSnapshot {
  if (state.controlState === CONTROL_STATE_PRODUCT_SELECTION) {
    return {
      ...state,
      controlState: CONTROL_STATE_CLASS_SELECTION,
      pendingSelection: null,
      searchText: "",
    };
  }

  if (
    state.controlState === CONTROL_STATE_QUANTITY_CAPTURE &&
    state.pendingSelection !== null
  ) {
    if (state.pendingSelection.editingLine !== null) {
      return {
        ...state,
        cartLines: [...state.cartLines, state.pendingSelection.editingLine],
        controlState: CONTROL_STATE_CLASS_SELECTION,
        pendingSelection: null,
        searchText: "",
      };
    }

    if (state.pendingSelection.captureMode === PRODUCT_DIRECT_MODE) {
      return {
        ...state,
        controlState: CONTROL_STATE_PRODUCT_SELECTION,
        pendingSelection: {
          ...state.pendingSelection,
          editingLine: null,
          product: null,
          quantityText: "",
        },
        searchText: "",
      };
    }

    return {
      ...state,
      controlState: CONTROL_STATE_CLASS_SELECTION,
      pendingSelection: null,
      searchText: "",
    };
  }

  if (state.controlState === CONTROL_STATE_PAYMENT_CAPTURE) {
    return {
      ...state,
      controlState: CONTROL_STATE_CLASS_SELECTION,
      searchText: "",
    };
  }

  return state;
}

export function setPendingQuantityText(
  state: PosTerminalSnapshot,
  quantityText: string,
): PosTerminalSnapshot {
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

export function appendPendingQuantityCharacter(
  state: PosTerminalSnapshot,
  character: string,
): PosTerminalSnapshot {
  if (state.pendingSelection === null) {
    return state;
  }

  return setPendingQuantityText(
    state,
    `${state.pendingSelection.quantityText}${character}`,
  );
}

export function backspacePendingQuantity(state: PosTerminalSnapshot): PosTerminalSnapshot {
  if (state.pendingSelection === null) {
    return state;
  }

  return setPendingQuantityText(
    state,
    state.pendingSelection.quantityText.slice(0, -1),
  );
}

export function clearPendingQuantity(state: PosTerminalSnapshot): PosTerminalSnapshot {
  return setPendingQuantityText(state, "");
}

export function incrementPendingQuantity(state: PosTerminalSnapshot): PosTerminalSnapshot {
  if (state.pendingSelection === null) {
    return state;
  }

  const currentQuantity = parseQuantityToMilliUnits(state.pendingSelection.quantityText) ?? 0;
  return setPendingQuantityText(
    state,
    formatQuantityFromMilliUnits(currentQuantity + 1000),
  );
}

export function decrementPendingQuantity(state: PosTerminalSnapshot): PosTerminalSnapshot {
  if (state.pendingSelection === null) {
    return state;
  }

  const currentQuantity = parseQuantityToMilliUnits(state.pendingSelection.quantityText) ?? 0;
  if (currentQuantity <= 1000) {
    return setPendingQuantityText(state, "");
  }

  return setPendingQuantityText(
    state,
    formatQuantityFromMilliUnits(currentQuantity - 1000),
  );
}

export function addPendingSelectionToCart(state: PosTerminalSnapshot): PosTerminalSnapshot {
  if (state.pendingSelection === null) {
    throw new Error("Selecciona un producto o clase antes de capturar la cantidad.");
  }

  const quantityMilliUnits = parseQuantityToMilliUnits(state.pendingSelection.quantityText);
  if (quantityMilliUnits === null || quantityMilliUnits <= 0) {
    throw new Error("Captura una cantidad mayor que cero.");
  }

  const nextLine = buildCartLine(state.pendingSelection, quantityMilliUnits);
  const existingLine = state.cartLines.find((line) => line.key === nextLine.key);
  const nextCartLines = existingLine
    ? state.cartLines.map((line) =>
        line.key === nextLine.key ? mergeCartLines(line, nextLine) : line,
      )
    : [...state.cartLines, nextLine];

  return {
    ...state,
    cartLines: nextCartLines,
    controlState: CONTROL_STATE_CLASS_SELECTION,
    lastCompletedSale: null,
    pendingSelection: null,
    searchText: "",
  };
}

export function incrementCartLineQuantity(
  state: PosTerminalSnapshot,
  lineKey: string,
): PosTerminalSnapshot {
  return {
    ...state,
    cartLines: state.cartLines.map((line) =>
      line.key === lineKey
        ? updateCartLineQuantity(line, line.quantityMilliUnits + 1000)
        : line,
    ),
    lastCompletedSale: null,
  };
}

export function decrementCartLineQuantity(
  state: PosTerminalSnapshot,
  lineKey: string,
): PosTerminalSnapshot {
  return {
    ...state,
    cartLines: state.cartLines.map((line) =>
      line.key === lineKey
        ? updateCartLineQuantity(line, Math.max(line.quantityMilliUnits - 1000, 1000))
        : line,
    ),
    lastCompletedSale: null,
  };
}

export function setCartLineQuantity(
  state: PosTerminalSnapshot,
  lineKey: string,
  quantityText: string,
): PosTerminalSnapshot {
  const quantityMilliUnits = parseQuantityToMilliUnits(quantityText);
  if (quantityMilliUnits === null || quantityMilliUnits <= 0) {
    throw new Error("Captura una cantidad mayor que cero.");
  }

  return {
    ...state,
    cartLines: state.cartLines.map((line) =>
      line.key === lineKey ? updateCartLineQuantity(line, quantityMilliUnits) : line,
    ),
    lastCompletedSale: null,
  };
}

export function removeCartLine(
  state: PosTerminalSnapshot,
  lineKey: string,
): PosTerminalSnapshot {
  const nextCartLines = state.cartLines.filter((line) => line.key !== lineKey);

  if (nextCartLines.length === 0) {
    return {
      ...createInitialPosTerminalState(),
      lastCompletedSale: null,
    };
  }

  return {
    ...state,
    cartLines: nextCartLines,
    lastCompletedSale: null,
  };
}

export function repeatLastCartLine(state: PosTerminalSnapshot): PosTerminalSnapshot {
  const lastLine = state.cartLines[state.cartLines.length - 1];
  if (!lastLine) {
    return state;
  }

  return {
    ...state,
    cartLines: state.cartLines.map((line) =>
      line.key === lastLine.key
        ? updateCartLineQuantity(line, line.quantityMilliUnits + lastLine.quantityMilliUnits)
        : line,
    ),
    lastCompletedSale: null,
  };
}

export function clearCart(_state: PosTerminalSnapshot): PosTerminalSnapshot {
  void _state;
  return {
    ...createInitialPosTerminalState(),
    lastCompletedSale: null,
  };
}

export function enterPaymentCapture(state: PosTerminalSnapshot): PosTerminalSnapshot {
  if (state.cartLines.length === 0) {
    return state;
  }

  return {
    ...state,
    controlState: CONTROL_STATE_PAYMENT_CAPTURE,
    lastCompletedSale: null,
  };
}

export function markSaleCompleted(
  _state: PosTerminalSnapshot,
  sale: SaleDetailView,
): PosTerminalSnapshot {
  void _state;
  return {
    cartLines: [],
    controlState: CONTROL_STATE_CLASS_SELECTION,
    lastCompletedSale: sale,
    pendingSelection: null,
    searchText: "",
  };
}

export function dismissLastCompletedSale(state: PosTerminalSnapshot): PosTerminalSnapshot {
  return {
    ...state,
    lastCompletedSale: null,
  };
}

export function computePaymentComputation({
  cashReceivedText,
  mixedConfirmedLegs,
  mixedNonCashAmountText,
  paymentMethodCode,
  totalAmountCents,
}: {
  cashReceivedText: string;
  mixedConfirmedLegs?: PosMixedPaymentLegDraft[];
  mixedNonCashAmountText: string;
  paymentMethodCode: PosPaymentMethodCode;
  totalAmountCents: number;
}): PosPaymentComputation {
  if (paymentMethodCode === CARD_PAYMENT_METHOD_CODE) {
    return {
      capturedAmountCents: totalAmountCents,
      cashTenderedAmountCents: 0,
      changeAmountCents: 0,
      hasInvalidNonCashOverage: false,
      nonCashTenderedAmountCents: totalAmountCents,
      remainingAmountCents: 0,
    };
  }

  const cashTenderedAmountCents = parseMoneyToCents(cashReceivedText) ?? 0;
  if (paymentMethodCode === CASH_PAYMENT_METHOD_CODE) {
    const remainingAmountCents = Math.max(totalAmountCents - cashTenderedAmountCents, 0);
    return {
      capturedAmountCents: cashTenderedAmountCents,
      cashTenderedAmountCents,
      changeAmountCents: Math.max(cashTenderedAmountCents - totalAmountCents, 0),
      hasInvalidNonCashOverage: false,
      nonCashTenderedAmountCents: 0,
      remainingAmountCents,
    };
  }

  const mixedLegTotals =
    mixedConfirmedLegs?.reduce(
      (totals, leg) => {
        const amountCents = parseMoneyToCents(leg.amountText) ?? 0;
        if (leg.methodCode === CASH_PAYMENT_METHOD_CODE) {
          totals.cashTenderedAmountCents += amountCents;
        } else {
          totals.nonCashTenderedAmountCents += amountCents;
        }
        return totals;
      },
      {
        cashTenderedAmountCents: 0,
        nonCashTenderedAmountCents: 0,
      },
    ) ?? null;
  const resolvedCashTenderedAmountCents =
    mixedLegTotals?.cashTenderedAmountCents ?? cashTenderedAmountCents;
  const nonCashTenderedAmountCents =
    mixedLegTotals?.nonCashTenderedAmountCents ?? (parseMoneyToCents(mixedNonCashAmountText) ?? 0);
  const capturedAmountCents =
    resolvedCashTenderedAmountCents + nonCashTenderedAmountCents;

  return {
    capturedAmountCents,
    cashTenderedAmountCents: resolvedCashTenderedAmountCents,
    changeAmountCents: Math.max(capturedAmountCents - totalAmountCents, 0),
    hasInvalidNonCashOverage: nonCashTenderedAmountCents > totalAmountCents,
    nonCashTenderedAmountCents,
    remainingAmountCents: Math.max(totalAmountCents - capturedAmountCents, 0),
  };
}

export function buildConfirmSaleRequest(
  workstationCode: string,
  lines: PosCartLine[],
  paymentDraft: PosPaymentDraft,
): ConfirmSaleRequest {
  if (lines.length === 0) {
    throw new Error("Agrega al menos una linea antes de cobrar.");
  }

  const totalAmountCents = getCartTotalCents(lines);
  const requestLines: ConfirmSaleLineRequest[] = lines.map((line) => {
    if (line.captureMode === CLASS_CAPTURE_MODE) {
      return {
        capture_mode: line.captureMode,
        product_class_id: line.productClassId!,
        quantity: formatQuantityFromMilliUnits(line.quantityMilliUnits),
      };
    }

    return {
      capture_mode: line.captureMode,
      product_id: line.productId!,
      quantity: formatQuantityFromMilliUnits(line.quantityMilliUnits),
    };
  });

  let payments: ConfirmSalePaymentRequest[];

  if (paymentDraft.paymentMethodCode === CASH_PAYMENT_METHOD_CODE) {
    const paymentComputation = computePaymentComputation({
      cashReceivedText: paymentDraft.cashReceivedText,
      mixedNonCashAmountText: "",
      paymentMethodCode: paymentDraft.paymentMethodCode,
      totalAmountCents,
    });

    if (paymentComputation.cashTenderedAmountCents <= 0) {
      throw new Error("Captura el dinero recibido antes de confirmar el cobro.");
    }

    if (paymentComputation.remainingAmountCents > 0) {
      throw new Error("El dinero recibido es menor al total.");
    }

    payments = [
      {
        payment_method_code: CASH_PAYMENT_METHOD_CODE,
        tendered_amount: formatMoneyFromCents(paymentComputation.cashTenderedAmountCents),
      },
    ];
  } else if (
    paymentDraft.paymentMethodCode === CARD_PAYMENT_METHOD_CODE
  ) {
    payments = [
      {
        payment_method_code: paymentDraft.paymentMethodCode,
        tendered_amount: formatMoneyFromCents(totalAmountCents),
      },
    ];
  } else {
    const mixedPaymentLegs = paymentDraft.mixedConfirmedLegs ?? [];
    const confirmedMixedTotalCents = mixedPaymentLegs.reduce(
      (sum, leg) => sum + (parseMoneyToCents(leg.amountText) ?? 0),
      0,
    );
    const confirmedNonCashCents = mixedPaymentLegs.reduce(
      (sum, leg) =>
        sum +
        (leg.methodCode === CARD_PAYMENT_METHOD_CODE ? parseMoneyToCents(leg.amountText) ?? 0 : 0),
      0,
    );

    if (mixedPaymentLegs.length === 0) {
      throw new Error("Confirma al menos un tramo del cobro mixto antes de vender.");
    }

    if (confirmedNonCashCents > totalAmountCents) {
      throw new Error("La parte sin efectivo no puede exceder el total.");
    }

    if (confirmedMixedTotalCents !== totalAmountCents) {
      throw new Error("El reparto mixto no cubre el total.");
    }

    payments = mixedPaymentLegs.map((leg) => {
      const amountCents = parseMoneyToCents(leg.amountText);
      if (amountCents === null || amountCents <= 0) {
        throw new Error("Cada tramo del cobro mixto debe ser mayor que cero.");
      }

      return {
        payment_method_code: leg.methodCode,
        tendered_amount: formatMoneyFromCents(amountCents),
      };
    });
  }

  return {
    lines: requestLines,
    payments,
    workstation_code: workstationCode,
  };
}

function buildCartLine(pendingSelection: PendingSelection, quantityMilliUnits: number): PosCartLine {
  const { productClass } = pendingSelection;

  if (pendingSelection.captureMode === CLASS_CAPTURE_MODE) {
    const unitPriceText = productClass.class_capture_unit_price;
    if (!unitPriceText) {
      throw new Error(`La clase ${productClass.code} no tiene precio configurado para captura por clase.`);
    }

    return {
      captureMode: pendingSelection.captureMode,
      catalogCodeSnapshot: productClass.code,
      catalogNameSnapshot: productClass.name,
      currencyCode: productClass.currency_code,
      key: `${pendingSelection.captureMode}:${productClass.id}`,
      productClassCode: productClass.code,
      productClassId: productClass.id,
      productClassName: productClass.name,
      productCode: null,
      productId: null,
      productName: null,
      quantityMilliUnits,
      quantityText: formatQuantityFromMilliUnits(quantityMilliUnits),
      unitPriceCents: parseMoneyToCents(unitPriceText)!,
      unitPriceText,
    };
  }

  if (pendingSelection.product === null) {
    throw new Error("Selecciona un producto antes de capturar la cantidad.");
  }

  return {
    captureMode: pendingSelection.captureMode,
    catalogCodeSnapshot: pendingSelection.product.code,
    catalogNameSnapshot: pendingSelection.product.name,
    currencyCode: pendingSelection.product.currency_code,
    key: `${pendingSelection.captureMode}:${pendingSelection.product.id}`,
    productClassCode: productClass.code,
    productClassId: productClass.id,
    productClassName: productClass.name,
    productCode: pendingSelection.product.code,
    productId: pendingSelection.product.id,
    productName: pendingSelection.product.name,
    quantityMilliUnits,
    quantityText: formatQuantityFromMilliUnits(quantityMilliUnits),
    unitPriceCents: parseMoneyToCents(pendingSelection.product.unit_price)!,
    unitPriceText: pendingSelection.product.unit_price,
  };
}

function mergeCartLines(existingLine: PosCartLine, nextLine: PosCartLine): PosCartLine {
  return updateCartLineQuantity(
    existingLine,
    existingLine.quantityMilliUnits + nextLine.quantityMilliUnits,
  );
}

function updateCartLineQuantity(line: PosCartLine, quantityMilliUnits: number): PosCartLine {
  return {
    ...line,
    quantityMilliUnits,
    quantityText: formatQuantityFromMilliUnits(quantityMilliUnits),
  };
}

function getCaptureModeSortOrder(captureMode: string): number {
  return captureMode === CLASS_CAPTURE_MODE ? 0 : 1;
}

function sanitizeDecimalInput(value: string, decimalPlaces: number): string {
  let wholePart = "";
  let decimalPart = "";
  let hasDecimalSeparator = false;

  for (const character of value) {
    if (character >= "0" && character <= "9") {
      if (hasDecimalSeparator) {
        if (decimalPart.length < decimalPlaces) {
          decimalPart += character;
        }
      } else {
        wholePart += character;
      }
      continue;
    }

    if (character === "." && !hasDecimalSeparator) {
      hasDecimalSeparator = true;
    }
  }

  if (hasDecimalSeparator) {
    const normalizedWholePart = wholePart.length > 0 ? wholePart : "0";
    return decimalPart.length > 0
      ? `${normalizedWholePart}.${decimalPart}`
      : `${normalizedWholePart}.`;
  }

  return wholePart;
}

function parseFixedDecimalToUnits(value: string, decimalPlaces: number): number | null {
  const normalizedValue = value.trim();
  if (!/^\d+(\.\d+)?$/.test(normalizedValue)) {
    return null;
  }

  const [wholePart, decimalPart = ""] = normalizedValue.split(".");
  if (decimalPart.length > decimalPlaces) {
    return null;
  }

  const paddedDecimalPart = decimalPart.padEnd(decimalPlaces, "0");
  const integerUnits =
    Number.parseInt(wholePart, 10) * 10 ** decimalPlaces +
    Number.parseInt(paddedDecimalPart, 10);

  return integerUnits > 0 ? integerUnits : null;
}

function formatFixedDecimalFromUnits(value: number, decimalPlaces: number): string {
  const unitsPerWhole = 10 ** decimalPlaces;
  const wholePart = Math.floor(value / unitsPerWhole);
  const remainder = value % unitsPerWhole;

  if (remainder === 0) {
    return `${wholePart}`;
  }

  return `${wholePart}.${`${remainder}`.padStart(decimalPlaces, "0").replace(/0+$/, "")}`;
}
