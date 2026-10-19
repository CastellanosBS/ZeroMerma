import { usePosAuthStore } from "../auth/auth-store";
import {
  ApiError,
  createCommandIntentionCoordinator,
  type CommandIntentionMetadata,
} from "@zeromerma/api-client";
import type {
  CancelCustomerOrderRequest,
  CreateCustomerOrderRequest,
  DeliverCustomerOrderRequest,
  OrderActionRequest,
} from "../../lib/api-contracts";
import {
  cancelOrder,
  createOrder,
  deliverOrder,
  markOrderReady,
  recoverOrderCommand,
  type OrderCommandCode,
  type OrderCommandResultView,
} from "./orders-api";

export interface OrderIntentionContext {
  userId: string;
  branchId: string;
  workstationId: string;
  workstationCode: string;
  cashSessionId: string;
  commandCode: OrderCommandCode;
  orderId: string | null;
}
export type OrderIntentionMetadata = CommandIntentionMetadata<OrderIntentionContext>;
export type OrderCommandPayload =
  | CreateCustomerOrderRequest
  | OrderActionRequest
  | DeliverCustomerOrderRequest
  | CancelCustomerOrderRequest;
export const ORDER_INTENTION_STORAGE_PREFIX = "zeromerma-order-intention:";
export const orderIntentions = createCommandIntentionCoordinator<
  OrderIntentionContext,
  OrderCommandPayload,
  OrderCommandResultView
>({
  storagePrefix: ORDER_INTENTION_STORAGE_PREFIX,
  eventName: "zeromerma-order-intention",
  contextFields: [
    "userId",
    "branchId",
    "workstationId",
    "workstationCode",
    "cashSessionId",
    "commandCode",
    "orderId",
  ],
  nullableFields: ["orderId"],
  scope: (context) => context.workstationId,
  validateContext: (context) =>
    ["create", "mark-ready", "deliver", "cancel"].includes(context.commandCode) &&
    (context.commandCode === "create" ? context.orderId === null : context.orderId !== null),
  send: (context, payload, idempotencyKey) => {
    const requestId = `orders-${context.commandCode}-${crypto.randomUUID()}`;
    if (context.commandCode === "create")
      return createOrder({
        payload: payload as CreateCustomerOrderRequest,
        requestId,
        idempotencyKey,
      });
    const args = { orderId: context.orderId!, payload, requestId, idempotencyKey };
    if (context.commandCode === "mark-ready") return markOrderReady(args);
    if (context.commandCode === "deliver") return deliverOrder(args);
    return cancelOrder({ ...args, payload: payload as CancelCustomerOrderRequest });
  },
  recover: async (metadata) => {
    const result = await recoverOrderCommand(
      metadata.commandCode,
      metadata.key,
      metadata.workstationCode,
      metadata.cashSessionId,
    );
    if (metadata.orderId !== null && result.id !== metadata.orderId)
      throw new ApiError(409, "La referencia pertenece a otro pedido.", {
        code: "IDEMPOTENCY_KEY_REUSED",
        message: "La referencia pertenece a otro pedido.",
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
    orderIntentions.forgetBodies();
});
