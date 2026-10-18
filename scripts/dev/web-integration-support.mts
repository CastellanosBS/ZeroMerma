import { mkdirSync, unlinkSync, writeFileSync } from "node:fs";
import { isAbsolute, join, relative } from "node:path";

type WebSurface = "pos" | "backoffice";

function required(name: string): string {
  const value = process.env[name]?.trim();
  if (!value) throw new Error(`The isolated web harness must set ${name}.`);
  return value;
}

function loopbackUrl(name: string): string {
  const url = new URL(required(name));
  if (
    url.protocol !== "https:" ||
    url.hostname !== "127.0.0.1" ||
    !url.port ||
    url.username ||
    url.password ||
    url.search ||
    url.hash ||
    url.pathname !== "/"
  ) {
    throw new Error(`${name} must be a dedicated HTTPS origin on 127.0.0.1.`);
  }
  return url.origin;
}

export function realEnvironment(surface: WebSurface) {
  if (process.env.ZM_WEB_INTEGRATION_ISOLATED !== "1") {
    throw new Error("Run real browser tests through scripts/dev/run-web-integration.ps1.");
  }
  const runId = required("ZM_E2E_RUN_ID");
  if (!/^[a-zA-Z0-9_-]+$/.test(runId)) throw new Error("Invalid isolated run identifier.");
  return {
    apiUrl: loopbackUrl("ZM_E2E_API_URL"),
    baseUrl: loopbackUrl(surface === "pos" ? "ZM_E2E_POS_URL" : "ZM_E2E_BACKOFFICE_URL"),
    email: required(surface === "pos" ? "ZM_E2E_POS_EMAIL" : "ZM_E2E_BACKOFFICE_EMAIL"),
    password: required("ZM_E2E_PASSWORD"),
    artifactDir: required("ZM_E2E_ARTIFACT_DIR"),
    runId,
  };
}

export function realPlaywrightOptions(surface: WebSurface) {
  const env = realEnvironment(surface);
  return {
    testDir: "./e2e-real",
    fullyParallel: false,
    workers: 1,
    retries: 0,
    timeout: 45_000,
    forbidOnly: true,
    outputDir: join(env.artifactDir, surface, "test-results"),
    reporter: [["../../scripts/dev/web-integration-support.mts", { surface }]] as [
      [string, { surface: WebSurface }],
    ],
    use: {
      baseURL: env.baseUrl,
      // Only the guarded disposable harness uses a one-run self-signed certificate.
      ignoreHTTPSErrors: true,
      viewport: { width: 1440, height: 1000 },
      trace: "off" as const,
      screenshot: "off" as const,
      video: "off" as const,
      serviceWorkers: "block" as const,
    },
  };
}

type ResponseObservation = {
  url(): string;
  status(): number;
  request(): { method(): string };
};
type PageObservation = {
  on(event: "response", listener: (response: ResponseObservation) => void): unknown;
};
type SaleFaultRoute = {
  request(): { method(): string };
  fetch(options: { maxRedirects: number }): Promise<{ status(): number; json(): Promise<unknown> }>;
  abort(errorCode?: string): Promise<void>;
};
type SaleRouteRegistration = (
  url: string,
  handler: (route: SaleFaultRoute) => Promise<void>,
  options: { times: number },
) => Promise<void>;
const saleFaultRegistrations = new WeakMap<object, SaleRouteRegistration>();
type ContextObservation = {
  on(event: "page", listener: (page: PageObservation) => void): unknown;
};

export type NetworkEvidence = { method: string; path: string; status: number }[];

export function observeRealApi(
  context: ContextObservation,
  page: PageObservation,
  apiUrl: string,
): NetworkEvidence {
  const evidence: NetworkEvidence = [];
  const blockInterception = (target: object) => {
    for (const method of ["route", "routeFromHAR", "routeWebSocket"]) {
      Object.defineProperty(target, method, {
        value: () => {
          throw new Error("API interception is forbidden in real integration tests.");
        },
        configurable: false,
        writable: false,
      });
    }
  };
  const observePage = (currentPage: PageObservation) => {
    const register = Reflect.get(currentPage, "route") as SaleRouteRegistration | undefined;
    if (register) saleFaultRegistrations.set(currentPage, register.bind(currentPage));
    blockInterception(currentPage);
    currentPage.on("response", (response) => {
      const url = new URL(response.url());
      if (url.origin === apiUrl && url.pathname.startsWith("/v1/")) {
        // No URL query, headers, response body, credentials or storage state is retained.
        evidence.push({
          method: response.request().method(),
          path: url.pathname.replace(/[0-9a-f]{8}-[0-9a-f-]{27,}/gi, "{id}"),
          status: response.status(),
        });
      }
    });
  };
  blockInterception(context);
  observePage(page);
  context.on("page", observePage);
  return evidence;
}

/** Lose only a real committed sale response. No fabricated response or arbitrary interception is exposed. */
export async function dropNextSaleConfirmationResponse(
  page: PageObservation,
  apiUrl: string,
  evidence: NetworkEvidence,
) {
  if (realEnvironment("pos").apiUrl !== apiUrl)
    throw new Error("Sale faults require the isolated real POS API.");
  const register = saleFaultRegistrations.get(page);
  if (!register)
    throw new Error(
      "Real API observation must be installed before injecting a sale response loss.",
    );
  let resolveCommitted!: (value: unknown) => void;
  let rejectCommitted!: (reason: unknown) => void;
  const committed = new Promise<unknown>((resolve, reject) => {
    resolveCommitted = resolve;
    rejectCommitted = reject;
  });
  await register(
    `${apiUrl}/v1/sales/confirm`,
    async (route) => {
      try {
        if (route.request().method() !== "POST")
          throw new Error("Only POST sale confirmation can lose a response.");
        const response = await route.fetch({ maxRedirects: 0 });
        if (response.status() !== 201)
          throw new Error(`Expected a real committed sale, received ${response.status()}.`);
        evidence.push({ method: "POST", path: "/v1/sales/confirm", status: 201 });
        resolveCommitted(await response.json());
      } catch (error) {
        rejectCommitted(error);
      } finally {
        await route.abort("failed");
      }
    },
    { times: 1 },
  );
  return { committed };
}

/** Lose only a real committed return response. No fabricated response or arbitrary interception is exposed. */
export async function dropNextReturnConfirmationResponse(
  page: PageObservation,
  apiUrl: string,
  evidence: NetworkEvidence,
) {
  if (realEnvironment("pos").apiUrl !== apiUrl)
    throw new Error("Return faults require the isolated real POS API.");
  const register = saleFaultRegistrations.get(page);
  if (!register)
    throw new Error(
      "Real API observation must be installed before injecting a return response loss.",
    );
  let resolveCommitted!: (value: unknown) => void;
  let rejectCommitted!: (reason: unknown) => void;
  const committed = new Promise<unknown>((resolve, reject) => {
    resolveCommitted = resolve;
    rejectCommitted = reject;
  });
  await register(
    `${apiUrl}/v1/returns/commit`,
    async (route) => {
      try {
        if (route.request().method() !== "POST")
          throw new Error("Only POST return confirmation can lose a response.");
        const response = await route.fetch({ maxRedirects: 0 });
        if (response.status() !== 201)
          throw new Error(`Expected a real committed return, received ${response.status()}.`);
        evidence.push({ method: "POST", path: "/v1/returns/commit", status: 201 });
        resolveCommitted(await response.json());
      } catch (error) {
        rejectCommitted(error);
      } finally {
        await route.abort("failed");
      }
    },
    { times: 1 },
  );
  return { committed };
}

/** Fault only an allowlisted order command after its real transaction committed. */
export async function dropNextOrderCommandResponse(
  page: PageObservation,
  apiUrl: string,
  evidence: NetworkEvidence,
  path: string,
) {
  if (
    realEnvironment("pos").apiUrl !== apiUrl ||
    !/^\/v1\/(?:orders|admin\/orders)(?:\/[0-9a-f-]{36}\/(?:mark-ready|deliver|cancel))?$/.test(
      path,
    ) ||
    path === "/v1/admin/orders"
  ) {
    throw new Error("Order faults require an allowlisted isolated command path.");
  }
  const register = saleFaultRegistrations.get(page);
  if (!register)
    throw new Error(
      "Real API observation must be installed before injecting an order response loss.",
    );
  let resolveCommitted!: (value: unknown) => void;
  let rejectCommitted!: (reason: unknown) => void;
  const committed = new Promise<unknown>((resolve, reject) => {
    resolveCommitted = resolve;
    rejectCommitted = reject;
  });
  await register(
    `${apiUrl}${path}`,
    async (route) => {
      try {
        if (route.request().method() !== "POST")
          throw new Error("Only POST order commands can lose a response.");
        const response = await route.fetch({ maxRedirects: 0 });
        const expected = path === "/v1/orders" ? 201 : 200;
        if (response.status() !== expected)
          throw new Error(
            `Expected a real committed order command, received ${response.status()}.`,
          );
        evidence.push({
          method: "POST",
          path: path.replace(/[0-9a-f]{8}-[0-9a-f-]{27,}/gi, "{id}"),
          status: expected,
        });
        resolveCommitted(await response.json());
      } catch (error) {
        rejectCommitted(error);
      } finally {
        await route.abort("failed");
      }
    },
    { times: 1 },
  );
  return { committed };
}

/** Fault only an allowlisted cash command after its real transaction committed. */
export async function dropNextCashCommandResponse(
  page: PageObservation,
  apiUrl: string,
  evidence: NetworkEvidence,
  path: string,
) {
  if (
    realEnvironment("pos").apiUrl !== apiUrl ||
    !["/v1/cash-sessions/open", "/v1/payments", "/v1/discounts", "/v1/cash-close/commit"].includes(
      path,
    )
  ) {
    throw new Error("Cash faults require an allowlisted isolated command path.");
  }
  const register = saleFaultRegistrations.get(page);
  if (!register)
    throw new Error(
      "Real API observation must be installed before injecting an cash response loss.",
    );
  let resolveCommitted!: (value: unknown) => void;
  let rejectCommitted!: (reason: unknown) => void;
  const committed = new Promise<unknown>((resolve, reject) => {
    resolveCommitted = resolve;
    rejectCommitted = reject;
  });
  await register(
    `${apiUrl}${path}`,
    async (route) => {
      try {
        if (route.request().method() !== "POST")
          throw new Error("Only POST cash commands can lose a response.");
        const response = await route.fetch({ maxRedirects: 0 });
        const expected = path === "/v1/cash-close/commit" ? 200 : 201;
        if (response.status() !== expected)
          throw new Error(`Expected a real committed cash command, received ${response.status()}.`);
        evidence.push({
          method: "POST",
          path: path.replace(/[0-9a-f]{8}-[0-9a-f-]{27,}/gi, "{id}"),
          status: expected,
        });
        resolveCommitted(await response.json());
      } catch (error) {
        rejectCommitted(error);
      } finally {
        await route.abort("failed");
      }
    },
    { times: 1 },
  );
  return { committed };
}

function sanitize(value: string): string {
  let result = value;
  for (const name of [
    "ZM_E2E_PASSWORD",
    "ZM_E2E_POS_EMAIL",
    "ZM_E2E_BACKOFFICE_EMAIL",
    "ZM_E2E_ORDER_OPERATOR_EMAIL",
  ]) {
    const secret = process.env[name];
    if (secret) result = result.split(secret).join("[REDACTED]");
  }
  return result
    .replace(/Bearer\s+[^\s"']+/gi, "Bearer [REDACTED]")
    .replace(/(__Host-zm-(?:pos|backoffice)-session=)[^;\s"']+/gi, "$1[REDACTED]")
    .replace(/("(?:csrf_token|credential|reset_token)"\s*:\s*")[^"]+/gi, "$1[REDACTED]")
    .replace(/eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+/g, "[REDACTED JWT]");
}

// Raw Playwright traces and HTML/JSON reporters can retain login payloads. This
// reporter writes a deliberately minimal result plus the separately sanitized API log.
export default class SafeWebIntegrationReporter {
  private readonly results: {
    title: string;
    status: string;
    durationMs: number;
    errors: string[];
  }[] = [];
  private readonly surface: WebSurface;

  constructor(options: { surface: WebSurface }) {
    this.surface = options.surface;
  }

  onTestEnd(
    test: { titlePath(): string[] },
    result: {
      status: string;
      duration: number;
      errors: { message?: string }[];
      attachments: { name: string; body?: Buffer; path?: string }[];
    },
  ) {
    const entry = {
      title: sanitize(test.titlePath().filter(Boolean).join(" > ")),
      status: result.status,
      durationMs: result.duration,
      errors: result.errors.map((error) => sanitize(error.message ?? "Unknown browser failure")),
    };
    this.results.push(entry);
    const directory = join(realEnvironment(this.surface).artifactDir, this.surface);
    mkdirSync(directory, { recursive: true });
    for (const attachment of result.attachments) {
      // Playwright creates a DOM error-context Markdown file even with tracing off.
      // Keep only the approved sanitized evidence, never that raw page snapshot.
      if (attachment.name === "error-context" && attachment.path) {
        const childPath = relative(join(directory, "test-results"), attachment.path);
        if (childPath.startsWith("..") || isAbsolute(childPath)) {
          throw new Error(
            "Refusing to remove an attachment outside the isolated output directory.",
          );
        }
        unlinkSync(attachment.path);
      }
      if (["sanitized-network", "route-coverage"].includes(attachment.name) && attachment.body) {
        writeFileSync(
          join(directory, `${this.results.length}-${attachment.name}.json`),
          sanitize(attachment.body.toString("utf8")),
        );
      }
    }
    process.stdout.write(`${entry.status}: ${entry.title}\n`);
    for (const error of entry.errors) process.stdout.write(`${error}\n`);
  }

  onError(error: { message?: string }) {
    process.stderr.write(`${sanitize(error.message ?? "Unknown Playwright failure")}\n`);
  }

  onEnd(result: { status: string }) {
    const env = realEnvironment(this.surface);
    const directory = join(env.artifactDir, this.surface);
    mkdirSync(directory, { recursive: true });
    writeFileSync(
      join(directory, "results.json"),
      JSON.stringify(
        {
          runId: env.runId,
          status: result.status,
          tests: this.results,
        },
        null,
        2,
      ),
    );
  }
}
