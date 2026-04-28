import { useCallback, useEffect, useMemo, useReducer } from "react";

import {
  CARD_PAYMENT_METHOD_CODE,
  CASH_PAYMENT_METHOD_CODE,
  CONTROL_STATE_PAYMENT_CAPTURE,
  CONTROL_STATE_QUANTITY_CAPTURE,
  MIXED_PAYMENT_METHOD_CODE,
  parseMoneyToCents,
  sanitizeMoneyInput,
  type PosControlState,
  type PosMixedPaymentLegDraft,
  type PosPaymentDraft,
  type PosPaymentMethodCode,
  type PosSplitPaymentMethodCode,
} from "./model";

export const SALE_FLOW_EMPTY_SELECTION = "SELECTION_EMPTY";
export const SALE_FLOW_ACTIVE_SELECTION = "SELECTION_ACTIVE";
export const SALE_FLOW_QUANTITY_CAPTURE = "QUANTITY_CAPTURE";
export const SALE_FLOW_PAYMENT_AMOUNT_CAPTURE = "PAYMENT_AMOUNT_CAPTURE";
export const SALE_FLOW_AMOUNT_CONFIRMED = "AMOUNT_CONFIRMED";
export const SALE_FLOW_PROCESSING = "PROCESSING";
export const SALE_FLOW_FINISHED = "SALE_FINISHED";
export const SALE_FLOW_RECOVERABLE_ERROR = "RECOVERABLE_ERROR";

export type SaleFlowMode =
  | typeof SALE_FLOW_EMPTY_SELECTION
  | typeof SALE_FLOW_ACTIVE_SELECTION
  | typeof SALE_FLOW_QUANTITY_CAPTURE
  | typeof SALE_FLOW_PAYMENT_AMOUNT_CAPTURE
  | typeof SALE_FLOW_AMOUNT_CONFIRMED
  | typeof SALE_FLOW_PROCESSING
  | typeof SALE_FLOW_FINISHED
  | typeof SALE_FLOW_RECOVERABLE_ERROR;

export interface PosMixedPaymentLeg
  extends PosMixedPaymentLegDraft {
  amountCents: number;
  key: string;
}

export interface SaleFlowRecoverableError {
  kind: "operation" | "payment";
  message: string;
  retryMode: typeof SALE_FLOW_AMOUNT_CONFIRMED | typeof SALE_FLOW_PAYMENT_AMOUNT_CAPTURE;
}

interface SaleFlowControllerState {
  cashReceivedText: string;
  mixedConfirmedLegs: PosMixedPaymentLeg[];
  mixedCurrentLegAmountText: string;
  mixedCurrentLegMethodCode: PosSplitPaymentMethodCode;
  mode: SaleFlowMode;
  paymentMethodCode: PosPaymentMethodCode;
  pendingPaymentIntentAt: number | null;
  printFailureMessage: string | null;
  recoverableError: SaleFlowRecoverableError | null;
  selectedTicketLineId: string | null;
  ticketRequested: boolean;
}

function createDraftResetState(
  overrides?: Partial<SaleFlowControllerState>,
): SaleFlowControllerState {
  return {
    ...createInitialSaleFlowControllerState(),
    ...overrides,
  };
}

type SaleFlowAction =
  | { type: "SYNC_CONTEXT"; cartLineCount: number; controlState: PosControlState; hasCompletedSale: boolean }
  | { type: "ARM_PAYMENT_INTENT"; now: number }
  | { type: "CLEAR_PAYMENT_INTENT" }
  | { type: "ENTER_PAYMENT_CAPTURE"; paymentMethodCode?: PosPaymentMethodCode }
  | { type: "SET_CASH_RECEIVED_TEXT"; value: string }
  | { type: "SET_MIXED_CURRENT_LEG_AMOUNT_TEXT"; value: string }
  | { type: "SET_MIXED_CURRENT_LEG_METHOD"; value: PosSplitPaymentMethodCode }
  | { type: "SWITCH_PAYMENT_METHOD"; value: PosPaymentMethodCode }
  | { type: "CONFIRM_AMOUNT" }
  | { type: "CONFIRM_MIXED_LEG"; leg: PosMixedPaymentLeg; remainingAfterConfirmCents: number }
  | { type: "RETURN_TO_PAYMENT_EDIT" }
  | { type: "START_PROCESSING" }
  | { type: "FINISH_SUCCESS" }
  | { type: "SET_RECOVERABLE_ERROR"; error: SaleFlowRecoverableError }
  | { type: "CLEAR_RECOVERABLE_ERROR"; retryMode?: SaleFlowRecoverableError["retryMode"] }
  | { type: "TOGGLE_TICKET_REQUESTED" }
  | { type: "SET_SELECTED_TICKET_LINE_ID"; value: string | null }
  | { type: "REGISTER_PRINT_FAILURE"; message: string }
  | { type: "CLEAR_PRINT_FAILURE" }
  | { type: "RESET_AFTER_FINISH" };

export interface SaleFlowPaymentComputation {
  capturedAmountCents: number;
  cashTenderedAmountCents: number;
  changeAmountCents: number;
  currentLegAmountCents: number;
  nonCashTenderedAmountCents: number;
  previewCapturedAmountCents: number;
  previewChangeAmountCents: number;
  previewRemainingAmountCents: number;
  remainingAmountCents: number;
}

function createInitialSaleFlowControllerState(): SaleFlowControllerState {
  return {
    cashReceivedText: "",
    mixedConfirmedLegs: [],
    mixedCurrentLegAmountText: "",
    mixedCurrentLegMethodCode: CASH_PAYMENT_METHOD_CODE,
    mode: SALE_FLOW_EMPTY_SELECTION,
    paymentMethodCode: CASH_PAYMENT_METHOD_CODE,
    pendingPaymentIntentAt: null,
    printFailureMessage: null,
    recoverableError: null,
    selectedTicketLineId: null,
    ticketRequested: false,
  };
}

function getSelectionMode({
  cartLineCount,
  controlState,
  hasCompletedSale,
}: {
  cartLineCount: number;
  controlState: PosControlState;
  hasCompletedSale: boolean;
}): SaleFlowMode {
  if (hasCompletedSale) {
    return SALE_FLOW_FINISHED;
  }

  if (controlState === CONTROL_STATE_QUANTITY_CAPTURE) {
    return SALE_FLOW_QUANTITY_CAPTURE;
  }

  if (controlState === CONTROL_STATE_PAYMENT_CAPTURE) {
    return SALE_FLOW_PAYMENT_AMOUNT_CAPTURE;
  }

  return cartLineCount > 0 ? SALE_FLOW_ACTIVE_SELECTION : SALE_FLOW_EMPTY_SELECTION;
}

function mergeMixedLegs(
  legs: PosMixedPaymentLeg[],
  nextLeg: PosMixedPaymentLeg,
): PosMixedPaymentLeg[] {
  const existingLeg = legs.find((leg) => leg.methodCode === nextLeg.methodCode);
  if (!existingLeg) {
    return [...legs, nextLeg];
  }

  const mergedAmountCents = existingLeg.amountCents + nextLeg.amountCents;
  const mergedAmountText = (mergedAmountCents / 100).toFixed(2);

  return legs.map((leg) =>
    leg.methodCode === nextLeg.methodCode
      ? {
          ...leg,
          amountCents: mergedAmountCents,
          amountText: mergedAmountText,
        }
      : leg,
  );
}

function reduceSaleFlowControllerState(
  state: SaleFlowControllerState,
  action: SaleFlowAction,
): SaleFlowControllerState {
  switch (action.type) {
    case "SYNC_CONTEXT": {
      const nextSelectionMode = getSelectionMode(action);
      if (action.hasCompletedSale) {
        return {
          ...state,
          mode: SALE_FLOW_FINISHED,
          pendingPaymentIntentAt: null,
          selectedTicketLineId: null,
        };
      }

      if (
        action.cartLineCount === 0 &&
        action.controlState !== CONTROL_STATE_QUANTITY_CAPTURE
      ) {
        return createDraftResetState({
          mode: nextSelectionMode,
        });
      }

      if (state.mode === SALE_FLOW_PROCESSING || state.mode === SALE_FLOW_AMOUNT_CONFIRMED) {
        return state;
      }

      if (state.mode === SALE_FLOW_RECOVERABLE_ERROR && action.controlState === CONTROL_STATE_PAYMENT_CAPTURE) {
        return state;
      }

      return {
        ...state,
        mode: nextSelectionMode,
        selectedTicketLineId:
          nextSelectionMode === SALE_FLOW_ACTIVE_SELECTION ? state.selectedTicketLineId : null,
      };
    }
    case "ARM_PAYMENT_INTENT":
      return {
        ...state,
        pendingPaymentIntentAt: action.now,
      };
    case "CLEAR_PAYMENT_INTENT":
      return {
        ...state,
        pendingPaymentIntentAt: null,
      };
    case "ENTER_PAYMENT_CAPTURE":
      return {
        ...state,
        mode: SALE_FLOW_PAYMENT_AMOUNT_CAPTURE,
        paymentMethodCode: action.paymentMethodCode ?? state.paymentMethodCode,
        pendingPaymentIntentAt: null,
        printFailureMessage: null,
        recoverableError: null,
        selectedTicketLineId: null,
      };
    case "SET_CASH_RECEIVED_TEXT":
      return {
        ...state,
        cashReceivedText: sanitizeMoneyInput(action.value),
        mode:
          state.mode === SALE_FLOW_AMOUNT_CONFIRMED || state.mode === SALE_FLOW_RECOVERABLE_ERROR
            ? SALE_FLOW_PAYMENT_AMOUNT_CAPTURE
            : state.mode,
        recoverableError: null,
      };
    case "SET_MIXED_CURRENT_LEG_AMOUNT_TEXT":
      return {
        ...state,
        mixedCurrentLegAmountText: sanitizeMoneyInput(action.value),
        mode:
          state.mode === SALE_FLOW_AMOUNT_CONFIRMED || state.mode === SALE_FLOW_RECOVERABLE_ERROR
            ? SALE_FLOW_PAYMENT_AMOUNT_CAPTURE
            : state.mode,
        recoverableError: null,
      };
    case "SET_MIXED_CURRENT_LEG_METHOD":
      return {
        ...state,
        mixedCurrentLegMethodCode: action.value,
        mode:
          state.mode === SALE_FLOW_AMOUNT_CONFIRMED || state.mode === SALE_FLOW_RECOVERABLE_ERROR
            ? SALE_FLOW_PAYMENT_AMOUNT_CAPTURE
            : state.mode,
        recoverableError: null,
      };
    case "SWITCH_PAYMENT_METHOD":
      return {
        ...state,
        cashReceivedText: "",
        mixedConfirmedLegs: [],
        mixedCurrentLegAmountText: "",
        mixedCurrentLegMethodCode:
          action.value === MIXED_PAYMENT_METHOD_CODE
            ? CASH_PAYMENT_METHOD_CODE
            : state.mixedCurrentLegMethodCode,
        mode: SALE_FLOW_PAYMENT_AMOUNT_CAPTURE,
        paymentMethodCode: action.value,
        pendingPaymentIntentAt: null,
        recoverableError: null,
      };
    case "CONFIRM_AMOUNT":
      return {
        ...state,
        mode: SALE_FLOW_AMOUNT_CONFIRMED,
        recoverableError: null,
      };
    case "CONFIRM_MIXED_LEG":
      return {
        ...state,
        mixedConfirmedLegs: mergeMixedLegs(state.mixedConfirmedLegs, action.leg),
        mixedCurrentLegAmountText: "",
        mixedCurrentLegMethodCode:
          action.leg.methodCode === CASH_PAYMENT_METHOD_CODE
            ? CARD_PAYMENT_METHOD_CODE
            : CASH_PAYMENT_METHOD_CODE,
        mode:
          action.remainingAfterConfirmCents === 0
            ? SALE_FLOW_AMOUNT_CONFIRMED
            : SALE_FLOW_PAYMENT_AMOUNT_CAPTURE,
        recoverableError: null,
      };
    case "RETURN_TO_PAYMENT_EDIT":
      return {
        ...state,
        mode: SALE_FLOW_PAYMENT_AMOUNT_CAPTURE,
        recoverableError: null,
      };
    case "START_PROCESSING":
      return {
        ...state,
        mode: SALE_FLOW_PROCESSING,
        recoverableError: null,
      };
    case "FINISH_SUCCESS":
      return {
        ...state,
        mode: SALE_FLOW_FINISHED,
        pendingPaymentIntentAt: null,
        printFailureMessage: null,
        recoverableError: null,
        selectedTicketLineId: null,
      };
    case "SET_RECOVERABLE_ERROR":
      return {
        ...state,
        mode: SALE_FLOW_RECOVERABLE_ERROR,
        recoverableError: action.error,
      };
    case "CLEAR_RECOVERABLE_ERROR":
      return {
        ...state,
        mode: action.retryMode ?? SALE_FLOW_PAYMENT_AMOUNT_CAPTURE,
        recoverableError: null,
      };
    case "TOGGLE_TICKET_REQUESTED":
      if (state.mode !== SALE_FLOW_AMOUNT_CONFIRMED) {
        return state;
      }

      return {
        ...state,
        ticketRequested: !state.ticketRequested,
      };
    case "SET_SELECTED_TICKET_LINE_ID":
      return {
        ...state,
        selectedTicketLineId: action.value,
      };
    case "REGISTER_PRINT_FAILURE":
      return {
        ...state,
        printFailureMessage: action.message,
      };
    case "CLEAR_PRINT_FAILURE":
      return {
        ...state,
        printFailureMessage: null,
      };
    case "RESET_AFTER_FINISH":
      return createInitialSaleFlowControllerState();
    default:
      return state;
  }
}

function computeMixedPaymentTotals(legs: PosMixedPaymentLeg[]) {
  return legs.reduce(
    (totals, leg) => ({
      cashTenderedAmountCents:
        totals.cashTenderedAmountCents +
        (leg.methodCode === CASH_PAYMENT_METHOD_CODE ? leg.amountCents : 0),
      nonCashTenderedAmountCents:
        totals.nonCashTenderedAmountCents +
        (leg.methodCode === CARD_PAYMENT_METHOD_CODE ? leg.amountCents : 0),
      totalAmountCents: totals.totalAmountCents + leg.amountCents,
    }),
    {
      cashTenderedAmountCents: 0,
      nonCashTenderedAmountCents: 0,
      totalAmountCents: 0,
    },
  );
}

export function isPaymentIntentComboReady(
  armedAt: number | null,
  now: number,
  windowMs = 300,
): boolean {
  return armedAt !== null && now - armedAt <= windowMs;
}

export function useSaleFlowController({
  cartLineCount,
  controlState,
  hasCompletedSale,
  totalAmountCents,
}: {
  cartLineCount: number;
  controlState: PosControlState;
  hasCompletedSale: boolean;
  totalAmountCents: number;
}) {
  const [state, dispatch] = useReducer(
    reduceSaleFlowControllerState,
    undefined,
    createInitialSaleFlowControllerState,
  );

  useEffect(() => {
    dispatch({
      type: "SYNC_CONTEXT",
      cartLineCount,
      controlState,
      hasCompletedSale,
    });
  }, [cartLineCount, controlState, hasCompletedSale]);

  const paymentComputation = useMemo<SaleFlowPaymentComputation>(() => {
    if (state.paymentMethodCode === CARD_PAYMENT_METHOD_CODE) {
      return {
        capturedAmountCents: totalAmountCents,
        cashTenderedAmountCents: 0,
        changeAmountCents: 0,
        currentLegAmountCents: 0,
        nonCashTenderedAmountCents: totalAmountCents,
        previewCapturedAmountCents: totalAmountCents,
        previewChangeAmountCents: 0,
        previewRemainingAmountCents: 0,
        remainingAmountCents: 0,
      };
    }

    if (state.paymentMethodCode === CASH_PAYMENT_METHOD_CODE) {
      const cashTenderedAmountCents = parseMoneyToCents(state.cashReceivedText) ?? 0;
      return {
        capturedAmountCents: cashTenderedAmountCents,
        cashTenderedAmountCents,
        changeAmountCents: Math.max(cashTenderedAmountCents - totalAmountCents, 0),
        currentLegAmountCents: cashTenderedAmountCents,
        nonCashTenderedAmountCents: 0,
        previewCapturedAmountCents: cashTenderedAmountCents,
        previewChangeAmountCents: Math.max(cashTenderedAmountCents - totalAmountCents, 0),
        previewRemainingAmountCents: Math.max(totalAmountCents - cashTenderedAmountCents, 0),
        remainingAmountCents: Math.max(totalAmountCents - cashTenderedAmountCents, 0),
      };
    }

    const currentLegAmountCents = parseMoneyToCents(state.mixedCurrentLegAmountText) ?? 0;
    const confirmedTotals = computeMixedPaymentTotals(state.mixedConfirmedLegs);
    const previewTotals =
      currentLegAmountCents > 0
        ? computeMixedPaymentTotals([
            ...state.mixedConfirmedLegs,
            {
              amountCents: currentLegAmountCents,
              amountText: state.mixedCurrentLegAmountText,
              key: "preview",
              methodCode: state.mixedCurrentLegMethodCode,
            },
          ])
        : confirmedTotals;

    return {
      capturedAmountCents: confirmedTotals.totalAmountCents,
      cashTenderedAmountCents: confirmedTotals.cashTenderedAmountCents,
      changeAmountCents: Math.max(confirmedTotals.totalAmountCents - totalAmountCents, 0),
      currentLegAmountCents,
      nonCashTenderedAmountCents: confirmedTotals.nonCashTenderedAmountCents,
      previewCapturedAmountCents: previewTotals.totalAmountCents,
      previewChangeAmountCents: Math.max(previewTotals.totalAmountCents - totalAmountCents, 0),
      previewRemainingAmountCents: Math.max(totalAmountCents - previewTotals.totalAmountCents, 0),
      remainingAmountCents: Math.max(totalAmountCents - confirmedTotals.totalAmountCents, 0),
    };
  }, [
    state.cashReceivedText,
    state.mixedConfirmedLegs,
    state.mixedCurrentLegAmountText,
    state.mixedCurrentLegMethodCode,
    state.paymentMethodCode,
    totalAmountCents,
  ]);

  const armPaymentIntentCombo = useCallback((now = Date.now()) => {
    dispatch({ type: "ARM_PAYMENT_INTENT", now });
  }, []);

  const clearPaymentIntentCombo = useCallback(() => {
    dispatch({ type: "CLEAR_PAYMENT_INTENT" });
  }, []);

  const switchPaymentMethod = useCallback((paymentMethodCode: PosPaymentMethodCode) => {
    dispatch({ type: "SWITCH_PAYMENT_METHOD", value: paymentMethodCode });
  }, []);

  const updateCashReceivedText = useCallback((value: string) => {
    dispatch({ type: "SET_CASH_RECEIVED_TEXT", value });
  }, []);

  const updateMixedCurrentLegAmountText = useCallback((value: string) => {
    dispatch({ type: "SET_MIXED_CURRENT_LEG_AMOUNT_TEXT", value });
  }, []);

  const setMixedCurrentLegMethodCode = useCallback((value: PosSplitPaymentMethodCode) => {
    dispatch({ type: "SET_MIXED_CURRENT_LEG_METHOD", value });
  }, []);

  const setSelectedTicketLineId = useCallback((value: string | null) => {
    dispatch({ type: "SET_SELECTED_TICKET_LINE_ID", value });
  }, []);

  const enterPaymentCapture = useCallback((paymentMethodCode?: PosPaymentMethodCode) => {
    dispatch({ type: "ENTER_PAYMENT_CAPTURE", paymentMethodCode });
  }, []);

  const toggleTicketRequested = useCallback(() => {
    dispatch({ type: "TOGGLE_TICKET_REQUESTED" });
  }, []);

  const returnToPaymentEdit = useCallback(() => {
    dispatch({ type: "RETURN_TO_PAYMENT_EDIT" });
  }, []);

  const registerRecoverableError = useCallback((error: SaleFlowRecoverableError) => {
    dispatch({ type: "SET_RECOVERABLE_ERROR", error });
  }, []);

  const clearRecoverableError = useCallback(
    (retryMode?: SaleFlowRecoverableError["retryMode"]) => {
      dispatch({ type: "CLEAR_RECOVERABLE_ERROR", retryMode });
    },
    [],
  );

  const registerPrintFailure = useCallback((message: string) => {
    dispatch({ type: "REGISTER_PRINT_FAILURE", message });
  }, []);

  const clearPrintFailure = useCallback(() => {
    dispatch({ type: "CLEAR_PRINT_FAILURE" });
  }, []);

  const resetAfterFinish = useCallback(() => {
    dispatch({ type: "RESET_AFTER_FINISH" });
  }, []);

  const startProcessing = useCallback(() => {
    dispatch({ type: "START_PROCESSING" });
  }, []);

  const finishSuccess = useCallback(() => {
    dispatch({ type: "FINISH_SUCCESS" });
  }, []);

  const buildPaymentDraft = useCallback((): PosPaymentDraft => {
    if (state.paymentMethodCode === MIXED_PAYMENT_METHOD_CODE) {
      return {
        cashReceivedText: "",
        mixedConfirmedLegs: state.mixedConfirmedLegs.map((leg) => ({
          amountText: leg.amountText,
          methodCode: leg.methodCode,
        })),
        paymentMethodCode: state.paymentMethodCode,
      };
    }

    return {
      cashReceivedText: state.cashReceivedText,
      paymentMethodCode: state.paymentMethodCode,
    };
  }, [state.cashReceivedText, state.mixedConfirmedLegs, state.paymentMethodCode]);

  const confirmAmount = useCallback(
    (totalAmountCents: number): { ok: true } | { error: string; ok: false } => {
      if (state.paymentMethodCode === CARD_PAYMENT_METHOD_CODE) {
        dispatch({ type: "CONFIRM_AMOUNT" });
        return { ok: true };
      }

      if (state.paymentMethodCode === CASH_PAYMENT_METHOD_CODE) {
        const cashTenderedAmountCents = parseMoneyToCents(state.cashReceivedText) ?? 0;
        if (cashTenderedAmountCents <= 0) {
          return { error: "Captura un monto valido antes de continuar.", ok: false };
        }

        if (cashTenderedAmountCents < totalAmountCents) {
          return {
            error: `Faltan $${((totalAmountCents - cashTenderedAmountCents) / 100).toFixed(2)}. Captura un monto suficiente.`,
            ok: false,
          };
        }

        dispatch({ type: "CONFIRM_AMOUNT" });
        return { ok: true };
      }

      const currentLegAmountCents = parseMoneyToCents(state.mixedCurrentLegAmountText) ?? 0;
      const confirmedTotals = computeMixedPaymentTotals(state.mixedConfirmedLegs);
      if (confirmedTotals.totalAmountCents === totalAmountCents && currentLegAmountCents === 0) {
        dispatch({ type: "CONFIRM_AMOUNT" });
        return { ok: true };
      }

      if (currentLegAmountCents <= 0) {
        return { error: "Captura un monto valido para el tramo actual.", ok: false };
      }

      const remainingBeforeCurrentLegCents = totalAmountCents - confirmedTotals.totalAmountCents;
      if (currentLegAmountCents > remainingBeforeCurrentLegCents) {
        return {
          error: `Este tramo excede el restante. Quedan $${(remainingBeforeCurrentLegCents / 100).toFixed(2)} por cubrir.`,
          ok: false,
        };
      }

      const nextRemainingCents = remainingBeforeCurrentLegCents - currentLegAmountCents;
      dispatch({
        type: "CONFIRM_MIXED_LEG",
        leg: {
          amountCents: currentLegAmountCents,
          amountText: state.mixedCurrentLegAmountText,
          key: `${state.mixedCurrentLegMethodCode}-${state.mixedConfirmedLegs.length}`,
          methodCode: state.mixedCurrentLegMethodCode,
        },
        remainingAfterConfirmCents: nextRemainingCents,
      });

      return { ok: true };
    },
    [
      state.cashReceivedText,
      state.mixedConfirmedLegs,
      state.mixedCurrentLegAmountText,
      state.mixedCurrentLegMethodCode,
      state.paymentMethodCode,
    ],
  );

  return {
    armPaymentIntentCombo,
    buildPaymentDraft,
    clearPaymentIntentCombo,
    clearPrintFailure,
    clearRecoverableError,
    confirmAmount,
    enterPaymentCapture,
    finishSuccess,
    isPaymentIntentComboReady: (now = Date.now(), windowMs = 300) =>
      isPaymentIntentComboReady(state.pendingPaymentIntentAt, now, windowMs),
    paymentComputation,
    registerPrintFailure,
    registerRecoverableError,
    resetAfterFinish,
    returnToPaymentEdit,
    setMixedCurrentLegMethodCode,
    setSelectedTicketLineId,
    startProcessing,
    state,
    switchPaymentMethod,
    toggleTicketRequested,
    updateCashReceivedText,
    updateMixedCurrentLegAmountText,
  };
}
