import type { CashSessionView, OpenCashSessionRequest } from "../../lib/api-contracts";
import { requestJson } from "../../lib/http";

export function getCurrentCashSession(
  workstationCode: string,
): Promise<CashSessionView | null> {
  return requestJson<CashSessionView | null>({
    path: `/v1/cash-sessions/current?workstation_code=${encodeURIComponent(workstationCode)}`,
  });
}

export function openCashSession({
  payload,
  requestId,
}: {

  payload: OpenCashSessionRequest;
  requestId: string;
}): Promise<CashSessionView> {
  return requestJson<CashSessionView>({
    method: "POST",
    path: "/v1/cash-sessions/open",
    body: payload,
    headers: {
      "X-Request-ID": requestId,
    },
  });
}
