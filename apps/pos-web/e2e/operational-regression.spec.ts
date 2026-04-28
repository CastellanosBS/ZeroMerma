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
    { path: "/pasar-a-mostrador", readyText: "Pasar a mostrador", assertionText: "Agrega productos exactos" },
    { path: "/enviar-a-sucursal", readyText: "Enviar a sucursal", assertionText: "Sucursal Norte" },
    { path: "/recibir-envio", readyText: "Recibir envio", assertionText: "ENV-3101" },
    { path: "/pedidos", readyText: "Pedidos", assertionText: "PED-1001" },
    { path: "/tickets", readyText: "Detalle del ticket", assertionText: "TCK-5001" },
    { path: "/devoluciones", readyText: "Devoluciones", assertionText: "TCK-5001" },
    { path: "/correcciones", readyText: "Ajustes auditados", assertionText: "ENV-2001" },
    { path: "/registrar-merma", readyText: "Registrar merma", assertionText: "Selecciona un origen" },
    { path: "/pagos", readyText: "Pagos operativos", assertionText: "PAG-2001" },
    { path: "/descuentos", readyText: "Descuentos operativos", assertionText: "DES-3001" },
    { path: "/cerrar-turno", readyText: "Wizard de cierre", assertionText: "Ver resumen del turno" },
  ] as const;

  for (const module of modules) {
    await openModule(page, module.path, module.readyText);
    await expect(page.locator("body")).toContainText(module.assertionText);
  }
});

test("starts a return from Tickets and preserves routed sale context", async ({ page }) => {
  await openModule(page, "/tickets", "Detalle del ticket");

  await page.getByRole("button", { name: /TCK-5001/i }).click();
  await page.getByRole("button", { name: "Iniciar devolucion" }).click();

  await expect(page).toHaveURL(/\/devoluciones/);
  await expect(page.locator("body")).toContainText("Devoluciones");
  await expect(page.locator("body")).toContainText("TCK-5001");
  await expect(page.locator("body")).toContainText("Confirmar devolucion");
});

test("advances the cash close route into the wizard summary step", async ({ page }) => {
  await openModule(page, "/cerrar-turno", "Wizard de cierre");

  await page.getByRole("button", { name: "Ver resumen del turno" }).click();

  await expect(page.locator("body")).toContainText("Resumen del turno");
  await expect(page.locator("body")).toContainText("Capturar efectivo");
  await expect(page.locator("body")).toContainText("Paso 2");
});
