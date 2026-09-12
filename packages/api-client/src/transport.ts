import type { components } from "./generated/schema";

export type ApiErrorResponse = components["schemas"]["ApiErrorResponse"];

export interface ApiRequestOptions {
  accessToken?: string | null;
  baseUrl: string;
  body?: unknown;
  headers?: HeadersInit;
  method?: "DELETE" | "GET" | "PATCH" | "POST" | "PUT";
  path: string;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
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

  constructor(statusCode: number, message: string, responseBody: unknown) {
    super(message);
    this.name = "ApiError";
    this.statusCode = statusCode;
    this.responseBody = responseBody;
    this.error = isApiErrorResponse(responseBody) ? responseBody : null;
  }
}

export async function requestApiJson<TResponse>({
  accessToken,
  baseUrl,
  body,
  headers,
  method = "GET",
  path,
}: ApiRequestOptions): Promise<TResponse> {
  const requestHeaders = new Headers(headers);

  if (accessToken) {
    requestHeaders.set("Authorization", `Bearer ${accessToken}`);
  }

  if (body !== undefined) {
    requestHeaders.set("Content-Type", "application/json");
  }

  const response = await fetch(`${baseUrl}${path}`, {
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
    throw new ApiError(response.status, message, responseBody);
  }

  if (response.status === 204) {
    return undefined as TResponse;
  }

  return (await response.json()) as TResponse;
}
