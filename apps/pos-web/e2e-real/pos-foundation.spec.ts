import type { SessionResponse } from "@zeromerma/api-client";
import { environment, expect, test } from "./fixtures";

test("real login, mandatory opening and persisted read state", async ({ page, network }) => {
  await page.goto("/pos");
  await expect(page).toHaveURL(/\/login$/);
  await page.getByLabel("Correo", { exact: true }).fill(environment.email);
  await page.getByLabel("Contrasena", { exact: true }).fill(environment.password);
  const login = page.waitForResponse(
    (response) =>
      response.url() === `${environment.apiUrl}/v1/auth/login` &&
      response.request().method() === "POST",
  );
  await page.getByRole("button", { name: "Entrar", exact: true }).click();
  const loginResponse = await login;
  expect(loginResponse.status()).toBe(200);
  const original: SessionResponse = await loginResponse.json();
  expect(original.session.audience).toBe("POS");
  expect(original.session.workstation_id).not.toBeNull();
  const cookies = await page.context().cookies(environment.apiUrl);
  expect(cookies.some(cookie => cookie.httpOnly && cookie.secure && cookie.sameSite === "Lax")).toBe(true);
  expect(await page.evaluate(() => localStorage.getItem("zeromerma-pos-auth"))).toBeNull();
  expect(await page.evaluate(() => document.cookie)).not.toContain("session");
  await expect(page).toHaveURL(/\/cash-session\/open$/);
  await expect(page.getByRole("heading", { name: "Registrar apertura" })).toBeVisible();

  await page.getByLabel("Monto de apertura").fill("0.00");
  const opening = page.waitForResponse(
    (response) =>
      response.url() === `${environment.apiUrl}/v1/cash-sessions/open` &&
      response.request().method() === "POST",
  );
  await page.getByRole("button", { name: "Abrir caja", exact: true }).click();
  expect((await opening).ok()).toBe(true);
  await expect(page).toHaveURL(/\/pos$/);
  await expect(page.getByRole("heading", { name: "Punto de venta", exact: true })).toBeVisible();

  const current = page
    .waitForEvent("framenavigated", (frame) => frame === page.mainFrame())
    .then(async () => {
      // Bind to a request from the reloaded document, not an earlier in-flight response.
      const request = await page.waitForRequest(
        (request) =>
          new URL(request.url()).pathname === "/v1/cash-sessions/current" &&
          request.method() === "GET",
      );
      const response = await request.response();
      if (!response) {
        throw new Error("The reloaded POS current-session request did not produce a response");
      }
      expect(response.status()).toBe(200);
      return response.json();
    });
  await page.reload();
  const session = await current;
  expect(session.status).toBe("OPEN");
  expect(session.opening_amount).toBe("0.00");
  await expect(page).toHaveURL(/\/pos$/);
  await expect
    .poll(() => network.some((entry) => entry.path === "/v1/pos/catalog" && entry.status === 200))
    .toBe(true);
  expect(network.filter((entry) => entry.method !== "GET" && entry.path !== "/v1/auth/activity").map((entry) => entry.path)).toEqual([
    "/v1/auth/login",
    "/v1/cash-sessions/open",
  ]);
  const lock = page.waitForResponse(response => new URL(response.url()).pathname === "/v1/auth/lock");
  await page.getByRole("button", { name: "Bloquear", exact: true }).click();
  expect((await lock).status()).toBe(200);
  await expect(page.getByRole("heading", { name: "Sesión bloqueada" })).toBeVisible();
  await page.reload();
  await expect(page.getByRole("heading", { name: "Sesión bloqueada" })).toBeVisible();
  const otherTab = await page.context().newPage();
  await otherTab.goto(`${environment.baseUrl}/pos`);
  await expect(otherTab.getByRole("heading", { name: "Sesión bloqueada" })).toBeVisible();
  await page.bringToFront();
  await page.getByLabel("Contraseña actual", { exact: true }).fill(environment.password);
  const unlock = page.waitForResponse(response => new URL(response.url()).pathname === "/v1/auth/reauthenticate");
  await page.getByRole("button", { name: "Desbloquear", exact: true }).click();
  const unlocked: SessionResponse = await (await unlock).json();
  expect(unlocked.session.id).toBe(original.session.id);
  expect(unlocked.session.absolute_expires_at).toBe(original.session.absolute_expires_at);
  expect(unlocked.csrf_token === original.csrf_token).toBe(false);
  await expect(page.getByRole("heading", { name: "Punto de venta", exact: true })).toBeVisible();
  const restoredOtherTab = otherTab.waitForResponse(response => new URL(response.url()).pathname === "/v1/auth/session");
  await otherTab.bringToFront();
  // Headless Chromium can keep both pages focused; deliver the focus notification explicitly.
  await otherTab.evaluate(() => window.dispatchEvent(new Event("focus")));
  const restored: SessionResponse = await (await restoredOtherTab).json();
  expect(restored.session.id).toBe(unlocked.session.id);
  expect(restored.csrf_token === unlocked.csrf_token).toBe(true);
  expect(restored.session.last_activity_at).toBe(unlocked.session.last_activity_at);
  expect(restored.session.idle_expires_at).toBe(unlocked.session.idle_expires_at);
  await expect(otherTab.getByRole("heading", { name: "Punto de venta", exact: true })).toBeVisible();
  await otherTab.close();
  await page.bringToFront();
  const logout = page.waitForResponse(response => new URL(response.url()).pathname === "/v1/auth/logout");
  await page.getByRole("button", { name: "Cerrar sesion", exact: true }).click();
  expect((await logout).status()).toBe(204);
  await expect(page).toHaveURL(/\/login$/);
  await page.goto("/pos");
  await expect(page).toHaveURL(/\/login$/);
});

test("unauthenticated API remains 401 and obsolete stored credential is ignored", async ({
  page,
  request,
}) => {
  const response = await request.get(`${environment.apiUrl}/v1/pos/bootstrap`, {
    headers: { "X-ZeroMerma-Surface": "POS", Origin: environment.baseUrl },
    params: { workstation_code: process.env.ZM_E2E_WORKSTATION_CODE ?? "POS-01" },
  });
  expect(response.status()).toBe(401);
  await page.goto("/login");
  await page.evaluate(() =>
    localStorage.setItem(
      "zeromerma-pos-auth",
      JSON.stringify({
        state: { accessToken: "expired-isolated-test-token" },
        version: 0,
      }),
    ),
  );
  await page.goto("/pos");
  await expect(page).toHaveURL(/\/login$/);
  expect(await page.evaluate(() => localStorage.getItem("zeromerma-pos-auth"))).toBeNull();
});
