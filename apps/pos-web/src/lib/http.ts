import { ApiError, requestApiJson } from "@zeromerma/api-client";

import { appEnv } from "../env";

export { ApiError };

interface RequestJsonOptions {
  accessToken?: string | null;
  body?: unknown;
  headers?: HeadersInit;
  method?: "GET" | "POST";
  path: string;
}

export async function requestJson<TResponse>({
  accessToken,
  body,
  headers,
  method = "GET",
  path,
}: RequestJsonOptions): Promise<TResponse> {
  return requestApiJson<TResponse>({
    accessToken,
    baseUrl: appEnv.VITE_API_BASE_URL,
    body,
    headers,
    method,
    path,
  });
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
