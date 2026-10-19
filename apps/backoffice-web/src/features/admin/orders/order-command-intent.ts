import { useBackofficeAuthStore } from "../../auth/backoffice-auth-store";
import {
  ApiError,
  createCommandIntentionCoordinator,
  type CommandIntentionMetadata,
  type paths,
} from "@zeromerma/api-client";
import {
  recoverAdminOrderCommand,
  sendAdminOrderCommand,
  type OrderCommandResultView,
} from "./api";

export type AdminOrderCommandCode =
  paths["/v1/admin/orders/commands/{command_code}/{idempotency_key}"]["get"]["parameters"]["path"]["command_code"];
export interface AdminOrderIntentionContext {
  userId: string;
  branchId: string;
  orderId: string;
  commandCode: AdminOrderCommandCode;
}
export type AdminOrderIntentionMetadata = CommandIntentionMetadata<AdminOrderIntentionContext>;
export const ADMIN_ORDER_INTENTION_SCOPE = "orders";
export const adminOrderIntentions = createCommandIntentionCoordinator<
  AdminOrderIntentionContext,
  Record<string, never>,
  OrderCommandResultView
>({
  storagePrefix: "zeromerma-admin-order-intention:",
  eventName: "zeromerma-admin-order-intention",
  contextFields: ["userId", "branchId", "orderId", "commandCode"],
  scope: () => ADMIN_ORDER_INTENTION_SCOPE,
  validateContext: (context) => ["mark-ready", "deliver", "cancel"].includes(context.commandCode),
  send: (context, _payload, key) =>
    sendAdminOrderCommand(context.commandCode, context.orderId, key),
  recover: async (metadata) => {
    const result = await recoverAdminOrderCommand(
      metadata.commandCode,
      metadata.key,
      metadata.branchId,
    );
    if (result.id !== metadata.orderId)
      throw new ApiError(409, "La referencia pertenece a otro pedido.", {
        code: "IDEMPOTENCY_KEY_REUSED",
        message: "La referencia pertenece a otro pedido.",
        details: null,
        field_errors: null,
        request_id: null,
      });
    return result;
  },
});

useBackofficeAuthStore.subscribe((state, previous) => {
  if (
    state.generation !== previous.generation ||
    state.user?.id !== previous.user?.id ||
    state.session?.id !== previous.session?.id ||
    state.user?.authorization_version !== previous.user?.authorization_version
  )
    adminOrderIntentions.forgetBodies();
});
