import type { components, SessionResponse, AuthSessionView } from "@zeromerma/api-client";
import { requestJson } from "../../lib/http";
import { usePosAuthStore } from "./auth-store";

export async function restoreSession(): Promise<void> {
  const generation = usePosAuthStore.getState().generation;
  const response = await requestJson<SessionResponse>({ path: "/v1/auth/session" });
  if (usePosAuthStore.getState().generation === generation) {
    usePosAuthStore.getState().setSession(response);
  }
}
export async function recordActivity(): Promise<void> {
  const generation = usePosAuthStore.getState().generation;
  const session = await requestJson<AuthSessionView>({ path: "/v1/auth/activity", method: "POST" });
  if (usePosAuthStore.getState().generation === generation) {
    usePosAuthStore.getState().updateSession(session);
  }
}
export async function logoutSession(): Promise<void> {
  const generation = usePosAuthStore.getState().generation;
  await requestJson<void>({ path: "/v1/auth/logout", method: "POST" });
  if (usePosAuthStore.getState().generation === generation) usePosAuthStore.getState().clearSession();
}
export async function changePassword(payload: components["schemas"]["PasswordChangeRequest"]): Promise<void> {
  const generation = usePosAuthStore.getState().generation;
  await requestJson<void>({ path: "/v1/auth/password/change", method: "POST", body: payload });
  if (usePosAuthStore.getState().generation === generation) usePosAuthStore.getState().clearSession();
}
export async function reauthenticate(payload: components["schemas"]["ReauthenticationRequest"]): Promise<void> {
  const generation = usePosAuthStore.getState().generation;
  const response = await requestJson<SessionResponse>({ path: "/v1/auth/reauthenticate", method: "POST", body: payload });
  if (usePosAuthStore.getState().generation === generation) usePosAuthStore.getState().setSession(response);
}
export async function lockSession(): Promise<void> {
  const generation = usePosAuthStore.getState().generation;
  await requestJson<AuthSessionView>({ path: "/v1/auth/lock", method: "POST" });
  if (usePosAuthStore.getState().generation === generation) usePosAuthStore.getState().markLocked();
}
