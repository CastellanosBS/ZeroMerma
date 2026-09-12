import { afterEach, describe, expect, it, vi } from "vitest";

import { ApiError, isApiErrorResponse, requestApiJson } from "./index";

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("api client package", () => {
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

    const result = requestApiJson({ baseUrl: "http://api.test", path: "/resource" });

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
      accessToken: "token-1",
      baseUrl: "http://api.test",
      body: { value: "1.25" },
      headers: { "X-Request-ID": "request-1" },
      method: "POST",
      path: "/resource",
    });

    expect(payload.status).toBe("ok");
    const [, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    const headers = init.headers as Headers;
    expect(headers.get("Authorization")).toBe("Bearer token-1");
    expect(headers.get("X-Request-ID")).toBe("request-1");
    expect(init.body).toBe('{"value":"1.25"}');
  });
});
