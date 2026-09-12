import { defineConfig } from "@playwright/test";
import { realPlaywrightOptions } from "../../scripts/dev/web-integration-support.mjs";

export default defineConfig({
  ...realPlaywrightOptions("pos"),
  projects: [{ name: "real-chromium", use: { browserName: "chromium" } }],
});
