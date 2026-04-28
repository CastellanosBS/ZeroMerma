import { describe, expect, it } from "vitest";

import {
  buildCreateOperationalDiscountRequest,
  canCommitOperationalDiscountDraft,
  createInitialOperationalDiscountDraftState,
  doesOperationalDiscountAffectCashDrawer,
  getOperationalDiscountBlockedReason,
  getOperationalDiscountCreateStepKey,
  getOperationalDiscountUiState,
  isOperationalDiscountHighValue,
} from "./model";

const discountMethods = [
  {
    affects_cash_drawer: false,
    code: "CARD",
    helper_text: "No cambia efectivo esperado.",
    is_enabled: true,
    label: "Tarjeta",
  },
  {
    affects_cash_drawer: true,
    code: "CASH",
    helper_text: "Incrementa efectivo esperado.",
    is_enabled: true,
    label: "Efectivo",
  },
  {
    affects_cash_drawer: false,
    code: "MIXED",
    helper_text: "No disponible en esta fase.",
    is_enabled: false,
    label: "Mixto",
  },
];

const discountCategories = [
  { code: "STAFF", display_order: 10, name: "Personal" },
  { code: "OPERATIONS", display_order: 20, name: "Operaciones" },
];

const discountControls = {
  high_value_amount_threshold: "200.00",
};

describe("discounts model", () => {
  it("starts with an explicit method selection requirement", () => {
    const draft = createInitialOperationalDiscountDraftState();

    expect(draft.paymentMethodCode).toBe("");
    expect(draft.highValueAcknowledged).toBe(false);
  });

  it("reads cash impact from the backend method catalog", () => {
    expect(doesOperationalDiscountAffectCashDrawer("CASH", discountMethods)).toBe(true);
    expect(doesOperationalDiscountAffectCashDrawer("CARD", discountMethods)).toBe(false);
  });

  it("derives blockers and step progression canonically", () => {
    const initialDraft = createInitialOperationalDiscountDraftState();

    expect(
      getOperationalDiscountUiState({
        categories: discountCategories,
        controls: discountControls,
        draft: initialDraft,
        hasCommitError: false,
        hasConfirmedDraft: false,
        hasSelectedDiscount: false,
        isCaptureActive: true,
        isCommitPending: false,
        methods: discountMethods,
      }),
    ).toBe("CAPTURING");
    expect(
      getOperationalDiscountCreateStepKey(
        initialDraft,
        discountMethods,
        discountCategories,
        discountControls,
      ),
    ).toBe("details");
    expect(
      getOperationalDiscountBlockedReason(
        initialDraft,
        discountMethods,
        discountCategories,
        discountControls,
      ),
    ).toBe("Captura la persona o entidad.");

    const detailsDraft = {
      ...initialDraft,
      categoryCode: "STAFF",
      concept: "Prestamo interno",
      subjectName: "Empleado Luis",
    };

    expect(
      getOperationalDiscountCreateStepKey(
        detailsDraft,
        discountMethods,
        discountCategories,
        discountControls,
      ),
    ).toBe("amount");
    expect(
      getOperationalDiscountUiState({
        categories: discountCategories,
        controls: discountControls,
        draft: detailsDraft,
        hasCommitError: false,
        hasConfirmedDraft: false,
        hasSelectedDiscount: false,
        isCaptureActive: true,
        isCommitPending: false,
        methods: discountMethods,
      }),
    ).toBe("BLOCKED_MISSING_AMOUNT");

    const amountDraft = {
      ...detailsDraft,
      totalAmountText: "40.50",
    };

    expect(
      getOperationalDiscountCreateStepKey(
        amountDraft,
        discountMethods,
        discountCategories,
        discountControls,
      ),
    ).toBe("method");
    expect(
      getOperationalDiscountUiState({
        categories: discountCategories,
        controls: discountControls,
        draft: amountDraft,
        hasCommitError: false,
        hasConfirmedDraft: false,
        hasSelectedDiscount: false,
        isCaptureActive: true,
        isCommitPending: false,
        methods: discountMethods,
      }),
    ).toBe("BLOCKED_MISSING_METHOD");

    const readyDraft = {
      ...amountDraft,
      paymentMethodCode: "CASH",
    };

    expect(
      getOperationalDiscountCreateStepKey(
        readyDraft,
        discountMethods,
        discountCategories,
        discountControls,
      ),
    ).toBe("save");
    expect(
      getOperationalDiscountUiState({
        categories: discountCategories,
        controls: discountControls,
        draft: readyDraft,
        hasCommitError: false,
        hasConfirmedDraft: false,
        hasSelectedDiscount: false,
        isCaptureActive: true,
        isCommitPending: false,
        methods: discountMethods,
      }),
    ).toBe("READY_TO_CONFIRM");
    expect(
      canCommitOperationalDiscountDraft(
        readyDraft,
        discountMethods,
        discountCategories,
        discountControls,
      ),
    ).toBe(true);
  });

  it("requires acknowledgement for high-value discounts", () => {
    const draft = {
      ...createInitialOperationalDiscountDraftState(),
      categoryCode: "OPERATIONS",
      concept: "Descuento especial",
      paymentMethodCode: "CARD",
      subjectName: "Empleado Rosa",
      totalAmountText: "250.00",
    };

    expect(isOperationalDiscountHighValue(draft, discountControls)).toBe(true);
    expect(
      getOperationalDiscountBlockedReason(
        draft,
        discountMethods,
        discountCategories,
        discountControls,
      ),
    ).toBe("Confirma el descuento de alto valor.");

    expect(
      canCommitOperationalDiscountDraft(
        draft,
        discountMethods,
        discountCategories,
        discountControls,
      ),
    ).toBe(false);
  });

  it("builds a backend request only when the draft is valid", () => {
    const draft = {
      ...createInitialOperationalDiscountDraftState(),
      categoryCode: "STAFF",
      concept: "Prestamo interno abril",
      paymentMethodCode: "CASH",
      subjectName: "Empleado Luis",
      totalAmountText: "40.50",
    };

    expect(
      buildCreateOperationalDiscountRequest(
        "POS-01",
        draft,
        discountMethods,
        discountCategories,
        discountControls,
      ),
    ).toEqual({
      workstation_code: "POS-01",
      subject_name: "Empleado Luis",
      concept: "Prestamo interno abril",
      payment_method_code: "CASH",
      total_amount: "40.50",
      category_code: "STAFF",
      high_value_acknowledged: false,
      notes: undefined,
    });
  });
});
