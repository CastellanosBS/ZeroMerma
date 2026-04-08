import { expect, test } from "@playwright/test";

test("loads the backoffice shell", async ({ page }) => {
  await page.goto("/");

  await expect(page.getByRole("heading", { name: "Branch operations" })).toBeVisible();
});
