import { createIdempotencyKey, type components } from "@zeromerma/api-client";
import { dropNextOrderCommandResponse } from "../../../scripts/dev/web-integration-support.mjs";
import { environment, expect, test } from "./fixtures";

test("real administrative transition recovers a lost response after reload without repeating effects", async ({
  page,
  network,
}) => {
  const station = process.env.ZM_E2E_ORDER_WORKSTATION_CODE!;
  const posOrigin = new URL(process.env.ZM_E2E_POS_URL!).origin;
  const login = await page.request.post(`${environment.apiUrl}/v1/auth/login`, {
    headers: { Origin: posOrigin, "X-ZeroMerma-Surface": "POS" },
    data: {
      email: process.env.ZM_E2E_ORDER_CASHIER_EMAIL,
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
  const summaryResponse = await page.request.get(
    `${environment.apiUrl}/v1/cash-close/summary?workstation_code=${station}`,
    { headers },
  );
  expect(summaryResponse.status()).toBe(200);
  const summary =
    (await summaryResponse.json()) as components["schemas"]["CashCloseSummaryResponse"];
  expect(summary.cash_order_collections_amount).toBe(order.payments[0]!.amount);
  const reconciliationResponse = await page.request.get(
    `${environment.apiUrl}/v1/cash-close/reconciliation?workstation_code=${station}`,
    { headers },
  );
  expect(reconciliationResponse.status()).toBe(200);
  const reconciliation =
    (await reconciliationResponse.json()) as components["schemas"]["CashCloseReconciliationResponse"];
  expect(reconciliation.pending_class_capture.has_pending_class_capture).toBe(false);
  // This isolated fixture shares the branch's stock with earlier real scenarios.
  // Preserve that stock using explicit counts and exercise the normal close validation.
  const closeBody: components["schemas"]["CashCloseCommitRequest"] = {
    workstation_code: station,
    cash_session_id: cash!.id,
    close_mode: "WITH_COUNT",
    counter_empty_confirmed: reconciliation.relevant_products.length === 0,
    counted_payment_methods: [
      { payment_method_code: "CASH", counted_amount: summary.expected_cash_amount },
    ],
    counted_product_lines: reconciliation.relevant_products.map((line) => ({
      product_id: line.product_id,
      counted_quantity: line.expected_quantity_before_deferred_attr,
    })),
  };
  const previewResponse = await page.request.post(`${environment.apiUrl}/v1/cash-close/preview`, {
    headers,
    data: closeBody,
  });
  expect(previewResponse.status()).toBe(200);
  const preview =
    (await previewResponse.json()) as components["schemas"]["CashClosePreviewResponse"];
  expect(preview.blockers).toEqual([]);
  expect(preview.reconciliation_status).toBe("READY");
  const closing = await page.request.post(`${environment.apiUrl}/v1/cash-close/commit`, {
    headers: { ...headers, "Idempotency-Key": createIdempotencyKey() },
    data: closeBody,
  });
  expect(closing.status()).toBe(200);
  const closed = (await closing.json()) as components["schemas"]["CashCloseCommitResultView"];
  expect(closed.cash_variance_amount).toBe("0.00");

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

  await page.goto("/admin/flujo-efectivo");
  const flowRead = page.waitForResponse((response) => {
    const url = new URL(response.url());
    return url.pathname === "/v1/admin/cash-flow" && url.searchParams.get("search") === order.folio;
  });
  await page.getByPlaceholder("Buscar folio, documento, categoria u operador").fill(order.folio);
  const flowResponse = await flowRead;
  expect(flowResponse.status()).toBe(200);
  const flow = (await flowResponse.json()) as components["schemas"]["AdminCashFlowListResponse"];
  expect(flow.items).toHaveLength(1);
  const movement = flow.items[0]!;
  expect(movement.source_type).toBe("ORDER_PAYMENT");
  expect(movement.order_payment_id).toBe(order.payments[0]!.id);
  expect(movement.amount).toBe(order.payments[0]!.amount);
  expect(flow.summary.order_collections_total).toBe(order.payments[0]!.amount);
  const movementRow = page.getByRole("row").filter({ hasText: order.folio });
  await expect(movementRow).toHaveCount(1);
  await movementRow.click();
  const flowDetail = page.getByRole("complementary").filter({
    has: page.getByRole("heading", { name: order.folio, exact: true }),
  });
  const sourceContext = flowDetail.locator("section").filter({
    has: page.getByRole("heading", { name: "Documento origen", exact: true }),
  });
  await sourceContext.getByText("Referencias financieras", { exact: true }).click();
  await expect(
    sourceContext.getByText(`Asiento: ${movement.financial_entry_id}`, { exact: true }),
  ).toBeVisible();
  await expect(sourceContext.getByText(`Turno: ${cash!.id}`, { exact: true })).toBeVisible();
  await expect(
    sourceContext.getByRole("link", { name: "Abrir origen", exact: true }),
  ).toHaveAttribute("href", `/admin/pedidos?order=${order.id}`);
  const cutRead = page.waitForResponse(
    (response) => new URL(response.url()).pathname === `/v1/admin/cash-cuts/${cash!.id}`,
  );
  await sourceContext.getByRole("link", { name: "Abrir corte", exact: true }).click();
  const cutResponse = await cutRead;
  expect(cutResponse.status()).toBe(200);
  const cut = (await cutResponse.json()) as components["schemas"]["AdminCashCutDetailView"];
  expect(cut.expected_vs_counted.expected_cash_amount).toBe(summary.expected_cash_amount);
  expect(cut.expected_vs_counted.cash_order_collections_amount).toBe(order.payments[0]!.amount);
  expect(cut.expected_vs_counted.difference_amount).toBe("0.00");
  expect(cut.order_payments).toHaveLength(1);
  expect(cut.order_payments[0]!.financial_entry_id).toBe(movement.financial_entry_id);
  const cutDetail = page.getByRole("complementary").filter({
    has: page.getByRole("heading", { name: cut.overview.folio, exact: true }),
  });
  const orderMovements = cutDetail.locator("section").filter({
    has: page.getByText("Movimientos de pedidos", { exact: true }),
  });
  await expect(orderMovements).toBeVisible();
  await orderMovements.getByText("Referencias del movimiento", { exact: true }).click();
  await expect(
    orderMovements.getByText(`Asiento: ${movement.financial_entry_id}`, { exact: true }),
  ).toBeVisible();
  const sourceRead = page.waitForResponse(
    (response) => new URL(response.url()).pathname === `/v1/admin/orders/${order.id}`,
  );
  await orderMovements.getByRole("link", { name: order.folio, exact: true }).click();
  const sourceResponse = await sourceRead;
  expect(sourceResponse.status()).toBe(200);
  const source = (await sourceResponse.json()) as components["schemas"]["AdminOrderDetailView"];
  expect(source.payments[0]!.financial_entry_id).toBe(movement.financial_entry_id);
  const orderDetail = page.getByRole("complementary").filter({
    has: page.getByRole("heading", { name: order.folio, exact: true }),
  });
  await orderDetail.getByText("Referencias del pago y turno", { exact: true }).click();
  await expect(
    orderDetail.getByText(`Pago: ${order.payments[0]!.id}`, { exact: true }),
  ).toBeVisible();
  await expect(
    orderDetail.getByText(`Asiento: ${movement.financial_entry_id}`, { exact: true }),
  ).toBeVisible();
});
