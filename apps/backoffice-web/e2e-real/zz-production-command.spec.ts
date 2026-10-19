import { createIdempotencyKey, type components } from "@zeromerma/api-client";
import { dropNextOperationalCommandResponse } from "../../../scripts/dev/web-integration-support.mjs";
import { environment, expect, test } from "./fixtures";

test("real production create and start stay distinct and completion recovers after a lost response", async ({
  page,
  network,
}) => {
  await page.goto("/login");
  await page
    .getByLabel("Correo", { exact: true })
    .fill(process.env.ZM_E2E_OPERATIONS_OPERATOR_EMAIL!);
  await page.getByLabel("Contraseña", { exact: true }).fill(environment.password);
  const loginResponse = page.waitForResponse(
    (response) =>
      new URL(response.url()).pathname === "/v1/auth/login" &&
      response.request().method() === "POST",
  );
  await page.getByRole("button", { name: "Entrar al backoffice" }).click();
  const authentication = (await (
    await loginResponse
  ).json()) as components["schemas"]["LoginResponse"];
  await expect(page).not.toHaveURL(/\/login$/);
  const headers = {
    Origin: environment.baseUrl,
    "X-ZeroMerma-Surface": "BACKOFFICE",
    "X-CSRF-Token": authentication.csrf_token,
  };
  const catalogResponse = await page.request.get(
    `${environment.apiUrl}/v1/admin/products?search=CONCHA-VAN`,
    { headers },
  );
  expect(catalogResponse.status()).toBe(200);
  const product = (
    (await catalogResponse.json()) as components["schemas"]["AdminProductsListResponse"]
  ).items.find((item) => item.code === "CONCHA-VAN")!;
  expect(product).toBeDefined();
  const rawResponse = await page.request.post(`${environment.apiUrl}/v1/admin/inputs-supplies`, {
    headers,
    data: {
      code: "BROWSER-PROD-RAW",
      name: "Browser production material",
      product_class_id: product.class_id,
      product_kind: "RAW_MATERIAL",
      unit_of_measure: "kg",
      standard_cost: "1",
    },
  });
  expect(rawResponse.status()).toBe(201);
  const raw = ((await rawResponse.json()) as components["schemas"]["AdminInputSupplyDetailView"])
    .overview;
  const recipeResponse = await page.request.post(
    `${environment.apiUrl}/v1/admin/recipes-costs/recipes`,
    {
      headers,
      data: {
        product_id: product.id,
        yield_qty: "20",
        yield_uom: product.unit_of_measure,
        activate: true,
        version_name: "Browser production recipe",
        inputs: [{ input_product_id: raw.id, quantity: "2" }],
      },
    },
  );
  expect(recipeResponse.status()).toBe(201);
  const recipe = (
    (await recipeResponse.json()) as components["schemas"]["AdminRecipeCostDetailView"]
  ).active_recipe!;
  const listResponse = await page.request.get(`${environment.apiUrl}/v1/admin/production`, {
    headers,
  });
  expect(listResponse.status()).toBe(200);
  const branch = (
    (await listResponse.json()) as components["schemas"]["AdminProductionListResponse"]
  ).filter_options.branches[0]!;
  const stock = await page.request.post(`${environment.apiUrl}/v1/admin/inventory/adjustments`, {
    headers: { ...headers, "Idempotency-Key": createIdempotencyKey() },
    data: {
      branch_id: branch.id,
      product_id: raw.id,
      location_code: "BACKROOM",
      adjustment_type: "INCREASE",
      quantity: "10",
      reason: "Isolated production acceptance",
    },
  });
  expect(stock.status()).toBe(201);

  await page.goto("/admin/produccion");
  await page.getByRole("button", { name: "Nueva produccion", exact: true }).click();
  const createForm = page.locator("form").filter({
    has: page.getByRole("heading", { name: "Nueva produccion", exact: true }),
  });
  await expect(createForm).toBeVisible();
  await createForm.getByRole("combobox", { name: /^Sucursal\b/ }).selectOption(branch.id);
  await createForm
    .getByRole("combobox", { name: /^Producto terminado\b/ })
    .selectOption(product.id);
  await createForm.getByLabel("Cantidad", { exact: true }).fill("20");
  await createForm.getByRole("combobox", { name: /^Receta activa\b/ }).selectOption(recipe.id);
  const createResponse = page.waitForResponse(
    (response) =>
      new URL(response.url()).pathname === "/v1/admin/production" &&
      response.request().method() === "POST",
  );
  const startResponse = page.waitForResponse(
    (response) =>
      /\/v1\/admin\/production\/[^/]+\/start$/.test(new URL(response.url()).pathname) &&
      response.request().method() === "POST",
  );
  await page.getByRole("button", { name: "Guardar e iniciar", exact: true }).click();
  const createdResponse = await createResponse;
  const startedResponse = await startResponse;
  expect(createdResponse.status()).toBe(201);
  expect(startedResponse.status()).toBe(200);
  expect(createdResponse.request().headers()["idempotency-key"]).not.toBe(
    startedResponse.request().headers()["idempotency-key"],
  );
  const batch =
    (await startedResponse.json()) as components["schemas"]["ProductionCommandResultView"];
  expect(batch.status).toBe("IN_PROGRESS");
  const row = page.getByRole("article").filter({ hasText: batch.folio });
  await row.getByRole("button", { name: "Completar", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Completar produccion", exact: true }),
  ).toBeVisible();
  await page.getByLabel("Salida real", { exact: true }).fill("20");
  const path = `/v1/admin/production/${batch.id}/complete`;
  const fault = await dropNextOperationalCommandResponse(page, environment.apiUrl, network, path);
  await page.getByRole("button", { name: "Completar produccion", exact: true }).click();
  const committed = (await fault.committed) as components["schemas"]["ProductionCommandResultView"];
  expect(committed.id).toBe(batch.id);
  expect(committed.status).toBe("COMPLETED");
  await expect(
    page.getByRole("heading", { name: "Producción pendiente de confirmar" }),
  ).toBeVisible();
  const secondTab = await page.context().newPage();
  await secondTab.goto(`${environment.baseUrl}/admin/produccion`);
  await expect(
    secondTab.getByRole("button", { name: "Nueva produccion", exact: true }),
  ).toBeDisabled();
  await secondTab.close();
  await page.reload();
  await expect(
    page.getByRole("button", { name: "Consultar resultado de producción" }),
  ).toBeVisible();
  await expect(page.getByRole("button", { name: "Reintentar el mismo comando" })).toHaveCount(0);
  const recovery = page.waitForResponse(
    (response) =>
      new URL(response.url()).pathname.includes("/production/commands/complete/") &&
      response.request().method() === "GET",
  );
  await page.getByRole("button", { name: "Consultar resultado de producción" }).click();
  const recovered = await recovery;
  expect(recovered.status()).toBe(200);
  expect(await recovered.json()).toEqual(committed);
  const detailResponse = await page.request.get(
    `${environment.apiUrl}/v1/admin/production/${batch.id}`,
    { headers },
  );
  expect(detailResponse.status()).toBe(200);
  const detail =
    (await detailResponse.json()) as components["schemas"]["AdminProductionDetailView"];
  expect(detail.inventory_impact.movements).toHaveLength(2);
  expect(detail.actual_consumption.map((line) => line.consumed_qty)).toEqual(["2.000"]);
  expect(
    network.filter(
      (entry) =>
        entry.method === "POST" && entry.path.endsWith("/complete") && entry.status === 200,
    ),
  ).toHaveLength(1);
});
