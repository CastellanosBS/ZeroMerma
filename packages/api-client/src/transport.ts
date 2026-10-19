import type { components } from "./generated/schema";

export type ApiErrorResponse = components["schemas"]["ApiErrorResponse"];

export interface ApiRequestOptions {
  csrfToken?: string | null;
  surface: components["schemas"]["AuthenticatedUser"]["default_surface"];
  baseUrl: string;
  body?: unknown;
  headers?: HeadersInit;
  method?: "DELETE" | "GET" | "PATCH" | "POST" | "PUT";
  path: string;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function safeTraceId(value: string | null): string | null {
  return value && /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(value)
    ? value.toLowerCase()
    : null;
}

export function isApiErrorResponse(value: unknown): value is ApiErrorResponse {
  if (!isRecord(value)) {
    return false;
  }

  return (
    typeof value.code === "string" &&
    value.code.length > 0 &&
    typeof value.message === "string" &&
    value.message.length > 0 &&
    (value.details === null || isRecord(value.details) || Array.isArray(value.details)) &&
    (value.request_id === null || typeof value.request_id === "string") &&
    (value.field_errors === null ||
      (Array.isArray(value.field_errors) &&
        value.field_errors.every(
          (field: unknown) =>
            isRecord(field) &&
            typeof field.message === "string" &&
            typeof field.type === "string" &&
            Array.isArray(field.location) &&
            field.location.every(
              (part: unknown) =>
                typeof part === "string" || (typeof part === "number" && Number.isInteger(part)),
            ),
        )))
  );
}

export class ApiError extends Error {
  readonly error: ApiErrorResponse | null;
  readonly responseBody: unknown;
  readonly statusCode: number;
  readonly idempotencyReplayed: boolean;
  readonly requestId: string | null;
  readonly correlationId: string | null;

  constructor(
    statusCode: number,
    message: string,
    responseBody: unknown,
    idempotencyReplayed = false,
    requestId: string | null = null,
    correlationId: string | null = null,
  ) {
    super(message);
    this.name = "ApiError";
    this.statusCode = statusCode;
    this.idempotencyReplayed = idempotencyReplayed;
    this.requestId = safeTraceId(requestId);
    this.correlationId = safeTraceId(correlationId);
    this.responseBody = responseBody;
    this.error = isApiErrorResponse(responseBody) ? responseBody : null;
  }
}

export async function requestApiJson<TResponse>({
  csrfToken,
  surface,
  baseUrl,
  body,
  headers,
  method = "GET",
  path,
}: ApiRequestOptions): Promise<TResponse> {
  const requestHeaders = new Headers(headers);

  if (requestHeaders.has("Authorization"))
    throw new Error("Bearer authentication is not supported.");
  // Each HTTP attempt is distinct; the intention key remains owned by its coordinator.
  const requestId = crypto.randomUUID();
  requestHeaders.set("X-Request-ID", requestId);
  requestHeaders.delete("X-Correlation-ID");
  requestHeaders.set("X-ZeroMerma-Surface", surface);
  requestHeaders.delete("X-CSRF-Token");
  if (method !== "GET" && csrfToken) requestHeaders.set("X-CSRF-Token", csrfToken);

  if (body !== undefined) {
    requestHeaders.set("Content-Type", "application/json");
  }

  const response = await fetch(`${baseUrl}${path}`, {
    credentials: "include",
    cache: "no-store",
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

    const message = isApiErrorResponse(responseBody)
      ? responseBody.message
      : `${method} ${path} failed.`;
    throw new ApiError(
      response.status,
      message,
      responseBody,
      response.headers.get("Idempotency-Replayed") === "true",
      safeTraceId(response.headers.get("X-Request-ID")) ?? requestId,
      safeTraceId(response.headers.get("X-Correlation-ID")),
    );
  }

  if (response.status === 204) {
    return undefined as TResponse;
  }

  return (await response.json()) as TResponse;
}
