import { describe, expect, it } from "vitest";

import type { PosCatalogClassView, PosCatalogProductView } from "../../lib/api-contracts";
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

    const productSelectionState = selectProductForPending(classSelectionState, productDirectProduct);
    expect(productSelectionState.controlState).toBe(CONTROL_STATE_QUANTITY_CAPTURE);

    const withLineState = addPendingSelectionToCart({
      ...productSelectionState,
      pendingSelection: {
        ...productSelectionState.pendingSelection!,
        quantityText: "1",
      },
    });

    const request = buildConfirmSaleRequest("POS-01", withLineState.cartLines, {
      cashReceivedText: "20.00",
      paymentMethodCode: CASH_PAYMENT_METHOD_CODE,
    });

    expect(request.workstation_code).toBe("POS-01");
    expect(request.lines).toEqual([
      {
        capture_mode: PRODUCT_DIRECT_MODE,
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

    const request = buildConfirmSaleRequest("POS-01", withLineState.cartLines, {
      cashReceivedText: "",
      paymentMethodCode: CARD_PAYMENT_METHOD_CODE,
    });

    expect(request.payments).toEqual([
      {
        payment_method_code: CARD_PAYMENT_METHOD_CODE,
        tendered_amount: "24",
      },
    ]);
  });

  it("builds a mixed sale request with explicit confirmed legs", () => {
    const withLineState = addClassLine("2");

    const request = buildConfirmSaleRequest("POS-01", withLineState.cartLines, {
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
    });

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
    expect(getPosCheckoutSummaryMetricRows()).toEqual([
      ["TOTAL", "RECEIVED"],
      ["RESULT"],
    ]);
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
