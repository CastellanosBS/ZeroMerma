import {
  ApiError,
  createCommandIntentionCoordinator,
  type CommandIntentionMetadata,
  type components,
} from "@zeromerma/api-client";
import { requestJson } from "../../lib/http";
import { usePosAuthStore } from "../auth/auth-store";

export type AttributionRequest = components["schemas"]["ClassAttributionRequest"];
export type AttributionResult = components["schemas"]["ClassAttributionResult"];
export interface AttributionContext {
  userId: string;
  branchId: string;
  workstationId: string;
  workstationCode: string;
  cashSessionId: string;
  saleId: string;
}
export type AttributionMetadata = CommandIntentionMetadata<AttributionContext>;
export const attributionIntentions = createCommandIntentionCoordinator<
  AttributionContext,
  AttributionRequest,
  AttributionResult
>({
  storagePrefix: "zeromerma-attribution-intention:",
  eventName: "zeromerma-attribution-intention",
  contextFields: [
    "userId",
    "branchId",
    "workstationId",
    "workstationCode",
    "cashSessionId",
    "saleId",
  ],
  scope: (context) => context.workstationId,
  send: (context, body, key) => {
    if (
      body.workstation_code !== context.workstationCode ||
      body.cash_session_id !== context.cashSessionId
    )
      throw new Error("La atribucion cambio de caja o turno. Conserva la referencia original.");
    return requestJson<AttributionResult>({
      method: "POST",
      path: `/v1/sales/${encodeURIComponent(context.saleId)}/attribute-inventory`,
      body,
      headers: { "Idempotency-Key": key },
    });
  },
  recover: async (metadata) => {
    const params = new URLSearchParams({
      workstation_code: metadata.workstationCode,
      cash_session_id: metadata.cashSessionId,
    });
    const result = await requestJson<AttributionResult>({
      path: `/v1/sales/${encodeURIComponent(metadata.saleId)}/inventory-attributions/${metadata.key}?${params}`,
    });
    if (result.sale_id !== metadata.saleId)
      throw new ApiError(409, "La atribucion pertenece a otra venta. Conserva la referencia.", {
        code: "IDEMPOTENCY_KEY_REUSED",
        message: "La atribucion pertenece a otra venta. Conserva la referencia.",
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
    attributionIntentions.forgetBodies();
});
