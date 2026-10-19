import {
  ApiError,
  createCommandIntentionCoordinator,
  type CommandIntentionMetadata,
  type components,
} from "@zeromerma/api-client";
import { requestJson } from "../../../lib/api";
import { useBackofficeAuthStore } from "../../auth/backoffice-auth-store";

export type InventoryDispositionRequest = components["schemas"]["InventoryDispositionRequest"];
export type InventoryDispositionResult = components["schemas"]["InventoryDispositionResult"];
export interface DispositionContext {
  userId: string;
  branchId: string;
  productId: string;
  kind: InventoryDispositionRequest["kind"];
  returnAllocationId: string | null;
  lotId: string | null;
}
export type DispositionMetadata = CommandIntentionMetadata<DispositionContext>;
export const DISPOSITION_SCOPE = "inventory-dispositions";
export const dispositionIntentions = createCommandIntentionCoordinator<
  DispositionContext,
  InventoryDispositionRequest,
  InventoryDispositionResult
>({
  storagePrefix: "zeromerma-inventory-disposition-intention:",
  eventName: "zeromerma-inventory-disposition-intention",
  contextFields: ["userId", "branchId", "productId", "kind", "returnAllocationId", "lotId"],
  nullableFields: ["returnAllocationId", "lotId"],
  scope: () => DISPOSITION_SCOPE,
  validateContext: (context) =>
    ["RETURN_CORRECTION", "QUARANTINE_RELEASE"].includes(context.kind) &&
    (context.kind === "RETURN_CORRECTION") === (context.returnAllocationId !== null),
  send: (context, body, key) => {
    if (
      body.branch_id !== context.branchId ||
      body.product_id !== context.productId ||
      body.kind !== context.kind ||
      (body.return_allocation_id ?? null) !== context.returnAllocationId ||
      (body.lot_id ?? null) !== context.lotId
    )
      throw new Error("La disposicion cambio de contexto. Conserva la referencia original.");
    return requestJson<InventoryDispositionResult>({
      method: "POST",
      path: "/v1/admin/inventory-dispositions",
      body,
      headers: { "Idempotency-Key": key },
    });
  },
  recover: async (metadata) => {
    const params = new URLSearchParams({ branch_id: metadata.branchId, kind: metadata.kind });
    const result = await requestJson<InventoryDispositionResult>({
      path: `/v1/admin/inventory-dispositions/confirmations/${metadata.key}?${params}`,
    });
    if (
      result.branch_id !== metadata.branchId ||
      result.product_id !== metadata.productId ||
      result.kind !== metadata.kind ||
      result.return_allocation_id !== metadata.returnAllocationId ||
      (metadata.kind === "QUARANTINE_RELEASE" && result.lot_id !== metadata.lotId)
    )
      throw new ApiError(
        409,
        "La confirmacion pertenece a otra disposicion. Conserva la referencia.",
        {
          code: "IDEMPOTENCY_KEY_REUSED",
          message: "La confirmacion pertenece a otra disposicion. Conserva la referencia.",
          details: null,
          field_errors: null,
          request_id: null,
        },
      );
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
    dispositionIntentions.forgetBodies();
});
