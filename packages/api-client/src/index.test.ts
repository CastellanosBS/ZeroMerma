import { afterEach, describe, expect, it, vi } from "vitest";

import { ApiError, isApiErrorResponse, requestApiJson } from "./index";
import type { components } from "./generated/schema";

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("api client package", () => {
  it.each(["POS", "BACKOFFICE"] as const)(
    "gives each %s attempt its own request ID while retrying the same intention",
    async (surface) => {
      const key: components["schemas"]["IdempotencyKey"] = "019a0000-0000-7000-8000-000000000001";
      const fetchMock = vi
        .fn()
        .mockRejectedValueOnce(new TypeError("Connection lost"))
        .mockResolvedValue(
          new Response(JSON.stringify({ status: "ok" }), {
            status: 200,
            headers: { "Content-Type": "application/json" },
          }),
        );
      vi.stubGlobal("fetch", fetchMock);
      for (const attempt of [0, 1]) {
        const request = requestApiJson({
          surface,
          baseUrl: "https://api.test",
          path: "/command",
          method: "POST",
          body: { amount: "12.30" },
          csrfToken: "memory-csrf",
          headers: {
            "Idempotency-Key": key,
            "X-Request-ID": "stale-request",
            "X-Correlation-ID": "untrusted-flow",
          },
        });
        if (attempt === 0) await expect(request).rejects.toThrow("Connection lost");
        else await expect(request).resolves.toEqual({ status: "ok" });
      }
      expect(fetchMock).toHaveBeenCalledTimes(2);
      const headers = fetchMock.mock.calls.map(
        ([, init]) => (init as RequestInit).headers as Headers,
      );
      expect(headers.map((value) => value.get("Idempotency-Key"))).toEqual([key, key]);
      const requestIds = headers.map((value) => value.get("X-Request-ID"));
      for (const requestId of requestIds)
        expect(requestId).toMatch(
          /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/,
        );
      expect(new Set(requestIds).size).toBe(2);
      expect(requestIds).not.toContain(key);
      expect(headers.every((value) => value.get("X-ZeroMerma-Surface") === surface)).toBe(true);
      expect(headers.every((value) => !value.has("X-Correlation-ID"))).toBe(true);
    },
  );
  it("keeps generated contracts as the package boundary", () => {
    const payload = {
      code: "CONFLICT",
      message: "The resource changed.",
      details: null,
      request_id: "request-1",
      field_errors: null,
    };

    expect(isApiErrorResponse(payload)).toBe(true);
    expect(isApiErrorResponse({ detail: "legacy-only" })).toBe(false);
    expect(isApiErrorResponse({ ...payload, request_id: 42 })).toBe(false);
    expect(isApiErrorResponse({ ...payload, details: "unstructured" })).toBe(false);
    expect(isApiErrorResponse({ ...payload, field_errors: [{}] })).toBe(false);
  });

  it("uses the generated error envelope in the central transport", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(
          JSON.stringify({
            code: "CONFLICT",
            message: "The resource changed.",
            details: { state: "CLOSED" },
            request_id: "request-1",
            field_errors: null,
          }),
          { status: 409, headers: { "Content-Type": "application/json" } },
        ),
      ),
    );

    const result = requestApiJson({
      surface: "POS",
      baseUrl: "http://api.test",
      path: "/resource",
    });

    await expect(result).rejects.toBeInstanceOf(ApiError);
    await expect(result).rejects.toMatchObject({
      message: "The resource changed.",
      statusCode: 409,
    });
  });

  it("preserves auth, headers, body, and a typed successful response", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ status: "ok" }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    const payload = await requestApiJson<{ status: string }>({
      surface: "POS",
      csrfToken: "memory-csrf",
      baseUrl: "http://api.test",
      body: { value: "1.25" },
      headers: { "X-Request-ID": "request-1" },
      method: "POST",
      path: "/resource",
    });

    expect(payload.status).toBe("ok");
    const [, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    const headers = init.headers as Headers;
    expect(headers.has("Authorization")).toBe(false);
    expect(headers.get("X-CSRF-Token")).toBe("memory-csrf");
    expect(headers.get("X-ZeroMerma-Surface")).toBe("POS");
    expect(init.credentials).toBe("include");
    expect(init.cache).toBe("no-store");
    expect(headers.get("X-Request-ID")).toMatch(/^[0-9a-f-]{36}$/);
    expect(headers.get("X-Request-ID")).not.toBe("request-1");
    expect(init.body).toBe('{"value":"1.25"}');
  });
});

it("identifies read and empty-response attempts without changing their return values", async () => {
  const fetchMock = vi
    .fn()
    .mockResolvedValueOnce(new Response(JSON.stringify({ value: 1 }), { status: 200 }))
    .mockResolvedValueOnce(new Response(null, { status: 204 }));
  vi.stubGlobal("fetch", fetchMock);
  const options = {
    surface: "BACKOFFICE" as const,
    baseUrl: "https://api.test",
    path: "/resource",
  };
  await expect(requestApiJson(options)).resolves.toEqual({ value: 1 });
  await expect(requestApiJson({ ...options, method: "DELETE" })).resolves.toBeUndefined();
  const requestIds = fetchMock.mock.calls.map(([, init]) =>
    ((init as RequestInit).headers as Headers).get("X-Request-ID"),
  );
  expect(requestIds.every((value) => /^[0-9a-f-]{36}$/.test(value!))).toBe(true);
  expect(new Set(requestIds).size).toBe(2);
});

it.each([
  null,
  "private-customer@example.test",
  "00000000-0000-4000-8000-000000000001, duplicate",
  "00000000-0000-4000-8000-000000000001",
])("exposes only safe response correlation IDs (%s)", async (traceId) => {
  const headers = new Headers({ "Set-Cookie": "private-cookie", "X-Private": "private-header" });
  if (traceId !== null) {
    headers.set("X-Request-ID", traceId);
    headers.set("X-Correlation-ID", traceId);
  }
  const fetchMock = vi.fn().mockResolvedValue(new Response(null, { status: 503, headers }));
  vi.stubGlobal("fetch", fetchMock);
  const failure = await requestApiJson({
    surface: "POS",
    baseUrl: "https://api.test",
    path: "/resource",
  }).catch((error) => error);
  expect(failure).toBeInstanceOf(ApiError);
  if (!(failure instanceof ApiError)) throw new Error("Expected canonical ApiError");
  const sentRequestId = (fetchMock.mock.calls[0]![1].headers as Headers).get("X-Request-ID");
  const valid = traceId === "00000000-0000-4000-8000-000000000001";
  expect(failure.requestId).toBe(valid ? traceId : sentRequestId);
  expect(failure.correlationId).toBe(valid ? traceId : null);
  expect(failure).not.toHaveProperty("headers");
  expect(JSON.stringify(failure)).not.toMatch(
    /private-cookie|private-header|private-customer|duplicate/,
  );
});

it.each([undefined, "false", "TRUE", "true"])(
  "exposes only the canonical replay boolean from an error response header %s",
  async (value) => {
    const headers = new Headers({
      "Content-Type": "application/json",
      "Set-Cookie": "private-session",
      "X-Private": "secret",
    });
    if (value !== undefined) headers.set("Idempotency-Replayed", value);
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(
          JSON.stringify({
            code: "CASH_CLOSE_ALREADY_EXISTS",
            message: "Already closed",
            details: null,
            field_errors: null,
            request_id: null,
          }),
          { status: 409, headers },
        ),
      ),
    );
    const failure = await requestApiJson({
      surface: "POS",
      baseUrl: "https://api.test",
      path: "/recovery",
    }).catch((error) => error);
    expect(failure).toBeInstanceOf(ApiError);
    if (!(failure instanceof ApiError)) throw new Error("Expected canonical ApiError");
    expect(failure.idempotencyReplayed).toBe(value === "true");
    expect(failure).not.toHaveProperty("headers");
    expect(JSON.stringify(failure)).not.toMatch(/private-session|X-Private|secret/);
  },
);
