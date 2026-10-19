import { usePosAuthStore } from "../auth/auth-store";
import {
  ApiError,
  createCommandIntentionCoordinator,
  type CommandIntentionMetadata,
} from "@zeromerma/api-client";
import type {
  CashCloseCommitRequest,
  CashCloseCommitResultView,
  CashSessionOpenResultView,
  CreateOperationalDiscountRequest,
  CreateOperationalPaymentRequest,
  OpenCashSessionRequest,
  OperationalDiscountCommitResultView,
  OperationalPaymentCommitResultView,
} from "../../lib/api-contracts";
import { requestJson } from "../../lib/http";
import { openCashSession } from "../cash-session-open/cash-session-api";
import { commitCashClose } from "../cash-close/cash-close-api";
import { createPayment } from "../payments/payments-api";
import { createDiscount } from "../discounts/discounts-api";

export type CashCommandCode = "open" | "payment" | "discount" | "close";
export interface CashIntentionContext {
  userId: string;
  branchId: string;
  workstationId: string;
  workstationCode: string;
  cashSessionId: string | null;
  commandCode: CashCommandCode;
}
export type CashIntentionMetadata = CommandIntentionMetadata<CashIntentionContext>;
export type CashCommandPayload =
  | OpenCashSessionRequest
  | CreateOperationalPaymentRequest
  | CreateOperationalDiscountRequest
  | CashCloseCommitRequest;
export type CashCommandResult =
  | CashSessionOpenResultView
  | OperationalPaymentCommitResultView
  | OperationalDiscountCommitResultView
  | CashCloseCommitResultView;
export const CASH_INTENTION_STORAGE_PREFIX = "zeromerma-cash-intention:";
const paths = {
  open: "cash-sessions",
  payment: "payments",
  discount: "discounts",
  close: "cash-close",
} as const;
export const cashIntentions = createCommandIntentionCoordinator<
  CashIntentionContext,
  CashCommandPayload,
  CashCommandResult
>({
  storagePrefix: CASH_INTENTION_STORAGE_PREFIX,
  eventName: "zeromerma-cash-intention",
  contextFields: [
    "userId",
    "branchId",
    "workstationId",
    "workstationCode",
    "cashSessionId",
    "commandCode",
  ],
  nullableFields: ["cashSessionId"],
  scope: (context) => context.workstationId,
  validateContext: (context) =>
    Object.hasOwn(paths, context.commandCode) &&
    (context.commandCode === "open"
      ? context.cashSessionId === null
      : context.cashSessionId !== null),
  send: (context, payload, idempotencyKey) => {
    if (context.commandCode === "open")
      return openCashSession({
        payload: payload as OpenCashSessionRequest,
        idempotencyKey,
      });
    if (context.commandCode === "payment")
      return createPayment({
        payload: payload as CreateOperationalPaymentRequest,
        idempotencyKey,
      });
    if (context.commandCode === "discount")
      return createDiscount({
        payload: payload as CreateOperationalDiscountRequest,
        idempotencyKey,
      });
    return commitCashClose(payload as CashCloseCommitRequest, idempotencyKey);
  },
  isRecoveredRejection: (metadata, error) =>
    metadata.commandCode === "close" &&
    error instanceof ApiError &&
    error.statusCode === 409 &&
    error.error?.code === "CASH_CLOSE_ALREADY_EXISTS" &&
    error.idempotencyReplayed,
  recover: async (metadata) => {
    const query = new URLSearchParams({ workstation_code: metadata.workstationCode });
    if (metadata.cashSessionId !== null) query.set("cash_session_id", metadata.cashSessionId);
    const result = await requestJson<CashCommandResult>({
      path: `/v1/${paths[metadata.commandCode]}/confirmations/${encodeURIComponent(metadata.key)}?${query}`,
    });
    if (
      result.branch_id !== metadata.branchId ||
      result.workstation_id !== metadata.workstationId ||
      (metadata.cashSessionId !== null &&
        (!("cash_session_id" in result) || result.cash_session_id !== metadata.cashSessionId))
    )
      throw new ApiError(409, "La referencia pertenece a otro turno o estación.", {
        code: "IDEMPOTENCY_KEY_REUSED",
        message: "La referencia pertenece a otro turno o estación.",
        details: null,
        field_errors: null,
        request_id: null,
      });
    return result;
  },
});

usePosAuthStore.subscribe((state, previous) => {
  if (
    state.generation !== previous.generation ||
    state.user?.id !== previous.user?.id ||
    state.session?.id !== previous.session?.id ||
    state.user?.authorization_version !== previous.user?.authorization_version
  )
    cashIntentions.forgetBodies();
});
