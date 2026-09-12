import { afterEach, describe, expect, it, vi } from "vitest";

import { observeRealApi, realEnvironment } from "../../../../scripts/dev/web-integration-support.mjs";

afterEach(() => vi.unstubAllEnvs());

function isolatedEnvironment() {
  vi.stubEnv("ZM_WEB_INTEGRATION_ISOLATED", "1");
  vi.stubEnv("ZM_E2E_RUN_ID", "guard-unit-test");
  vi.stubEnv("ZM_E2E_API_URL", "http://127.0.0.1:41201");
  vi.stubEnv("ZM_E2E_POS_URL", "http://127.0.0.1:41202");
  vi.stubEnv("ZM_E2E_POS_EMAIL", "synthetic@example.test");
  vi.stubEnv("ZM_E2E_PASSWORD", "unit-only-password");
  vi.stubEnv("ZM_E2E_ARTIFACT_DIR", ".tmp/unit-web-guard");
}

describe("real browser integration safety", () => {
  it("rejects direct invocation and remote or credential-bearing API origins", () => {
    vi.stubEnv("ZM_WEB_INTEGRATION_ISOLATED", "");
    expect(() => realEnvironment("pos")).toThrow("run-web-integration.ps1");
    isolatedEnvironment();
    for (const url of [
      "https://production.example.test",
      "http://localhost:8000",
      "http://user:secret@127.0.0.1:41201",
      "http://127.0.0.1:41201?token=secret",
    ]) {
      vi.stubEnv("ZM_E2E_API_URL", url);
      expect(() => realEnvironment("pos")).toThrow("dedicated HTTP origin");
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
    const network = observeRealApi(context, page, "http://127.0.0.1:41201");
    expect(() => page.route()).toThrow("interception is forbidden");
    expect(() => context.routeFromHAR()).toThrow("interception is forbidden");
    responseListener?.({
      url: () => "http://127.0.0.1:41201/v1/admin/products?email=private&access_token=secret",
      status: () => 200,
      request: () => ({ method: () => "GET" }),
    });
    expect(network).toEqual([{ method: "GET", path: "/v1/admin/products", status: 200 }]);
  });
});
