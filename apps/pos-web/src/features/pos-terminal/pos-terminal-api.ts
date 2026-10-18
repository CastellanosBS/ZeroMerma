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
  workstationCode: string,
  query: string | undefined,
): Promise<PosCatalogResponse> {
  return requestJson<PosCatalogResponse>({
    path: `/v1/pos/catalog${buildQueryString({
      workstation_code: workstationCode,
      query,
    })}`,
  });
}

export function getPosClassProducts(
  workstationCode: string,
  classId: string,
  query: string | undefined,
): Promise<PosClassProductsResponse> {
  return requestJson<PosClassProductsResponse>({
    path: `/v1/pos/classes/${classId}/products${buildQueryString({
      workstation_code: workstationCode,
      query,
    })}`,
  });
}

export function confirmPosSale(
  payload: ConfirmSaleRequest,
): Promise<SaleDetailView> {
  return requestJson<SaleDetailView>({
    body: payload,
    method: "POST",
    path: "/v1/sales/confirm",
  });
}
