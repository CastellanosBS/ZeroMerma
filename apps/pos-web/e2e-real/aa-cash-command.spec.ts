import { createIdempotencyKey, type components } from "@zeromerma/api-client";
import { dropNextCashCommandResponse } from "../../../scripts/dev/web-integration-support.mjs";
import { environment, expect, test } from "./fixtures";

test("real cash opening, outflow and close recover lost responses across reload and renewed login", async ({
  page,
  network,
}) => {
  const station = process.env.ZM_E2E_WORKSTATION_CODE ?? "POS-01";
  const headers = { Origin: new URL(environment.baseUrl).origin, "X-ZeroMerma-Surface": "POS" };
  async function login() {
    await page.goto("/login");
    await page.getByLabel("Correo", { exact: true }).fill(environment.email);
    await page.getByLabel("Contrasena", { exact: true }).fill(environment.password);
    await page.getByRole("button", { name: "Entrar", exact: true }).click();
    await expect(page).toHaveURL(/\/(pos|cash-session\/open)$/);
  }
  async function recover(path: string, expectedId: string) {
    const response = page.waitForResponse(
      (response) => new URL(response.url()).pathname.startsWith(path) && response.status() === 200,
    );
    await page.getByRole("button", { name: "Consultar resultado de caja", exact: true }).click();
    const snapshot = await (await response).json();
    expect(snapshot.id).toBe(expectedId);
    await expect(
      page.getByRole("heading", { name: "Operación de caja pendiente de confirmar" }),
    ).toHaveCount(0);
    return snapshot;
  }
  await login();
  await expect(page).toHaveURL(/\/cash-session\/open$/);
  const other = await page.context().newPage();
  await other.goto(`${environment.baseUrl}/cash-session/open`);
  await other.getByLabel("Monto de apertura").fill("500.00");
  await page.bringToFront();
  await page.getByLabel("Monto de apertura").fill("0.00");
  const openingFault = await dropNextCashCommandResponse(
    page,
    environment.apiUrl,
    network,
    "/v1/cash-sessions/open",
  );
  await page.getByRole("button", { name: "Abrir caja", exact: true }).click();
  const opened =
    (await openingFault.committed) as components["schemas"]["CashSessionOpenResultView"];
  expect(opened.opening_amount).toBe("0.00");
  await expect(
    other.getByRole("heading", { name: "Operación de caja pendiente de confirmar" }),
  ).toBeVisible();
  await expect(
    other.getByRole("button", { name: "Abrir caja", exact: true }).and(other.locator(":enabled")),
  ).toHaveCount(0);
  await page.reload();
  await expect(
    page.getByRole("heading", { name: "Operación de caja pendiente de confirmar" }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Reintentar la misma operación de caja" }),
  ).toHaveCount(0);
  await recover("/v1/cash-sessions/confirmations/", opened.id);
  await other.close();
  await page.goto("/pagos");
  await page.getByRole("button", { name: /^Nuevo pago/ }).click();
  await page.getByLabel("Beneficiario del pago").fill("Integration supplier");
  await page.getByLabel("Categoria del pago").selectOption("SUPPLIER");
  await page.getByLabel("Referencia del pago").fill("Integration cash outflow");
  await page.getByLabel("Monto del pago").fill("10.00");
  await page.getByRole("button", { name: /^Efectivo/ }).click();
  const paymentFault = await dropNextCashCommandResponse(
    page,
    environment.apiUrl,
    network,
    "/v1/payments",
  );
  await page.getByRole("button", { name: /^Guardar pago/ }).click();
  await page.getByRole("button", { name: "Confirmar pago", exact: true }).click();
  const paid =
    (await paymentFault.committed) as components["schemas"]["OperationalPaymentCommitResultView"];
  expect(paid.cash_session_id).toBe(opened.id);
  expect(paid.cash_movement_id).toBeNull();
  await page.reload();
  const payment = await recover("/v1/payments/confirmations/", paid.id);
  expect(payment.cash_movement_id).toBe(paid.cash_movement_id);
  const stored = await page.evaluate(() =>
    Object.entries(localStorage)
      .filter(([key]) => key.startsWith("zeromerma-cash-intention:"))
      .map(([, value]) => JSON.parse(value)),
  );
  expect(Object.keys(stored[0]).sort()).toEqual(
    [
      "branchId",
      "cashSessionId",
      "commandCode",
      "key",
      "payloadDigest",
      "status",
      "userId",
      "workstationCode",
      "workstationId",
    ].sort(),
  );
  expect(stored[0].cashSessionId).toBe(opened.id);

  // Operational discounts remain hidden in navigation. Exercise the existing inflow API,
  // without pretending this is acceptance of the paused discounts UI.
  const sessionResponse = await page.request.get(`${environment.apiUrl}/v1/auth/session`, {
    headers,
  });
  expect(sessionResponse.status()).toBe(200);
  const session = (await sessionResponse.json()) as components["schemas"]["LoginResponse"];
  const discountKey = createIdempotencyKey();
  const discountBody: components["schemas"]["CreateOperationalDiscountRequest"] = {
    workstation_code: station,
    cash_session_id: opened.id,
    subject_name: "Integration operator",
    concept: "Integration cash inflow",
    total_amount: "20.00",
    payment_method_code: "CASH",
    high_value_acknowledged: false,
  };
  const discountHeaders = {
    ...headers,
    "X-CSRF-Token": session.csrf_token,
    "Idempotency-Key": discountKey,
  };
  const inflow = await page.request.post(`${environment.apiUrl}/v1/discounts`, {
    headers: discountHeaders,
    data: discountBody,
  });
  expect(inflow.status()).toBe(201);
  const discount =
    (await inflow.json()) as components["schemas"]["OperationalDiscountCommitResultView"];
  const repeated = await page.request.post(`${environment.apiUrl}/v1/discounts`, {
    headers: discountHeaders,
    data: discountBody,
  });
  expect(repeated.status()).toBe(201);
  expect(repeated.headers()["idempotency-replayed"]).toBe("true");
  expect(await repeated.json()).toEqual(discount);
  expect(discount.cash_movement_id).toBeNull();
  const restoredDiscount = await page.request.get(
    `${environment.apiUrl}/v1/discounts/confirmations/${discountKey}?workstation_code=${station}&cash_session_id=${opened.id}`,
    { headers },
  );
  expect(restoredDiscount.status()).toBe(200);
  expect(await restoredDiscount.json()).toEqual(discount);

  const reconciliationResponse = await page.request.get(
    `${environment.apiUrl}/v1/cash-close/reconciliation?workstation_code=${station}`,
    { headers },
  );
  expect(reconciliationResponse.status()).toBe(200);
  const reconciliation =
    (await reconciliationResponse.json()) as components["schemas"]["CashCloseReconciliationResponse"];
  expect(reconciliation.pending_class_capture.has_pending_class_capture).toBe(false);
  const physicalStock = reconciliation.relevant_products.filter(
    (line) => Number(line.expected_quantity_before_deferred_attr) > 0,
  );
  expect(physicalStock.length).toBeGreaterThan(0);
  await page.goto("/cerrar-turno");
  await expect(page.getByRole("heading", { name: "Cierre de turno", exact: true })).toBeVisible();
  // Enter the fixture's actual stock through the same counting UI used by the
  // operator. Do not claim an empty counter or create a corrective stock loss.
  for (const line of physicalStock) {
    await page
      .locator('[data-pos-catalog-card="true"]')
      .filter({ has: page.getByText(line.product_class_name, { exact: true }) })
      .click();
    await page
      .locator('[data-pos-catalog-card="true"]')
      .filter({ has: page.getByText(line.product_name, { exact: true }) })
      .click();
    await page
      .getByLabel(`Cantidad contada de ${line.product_name}`, { exact: true })
      .fill(line.expected_quantity_before_deferred_attr);
    await page.getByRole("button", { name: "Guardar conteo", exact: true }).click();
    if (line.lot_tracking_enabled) {
      const lotCounts = page.getByRole("group", {
        name: `Lotes contados · ${line.product_name}`,
        exact: true,
      });
      for (const lot of line.lots ?? [])
        await lotCounts
          .getByLabel(`Conteo lote ${lot.lot_code}`, { exact: true })
          .fill(lot.expected_quantity);
    }
  }
  await page.getByRole("button", { name: "Cerrar con conteo", exact: true }).click();
  await expect(page.getByLabel("Efectivo", { exact: true })).toBeVisible();
  await page.getByLabel("Efectivo", { exact: true }).fill("10.00");
  const closeFault = await dropNextCashCommandResponse(
    page,
    environment.apiUrl,
    network,
    "/v1/cash-close/commit",
  );
  const submittedClose = page.waitForRequest(
    (request) =>
      new URL(request.url()).pathname === "/v1/cash-close/commit" && request.method() === "POST",
  );
  await page
    .locator('[data-pos-shell-region="right"]')
    .getByRole("button", { name: "Cerrar turno", exact: true })
    .click();
  const closePayload = (
    await submittedClose
  ).postDataJSON() as components["schemas"]["CashCloseCommitRequest"];
  expect(closePayload.counter_empty_confirmed).toBe(false);
  for (const counted of physicalStock)
    expect(
      closePayload.counted_product_lines?.find((line) => line.product_id === counted.product_id)
        ?.counted_quantity,
    ).toBe(String(Number(counted.expected_quantity_before_deferred_attr)));
  const closed = (await closeFault.committed) as components["schemas"]["CashCloseCommitResultView"];
  expect(closed.cash_session_id).toBe(opened.id);
  expect(closed.expected_cash_amount).toBe("10.00");
  const oldSession = await page.request.get(`${environment.apiUrl}/v1/auth/session`, { headers });
  expect(oldSession.status()).toBe(401);
  await page.reload();
  await expect(page).toHaveURL(/\/login$/);
  await login();
  await expect(page).toHaveURL(/\/cash-session\/open$/);
  await expect(
    page.getByRole("heading", { name: "Operación de caja pendiente de confirmar" }),
  ).toBeVisible();
  await expect(page.getByRole("button", { name: "Abriendo caja...", exact: true })).toBeDisabled();
  await expect(
    page.getByRole("button", { name: "Reintentar la misma operación de caja" }),
  ).toHaveCount(0);
  const recovered = await recover("/v1/cash-close/confirmations/", closed.id);
  expect(recovered).toEqual(closed);
  const detailResponse = await page.request.get(
    `${environment.apiUrl}/v1/cash-close/${closed.id}?workstation_code=${station}`,
    { headers },
  );
  expect(detailResponse.status()).toBe(200);
  const detail = (await detailResponse.json()) as components["schemas"]["CashCloseDetailResponse"];
  expect(detail.counter_empty_confirmed).toBe(false);
  for (const counted of physicalStock) {
    const recorded = detail.counted_product_lines.find(
      (line) => line.product_id === counted.product_id,
    );
    expect(recorded?.counted_quantity).toBe(counted.expected_quantity_before_deferred_attr);
  }
  expect(detail.generated_discrepancy_documents).toEqual([]);
  const methods = Object.fromEntries(
    detail.payment_method_rows.map((row) => [row.payment_method_code, row]),
  );
  expect(Object.keys(methods).sort()).toEqual(["CARD", "CASH"]);
  expect(methods.CASH?.variance_amount).toBe("0.00");
  expect(methods.CARD?.expected_amount).toBe("0.00");
  expect(methods.CARD?.counted_amount).toBeNull();
  expect(methods.CARD?.variance_amount).toBeNull();
  const current = await page.request.get(
    `${environment.apiUrl}/v1/cash-sessions/current?workstation_code=${station}`,
    { headers },
  );
  expect(current.status()).toBe(200);
  expect(await current.json()).toBeNull();
  await expect(page.getByRole("button", { name: "Abrir caja", exact: true })).toBeEnabled();
  for (const path of ["/v1/cash-sessions/open", "/v1/payments", "/v1/cash-close/commit"]) {
    expect(network.filter((entry) => entry.method === "POST" && entry.path === path)).toHaveLength(
      1,
    );
  }
});
