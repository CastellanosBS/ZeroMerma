import { afterEach, describe, expect, it, vi } from "vitest";

import { ApiError, isApiErrorResponse, requestApiJson } from "./index";
import type { components } from "./generated/schema";

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("api client package", () => {
  it("preserves an intention key across explicit retries with independent request IDs", async () => {
    const key: components["schemas"]["IdempotencyKey"] = "019a0000-0000-7000-8000-000000000001";
    const fetchMock = vi.fn().mockImplementation(() => Promise.resolve(
      new Response(JSON.stringify({ status: "ok" }), {
        status: 200, headers: { "Content-Type": "application/json" },
      }),
    ));
    vi.stubGlobal("fetch", fetchMock);
    for (const requestId of ["request-one", "request-two"]) {
      await requestApiJson({
        surface: "POS", baseUrl: "https://api.test", path: "/command", method: "POST",
        body: { amount: "12.30" }, csrfToken: "memory-csrf",
        headers: { "Idempotency-Key": key, "X-Request-ID": requestId },
      });
    }
    expect(fetchMock).toHaveBeenCalledTimes(2);
    const headers = fetchMock.mock.calls.map(([, init]) => (init as RequestInit).headers as Headers);
    expect(headers.map((value) => value.get("Idempotency-Key"))).toEqual([key, key]);
    expect(headers.map((value) => value.get("X-Request-ID"))).toEqual(["request-one", "request-two"]);
  });
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

    const result = requestApiJson({ surface: "POS", baseUrl: "http://api.test", path: "/resource" });

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
    expect(headers.get("X-Request-ID")).toBe("request-1");
    expect(init.body).toBe('{"value":"1.25"}');
  });
});
