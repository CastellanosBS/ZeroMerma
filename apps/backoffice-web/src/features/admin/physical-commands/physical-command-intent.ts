import { useBackofficeAuthStore } from "../../auth/backoffice-auth-store";
import {
  ApiError,
  createCommandIntentionCoordinator,
  type components,
  type CommandIntentionMetadata,
} from "@zeromerma/api-client";
import { requestJson } from "../../../lib/api";
import { createAdminWaste } from "../waste/api";
import { createAdminInventoryAdjustment } from "../inventory/api";
import type { AdminWasteCreatePayload } from "../waste/types";
import type { AdminInventoryAdjustmentPayload } from "../inventory/types";
export interface PhysicalIntentionContext {
  userId: string;
  branchId: string;
  commandCode: "waste" | "adjustment";
}
export type PhysicalIntentionMetadata = CommandIntentionMetadata<PhysicalIntentionContext>;
export type PhysicalIntentionPayload =
  | { commandCode: "waste"; body: AdminWasteCreatePayload }
  | { commandCode: "adjustment"; body: AdminInventoryAdjustmentPayload };
export type PhysicalCommandResult =
  | components["schemas"]["OperationCommitResultView"]
  | components["schemas"]["AdminInventoryAdjustmentResultView"];
export const PHYSICAL_INTENTION_SCOPE = "physical-commands";
export const physicalIntentions = createCommandIntentionCoordinator<
  PhysicalIntentionContext,
  PhysicalIntentionPayload,
  PhysicalCommandResult
>({
  storagePrefix: "zeromerma-admin-physical-intention:",
  eventName: "zeromerma-admin-physical-intention",
  contextFields: ["userId", "branchId", "commandCode"],
  scope: () => PHYSICAL_INTENTION_SCOPE,
  validateContext: (context) =>
    context.commandCode === "waste" || context.commandCode === "adjustment",
  send: (context, payload, key) => {
    if (context.commandCode !== payload.commandCode || context.branchId !== payload.body.branchId)
      throw new Error("El contexto del movimiento cambió.");
    return payload.commandCode === "waste"
      ? createAdminWaste(payload.body, key)
      : createAdminInventoryAdjustment(payload.body, key);
  },
  recover: async (metadata) => {
    const path = metadata.commandCode === "waste" ? "waste" : "inventory/adjustments";
    const result = await requestJson<PhysicalCommandResult>({
      path: `/v1/admin/${path}/confirmations/${encodeURIComponent(metadata.key)}?branch_id=${encodeURIComponent(metadata.branchId)}`,
    });
    if (result.branch_id !== metadata.branchId)
      throw new ApiError(409, "El resultado pertenece a otra sucursal.", {
        code: "IDEMPOTENCY_KEY_REUSED",
        message: "El resultado pertenece a otra sucursal.",
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
    physicalIntentions.forgetBodies();
});
