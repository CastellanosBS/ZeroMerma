import { expect, test } from "@playwright/test";

import { installPosApiMocks } from "./helpers/pos-mocks";

test("shows the cashier login screen for unauthenticated access", async ({ page }) => {
  await page.goto("/");

  await expect(page.getByRole("heading", { name: "Acceso del cajero" })).toBeVisible();
  await expect(page.getByLabel("Correo")).toBeVisible();
  await expect(page.getByLabel("Contrasena")).toBeVisible();
  await expect(page.getByLabel("Correo")).toBeFocused();
});

test("routes an authenticated operator with an active session directly into POS and allows a basic checkout", async ({
  page,
}) => {
  await installPosApiMocks(page, { hasActiveCashSession: true });

  await page.goto("/login");
  await page.getByLabel("Correo").fill("cashier@zeromerma.local");
  await page.keyboard.press("Enter");
  await expect(page.getByLabel("Contrasena")).toBeFocused();
  await page.getByLabel("Contrasena").fill("secret");
  await page.keyboard.press("Enter");

  await expect(page).toHaveURL(/\/pos$/);
  await expect(page.getByRole("heading", { name: "Punto de venta" })).toBeVisible();

  await page.getByRole("button", { name: /Pan dulce/ }).click();
  await page.getByLabel("Cantidad").fill("2");
  await page.getByRole("button", { name: "Agregar" }).click();
  await page.getByLabel("Dinero recibido").click();
  await expect(page.getByLabel("Dinero recibido")).toBeFocused();
  await page.getByLabel("Dinero recibido").fill("50");
  await page.keyboard.press("Enter");
  await expect(page.getByRole("button", { name: "Cobrar" })).toBeVisible();
  await page.getByRole("button", { name: "Cobrar" }).click();

  await expect(page.locator("body")).toContainText("Venta registrada.");
  await expect(
    page.getByText("El ticket esta vacio. Agrega productos desde el catalogo para empezar la venta."),
  ).toBeVisible();
});

test("sends an authenticated operator without an active session to the cash-session gate", async ({
  page,
}) => {
  await installPosApiMocks(page, { hasActiveCashSession: false });

  await page.goto("/login");
  await page.getByLabel("Correo").fill("cashier@zeromerma.local");
  await page.keyboard.press("Enter");
  await expect(page.getByLabel("Contrasena")).toBeFocused();
  await page.getByLabel("Contrasena").fill("secret");
  await page.keyboard.press("Enter");

  await expect(page).toHaveURL(/\/cash-session\/open$/);
  await expect(page.getByRole("heading", { name: "Registrar apertura" })).toBeVisible();
  await expect(page.getByLabel("Monto de apertura")).toBeFocused();
  await page.getByLabel("Monto de apertura").fill("0.00");
  await page.keyboard.press("Enter");

  await expect(page.getByRole("status")).toContainText("Caja abierta · Turno iniciado");
  await expect(page.getByRole("heading", { name: "Caja abierta" })).toBeVisible();
  await page.getByRole("button", { name: "Ir al POS" }).click();

  await expect(page).toHaveURL(/\/pos$/);
  await expect(page.getByRole("heading", { name: "Punto de venta" })).toBeVisible();
});

test("shows the already-open state on the cash-session gate when a session exists", async ({
  page,
}) => {
  await installPosApiMocks(page, { hasActiveCashSession: true });

  await page.addInitScript(() => {
    localStorage.setItem(
      "zeromerma-pos-auth",
      JSON.stringify({
        state: {
          accessToken: "test-access-token",
        },
        version: 0,
      }),
    );
  });

  await page.goto("/cash-session/open");

  await expect(page.getByRole("heading", { name: "Caja abierta" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Ir al POS" })).toBeVisible();
});

