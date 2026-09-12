import type { Page, Route } from "@playwright/test";

const bootstrapResponse = {
  branch: {
    code: "MAIN",
    name: "Main Branch",
    timezone: "America/Hermosillo",
  },
  local_timestamp: "2026-04-13T10:00:00Z",
  user: {
    email: "cashier@zeromerma.local",
    default_surface: "POS",
    allowed_surfaces: ["POS"],
    full_name: "Main Branch Cashier",
    id: "user-1",
  },
  workstation: {
    code: "POS-01",
    name: "Front Register 01",
  },
};

const activeCashSession = {
  id: "cash-session-1",
  status: "OPEN",
  opening_amount: "500.00",
  opened_at: "2026-04-13T09:00:00Z",
  user_id: "user-1",
  workstation_code: "POS-01",
};

const posCatalogResponse = {
  classes: [
    {
      capture_mode_default: "CLASS_CAPTURE",
      class_capture_unit_price: "12.00",
      code: "PAN-DULCE",
      currency_code: "MXN",
      display_order: 10,
      id: "class-pan-dulce",
      name: "Pan dulce",
      product_count: 0,
      quick_name: "Pan dulce",
    },
  ],
};

const saleDetailResponse = {
  change_amount: "26.00",
  id: "sale-1",
  payments: [{ payment_method_code: "CASH" }],
  total_amount: "24.00",
};

const ticketDetailResponse = {
  branch: {
    timezone: "America/Hermosillo",
  },
  can_reprint: true,
  cash_session_id: "cash-session-1",
  change_amount: "26.00",
  confirmed_at: "2026-04-13T10:05:00Z",
  currency_code: "MXN",
  folio: "TCK-SALE",
  id: "sale-1",
  item_count: 1,
  lines: [],
  operator: {
    full_name: "Main Branch Cashier",
  },
  paid_amount: "50.00",
  payments: [],
  status: "CONFIRMED",
  subtotal_amount: "24.00",
  total_amount: "24.00",
  total_quantity: "2.000",
  workstation: {
    code: "POS-01",
    name: "Front Register 01",
  },
};

async function fulfillJson(route: Route, body: unknown, status = 200) {
  await route.fulfill({
    body: JSON.stringify(body),
    contentType: "application/json",
    status,
  });
}

export async function installPosApiMocks(
  page: Page,
  options?: {
    hasActiveCashSession?: boolean;
  },
) {
  let currentCashSession = options?.hasActiveCashSession ? activeCashSession : null;

  await page.route("**/v1/auth/login", async (route) => {
    await fulfillJson(route, {
      access_token: "test-access-token",
      token_type: "bearer",
      user: bootstrapResponse.user,
    });
  });

  await page.route("**/v1/pos/bootstrap**", async (route) => {
    await fulfillJson(route, bootstrapResponse);
  });

  await page.route("**/v1/cash-sessions/current**", async (route) => {
    await fulfillJson(route, currentCashSession);
  });

  await page.route("**/v1/cash-sessions/open", async (route) => {
    currentCashSession = activeCashSession;
    await fulfillJson(route, activeCashSession);
  });

  await page.route("**/v1/orders**", async (route) => {
    await fulfillJson(route, {
      orders: [],
    });
  });

  await page.route("**/v1/transfers/inbound/pending**", async (route) => {
    await fulfillJson(route, {
      transfers: [],
    });
  });

  await page.route("**/v1/cash-close/summary**", async (route) => {
    await fulfillJson(route, {
      blockers: [],
      warnings: [],
    });
  });

  await page.route("**/v1/pos/catalog**", async (route) => {
    await fulfillJson(route, posCatalogResponse);
  });

  await page.route("**/v1/sales/confirm", async (route) => {
    await fulfillJson(route, saleDetailResponse);
  });

  await page.route("**/v1/tickets/sale-1**", async (route) => {
    await fulfillJson(route, ticketDetailResponse);
  });
}
