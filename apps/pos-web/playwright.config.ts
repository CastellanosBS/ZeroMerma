import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  // Component-oriented browser coverage; real API tests use playwright.real.config.ts.
  testDir: "./e2e",
  fullyParallel: true,
  workers: 2,
  reporter: "list",
  use: {
    actionTimeout: 15_000,
    baseURL: "http://127.0.0.1:5173",
    trace: "on-first-retry",
  },
  webServer: {
    command: "corepack pnpm exec vite --host 127.0.0.1 --port 5173 --strictPort",
    url: "http://127.0.0.1:5173",
    reuseExistingServer: false,
    env: { VITE_API_BASE_URL: "http://127.0.0.1:9" },
    timeout: 120_000,
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
});
