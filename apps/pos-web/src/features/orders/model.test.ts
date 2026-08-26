import { describe, expect, it } from "vitest";

import type { OrdersCatalogClassView, OrdersCatalogProductView } from "../../lib/api-contracts";
import {
  addPendingSelectionLine,
  buildCreateOrderAdvancePayments,
  buildDeliverOrderSettlementPayments,
  buildCreateOrderItems,
  createInitialOrderCreateDraftState,
  getAdvanceAmountCents,
  getOrderAdvanceAmountCents,
  getOrderAdvanceValidationMessage,
  getOrderCreateBlockingMessage,
  getOrderCreateChecklistMessages,
  getOrderCreateUiState,
  isOrderCustomerPhoneComplete,
  getOrderSubtotalCents,
  getRemainingBalanceCents,
  selectClassForOrder,
  selectProductForOrder,
  setPendingQuantityText,
} from "./model";

const bebidasClass: OrdersCatalogClassView = {
  code: "BEBIDAS",
  display_order: 20,
  id: "class-bebidas",
  name: "Bebidas",
  product_count: 2,
  quick_name: "Bebidas",
};

const americanoProduct: OrdersCatalogProductView = {
  code: "CAFE-AMERICANO",
  currency_code: "MXN",
  display_order: 20,
  id: "product-americano",
  name: "Cafe americano",
  quick_name: "Americano",
  unit_price: "22.00",
};

describe("orders model", () => {
  it("requires a complete customer phone before enabling order capture", () => {
    expect(isOrderCustomerPhoneComplete("662")).toBe(false);
    expect(isOrderCustomerPhoneComplete("662-123-4567")).toBe(true);
  });

  it("merges duplicate exact-product lines and computes totals", () => {
    const baseState = createInitialOrderCreateDraftState();
    const firstSelection = setPendingQuantityText(
      selectProductForOrder(selectClassForOrder(baseState, bebidasClass), americanoProduct),
      "2",
    );
    const stateWithOneLine = addPendingSelectionLine(firstSelection);
    const duplicateSelection = setPendingQuantityText(
      selectProductForOrder(selectClassForOrder(stateWithOneLine, bebidasClass), americanoProduct),
      "1.5",
    );
    const finalState = addPendingSelectionLine(duplicateSelection);

    expect(finalState.lines).toHaveLength(1);
    expect(finalState.lines[0]?.quantityText).toBe("3.5");
    expect(getOrderSubtotalCents(finalState.lines)).toBe(7700);
  });

  it("builds create-order items and remaining balance from the canonical draft", () => {
    const draft = {
      ...createInitialOrderCreateDraftState(),
      lines: [
        {
          key: "product-americano",
          productClassCode: "BEBIDAS",
          productClassId: "class-bebidas",
          productClassName: "Bebidas",
          productCode: "CAFE-AMERICANO",
          productId: "product-americano",
          productName: "Cafe americano",
          quantityMilliUnits: 2000,
          quantityText: "2",
          unitPriceCents: 2200,
          unitPriceText: "$22.00",
        },
      ],
    };

    expect(buildCreateOrderItems(draft.lines)).toEqual([
      {
        product_id: "product-americano",
        quantity: "2",
      },
    ]);
    expect(getAdvanceAmountCents("10.00")).toBe(1000);
    expect(
      getRemainingBalanceCents(
        draft.lines,
        getOrderAdvanceAmountCents({
          advanceAmountText: "10.00",
          mixedCardAmountText: "",
          mixedCashAmountText: "",
          paymentMethodCode: "CASH",
        }),
      ),
    ).toBe(3400);
    expect(
      buildCreateOrderAdvancePayments({
        advanceAmountText: "",
        mixedCardAmountText: "6.00",
        mixedCashAmountText: "4.00",
        paymentMethodCode: "MIXED",
      }),
    ).toEqual([
      { amount: "4", payment_method_code: "CASH" },
      { amount: "6", payment_method_code: "CARD" },
    ]);
    expect(
      buildCreateOrderAdvancePayments({
        advanceAmountText: "10.00",
        mixedCardAmountText: "",
        mixedCashAmountText: "",
        paymentMethodCode: "CASH",
      }),
    ).toEqual([]);
    expect(
      buildDeliverOrderSettlementPayments({
        mixedCardAmountText: "15.00",
        mixedCashAmountText: "9.00",
        paymentMethodCode: "MIXED",
      }),
    ).toEqual([
      { amount: "9", payment_method_code: "CASH" },
      { amount: "15", payment_method_code: "CARD" },
    ]);
    expect(
      buildDeliverOrderSettlementPayments({
        mixedCardAmountText: "",
        mixedCashAmountText: "",
        paymentMethodCode: "CASH",
      }),
    ).toEqual([]);
  });

  it("returns the canonical create-order blocking message for invalid drafts", () => {
    const draft = {
      ...createInitialOrderCreateDraftState(),
      lines: [
        {
          key: "product-americano",
          productClassCode: "BEBIDAS",
          productClassId: "class-bebidas",
          productClassName: "Bebidas",
          productCode: "CAFE-AMERICANO",
          productId: "product-americano",
          productName: "Cafe americano",
          quantityMilliUnits: 2000,
          quantityText: "2",
          unitPriceCents: 2200,
          unitPriceText: "$22.00",
        },
      ],
    };

    expect(
      getOrderCreateBlockingMessage({
        advanceAmountText: "0.00",
        advancePaymentMethodCode: "",
        customerName: "",
        customerPhone: "",
        mixedCardAmountText: "",
        mixedCashAmountText: "",
        lines: draft.lines,
        requestedForInput: "2026-04-15T12:00",
      }),
    ).toBe("Captura el cliente antes de guardar.");

    expect(
      getOrderCreateBlockingMessage({
        advanceAmountText: "0.00",
        advancePaymentMethodCode: "",
        customerName: "Cliente demo",
        customerPhone: "",
        mixedCardAmountText: "",
        mixedCashAmountText: "",
        lines: draft.lines,
        requestedForInput: "2026-04-15T12:00",
      }),
    ).toBe("Captura el telefono completo antes de guardar.");

    expect(
      getOrderCreateBlockingMessage({
        advanceAmountText: "0.00",
        advancePaymentMethodCode: "",
        customerName: "Cliente demo",
        customerPhone: "662",
        mixedCardAmountText: "",
        mixedCashAmountText: "",
        lines: draft.lines,
        requestedForInput: "2026-04-15T12:00",
      }),
    ).toBe("Captura el telefono completo antes de guardar.");

    expect(
      getOrderCreateBlockingMessage({
        advanceAmountText: "0.00",
        advancePaymentMethodCode: "",
        customerName: "Cliente demo",
        customerPhone: "6621234567",
        mixedCardAmountText: "",
        mixedCashAmountText: "",
        lines: draft.lines,
        requestedForInput: "",
      }),
    ).toBe("Captura la fecha de recoleccion antes de guardar.");

    expect(
      getOrderCreateBlockingMessage({
        advanceAmountText: "50.00",
        advancePaymentMethodCode: "",
        customerName: "Cliente demo",
        customerPhone: "6621234567",
        mixedCardAmountText: "",
        mixedCashAmountText: "",
        hasNegativeAdvanceAttempt: false,
        lines: draft.lines,
        requestedForInput: "2026-04-15T12:00",
      }),
    ).toBe("El anticipo no puede exceder el total.");

    expect(
      getOrderCreateBlockingMessage({
        advanceAmountText: "10.00",
        advancePaymentMethodCode: "",
        customerName: "Cliente demo",
        customerPhone: "6621234567",
        mixedCardAmountText: "",
        mixedCashAmountText: "",
        hasNegativeAdvanceAttempt: false,
        lines: draft.lines,
        requestedForInput: "2026-04-15T12:00",
      }),
    ).toBe("Selecciona el metodo del anticipo.");

    expect(
      getOrderCreateBlockingMessage({
        advanceAmountText: "",
        advancePaymentMethodCode: "MIXED",
        customerName: "Cliente demo",
        customerPhone: "6621234567",
        mixedCardAmountText: "10.00",
        mixedCashAmountText: "",
        hasNegativeAdvanceAttempt: false,
        lines: draft.lines,
        requestedForInput: "2026-04-15T12:00",
      }),
    ).toBe("Captura efectivo y tarjeta para el anticipo mixto.");
  });

  it("returns advance validation, checklist messages, and create UI state", () => {
    const draft = {
      ...createInitialOrderCreateDraftState(),
      lines: [
        {
          key: "product-americano",
          productClassCode: "BEBIDAS",
          productClassId: "class-bebidas",
          productClassName: "Bebidas",
          productCode: "CAFE-AMERICANO",
          productId: "product-americano",
          productName: "Cafe americano",
          quantityMilliUnits: 2000,
          quantityText: "2",
          unitPriceCents: 2200,
          unitPriceText: "$22.00",
        },
      ],
    };

    expect(
      getOrderAdvanceValidationMessage({
        advanceAmountText: "",
        advancePaymentMethodCode: "",
        mixedCardAmountText: "",
        mixedCashAmountText: "",
        hasNegativeAdvanceAttempt: true,
        lines: draft.lines,
      }),
    ).toBe("El anticipo no puede ser negativo.");

    expect(
      getOrderCreateChecklistMessages({
        advanceAmountText: "10.00",
        advancePaymentMethodCode: "",
        customerName: "",
        customerPhone: "",
        mixedCardAmountText: "",
        mixedCashAmountText: "",
        hasNegativeAdvanceAttempt: false,
        lines: [],
        requestedForInput: "",
      }),
    ).toEqual([
      "Falta cliente.",
      "Falta telefono completo.",
      "Falta fecha de recoleccion.",
      "Agrega al menos una linea.",
      "El anticipo no puede exceder el total.",
    ]);

    expect(
      getOrderCreateUiState({
        customerName: "",
        customerPhone: "",
        hasBlockingMessage: true,
        isSaving: false,
        lineCount: 0,
        requestedForInput: "",
      }),
    ).toBe("DRAFT_EMPTY");

    expect(
      getOrderCreateUiState({
        customerName: "Cliente demo",
        customerPhone: "6621234567",
        hasBlockingMessage: false,
        isSaving: false,
        lineCount: 0,
        requestedForInput: "2026-04-15T12:00",
      }),
    ).toBe("PRODUCTS_PENDING");

    expect(
      getOrderCreateUiState({
        customerName: "Cliente demo",
        customerPhone: "6621234567",
        hasBlockingMessage: true,
        isSaving: false,
        lineCount: 2,
        requestedForInput: "",
      }),
    ).toBe("DETAILS_PENDING");

    expect(
      getOrderCreateUiState({
        customerName: "Cliente demo",
        customerPhone: "662",
        hasBlockingMessage: true,
        isSaving: false,
        lineCount: 2,
        requestedForInput: "2026-04-15T12:00",
      }),
    ).toBe("DETAILS_PENDING");

    expect(
      getOrderCreateUiState({
        customerName: "Cliente demo",
        customerPhone: "6621234567",
        hasBlockingMessage: true,
        isSaving: false,
        lineCount: 2,
        requestedForInput: "2026-04-15T12:00",
      }),
    ).toBe("SUMMARY_PENDING");

    expect(
      getOrderCreateUiState({
        customerName: "Cliente demo",
        customerPhone: "6621234567",
        hasBlockingMessage: false,
        isSaving: false,
        lineCount: 2,
        requestedForInput: "2026-04-15T12:00",
      }),
    ).toBe("READY_TO_SAVE");
  });
});
