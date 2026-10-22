import { defineConfig, devices } from "@playwright/test";

// The tests run against the production build, the real API and a migrated, synced
// database (docs/development/web.md). Start them first, or set WEB_BASE_URL.
export default defineConfig({
  testDir: "./tests/e2e",
  fullyParallel: true,
  // One local API process serves every page's requests; more workers than this queue
  // behind it and time out rather than test anything.
  workers: 2,
  forbidOnly: Boolean(process.env.CI),
  retries: 0,
  reporter: [["list"]],
  // Pages stream catalogue data from the API after the shell; allow for a loaded machine.
  expect: { timeout: 15_000 },
  use: {
    baseURL: process.env.WEB_BASE_URL ?? "http://127.0.0.1:3000",
    trace: "retain-on-failure",
  },
  projects: [
    { name: "desktop", use: { ...devices["Desktop Chrome"] } },
    { name: "mobile", use: { ...devices["Pixel 7"] } },
  ],
});
