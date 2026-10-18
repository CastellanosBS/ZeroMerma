import { createIdempotencyKey, type components } from "@zeromerma/api-client";
import { dropNextOrderCommandResponse } from "../../../scripts/dev/web-integration-support.mjs";
import { environment, expect, test } from "./fixtures";

test("real administrative transition recovers a lost response after reload without repeating effects", async ({
  page,
  network,
}) => {
  const station = process.env.ZM_E2E_WORKSTATION_CODE ?? "POS-01";
  const posOrigin = new URL(process.env.ZM_E2E_POS_URL!).origin;
  const login = await page.request.post(`${environment.apiUrl}/v1/auth/login`, {
    headers: { Origin: posOrigin, "X-ZeroMerma-Surface": "POS" },
    data: {
      email: process.env.ZM_E2E_POS_EMAIL,
      password: environment.password,
      audience: "POS",
      workstation_code: station,
    },
  });
  expect(login.status()).toBe(200);
  const session = (await login.json()) as components["schemas"]["LoginResponse"];
  const headers = {
    Origin: posOrigin,
    "X-ZeroMerma-Surface": "POS",
    "X-CSRF-Token": session.csrf_token,
  };
  const current = await page.request.get(
    `${environment.apiUrl}/v1/cash-sessions/current?workstation_code=${station}`,
    { headers },
  );
  expect(current.status()).toBe(200);
  let cash = (await current.json()) as components["schemas"]["CashSessionView"] | null;
  if (!cash) {
    const opening = await page.request.post(`${environment.apiUrl}/v1/cash-sessions/open`, {
      headers: { ...headers, "Idempotency-Key": createIdempotencyKey() },
      data: { workstation_code: station, opening_amount: "0.00" },
    });
    expect(opening.ok()).toBe(true);
    cash = await opening.json();
  }
  const catalog = await page.request.get(
    `${environment.apiUrl}/v1/orders/catalog?workstation_code=${station}`,
    { headers },
  );
  expect(catalog.status()).toBe(200);
  const classes = (await catalog.json()) as components["schemas"]["OrdersCatalogResponse"];
  const productsResponse = await page.request.get(
    `${environment.apiUrl}/v1/orders/classes/${classes.classes[0]!.id}/products?workstation_code=${station}`,
    { headers },
  );
  expect(productsResponse.status()).toBe(200);
  const product = (
    (await productsResponse.json()) as components["schemas"]["OrdersClassProductsResponse"]
  ).products[0]!;
  const created = await page.request.post(`${environment.apiUrl}/v1/orders`, {
    headers: { ...headers, "Idempotency-Key": createIdempotencyKey() },
    data: {
      workstation_code: station,
      cash_session_id: cash!.id,
      customer_name: "Integration administrative order",
      customer_phone: "6620000001",
      requested_for_at: new Date(Date.now() + 86400000).toISOString(),
      items: [{ product_id: product.id, quantity: "1" }],
      advance_amount: product.unit_price,
      advance_payment_method_code: "CASH",
    },
  });
  expect(created.status()).toBe(201);
  const order = (await created.json()) as components["schemas"]["OrderCommandResultView"];

  await page.goto("/login");
  await page.getByLabel("Correo", { exact: true }).fill(process.env.ZM_E2E_ORDER_OPERATOR_EMAIL!);
  await page.getByLabel("Contraseña", { exact: true }).fill(environment.password);
  await page.getByRole("button", { name: "Entrar al backoffice" }).click();
  await expect(page).not.toHaveURL(/\/login$/);
  await page.goto("/admin/pedidos");
  await page
    .getByRole("article")
    .filter({ hasText: order.folio })
    .getByRole("button", { name: "Ver", exact: true })
    .click();
  const path = `/v1/admin/orders/${order.id}/mark-ready`;
  const fault = await dropNextOrderCommandResponse(page, environment.apiUrl, network, path);
  const outgoing = page.waitForRequest(
    (request) => new URL(request.url()).pathname === path && request.method() === "POST",
  );
  await page.getByRole("button", { name: "Marcar listo", exact: true }).click();
  const key = (await outgoing).headers()["idempotency-key"];
  const committed = (await fault.committed) as components["schemas"]["OrderCommandResultView"];
  expect(committed.id).toBe(order.id);
  expect(committed.status).toBe("READY");
  expect(committed.payments).toEqual(order.payments);
  await expect(page.getByRole("heading", { name: "Pedido pendiente de confirmar" })).toBeVisible();
  await page.reload();
  await expect(page.getByRole("heading", { name: "Pedido pendiente de confirmar" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Reintentar el mismo comando" })).toHaveCount(0);
  const recovered = page.waitForResponse(
    (response) =>
      new URL(response.url()).pathname === `/v1/admin/orders/commands/mark-ready/${key}`,
  );
  await page.getByRole("button", { name: "Consultar resultado del pedido" }).click();
  const result = await recovered;
  expect(result.status()).toBe(200);
  expect(await result.json()).toEqual(committed);
  expect(
    network.filter(
      (entry) => entry.method === "POST" && entry.path === "/v1/admin/orders/{id}/mark-ready",
    ),
  ).toHaveLength(1);
  await expect(page.getByRole("heading", { name: "Pedido pendiente de confirmar" })).toHaveCount(0);
  const metadata = await page.evaluate(() =>
    Object.entries(localStorage)
      .filter(([name]) => name.startsWith("zeromerma-admin-order-intention:"))
      .map(([, value]) => JSON.parse(value)),
  );
  expect(metadata).toHaveLength(1);
  expect(Object.keys(metadata[0]).sort()).toEqual(
    ["userId", "branchId", "orderId", "commandCode", "key", "payloadDigest", "status"].sort(),
  );
});
