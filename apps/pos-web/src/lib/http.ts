import { appEnv } from "../env";

interface RequestJsonOptions {
  accessToken?: string | null;
  body?: unknown;
  headers?: HeadersInit;
  method?: "GET" | "POST";
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
  headers,
  method = "GET",
  path,
}: RequestJsonOptions): Promise<TResponse> {
  const requestHeaders = new Headers(headers);

  if (accessToken) {
    requestHeaders.set("Authorization", `Bearer ${accessToken}`);
  }

  if (body !== undefined) {
    requestHeaders.set("Content-Type", "application/json");
  }

  const response = await fetch(`${appEnv.VITE_API_BASE_URL}${path}`, {
    method,
    headers: requestHeaders,
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

export function toOperationalErrorMessage(error: unknown, fallback: string): string {
  if (error instanceof ApiError) {
    return error.message;
  }

  if (error instanceof Error && error.message.trim().length > 0) {
    return error.message;
  }

  return fallback;
}
