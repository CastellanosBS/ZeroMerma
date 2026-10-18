import type { components } from "@zeromerma/api-client";
import { dropNextSaleConfirmationResponse } from "../../../scripts/dev/web-integration-support.mjs";
import { environment, expect, test } from "./fixtures";

test("lost committed sale response recovers after reload and another tab cannot repeat the checkout", async ({
  page,
  network,
}) => {
  await page.goto("/login");
  await page.getByLabel("Correo", { exact: true }).fill(environment.email);
  await page.getByLabel("Contrasena", { exact: true }).fill(environment.password);
  await page.getByRole("button", { name: "Entrar", exact: true }).click();
  await expect(page).toHaveURL(/\/(pos|cash-session\/open)$/);
  if (new URL(page.url()).pathname === "/cash-session/open") {
    await page.getByLabel("Monto de apertura").fill("0.00");
    await page.getByRole("button", { name: "Abrir caja", exact: true }).click();
  }
  await expect(page).toHaveURL(/\/pos$/);

  const otherTab = await page.context().newPage();
  const pageErrors: string[] = [];
  for (const tab of [page, otherTab])
    tab.on("pageerror", (error) => pageErrors.push(error.message));
  await otherTab.goto(`${environment.baseUrl}/pos`);
  await expect(
    otherTab.getByRole("heading", { name: "Punto de venta", exact: true }),
  ).toBeVisible();
  for (const tab of [otherTab, page]) {
    await tab.bringToFront();
    await tab.getByRole("button", { name: /Pan dulce/ }).click();
    await tab.getByRole("textbox", { name: "Cantidad", exact: true }).fill("1");
    await tab.getByRole("button", { name: "Agregar", exact: true }).click();
    await tab.getByLabel("Dinero recibido").click();
    await expect(tab.getByLabel("Dinero recibido")).toBeFocused();
    await tab.getByLabel("Dinero recibido").fill("100");
    await expect(tab.getByLabel("Dinero recibido")).toHaveValue("100");
    expect(pageErrors).toEqual([]);
    await expect(tab.getByRole("button", { name: /^Cobrar(?:\s+Enter)?$/ })).toBeEnabled();
    await tab.getByRole("button", { name: /^Cobrar(?:\s+Enter)?$/ }).click();
    expect(pageErrors).toEqual([]);
    await expect(tab.getByRole("button", { name: /^Cobrar(?:\s+Enter)?$/ })).toBeEnabled();
  }
  const post = page.waitForRequest(
    (request) =>
      new URL(request.url()).pathname === "/v1/sales/confirm" && request.method() === "POST",
  );
  const fault = await dropNextSaleConfirmationResponse(page, environment.apiUrl, network);
  await page.getByRole("button", { name: /^Cobrar(?:\s+Enter)?$/ }).click();
  const originalRequest = await post;
  const committed = (await fault.committed) as components["schemas"]["SaleConfirmationView"];
  const key = originalRequest.headers()["idempotency-key"];
  expect(key).toMatch(/^[0-9a-f]{8}-[0-9a-f]{4}-7[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/);
  expect(committed.cash_session_id).toBe(originalRequest.postDataJSON().cash_session_id);
  expect(committed).not.toHaveProperty("operator_email");
  expect(committed).not.toHaveProperty("operator_full_name");
  await expect(page.getByRole("heading", { name: "Resultado de venta pendiente" })).toBeVisible();
  await expect(
    otherTab.getByRole("heading", { name: "Resultado de venta pendiente" }),
  ).toBeVisible();
  await expect(otherTab.getByRole("button", { name: /^Cobrar(?:\s+Enter)?$/ })).toHaveCount(0);

  await page.reload();
  await expect(page.getByRole("heading", { name: "Resultado de venta pendiente" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Reintentar misma venta" })).toHaveCount(0);
  const stored = await page.evaluate(() =>
    Object.entries(localStorage)
      .filter(([name]) => name.startsWith("zeromerma-sale-intention:"))
      .map(([, value]) => JSON.parse(value)),
  );
  expect(stored).toHaveLength(1);
  expect(Object.keys(stored[0]).sort()).toEqual(
    [
      "key",
      "userId",
      "branchId",
      "workstationId",
      "workstationCode",
      "cashSessionId",
      "payloadDigest",
      "status",
    ].sort(),
  );
  expect(stored[0].key).toBe(key);
  const recovered = page.waitForResponse(
    (response) => new URL(response.url()).pathname === `/v1/sales/confirmations/${key}`,
  );
  await page.getByRole("button", { name: "Recuperar venta", exact: true }).click();
  const recoveryResponse = await recovered;
  expect(recoveryResponse.status()).toBe(200);
  expect(await recoveryResponse.json()).toEqual(committed);
  await expect(
    page.getByText(
      "El ticket esta vacio. Agrega productos desde el catalogo para empezar la venta.",
    ),
  ).toBeVisible();
  await expect(
    otherTab.getByText(
      "El ticket esta vacio. Agrega productos desde el catalogo para empezar la venta.",
    ),
  ).toBeVisible();
  expect(
    network.filter((entry) => entry.method === "POST" && entry.path === "/v1/sales/confirm"),
  ).toHaveLength(1);

  // A second, deliberate sale with the same cart has a different identity and domain document.
  await page.getByRole("button", { name: /Pan dulce/ }).click();
  await page.getByRole("textbox", { name: "Cantidad", exact: true }).fill("1");
  await page.getByRole("button", { name: "Agregar", exact: true }).click();
  await page.getByLabel("Dinero recibido").click();
  await page.getByLabel("Dinero recibido").fill("100");
  await page.getByLabel("Dinero recibido").press("Enter");
  const next = page.waitForResponse(
    (response) =>
      new URL(response.url()).pathname === "/v1/sales/confirm" &&
      response.request().method() === "POST",
  );
  await page.getByRole("button", { name: /^Cobrar(?:\s+Enter)?$/ }).click();
  const nextResponse = await next;
  expect(nextResponse.status()).toBe(201);
  expect(nextResponse.request().headers()["idempotency-key"]).not.toBe(key);
  expect((await nextResponse.json()).id).not.toBe(committed.id);
  await otherTab.close();
});
