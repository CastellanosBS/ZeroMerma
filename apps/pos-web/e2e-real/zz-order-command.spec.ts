import type { components } from "@zeromerma/api-client";
import { dropNextOrderCommandResponse } from "../../../scripts/dev/web-integration-support.mjs";
import { environment, expect, test } from "./fixtures";

test("real order advance survives a lost creation response, reload and a duplicate tab", async ({
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
  await page.goto("/pedidos");
  const other = await page.context().newPage();
  await other.goto(`${environment.baseUrl}/pedidos`);
  await page.bringToFront();
  await page.getByRole("button", { name: "Nuevo pedido", exact: true }).first().click();
  await page
    .getByPlaceholder("Nombre del cliente", { exact: true })
    .fill("Integration order customer");
  await page.getByPlaceholder("Telefono", { exact: true }).fill("6620000000");
  const tomorrow = new Date(Date.now() + 86400000).toISOString().slice(0, 10);
  await page.getByLabel("Fecha de recoleccion").fill(tomorrow);
  const catalog = page.waitForResponse((response) =>
    /\/v1\/orders\/classes\/[^/]+\/products$/.test(new URL(response.url()).pathname),
  );
  await page.getByRole("button", { name: /Pan dulce/ }).click();
  const products = (await (
    await catalog
  ).json()) as components["schemas"]["OrdersClassProductsResponse"];
  const product = products.products[0]!;
  await page.getByRole("button", { name: new RegExp(product.name) }).click();
  await page.getByLabel("Cantidad del pedido").fill("1");
  await page.getByLabel("Cantidad del pedido").press("Enter");
  await page.getByLabel("Anticipo del pedido").click();
  await page.getByLabel("Anticipo del pedido").fill(String(product.unit_price));
  const fault = await dropNextOrderCommandResponse(page, environment.apiUrl, network, "/v1/orders");
  const outgoing = page.waitForRequest(
    (request) => new URL(request.url()).pathname === "/v1/orders" && request.method() === "POST",
  );
  await page.getByRole("button", { name: /^Guardar pedido(?:\s+Enter)?$/ }).click();
  const request = await outgoing;
  const key = request.headers()["idempotency-key"];
  const committed = (await fault.committed) as components["schemas"]["OrderCommandResultView"];
  expect(committed.payments).toHaveLength(1);
  expect(committed.remaining_balance_amount).toBe("0.00");
  expect(committed).not.toHaveProperty("customer_name");
  for (const tab of [page, other])
    await expect(tab.getByRole("heading", { name: "Pedido pendiente de confirmar" })).toBeVisible();
  await page.reload();
  await expect(page.getByRole("heading", { name: "Pedido pendiente de confirmar" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Reintentar el mismo comando" })).toHaveCount(0);
  const metadata = await page.evaluate(() =>
    Object.entries(localStorage)
      .filter(([name]) => name.startsWith("zeromerma-order-intention:"))
      .map(([, value]) => JSON.parse(value)),
  );
  expect(metadata).toHaveLength(1);
  expect(metadata[0].key).toBe(key);
  expect(Object.keys(metadata[0]).sort()).toEqual(
    [
      "userId",
      "branchId",
      "workstationId",
      "workstationCode",
      "cashSessionId",
      "commandCode",
      "orderId",
      "key",
      "payloadDigest",
      "status",
    ].sort(),
  );
  const recovered = page.waitForResponse(
    (response) => new URL(response.url()).pathname === `/v1/orders/commands/create/${key}`,
  );
  await page.getByRole("button", { name: "Consultar resultado del pedido" }).click();
  const response = await recovered;
  expect(response.status()).toBe(200);
  expect(await response.json()).toEqual(committed);
  await expect(other.getByRole("heading", { name: "Pedido pendiente de confirmar" })).toHaveCount(
    0,
  );
  expect(
    network.filter((entry) => entry.method === "POST" && entry.path === "/v1/orders"),
  ).toHaveLength(1);
  await page.getByRole("row").filter({ hasText: committed.folio }).click();
  const ready = page.waitForResponse(
    (response) =>
      new URL(response.url()).pathname === `/v1/orders/${committed.id}/mark-ready` &&
      response.request().method() === "POST",
  );
  await page.getByRole("button", { name: "Marcar listo para entrega", exact: true }).click();
  const readyResponse = await ready;
  expect(readyResponse.status()).toBe(200);
  expect(readyResponse.request().headers()["idempotency-key"]).not.toBe(key);
  const readyResult = await readyResponse.json();
  expect(readyResult.id).toBe(committed.id);
  expect(readyResult.payments).toEqual(committed.payments);
  expect(readyResult.status).toBe("READY");
  await other.close();
});
