import type { CashSessionView, OpenCashSessionRequest } from "../../lib/api-contracts";
import { requestJson } from "../../lib/http";

export function getCurrentCashSession(
  accessToken: string,
  workstationCode: string,
): Promise<CashSessionView | null> {
  return requestJson<CashSessionView | null>({
    accessToken,
    path: `/v1/cash-sessions/current?workstation_code=${encodeURIComponent(workstationCode)}`,
  });
}

export function openCashSession({
  accessToken,
  payload,
  requestId,
}: {
  accessToken: string;
  payload: OpenCashSessionRequest;
  requestId: string;
}): Promise<CashSessionView> {
  return requestJson<CashSessionView>({
    accessToken,
    method: "POST",
    path: "/v1/cash-sessions/open",
    body: payload,
    headers: {
      "X-Request-ID": requestId,
    },
  });
}
