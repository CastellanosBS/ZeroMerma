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
  await page.getByRole("button", { name: "Enviar transferencia", exact: true }).click();
  const dispatchedResponse = page.waitForResponse(
    (response) =>
      new URL(response.url()).pathname === `/v1/admin/transfers/${committed.id}/dispatch` &&
      response.request().method() === "POST",
  );
  await page.getByRole("button", { name: "Confirmar envio", exact: true }).click();
  expect((await dispatchedResponse).status()).toBe(200);
  const physicalDetail = page
    .getByRole("complementary")
    .filter({ has: page.getByRole("region", { name: "Resoluciones del tránsito", exact: true }) });
  await physicalDetail.getByRole("button", { name: "Recibir", exact: true }).click();
  const receipt = page
    .locator("form")
    .filter({ has: page.getByRole("button", { name: "Confirmar recepcion", exact: true }) });
  await receipt.getByLabel("Recibido", { exact: true }).fill("1");
  await receipt
    .getByLabel("Razon si difiere", { exact: true })
    .fill("Remaining product physically returned to origin");
  const receivedResponse = page.waitForResponse(
    (response) =>
      new URL(response.url()).pathname === `/v1/admin/transfers/${committed.id}/receive` &&
      response.request().method() === "POST",
  );
  await receipt.getByRole("button", { name: "Confirmar recepcion", exact: true }).click();
  const partial = (await (
    await receivedResponse
  ).json()) as components["schemas"]["TransferCommandResultView"];
  expect(partial.status).toBe("IN_TRANSIT");
  expect(Number(partial.lines[0]!.pending_quantity)).toBe(1);
  const resolution = page.getByRole("region", { name: "Resoluciones del tránsito", exact: true });
  await resolution.getByText("Resolver mercancía en tránsito", { exact: true }).click();
  await resolution.getByLabel(/^Cantidad a resolver:/).fill("1");
  await resolution
    .getByLabel("Motivo de la disposición", { exact: true })
    .fill("Physical return inspected in quarantine");
  const resolvePath = `/v1/admin/transfers/${committed.id}/resolve`;
  const resolutionFault = await dropNextOperationalCommandResponse(
    page,
    environment.apiUrl,
    network,
    resolvePath,
  );
  await resolution
    .getByRole("button", { name: "Confirmar disposición física", exact: true })
    .click();
  const resolved =
    (await resolutionFault.committed) as components["schemas"]["TransferCommandResultView"];
  expect(resolved.status).toBe("RECEIVED_WITH_VARIANCE");
  expect(Number(resolved.lines[0]!.pending_quantity)).toBe(0);
  expect(Number(resolved.lines[0]!.received_quantity)).toBe(1);
  expect(Number(resolved.lines[0]!.returned_quantity)).toBe(1);
  await page.reload();
  await expect(page.getByRole("button", { name: "Reintentar la misma transferencia" })).toHaveCount(
    0,
  );
  const resolvedRecovery = page.waitForResponse((response) =>
    new URL(response.url()).pathname.startsWith(
      "/v1/admin/transfers/commands/resolve_return/confirmations/",
    ),
  );
  await page
    .getByRole("button", { name: "Consultar resultado de la transferencia", exact: true })
    .click();
  expect(await (await resolvedRecovery).json()).toEqual(resolved);
  expect(
    network.filter(
      (entry) => entry.method === "POST" && entry.path === "/v1/admin/transfers/{id}/resolve",
    ),
  ).toHaveLength(1);
});
