import {
  createCommandIntentionCoordinator,
  isCommandIntentionPending,
  type CommandIntentionMetadata,
} from "@zeromerma/api-client";
import type { ConfirmSaleRequest, SaleConfirmationView } from "../../lib/api-contracts";
import { confirmPosSale, getSaleConfirmation } from "./pos-terminal-api";

export interface SaleIntentionContext {
  userId: string;
  branchId: string;
  workstationId: string;
  workstationCode: string;
  cashSessionId: string;
}
export type SaleIntentionMetadata = CommandIntentionMetadata<SaleIntentionContext>;
export const SALE_INTENTION_EVENT = "zeromerma-sale-intention";
export const SALE_INTENTION_STORAGE_PREFIX = "zeromerma-sale-intention:";
const coordinator = createCommandIntentionCoordinator<
  SaleIntentionContext,
  ConfirmSaleRequest,
  SaleConfirmationView
>({
  storagePrefix: SALE_INTENTION_STORAGE_PREFIX,
  eventName: SALE_INTENTION_EVENT,
  contextFields: ["userId", "branchId", "workstationId", "workstationCode", "cashSessionId"],
  scope: (context) => context.workstationId,
  send: (_context, payload, key) => confirmPosSale(payload, key),
  recover: (metadata) =>
    getSaleConfirmation(metadata.key, metadata.workstationCode, metadata.cashSessionId),
});
export const readSaleIntention = coordinator.read;
export const isSaleIntentionPending = isCommandIntentionPending;
export const hasSaleIntentionBody = coordinator.hasBody;
export const forgetSaleIntentionBodies = coordinator.forgetBodies;
export const beginSaleConfirmation = coordinator.begin;
export const retrySaleConfirmation = coordinator.retry;
export const recoverSaleConfirmation = coordinator.recover;
