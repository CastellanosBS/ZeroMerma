import type { components } from "@zeromerma/api-client";
import { dropNextOperationalCommandResponse } from "../../../scripts/dev/web-integration-support.mjs";
import { environment, expect, test } from "./fixtures";

test("transfer draft survives lost acknowledgement and reload without dispatching automatically", async ({
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
  await page.goto("/admin/transferencias");
  await page.getByRole("button", { name: "Nueva transferencia", exact: true }).click();
  const form = page
    .locator("form")
    .filter({ has: page.getByRole("button", { name: "Guardar borrador", exact: true }) });
  await form.getByLabel(/^Producto 1/).selectOption({ index: 1 });
  await form.getByLabel("Cantidad", { exact: true }).fill("2");
  await form.getByLabel("Notas", { exact: true }).fill("Private transfer note");
  const origin = form.getByLabel(/^Origen/);
  const destination = form.getByLabel(/^Destino/);
  await expect(origin).not.toHaveValue("");
  await expect(destination).not.toHaveValue("");
  expect(await destination.inputValue()).not.toBe(await origin.inputValue());
  const path = "/v1/admin/transfers";
  const fault = await dropNextOperationalCommandResponse(page, environment.apiUrl, network, path);
  const sent = page.waitForRequest(
    (request) => request.method() === "POST" && new URL(request.url()).pathname === path,
    { timeout: 10_000 },
  );
  await form.getByRole("button", { name: "Guardar borrador", exact: true }).click();
  await expect(page.getByText("Selecciona una sucursal origen.", { exact: true })).toHaveCount(0);
  await expect(page.getByText("Selecciona una sucursal destino.", { exact: true })).toHaveCount(0);
  await sent;
  const committed = (await fault.committed) as components["schemas"]["TransferCommandResultView"];
  expect(committed.status).toBe("DRAFT");
  await expect(
    page.getByRole("heading", { name: "Transferencia pendiente de confirmar" }),
  ).toBeVisible();
  await page.reload();
  await expect(
    page.getByRole("heading", { name: "Transferencia pendiente de confirmar" }),
  ).toBeVisible();
  await expect(page.getByRole("button", { name: "Reintentar la misma transferencia" })).toHaveCount(
    0,
  );
  const recovered = page.waitForResponse((response) =>
    new URL(response.url()).pathname.startsWith(
      "/v1/admin/transfers/commands/create/confirmations/",
    ),
  );
  await page.getByRole("button", { name: "Consultar resultado de la transferencia" }).click();
  expect(await (await recovered).json()).toEqual(committed);
  await expect(
    page.getByRole("heading", { name: "Transferencia pendiente de confirmar" }),
  ).toHaveCount(0);
  expect(network.filter((entry) => entry.method === "POST" && entry.path === path)).toHaveLength(1);
  expect(
    network.filter((entry) => entry.method === "POST" && entry.path.endsWith("/dispatch")),
  ).toHaveLength(0);
  await page.getByText(committed.folio, { exact: true }).first().click();
  await expect(page.getByRole("button", { name: "Enviar", exact: true }).first()).toBeVisible();
  const metadata = await page.evaluate(() =>
    localStorage.getItem("zeromerma-admin-transfer-intention:transfers"),
  );
  expect(metadata).not.toContain("Private transfer note");
  expect(Object.keys(JSON.parse(metadata!)).sort()).toEqual(
    ["userId", "branchId", "transferId", "commandCode", "key", "payloadDigest", "status"].sort(),
  );
});
