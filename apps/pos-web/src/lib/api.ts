import type { HealthResponse } from "./api-contracts";
import { requestJson } from "./http";

export type { HealthResponse } from "./api-contracts";

export async function fetchApiHealth(): Promise<HealthResponse> {
  return requestJson<HealthResponse>({ path: "/health" });
}
