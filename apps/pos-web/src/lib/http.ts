import { ApiError, requestApiJson } from "@zeromerma/api-client";

import { appEnv } from "../env";
import { usePosAuthStore } from "../features/auth/auth-store";

export { ApiError };

interface RequestJsonOptions {

  body?: unknown;
  headers?: HeadersInit;
  method?: "GET" | "POST";
  path: string;
}

export async function requestJson<TResponse>({
  body,
  headers,
  method = "GET",
  path,
}: RequestJsonOptions): Promise<TResponse> {
  const generation = usePosAuthStore.getState().generation;
  try {
  return await requestApiJson<TResponse>({
    surface: "POS",
    csrfToken: usePosAuthStore.getState().csrfToken,
    baseUrl: appEnv.VITE_API_BASE_URL,
    body,
    headers,
    method,
    path,
  });
  } catch (error) {
    if (error instanceof ApiError && usePosAuthStore.getState().generation === generation && path !== "/v1/auth/login") {
      if (error.statusCode === 401 && error.error?.code !== "INVALID_CREDENTIALS") usePosAuthStore.getState().clearSession();
      if (error.statusCode === 423) usePosAuthStore.getState().markLocked();
      if (error.error?.code === "PASSWORD_RESET_REQUIRED") usePosAuthStore.getState().requirePasswordChange();
    }
    throw error;
  }
}

export function toOperationalErrorMessage(error: unknown, fallback: string): string {
  if (error instanceof ApiError) {
    return error.message;
  }

  if (error instanceof Error && error.message.trim().length > 0) {
    return error.message;
  }

  return fallback;
}
