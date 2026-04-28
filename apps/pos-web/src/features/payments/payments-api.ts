import type {
  CreateOperationalPaymentRequest,
  OperationalPaymentDetailResponse,
  PaymentsBootstrapResponse,
  PaymentsListResponse,
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

export function getPaymentsBootstrap(
  accessToken: string,
  workstationCode: string,
): Promise<PaymentsBootstrapResponse> {
  return requestJson<PaymentsBootstrapResponse>({
    accessToken,
    path: `/v1/payments/bootstrap?workstation_code=${encodeURIComponent(workstationCode)}`,
  });
}

export function listPayments({
  accessToken,
  category,
  createdByUserId,
  paymentMethod,
  query,
  scope,
  workstationCode,
}: {
  accessToken: string;
  category?: string;
  createdByUserId?: string;
  paymentMethod?: string;
  query?: string;
  scope?: string;
  workstationCode: string;
}): Promise<PaymentsListResponse> {
  return requestJson<PaymentsListResponse>({
    accessToken,
    path: `/v1/payments${buildQueryString({
      workstation_code: workstationCode,
      scope,
      created_by_user_id: createdByUserId,
      query,
      category,
      payment_method: paymentMethod,
    })}`,
  });
}

export function getPaymentDetail({
  accessToken,
  paymentId,
  workstationCode,
}: {
  accessToken: string;
  paymentId: string;
  workstationCode: string;
}): Promise<OperationalPaymentDetailResponse> {
  return requestJson<OperationalPaymentDetailResponse>({
    accessToken,
    path: `/v1/payments/${encodeURIComponent(paymentId)}?workstation_code=${encodeURIComponent(workstationCode)}`,
  });
}

export function createPayment({
  accessToken,
  payload,
  requestId,
}: {
  accessToken: string;
  payload: CreateOperationalPaymentRequest;
  requestId: string;
}): Promise<OperationalPaymentDetailResponse> {
  return requestJson<OperationalPaymentDetailResponse>({
    accessToken,
    body: payload,
    method: "POST",
    path: "/v1/payments",
    headers: {
      "X-Request-ID": requestId,
    },
  });
}
