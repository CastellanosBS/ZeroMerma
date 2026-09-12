import { test as base, expect } from "@playwright/test";
import {
  observeRealApi,
  realEnvironment,
  type NetworkEvidence,
} from "../../../scripts/dev/web-integration-support.mjs";

export const environment = realEnvironment("backoffice");
export const test = base.extend<{ network: NetworkEvidence }>({
  network: [
    async ({ context, page }, use, testInfo) => {
      const network = observeRealApi(context, page, environment.apiUrl);
      await use(network);
      await testInfo.attach("sanitized-network", {
        body: JSON.stringify(network, null, 2),
        contentType: "application/json",
      });
    },
    { auto: true },
  ],
});
export { expect };
