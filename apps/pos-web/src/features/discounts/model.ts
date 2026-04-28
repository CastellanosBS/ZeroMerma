import type {
  CreateOperationalDiscountRequest,
  DiscountControlsView,
  OperationalDiscountCategoryView,
  OperationalDiscountMethodView,
} from "../../lib/api-contracts";
import {
  formatMoneyFromCents,
  parseMoneyToCents,
  sanitizeMoneyInput,
} from "../pos-terminal/model";

export interface OperationalDiscountDraftState {
  categoryCode: string;
  concept: string;
  highValueAcknowledged: boolean;
  notes: string;
  paymentMethodCode: string;
  subjectName: string;
  totalAmountText: string;
}

export type OperationalDiscountUiState =
  | "NO_SELECTION"
  | "LIST_VIEW_READY"
  | "CAPTURING"
  | "DRAFT_INCOMPLETE"
  | "BLOCKED_MISSING_CATEGORY"
  | "BLOCKED_MISSING_REFERENCE"
  | "BLOCKED_MISSING_AMOUNT"
  | "BLOCKED_MISSING_METHOD"
  | "BLOCKED_HIGH_VALUE_ACKNOWLEDGEMENT"
  | "READY_TO_CONFIRM"
  | "CONFIRMING"
  | "CONFIRMED"
  | "ERROR";

export function createInitialOperationalDiscountDraftState(): OperationalDiscountDraftState {
  return {
    categoryCode: "",
    concept: "",
    highValueAcknowledged: false,
    notes: "",
    paymentMethodCode: "",
    subjectName: "",
    totalAmountText: "",
  };
}

export function getOperationalDiscountMethodLabel(code: string): string {
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

export function getOperationalDiscountMethod(
  paymentMethodCode: string,
  methods: OperationalDiscountMethodView[],
): OperationalDiscountMethodView | null {
  return methods.find((method) => method.code === paymentMethodCode) ?? null;
}

export function isOperationalDiscountMethodSelectable(
  paymentMethodCode: string,
  methods: OperationalDiscountMethodView[],
): boolean {
  const selectedMethod = getOperationalDiscountMethod(paymentMethodCode, methods);
  return Boolean(selectedMethod?.is_enabled);
}

export function doesOperationalDiscountAffectCashDrawer(
  paymentMethodCode: string,
  methods: OperationalDiscountMethodView[] = [],
): boolean {
  const selectedMethod = getOperationalDiscountMethod(paymentMethodCode, methods);
  if (selectedMethod) {
    return selectedMethod.affects_cash_drawer;
  }

  return paymentMethodCode === "CASH";
}

export function sanitizeOperationalDiscountAmountInput(value: string): string {
  return sanitizeMoneyInput(value);
}

export function getOperationalDiscountDerivedConcept(
  draft: OperationalDiscountDraftState,
  categories: OperationalDiscountCategoryView[] = [],
): string {
  void categories;
  return draft.concept.trim();
}

export function getOperationalDiscountAmountCents(amountText: string): number | null {
  const amountCents = parseMoneyToCents(amountText);
  if (amountCents === null || amountCents <= 0) {
    return null;
  }

  return amountCents;
}

export function getOperationalDiscountCategoryLabel(
  categoryCode: string,
  categories: OperationalDiscountCategoryView[],
): string | null {
  return categories.find((category) => category.code === categoryCode)?.name ?? null;
}

export function isOperationalDiscountHighValue(
  draft: OperationalDiscountDraftState,
  controls?: Pick<DiscountControlsView, "high_value_amount_threshold"> | null,
): boolean {
  if (!controls) {
    return false;
  }

  const amountCents = getOperationalDiscountAmountCents(draft.totalAmountText);
  const thresholdCents =
    controls.high_value_amount_threshold === undefined
      ? null
      : parseMoneyToCents(String(controls.high_value_amount_threshold));

  if (amountCents === null || thresholdCents === null) {
    return false;
  }

  return amountCents >= thresholdCents;
}

export function getOperationalDiscountBlockingMessages(
  draft: OperationalDiscountDraftState,
  methods: OperationalDiscountMethodView[],
  categories: OperationalDiscountCategoryView[] = [],
  controls?: Pick<DiscountControlsView, "high_value_amount_threshold"> | null,
): string[] {
  const messages: string[] = [];

  if (draft.subjectName.trim().length === 0) {
    messages.push("Captura la persona o entidad.");
  }

  if (draft.categoryCode.trim().length === 0) {
    messages.push("Selecciona la categoria del descuento.");
  }

  if (getOperationalDiscountDerivedConcept(draft, categories).length === 0) {
    messages.push("Captura un motivo o referencia.");
  }

  if (getOperationalDiscountAmountCents(draft.totalAmountText) === null) {
    messages.push("Captura un monto valido.");
  }

  if (!isOperationalDiscountMethodSelectable(draft.paymentMethodCode, methods)) {
    messages.push("Selecciona el metodo del descuento.");
  }

  if (isOperationalDiscountHighValue(draft, controls) && !draft.highValueAcknowledged) {
    messages.push("Confirma el descuento de alto valor.");
  }

  return messages;
}

export function getOperationalDiscountBlockedReason(
  draft: OperationalDiscountDraftState,
  methods: OperationalDiscountMethodView[],
  categories: OperationalDiscountCategoryView[] = [],
  controls?: Pick<DiscountControlsView, "high_value_amount_threshold"> | null,
): string | null {
  return getOperationalDiscountBlockingMessages(draft, methods, categories, controls)[0] ?? null;
}

export function canCommitOperationalDiscountDraft(
  draft: OperationalDiscountDraftState,
  methods: OperationalDiscountMethodView[],
  categories: OperationalDiscountCategoryView[] = [],
  controls?: Pick<DiscountControlsView, "high_value_amount_threshold"> | null,
): boolean {
  return getOperationalDiscountBlockingMessages(draft, methods, categories, controls).length === 0;
}

export function getOperationalDiscountUiState({
  categories = [],
  controls,
  draft,
  hasCommitError,
  hasConfirmedDraft,
  hasSelectedDiscount,
  isCaptureActive,
  isCommitPending,
  methods,
}: {
  categories?: OperationalDiscountCategoryView[];
  controls?: Pick<DiscountControlsView, "high_value_amount_threshold"> | null;
  draft: OperationalDiscountDraftState;
  hasCommitError: boolean;
  hasConfirmedDraft: boolean;
  hasSelectedDiscount: boolean;
  isCaptureActive: boolean;
  isCommitPending: boolean;
  methods: OperationalDiscountMethodView[];
}): OperationalDiscountUiState {
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
    return hasSelectedDiscount ? "LIST_VIEW_READY" : "NO_SELECTION";
  }

  if (
    draft.subjectName.trim().length === 0 &&
    draft.categoryCode.trim().length === 0 &&
    draft.paymentMethodCode.trim().length === 0 &&
    draft.totalAmountText.trim().length === 0 &&
    draft.notes.trim().length === 0 &&
    draft.concept.trim().length === 0
  ) {
    return "CAPTURING";
  }

  if (draft.subjectName.trim().length === 0) {
    return "DRAFT_INCOMPLETE";
  }

  if (draft.categoryCode.trim().length === 0) {
    return "BLOCKED_MISSING_CATEGORY";
  }

  if (getOperationalDiscountDerivedConcept(draft, categories).length === 0) {
    return "BLOCKED_MISSING_REFERENCE";
  }

  if (getOperationalDiscountAmountCents(draft.totalAmountText) === null) {
    return "BLOCKED_MISSING_AMOUNT";
  }

  if (!isOperationalDiscountMethodSelectable(draft.paymentMethodCode, methods)) {
    return "BLOCKED_MISSING_METHOD";
  }

  if (isOperationalDiscountHighValue(draft, controls) && !draft.highValueAcknowledged) {
    return "BLOCKED_HIGH_VALUE_ACKNOWLEDGEMENT";
  }

  return "READY_TO_CONFIRM";
}

export function getOperationalDiscountCreateStepKey(
  draft: OperationalDiscountDraftState,
  methods: OperationalDiscountMethodView[],
  categories: OperationalDiscountCategoryView[] = [],
  controls?: Pick<DiscountControlsView, "high_value_amount_threshold"> | null,
): string {
  if (
    draft.subjectName.trim().length === 0 ||
    draft.categoryCode.trim().length === 0 ||
    getOperationalDiscountDerivedConcept(draft, categories).length === 0
  ) {
    return "details";
  }

  if (getOperationalDiscountAmountCents(draft.totalAmountText) === null) {
    return "amount";
  }

  if (!isOperationalDiscountMethodSelectable(draft.paymentMethodCode, methods)) {
    return "method";
  }

  if (isOperationalDiscountHighValue(draft, controls) && !draft.highValueAcknowledged) {
    return "save";
  }

  return "save";
}

export function buildCreateOperationalDiscountRequest(
  workstationCode: string,
  draft: OperationalDiscountDraftState,
  methods: OperationalDiscountMethodView[] = [],
  categories: OperationalDiscountCategoryView[] = [],
  controls?: Pick<DiscountControlsView, "high_value_amount_threshold"> | null,
): CreateOperationalDiscountRequest {
  const totalCents = getOperationalDiscountAmountCents(draft.totalAmountText);
  const derivedConcept = getOperationalDiscountDerivedConcept(draft, categories);

  if (draft.subjectName.trim().length === 0) {
    throw new Error("Captura la persona o entidad antes de guardar.");
  }

  if (draft.categoryCode.trim().length === 0) {
    throw new Error("Selecciona la categoria antes de guardar.");
  }

  if (derivedConcept.length === 0) {
    throw new Error("Captura un motivo o referencia antes de guardar.");
  }

  if (totalCents === null) {
    throw new Error("Captura un monto valido antes de guardar.");
  }

  if (!isOperationalDiscountMethodSelectable(draft.paymentMethodCode, methods)) {
    throw new Error("Selecciona el metodo antes de guardar.");
  }

  if (isOperationalDiscountHighValue(draft, controls) && !draft.highValueAcknowledged) {
    throw new Error("Confirma el descuento de alto valor antes de guardar.");
  }

  return {
    workstation_code: workstationCode,
    subject_name: draft.subjectName.trim(),
    concept: derivedConcept,
    category_code: draft.categoryCode.length > 0 ? draft.categoryCode : undefined,
    payment_method_code: draft.paymentMethodCode,
    total_amount: formatCurrencyAmountForRequest(totalCents),
    high_value_acknowledged: draft.highValueAcknowledged,
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
