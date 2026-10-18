import { expect, test } from "@playwright/test";

test("loads the backoffice shell", async ({ page }) => {
  await page.route("**/v1/auth/session", route => route.fulfill({ status: 401, json: { code: "SESSION_REQUIRED", message: "Inicia sesión." } }));
  await page.goto("/");

  await expect(page.getByRole("heading", { name: "Branch operations" })).toBeVisible();
});
