import type { components } from "@zeromerma/api-client";

import { appEnv } from "../env";

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

interface ValidationErrorDetail {
  msg?: string;
}

function isValidationErrorDetailArray(value: unknown): value is ValidationErrorDetail[] {
  return Array.isArray(value);
}

function extractApiErrorMessage(payload: unknown, fallback: string): string {
  if (!payload || typeof payload !== "object") {
    return fallback;
  }

  const detail = (payload as { detail?: unknown }).detail;

  if (typeof detail === "string" && detail.trim().length > 0) {
    return detail;
  }

  if (isValidationErrorDetailArray(detail)) {
    const message = detail.find((item) => typeof item.msg === "string" && item.msg.length > 0)?.msg;
    if (message) {
      return message;
    }
  }

  return fallback;
}

export class ApiError extends Error {
  readonly responseBody: unknown;
  readonly statusCode: number;

  constructor(statusCode: number, message: string, responseBody: unknown) {
    super(message);
    this.name = "ApiError";
    this.statusCode = statusCode;
    this.responseBody = responseBody;
  }
}

export async function requestJson<TResponse>({
  accessToken,
  body,
  method = "GET",
  path,
}: RequestJsonOptions): Promise<TResponse> {
  const headers = new Headers();

  if (accessToken) {
    headers.set("Authorization", `Bearer ${accessToken}`);
  }

  if (body !== undefined) {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(`${appEnv.VITE_API_BASE_URL}${path}`, {
    method,
    headers,
    body: body === undefined ? undefined : JSON.stringify(body),
  });

  if (!response.ok) {
    let responseBody: unknown = null;

    try {
      responseBody = await response.json();
    } catch {
      responseBody = null;
    }

    throw new ApiError(
      response.status,
      extractApiErrorMessage(responseBody, `${method} ${path} failed.`),
      responseBody,
    );
  }

  return (await response.json()) as TResponse;
}

export async function fetchApiHealth(): Promise<HealthResponse> {
  const response = await fetch(`${appEnv.VITE_API_BASE_URL}/health`);

  if (!response.ok) {
    throw new Error("API health check failed.");
  }

  return (await response.json()) as HealthResponse;
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
