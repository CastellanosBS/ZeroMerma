import type { components } from "@zeromerma/api-client";
import {
  dropNextSaleConfirmationResponse,
  dropNextOperationalCommandResponse,
} from "../../../scripts/dev/web-integration-support.mjs";
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
  expect(originalRequest.postDataJSON().lines[0]).toMatchObject({
    expected_unit_price: "12.00",
    expected_currency_code: "MXN",
  });
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
  await page.getByRole("button", { name: /Mixto \(registro\)/ }).click();
  await page.getByRole("button", { name: /\* Tarjeta/ }).click();
  await page.getByLabel("Monto del tramo").fill("2.00");
  await page.getByLabel("Monto del tramo").press("Enter");
  await page.getByRole("button", { name: /\/ Efectivo/ }).click();
  await page.getByLabel("Monto del tramo").fill("20.00");
  await page.getByLabel("Monto del tramo").press("Enter");
  const next = page.waitForResponse(
    (response) =>
      new URL(response.url()).pathname === "/v1/sales/confirm" &&
      response.request().method() === "POST",
  );
  await page.getByRole("button", { name: /^Cobrar(?:\s+Enter)?$/ }).click();
  const nextResponse = await next;
  expect(nextResponse.status()).toBe(201);
  expect(nextResponse.request().headers()["idempotency-key"]).not.toBe(key);
  const mixed = (await nextResponse.json()) as components["schemas"]["SaleConfirmationView"];
  expect(mixed.id).not.toBe(committed.id);
  expect(Number(mixed.total_amount)).toBe(12);
  expect(Number(mixed.change_amount)).toBe(10);
  expect(mixed.payments).toEqual(expect.arrayContaining([
    expect.objectContaining({ payment_method_code: "CARD", applied_amount: "2.00" }),
    expect.objectContaining({ payment_method_code: "CASH", applied_amount: "10.00", change_amount: "10.00" }),
  ]));
  await otherTab.close();

  await page.goto(`/tickets?ticketId=${committed.id}`);
  const physical = page.getByRole("region", { name: "Atribucion fisica del ticket", exact: true });
  await expect(physical).toContainText("Pendiente de atribuir: 1.000");
  const product = physical.getByLabel("Producto y lote entregados", { exact: true });
  await expect(product).toBeVisible();
  await expect(product).toBeEnabled();
  await expect(product.locator("option").nth(1)).toHaveAttribute("value", /.+/);
  await product.selectOption({ index: 1 });
  const selectedOption = await product.inputValue();
  await physical.getByLabel("Cantidad a atribuir", { exact: true }).fill("0.4");
  const attributionPath = `/v1/sales/${committed.id}/attribute-inventory`;
  const attributionFault = await dropNextOperationalCommandResponse(
    page,
    environment.apiUrl,
    network,
    attributionPath,
  );
  await physical.getByRole("button", { name: "Confirmar producto entregado", exact: true }).click();
  const attributed =
    (await attributionFault.committed) as components["schemas"]["ClassAttributionResult"];
  expect(attributed.sale_id).toBe(committed.id);
  expect(Number(attributed.lines[0]!.quantity)).toBe(0.4);
  expect(Number(attributed.lines[0]!.remaining_quantity)).toBe(0.6);
  expect(attributed.lines[0]!.inventory_movement_id).toBeTruthy();
  await expect(
    page.getByRole("heading", { name: "Atribucion fisica pendiente de confirmar" }),
  ).toBeVisible();
  await page.reload();
  await expect(page.getByRole("button", { name: "Reintentar la misma atribucion" })).toHaveCount(0);
  const attributionRecovery = page.waitForResponse((response) =>
    new URL(response.url()).pathname.startsWith(
      `/v1/sales/${committed.id}/inventory-attributions/`,
    ),
  );
  await page.getByRole("button", { name: "Consultar atribucion fisica", exact: true }).click();
  expect(await (await attributionRecovery).json()).toEqual(attributed);
  expect(
    network.filter(
      (entry) => entry.method === "POST" && entry.path === "/v1/sales/{id}/attribute-inventory",
    ),
  ).toHaveLength(1);
  await expect(physical).toContainText("Pendiente de atribuir: 0.600");
  await product.selectOption(selectedOption);
  await physical.getByLabel("Cantidad a atribuir", { exact: true }).fill("0.6");
  const completedAttribution = page.waitForResponse(
    (response) =>
      new URL(response.url()).pathname === attributionPath &&
      response.request().method() === "POST",
  );
  await physical.getByRole("button", { name: "Confirmar producto entregado", exact: true }).click();
  const completedResponse = await completedAttribution;
  expect(completedResponse.status()).toBe(200);
  const complete =
    (await completedResponse.json()) as components["schemas"]["ClassAttributionResult"];
  expect(complete.operation_id).not.toBe(attributed.operation_id);
  expect(Number(complete.lines[0]!.quantity)).toBe(0.6);
  expect(Number(complete.lines[0]!.remaining_quantity)).toBe(0);
  await expect(physical).toContainText("Pendiente de atribuir: 0.000");
  await expect(
    physical.getByRole("button", { name: "Confirmar producto entregado", exact: true }),
  ).toHaveCount(0);
  const ticketResponse = await page.request.get(
    `${environment.apiUrl}/v1/tickets/${committed.id}?workstation_code=${process.env.ZM_E2E_WORKSTATION_CODE ?? "POS-01"}`,
    { headers: { Origin: new URL(environment.baseUrl).origin, "X-ZeroMerma-Surface": "POS" } },
  );
  expect(ticketResponse.status()).toBe(200);
  const ticket = (await ticketResponse.json()) as components["schemas"]["TicketDetailResponse"];
  expect(ticket.total_amount).toBe(committed.total_amount);
  expect(ticket.receipt?.source_id).toBe(committed.id);
  expect(ticket.receipt?.total_amount).toBe(committed.total_amount);
  expect(ticket.receipt?.folio).toBe(ticket.folio);
  expect(ticket.lines[0]!.physical_attributions).toHaveLength(2);
  expect(
    network.filter((entry) => entry.method === "POST" && entry.path === "/v1/sales/confirm"),
  ).toHaveLength(2);
});
