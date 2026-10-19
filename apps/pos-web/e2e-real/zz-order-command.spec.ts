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
  const headers = { Origin: new URL(environment.baseUrl).origin, "X-ZeroMerma-Surface": "POS" };
  const summaryUrl = `${environment.apiUrl}/v1/cash-close/summary?workstation_code=${process.env.ZM_E2E_WORKSTATION_CODE!}`;
  const beforeResponse = await page.request.get(summaryUrl, { headers });
  expect(beforeResponse.status()).toBe(200);
  const before = (await beforeResponse.json()) as components["schemas"]["CashCloseSummaryResponse"];
  await page.goto("/pedidos");
  const other = await page.context().newPage();
  await other.goto(`${environment.baseUrl}/pedidos`);
  await page.bringToFront();
  await page.getByRole("button", { name: "Nuevo pedido", exact: true }).first().click();
  await page
    .getByPlaceholder("Nombre del cliente", { exact: true })
    .fill("Integration order customer");
  await page.getByPlaceholder("Telefono", { exact: true }).fill("6620000000");
  const deliveryDate = new Date(Date.now() + 3 * 86400000).toISOString().slice(0, 10);
  await page.getByLabel("Fecha de recoleccion").fill(deliveryDate);
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
  await expect(page.getByRole("dialog", { name: "Revisar pedido" })).toBeVisible();
  await page.getByRole("button", { name: "Confirmar pedido cotizado", exact: true }).click();
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
  await page.getByRole("button", { name: "Abonos y cambios", exact: true }).click();
  await page.getByRole("button", { name: "Modificar pedido", exact: true }).click();
  await page.getByLabel("Motivo de modificación").fill("Synthetic explicit commercial revision");
  await page.getByRole("button", { name: "Cotizar modificación", exact: true }).click();
  const amended = page.waitForResponse(
    (response) =>
      new URL(response.url()).pathname === `/v1/orders/${committed.id}/amend` &&
      response.request().method() === "POST",
  );
  await page.getByRole("button", { name: "Confirmar nueva versión", exact: true }).click();
  const amendedResponse = await amended;
  expect(amendedResponse.status()).toBe(200);
  expect(amendedResponse.request().headers()["idempotency-key"]).not.toBe(key);
  const amendedResult = await amendedResponse.json();
  expect(amendedResult.id).toBe(committed.id);
  expect(amendedResult.payments).toEqual(committed.payments);
  expect(amendedResult.status).toBe("PENDING");
  await page.getByRole("button", { name: "Cerrar seguimiento", exact: true }).click();
  await other.close();

  const detailResponse = await page.request.get(
    `${environment.apiUrl}/v1/orders/${committed.id}?workstation_code=${process.env.ZM_E2E_WORKSTATION_CODE!}`,
    { headers },
  );
  expect(detailResponse.status()).toBe(200);
  const detail =
    (await detailResponse.json()) as components["schemas"]["CustomerOrderDetailResponse"];
  expect(detail.payments).toHaveLength(1);
  expect(detail.version).toBe(2);
  expect(detail.can_mark_ready).toBe(false);
  expect(detail.payments[0]!.id).toBe(committed.payments[0]!.id);
  expect(detail.payments[0]!.financial_entry_id).toBeTruthy();
  expect(detail.payments[0]!.financial_operation_id).toBeTruthy();
  expect(detail.payments[0]!.cash_session_id).toBe(committed.payments[0]!.cash_session_id);
  const afterResponse = await page.request.get(summaryUrl, { headers });
  expect(afterResponse.status()).toBe(200);
  const after = (await afterResponse.json()) as components["schemas"]["CashCloseSummaryResponse"];
  const cents = (value: string) => Math.round(Number(value) * 100);
  expect(cents(after.expected_cash_amount) - cents(before.expected_cash_amount)).toBe(
    cents(committed.payments[0]!.amount),
  );
  expect(
    cents(after.cash_order_collections_amount) - cents(before.cash_order_collections_amount),
  ).toBe(cents(committed.payments[0]!.amount));

  const decisionPanel = page.locator('[data-pos-shell-region="right"]');
  await expect(
    decisionPanel.getByRole("heading", { name: "Entrega y cobro", exact: true }),
  ).toBeVisible();
  await decisionPanel.getByText("Pagos registrados (1)", { exact: true }).click();
  await decisionPanel.getByText("Referencias del pago y turno", { exact: true }).click();
  await expect(
    decisionPanel.getByText(`Asiento: ${detail.payments[0]!.financial_entry_id}`, { exact: true }),
  ).toBeVisible();
  await expect(
    decisionPanel.getByRole("button", { name: "Entregar pedido", exact: true }),
  ).toHaveCount(0);
  await page.goto("/cerrar-turno");
  await expect(page.getByRole("heading", { name: "Cierre de turno", exact: true })).toBeVisible();
  await page.getByRole("button", { name: "No sobró pan", exact: true }).click();
  await expect(page.getByLabel("Efectivo", { exact: true })).toBeVisible();
  await page.getByLabel("Efectivo", { exact: true }).fill(after.expected_cash_amount);
  const countedPreview = page.waitForResponse((response) => {
    if (
      new URL(response.url()).pathname !== "/v1/cash-close/preview" ||
      response.request().method() !== "POST"
    )
      return false;
    const body = response
      .request()
      .postDataJSON() as components["schemas"]["CashClosePreviewRequest"];
    return (
      body.counted_payment_methods?.some(
        (row) => row.payment_method_code === "CARD" && row.counted_amount === "60.00",
      ) ?? false
    );
  });
  await page.getByLabel("Tarjeta", { exact: true }).fill("60.00");
  const preview = await countedPreview;
  expect(preview.status()).toBe(200);
  expect((await preview.json()).cash_variance_amount).toBe("0.00");
  await expect(page.getByText("Cobros de pedidos en efectivo", { exact: true })).toBeVisible();
  const difference = page.getByText("Diferencia de efectivo", { exact: true }).locator("../..");
  await expect(difference.getByText("$0.00", { exact: true })).toBeVisible();
});
