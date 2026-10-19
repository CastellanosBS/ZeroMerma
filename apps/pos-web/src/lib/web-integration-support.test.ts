import { afterEach, describe, expect, it, vi } from "vitest";

import {
  dropNextSaleConfirmationResponse,
  dropNextReturnConfirmationResponse,
  dropNextOrderCommandResponse,
  dropNextCashCommandResponse,
  dropNextOperationalCommandResponse,
  observeRealApi,
  realEnvironment,
} from "../../../../scripts/dev/web-integration-support.mjs";

afterEach(() => vi.unstubAllEnvs());

function isolatedEnvironment() {
  vi.stubEnv("ZM_WEB_INTEGRATION_ISOLATED", "1");
  vi.stubEnv("ZM_E2E_RUN_ID", "guard-unit-test");
  vi.stubEnv("ZM_E2E_API_URL", "https://127.0.0.1:41201");
  vi.stubEnv("ZM_E2E_POS_URL", "https://127.0.0.1:41202");
  vi.stubEnv("ZM_E2E_BACKOFFICE_URL", "https://127.0.0.1:41203");
  vi.stubEnv("ZM_E2E_BACKOFFICE_EMAIL", "reader@example.test");
  vi.stubEnv("ZM_E2E_POS_EMAIL", "synthetic@example.test");
  vi.stubEnv("ZM_E2E_PASSWORD", "unit-only-password");
  vi.stubEnv("ZM_E2E_ARTIFACT_DIR", ".tmp/unit-web-guard");
}

describe("real browser integration safety", () => {
  it("restricts operational response loss to explicit mutations and rejects query overrides", async () => {
    isolatedEnvironment();
    const page = { on: vi.fn(), route: vi.fn() };
    const evidence = observeRealApi({ on: vi.fn() }, page, "https://127.0.0.1:41201");
    for (const path of [
      "/v1/auth/login",
      "/v1/admin/purchases?override=true",
      "/v1/admin/inventory",
      "/v1/admin/production/invalid/complete",
      "/v1/admin/suppliers",
      "/v1/returns/invalid/refund-settlements",
      "/v1/returns/019a0000-0000-7000-8000-000000000001/refund-settlements?override=true",
    ]) {
      await expect(
        dropNextOperationalCommandResponse(page, "https://127.0.0.1:41201", evidence, path),
      ).rejects.toThrow("allowlisted");
    }
    await expect(
      dropNextOperationalCommandResponse(
        page,
        "https://127.0.0.1:41201",
        evidence,
        "/v1/admin/purchases",
        "PATCH",
      ),
    ).rejects.toThrow("allowlisted");
  });
  it.each(["returns", "orders"])(
    "drops a real %s refund continuation response only after fetching the committed result",
    async (source) => {
      isolatedEnvironment();
      const route = {
        request: () => ({ method: () => "POST" }),
        fetch: vi.fn(async () => ({
          status: () => 200,
          json: async () => ({ amount_pending: "0.00" }),
        })),
        abort: vi.fn(async () => {}),
      };
      let handler: ((value: typeof route) => Promise<void>) | undefined;
      const page = {
        on: vi.fn(),
        route: vi.fn(async (_url: string, callback: typeof handler) => {
          handler = callback;
        }),
      };
      const evidence = observeRealApi({ on: vi.fn() }, page, "https://127.0.0.1:41201");
      const fault = await dropNextOperationalCommandResponse(
        page,
        "https://127.0.0.1:41201",
        evidence,
        `/v1/${source}/019a0000-0000-7000-8000-000000000001/refund-settlements`,
      );
      await handler!(route);
      await expect(fault.committed).resolves.toEqual({ amount_pending: "0.00" });
      expect(route.fetch).toHaveBeenCalledWith({ maxRedirects: 0 });
      expect(route.abort).toHaveBeenCalledWith("failed");
      expect(evidence).toEqual([
        { method: "POST", path: `/v1/${source}/{id}/refund-settlements`, status: 200 },
      ]);
    },
  );
  it.each([200, 409])(
    "drops an actual operational PATCH only after a successful commit (%i)",
    async (status) => {
      isolatedEnvironment();
      const route = {
        request: () => ({ method: () => "PATCH" }),
        fetch: vi.fn(async () => ({
          status: () => status,
          json: async () => ({ id: "document" }),
        })),
        abort: vi.fn(async () => {}),
      };
      let handler: ((value: typeof route) => Promise<void>) | undefined;
      const page = {
        on: vi.fn(),
        route: vi.fn(async (_url: string, callback: typeof handler) => {
          handler = callback;
        }),
      };
      const evidence = observeRealApi({ on: vi.fn() }, page, "https://127.0.0.1:41201");
      const fault = await dropNextOperationalCommandResponse(
        page,
        "https://127.0.0.1:41201",
        evidence,
        "/v1/admin/production/019a0000-0000-7000-8000-000000000001",
        "PATCH",
      );
      const outcome =
        status === 200
          ? expect(fault.committed).resolves.toEqual({ id: "document" })
          : expect(fault.committed).rejects.toThrow("received 409");
      await handler!(route);
      await outcome;
      expect(route.fetch).toHaveBeenCalledWith({ maxRedirects: 0 });
      expect(route.abort).toHaveBeenCalledWith("failed");
      expect(evidence).toEqual(
        status === 200 ? [{ method: "PATCH", path: "/v1/admin/production/{id}", status: 200 }] : [],
      );
    },
  );
  it("does not expose order response loss for arbitrary or administrative creation paths", async () => {
    isolatedEnvironment();
    const register = vi.fn();
    const page = { on: vi.fn(), route: register };
    const evidence = observeRealApi({ on: vi.fn() }, page, "https://127.0.0.1:41201");
    for (const path of [
      "/v1/auth/login",
      "/v1/admin/orders",
      "/v1/orders?override=true",
      "/v1/orders/anything/cancel",
    ]) {
      await expect(
        dropNextOrderCommandResponse(page, "https://127.0.0.1:41201", evidence, path),
      ).rejects.toThrow("allowlisted");
    }
    expect(register).not.toHaveBeenCalled();
  });
  it.each([200, 409])(
    "drops only a real successful order transition response, received %i",
    async (status) => {
      isolatedEnvironment();
      const route = {
        request: () => ({ method: () => "POST" }),
        fetch: vi.fn(async () => ({ status: () => status, json: async () => ({ id: "order" }) })),
        abort: vi.fn(async () => {}),
      };
      let handler: ((value: typeof route) => Promise<void>) | undefined;
      const register = vi.fn(async (_url: string, callback: typeof handler) => {
        handler = callback;
      });
      const page = { on: vi.fn(), route: register };
      const evidence = observeRealApi({ on: vi.fn() }, page, "https://127.0.0.1:41201");
      const path = "/v1/admin/orders/00000000-0000-4000-8000-000000000001/mark-ready";
      const fault = await dropNextOrderCommandResponse(
        page,
        "https://127.0.0.1:41201",
        evidence,
        path,
      );
      const outcome =
        status === 200
          ? expect(fault.committed).resolves.toEqual({ id: "order" })
          : expect(fault.committed).rejects.toThrow("received 409");
      await handler!(route);
      await outcome;
      expect(route.fetch).toHaveBeenCalledWith({ maxRedirects: 0 });
      expect(route.abort).toHaveBeenCalledWith("failed");
      expect(evidence).toEqual(
        status === 200
          ? [{ method: "POST", path: "/v1/admin/orders/{id}/mark-ready", status: 200 }]
          : [],
      );
    },
  );
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

  it.each([201, 409])(
    "loses a response only after the real return fetch and requires 201, received %i",
    async (status) => {
      isolatedEnvironment();
      const route = {
        request: () => ({ method: () => "POST" }),
        fetch: vi.fn(async () => ({ status: () => status, json: async () => ({ id: "return" }) })),
        abort: vi.fn(async () => {}),
      };
      let handler: ((value: typeof route) => Promise<void>) | undefined;
      const register = vi.fn(async (_url: string, callback: typeof handler) => {
        handler = callback;
      });
      const page = { on: vi.fn(), route: register };
      const network = observeRealApi({ on: vi.fn() }, page, "https://127.0.0.1:41201");
      const fault = await dropNextReturnConfirmationResponse(
        page,
        "https://127.0.0.1:41201",
        network,
      );
      const outcome =
        status === 201
          ? expect(fault.committed).resolves.toEqual({ id: "return" })
          : expect(fault.committed).rejects.toThrow("received 409");
      await handler!(route);
      await outcome;
      expect(register.mock.calls[0]?.[0]).toBe("https://127.0.0.1:41201/v1/returns/commit");
      expect(route.fetch).toHaveBeenCalledWith({ maxRedirects: 0 });
      expect(route.abort).toHaveBeenCalledWith("failed");
      expect(network).toEqual(
        status === 201 ? [{ method: "POST", path: "/v1/returns/commit", status: 201 }] : [],
      );
      expect(() => page.route("", undefined)).toThrow("interception is forbidden");
    },
  );

  it("limits cash faults to the four exact command paths", async () => {
    isolatedEnvironment();
    const register = vi.fn();
    const page = { on: vi.fn(), route: register };
    const evidence = observeRealApi({ on: vi.fn() }, page, "https://127.0.0.1:41201");
    for (const path of [
      "/v1/auth/login",
      "/v1/payments?unsafe=true",
      "/v1/cash-close/preview",
      "/v1/admin/cash-cuts",
    ]) {
      await expect(
        dropNextCashCommandResponse(page, "https://127.0.0.1:41201", evidence, path),
      ).rejects.toThrow("allowlisted");
    }
    expect(register).not.toHaveBeenCalled();
  });
  it.each([201, 409])(
    "records only a successful real cash transaction before dropping response %i",
    async (status) => {
      isolatedEnvironment();
      const route = {
        request: () => ({ method: () => "POST" }),
        fetch: vi.fn(async () => ({ status: () => status, json: async () => ({ id: "cash" }) })),
        abort: vi.fn(async () => {}),
      };
      let handler: ((value: typeof route) => Promise<void>) | undefined;
      const page = {
        on: vi.fn(),
        route: vi.fn(async (_url: string, callback: typeof handler) => {
          handler = callback;
        }),
      };
      const evidence = observeRealApi({ on: vi.fn() }, page, "https://127.0.0.1:41201");
      const fault = await dropNextCashCommandResponse(
        page,
        "https://127.0.0.1:41201",
        evidence,
        "/v1/cash-sessions/open",
      );
      const outcome =
        status === 201
          ? expect(fault.committed).resolves.toEqual({ id: "cash" })
          : expect(fault.committed).rejects.toThrow("received 409");
      await handler!(route);
      await outcome;
      expect(route.fetch).toHaveBeenCalledWith({ maxRedirects: 0 });
      expect(route.abort).toHaveBeenCalledWith("failed");
      expect(evidence).toEqual(
        status === 201 ? [{ method: "POST", path: "/v1/cash-sessions/open", status: 201 }] : [],
      );
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
