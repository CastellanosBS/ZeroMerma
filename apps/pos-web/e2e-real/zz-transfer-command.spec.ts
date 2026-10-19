import type { components } from "@zeromerma/api-client";
import { dropNextOperationalCommandResponse } from "../../../scripts/dev/web-integration-support.mjs";
import { environment, expect, test } from "./fixtures";

test("real transfer dispatch recovers after response loss and reload without a second shipment", async ({
  page,
  network,
}) => {
  await page.goto("/login");
  await page.getByLabel("Correo", { exact: true }).fill(environment.email);
  await page.getByLabel("Contrasena", { exact: true }).fill(environment.password);
  await page.getByRole("button", { name: "Entrar", exact: true }).click();
  await expect(page).toHaveURL(/\/(pos|cash-session\/open)$/);
  if (new URL(page.url()).pathname === "/cash-session/open") {
    await page.getByLabel("Monto de apertura").fill("0");
    await page.getByRole("button", { name: "Abrir caja", exact: true }).click();
  }
  await expect(page).toHaveURL(/\/pos$/);
  const station = process.env.ZM_E2E_WORKSTATION_CODE ?? "POS-01";
  const headers = { Origin: new URL(environment.baseUrl).origin, "X-ZeroMerma-Surface": "POS" };
  const bootResponse = await page.request.get(
    `${environment.apiUrl}/v1/operations/bootstrap?workstation_code=${station}`,
    { headers },
  );
  expect(bootResponse.status()).toBe(200);
  const boot = (await bootResponse.json()) as components["schemas"]["OperationsBootstrapResponse"];
  const cashResponse = await page.request.get(
    `${environment.apiUrl}/v1/cash-sessions/current?workstation_code=${station}`,
    { headers },
  );
  const cash = (await cashResponse.json()) as components["schemas"]["CashSessionView"];
  const catalogResponse = await page.request.get(
    `${environment.apiUrl}/v1/operations/catalog?workstation_code=${station}&module=BRANCH_TRANSFER_SHIPMENT`,
    { headers },
  );
  expect(catalogResponse.status()).toBe(200);
  const catalog =
    (await catalogResponse.json()) as components["schemas"]["OperationsCatalogResponse"];
  const productsResponse = await page.request.get(
    `${environment.apiUrl}/v1/operations/classes/${catalog.classes[0]!.id}/products?workstation_code=${station}&module=BRANCH_TRANSFER_SHIPMENT`,
    { headers },
  );
  const product = (
    (await productsResponse.json()) as components["schemas"]["OperationsClassProductsResponse"]
  ).products[0]!;
  const path = "/v1/transfers/dispatch/commit";
  const fault = await dropNextOperationalCommandResponse(page, environment.apiUrl, network, path);
  const context = {
    userId: boot.user.id,
    branchId: boot.branch.id,
    workstationId: boot.workstation.id,
    workstationCode: station,
    cashSessionId: cash.id,
    commandCode: "dispatch",
    transferId: null,
  };
  const body = {
    workstation_code: station,
    cash_session_id: cash.id,
    destination_branch_id: boot.destination_branches[0]!.id,
    notes: "Private transfer note",
    lines: [{ product_id: product.id, quantity: "1" }],
  };
  const sent = page.evaluate(
    async ({ context, body }) => {
      const modulePath = "/src/features/transfers/transfer-command-intent.ts";
      const { transferIntentions } = await import(modulePath);
      await transferIntentions
        .begin(context, body, transferIntentions.read(context.workstationId)?.key ?? null)
        .catch(() => undefined);
    },
    { context, body },
  );
  const committed = (await fault.committed) as components["schemas"]["TransferCommandResultView"];
  await sent;
  await page.reload();
  await expect(
    page.getByRole("heading", { name: "Transferencia pendiente de confirmar" }),
  ).toBeVisible();
  await expect(page.getByRole("button", { name: "Reintentar la misma transferencia" })).toHaveCount(
    0,
  );
  const recovered = page.waitForResponse((response) =>
    new URL(response.url()).pathname.startsWith("/v1/transfers/commands/dispatch/confirmations/"),
  );
  await page.getByRole("button", { name: "Consultar resultado de la transferencia" }).click();
  expect(await (await recovered).json()).toEqual(committed);
  expect(network.filter((entry) => entry.method === "POST" && entry.path === path)).toHaveLength(1);
  await expect(
    page.getByRole("heading", { name: "Transferencia pendiente de confirmar" }),
  ).toHaveCount(0);
  const metadata = await page.evaluate(
    (id) => localStorage.getItem(`zeromerma-transfer-intention:${id}`),
    boot.workstation.id,
  );
  expect(metadata).not.toContain("Private transfer note");
});
