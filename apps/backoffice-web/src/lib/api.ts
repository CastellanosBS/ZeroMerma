import { ApiError, requestApiJson, type components, type SessionResponse } from "@zeromerma/api-client";

import { appEnv } from "../env";
import {
  backofficeAuthorizationQueryKey,
  clearAdministrativeQueries,
  queryClient,
} from "./query-client";
import { useBackofficeAuthStore } from "../features/auth/backoffice-auth-store";

export { ApiError };

export type HealthResponse = components["schemas"]["HealthResponse"];
export type AuthenticatedUser = components["schemas"]["AuthenticatedUser"];
export type LoginRequest = components["schemas"]["LoginRequest"];
export type LoginResponse = components["schemas"]["LoginResponse"];

interface RequestJsonOptions {

  body?: unknown;
  method?: "DELETE" | "GET" | "PATCH" | "POST";
  path: string;
}

export async function requestJson<TResponse>({
  body,
  method = "GET",
  path,
}: RequestJsonOptions): Promise<TResponse> {
  const generation = useBackofficeAuthStore.getState().generation;
  try {
    return await requestApiJson<TResponse>({
      surface: "BACKOFFICE",
      csrfToken: useBackofficeAuthStore.getState().csrfToken,
      baseUrl: appEnv.VITE_API_BASE_URL,
      body,
      method,
      path,
    });
  } catch (error) {
    if (error instanceof ApiError && useBackofficeAuthStore.getState().generation === generation && path !== "/v1/auth/login") {
      if (error.statusCode === 401 && error.error?.code !== "INVALID_CREDENTIALS") useBackofficeAuthStore.getState().clearSession();
      if (error.error?.code === "PASSWORD_RESET_REQUIRED") useBackofficeAuthStore.getState().requirePasswordChange();
      if (error.error?.code === "CSRF_FAILED" && path !== "/v1/auth/session") {
        // Restore a cookie rotated by another tab, but never replay an unsafe request.
        useBackofficeAuthStore.getState().requireVerification();
        const recoveryGeneration = useBackofficeAuthStore.getState().generation;
        try {
          const response = await requestJson<SessionResponse>({ path: "/v1/auth/session" });
          if (useBackofficeAuthStore.getState().generation === recoveryGeneration) useBackofficeAuthStore.getState().setSession(response);
        } catch {
          // Preserve the original operation error; session reads handle revocation separately.
        }
      }
      if (error.statusCode === 403 && error.error?.code !== "CSRF_FAILED" && path.split("?")[0] !== "/v1/auth/me") {
        void clearAdministrativeQueries(queryClient).then(() =>
          queryClient.invalidateQueries({ queryKey: backofficeAuthorizationQueryKey }),
        );
      }
    }
    throw error;
  }
}

export async function fetchApiHealth(): Promise<HealthResponse> {
  return requestJson<HealthResponse>({ path: "/health" });
}

export function loginBackofficeUser(payload: LoginRequest): Promise<LoginResponse> {
  return requestJson<LoginResponse>({
    method: "POST",
    path: "/v1/auth/login",
    body: payload,
  });
}

export function getCurrentBackofficeUser(): Promise<AuthenticatedUser> {
  return requestJson<AuthenticatedUser>({
    path: "/v1/auth/me",
  });
}

export function toBackofficeErrorMessage(error: unknown, fallback: string): string {
  if (error instanceof ApiError) {
    return error.message;
  }

  if (error instanceof Error && error.message.trim().length > 0) {
    return error.message;
  }

  return fallback;
}
