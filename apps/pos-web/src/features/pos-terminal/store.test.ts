import { describe, expect, it } from "vitest";

import type { PosCatalogClassView, PosCatalogProductView } from "../../lib/api-contracts";
import { usePosTerminalStore } from "./store";
import type { SaleIntentionMetadata } from "./sale-confirmation-intent";
import {
  addPendingSelectionToCart,
  beginEditingCartLine,
  beginSelectionFromClass,
  buildConfirmSaleRequest,
  CARD_PAYMENT_METHOD_CODE,
  CASH_PAYMENT_METHOD_CODE,
  CLASS_CAPTURE_MODE,
  computePaymentComputation,
  CONTROL_STATE_CLASS_SELECTION,
  CONTROL_STATE_PAYMENT_CAPTURE,
  CONTROL_STATE_PRODUCT_SELECTION,
  CONTROL_STATE_QUANTITY_CAPTURE,
  createInitialPosTerminalState,
  enterPaymentCapture,
  formatQuantityFromMilliUnits,
  getCartTotalCents,
  getPendingCaptureTargetKey,
  getPosCheckoutPaymentControlRows,
  getPosCheckoutSummaryMetricRows,
  getPosWorkObjectState,
  hasCapturedQuantity,
  isSplitPaymentMethodCode,
  MIXED_PAYMENT_METHOD_CODE,
  PRODUCT_DIRECT_MODE,
  repeatLastCartLine,
  selectProductForPending,
  sortCatalogClasses,
  usesReceivedAmountInput,
} from "./model";

const classCaptureClass: PosCatalogClassView = {
  capture_mode_default: CLASS_CAPTURE_MODE,
  class_capture_unit_price: "12.00",
  code: "PAN-DULCE",
  currency_code: "MXN",
  display_order: 20,
  id: "class-pan-dulce",
  name: "Pan dulce",
  product_count: 0,
  quick_name: "Dulce",
};

const bolilloClass: PosCatalogClassView = {
  capture_mode_default: CLASS_CAPTURE_MODE,
  class_capture_unit_price: "3.00",
  code: "BOLILLO",
  currency_code: "MXN",
  display_order: 10,
  id: "class-bolillo",
  name: "Bolillo",
  product_count: 0,
  quick_name: "Bolillo",
};

const productDirectClass: PosCatalogClassView = {
  capture_mode_default: PRODUCT_DIRECT_MODE,
  class_capture_unit_price: null,
  code: "BEBIDAS",
  currency_code: "MXN",
  display_order: 110,
  id: "class-bebidas",
  name: "Bebidas",
  product_count: 2,
  quick_name: "Bebidas",
};

const productDirectProduct: PosCatalogProductView = {
  is_inventory_tracked: true,
  lot_tracking_enabled: false,
  available_quantity: "100.000",
  reserved_quantity: "0.000",
  available_lots: [],
  code: "COCA-355",
  currency_code: "MXN",
  display_order: 10,
  id: "product-coca-355",
  name: "Coca-Cola 355 ml",
  quick_name: "Coca 355",
  unit_price: "18.00",
};

function addClassLine(quantityText: string) {
  return addPendingSelectionToCart({
    ...beginSelectionFromClass(createInitialPosTerminalState(), classCaptureClass),
    pendingSelection: {
      captureMode: CLASS_CAPTURE_MODE,
      editingLine: null,
      productClass: classCaptureClass,
      product: null,
      quantityText,
    },
  });
}

describe("pos terminal model", () => {
  it.each(["PENDING", "UNKNOWN", "CONFLICT"] as const)("freezes cart commands for %s until canonical rejection or confirmation", (status) => {
    const store = usePosTerminalStore.getState();
    store.reset();
    store.selectClass(bolilloClass);
    store.setQuantityText("1");
    store.addPendingLine();
    store.observeSaleIntention(null);
    const original = usePosTerminalStore.getState().cartLines;
    const metadata: SaleIntentionMetadata = {
      key: "019a4000-0000-7000-8000-000000000001", payloadDigest: "a".repeat(64),
      userId: "user-1", branchId: "branch-1", workstationId: "station-1", workstationCode: "POS-01", cashSessionId: "cash-1", status,
    };
    store.setSaleSubmissionPending(true);
    store.observeSaleIntention(null);
    expect(usePosTerminalStore.getState().cartMutationBlocked).toBe(true);
    store.observeSaleIntention(metadata);
    store.setSaleSubmissionPending(false);
    store.incrementLineQuantity(original[0].key);
    store.decrementLineQuantity(original[0].key);
    store.setLineQuantity(original[0].key, "9");
    store.removeLine(original[0].key);
    store.clearCart();
    store.repeatLastLine();
    store.selectClass(classCaptureClass);
    store.setQuantityText("9");
    store.addPendingLine();
    expect(store.replaceReviewedPrices(original, [])).toBe(false);
    expect(usePosTerminalStore.getState().cartLines).toBe(original);
    store.observeSaleIntention({ ...metadata, status: "REJECTED" });
    expect(usePosTerminalStore.getState().cartMutationBlocked).toBe(false);
    store.incrementLineQuantity(original[0].key);
    expect(usePosTerminalStore.getState().cartLines[0].quantityMilliUnits).toBe(2000);
    store.observeSaleIntention({ ...metadata, key: "019a4000-0000-7000-8000-000000000002", status: "CONFIRMED" });
    expect(usePosTerminalStore.getState().cartLines).toHaveLength(0);
    store.reset();
  });
  it("rejects unavailable direct products and quantities beyond the consulted balance", () => {
    const initial = beginSelectionFromClass(createInitialPosTerminalState(), productDirectClass);
    expect(() =>
      selectProductForPending(initial, { ...productDirectProduct, available_quantity: "0.000" }),
    ).toThrow(/existencias/);
    const selected = selectProductForPending(initial, {
      ...productDirectProduct,
      available_quantity: "0.500",
    });
    expect(() =>
      addPendingSelectionToCart({
        ...selected,
        pendingSelection: { ...selected.pendingSelection!, quantityText: "1" },
      }),
    ).toThrow(/existencias/);
    const untracked = selectProductForPending(initial, {
      ...productDirectProduct,
      is_inventory_tracked: false,
      available_quantity: null,
    });
    expect(
      addPendingSelectionToCart({
        ...untracked,
        pendingSelection: { ...untracked.pendingSelection!, quantityText: "1" },
      }).cartLines,
    ).toHaveLength(1);
  });
  it("orders class capture entries before product direct entries and by display order", () => {
    expect(
      sortCatalogClasses([productDirectClass, classCaptureClass, bolilloClass]).map(
        (entry) => entry.code,
      ),
    ).toEqual(["BOLILLO", "PAN-DULCE", "BEBIDAS"]);
  });

  it("moves class capture directly into quantity and returns to class selection after add", () => {
    const selectionState = beginSelectionFromClass(createInitialPosTerminalState(), bolilloClass);

    expect(selectionState.controlState).toBe(CONTROL_STATE_QUANTITY_CAPTURE);

    const nextState = addPendingSelectionToCart({
      ...selectionState,
      pendingSelection: {
        ...selectionState.pendingSelection!,
        quantityText: "2",
      },
    });

    expect(nextState.controlState).toBe(CONTROL_STATE_CLASS_SELECTION);
    expect(nextState.pendingSelection).toBeNull();
    expect(nextState.cartLines).toHaveLength(1);
    expect(nextState.cartLines[0]?.captureMode).toBe(CLASS_CAPTURE_MODE);
  });

  it("moves product direct from class to product to quantity and builds the expected request", () => {
    const classSelectionState = beginSelectionFromClass(
      createInitialPosTerminalState(),
      productDirectClass,
    );

    expect(classSelectionState.controlState).toBe(CONTROL_STATE_PRODUCT_SELECTION);

    const productSelectionState = selectProductForPending(
      classSelectionState,
      productDirectProduct,
    );
    expect(productSelectionState.controlState).toBe(CONTROL_STATE_QUANTITY_CAPTURE);

    const withLineState = addPendingSelectionToCart({
      ...productSelectionState,
      pendingSelection: {
        ...productSelectionState.pendingSelection!,
        quantityText: "1",
      },
    });

    const request = buildConfirmSaleRequest(
      "POS-01",
      withLineState.cartLines,
      {
        cashReceivedText: "20.00",
        paymentMethodCode: CASH_PAYMENT_METHOD_CODE,
      },
      "cash-session-1",
    );

    expect(request.workstation_code).toBe("POS-01");
    expect(request.lines).toEqual([
      {
        capture_mode: PRODUCT_DIRECT_MODE,
        expected_unit_price: "18.00",
        expected_currency_code: "MXN",
        product_id: "product-coca-355",
        quantity: "1",
      },
    ]);
  });

  it("supports intentional payment capture after building the ticket", () => {
    const stateWithLine = addClassLine("2");

    expect(getCartTotalCents(stateWithLine.cartLines)).toBe(2400);
    expect(stateWithLine.controlState).toBe(CONTROL_STATE_CLASS_SELECTION);

    const paymentState = enterPaymentCapture(stateWithLine);
    expect(paymentState.controlState).toBe(CONTROL_STATE_PAYMENT_CAPTURE);
  });

  it("builds a card sale request without cash capture", () => {
    const withLineState = addClassLine("2");

    const request = buildConfirmSaleRequest(
      "POS-01",
      withLineState.cartLines,
      {
        cashReceivedText: "",
        paymentMethodCode: CARD_PAYMENT_METHOD_CODE,
      },
      "cash-session-1",
    );

    expect(request.payments).toEqual([
      {
        payment_method_code: CARD_PAYMENT_METHOD_CODE,
        tendered_amount: "24",
      },
    ]);
  });

  it("builds a mixed sale request with explicit confirmed legs", () => {
    const withLineState = addClassLine("2");

    const request = buildConfirmSaleRequest(
      "POS-01",
      withLineState.cartLines,
      {
        cashReceivedText: "",
        mixedConfirmedLegs: [
          {
            amountText: "10.00",
            methodCode: CASH_PAYMENT_METHOD_CODE,
          },
          {
            amountText: "14.00",
            methodCode: CARD_PAYMENT_METHOD_CODE,
          },
        ],
        paymentMethodCode: MIXED_PAYMENT_METHOD_CODE,
      },
      "cash-session-1",
    );

    expect(request.payments).toEqual([
      {
        payment_method_code: CASH_PAYMENT_METHOD_CODE,
        tendered_amount: "10",
      },
      {
        payment_method_code: CARD_PAYMENT_METHOD_CODE,
        tendered_amount: "14",
      },
    ]);
  });

  it("computes mixed change from confirmed legs when they exist", () => {
    expect(
      computePaymentComputation({
        cashReceivedText: "",
        mixedConfirmedLegs: [
          { amountText: "20.00", methodCode: CASH_PAYMENT_METHOD_CODE },
          { amountText: "50.00", methodCode: CARD_PAYMENT_METHOD_CODE },
        ],
        mixedNonCashAmountText: "",
        paymentMethodCode: MIXED_PAYMENT_METHOD_CODE,
        totalAmountCents: 6200,
      }),
    ).toMatchObject({
      capturedAmountCents: 7000,
      changeAmountCents: 800,
      hasInvalidNonCashOverage: false,
      remainingAmountCents: 0,
    });
  });

  it("keeps direct methods primary while mixed stays an explicit split-payment path", () => {
    expect(getPosCheckoutPaymentControlRows()).toEqual([
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
    ]);
    expect(getPosCheckoutSummaryMetricRows()).toEqual([["TOTAL", "RECEIVED"], ["RESULT"]]);
    expect(isSplitPaymentMethodCode(MIXED_PAYMENT_METHOD_CODE)).toBe(true);
    expect(isSplitPaymentMethodCode(CARD_PAYMENT_METHOD_CODE)).toBe(false);
    expect(usesReceivedAmountInput(CASH_PAYMENT_METHOD_CODE)).toBe(true);
    expect(usesReceivedAmountInput(MIXED_PAYMENT_METHOD_CODE)).toBe(true);
    expect(usesReceivedAmountInput(CARD_PAYMENT_METHOD_CODE)).toBe(false);
  });

  it("derives the live POS work state from the ticket and payment flow", () => {
    expect(
      getPosWorkObjectState({
        cartLineCount: 0,
        hasCompletedSale: false,
        isCommitPending: false,
        isPaymentCaptureActive: false,
        isPaymentReady: false,
      }),
    ).toBe("TICKET_EMPTY");

    expect(
      getPosWorkObjectState({
        cartLineCount: 2,
        hasCompletedSale: false,
        isCommitPending: false,
        isPaymentCaptureActive: false,
        isPaymentReady: false,
      }),
    ).toBe("TICKET_BUILDING");

    expect(
      getPosWorkObjectState({
        cartLineCount: 2,
        hasCompletedSale: false,
        isCommitPending: false,
        isPaymentCaptureActive: true,
        isPaymentReady: true,
      }),
    ).toBe("READY_TO_PAY");

    expect(
      getPosWorkObjectState({
        cartLineCount: 1,
        hasCompletedSale: false,
        isCommitPending: true,
        isPaymentCaptureActive: true,
        isPaymentReady: true,
      }),
    ).toBe("PAYING");

    expect(
      getPosWorkObjectState({
        cartLineCount: 0,
        hasCompletedSale: true,
        isCommitPending: false,
        isPaymentCaptureActive: false,
        isPaymentReady: false,
      }),
    ).toBe("SALE_CONFIRMED");
  });

  it("treats zero quantity as pending instead of captured", () => {
    expect(hasCapturedQuantity("")).toBe(false);
    expect(hasCapturedQuantity("0")).toBe(false);
    expect(hasCapturedQuantity("0.000")).toBe(false);
    expect(hasCapturedQuantity("1")).toBe(true);
  });

  it("keeps the quantity focus target stable while the cashier edits digits", () => {
    expect(
      getPendingCaptureTargetKey({
        captureMode: CLASS_CAPTURE_MODE,
        editingLine: null,
        productClass: bolilloClass,
        product: null,
        quantityText: "",
      }),
    ).toBe("class:class-bolillo");

    expect(
      getPendingCaptureTargetKey({
        captureMode: CLASS_CAPTURE_MODE,
        editingLine: null,
        productClass: bolilloClass,
        product: null,
        quantityText: "12",
      }),
    ).toBe("class:class-bolillo");

    expect(
      getPendingCaptureTargetKey({
        captureMode: PRODUCT_DIRECT_MODE,
        editingLine: null,
        productClass: productDirectClass,
        product: productDirectProduct,
        quantityText: "24",
      }),
    ).toBe("product:product-coca-355");
  });

  it("reopens an existing ticket line in quantity capture for edit", () => {
    const withLineState = addClassLine("2");
    const editedState = beginEditingCartLine(withLineState, withLineState.cartLines[0]!.key);

    expect(editedState.controlState).toBe(CONTROL_STATE_QUANTITY_CAPTURE);
    expect(editedState.cartLines).toHaveLength(0);
    expect(editedState.pendingSelection?.editingLine?.key).toBe(withLineState.cartLines[0]!.key);
    expect(editedState.pendingSelection?.quantityText).toBe(
      formatQuantityFromMilliUnits(withLineState.cartLines[0]!.quantityMilliUnits),
    );
  });

  it("repeats the last cart line without leaving selection inconsistent", () => {
    const repeatedState = repeatLastCartLine(addClassLine("2"));

    expect(repeatedState.cartLines).toHaveLength(1);
    expect(repeatedState.cartLines[0]?.quantityText).toBe("4");
    expect(getCartTotalCents(repeatedState.cartLines)).toBe(4800);
  });
});
