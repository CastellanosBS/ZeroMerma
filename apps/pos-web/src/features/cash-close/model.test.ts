import { describe, expect, it } from "vitest";

import type {
  CashClosePaymentMethodCatalogView,
  OperationsCatalogClassView,
  OperationsCatalogProductView,
} from "../../lib/api-contracts";
import {
  addCashClosePendingCountLine,
  buildCashClosePreviewRequest,
  createInitialCashCloseDraftState,
  getCashCloseBlockingReason,
  getCashCloseCountValueState,
  getCashCloseUiState,
  hasCashCloseExpectedPaymentCounts,
  selectClassForCashCloseCount,
  selectProductForCashCloseCount,
  setCashClosePendingQuantityText,
  syncCashCloseDraftState,
} from "./model";

const paymentMethodCatalog: CashClosePaymentMethodCatalogView[] = [
  {
    currency_code: "MXN",
    display_order: 10,
    is_active: true,
    is_expected_supported: true,
    payment_method_code: "CASH",
  },
  {
    currency_code: "MXN",
    display_order: 20,
    is_active: true,
    is_expected_supported: false,
    payment_method_code: "CARD",
  },
];

const bolilloClass: OperationsCatalogClassView = {
  code: "BOLILLO",
  display_order: 10,
  id: "class-bolillo",
  name: "Bolillo",
  product_count: 1,
  quick_name: "Bolillo",
};

const bolilloProduct: OperationsCatalogProductView = {
  code: "BOLILLO-STD",
  currency_code: "MXN",
  display_order: 10,
  id: "product-bolillo-std",
  name: "Bolillo estandar",
  quick_name: "Bolillo",
  unit_price: "0.00",
};

describe("cash close model", () => {
  it("seeds counted payment slots from the payment method catalog", () => {
    const draft = syncCashCloseDraftState(createInitialCashCloseDraftState(), {
      paymentMethodCatalog,
    });

    expect(draft.countedPaymentAmounts).toEqual({
      CARD: "",
      CASH: "",
    });
    expect(draft.countedProductDraftLines).toEqual([]);
  });

  it("builds the preview payload from counted methods and counted product lines only", () => {
    const draft = createInitialCashCloseDraftState();
    draft.countedPaymentAmounts = {
      CARD: "25.00",
      CASH: "174.00",
    };
    draft.countedProductDraftLines = [
      {
        key: "product-concha-van",
        productClassCode: "PAN-DULCE",
        productClassId: "class-pan-dulce",
        productClassName: "Pan dulce",
        productCode: "CONCHA-VAN",
        productId: "product-concha-van",
        productName: "Vanilla Concha",
        quantityMilliUnits: 3000,
        quantityText: "3",
      },
      {
        key: "product-concha-choco",
        productClassCode: "PAN-DULCE",
        productClassId: "class-pan-dulce",
        productClassName: "Pan dulce",
        productCode: "CONCHA-CHOCO",
        productId: "product-concha-choco",
        productName: "Chocolate Concha",
        quantityMilliUnits: 0,
        quantityText: "0",
      },
    ];

    expect(buildCashClosePreviewRequest("POS-01", draft)).toEqual({
      workstation_code: "POS-01",
      counted_payment_methods: [
        {
          counted_amount: "25.00",
          payment_method_code: "CARD",
        },
        {
          counted_amount: "174.00",
          payment_method_code: "CASH",
        },
      ],
      counted_product_lines: [
        {
          counted_quantity: "3",
          product_id: "product-concha-van",
        },
        {
          counted_quantity: "0",
          product_id: "product-concha-choco",
        },
      ],
    });
  });

  it("builds counted product lines through the selection-driven close grammar", () => {
    let draft = createInitialCashCloseDraftState();
    draft = selectClassForCashCloseCount(draft, bolilloClass);
    draft = selectProductForCashCloseCount(draft, bolilloProduct);
    draft = setCashClosePendingQuantityText(draft, "8");
    draft = addCashClosePendingCountLine(draft);

    expect(draft.countedProductDraftLines).toEqual([
      {
        key: "product-bolillo-std",
        productClassCode: "BOLILLO",
        productClassId: "class-bolillo",
        productClassName: "Bolillo",
        productCode: "BOLILLO-STD",
        productId: "product-bolillo-std",
        productName: "Bolillo estandar",
        quantityMilliUnits: 8000,
        quantityText: "8",
      },
    ]);
  });

  it("distinguishes pending counted values from captured zero-like semantics", () => {
    expect(getCashCloseCountValueState("")).toBe("PENDING");
    expect(getCashCloseCountValueState("0.00")).toBe("CAPTURED");
  });

  it("derives readiness for expected financial counts from the catalog", () => {
    const draft = syncCashCloseDraftState(createInitialCashCloseDraftState(), {
      paymentMethodCatalog,
    });

    expect(
      hasCashCloseExpectedPaymentCounts(paymentMethodCatalog, draft.countedPaymentAmounts),
    ).toBe(false);

    draft.countedPaymentAmounts.CASH = "180.00";
    expect(
      hasCashCloseExpectedPaymentCounts(paymentMethodCatalog, draft.countedPaymentAmounts),
    ).toBe(true);
  });

  it("derives ui state and blocking reason canonically from draft and preview state", () => {
    const draft = syncCashCloseDraftState(createInitialCashCloseDraftState(), {
      paymentMethodCatalog,
    });

    expect(
      getCashCloseUiState({
        activeSection: "CONTEXT",
        draftState: draft,
        hasClosedSuccessfully: false,
        hasOpenCashSession: true,
        hasSubmitError: false,
        isClosing: false,
        isLoadingContext: false,
        isPreviewPending: false,
        paymentMethodCatalog,
        previewResult: null,
      }),
    ).toBe("CONTEXT_REVIEW");
    expect(
      getCashCloseBlockingReason({
        draftState: draft,
        hasOpenCashSession: true,
        paymentMethodCatalog,
        previewResult: null,
      }),
    ).toBe("Falta capturar efectivo contado.");

    draft.countedPaymentAmounts.CASH = "174.00";
    draft.countedProductDraftLines = [
      {
        key: "product-bolillo-std",
        productClassCode: "BOLILLO",
        productClassId: "class-bolillo",
        productClassName: "Bolillo",
        productCode: "BOLILLO-STD",
        productId: "product-bolillo-std",
        productName: "Bolillo estandar",
        quantityMilliUnits: 8000,
        quantityText: "8",
      },
    ];

    expect(
      getCashCloseUiState({
        activeSection: "REVIEW",
        draftState: draft,
        hasClosedSuccessfully: false,
        hasOpenCashSession: true,
        hasSubmitError: false,
        isClosing: false,
        isLoadingContext: false,
        isPreviewPending: false,
        paymentMethodCatalog,
        previewResult: {
          blockers: [],
          reconciliation_status: "READY",
          warnings: [],
        },
      }),
    ).toBe("READY_TO_CLOSE");

    expect(
      getCashCloseUiState({
        activeSection: "REVIEW",
        draftState: draft,
        hasClosedSuccessfully: false,
        hasOpenCashSession: true,
        hasSubmitError: false,
        isClosing: false,
        isLoadingContext: false,
        isPreviewPending: false,
        paymentMethodCatalog,
        previewResult: {
          blockers: [{ code: "MISSING_COUNTED_CLOSING_STOCK", message: "Falta conteo físico." }],
          reconciliation_status: "REVIEW_REQUIRED",
          warnings: [],
        },
      }),
    ).toBe("HAS_HARD_BLOCKERS");
  });
});
