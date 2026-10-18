import type { components, paths } from "@zeromerma/api-client";
export type OrderCommandResultView = components["schemas"]["OrderCommandResultView"];
export type OrderCommandCode =
  paths["/v1/orders/commands/{command_code}/{idempotency_key}"]["get"]["parameters"]["path"]["command_code"];
import type {
  CancelCustomerOrderRequest,
  CreateCustomerOrderRequest,
  CustomerOrderDetailResponse,
  DeliverCustomerOrderRequest,
  OrderActionRequest,
  OrdersBootstrapResponse,
  OrdersCatalogResponse,
  OrdersClassProductsResponse,
  OrdersListResponse,
} from "../../lib/api-contracts";
import { requestJson } from "../../lib/http";

function buildQueryString(params: Record<string, string | undefined>): string {
  const searchParams = new URLSearchParams();

  for (const [key, value] of Object.entries(params)) {
    if (value === undefined) {
      continue;
    }

    searchParams.set(key, value);
  }

  const serialized = searchParams.toString();
  return serialized.length > 0 ? `?${serialized}` : "";
}

export function getOrdersBootstrap(workstationCode: string): Promise<OrdersBootstrapResponse> {
  return requestJson<OrdersBootstrapResponse>({
    path: `/v1/orders/bootstrap?workstation_code=${encodeURIComponent(workstationCode)}`,
  });
}

export function listOrders({
  dateFrom,
  dateTo,
  query,
  status,
  workstationCode,
}: {
  dateFrom?: string;
  dateTo?: string;
  query?: string;
  status?: string;
  workstationCode: string;
}): Promise<OrdersListResponse> {
  return requestJson<OrdersListResponse>({
    path: `/v1/orders${buildQueryString({
      workstation_code: workstationCode,
      status,
      query,
      date_from: dateFrom,
      date_to: dateTo,
    })}`,
  });
}

export function getOrderDetail({
  orderId,
  workstationCode,
}: {
  orderId: string;
  workstationCode: string;
}): Promise<CustomerOrderDetailResponse> {
  return requestJson<CustomerOrderDetailResponse>({
    path: `/v1/orders/${encodeURIComponent(orderId)}?workstation_code=${encodeURIComponent(workstationCode)}`,
  });
}

export function getOrdersCatalog({
  query,
  workstationCode,
}: {
  query?: string;
  workstationCode: string;
}): Promise<OrdersCatalogResponse> {
  return requestJson<OrdersCatalogResponse>({
    path: `/v1/orders/catalog${buildQueryString({
      workstation_code: workstationCode,
      query,
    })}`,
  });
}

export function getOrdersClassProducts({
  classId,
  query,
  workstationCode,
}: {
  classId: string;
  query?: string;
  workstationCode: string;
}): Promise<OrdersClassProductsResponse> {
  return requestJson<OrdersClassProductsResponse>({
    path: `/v1/orders/classes/${encodeURIComponent(classId)}/products${buildQueryString({
      workstation_code: workstationCode,
      query,
    })}`,
  });
}

export function createOrder({
  payload,
  requestId,
  idempotencyKey,
}: {
  payload: CreateCustomerOrderRequest;
  requestId: string;
  idempotencyKey: string;
}): Promise<OrderCommandResultView> {
  return requestJson<OrderCommandResultView>({
    body: payload,
    method: "POST",
    path: "/v1/orders",
    headers: {
      "X-Request-ID": requestId,
      "Idempotency-Key": idempotencyKey,
    },
  });
}

export function markOrderReady({
  orderId,
  payload,
  requestId,
  idempotencyKey,
}: {
  orderId: string;
  payload: OrderActionRequest;
  requestId: string;
  idempotencyKey: string;
}): Promise<OrderCommandResultView> {
  return requestJson<OrderCommandResultView>({
    body: payload,
    method: "POST",
    path: `/v1/orders/${encodeURIComponent(orderId)}/mark-ready`,
    headers: {
      "X-Request-ID": requestId,
      "Idempotency-Key": idempotencyKey,
    },
  });
}

export function deliverOrder({
  orderId,
  payload,
  requestId,
  idempotencyKey,
}: {
  orderId: string;
  payload: DeliverCustomerOrderRequest;
  requestId: string;
  idempotencyKey: string;
}): Promise<OrderCommandResultView> {
  return requestJson<OrderCommandResultView>({
    body: payload,
    method: "POST",
    path: `/v1/orders/${encodeURIComponent(orderId)}/deliver`,
    headers: {
      "X-Request-ID": requestId,
      "Idempotency-Key": idempotencyKey,
    },
  });
}

export function cancelOrder({
  orderId,
  payload,
  requestId,
  idempotencyKey,
}: {
  orderId: string;
  payload: CancelCustomerOrderRequest;
  requestId: string;
  idempotencyKey: string;
}): Promise<OrderCommandResultView> {
  return requestJson<OrderCommandResultView>({
    body: payload,
    method: "POST",
    path: `/v1/orders/${encodeURIComponent(orderId)}/cancel`,
    headers: {
      "X-Request-ID": requestId,
      "Idempotency-Key": idempotencyKey,
    },
  });
}

export function recoverOrderCommand(
  commandCode: OrderCommandCode,
  key: string,
  workstationCode: string,
  cashSessionId: string,
): Promise<OrderCommandResultView> {
  return requestJson<OrderCommandResultView>({
    path: `/v1/orders/commands/${commandCode}/${encodeURIComponent(key)}${buildQueryString({ workstation_code: workstationCode, cash_session_id: cashSessionId })}`,
  });
}
