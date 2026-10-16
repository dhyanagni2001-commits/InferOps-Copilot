import { test, expect } from "@playwright/test";

test("diagnoses the default OOM scenario with cited evidence", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByTestId("mode")).toContainText("demo replay");
  await page.getByRole("button", { name: "Run diagnostic" }).click();

  const diagnosis = page.getByRole("region", { name: "Diagnosis" });
  await expect(diagnosis.getByRole("heading", { level: 2 })).toContainText("OOMKilled");
  await expect(diagnosis).toContainText("high confidence");
  await expect(diagnosis.getByRole("link", { name: "status-1" })).toBeVisible();
  await expect(page.getByRole("list", { name: "Diagnostic steps" }).getByRole("listitem").first()).toContainText("Read workload");

  const evidence = page.getByRole("region", { name: "Evidence" });
  await expect(evidence.getByRole("heading", { name: "Runbooks" })).toBeVisible();
  await expect(evidence.locator("#evidence-status-1")).toHaveAttribute("open", "");
});

test("scenario chips switch workload and service diagnosis", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Service port" }).click();
  await expect(page.getByLabel("Resource")).toHaveValue("Service");
  await page.getByRole("button", { name: "Run diagnostic" }).click();
  await expect(page.getByRole("region", { name: "Diagnosis" })).toContainText("targetPort 9999");
  await expect(page.getByRole("region", { name: "Diagnosis" }).getByText("kubectl get service broken-service")).toBeVisible();
});

test("shows API errors for an invalid token", async ({ page }) => {
  await page.goto("/");
  await page.getByLabel("API token").fill("wrong-token");
  await page.getByRole("button", { name: "Run diagnostic" }).click();
  await expect(page.getByRole("alert")).toHaveText("invalid bearer token");
});
