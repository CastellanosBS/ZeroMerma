import type {
  ReturnCommitRequest,
  ReturnsHistoryResponse,
  ReturnOriginalSaleDetailResponse,
  ReturnsBootstrapResponse,
  ReturnsClassProductsResponse,
  ReturnsSearchSalesResponse,
  SaleReturnDetailResponse,
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

export function getReturnsBootstrap(
  accessToken: string,
  workstationCode: string,
): Promise<ReturnsBootstrapResponse> {
  return requestJson<ReturnsBootstrapResponse>({
    accessToken,
    path: `/v1/returns/bootstrap?workstation_code=${encodeURIComponent(workstationCode)}`,
  });
}

export function searchReturnSales({
  accessToken,
  dateFrom,
  dateTo,
  query,
  scope,
  workstationCode,
}: {
  accessToken: string;
  dateFrom?: string;
  dateTo?: string;
  query?: string;
  scope?: string;
  workstationCode: string;
}): Promise<ReturnsSearchSalesResponse> {
  return requestJson<ReturnsSearchSalesResponse>({
    accessToken,
    path: `/v1/returns/search-sales${buildQueryString({
      workstation_code: workstationCode,
      scope,
      query,
      date_from: dateFrom,
      date_to: dateTo,
    })}`,
  });
}

export function getReturnSaleDetail({
  accessToken,
  saleId,
  workstationCode,
}: {
  accessToken: string;
  saleId: string;
  workstationCode: string;
}): Promise<ReturnOriginalSaleDetailResponse> {
  return requestJson<ReturnOriginalSaleDetailResponse>({
    accessToken,
    path: `/v1/returns/sales/${encodeURIComponent(saleId)}?workstation_code=${encodeURIComponent(workstationCode)}`,
  });
}

export function getReturnsHistory({
  accessToken,
  createdByUserId,
  dateFrom,
  dateTo,
  query,
  reasonCode,
  scope,
  workstationCode,
}: {
  accessToken: string;
  createdByUserId?: string;
  dateFrom?: string;
  dateTo?: string;
  query?: string;
  reasonCode?: string;
  scope?: string;
  workstationCode: string;
}): Promise<ReturnsHistoryResponse> {
  return requestJson<ReturnsHistoryResponse>({
    accessToken,
    path: `/v1/returns/history${buildQueryString({
      workstation_code: workstationCode,
      scope,
      query,
      date_from: dateFrom,
      date_to: dateTo,
      created_by_user_id: createdByUserId,
      reason_code: reasonCode,
    })}`,
  });
}

export function getReturnsClassProducts({
  accessToken,
  classId,
  workstationCode,
}: {
  accessToken: string;
  classId: string;
  workstationCode: string;
}): Promise<ReturnsClassProductsResponse> {
  return requestJson<ReturnsClassProductsResponse>({
    accessToken,
    path: `/v1/returns/classes/${encodeURIComponent(classId)}/products?workstation_code=${encodeURIComponent(workstationCode)}`,
  });
}

export function commitSaleReturn({
  accessToken,
  payload,
  requestId,
}: {
  accessToken: string;
  payload: ReturnCommitRequest;
  requestId: string;
}): Promise<SaleReturnDetailResponse> {
  return requestJson<SaleReturnDetailResponse>({
    accessToken,
    body: payload,
    method: "POST",
    path: "/v1/returns/commit",
    headers: {
      "X-Request-ID": requestId,
    },
  });
}

export function getSaleReturnDetail({
  accessToken,
  returnId,
  workstationCode,
}: {
  accessToken: string;
  returnId: string;
  workstationCode: string;
}): Promise<SaleReturnDetailResponse> {
  return requestJson<SaleReturnDetailResponse>({
    accessToken,
    path: `/v1/returns/${encodeURIComponent(returnId)}?workstation_code=${encodeURIComponent(workstationCode)}`,
  });
}
