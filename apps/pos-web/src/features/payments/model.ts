import type {
  CreateOperationalPaymentRequest,
  OperationalPaymentCategoryView,
  OperationalPaymentMethodView,
} from "../../lib/api-contracts";
import {
  formatMoneyFromCents,
  parseMoneyToCents,
  sanitizeMoneyInput,
} from "../pos-terminal/model";

export interface OperationalPaymentDraftState {
  categoryCode: string;
  concept: string;
  notes: string;
  payeeName: string;
  paymentMethodCode: string;
  totalAmountText: string;
}

export type OperationalPaymentUiState =
  | "NO_SELECTION"
  | "LIST_VIEW_READY"
  | "CAPTURING"
  | "DRAFT_INCOMPLETE"
  | "BLOCKED_MISSING_CATEGORY"
  | "BLOCKED_MISSING_REFERENCE"
  | "BLOCKED_MISSING_AMOUNT"
  | "BLOCKED_MISSING_METHOD"
  | "READY_TO_CONFIRM"
  | "CONFIRMING"
  | "CONFIRMED"
  | "ERROR";

export function createInitialOperationalPaymentDraftState(): OperationalPaymentDraftState {
  return {
    categoryCode: "",
    concept: "",
    notes: "",
    payeeName: "",
    paymentMethodCode: "",
    totalAmountText: "",
  };
}

export function getOperationalPaymentMethodLabel(code: string): string {
  switch (code) {
    case "CASH":
      return "Efectivo";
    case "CARD":
      return "Tarjeta";
    case "MIXED":
      return "Mixto";
    default:
      return code;
  }
}

export function getOperationalPaymentMethod(
  paymentMethodCode: string,
  methods: OperationalPaymentMethodView[],
): OperationalPaymentMethodView | null {
  return methods.find((method) => method.code === paymentMethodCode) ?? null;
}

export function isOperationalPaymentMethodSelectable(
  paymentMethodCode: string,
  methods: OperationalPaymentMethodView[],
): boolean {
  const selectedMethod = getOperationalPaymentMethod(paymentMethodCode, methods);
  return Boolean(selectedMethod?.is_enabled);
}

export function doesOperationalPaymentAffectCashDrawer(
  paymentMethodCode: string,
  methods: OperationalPaymentMethodView[] = [],
): boolean {
  const selectedMethod = getOperationalPaymentMethod(paymentMethodCode, methods);
  if (selectedMethod) {
    return selectedMethod.affects_cash_drawer;
  }

  return paymentMethodCode === "CASH";
}

export function sanitizeOperationalPaymentAmountInput(value: string): string {
  return sanitizeMoneyInput(value);
}

export function getOperationalPaymentDerivedConcept(
  draft: OperationalPaymentDraftState,
  categories: OperationalPaymentCategoryView[] = [],
): string {
  void categories;
  return draft.concept.trim();
}

export function getOperationalPaymentAmountCents(amountText: string): number | null {
  const amountCents = parseMoneyToCents(amountText);
  if (amountCents === null || amountCents <= 0) {
    return null;
  }

  return amountCents;
}

export function getOperationalPaymentBlockingMessages(
  draft: OperationalPaymentDraftState,
  methods: OperationalPaymentMethodView[],
  categories: OperationalPaymentCategoryView[] = [],
): string[] {
  const messages: string[] = [];

  if (draft.payeeName.trim().length === 0) {
    messages.push("Captura el beneficiario del pago.");
  }

  if (draft.categoryCode.trim().length === 0) {
    messages.push("Selecciona la categoria del pago.");
  }

  if (getOperationalPaymentDerivedConcept(draft, categories).length === 0) {
    messages.push("Captura una referencia del pago.");
  }

  if (getOperationalPaymentAmountCents(draft.totalAmountText) === null) {
    messages.push("Captura un monto valido.");
  }

  if (!isOperationalPaymentMethodSelectable(draft.paymentMethodCode, methods)) {
    messages.push("Selecciona el metodo del pago.");
  }

  return messages;
}

export function getOperationalPaymentBlockedReason(
  draft: OperationalPaymentDraftState,
  methods: OperationalPaymentMethodView[],
  categories: OperationalPaymentCategoryView[] = [],
): string | null {
  return getOperationalPaymentBlockingMessages(draft, methods, categories)[0] ?? null;
}

export function canCommitOperationalPaymentDraft(
  draft: OperationalPaymentDraftState,
  methods: OperationalPaymentMethodView[],
  categories: OperationalPaymentCategoryView[] = [],
): boolean {
  return getOperationalPaymentBlockingMessages(draft, methods, categories).length === 0;
}

export function getOperationalPaymentUiState({
  categories = [],
  draft,
  hasCommitError,
  hasConfirmedDraft,
  hasSelectedPayment,
  isCaptureActive,
  isCommitPending,
  methods,
}: {
  categories?: OperationalPaymentCategoryView[];
  draft: OperationalPaymentDraftState;
  hasCommitError: boolean;
  hasConfirmedDraft: boolean;
  hasSelectedPayment: boolean;
  isCaptureActive: boolean;
  isCommitPending: boolean;
  methods: OperationalPaymentMethodView[];
}): OperationalPaymentUiState {
  if (hasCommitError) {
    return "ERROR";
  }

  if (isCommitPending) {
    return "CONFIRMING";
  }

  if (hasConfirmedDraft) {
    return "CONFIRMED";
  }

  if (!isCaptureActive) {
    return hasSelectedPayment ? "LIST_VIEW_READY" : "NO_SELECTION";
  }

  if (
    draft.payeeName.trim().length === 0 &&
    draft.categoryCode.trim().length === 0 &&
    draft.paymentMethodCode.trim().length === 0 &&
    draft.totalAmountText.trim().length === 0 &&
    draft.notes.trim().length === 0 &&
    draft.concept.trim().length === 0
  ) {
    return "CAPTURING";
  }

  if (draft.payeeName.trim().length === 0) {
    return "DRAFT_INCOMPLETE";
  }

  if (draft.categoryCode.trim().length === 0) {
    return "BLOCKED_MISSING_CATEGORY";
  }

  if (getOperationalPaymentDerivedConcept(draft, categories).length === 0) {
    return "BLOCKED_MISSING_REFERENCE";
  }

  if (getOperationalPaymentAmountCents(draft.totalAmountText) === null) {
    return "BLOCKED_MISSING_AMOUNT";
  }

  if (!isOperationalPaymentMethodSelectable(draft.paymentMethodCode, methods)) {
    return "BLOCKED_MISSING_METHOD";
  }

  return "READY_TO_CONFIRM";
}

export function getOperationalPaymentCreateStepKey(
  draft: OperationalPaymentDraftState,
  methods: OperationalPaymentMethodView[],
  categories: OperationalPaymentCategoryView[] = [],
): string {
  if (
    draft.payeeName.trim().length === 0 ||
    draft.categoryCode.trim().length === 0 ||
    getOperationalPaymentDerivedConcept(draft, categories).length === 0
  ) {
    return "details";
  }

  if (getOperationalPaymentAmountCents(draft.totalAmountText) === null) {
    return "amount";
  }

  if (!isOperationalPaymentMethodSelectable(draft.paymentMethodCode, methods)) {
    return "method";
  }

  return "save";
}

export function buildCreateOperationalPaymentRequest(
  workstationCode: string,
  draft: OperationalPaymentDraftState,
  methods: OperationalPaymentMethodView[] = [],
  categories: OperationalPaymentCategoryView[] = [],
): CreateOperationalPaymentRequest {
  const totalCents = getOperationalPaymentAmountCents(draft.totalAmountText);
  const derivedConcept = getOperationalPaymentDerivedConcept(draft, categories);

  if (draft.payeeName.trim().length === 0) {
    throw new Error("Captura el beneficiario antes de guardar.");
  }

  if (draft.categoryCode.trim().length === 0) {
    throw new Error("Selecciona la categoria antes de guardar.");
  }

  if (derivedConcept.length === 0) {
    throw new Error("Captura una referencia antes de guardar.");
  }

  if (totalCents === null) {
    throw new Error("Captura un monto valido antes de guardar.");
  }

  if (!isOperationalPaymentMethodSelectable(draft.paymentMethodCode, methods)) {
    throw new Error("Selecciona el metodo antes de guardar.");
  }

  return {
    workstation_code: workstationCode,
    payee_name: draft.payeeName.trim(),
    concept: derivedConcept,
    category_code: draft.categoryCode.length > 0 ? draft.categoryCode : undefined,
    payment_method_code: draft.paymentMethodCode,
    total_amount: formatCurrencyAmountForRequest(totalCents),
    notes: draft.notes.trim().length > 0 ? draft.notes.trim() : undefined,
  };
}

function formatCurrencyAmountForRequest(totalCents: number): string {
  const formattedValue = formatMoneyFromCents(totalCents);
  if (formattedValue.includes(".")) {
    return formattedValue.padEnd(formattedValue.indexOf(".") + 3, "0");
  }

  return `${formattedValue}.00`;
}
