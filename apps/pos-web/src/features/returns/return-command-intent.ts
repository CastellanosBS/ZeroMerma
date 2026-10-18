import {
  ApiError,
  createCommandIntentionCoordinator,
  type CommandIntentionMetadata,
} from "@zeromerma/api-client";
import type { ReturnCommitRequest, ReturnCommitResultView } from "../../lib/api-contracts";
import { commitSaleReturn, recoverSaleReturn } from "./returns-api";

export interface ReturnIntentionContext {
  userId: string;
  branchId: string;
  workstationId: string;
  workstationCode: string;
  cashSessionId: string;
  originalSaleId: string;
}
export type ReturnIntentionMetadata = CommandIntentionMetadata<ReturnIntentionContext>;
export const RETURN_INTENTION_STORAGE_PREFIX = "zeromerma-return-intention:";
export const returnIntentions = createCommandIntentionCoordinator<
  ReturnIntentionContext,
  ReturnCommitRequest,
  ReturnCommitResultView
>({
  storagePrefix: RETURN_INTENTION_STORAGE_PREFIX,
  eventName: "zeromerma-return-intention",
  contextFields: [
    "userId",
    "branchId",
    "workstationId",
    "workstationCode",
    "cashSessionId",
    "originalSaleId",
  ],
  scope: (context) => context.workstationId,
  send: (_context, payload, idempotencyKey) =>
    commitSaleReturn({ payload, idempotencyKey, requestId: `return-${crypto.randomUUID()}` }),
  recover: async (metadata) => {
    const result = await recoverSaleReturn(
      metadata.key,
      metadata.workstationCode,
      metadata.cashSessionId,
    );
    if (result.original_sale_id !== metadata.originalSaleId) {
      throw new ApiError(409, "La referencia pertenece a otra venta.", {
        code: "IDEMPOTENCY_KEY_REUSED",
        message: "La referencia pertenece a otra venta.",
        details: null,
        field_errors: null,
        request_id: null,
      });
    }
    return result;
  },
});
