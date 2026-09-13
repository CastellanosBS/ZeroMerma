import { ApiError, requestApiJson, type components } from "@zeromerma/api-client";

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
  accessToken?: string | null;
  body?: unknown;
  method?: "GET" | "PATCH" | "POST";
  path: string;
}

export async function requestJson<TResponse>({
  accessToken,
  body,
  method = "GET",
  path,
}: RequestJsonOptions): Promise<TResponse> {
  try {
    return await requestApiJson<TResponse>({
      accessToken,
      baseUrl: appEnv.VITE_API_BASE_URL,
      body,
      method,
      path,
    });
  } catch (error) {
    if (accessToken && error instanceof ApiError) {
      if (error.statusCode === 401) useBackofficeAuthStore.getState().clearSession();
      if (error.statusCode === 403 && path.split("?")[0] !== "/v1/auth/me") {
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

export function getCurrentBackofficeUser(accessToken: string): Promise<AuthenticatedUser> {
  return requestJson<AuthenticatedUser>({
    accessToken,
    path: "/v1/auth/me?surface=BACKOFFICE",
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
