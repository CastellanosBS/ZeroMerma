import type { components, SessionResponse, AuthSessionView } from "@zeromerma/api-client";
import { requestJson } from "../../lib/api";
import { useBackofficeAuthStore } from "./backoffice-auth-store";

export async function restoreSession(): Promise<void> {
  const generation = useBackofficeAuthStore.getState().generation;
  const response = await requestJson<SessionResponse>({ path: "/v1/auth/session" });
  if (useBackofficeAuthStore.getState().generation === generation) {
    useBackofficeAuthStore.getState().setSession(response);
  }
}
export async function recordActivity(): Promise<void> {
  const generation = useBackofficeAuthStore.getState().generation;
  const session = await requestJson<AuthSessionView>({ path: "/v1/auth/activity", method: "POST" });
  if (useBackofficeAuthStore.getState().generation === generation) {
    useBackofficeAuthStore.getState().updateSession(session);
  }
}
export async function logoutSession(): Promise<void> {
  const generation = useBackofficeAuthStore.getState().generation;
  await requestJson<void>({ path: "/v1/auth/logout", method: "POST" });
  if (useBackofficeAuthStore.getState().generation === generation) useBackofficeAuthStore.getState().clearSession();
}
export async function changePassword(payload: components["schemas"]["PasswordChangeRequest"]): Promise<void> {
  const generation = useBackofficeAuthStore.getState().generation;
  await requestJson<void>({ path: "/v1/auth/password/change", method: "POST", body: payload });
  if (useBackofficeAuthStore.getState().generation === generation) useBackofficeAuthStore.getState().clearSession();
}
export function listOwnSessions(page = 1) {
  return requestJson<components["schemas"]["AuthSessionsResponse"]>({ path: `/v1/auth/sessions?page=${page}&page_size=10` });
}
export function revokeSession(id: string) {
  return requestJson<void>({ path: "/v1/auth/sessions/" + encodeURIComponent(id), method: "DELETE" });
}
export function revokeOtherSessions() {
  return requestJson<void>({ path: "/v1/auth/sessions/revoke-others", method: "POST" });
}
