import { useQuery } from "@tanstack/react-query";

import { appEnv } from "../../env";
import { usePosAuthStore } from "../auth/auth-store";
import { getTicketDetail, getTicketsBootstrap, listTickets } from "./tickets-api";

function normalizeQuery(query: string): string {
  return query.trim();
}

export function ticketsBootstrapQueryKey(workstationCode: string) {
  return ["tickets-bootstrap", workstationCode] as const;
}

export function useTicketsBootstrapQuery() {
  const isAuthenticated = usePosAuthStore((state) => state.isAuthenticated);

  return useQuery({
    queryKey: ticketsBootstrapQueryKey(appEnv.VITE_POS_WORKSTATION_CODE),
    queryFn: () => getTicketsBootstrap(appEnv.VITE_POS_WORKSTATION_CODE),
    enabled: isAuthenticated,
  });
}

export function ticketsListQueryKey(workstationCode: string, scope: string, query: string) {
  return ["tickets-list", workstationCode, scope, normalizeQuery(query)] as const;
}

export function useTicketsListQuery(scope: string, query: string) {
  const isAuthenticated = usePosAuthStore((state) => state.isAuthenticated);
  const normalizedQuery = normalizeQuery(query);

  return useQuery({
    queryKey: ticketsListQueryKey(appEnv.VITE_POS_WORKSTATION_CODE, scope, normalizedQuery),
    queryFn: () =>
      listTickets({
        workstationCode: appEnv.VITE_POS_WORKSTATION_CODE,
        scope,
        query: normalizedQuery.length > 0 ? normalizedQuery : undefined,
      }),
    enabled: isAuthenticated,
  });
}

export function ticketDetailQueryKey(workstationCode: string, ticketId: string) {
  return ["ticket-detail", workstationCode, ticketId] as const;
}

export function useTicketDetailQuery(ticketId: string | null) {
  const isAuthenticated = usePosAuthStore((state) => state.isAuthenticated);

  return useQuery({
    queryKey: ticketDetailQueryKey(appEnv.VITE_POS_WORKSTATION_CODE, ticketId ?? "none"),
    queryFn: () =>
      getTicketDetail({
        ticketId: ticketId!,
        workstationCode: appEnv.VITE_POS_WORKSTATION_CODE,
      }),
    enabled: isAuthenticated && ticketId !== null,
  });
}
