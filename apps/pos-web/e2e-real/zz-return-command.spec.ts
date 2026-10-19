import { createIdempotencyKey, type components } from "@zeromerma/api-client";
import {
  dropNextOperationalCommandResponse,
  dropNextReturnConfirmationResponse,
} from "../../../scripts/dev/web-integration-support.mjs";
import { environment, expect, test } from "./fixtures";

test("real partial refund survives a lost response, reload and another tab and reconciles with backoffice", async ({
  page,
  network,
}) => {
  test.setTimeout(90_000);
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
  expect(product.is_inventory_tracked).toBe(true);
  expect(Number(product.available_quantity)).toBeGreaterThanOrEqual(4);
  await page
    .getByRole("button")
    .filter({ has: page.getByText(directClass.name, { exact: true }) })
    .click();
  const productCard = page
    .getByRole("button")
    .filter({ has: page.getByText(product.name, { exact: true }) });
  await expect(productCard).toContainText(`Disponible ${product.available_quantity}`);
  await expect(productCard).toContainText(`Reservado ${product.reserved_quantity}`);
  const saleResponse = await page.request.post(`${environment.apiUrl}/v1/sales/confirm`, {
    headers: {
      ...headers,
      "X-CSRF-Token": session.csrf_token,
      "Idempotency-Key": createIdempotencyKey(),
    },
    data: {
      workstation_code: station,
      cash_session_id: cash.id,
      lines: [{ capture_mode: "PRODUCT_DIRECT", product_id: product.id, quantity: "3",
        expected_unit_price: product.unit_price, expected_currency_code: product.currency_code }],
      payments: [{ payment_method_code: "CASH", tendered_amount: "1000.00" }],
    } satisfies components["schemas"]["ConfirmSaleRequest"],
  });
  expect(saleResponse.status()).toBe(201);
  const sale = (await saleResponse.json()) as components["schemas"]["SaleConfirmationView"];
  const summaryResponse = await page.request.get(
    `${environment.apiUrl}/v1/cash-close/summary?workstation_code=${station}`,
    { headers },
  );
  expect(summaryResponse.status()).toBe(200);
  const summary =
    (await summaryResponse.json()) as components["schemas"]["CashCloseSummaryResponse"];
  const availableCents = Math.round(Number(summary.expected_cash_amount) * 100);
  expect(availableCents).toBeGreaterThan(1);
  expect(Number(sale.lines[0]!.unit_price)).toBeGreaterThan(0.01);
  // A real operational outflow leaves only one cent available for CASH_FIRST.
  const outflow = await page.request.post(`${environment.apiUrl}/v1/payments`, {
    headers: {
      ...headers,
      "X-CSRF-Token": session.csrf_token,
      "Idempotency-Key": createIdempotencyKey(),
    },
    data: {
      workstation_code: station,
      cash_session_id: cash.id,
      payee_name: "Integration supplier",
      concept: "Refund capacity acceptance fixture",
      category_code: "SUPPLIER",
      payment_method_code: "CASH",
      total_amount: ((availableCents - 1) / 100).toFixed(2),
    } satisfies components["schemas"]["CreateOperationalPaymentRequest"],
  });
  expect(outflow.status()).toBe(201);
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
    const allocations = tab.getByRole("region", {
      name: `Disposiciones de ${sale.lines[0]!.catalog_name_snapshot}`,
      exact: true,
    });
    await allocations.getByRole("button", { name: "Dividir destino físico", exact: true }).click();
    await allocations.getByLabel("Cantidad de disposición 1", { exact: true }).fill("0.4");
    await allocations.getByLabel("Cantidad de disposición 2", { exact: true }).fill("0.6");
    await allocations
      .getByLabel("Destino de disposición 2", { exact: true })
      .selectOption("SEND_TO_WASTE");
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
  expect(committed.refund_cash_movement_id).toBeNull();
  expect(committed.lines).toHaveLength(1);
  expect(committed.lines[0]!.allocations).toHaveLength(2);
  expect(
    committed.lines[0]!.allocations.map((allocation) => ({
      ...allocation,
      quantity: Number(allocation.quantity),
    })),
  ).toEqual(
    expect.arrayContaining([
      expect.objectContaining({ quantity: 0.4, disposition_code: "QUARANTINE" }),
      expect.objectContaining({ quantity: 0.6, disposition_code: "SEND_TO_WASTE" }),
    ]),
  );
  const refund = committed.financial_refund!;
  expect(refund.amount_due).toBe(committed.total_refund_amount);
  expect(refund.amount_settled).toBe("0.01");
  expect(refund.amount_pending).toBe((Number(refund.amount_due) - 0.01).toFixed(2));
  expect(refund.state).toBe("PARTIALLY_SETTLED");
  expect(refund.entries).toHaveLength(1);
  expect(refund.entries[0]).toMatchObject({
    payment_method_code: "CASH",
    state: "CONFIRMED",
    amount: "0.01",
    cash_session_id: cash.id,
  });
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
  await page
    .getByRole("table", { name: "Historial de devoluciones", exact: true })
    .getByRole("row")
    .filter({ hasText: committed.folio })
    .click();
  const refundPanel = page.getByRole("region", { name: "Estado del reembolso", exact: true });
  await expect(refundPanel).toContainText("Entrega confirmada: $0.01");
  await expect(refundPanel).toContainText(`Pendiente de entregar: $${refund.amount_pending}`);
  // A later real collection makes the remainder payable in this drawer.
  const replenished = await page.request.post(`${environment.apiUrl}/v1/sales/confirm`, {
    headers: {
      ...headers,
      "X-CSRF-Token": session.csrf_token,
      "Idempotency-Key": createIdempotencyKey(),
    },
    data: {
      workstation_code: station,
      cash_session_id: cash.id,
      lines: [{ capture_mode: "PRODUCT_DIRECT", product_id: product.id, quantity: "1",
        expected_unit_price: product.unit_price, expected_currency_code: product.currency_code }],
      payments: [{ payment_method_code: "CASH", tendered_amount: "1000.00" }],
    } satisfies components["schemas"]["ConfirmSaleRequest"],
  });
  expect(replenished.status()).toBe(201);
  const settlementPath = `/v1/returns/${committed.id}/refund-settlements`;
  const settlementFault = await dropNextOperationalCommandResponse(
    page,
    environment.apiUrl,
    network,
    settlementPath,
  );
  const settlementRequest = page.waitForRequest(
    (request) => new URL(request.url()).pathname === settlementPath && request.method() === "POST",
  );
  await refundPanel.getByRole("button", { name: "Continuar reembolso en efectivo" }).click();
  const settlementKey = (await settlementRequest).headers()["idempotency-key"];
  const settled = (await settlementFault.committed) as components["schemas"]["FinancialRefundView"];
  expect(settled.financial_operation_id).toBe(refund.financial_operation_id);
  expect(settled.amount_settled).toBe(refund.amount_due);
  expect(settled.amount_pending).toBe("0.00");
  expect(settled.entries).toHaveLength(2);
  expect(settled.entries[0]).toEqual(refund.entries[0]);
  expect(settled.entries[1]).toMatchObject({
    payment_method_code: "CASH",
    amount: refund.amount_pending,
    state: "CONFIRMED",
    cash_session_id: cash.id,
  });
  await expect(
    page.getByRole("heading", { name: "Entrega de reembolso por verificar" }),
  ).toBeVisible();
  await page.reload();
  await expect(page.getByRole("button", { name: "Reintentar la misma entrega" })).toHaveCount(0);
  const settlementRecovery = page.waitForResponse(
    (response) =>
      new URL(response.url()).pathname === `/v1/returns/refund-settlements/${settlementKey}`,
  );
  await page.getByRole("button", { name: "Consultar entrega de reembolso", exact: true }).click();
  const recoveredSettlement = await settlementRecovery;
  expect(recoveredSettlement.status()).toBe(200);
  expect(await recoveredSettlement.json()).toEqual(settled);
  await expect(
    page.getByRole("heading", { name: "Entrega de reembolso por verificar" }),
  ).toHaveCount(0);
  expect(
    network.filter(
      (item) => item.method === "POST" && item.path === "/v1/returns/{id}/refund-settlements",
    ),
  ).toHaveLength(1);
  const historyTable = page.getByRole("table", { name: "Historial de devoluciones", exact: true });
  const historyNavigation = page.getByRole("button", { name: "Ver historial", exact: true });
  // Recovery can already return the screen to history when its saved return identity loads.
  await expect(historyTable.or(historyNavigation)).toBeVisible();
  if (!(await historyTable.isVisible())) await historyNavigation.click();
  await historyTable.getByRole("row").filter({ hasText: committed.folio }).click();
  await expect(refundPanel).toContainText(`Entrega confirmada: $${refund.amount_due}`);
  await expect(refundPanel).toContainText("Pendiente de entregar: $0.00");
  await expect(
    refundPanel.getByRole("button", { name: "Continuar reembolso en efectivo" }),
  ).toHaveCount(0);
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
  expect(admin.refund_impact.cash_impact_amount).toBe(refund.amount_due);
  expect(admin.financial_refund).toEqual(settled);
  expect(admin.returned_lines).toHaveLength(1);
  expect(
    admin.returned_lines[0]!.allocations.map((allocation) => ({
      ...allocation,
      quantity: Number(allocation.quantity),
    })),
  ).toEqual(
    committed.lines[0]!.allocations.map((allocation) => ({
      ...allocation,
      quantity: Number(allocation.quantity),
    })),
  );

  // Quarantined stock is not saleable. Its physical disposal is a separate,
  // recoverable command and cannot change the already settled refund.
  const operationsLogin = await page.request.post(`${environment.apiUrl}/v1/auth/login`, {
    headers: backofficeHeaders,
    data: {
      email: process.env.ZM_E2E_OPERATIONS_OPERATOR_EMAIL,
      password: environment.password,
      audience: "BACKOFFICE",
    },
  });
  expect(operationsLogin.status()).toBe(200);
  const adminPage = await page.context().newPage();
  await adminPage.goto(
    `${process.env.ZM_E2E_BACKOFFICE_URL}/admin/inventario?branchId=${committed.branch_id}`,
  );
  await adminPage.getByPlaceholder("Buscar producto, codigo, clase o sucursal").fill(product.code);
  await adminPage.getByRole("button", { name: /^Abrir filtros/ }).click();
  const filters = adminPage.getByRole("dialog", { name: "Filtros", exact: true });
  await expect(filters).toBeVisible();
  await filters.getByLabel(/^Ubicacion/).selectOption("QUARANTINE");
  await filters.getByRole("button", { name: "Cerrar", exact: true }).click();
  await adminPage
    .getByRole("button", { name: `${product.name} ${product.code}`, exact: true })
    .click();
  const disposal = adminPage.locator("details").filter({
    has: adminPage.getByText("Resolver producto en cuarentena", { exact: true }),
  });
  await disposal.getByText("Resolver producto en cuarentena", { exact: true }).click();
  await disposal.getByLabel("Cantidad a disponer", { exact: true }).fill("0.4");
  await disposal.getByLabel("Destino fisico", { exact: true }).selectOption("WASTE");
  const lotSelect = disposal.getByLabel("Lote fisico", { exact: true });
  if (await lotSelect.count()) {
    const quarantine = committed.lines[0]!.allocations.find(
      (allocation) => allocation.disposition_code === "QUARANTINE",
    )!;
    expect(quarantine.lot_id).toBeTruthy();
    await lotSelect.selectOption(quarantine.lot_id!);
  }
  await disposal
    .getByLabel("Motivo de disposicion", { exact: true })
    .fill("Returned product physically disposed after inspection");
  const disposalPath = "/v1/admin/inventory-dispositions";
  const disposalFault = await dropNextOperationalCommandResponse(
    adminPage,
    environment.apiUrl,
    network,
    disposalPath,
  );
  await disposal.getByRole("button", { name: "Confirmar disposicion fisica", exact: true }).click();
  const disposed =
    (await disposalFault.committed) as components["schemas"]["InventoryDispositionResult"];
  expect(disposed).toMatchObject({
    branch_id: committed.branch_id,
    product_id: product.id,
    kind: "QUARANTINE_RELEASE",
    source: "QUARANTINE",
    destination: "WASTE",
  });
  expect(Number(disposed.quantity)).toBe(0.4);
  expect(disposed.movement_ids).toHaveLength(2);
  await expect(
    adminPage.getByRole("heading", { name: "Disposicion fisica pendiente de confirmar" }),
  ).toBeVisible();
  await adminPage.reload();
  await expect(
    adminPage.getByRole("button", { name: "Reintentar la misma disposicion" }),
  ).toHaveCount(0);
  const disposalRecovery = adminPage.waitForResponse((response) =>
    new URL(response.url()).pathname.startsWith(`${disposalPath}/confirmations/`),
  );
  await adminPage
    .getByRole("button", { name: "Consultar disposicion fisica", exact: true })
    .click();
  expect(await (await disposalRecovery).json()).toEqual(disposed);
  expect(
    network.filter((entry) => entry.method === "POST" && entry.path === disposalPath),
  ).toHaveLength(1);
  const remainingResponse = await page.request.get(
    `${environment.apiUrl}/v1/pos/classes/${directClass.id}/products?workstation_code=${station}`,
    { headers },
  );
  expect(remainingResponse.status()).toBe(200);
  const remaining = (
    (await remainingResponse.json()) as components["schemas"]["PosClassProductsResponse"]
  ).products.find((item) => item.id === product.id)!;
  expect(Number(remaining.available_quantity)).toBe(Number(product.available_quantity) - 4);
  const unchangedRefundResponse = await page.request.get(
    `${environment.apiUrl}/v1/returns/${committed.id}?workstation_code=${station}`,
    { headers },
  );
  expect(unchangedRefundResponse.status()).toBe(200);
  const unchangedReturn =
    (await unchangedRefundResponse.json()) as components["schemas"]["SaleReturnDetailResponse"];
  expect(unchangedReturn.financial_refund).toEqual(settled);
  await adminPage.close();
  await other.close();
});
