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
  expect((await login).status()).toBe(200);
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
  expect(network.filter((entry) => entry.method !== "GET").map((entry) => entry.path)).toEqual([
    "/v1/auth/login",
    "/v1/cash-sessions/open",
  ]);
});

test("unauthenticated API remains 401 and invalid session returns to login", async ({
  page,
  request,
}) => {
  const response = await request.get(`${environment.apiUrl}/v1/pos/bootstrap`, {
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
});
