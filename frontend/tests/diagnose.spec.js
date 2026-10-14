import { test, expect } from "@playwright/test";

test("runs a diagnosis and displays its evidence", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Run diagnostic" }).click();
  await expect(page.getByText("The container is restarting because it exceeded its memory limit.")).toBeVisible();
  await expect(page.getByRole("heading", { name: "Evidence" })).toBeVisible();
  await expect(page.getByText("2 records")).toBeVisible();
});
