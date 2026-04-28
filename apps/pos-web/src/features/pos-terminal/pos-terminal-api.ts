import type {
  ConfirmSaleRequest,
  PosCatalogResponse,
  PosClassProductsResponse,
  SaleDetailView,
} from "../../lib/api-contracts";
import { requestJson } from "../../lib/http";

function buildQueryString(values: Record<string, string | undefined>): string {
  const searchParams = new URLSearchParams();

  for (const [key, value] of Object.entries(values)) {
    if (value) {
      searchParams.set(key, value);
    }
  }

  const queryString = searchParams.toString();
  return queryString.length > 0 ? `?${queryString}` : "";
}

export function getPosCatalog(
  accessToken: string,
  workstationCode: string,
  query: string | undefined,
): Promise<PosCatalogResponse> {
  return requestJson<PosCatalogResponse>({
    accessToken,
    path: `/v1/pos/catalog${buildQueryString({
      workstation_code: workstationCode,
      query,
    })}`,
  });
}

export function getPosClassProducts(
  accessToken: string,
  workstationCode: string,
  classId: string,
  query: string | undefined,
): Promise<PosClassProductsResponse> {
  return requestJson<PosClassProductsResponse>({
    accessToken,
    path: `/v1/pos/classes/${classId}/products${buildQueryString({
      workstation_code: workstationCode,
      query,
    })}`,
  });
}

export function confirmPosSale(
  accessToken: string,
  payload: ConfirmSaleRequest,
): Promise<SaleDetailView> {
  return requestJson<SaleDetailView>({
    accessToken,
    body: payload,
    method: "POST",
    path: "/v1/sales/confirm",
  });
}
