import type { CashSessionOpenResultView } from "../../lib/api-contracts";
import type { CashSessionView, OpenCashSessionRequest } from "../../lib/api-contracts";
import { requestJson } from "../../lib/http";

export function getCurrentCashSession(workstationCode: string): Promise<CashSessionView | null> {
  return requestJson<CashSessionView | null>({
    path: `/v1/cash-sessions/current?workstation_code=${encodeURIComponent(workstationCode)}`,
  });
}

export function openCashSession({
  idempotencyKey,
  payload,
  requestId,
}: {
  idempotencyKey: string;
  payload: OpenCashSessionRequest;
  requestId: string;
}): Promise<CashSessionOpenResultView> {
  return requestJson<CashSessionOpenResultView>({
    method: "POST",
    path: "/v1/cash-sessions/open",
    body: payload,
    headers: {
      "X-Request-ID": requestId,
      "Idempotency-Key": idempotencyKey,
    },
  });
}
