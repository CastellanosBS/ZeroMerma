import { createCommandIntentionCoordinator, type components } from "@zeromerma/api-client";
import { requestJson } from "../../../lib/api";
import { useBackofficeAuthStore } from "../../auth/backoffice-auth-store";

export type OrderPolicyRequest = components["schemas"]["OrderPolicyRequest"];
export type OrderPolicyView = components["schemas"]["OrderPolicyView"];
export interface OrderPolicyContext { userId: string; branchId: string }
export const ORDER_POLICY_SCOPE = "order-policy";

export const orderPolicyIntentions = createCommandIntentionCoordinator<OrderPolicyContext, OrderPolicyRequest, OrderPolicyView>({
  storagePrefix: "zeromerma-order-policy-intention:",
  eventName: "zeromerma-order-policy-intention",
  contextFields: ["userId", "branchId"],
  scope: () => ORDER_POLICY_SCOPE,
  send: (context, payload, key) => requestJson({
    path: `/v1/admin/orders/commitment-policies/${encodeURIComponent(context.branchId)}`,
    method: "POST", body: payload, headers: { "Idempotency-Key": key },
  }),
  recover: metadata => requestJson({
    path: `/v1/admin/orders/commitment-policies/${encodeURIComponent(metadata.branchId)}/confirmations/${encodeURIComponent(metadata.key)}`,
  }),
});

export function readOrderPolicy(branchId: string) {
  return requestJson<OrderPolicyView | null>({ path: `/v1/admin/orders/commitment-policies/${encodeURIComponent(branchId)}` });
}

useBackofficeAuthStore.subscribe((state, previous) => {
  if (state.generation !== previous.generation || state.user?.id !== previous.user?.id ||
    state.session?.id !== previous.session?.id || state.user?.authorization_version !== previous.user?.authorization_version) {
    orderPolicyIntentions.forgetBodies();
  }
});
