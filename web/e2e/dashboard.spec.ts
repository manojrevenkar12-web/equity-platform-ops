import AxeBuilder from "@axe-core/playwright";
import { expect, type Page, test } from "@playwright/test";

async function noViolations(page: Page) {
  const r = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa"]).analyze();
  expect(r.violations.map((v) => `${v.id}: ${v.nodes.length}`)).toEqual([]);
}

test("hours shows every design, split by where the hours go, with the numbers in a table", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { level: 1 })).toContainText("engineering hours lost a week as found");
  await expect(page.getByRole("img", { name: /^Platform: .* hours a week/ })).toBeVisible();
  await expect(page.locator("tbody tr")).toHaveCount(13);
  await expect(page.getByText(/gate passed|gate not passed|not run yet/).first()).toBeVisible();
  await noViolations(page);
});

for (const [hash, heading, rows] of [
  ["delivery", /Pull requests hear back in/, 6],
  ["oncall", /pages a week instead of/, 5],
  ["jobs", /duplicate vesting records/, 4],
] as const) {
  test(`${hash} compares the designs that change it`, async ({ page }) => {
    await page.goto(`/#/${hash}`);
    await expect(page.getByRole("heading", { level: 1 })).toContainText(heading);
    await expect(page.locator("tbody tr")).toHaveCount(rows);
    await noViolations(page);
  });
}

test("the guard blocks an open database port and applies a routine change", async ({ page }) => {
  await page.goto("/#/changes");
  await expect(page.getByRole("button", { name: "Database port open to the internet" })).toHaveAttribute("aria-pressed", "true");
  await page.getByRole("button", { name: "Run the guard" }).click();
  await expect(page.getByText("Blocked")).toBeVisible();
  await expect(page.getByText("internet_to_sensitive_port")).toBeVisible();
  await page.getByRole("button", { name: "Routine: a private bucket" }).click();
  await page.getByRole("button", { name: "Run the guard" }).click();
  await expect(page.getByText("Applies after CI")).toBeVisible();
  await noViolations(page);
});

test("a plan that is not JSON gets a way to fix it", async ({ page }) => {
  await page.goto("/#/changes");
  await page.getByLabel("Plan (terraform show -json)").fill("{ not json");
  await page.getByRole("button", { name: "Run the guard" }).click();
  await expect(page.getByRole("alert")).toContainText("terraform show -json");
});

test("an API failure offers a retry", async ({ page }) => {
  await page.route("**/api/results", (r) => r.fulfill({ status: 503, body: JSON.stringify({ detail: "warming up" }) }));
  await page.goto("/");
  await expect(page.getByRole("alert")).toContainText("warming up");
  await expect(page.getByRole("button", { name: "Try again" })).toBeVisible();
});
