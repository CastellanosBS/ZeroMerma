import { useBackofficeAuthStore } from "../../auth/backoffice-auth-store";
import {
  createCommandIntentionCoordinator,
  type CommandIntentionMetadata,
} from "@zeromerma/api-client";
import {
  createAdminTransfer,
  updateAdminTransfer,
  dispatchAdminTransfer,
  receiveAdminTransfer,
  cancelAdminTransfer,
  recoverAdminTransferCommand,
  type TransferCommandResultView,
  type TransferCommandCode,
} from "./api";
import type {
  AdminTransferCreatePayload,
  AdminTransferUpdatePayload,
  AdminTransferReceivePayload,
} from "./types";
export interface TransferIntentionContext {
  userId: string;
  branchId: string;
  transferId: string | null;
  commandCode: TransferCommandCode;
}
export type TransferIntentionMetadata = CommandIntentionMetadata<TransferIntentionContext>;
export type TransferIntentionPayload =
  | { commandCode: "create"; body: AdminTransferCreatePayload }
  | { commandCode: "update"; body: AdminTransferUpdatePayload }
  | { commandCode: "receive"; body: AdminTransferReceivePayload }
  | { commandCode: "dispatch"; notes: string | null | undefined }
  | { commandCode: "cancel"; reason: string | null | undefined };
export const TRANSFER_INTENTION_SCOPE = "transfers";
export const transferIntentions = createCommandIntentionCoordinator<
  TransferIntentionContext,
  TransferIntentionPayload,
  TransferCommandResultView
>({
  storagePrefix: "zeromerma-admin-transfer-intention:",
  eventName: "zeromerma-admin-transfer-intention",
  contextFields: ["userId", "branchId", "transferId", "commandCode"],
  nullableFields: ["transferId"],
  scope: () => TRANSFER_INTENTION_SCOPE,
  validateContext: (context) =>
    ["create", "update", "dispatch", "receive", "cancel"].includes(context.commandCode) &&
    (context.commandCode === "create") === (context.transferId === null),
  send: (context, payload, key) => {
    if (payload.commandCode !== context.commandCode) throw new Error("El comando cambió.");
    if (payload.commandCode === "create") return createAdminTransfer(payload.body, key);
    if (!context.transferId) throw new Error("Se requiere el envío original.");
    if (payload.commandCode === "update")
      return updateAdminTransfer(context.transferId, payload.body, key);
    if (payload.commandCode === "receive")
      return receiveAdminTransfer(context.transferId, payload.body, key);
    if (payload.commandCode === "dispatch")
      return dispatchAdminTransfer(context.transferId, payload.notes, key);
    return cancelAdminTransfer(context.transferId, payload.reason, key);
  },
  recover: async (metadata) => {
    const result = await recoverAdminTransferCommand(
      metadata.commandCode,
      metadata.key,
      metadata.branchId,
    );
    if (metadata.transferId && result.id !== metadata.transferId)
      throw new Error("El resultado pertenece a otro envío. Conserva la referencia.");
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
    transferIntentions.forgetBodies();
});
