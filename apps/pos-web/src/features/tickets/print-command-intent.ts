import {
  createCommandIntentionCoordinator,
  type CommandIntentionMetadata,
  type components,
} from "@zeromerma/api-client";

import { requestJson } from "../../lib/http";
import { usePosAuthStore } from "../auth/auth-store";

export interface PrintContext {
  userId: string;
  workstationId: string;
  workstationCode: string;
  sourceKind: components["schemas"]["OperationalReceiptView"]["source_kind"];
  sourceId: string;
}
export type HardwareAcknowledgement = components["schemas"]["HardwareCommandAcknowledgement"];
export type PrintAcknowledgement = components["schemas"]["ReceiptPrintAcknowledgement"];
const fields = ["userId", "workstationId", "workstationCode", "sourceKind", "sourceId"] as const;
export const printScope = (context: PrintContext) => `${context.workstationId}:${context.sourceKind}:${context.sourceId}`;

export async function recoverHardwareCommand(metadata: CommandIntentionMetadata<PrintContext>) {
  const result = await requestJson<HardwareAcknowledgement>({
    path: `/v1/hardware/commands/by-key/${metadata.key}?workstation_code=${encodeURIComponent(metadata.workstationCode)}`,
  });
  if (result.grant.command.workstation_id !== metadata.workstationId
    || result.grant.command.receipt?.source_kind !== metadata.sourceKind
    || result.grant.command.receipt?.source_id !== metadata.sourceId) {
    throw new Error("La intención corresponde a otro comprobante o caja.");
  }
  return result;
}

export const hardwareIntentions = createCommandIntentionCoordinator<PrintContext,
  components["schemas"]["HardwareCommandRequest"], HardwareAcknowledgement>({
  storagePrefix: "zeromerma-hardware-intention:", eventName: "zeromerma-hardware-intention",
  contextFields: fields, scope: printScope,
  send: (context, body, key) => {
    if (body.workstation_code !== context.workstationCode || body.receipt_source_kind !== context.sourceKind
      || body.receipt_source_id !== context.sourceId || body.kind !== "PRINT") {
      throw new Error("La impresión cambió de documento o caja.");
    }
    return requestJson<HardwareAcknowledgement>({ method: "POST", path: "/v1/hardware/commands", body,
      headers: { "Idempotency-Key": key } });
  },
  recover: recoverHardwareCommand,
});

export const browserPrintIntentions = createCommandIntentionCoordinator<PrintContext,
  components["schemas"]["ReceiptPrintRequest"], PrintAcknowledgement>({
  storagePrefix: "zeromerma-browser-print-intention:", eventName: "zeromerma-browser-print-intention",
  contextFields: fields, scope: printScope,
  send: (context, body, key) => {
    if (body.workstation_code !== context.workstationCode) throw new Error("La caja cambió.");
    return requestJson<PrintAcknowledgement>({ method: "POST",
      path: `/v1/tickets/receipts/${context.sourceKind}/${context.sourceId}/print-request`, body,
      headers: { "Idempotency-Key": key } });
  },
  recover: (metadata) => requestJson<PrintAcknowledgement>({
    path: `/v1/tickets/receipts/${metadata.sourceKind}/${metadata.sourceId}/print-requests/${metadata.key}?workstation_code=${encodeURIComponent(metadata.workstationCode)}`,
  }),
});

usePosAuthStore.subscribe((state, previous) => {
  if (state.generation !== previous.generation || state.user?.id !== previous.user?.id
    || state.session?.id !== previous.session?.id
    || state.user?.authorization_version !== previous.user?.authorization_version) {
    hardwareIntentions.forgetBodies();
    browserPrintIntentions.forgetBodies();
  }
});
