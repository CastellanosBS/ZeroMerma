import {
  ApiError,
  createCommandIntentionCoordinator,
  type CommandIntentionMetadata,
} from "@zeromerma/api-client";
import {
  recoverProductionCommand,
  sendProductionCommand,
  type ProductionCommandCode,
  type ProductionCommandPayload,
  type ProductionCommandResultView,
} from "./api";
import { useBackofficeAuthStore } from "../../auth/backoffice-auth-store";

export interface ProductionIntentionContext {
  userId: string;
  branchId: string;
  productionId: string | null;
  commandCode: ProductionCommandCode;
}
export type ProductionIntentionMetadata = CommandIntentionMetadata<ProductionIntentionContext>;
export const PRODUCTION_INTENTION_SCOPE = "production";
export const productionIntentions = createCommandIntentionCoordinator<
  ProductionIntentionContext,
  ProductionCommandPayload,
  ProductionCommandResultView
>({
  storagePrefix: "zeromerma-production-intention:",
  eventName: "zeromerma-production-intention",
  contextFields: ["userId", "branchId", "productionId", "commandCode"],
  nullableFields: ["productionId"],
  scope: () => PRODUCTION_INTENTION_SCOPE,
  validateContext: (context) =>
    ["create", "update", "start", "complete", "cancel"].includes(context.commandCode) &&
    (context.commandCode === "create"
      ? context.productionId === null
      : context.productionId !== null),
  send: (context, payload, key) =>
    sendProductionCommand(context.commandCode, context.productionId, payload, key),
  isRecoveredRejection: (_metadata, error) =>
    error instanceof ApiError &&
    error.idempotencyReplayed &&
    error.statusCode === 409 &&
    error.error?.code === "PRODUCTION_CONFLICT",
  recover: async (metadata) => {
    const result = await recoverProductionCommand(
      metadata.commandCode,
      metadata.key,
      metadata.branchId,
    );
    if (
      result.branch_id !== metadata.branchId ||
      (metadata.productionId !== null && result.id !== metadata.productionId)
    )
      throw new ApiError(409, "La referencia pertenece a otro lote o sucursal.", {
        code: "IDEMPOTENCY_KEY_REUSED",
        message: "La referencia pertenece a otro lote o sucursal.",
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
    productionIntentions.forgetBodies();
});

export async function beginProductionCommand(
  context: ProductionIntentionContext,
  payload: ProductionCommandPayload,
  observedKey: string | null,
  options: {
    startNow: boolean;
    canContinue: () => boolean;
    onCreated: (result: ProductionCommandResultView) => void;
  },
): Promise<ProductionCommandResultView> {
  if (options.startNow && context.commandCode !== "create")
    throw new Error("Sólo la creación puede solicitar el inicio posterior.");
  const result = await productionIntentions.begin(context, payload, observedKey);
  if (!options.startNow) return result;
  // These are two intentions: losing either response must never repeat creation.
  options.onCreated(result);
  if (!options.canContinue()) return result;
  const created = productionIntentions.read(PRODUCTION_INTENTION_SCOPE);
  return productionIntentions.begin(
    { ...context, commandCode: "start", productionId: result.id },
    {},
    created?.key ?? null,
  );
}
