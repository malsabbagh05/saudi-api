import { expect, test } from "@playwright/test";

test.describe("locales", () => {
  for (const [locale, dir, heading] of [
    ["en", "ltr", "Every Saudi API"],
    ["ar", "rtl", "كل واجهة برمجية سعودية"],
  ] as const) {
    test(`home renders in ${locale} with its direction`, async ({ page }) => {
      await page.goto(`/${locale}`);
      await expect(page.locator("html")).toHaveAttribute("lang", locale);
      await expect(page.locator("html")).toHaveAttribute("dir", dir);
      await expect(page.getByRole("heading", { level: 1 })).toContainText(heading);
      // The counts and the sector index stream in from the API.
      await expect(page.getByRole("heading", { level: 2 }).first()).toBeVisible();
      await expect(page.locator("#sectors ~ ul li, section[aria-labelledby=sectors] li").first()).toBeVisible();
    });
  }

  test("the root redirects to a locale", async ({ page }) => {
    await page.goto("/");
    await expect(page).toHaveURL(/\/(en|ar)$/);
  });

  test("switching language keeps the page and its query", async ({ page }) => {
    await page.goto("/en/apis?access=open");
    await page.getByRole("link", { name: "Read this page in Arabic" }).click();
    await expect(page).toHaveURL(/\/ar\/apis\?access=open$/);
    await expect(page.locator("html")).toHaveAttribute("dir", "rtl");
  });

  test("a path without a locale redirects to one", async ({ request }) => {
    const response = await request.get("/apis", { maxRedirects: 0 });
    expect(response.status()).toBe(307);
    expect(response.headers()["location"]).toMatch(/\/en\/apis$/);
  });

  test("an unknown first segment answers 404, not an error", async ({ request }) => {
    // Redirected by the proxy to /en/no-such-page.
    expect((await request.get("/no-such-page")).status()).toBe(404);
    // A dot keeps the proxy out, so the segment reaches the [locale] layout as is.
    expect((await request.get("/no.such/apis")).status()).toBe(404);
  });

  test("unknown pages show the localized not-found page", async ({ page }) => {
    const response = await page.goto("/ar/no-such-page");
    expect(response?.status()).toBe(404);
    await expect(page.getByRole("heading", { level: 1 })).toHaveText("الصفحة غير موجودة");
  });
});

test.describe("search", () => {
  test("an Arabic query finds the national address APIs", async ({ page }) => {
    await page.goto("/ar");
    await page.getByRole("searchbox", { name: "ابحث في الدليل" }).last().fill("العنوان الوطني");
    await page.getByRole("button", { name: "ابحث" }).click();
    await expect(page).toHaveURL(/\/ar\/search\?q=/);
    await expect(page.getByRole("link", { name: /واجهة العنوان الوطني/ }).first()).toBeVisible();
  });

  test("an English query finds GASTAT inflation datasets", async ({ page }) => {
    await page.goto("/en/search?q=inflation");
    await expect(page.getByRole("link", { name: /CPI Inflation Rate/ }).first()).toBeVisible();
  });
});

test.describe("directory", () => {
  test("the access filter narrows the list and lights its lattice", async ({ page }) => {
    await page.goto("/en/apis");
    await page.getByLabel("Access", { exact: true }).selectOption("open");
    await page.getByRole("button", { name: "Apply" }).click();
    await expect(page).toHaveURL(/access=open/);
    const rows = page.locator("section[aria-labelledby=results-count] li");
    await expect(rows.first()).toBeVisible();
    for (const label of await rows.getByRole("img").evaluateAll((nodes) => nodes.map((n) => n.getAttribute("aria-label")))) {
      expect(label).toContain("Open");
    }
    await expect(page.getByRole("link", { name: "DataSaudi statistics API" })).toBeVisible();
  });

  test("a filter with no match says so and offers a way out", async ({ page }) => {
    await page.goto("/en/apis?q=zzzzzzzz");
    await expect(page.getByText("No API matches these filters.")).toBeVisible();
  });
});

test.describe("api detail", () => {
  test("shows access, endpoints, examples and evidence", async ({ page }) => {
    await page.goto("/en/apis/datasaudi");
    await expect(page.getByRole("heading", { level: 1 })).toHaveText("DataSaudi statistics API");
    await expect(page.getByRole("img", { name: /Access: Open, 1 of 5/ }).first()).toBeVisible();
    await expect(page.locator("#query-cube")).toContainText("/data.jsonrecords");
    await page.locator("#query-cube").getByRole("tab", { name: "Python" }).click();
    await expect(page.locator("#query-cube").getByRole("tabpanel")).toContainText("import httpx");
    await expect(page.getByRole("link", { name: /api\.datasaudi\.sa\/tesseract\/cubes/ })).toBeVisible();
  });

  test("keeps code left-to-right on an Arabic page", async ({ page }) => {
    await page.goto("/ar/apis/zatca-e-invoicing");
    await expect(page.locator("html")).toHaveAttribute("dir", "rtl");
    const code = page.locator("pre").first();
    await expect(code).toBeVisible();
    expect(await code.evaluate((node) => getComputedStyle(node).direction)).toBe("ltr");
  });
});

test.describe("layout", () => {
  for (const path of ["/en", "/ar", "/en/apis", "/ar/apis/zatca-e-invoicing", "/ar/datasets/datasaudi/gastat_inflation", "/ar/agents"]) {
    test(`no horizontal overflow on ${path}`, async ({ page }) => {
      await page.goto(path);
      await page.waitForLoadState("networkidle");
      const overflow = await page.evaluate(
        () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
      );
      expect(overflow).toBeLessThanOrEqual(1);
    });
  }

  test("the first Tab reaches the skip link", async ({ page }) => {
    await page.goto("/en");
    await page.keyboard.press("Tab");
    await expect(page.getByRole("link", { name: "Skip to content" })).toBeFocused();
  });
});
