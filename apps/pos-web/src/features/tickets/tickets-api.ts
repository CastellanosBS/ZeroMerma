import type {
  TicketDetailResponse,
  TicketReprintRequest,
  TicketsBootstrapResponse,
  TicketsListResponse,
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

export function getTicketsBootstrap(
  accessToken: string,
  workstationCode: string,
): Promise<TicketsBootstrapResponse> {
  return requestJson<TicketsBootstrapResponse>({
    accessToken,
    path: `/v1/tickets/bootstrap?workstation_code=${encodeURIComponent(workstationCode)}`,
  });
}

export function listTickets({
  accessToken,
  query,
  scope,
  workstationCode,
}: {
  accessToken: string;
  query?: string;
  scope?: string;
  workstationCode: string;
}): Promise<TicketsListResponse> {
  return requestJson<TicketsListResponse>({
    accessToken,
    path: `/v1/tickets${buildQueryString({
      workstation_code: workstationCode,
      scope,
      query,
    })}`,
  });
}

export function getTicketDetail({
  accessToken,
  ticketId,
  workstationCode,
}: {
  accessToken: string;
  ticketId: string;
  workstationCode: string;
}): Promise<TicketDetailResponse> {
  return requestJson<TicketDetailResponse>({
    accessToken,
    path: `/v1/tickets/${encodeURIComponent(ticketId)}?workstation_code=${encodeURIComponent(workstationCode)}`,
  });
}

export function reprintTicket({
  accessToken,
  payload,
  requestId,
  ticketId,
}: {
  accessToken: string;
  payload: TicketReprintRequest;
  requestId: string;
  ticketId: string;
}): Promise<TicketDetailResponse> {
  return requestJson<TicketDetailResponse>({
    accessToken,
    body: payload,
    method: "POST",
    path: `/v1/tickets/${encodeURIComponent(ticketId)}/reprint`,
    headers: {
      "X-Request-ID": requestId,
    },
  });
}
