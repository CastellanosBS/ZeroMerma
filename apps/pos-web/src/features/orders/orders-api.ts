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

export function getOrdersBootstrap(
  accessToken: string,
  workstationCode: string,
): Promise<OrdersBootstrapResponse> {
  return requestJson<OrdersBootstrapResponse>({
    accessToken,
    path: `/v1/orders/bootstrap?workstation_code=${encodeURIComponent(workstationCode)}`,
  });
}

export function listOrders({
  accessToken,
  dateFrom,
  dateTo,
  query,
  status,
  workstationCode,
}: {
  accessToken: string;
  dateFrom?: string;
  dateTo?: string;
  query?: string;
  status?: string;
  workstationCode: string;
}): Promise<OrdersListResponse> {
  return requestJson<OrdersListResponse>({
    accessToken,
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
  accessToken,
  orderId,
  workstationCode,
}: {
  accessToken: string;
  orderId: string;
  workstationCode: string;
}): Promise<CustomerOrderDetailResponse> {
  return requestJson<CustomerOrderDetailResponse>({
    accessToken,
    path: `/v1/orders/${encodeURIComponent(orderId)}?workstation_code=${encodeURIComponent(workstationCode)}`,
  });
}

export function getOrdersCatalog({
  accessToken,
  query,
  workstationCode,
}: {
  accessToken: string;
  query?: string;
  workstationCode: string;
}): Promise<OrdersCatalogResponse> {
  return requestJson<OrdersCatalogResponse>({
    accessToken,
    path: `/v1/orders/catalog${buildQueryString({
      workstation_code: workstationCode,
      query,
    })}`,
  });
}

export function getOrdersClassProducts({
  accessToken,
  classId,
  query,
  workstationCode,
}: {
  accessToken: string;
  classId: string;
  query?: string;
  workstationCode: string;
}): Promise<OrdersClassProductsResponse> {
  return requestJson<OrdersClassProductsResponse>({
    accessToken,
    path: `/v1/orders/classes/${encodeURIComponent(classId)}/products${buildQueryString({
      workstation_code: workstationCode,
      query,
    })}`,
  });
}

export function createOrder({
  accessToken,
  payload,
  requestId,
}: {
  accessToken: string;
  payload: CreateCustomerOrderRequest;
  requestId: string;
}): Promise<CustomerOrderDetailResponse> {
  return requestJson<CustomerOrderDetailResponse>({
    accessToken,
    body: payload,
    method: "POST",
    path: "/v1/orders",
    headers: {
      "X-Request-ID": requestId,
    },
  });
}

export function markOrderReady({
  accessToken,
  orderId,
  payload,
  requestId,
}: {
  accessToken: string;
  orderId: string;
  payload: OrderActionRequest;
  requestId: string;
}): Promise<CustomerOrderDetailResponse> {
  return requestJson<CustomerOrderDetailResponse>({
    accessToken,
    body: payload,
    method: "POST",
    path: `/v1/orders/${encodeURIComponent(orderId)}/mark-ready`,
    headers: {
      "X-Request-ID": requestId,
    },
  });
}

export function deliverOrder({
  accessToken,
  orderId,
  payload,
  requestId,
}: {
  accessToken: string;
  orderId: string;
  payload: DeliverCustomerOrderRequest;
  requestId: string;
}): Promise<CustomerOrderDetailResponse> {
  return requestJson<CustomerOrderDetailResponse>({
    accessToken,
    body: payload,
    method: "POST",
    path: `/v1/orders/${encodeURIComponent(orderId)}/deliver`,
    headers: {
      "X-Request-ID": requestId,
    },
  });
}

export function cancelOrder({
  accessToken,
  orderId,
  payload,
  requestId,
}: {
  accessToken: string;
  orderId: string;
  payload: CancelCustomerOrderRequest;
  requestId: string;
}): Promise<CustomerOrderDetailResponse> {
  return requestJson<CustomerOrderDetailResponse>({
    accessToken,
    body: payload,
    method: "POST",
    path: `/v1/orders/${encodeURIComponent(orderId)}/cancel`,
    headers: {
      "X-Request-ID": requestId,
    },
  });
}
