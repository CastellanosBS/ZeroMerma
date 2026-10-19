import { expect, test } from "@playwright/test";
import { installPosApiMocks } from "./helpers/pos-mocks";

const ready = { status: "READY", database: "READY", internet: "UNKNOWN", transactional_mode: "LOCAL_FIRST", browser_offline_mutations: false };

for (const viewport of [{ width: 800, height: 600 }, { width: 1366, height: 768 }, { width: 1920, height: 1080 }]) {
  test(`keyboard help contains focus and remains reachable at ${viewport.width}x${viewport.height}`, async ({ page }, testInfo) => {
    await page.setViewportSize(viewport);
    await installPosApiMocks(page, { authenticated: true, hasActiveCashSession: true });
    await page.goto("/pos");
    await expect(page.getByRole("heading", { name: "Punto de venta", exact: true })).toBeVisible();
    await page.keyboard.press("F1");
    const dialog = page.getByRole("dialog", { name: "Atajos del POS", exact: true });
    await expect(dialog).toBeVisible();
    await expect(dialog.getByRole("button", { name: "Cerrar", exact: true })).toBeFocused();
    await page.keyboard.press("Shift+Tab");
    await expect(dialog.getByRole("button", { name: "Volver al flujo" })).toBeFocused();
    await page.keyboard.press("Tab");
    await expect(dialog.getByRole("button", { name: "Cerrar", exact: true })).toBeFocused();
    await expect.poll(() => page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    await testInfo.attach(`keyboard-${viewport.width}x${viewport.height}`, {
      body: await page.screenshot(), contentType: "image/png",
    });
    await page.keyboard.press("Escape");
    await expect(dialog).toHaveCount(0);
  });
}

test("a browser Internet hint does not pause local cash opening", async ({ page }) => {
  await page.addInitScript(() => Object.defineProperty(navigator, "onLine", { get: () => false, configurable: true }));
  await installPosApiMocks(page, { authenticated: true, hasActiveCashSession: false });
  let openings = 0;
  page.on("request", request => { if (request.method() === "POST" && new URL(request.url()).pathname === "/v1/cash-sessions/open") openings += 1; });
  await page.goto("/cash-session/open");
  await expect(page.getByLabel("Conectividad del punto de venta")).toContainText("Servidor local disponible");
  await expect(page.getByLabel("Conectividad del punto de venta")).toContainText("El navegador informa un corte");
  await page.getByLabel("Monto de apertura").fill("100.00");
  await page.getByRole("button", { name: "Abrir caja", exact: true }).click();
  await expect(page).toHaveURL(/\/pos$/);
  expect(openings).toBe(1);
});

test("local database loss blocks admission and reconnect never posts the pending command", async ({ page }) => {
  await installPosApiMocks(page, { authenticated: true, hasActiveCashSession: false });
  let available = true;
  let openings = 0;
  let reads = 0;
  await page.route("**/ready", route => route.fulfill(available
    ? { json: ready }
    : { status: 503, json: { ...ready, status: "UNAVAILABLE", database: "UNAVAILABLE" } }));
  page.on("request", request => {
    const path = new URL(request.url()).pathname;
    if (request.method() === "POST" && path === "/v1/cash-sessions/open") openings += 1;
    if (request.method() === "GET" && path.startsWith("/v1/")) reads += 1;
  });
  await page.goto("/cash-session/open");
  await page.getByLabel("Monto de apertura").fill("100.00");
  available = false;
  await page.getByRole("button", { name: "Abrir caja", exact: true }).click();
  await expect(page.getByLabel("Conectividad del punto de venta")).toContainText("su base de datos no está disponible");
  await expect(page.getByText(/No se envió la operación:/).first()).toBeVisible();
  expect(openings).toBe(0);
  available = true;
  const readsBeforeReconnect = reads;
  await page.getByRole("button", { name: "Verificar conexión", exact: true }).click();
  await expect(page.getByLabel("Conectividad del punto de venta")).toContainText("Servidor local disponible");
  await expect.poll(() => reads).toBeGreaterThan(readsBeforeReconnect);
  expect(openings).toBe(0);
  await page.reload();
  await expect(page.getByRole("button", { name: "Consultar resultado de caja" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Reintentar la misma operación de caja" })).toHaveCount(0);
  expect(openings).toBe(0);
});
