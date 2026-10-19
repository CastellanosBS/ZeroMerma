import { ApiError, createCommandIntentionCoordinator, type paths } from "@zeromerma/api-client";
import { useBackofficeAuthStore } from "../../auth/backoffice-auth-store";
import {
  cancelAdminPurchase,
  confirmAdminPurchase,
  createAdminDirectEntry,
  createAdminPurchase,
  receiveAdminPurchase,
  recoverAdminPurchaseCommand,
  updateAdminPurchase,
  type PurchaseCommandResultView,
  type PurchaseUpdatePayload,
} from "./api";
import type {
  AdminDirectEntryPayload,
  AdminPurchaseCancelPayload,
  AdminPurchasePayload,
  AdminPurchaseReceiptPayload,
} from "./types";

export type PurchaseCommandCode =
  paths["/v1/admin/purchases/commands/{command_code}/{idempotency_key}"]["get"]["parameters"]["path"]["command_code"];
export interface PurchaseIntentionContext {
  userId: string;
  branchId: string;
  purchaseId: string | null;
  commandCode: PurchaseCommandCode;
}
export type PurchaseIntentionPayload =
  | { commandCode: "create"; body: AdminPurchasePayload }
  | { commandCode: "direct-entry"; body: AdminDirectEntryPayload }
  | { commandCode: "update"; body: PurchaseUpdatePayload }
  | { commandCode: "receive"; body: AdminPurchaseReceiptPayload }
  | { commandCode: "cancel"; body: AdminPurchaseCancelPayload }
  | { commandCode: "confirm" };

export const PURCHASE_INTENTION_SCOPE = "purchases";
export const purchaseIntentions = createCommandIntentionCoordinator<
  PurchaseIntentionContext,
  PurchaseIntentionPayload,
  PurchaseCommandResultView
>({
  storagePrefix: "zeromerma-admin-purchase-intention:",
  eventName: "zeromerma-admin-purchase-intention",
  contextFields: ["userId", "branchId", "purchaseId", "commandCode"],
  nullableFields: ["purchaseId"],
  scope: () => PURCHASE_INTENTION_SCOPE,
  validateContext: (context) =>
    ["create", "direct-entry", "update", "confirm", "receive", "cancel"].includes(
      context.commandCode,
    ) && ["create", "direct-entry"].includes(context.commandCode) === (context.purchaseId === null),
  send: (context, payload, key) => {
    if (context.commandCode !== payload.commandCode)
      throw new Error("El comando de compra cambió.");
    if (payload.commandCode === "create") return createAdminPurchase(payload.body, key);
    if (payload.commandCode === "direct-entry") return createAdminDirectEntry(payload.body, key);
    if (!context.purchaseId) throw new Error("Se requiere la compra original.");
    if (payload.commandCode === "update")
      return updateAdminPurchase(context.purchaseId, payload.body, key);
    if (payload.commandCode === "receive")
      return receiveAdminPurchase(context.purchaseId, payload.body, key);
    if (payload.commandCode === "cancel")
      return cancelAdminPurchase(context.purchaseId, payload.body, key);
    return confirmAdminPurchase(context.purchaseId, key);
  },
  recover: async (metadata) => {
    const result = await recoverAdminPurchaseCommand(
      metadata.commandCode,
      metadata.key,
      metadata.branchId,
    );
    if (metadata.purchaseId && result.id !== metadata.purchaseId)
      throw new Error(
        "El resultado pertenece a otra compra. Conserva la referencia y solicita revisión.",
      );
    return result;
  },
  isRecoveredRejection: (_metadata, error) =>
    error instanceof ApiError &&
    error.idempotencyReplayed === true &&
    error.error?.code === "PURCHASE_COMMAND_REJECTED",
});

useBackofficeAuthStore.subscribe((state, previous) => {
  if (
    state.generation !== previous.generation ||
    state.user?.id !== previous.user?.id ||
    state.session?.id !== previous.session?.id ||
    state.user?.authorization_version !== previous.user?.authorization_version
  )
    purchaseIntentions.forgetBodies();
});
