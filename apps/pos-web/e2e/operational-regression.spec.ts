import { expect, test, type Page } from "@playwright/test";

import {
  installAuthenticatedOperatorSession,
  installOperationalRegressionApiMocks,
} from "./helpers/operational-regression-mocks";

async function openModule(page: Page, modulePath: string, readyText: string) {
  await page.goto(modulePath);
  await expect(page.locator("body")).toContainText(readyText);
}

test.describe.configure({ mode: "serial" });

test.beforeEach(async ({ page }) => {
  await installAuthenticatedOperatorSession(page);
  await installOperationalRegressionApiMocks(page);
});

test("loads the operational routes with seeded module data", async ({ page }) => {
  const modules = [
    { path: "/pos", readyText: "Punto de venta", assertionText: "Pan dulce" },
    {
      path: "/pasar-a-mostrador",
      readyText: "Pasar a mostrador",
      assertionText: "Sin productos seleccionados.",
    },
    { path: "/enviar-a-sucursal", readyText: "Enviar a sucursal", assertionText: "Sucursal Norte" },
    { path: "/recibir-envio", readyText: "Recibir envio", assertionText: "ENV-3101" },
    { path: "/pedidos", readyText: "Pedidos", assertionText: "PED-1001" },
    { path: "/tickets", readyText: "Tickets emitidos", assertionText: "TCK-5001" },
    { path: "/devoluciones", readyText: "Devoluciones", assertionText: "TCK-5001" },
    { path: "/correcciones", readyText: "Ajustes", assertionText: "ENV-2001" },
    { path: "/registrar-merma", readyText: "Registrar merma", assertionText: "Mostrador" },
    { path: "/pagos", readyText: "Pagos operativos", assertionText: "PAG-2001" },
    { path: "/cerrar-turno", readyText: "Cierre de turno", assertionText: "Contar productos" },
  ] as const;

  for (const module of modules) {
    await openModule(page, module.path, module.readyText);
    await expect(page.locator("body")).toContainText(module.assertionText);
  }
});

test("starts a return from Tickets and preserves routed sale context", async ({ page }) => {
  await openModule(page, "/tickets", "Tickets emitidos");

  await page.getByRole("row").filter({ hasText: "TCK-5001" }).click();
  await page.getByRole("button", { name: "Iniciar devolucion" }).click();

  await expect(page).toHaveURL(/\/devoluciones/);
  await expect(page.locator("body")).toContainText("Devoluciones");
  await expect(page.locator("body")).toContainText("TCK-5001");
  await expect(page.locator("body")).toContainText("Confirmar devolucion");
});

test("advances from physical counting to monetary review and preserves the release redirect", async ({
  page,
}) => {
  await openModule(page, "/cerrar-turno", "Cierre de turno");
  await expect(page.locator("body")).toContainText("Contar productos");
  await expect(page.getByRole("button", { name: /Pan dulce/ })).toBeVisible();
  await page.getByRole("button", { name: "No sobró pan", exact: true }).click();
  await expect(page.getByRole("textbox", { name: "Efectivo", exact: true })).toBeVisible();
  await expect(page.getByRole("textbox", { name: "Tarjeta", exact: true })).toBeVisible();
  await page.goto("/descuentos");
  await expect(page).toHaveURL(/\/pos$/);
});
