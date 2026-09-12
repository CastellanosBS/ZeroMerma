import { environment, expect, test } from "./fixtures";

const routes = [
  {
    family: "catalogCosts",
    path: "/admin/productos",
    heading: "Productos",
    api: "/v1/admin/products",
  },
  {
    family: "salesOrders",
    path: "/admin/ventas",
    heading: "Ventas / tickets",
    api: "/v1/admin/sales/tickets",
  },
  {
    family: "multibranchOperations",
    path: "/admin/sucursales",
    heading: "Sucursales",
    api: "/v1/admin/branches",
  },
  {
    family: "purchasesSupply",
    path: "/admin/proveedores",
    heading: "Proveedores",
    api: "/v1/admin/suppliers",
  },
  {
    family: "cashFinance",
    path: "/admin/cortes-caja",
    heading: "Cortes de caja",
    api: "/v1/admin/cash-cuts",
  },
  {
    family: "qualityHygiene",
    path: "/admin/incidencias",
    heading: "Incidencias",
    api: "/v1/admin/incidents",
  },
  { family: "control", path: "/admin/auditoria", heading: "Auditoria", api: "/v1/admin/audit" },
] as const;

test("real administrative login and read-only route in every released family", async ({
  page,
  network,
}, testInfo) => {
  await page.goto("/admin/productos");
  await expect(page).toHaveURL(/\/login$/);
  await page.getByLabel("Correo", { exact: true }).fill(environment.email);
  await page.getByLabel("Contraseña", { exact: true }).fill(environment.password);
  const login = page.waitForResponse(
    (response) =>
      response.url() === `${environment.apiUrl}/v1/auth/login` &&
      response.request().method() === "POST",
  );
  await page.getByRole("button", { name: "Entrar al backoffice" }).click();
  expect((await login).status()).toBe(200);
  await expect(page).toHaveURL(/\/admin\/productos$/);

  for (const route of routes) {
    await test.step(`read ${route.family}`, async () => {
      const read = page.waitForResponse(
        (response) =>
          new URL(response.url()).pathname === route.api && response.request().method() === "GET",
      );
      await page.goto(route.path);
      expect((await read).status()).toBe(200);
      await expect(
        page.getByRole("heading", { name: route.heading, exact: true, level: 2 }),
      ).toBeVisible();
      await expect(page).toHaveURL(`${environment.baseUrl}${route.path}`);
    });
  }
  const refresh = page.waitForResponse(
    (response) => new URL(response.url()).pathname === "/v1/admin/audit" && response.ok(),
  );
  await page.reload();
  expect((await refresh).status()).toBe(200);
  await expect(page.getByRole("heading", { name: "Auditoria", exact: true })).toBeVisible();
  expect(network.filter((entry) => entry.method !== "GET").map((entry) => entry.path)).toEqual([
    "/v1/auth/login",
  ]);
  await testInfo.attach("route-coverage", {
    body: JSON.stringify(routes, null, 2),
    contentType: "application/json",
  });
});

test("hidden placeholders redirect and never count as real family coverage", async ({
  page,
  network,
}) => {
  await page.goto("/login");
  await page.getByLabel("Correo", { exact: true }).fill(environment.email);
  await page.getByLabel("Contraseña", { exact: true }).fill(environment.password);
  await page.getByRole("button", { name: "Entrar al backoffice" }).click();
  await expect(page).toHaveURL(/\/admin\/productos$/);
  for (const path of ["/admin/dashboard", "/admin/alertas", "/admin/pagos-operativos"]) {
    await page.goto(path);
    await expect(page).toHaveURL(/\/admin\/productos$/);
    await expect(page.getByRole("heading", { name: "Productos", exact: true })).toBeVisible();
  }
  expect(network.some((entry) => /dashboard|alerts|operational-payments/.test(entry.path))).toBe(
    false,
  );
});

test("unauthenticated administrative reads are rejected and invalid session is cleared", async ({
  page,
  request,
}) => {
  expect((await request.get(`${environment.apiUrl}/v1/admin/products`)).status()).toBe(401);
  await page.goto("/login");
  await page.evaluate(() =>
    localStorage.setItem(
      "zeromerma-backoffice-auth",
      JSON.stringify({
        state: { accessToken: "expired-isolated-test-token" },
        version: 0,
      }),
    ),
  );
  await page.goto("/admin/productos");
  await expect(page).toHaveURL(/\/login$/);
});
