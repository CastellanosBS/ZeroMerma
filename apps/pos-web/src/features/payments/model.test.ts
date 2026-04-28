import { describe, expect, it } from "vitest";

import {
  buildCreateOperationalPaymentRequest,
  canCommitOperationalPaymentDraft,
  createInitialOperationalPaymentDraftState,
  doesOperationalPaymentAffectCashDrawer,
  getOperationalPaymentBlockedReason,
  getOperationalPaymentCreateStepKey,
  getOperationalPaymentUiState,
} from "./model";

const paymentMethods = [
  {
    code: "CARD",
    label: "Tarjeta",
    affects_cash_drawer: false,
    helper_text: "No reduce efectivo esperado.",
    is_enabled: true,
  },
  {
    code: "CASH",
    label: "Efectivo",
    affects_cash_drawer: true,
    helper_text: "Reduce efectivo esperado.",
    is_enabled: true,
  },
  {
    code: "MIXED",
    label: "Mixto",
    affects_cash_drawer: false,
    helper_text: "No disponible en esta fase.",
    is_enabled: false,
  },
];

const paymentCategories = [
  { code: "SUPPLIES", display_order: 10, name: "Insumos" },
  { code: "SERVICES", display_order: 20, name: "Servicios" },
];

describe("payments model", () => {
  it("starts with an explicit method selection requirement", () => {
    const draft = createInitialOperationalPaymentDraftState();

    expect(draft.paymentMethodCode).toBe("");
  });

  it("reads cash impact from the backend method catalog", () => {
    expect(doesOperationalPaymentAffectCashDrawer("CASH", paymentMethods)).toBe(true);
    expect(doesOperationalPaymentAffectCashDrawer("CARD", paymentMethods)).toBe(false);
  });

  it("derives create blockers and step progression canonically", () => {
    const initialDraft = createInitialOperationalPaymentDraftState();

    expect(
      getOperationalPaymentUiState({
        categories: paymentCategories,
        draft: initialDraft,
        hasCommitError: false,
        hasConfirmedDraft: false,
        hasSelectedPayment: false,
        isCaptureActive: true,
        isCommitPending: false,
        methods: paymentMethods,
      }),
    ).toBe("CAPTURING");
    expect(
      getOperationalPaymentCreateStepKey(initialDraft, paymentMethods, paymentCategories),
    ).toBe("details");
    expect(
      getOperationalPaymentBlockedReason(initialDraft, paymentMethods, paymentCategories),
    ).toBe(
      "Captura el beneficiario del pago.",
    );

    const detailsDraft = {
      ...initialDraft,
      categoryCode: "SUPPLIES",
      concept: "REF-001",
      payeeName: "Proveedor",
    };

    expect(
      getOperationalPaymentCreateStepKey(detailsDraft, paymentMethods, paymentCategories),
    ).toBe("amount");
    expect(
      getOperationalPaymentUiState({
        categories: paymentCategories,
        draft: detailsDraft,
        hasCommitError: false,
        hasConfirmedDraft: false,
        hasSelectedPayment: false,
        isCaptureActive: true,
        isCommitPending: false,
        methods: paymentMethods,
      }),
    ).toBe("BLOCKED_MISSING_AMOUNT");

    const amountDraft = {
      ...detailsDraft,
      totalAmountText: "40.50",
    };

    expect(
      getOperationalPaymentCreateStepKey(amountDraft, paymentMethods, paymentCategories),
    ).toBe("method");
    expect(
      getOperationalPaymentUiState({
        categories: paymentCategories,
        draft: amountDraft,
        hasCommitError: false,
        hasConfirmedDraft: false,
        hasSelectedPayment: false,
        isCaptureActive: true,
        isCommitPending: false,
        methods: paymentMethods,
      }),
    ).toBe("BLOCKED_MISSING_METHOD");

    const readyDraft = {
      ...amountDraft,
      paymentMethodCode: "CASH",
    };

    expect(
      getOperationalPaymentCreateStepKey(readyDraft, paymentMethods, paymentCategories),
    ).toBe("save");
    expect(
      getOperationalPaymentUiState({
        categories: paymentCategories,
        draft: readyDraft,
        hasCommitError: false,
        hasConfirmedDraft: false,
        hasSelectedPayment: false,
        isCaptureActive: true,
        isCommitPending: false,
        methods: paymentMethods,
      }),
    ).toBe("READY_TO_CONFIRM");
    expect(canCommitOperationalPaymentDraft(readyDraft, paymentMethods, paymentCategories)).toBe(
      true,
    );
  });

  it("builds a backend request only when the draft is valid", () => {
    const draft = {
      ...createInitialOperationalPaymentDraftState(),
      categoryCode: "SUPPLIES",
      concept: "REF-8891",
      paymentMethodCode: "CASH",
      payeeName: "Proveedor",
      totalAmountText: "40.50",
    };

    expect(
      buildCreateOperationalPaymentRequest(
        "POS-01",
        draft,
        paymentMethods,
        paymentCategories,
      ),
    ).toEqual({
      workstation_code: "POS-01",
      payee_name: "Proveedor",
      concept: "REF-8891",
      payment_method_code: "CASH",
      total_amount: "40.50",
      category_code: "SUPPLIES",
      notes: undefined,
    });
  });
});
