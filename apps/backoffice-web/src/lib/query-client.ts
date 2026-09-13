import { QueryClient } from "@tanstack/react-query";

export const queryClient = new QueryClient();

export const backofficeAuthorizationQueryKey = ["backoffice-auth", "me"] as const;

export async function clearAdministrativeQueries(client: QueryClient) {
  await client.cancelQueries({ queryKey: ["admin"] });
  client.removeQueries({ queryKey: ["admin"] });
  client.getMutationCache().clear();
}
