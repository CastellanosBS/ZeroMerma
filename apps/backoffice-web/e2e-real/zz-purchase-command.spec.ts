import type { components } from "@zeromerma/api-client";
import { dropNextOperationalCommandResponse } from "../../../scripts/dev/web-integration-support.mjs";
import { environment, expect, test } from "./fixtures";

test("a real direct purchase entry survives response loss and reload with one receipt", async ({
  page,
  network,
}) => {
  await page.goto("/login");
  await page
    .getByLabel("Correo", { exact: true })
    .fill(process.env.ZM_E2E_OPERATIONS_OPERATOR_EMAIL!);
  await page.getByLabel("Contraseña", { exact: true }).fill(environment.password);
  const loggedIn = page.waitForResponse(
    (response) => new URL(response.url()).pathname === "/v1/auth/login",
  );
  await page.getByRole("button", { name: "Entrar al backoffice" }).click();
  const authentication = (await (await loggedIn).json()) as components["schemas"]["LoginResponse"];
  await expect(page).not.toHaveURL(/\/login$/);
  const headers = {
    Origin: new URL(environment.baseUrl).origin,
    "X-ZeroMerma-Surface": "BACKOFFICE",
    "X-CSRF-Token": authentication.csrf_token,
  };
  const optionsResponse = await page.request.get(`${environment.apiUrl}/v1/admin/purchases`, {
    headers,
  });
  expect(optionsResponse.status()).toBe(200);
  const options =
    (await optionsResponse.json()) as components["schemas"]["AdminPurchaseListResponse"];
  const branchId = String(options.filter_options.branches[0]!.id);
  const productId = String(options.filter_options.products[0]!.id);
  const supplierResponse = await page.request.post(`${environment.apiUrl}/v1/admin/suppliers`, {
    headers,
    data: { legal_name: "Integration receipt supplier", branch_ids: [branchId], category: "OTHER" },
  });
  expect(supplierResponse.status()).toBe(201);
  const supplier =
    (await supplierResponse.json()) as components["schemas"]["AdminSupplierDetailView"];
  await page.goto("/admin/compras");
  await page.getByRole("button", { name: "Nueva entrada directa", exact: true }).click();
  const form = page
    .getByRole("complementary")
    .filter({ has: page.getByRole("heading", { name: "Nueva entrada directa", exact: true }) });
  await form.getByRole("combobox", { name: /^Proveedor/ }).selectOption(supplier.overview.id);
  await form.getByRole("combobox", { name: /^Sucursal receptora/ }).selectOption(branchId);
  await form.getByRole("combobox", { name: /^Producto/ }).selectOption(productId);
  await form.getByLabel("Cantidad recibida", { exact: true }).fill("3.000");
  await form.getByLabel("Costo unitario", { exact: true }).fill("9.2500");
  await form.getByLabel("Notas", { exact: true }).last().fill("Private direct-entry note");
  const path = "/v1/admin/purchases/direct-entry";
  const fault = await dropNextOperationalCommandResponse(page, environment.apiUrl, network, path);
  const outgoing = page.waitForRequest(
    (request) => new URL(request.url()).pathname === path && request.method() === "POST",
  );
  await form.getByRole("button", { name: "Confirmar entrada", exact: true }).click();
  const key = (await outgoing).headers()["idempotency-key"]!;
  const committed = (await fault.committed) as components["schemas"]["PurchaseCommandResultView"];
  expect(committed.status).toBe("RECEIVED");
  expect(committed.receipt_ids).toHaveLength(1);
  expect(committed.inventory_movement_ids).toHaveLength(1);
  await expect(page.getByRole("heading", { name: "Compra pendiente de confirmar" })).toBeVisible();
  await page.reload();
  await expect(page.getByRole("heading", { name: "Compra pendiente de confirmar" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Reintentar el mismo comando" })).toHaveCount(0);
  const recoveredResponse = page.waitForResponse(
    (response) =>
      new URL(response.url()).pathname === `/v1/admin/purchases/commands/direct-entry/${key}`,
  );
  await page.getByRole("button", { name: "Consultar resultado de compra" }).click();
  const recovered = await recoveredResponse;
  expect(recovered.status()).toBe(200);
  expect(await recovered.json()).toEqual(committed);
  expect(network.filter((entry) => entry.method === "POST" && entry.path === path)).toHaveLength(1);
  await expect(page.getByRole("heading", { name: "Compra pendiente de confirmar" })).toHaveCount(0);
  const detailResponse = await page.request.get(
    `${environment.apiUrl}/v1/admin/purchases/${committed.id}`,
    { headers },
  );
  expect(detailResponse.status()).toBe(200);
  const detail = (await detailResponse.json()) as components["schemas"]["AdminPurchaseDetailView"];
  expect(detail.receipt.receipt_count).toBe(1);
  expect(detail.inventory_impact.movements.map((movement) => movement.id)).toEqual(
    committed.inventory_movement_ids,
  );
  const metadata = await page.evaluate(() =>
    Object.entries(localStorage)
      .filter(([key]) => key.startsWith("zeromerma-admin-purchase-intention:"))
      .map(([, value]) => JSON.parse(value)),
  );
  expect(metadata).toHaveLength(1);
  expect(Object.keys(metadata[0]).sort()).toEqual(
    ["userId", "branchId", "purchaseId", "commandCode", "key", "payloadDigest", "status"].sort(),
  );
  expect(JSON.stringify(metadata)).not.toContain("Private direct-entry note");
});
