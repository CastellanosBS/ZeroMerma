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
  accessToken: string,
  workstationCode: string,
): Promise<DiscountsBootstrapResponse> {
  return requestJson<DiscountsBootstrapResponse>({
    accessToken,
    path: `/v1/discounts/bootstrap?workstation_code=${encodeURIComponent(workstationCode)}`,
  });
}

export function listDiscounts({
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
}): Promise<DiscountsListResponse> {
  return requestJson<DiscountsListResponse>({
    accessToken,
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
  accessToken,
  discountId,
  workstationCode,
}: {
  accessToken: string;
  discountId: string;
  workstationCode: string;
}): Promise<OperationalDiscountDetailResponse> {
  return requestJson<OperationalDiscountDetailResponse>({
    accessToken,
    path: `/v1/discounts/${encodeURIComponent(discountId)}?workstation_code=${encodeURIComponent(workstationCode)}`,
  });
}

export function createDiscount({
  accessToken,
  payload,
  requestId,
}: {
  accessToken: string;
  payload: CreateOperationalDiscountRequest;
  requestId: string;
}): Promise<OperationalDiscountDetailResponse> {
  return requestJson<OperationalDiscountDetailResponse>({
    accessToken,
    body: payload,
    method: "POST",
    path: "/v1/discounts",
    headers: {
      "X-Request-ID": requestId,
    },
  });
}
