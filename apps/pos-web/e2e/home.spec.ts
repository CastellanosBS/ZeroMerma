import { expect, test } from "@playwright/test";

test("loads the POS shell", async ({ page }) => {
  await page.goto("/");

  await expect(page.getByRole("heading", { name: "Cash session required" })).toBeVisible();
});
