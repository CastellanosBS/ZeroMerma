import type { OperationalPaymentCommitResultView } from "../../lib/api-contracts";
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

export function getPaymentsBootstrap(workstationCode: string): Promise<PaymentsBootstrapResponse> {
  return requestJson<PaymentsBootstrapResponse>({
    path: `/v1/payments/bootstrap?workstation_code=${encodeURIComponent(workstationCode)}`,
  });
}

export function listPayments({
  category,
  createdByUserId,
  paymentMethod,
  query,
  scope,
  workstationCode,
}: {
  category?: string;
  createdByUserId?: string;
  paymentMethod?: string;
  query?: string;
  scope?: string;
  workstationCode: string;
}): Promise<PaymentsListResponse> {
  return requestJson<PaymentsListResponse>({
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
  paymentId,
  workstationCode,
}: {
  paymentId: string;
  workstationCode: string;
}): Promise<OperationalPaymentDetailResponse> {
  return requestJson<OperationalPaymentDetailResponse>({
    path: `/v1/payments/${encodeURIComponent(paymentId)}?workstation_code=${encodeURIComponent(workstationCode)}`,
  });
}

export function createPayment({
  idempotencyKey,
  payload,
  requestId,
}: {
  idempotencyKey: string;
  payload: CreateOperationalPaymentRequest;
  requestId: string;
}): Promise<OperationalPaymentCommitResultView> {
  return requestJson<OperationalPaymentCommitResultView>({
    body: payload,
    method: "POST",
    path: "/v1/payments",
    headers: {
      "X-Request-ID": requestId,
      "Idempotency-Key": idempotencyKey,
    },
  });
}
