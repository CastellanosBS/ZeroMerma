import { expect, test } from "@playwright/test";

test("loads the POS login screen", async ({ page }) => {
  await page.goto("/");

  await expect(page.getByRole("heading", { name: "Operator sign in" })).toBeVisible();
  await expect(page.getByLabel("Operator email")).toBeVisible();
  await expect(page.getByLabel("Password")).toBeVisible();
});
