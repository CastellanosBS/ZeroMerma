import { expect, test } from "@playwright/test";
import { mockSessionResponse } from "./helpers/session-mocks";

const errorEnvelope = { details: null, request_id: null, field_errors: null };

test("temporary password gates all business routes until the password is changed", async ({ page }) => {
  let signedIn = false;
  const session = mockSessionResponse(); session.user.password_reset_required = true; session.user.effective_grants = [];
  let passwordChanged = false;
  await page.route("**/v1/auth/**", async route => {
    const request = route.request(); const path = new URL(request.url()).pathname;
    expect(request.headers()["authorization"]).toBeUndefined();
    expect(request.headers()["x-zeromerma-surface"]).toBe("POS");
    if (path.endsWith("/login")) { signedIn = true; await route.fulfill({ json: session }); return; }
    if (path.endsWith("/password/change")) {
      expect(request.headers()["x-csrf-token"]).toBe(session.csrf_token);
      expect(request.postDataJSON()).toEqual({ current_password: "temporary-test-password", new_password: "replacement-test-password" });
      passwordChanged = true; signedIn = false;
      await route.fulfill({ status: 204 }); return;
    }
    await route.fulfill(signedIn ? { json: session } : { status: 401, json: { ...errorEnvelope, code: "AUTHENTICATION_REQUIRED", message: "Inicia sesión." } });
  });
  await page.goto("/pos");
  await page.getByLabel("Correo", { exact: true }).fill("temporary@example.invalid");
  await page.getByLabel("Contrasena", { exact: true }).fill("temporary-test-password");
  await page.getByRole("button", { name: "Entrar", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Cambia tu contraseña" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Punto de venta", exact: true })).toHaveCount(0);
  await page.getByLabel("Contraseña actual", { exact: true }).fill("temporary-test-password");
  await page.getByLabel("Nueva contraseña", { exact: true }).fill("replacement-test-password");
  await page.getByLabel("Confirma la nueva contraseña", { exact: true }).fill("replacement-test-password");
  await page.getByRole("button", { name: "Cambiar contraseña", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Acceso del cajero" })).toBeVisible();
  expect(passwordChanged).toBe(true);
  expect(await page.evaluate(() => localStorage.getItem("zeromerma-pos-auth"))).toBeNull();
});

test("wrong unlock password preserves the lock and server logout remains available", async ({ page }) => {
  let signedIn = true;
  const session = mockSessionResponse(); session.session.status = "LOCKED";
  let logout = false;
  await page.route("**/v1/auth/**", async route => {
    const path = new URL(route.request().url()).pathname;
    if (path.endsWith("/reauthenticate")) {
      await route.fulfill({ status: 401, json: { ...errorEnvelope, code: "INVALID_CREDENTIALS", message: "Contraseña incorrecta." } }); return;
    }
    if (path.endsWith("/logout")) {
      expect(route.request().headers()["x-csrf-token"]).toBe(session.csrf_token);
      logout = true; signedIn = false; await route.fulfill({ status: 204 }); return;
    }
    await route.fulfill(signedIn ? { json: session } : { status: 401, json: { ...errorEnvelope, code: "AUTHENTICATION_REQUIRED", message: "Inicia sesión." } });
  });
  await page.goto("/pos");
  await expect(page.getByRole("heading", { name: "Sesión bloqueada" })).toBeVisible();
  await page.getByLabel("Contraseña actual").fill("incorrect-password");
  await page.getByRole("button", { name: "Desbloquear", exact: true }).click();
  await expect(page.getByRole("alert")).toContainText("Contraseña incorrecta.");
  await expect(page.getByRole("heading", { name: "Sesión bloqueada" })).toBeVisible();
  await page.getByRole("button", { name: "Cerrar sesión", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Acceso del cajero" })).toBeVisible();
  expect(logout).toBe(true);
});
