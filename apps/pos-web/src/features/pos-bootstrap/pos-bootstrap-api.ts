import type { PosBootstrapResponse } from "../../lib/api-contracts";
import { requestJson } from "../../lib/http";

export function getPosBootstrap(
  workstationCode: string,
): Promise<PosBootstrapResponse> {
  return requestJson<PosBootstrapResponse>({
    path: `/v1/pos/bootstrap?workstation_code=${encodeURIComponent(workstationCode)}`,
  });
}
