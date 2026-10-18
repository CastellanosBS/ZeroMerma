import type { OperationalDiscountCommitResultView } from "../../lib/api-contracts";
import type {
  CreateOperationalDiscountRequest,
  DiscountsBootstrapResponse,
  DiscountsListResponse,
  OperationalDiscountDetailResponse,
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

export function getDiscountsBootstrap(
  workstationCode: string,
): Promise<DiscountsBootstrapResponse> {
  return requestJson<DiscountsBootstrapResponse>({
    path: `/v1/discounts/bootstrap?workstation_code=${encodeURIComponent(workstationCode)}`,
  });
}

export function listDiscounts({
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
}): Promise<DiscountsListResponse> {
  return requestJson<DiscountsListResponse>({
    path: `/v1/discounts${buildQueryString({
      workstation_code: workstationCode,
      scope,
      created_by_user_id: createdByUserId,
      query,
      category,
      payment_method: paymentMethod,
    })}`,
  });
}

export function getDiscountDetail({
  discountId,
  workstationCode,
}: {
  discountId: string;
  workstationCode: string;
}): Promise<OperationalDiscountDetailResponse> {
  return requestJson<OperationalDiscountDetailResponse>({
    path: `/v1/discounts/${encodeURIComponent(discountId)}?workstation_code=${encodeURIComponent(workstationCode)}`,
  });
}

export function createDiscount({
  idempotencyKey,
  payload,
  requestId,
}: {
  idempotencyKey: string;
  payload: CreateOperationalDiscountRequest;
  requestId: string;
}): Promise<OperationalDiscountCommitResultView> {
  return requestJson<OperationalDiscountCommitResultView>({
    body: payload,
    method: "POST",
    path: "/v1/discounts",
    headers: {
      "X-Request-ID": requestId,
      "Idempotency-Key": idempotencyKey,
    },
  });
}
