import { usePosAuthStore } from "../auth/auth-store";
import {
  ApiError,
  createCommandIntentionCoordinator,
  type CommandIntentionMetadata,
} from "@zeromerma/api-client";
import type {
  PosTransferCommandCode,
  TransferCommandResultView,
  TransferDispatchCommitRequest,
  TransferReceiveRequest,
} from "../../lib/api-contracts";
import { commitTransferDispatch, receiveTransfer, recoverTransferCommand } from "./transfers-api";
export interface TransferIntentionContext {
  userId: string;
  branchId: string;
  workstationId: string;
  workstationCode: string;
  cashSessionId: string;
  commandCode: PosTransferCommandCode;
  transferId: string | null;
}
export type TransferIntentionMetadata = CommandIntentionMetadata<TransferIntentionContext>;
export const transferIntentions = createCommandIntentionCoordinator<
  TransferIntentionContext,
  TransferDispatchCommitRequest | TransferReceiveRequest,
  TransferCommandResultView
>({
  storagePrefix: "zeromerma-transfer-intention:",
  eventName: "zeromerma-transfer-intention",
  contextFields: [
    "userId",
    "branchId",
    "workstationId",
    "workstationCode",
    "cashSessionId",
    "commandCode",
    "transferId",
  ],
  nullableFields: ["transferId"],
  scope: (context) => context.workstationId,
  validateContext: (context) =>
    context.commandCode === "dispatch"
      ? context.transferId === null
      : context.commandCode === "receive" && context.transferId !== null,
  send: (context, payload, key) =>
    context.commandCode === "dispatch"
      ? commitTransferDispatch(payload as TransferDispatchCommitRequest, key)
      : receiveTransfer(context.transferId!, payload as TransferReceiveRequest, key),
  recover: async (metadata) => {
    const result = await recoverTransferCommand(
      metadata.commandCode,
      metadata.key,
      metadata.workstationCode,
      metadata.cashSessionId,
    );
    if (metadata.transferId !== null && result.id !== metadata.transferId)
      throw new ApiError(409, "La referencia pertenece a otro envío.", {
        code: "IDEMPOTENCY_KEY_REUSED",
        message: "La referencia pertenece a otro envío.",
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
    transferIntentions.forgetBodies();
});
