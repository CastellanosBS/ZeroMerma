import {
  ApiError,
  createCommandIntentionCoordinator,
  type components,
} from "@zeromerma/api-client";
import { requestJson } from "../../lib/http";
import { usePosAuthStore } from "../auth/auth-store";

export type FinancialRefund = components["schemas"]["FinancialRefundView"];
type SettlementRequest = components["schemas"]["RefundSettlementRequest"];
export interface RefundIntentionContext {
  userId: string;
  branchId: string;
  workstationId: string;
  workstationCode: string;
  cashSessionId: string;
  sourceType: string;
  sourceId: string;
}
function prefix(sourceType: string) {
  return sourceType === "SALE_RETURN" ? "/v1/returns" : "/v1/orders";
}
export const refundIntentions = createCommandIntentionCoordinator<
  RefundIntentionContext,
  SettlementRequest,
  FinancialRefund
>({
  storagePrefix: "zeromerma-refund-settlement:",
  eventName: "zeromerma-refund-settlement",
  contextFields: [
    "userId",
    "branchId",
    "workstationId",
    "workstationCode",
    "cashSessionId",
    "sourceType",
    "sourceId",
  ],
  scope: (context) => context.workstationId,
  validateContext: (context) => ["SALE_RETURN", "ORDER_CANCELLATION"].includes(context.sourceType),
  send: (context, body, key) =>
    requestJson<FinancialRefund>({
      path: `${prefix(context.sourceType)}/${encodeURIComponent(context.sourceId)}/refund-settlements`,
      method: "POST",
      body,
      headers: { "Idempotency-Key": key },
    }),
  recover: async (metadata) => {
    const params = new URLSearchParams({
      workstation_code: metadata.workstationCode,
      cash_session_id: metadata.cashSessionId,
    });
    const result = await requestJson<FinancialRefund>({
      path: `${prefix(metadata.sourceType)}/refund-settlements/${encodeURIComponent(metadata.key)}?${params}`,
    });
    if (result.source_id !== metadata.sourceId || result.source_type !== metadata.sourceType) {
      throw new ApiError(409, "La referencia pertenece a otro reembolso.", {
        code: "IDEMPOTENCY_KEY_REUSED",
        message: "La referencia pertenece a otro reembolso.",
        details: null,
        field_errors: null,
        request_id: null,
      });
    }
    return result;
  },
});
usePosAuthStore.subscribe((state, previous) => {
  if (
    state.generation !== previous.generation ||
    state.user?.id !== previous.user?.id ||
    state.session?.id !== previous.session?.id ||
    state.user?.authorization_version !== previous.user?.authorization_version
  ) {
    refundIntentions.forgetBodies();
  }
});
