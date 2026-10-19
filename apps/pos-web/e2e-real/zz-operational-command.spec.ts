import type { components } from "@zeromerma/api-client";
import { dropNextOperationalCommandResponse } from "../../../scripts/dev/web-integration-support.mjs";
import { environment, expect, test } from "./fixtures";

test("real counter, correction and waste coordinators recover original documents after lost responses and reload", async ({
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
  expect(cashResponse.status()).toBe(200);
  const cash = (await cashResponse.json()) as components["schemas"]["CashSessionView"];
  const catalogResponse = await page.request.get(
    `${environment.apiUrl}/v1/operations/catalog?workstation_code=${station}&module=COUNTER_TRANSFER`,
    { headers },
  );
  expect(catalogResponse.status()).toBe(200);
  const catalog =
    (await catalogResponse.json()) as components["schemas"]["OperationsCatalogResponse"];
  const productsResponse = await page.request.get(
    `${environment.apiUrl}/v1/operations/classes/${catalog.classes[0]!.id}/products?workstation_code=${station}&module=COUNTER_TRANSFER`,
    { headers },
  );
  expect(productsResponse.status()).toBe(200);
  const product = (
    (await productsResponse.json()) as components["schemas"]["OperationsClassProductsResponse"]
  ).products[0]!;
  let target: components["schemas"]["OperationCommitResultView"] | null = null;
  for (const commandCode of ["counter-transfer", "correction", "waste"] as const) {
    const path =
      commandCode === "correction"
        ? "/v1/corrections/commit"
        : `/v1/operations/${commandCode}/commit`;
    const fault = await dropNextOperationalCommandResponse(page, environment.apiUrl, network, path);
    const body =
      commandCode === "correction"
        ? {
            workstation_code: station,
            cash_session_id: cash.id,
            target_document_id: target!.id,
            reason_code: "WRONG_QUANTITY",
            high_impact_acknowledged: false,
            lines: [
              {
                product_id: product.id,
                target_line_id: target!.lines[0]!.id,
                delta_quantity: "-1",
              },
            ],
          }
        : {
            workstation_code: station,
            cash_session_id: cash.id,
            lines: [{ product_id: product.id, quantity: "2" }],
            ...(commandCode === "waste"
              ? {
                  source_bucket_code: "BACKROOM",
                  reason_code: "DAMAGED",
                  notes: "Damaged during isolated integration handling",
                  high_impact_acknowledged: false,
                }
              : {}),
          };
    const context = {
      userId: boot.user.id,
      branchId: boot.branch.id,
      workstationId: boot.workstation.id,
      workstationCode: station,
      cashSessionId: cash.id,
      commandCode,
      targetDocumentId: commandCode === "correction" ? target!.id : null,
    };
    const sent = page.evaluate(
      async ({ context, body }) => {
        const modulePath = "/src/features/operation-commands/operation-command-intent.ts";
        const { operationIntentions } = await import(modulePath);
        const observed = operationIntentions.read(context.workstationId)?.key ?? null;
        await operationIntentions
          .begin(context, { commandCode: context.commandCode, body }, observed)
          .catch(() => undefined);
      },
      { context, body },
    );
    const committed = (await fault.committed) as
      | components["schemas"]["OperationCommitResultView"]
      | components["schemas"]["CorrectionCommitResultView"];
    await sent;
    if (commandCode === "counter-transfer")
      target = committed as components["schemas"]["OperationCommitResultView"];
    await page.reload();
    await expect(
      page.getByRole("heading", { name: "Movimiento pendiente de confirmar" }),
    ).toBeVisible();
    await expect(
      page.getByRole("button", { name: "Reintentar la misma operación", exact: true }),
    ).toHaveCount(0);
    const prefix =
      commandCode === "correction"
        ? "/v1/corrections/confirmations/"
        : `/v1/operations/${commandCode}/confirmations/`;
    const recovered = page.waitForResponse(
      (response) =>
        new URL(response.url()).pathname.startsWith(prefix) && response.status() === 200,
    );
    await page
      .getByRole("button", { name: "Consultar resultado del movimiento", exact: true })
      .click();
    expect(await (await recovered).json()).toEqual(committed);
    await expect(
      page.getByRole("heading", { name: "Movimiento pendiente de confirmar" }),
    ).toHaveCount(0);
    expect(network.filter((entry) => entry.method === "POST" && entry.path === path)).toHaveLength(
      1,
    );
  }
  const saved = await page.evaluate(
    ({ id }) => JSON.parse(localStorage.getItem(`zeromerma-operation-intention:${id}`)!),
    { id: boot.workstation.id },
  );
  expect(Object.keys(saved).sort()).toEqual(
    [
      "userId",
      "branchId",
      "workstationId",
      "workstationCode",
      "cashSessionId",
      "commandCode",
      "targetDocumentId",
      "key",
      "status",
      "payloadDigest",
    ].sort(),
  );
});
