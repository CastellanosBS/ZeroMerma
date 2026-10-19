import type { components } from "@zeromerma/api-client";
import { dropNextOperationalCommandResponse } from "../../../scripts/dev/web-integration-support.mjs";
import { environment, expect, test } from "./fixtures";

test("real inventory adjustment form and waste command recover lost acknowledgements without another movement", async ({
  page,
  network,
}) => {
  await page.goto("/login");
  await page
    .getByLabel("Correo", { exact: true })
    .fill(process.env.ZM_E2E_OPERATIONS_OPERATOR_EMAIL!);
  await page.getByLabel("Contraseña", { exact: true }).fill(environment.password);
  await page.getByRole("button", { name: "Entrar al backoffice" }).click();
  await expect(page).not.toHaveURL(/\/login$/);
  await page.goto("/admin/inventario");
  await page.getByRole("button", { name: "Nuevo ajuste", exact: true }).click();
  const dialog = page.getByRole("dialog", { name: "Nuevo ajuste de inventario", exact: true });
  const product = dialog.getByRole("combobox", { name: /^Producto/ });
  const branch = dialog.getByRole("combobox", { name: /^Sucursal/ });
  await expect(product).toBeEnabled();
  await expect(product).not.toHaveValue("");
  await expect(branch).not.toHaveValue("");
  const productId = await product.inputValue();
  const branchId = await branch.inputValue();
  await dialog.getByRole("combobox", { name: /^Ubicacion/ }).selectOption("BACKROOM");
  await dialog.getByLabel("Cantidad", { exact: true }).fill("4.000");
  await dialog.getByLabel("Razon obligatoria", { exact: true }).fill("Integration physical count");
  const fault = await dropNextOperationalCommandResponse(
    page,
    environment.apiUrl,
    network,
    "/v1/admin/inventory/adjustments",
  );
  const submitted = page
    .waitForRequest(
      (request) =>
        request.method() === "POST" &&
        new URL(request.url()).pathname === "/v1/admin/inventory/adjustments",
      { timeout: 5000 },
    )
    .catch(async () => {
      const validation = await dialog
        .locator("p")
        .filter({
          hasText:
            /Selecciona un producto|Selecciona una sucursal|Selecciona una ubicacion|La cantidad debe|La razon del ajuste/,
        })
        .allTextContents();
      throw new Error(
        `Inventory adjustment did not reach the API. Form validation: ${validation.join("; ") || "none"}`,
      );
    });
  await dialog.getByRole("button", { name: "Guardar ajuste", exact: true }).click();
  await submitted;
  const adjusted =
    (await fault.committed) as components["schemas"]["AdminInventoryAdjustmentResultView"];
  expect(adjusted.branch_id).toBe(branchId);
  expect(adjusted.product_id).toBe(productId);
  expect(adjusted.inventory_movement_id).toBeTruthy();
  await page.reload();
  const recovered = page.waitForResponse(
    (response) =>
      new URL(response.url()).pathname.startsWith(
        "/v1/admin/inventory/adjustments/confirmations/",
      ) && response.status() === 200,
  );
  await page
    .getByRole("button", { name: "Consultar resultado del movimiento", exact: true })
    .click();
  expect(await (await recovered).json()).toEqual(adjusted);
  await expect(
    page.getByRole("heading", { name: "Movimiento de inventario pendiente de confirmar" }),
  ).toHaveCount(0);
  const headers = {
    Origin: new URL(environment.baseUrl).origin,
    "X-ZeroMerma-Surface": "BACKOFFICE",
  };
  const sessionResponse = await page.request.get(`${environment.apiUrl}/v1/auth/session`, {
    headers,
  });
  expect(sessionResponse.status()).toBe(200);
  const session = (await sessionResponse.json()) as components["schemas"]["LoginResponse"];
  const wasteFault = await dropNextOperationalCommandResponse(
    page,
    environment.apiUrl,
    network,
    "/v1/admin/waste",
  );
  // Exercise the same production coordinator as the waste form; UI form acceptance above is inventory.
  const sent = page.evaluate(
    async ({ userId, branchId, productId }) => {
      const modulePath = "/src/features/admin/physical-commands/physical-command-intent.ts";
      const { physicalIntentions, PHYSICAL_INTENTION_SCOPE } = await import(modulePath);
      const observed = physicalIntentions.read(PHYSICAL_INTENTION_SCOPE)?.key ?? null;
      await physicalIntentions
        .begin(
          { userId, branchId, commandCode: "waste" },
          {
            commandCode: "waste",
            body: {
              branchId,
              productId,
              locationCode: "BACKROOM",
              quantity: "1.000",
              reasonCode: "DAMAGED",
              notes: "Integration damaged product",
            },
          },
          observed,
        )
        .catch(() => undefined);
    },
    { userId: session.user.id, branchId, productId },
  );
  const wasted = (await wasteFault.committed) as components["schemas"]["OperationCommitResultView"];
  await sent;
  expect(wasted.inventory_movement_ids).toHaveLength(1);
  await page.reload();
  const recoveredWaste = page.waitForResponse(
    (response) =>
      new URL(response.url()).pathname.startsWith("/v1/admin/waste/confirmations/") &&
      response.status() === 200,
  );
  await page
    .getByRole("button", { name: "Consultar resultado del movimiento", exact: true })
    .click();
  expect(await (await recoveredWaste).json()).toEqual(wasted);
  const detail = await page.request.get(
    `${environment.apiUrl}/v1/admin/inventory/${adjusted.balance_id}`,
    { headers },
  );
  expect(detail.status()).toBe(200);
  const balance = (await detail.json()) as components["schemas"]["AdminInventoryDetailView"];
  expect(Number(balance.stock_breakdown.quantity_on_hand)).toBe(Number(adjusted.new_quantity) - 1);
  expect(
    balance.movements.filter((movement) => movement.id === wasted.inventory_movement_ids[0]),
  ).toHaveLength(1);
  const saved = await page.evaluate(() =>
    JSON.parse(localStorage.getItem("zeromerma-admin-physical-intention:physical-commands")!),
  );
  expect(Object.keys(saved).sort()).toEqual(
    ["userId", "branchId", "commandCode", "key", "status", "payloadDigest"].sort(),
  );
  for (const path of ["/v1/admin/inventory/adjustments", "/v1/admin/waste"])
    expect(network.filter((entry) => entry.method === "POST" && entry.path === path)).toHaveLength(
      1,
    );
});
