import { ApiError, requestApiJson, type SessionResponse } from "@zeromerma/api-client";

import { appEnv } from "../env";
import { usePosAuthStore } from "../features/auth/auth-store";
import { markLocalConnectionUnreachable, requireLocalBackendForCommand } from "../features/connectivity/connectivity-state";

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
  if (method !== "GET" && !path.startsWith("/v1/auth/")) {
    await requireLocalBackendForCommand();
    if (usePosAuthStore.getState().generation !== generation) {
      throw new Error("La sesión cambió. Verifica la sesión antes de continuar.");
    }
  }
  const controller = new AbortController();
  const timeout = globalThis.setTimeout(() => controller.abort(), 15_000);
  try {
  return await requestApiJson<TResponse>({
    surface: "POS",
    csrfToken: usePosAuthStore.getState().csrfToken,
    baseUrl: appEnv.VITE_API_BASE_URL,
    body,
    headers,
    method,
    path,
    signal: controller.signal,
  });
  } catch (error) {
    if (!(error instanceof ApiError)) {
      markLocalConnectionUnreachable();
      if (!path.startsWith("/v1/auth/")) {
        throw new Error(method === "GET"
          ? "No fue posible consultar el servidor local. Verifica la conexión y vuelve a consultar."
          : "No se pudo confirmar el resultado de la operación enviada. Consulta su referencia antes de reintentar; no vuelvas a cobrar.",
        { cause: error });
      }
    }
    if (error instanceof ApiError && usePosAuthStore.getState().generation === generation && path !== "/v1/auth/login") {
      if (error.statusCode === 401 && error.error?.code !== "INVALID_CREDENTIALS") usePosAuthStore.getState().clearSession();
      if (error.statusCode === 423) usePosAuthStore.getState().markLocked();
      if (error.error?.code === "PASSWORD_RESET_REQUIRED") usePosAuthStore.getState().requirePasswordChange();
      if (error.error?.code === "CSRF_FAILED" && path !== "/v1/auth/session") {
        // Another tab can rotate the shared cookie. Restore its envelope without replaying the mutation.
        usePosAuthStore.getState().requireVerification();
        const recoveryGeneration = usePosAuthStore.getState().generation;
        try {
          const response = await requestJson<SessionResponse>({ path: "/v1/auth/session" });
          if (usePosAuthStore.getState().generation === recoveryGeneration) usePosAuthStore.getState().setSession(response);
        } catch {
          // Preserve the original operation error; session reads handle revocation separately.
        }
      }
    }
    throw error;
  } finally {
    globalThis.clearTimeout(timeout);
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
