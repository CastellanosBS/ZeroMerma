import { usePosAuthStore } from "../auth/auth-store";
import {
  ApiError,
  createCommandIntentionCoordinator,
  type CommandIntentionMetadata,
} from "@zeromerma/api-client";
import type {
  CorrectionCommitRequest,
  CorrectionCommitResultView,
  CounterTransferCommitRequest,
  WasteCommitRequest,
  OperationCommitResultView,
} from "../../lib/api-contracts";
import { requestJson } from "../../lib/http";
import { commitCorrection } from "../corrections/corrections-api";
import { commitCounterTransfer, commitWasteRecord } from "../operations/operations-api";
export type OperationCommandCode = "correction" | "counter-transfer" | "waste";
export interface OperationIntentionContext {
  userId: string;
  branchId: string;
  workstationId: string;
  workstationCode: string;
  cashSessionId: string;
  commandCode: OperationCommandCode;
  targetDocumentId: string | null;
}
export type OperationIntentionMetadata = CommandIntentionMetadata<OperationIntentionContext>;
export type OperationCommandPayload =
  | { commandCode: "correction"; body: CorrectionCommitRequest }
  | { commandCode: "counter-transfer"; body: CounterTransferCommitRequest }
  | { commandCode: "waste"; body: WasteCommitRequest };
export type OperationCommandResult = CorrectionCommitResultView | OperationCommitResultView;
const paths = {
  correction: "corrections",
  "counter-transfer": "operations/counter-transfer",
  waste: "operations/waste",
} as const;
export const operationIntentions = createCommandIntentionCoordinator<
  OperationIntentionContext,
  OperationCommandPayload,
  OperationCommandResult
>({
  storagePrefix: "zeromerma-operation-intention:",
  eventName: "zeromerma-operation-intention",
  contextFields: [
    "userId",
    "branchId",
    "workstationId",
    "workstationCode",
    "cashSessionId",
    "commandCode",
    "targetDocumentId",
  ],
  nullableFields: ["targetDocumentId"],
  scope: (context) => context.workstationId,
  validateContext: (context) =>
    Object.hasOwn(paths, context.commandCode) &&
    (context.commandCode === "correction") === (context.targetDocumentId !== null),
  send: (context, payload, key) => {
    if (context.commandCode !== payload.commandCode)
      throw new Error("El movimiento cambió. Conserva la referencia original.");
    if (payload.commandCode === "correction")
      return commitCorrection({
        payload: payload.body,
        idempotencyKey: key,
        requestId: `correction-${crypto.randomUUID()}`,
      });
    if (payload.commandCode === "counter-transfer") return commitCounterTransfer(payload.body, key);
    return commitWasteRecord(payload.body, key);
  },
  recover: async (metadata) => {
    const query = new URLSearchParams({
      workstation_code: metadata.workstationCode,
      cash_session_id: metadata.cashSessionId,
    });
    const result = await requestJson<OperationCommandResult>({
      path: `/v1/${paths[metadata.commandCode]}/confirmations/${encodeURIComponent(metadata.key)}?${query}`,
    });
    if (
      result.branch_id !== metadata.branchId ||
      result.workstation_id !== metadata.workstationId ||
      result.cash_session_id !== metadata.cashSessionId ||
      (metadata.targetDocumentId !== null &&
        (!("target_document_id" in result) ||
          result.target_document_id !== metadata.targetDocumentId))
    )
      throw new ApiError(409, "El resultado pertenece a otro movimiento.", {
        code: "IDEMPOTENCY_KEY_REUSED",
        message: "El resultado pertenece a otro movimiento.",
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
    operationIntentions.forgetBodies();
});
