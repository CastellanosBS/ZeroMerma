import { afterEach, describe, expect, it, vi } from "vitest";

import {
  dropNextSaleConfirmationResponse,
  observeRealApi,
  realEnvironment,
} from "../../../../scripts/dev/web-integration-support.mjs";

afterEach(() => vi.unstubAllEnvs());

function isolatedEnvironment() {
  vi.stubEnv("ZM_WEB_INTEGRATION_ISOLATED", "1");
  vi.stubEnv("ZM_E2E_RUN_ID", "guard-unit-test");
  vi.stubEnv("ZM_E2E_API_URL", "https://127.0.0.1:41201");
  vi.stubEnv("ZM_E2E_POS_URL", "https://127.0.0.1:41202");
  vi.stubEnv("ZM_E2E_POS_EMAIL", "synthetic@example.test");
  vi.stubEnv("ZM_E2E_PASSWORD", "unit-only-password");
  vi.stubEnv("ZM_E2E_ARTIFACT_DIR", ".tmp/unit-web-guard");
}

describe("real browser integration safety", () => {
  it.each([201, 409])(
    "loses a response only after the real sale fetch and requires 201, received %i",
    async (status) => {
      isolatedEnvironment();
      const route = {
        request: () => ({ method: () => "POST" }),
        fetch: vi.fn(async () => ({ status: () => status, json: async () => ({ id: "sale" }) })),
        abort: vi.fn(async () => {}),
      };
      let handler: ((value: typeof route) => Promise<void>) | undefined;
      const register = vi.fn(async (_url: string, callback: typeof handler) => {
        handler = callback;
      });
      const page = { on: vi.fn(), route: register };
      const network = observeRealApi({ on: vi.fn() }, page, "https://127.0.0.1:41201");
      const fault = await dropNextSaleConfirmationResponse(
        page,
        "https://127.0.0.1:41201",
        network,
      );
      const outcome =
        status === 201
          ? expect(fault.committed).resolves.toEqual({ id: "sale" })
          : expect(fault.committed).rejects.toThrow("received 409");
      await handler!(route);
      await outcome;
      expect(register.mock.calls[0]?.[0]).toBe("https://127.0.0.1:41201/v1/sales/confirm");
      expect(route.fetch).toHaveBeenCalledWith({ maxRedirects: 0 });
      expect(route.abort).toHaveBeenCalledWith("failed");
      expect(network).toEqual(
        status === 201 ? [{ method: "POST", path: "/v1/sales/confirm", status: 201 }] : [],
      );
      expect(() => page.route("", undefined)).toThrow("interception is forbidden");
    },
  );

  it("rejects direct invocation and remote or credential-bearing API origins", () => {
    vi.stubEnv("ZM_WEB_INTEGRATION_ISOLATED", "");
    expect(() => realEnvironment("pos")).toThrow("run-web-integration.ps1");
    isolatedEnvironment();
    for (const url of [
      "https://production.example.test",
      "http://localhost:8000",
      "http://user:secret@127.0.0.1:41201",
      "https://127.0.0.1:41201?token=secret",
    ]) {
      vi.stubEnv("ZM_E2E_API_URL", url);
      expect(() => realEnvironment("pos")).toThrow("dedicated HTTPS origin");
    }
  });

  it("forbids route interception and retains no queries, payloads or headers", () => {
    type Observation = Parameters<Parameters<typeof observeRealApi>[1]["on"]>[1];
    let responseListener: Observation | undefined;
    const page = {
      on: (_event: "response", listener: Observation) => {
        responseListener = listener;
      },
      route: vi.fn(),
      routeFromHAR: vi.fn(),
    };
    const context = { on: vi.fn(), route: vi.fn(), routeFromHAR: vi.fn() };
    const network = observeRealApi(context, page, "https://127.0.0.1:41201");
    expect(() => page.route()).toThrow("interception is forbidden");
    expect(() => context.routeFromHAR()).toThrow("interception is forbidden");
    responseListener?.({
      url: () => "https://127.0.0.1:41201/v1/admin/products?email=private&access_token=secret",
      status: () => 200,
      request: () => ({ method: () => "GET" }),
    });
    expect(network).toEqual([{ method: "GET", path: "/v1/admin/products", status: 200 }]);
  });
});
