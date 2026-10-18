import { createIdempotencyKey, type components } from "@zeromerma/api-client";
import { dropNextReturnConfirmationResponse } from "../../../scripts/dev/web-integration-support.mjs";
import { environment, expect, test } from "./fixtures";

test("real partial refund survives a lost response, reload and another tab and reconciles with backoffice", async ({
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
  const station = process.env.ZM_E2E_WORKSTATION_CODE ?? "POS-01";
  const headers = { Origin: new URL(environment.baseUrl).origin, "X-ZeroMerma-Surface": "POS" };
  const restored = await page.request.get(`${environment.apiUrl}/v1/auth/session`, { headers });
  expect(restored.status()).toBe(200);
  const session = (await restored.json()) as components["schemas"]["LoginResponse"];
  const current = await page.request.get(
    `${environment.apiUrl}/v1/cash-sessions/current?workstation_code=${station}`,
    { headers },
  );
  expect(current.status()).toBe(200);
  const cash = (await current.json()) as components["schemas"]["CashSessionView"];
  const catalogResponse = await page.request.get(
    `${environment.apiUrl}/v1/pos/catalog?workstation_code=${station}`,
    { headers },
  );
  expect(catalogResponse.status()).toBe(200);
  const catalog = (await catalogResponse.json()) as components["schemas"]["PosCatalogResponse"];
  const directClass = catalog.classes.find(
    (item) => item.capture_mode_default === "PRODUCT_DIRECT",
  )!;
  expect(directClass).toBeTruthy();
  const productResponse = await page.request.get(
    `${environment.apiUrl}/v1/pos/classes/${directClass.id}/products?workstation_code=${station}`,
    { headers },
  );
  expect(productResponse.status()).toBe(200);
  const product = (
    (await productResponse.json()) as components["schemas"]["PosClassProductsResponse"]
  ).products[0]!;
  const saleResponse = await page.request.post(`${environment.apiUrl}/v1/sales/confirm`, {
    headers: {
      ...headers,
      "X-CSRF-Token": session.csrf_token,
      "Idempotency-Key": createIdempotencyKey(),
    },
    data: {
      workstation_code: station,
      cash_session_id: cash.id,
      lines: [{ capture_mode: "PRODUCT_DIRECT", product_id: product.id, quantity: "3" }],
      payments: [{ payment_method_code: "CASH", tendered_amount: "1000.00" }],
    },
  });
  expect(saleResponse.status()).toBe(201);
  const sale = (await saleResponse.json()) as components["schemas"]["SaleConfirmationView"];
  await page.goto(`/devoluciones?saleId=${sale.id}`);
  const other = await page.context().newPage();
  await other.goto(`${environment.baseUrl}/devoluciones?saleId=${sale.id}`);
  for (const tab of [other, page]) {
    await tab.bringToFront();
    const quantityInput = tab.getByLabel(
      `Cantidad a devolver de ${sale.lines[0]!.catalog_name_snapshot}`,
    );
    await quantityInput.click();
    await expect(quantityInput).toBeFocused();
    await quantityInput.fill("1");
    await expect(quantityInput).toHaveValue("1");
    await tab.getByLabel("Motivo de devolucion").selectOption("WRONG_ITEM");
    await tab.getByLabel("Metodo de reembolso").selectOption("CASH");
    await expect(tab.getByLabel("Motivo de devolucion")).toHaveValue("WRONG_ITEM");
    await expect(tab.getByLabel("Metodo de reembolso")).toHaveValue("CASH");
    const acknowledgement = tab.getByLabel("Confirmo que la devolucion fue validada.");
    if (await acknowledgement.count()) await acknowledgement.check();
    await expect(
      tab.getByRole("button", { name: /^Confirmar devolucion(?:\s+Enter)?$/ }),
    ).toBeEnabled();
  }
  const fault = await dropNextReturnConfirmationResponse(page, environment.apiUrl, network);
  const outgoing = page.waitForRequest(
    (request) =>
      new URL(request.url()).pathname === "/v1/returns/commit" && request.method() === "POST",
  );
  await page.getByRole("button", { name: /^Confirmar devolucion(?:\s+Enter)?$/ }).click();
  const key = (await outgoing).headers()["idempotency-key"];
  const committed = (await fault.committed) as components["schemas"]["ReturnCommitResultView"];
  expect(committed.original_sale_id).toBe(sale.id);
  expect(committed.total_refund_amount).toBe(sale.lines[0]!.unit_price);
  expect(committed.refund_cash_movement_id).toBeTruthy();
  expect(committed).not.toHaveProperty("created_by");
  expect(committed).not.toHaveProperty("notes");
  for (const tab of [page, other])
    await expect(
      tab.getByRole("heading", { name: "Devolución pendiente de confirmar" }),
    ).toBeVisible();
  await expect(
    other.getByRole("button", { name: /^Confirmar devolucion(?:\s+Enter)?$/ }),
  ).toBeDisabled();
  await page.reload();
  await expect(
    page.getByRole("heading", { name: "Devolución pendiente de confirmar" }),
  ).toBeVisible();
  await expect(page.getByRole("button", { name: "Reintentar la misma devolución" })).toHaveCount(0);
  const resumedQuantity = page.getByLabel(
    `Cantidad a devolver de ${sale.lines[0]!.catalog_name_snapshot}`,
  );
  await resumedQuantity.click();
  await resumedQuantity.fill("1");
  await expect(resumedQuantity).toHaveValue("1");
  await page.getByLabel("Motivo de devolucion").selectOption("WRONG_ITEM");
  await expect(
    page.getByRole("button", { name: /^Confirmar devolucion(?:\s+Enter)?$/ }),
  ).toBeDisabled();
  const metadata = await page.evaluate(() =>
    Object.entries(localStorage)
      .filter(([name]) => name.startsWith("zeromerma-return-intention:"))
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
      "originalSaleId",
      "key",
      "payloadDigest",
      "status",
    ].sort(),
  );
  const recovered = page.waitForResponse(
    (response) => new URL(response.url()).pathname === `/v1/returns/confirmations/${key}`,
  );
  await page.getByRole("button", { name: "Consultar resultado de la devolución" }).click();
  const response = await recovered;
  expect(response.status()).toBe(200);
  expect(await response.json()).toEqual(committed);
  await expect(
    page.getByRole("button", { name: /^Confirmar devolucion(?:\s+Enter)?$/ }),
  ).toHaveCount(0);
  await expect(
    other.getByRole("heading", { name: "Devolución pendiente de confirmar" }),
  ).toHaveCount(0);
  await expect(
    other.getByRole("button", { name: /^Confirmar devolucion(?:\s+Enter)?$/ }),
  ).toHaveCount(0);
  expect(
    network.filter((item) => item.method === "POST" && item.path === "/v1/returns/commit"),
  ).toHaveLength(1);
  const saleDetailResponse = await page.request.get(
    `${environment.apiUrl}/v1/returns/sales/${sale.id}?workstation_code=${station}`,
    { headers },
  );
  expect(saleDetailResponse.status()).toBe(200);
  const detail =
    (await saleDetailResponse.json()) as components["schemas"]["ReturnOriginalSaleDetailResponse"];
  expect(detail.return_count).toBe(1);
  expect(detail.lines[0]!.already_refunded_amount).toBe(committed.total_refund_amount);
  expect(detail.lines[0]!.already_returned_quantity).toBe("1.000");
  const backofficeHeaders = {
    Origin: new URL(process.env.ZM_E2E_BACKOFFICE_URL!).origin,
    "X-ZeroMerma-Surface": "BACKOFFICE",
  };
  const adminLogin = await page.request.post(`${environment.apiUrl}/v1/auth/login`, {
    headers: backofficeHeaders,
    data: {
      email: process.env.ZM_E2E_ORDER_OPERATOR_EMAIL,
      password: environment.password,
      audience: "BACKOFFICE",
    },
  });
  expect(adminLogin.status()).toBe(200);
  const adminResponse = await page.request.get(
    `${environment.apiUrl}/v1/admin/returns-corrections/returns/${committed.id}`,
    { headers: backofficeHeaders },
  );
  expect(adminResponse.status()).toBe(200);
  const admin = (await adminResponse.json()) as components["schemas"]["AdminReturnDetailView"];
  expect(admin.refund_impact.linked_cash_movement_id).toBe(committed.refund_cash_movement_id);
  expect(admin.refund_impact.refund_amount).toBe(committed.total_refund_amount);
  await other.close();
});
