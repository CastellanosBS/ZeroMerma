import { mkdirSync } from "node:fs";
import path from "node:path";

import { expect, test, type Page, type Route } from "@playwright/test";

const branch = {
  brand_key: "EMP",
  code: "MAIN",
  name: "Sucursal Centro",
  timezone: "America/Hermosillo",
};

const workstation = {
  code: "POS-01",
  name: "Caja 01",
};

const user = {
  full_name: "Ana Cajera",
  id: "user-1",
};

const posBootstrap = {
  branch,
  user,
  workstation,
};

const activeCashSession = {
  id: "cash-session-1",
  opening_amount: "500.00",
  opened_at: "2026-04-15T08:00:00Z",
  user_id: user.id,
  workstation_code: workstation.code,
};

const categoryCatalog = [
  { code: "SUPPLIES", display_order: 10, name: "Insumos" },
  { code: "SERVICES", display_order: 20, name: "Servicios" },
];

const paymentMethods = [
  { affects_cash_drawer: true, code: "CASH", is_enabled: true, label: "Efectivo" },
  { affects_cash_drawer: false, code: "CARD", is_enabled: true, label: "Tarjeta" },
  { affects_cash_drawer: false, code: "MIXED", is_enabled: false, label: "Mixto" },
];

const discountMethods = [
  { affects_cash_drawer: true, code: "CASH", is_enabled: true, label: "Efectivo" },
  { affects_cash_drawer: false, code: "CARD", is_enabled: true, label: "Tarjeta" },
  { affects_cash_drawer: false, code: "MIXED", is_enabled: false, label: "Mixto" },
];

const operationsClass = {
  code: "PAN-DULCE",
  display_order: 10,
  id: "class-pan-dulce",
  name: "Pan dulce",
};

const operationsProduct = {
  code: "CONCHA-VAN",
  display_order: 10,
  id: "product-concha",
  name: "Concha vainilla",
};

const orderListItem = {
  advance_amount: "60.00",
  created_at_utc: "2026-04-15T10:00:00Z",
  customer_name: "Maria Lopez",
  customer_phone: "6621234567",
  folio: "PED-1001",
  id: "order-1",
  line_count: 2,
  remaining_balance_amount: "120.00",
  requested_for_at: "2026-04-15T18:30:00Z",
  status: "PENDING",
  total_amount: "180.00",
  total_units: "15",
};

const orderDetail = {
  ...orderListItem,
  branch,
  can_cancel: true,
  can_deliver: false,
  can_mark_ready: true,
  items: [
    {
      id: "order-item-1",
      line_total_amount: "144.00",
      product_name_snapshot: "Concha vainilla",
      quantity: "12",
    },
    {
      id: "order-item-2",
      line_total_amount: "36.00",
      product_name_snapshot: "Oreja",
      quantity: "3",
    },
  ],
  notes: "Entregar a las 18:30.",
  requires_settlement_on_delivery: true,
};

const ticketListItem = {
  change_amount: "26.00",
  confirmed_at: "2026-04-15T11:00:00Z",
  folio: "TK-5001",
  id: "ticket-1",
  item_count: 2,
  operator_full_name: "Ana Cajera",
  payment_summary: [{ payment_method_code: "CASH" }],
  total_amount: "94.00",
  total_quantity: "4",
};

const ticketDetail = {
  ...ticketListItem,
  branch,
  can_reprint: true,
  has_returnable_quantity: true,
  lines: [
    {
      id: "ticket-line-1",
      line_total_amount: "72.00",
      name: "Concha vainilla",
      quantity: "3",
      unit_price: "24.00",
    },
    {
      id: "ticket-line-2",
      line_total_amount: "22.00",
      name: "Cafe americano",
      quantity: "1",
      unit_price: "22.00",
    },
  ],
  operator: {
    full_name: "Ana Cajera",
  },
  payments: [
    {
      applied_amount: "94.00",
      change_amount: "26.00",
      id: "ticket-payment-1",
      payment_method_code: "CASH",
      tendered_amount: "120.00",
    },
  ],
  status: "CONFIRMED",
  workstation,
};

const returnSaleSearchItem = {
  confirmed_at: "2026-04-15T09:30:00Z",
  folio: "TK-5001",
  has_returnable_quantity: true,
  id: "sale-1",
  item_count: 1,
  operator_full_name: "Ana Cajera",
  total_amount: "72.00",
  total_quantity: "6",
};

const returnSaleDetail = {
  branch,
  has_returnable_lines: true,
  change_amount: "0.00",
  confirmed_at: "2026-04-15T09:30:00Z",
  folio: "TK-5001",
  lines: [
    {
      already_returned_quantity: "0",
      capture_mode: "PRODUCT_DIRECT",
      catalog_name_snapshot: "Concha vainilla",
      id: "sale-line-1",
      product_class_id: "class-pan-dulce",
      product_class_name: "Pan dulce",
      product_name: "Concha vainilla",
      quantity: "6",
      remaining_returnable_quantity: "2",
      requires_exact_product_selection: false,
      sequence: 1,
      unit_price: "12.00",
    },
  ],
  operator: {
    full_name: "Ana Cajera",
  },
  paid_amount: "72.00",
  total_amount: "72.00",
};

const correctionSearchDocument = {
  committed_at_utc: "2026-04-15T08:45:00Z",
  correction_count: 0,
  destination_branch_name: "Sucursal Norte",
  display_title: "ENV-2001",
  folio: "ENV-2001",
  document_type: "BRANCH_TRANSFER_SHIPMENT",
  id: "correction-target-1",
  source_branch_name: "Sucursal Centro",
  workstation_name: "Caja 01",
};

const correctionTargetDetail = {
  applied_corrections: [],
  blocking_reason: null,
  document_title: "ENV-2001",
  is_correctable: true,
  target_document: {
    committed_at_utc: "2026-04-15T08:45:00Z",
    destination_branch_name: "Sucursal Norte",
    document_type: "BRANCH_TRANSFER_SHIPMENT",
    lines: [
      {
        id: "correction-line-1",
        line_number: 1,
        product_class_code_snapshot: "PAN-DULCE",
        product_class_id: "class-pan-dulce",
        product_class_name_snapshot: "Pan dulce",
        product_code_snapshot: "CONCHA-VAN",
        product_id: "product-concha",
        product_name_snapshot: "Concha vainilla",
        quantity: "6",
      },
    ],
    source_branch_name: "Sucursal Centro",
    workstation_name: "Caja 01",
  },
};

const paymentListItem = {
  affects_cash_drawer: true,
  category_name: "Insumos",
  concept: "Insumos",
  created_at_utc: "2026-04-15T12:00:00Z",
  folio: "PAG-2001",
  id: "payment-1",
  operator_full_name: "Ana Cajera",
  payee_name: "Distribuidora Norte",
  payment_method_code: "CASH",
  total_amount: "250.00",
};

const paymentDetail = {
  ...paymentListItem,
  branch,
  committed_at_utc: "2026-04-15T12:00:00Z",
  created_by: {
    full_name: "Ana Cajera",
  },
  notes: "Reposicion urgente de insumos.",
};

const discountListItem = {
  affects_cash_drawer: false,
  category_name: "Personal",
  concept: "Personal",
  created_at_utc: "2026-04-15T13:00:00Z",
  folio: "DES-3001",
  id: "discount-1",
  operator_full_name: "Ana Cajera",
  payment_method_code: "CARD",
  subject_name: "Equipo de reparto",
  total_amount: "180.00",
};

const discountDetail = {
  ...discountListItem,
  branch,
  committed_at_utc: "2026-04-15T13:00:00Z",
  created_by: {
    full_name: "Ana Cajera",
  },
  notes: "Cargo interno por reposicion.",
};

const pendingInboundTransfer = {
  committed_at_utc: "2026-04-15T09:15:00Z",
  created_at_utc: "2026-04-15T09:00:00Z",
  destination_branch_name: branch.name,
  expected_total_quantity: "12",
  folio: "ENV-3101",
  id: "transfer-1",
  line_count: 1,
  source_branch_code: "NORTE",
  source_branch_name: "Sucursal Norte",
  status: "IN_TRANSIT",
};

const inboundTransferDetail = {
  shipment: {
    committed_at_utc: "2026-04-15T09:15:00Z",
    created_at_utc: "2026-04-15T09:00:00Z",
    destination_branch_name: branch.name,
    id: "transfer-1",
    lines: [
      {
        expected_quantity: "12",
        id: "transfer-line-1",
        line_number: 1,
        product_class_name_snapshot: "Pan dulce",
        product_code_snapshot: "CONCHA-VAN",
        product_name_snapshot: "Concha vainilla",
        quantity: "12",
      },
    ],
    notes: "Recibir en cuanto llegue el surtido.",
    source_branch_name: "Sucursal Norte",
    status: "IN_TRANSIT",
  },
  shipment_summary: {
    folio: "ENV-3101",
  },
};

const cashCloseBootstrap = {
  baseline_snapshot: {
    captured_at_utc: "2026-04-15T19:00:00Z",
    is_available: true,
    is_first_controlled_close: false,
    latest_snapshot_id: "snapshot-1",
    snapshot_type: "COUNTER_BASELINE",
    source_cash_session_close_id: null,
  },
  blockers: [],
  branch,
  branch_brand_key: branch.brand_key,
  can_start_close: true,
  current_open_cash_session: activeCashSession,
  local_timestamp: "2026-04-15T19:30:00Z",
  payment_method_catalog: [
    {
      currency_code: "MXN",
      display_order: 10,
      is_active: true,
      is_expected_supported: true,
      payment_method_code: "CASH",
    },
    {
      currency_code: "MXN",
      display_order: 20,
      is_active: true,
      is_expected_supported: true,
      payment_method_code: "CARD",
    },
  ],
  pending_class_capture: {
    has_pending_class_capture: true,
    pending_class_capture_classes_count: 1,
    pending_class_capture_total_quantity: "5.000",
  },
  user,
  warnings: [],
  workstation,
};

const cashCloseSummary = {
  baseline_snapshot: cashCloseBootstrap.baseline_snapshot,
  blockers: [],
  can_start_close: true,
  cash_session: activeCashSession,
  currency_code: "MXN",
  expected_cash_amount: "180.00",
  movement_breakdown: [],
  opening_amount: activeCashSession.opening_amount,
  pending_class_capture: cashCloseBootstrap.pending_class_capture,
  reconciliation_status: "REVIEW_REQUIRED",
  total_cash_in: "205.00",
  total_cash_out: "10.00",
  warnings: [],
};

const cashClosePreview = {
  blockers: [],
  class_reconciliations: [],
  discrepancy_resolutions: [],
  expected_cash_amount: "650.00",
  generated_discrepancy_documents: [],
  payment_method_rows: [
    {
      expected_amount: "650.00",
      payment_method_code: "CASH",
      variance_amount: "0.00",
    },
    {
      expected_amount: "0.00",
      payment_method_code: "CARD",
      variance_amount: "0.00",
    },
  ],
  reconciliation_status: "READY",
  warnings: [],
};

function buildJsonResponse(body: unknown, status = 200) {
  return {
    body: JSON.stringify(body),
    contentType: "application/json",
    status,
  };
}

async function fulfillJson(route: Route, body: unknown, status = 200) {
  await route.fulfill(buildJsonResponse(body, status));
}

async function installAuthSession(page: Page) {
  await page.addInitScript(() => {
    window.localStorage.setItem(
      "zeromerma-pos-auth",
      JSON.stringify({
        state: {
          accessToken: "test-access-token",
        },
        version: 0,
      }),
    );
  });
}

async function installApiMocks(page: Page) {
  await page.route("**/v1/**", async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    const pathname = url.pathname;

    if (pathname === "/v1/pos/bootstrap") {
      await fulfillJson(route, posBootstrap);
      return;
    }

    if (pathname === "/v1/cash-sessions/current") {
      await fulfillJson(route, activeCashSession);
      return;
    }

    if (pathname === "/v1/pos/catalog") {
      await fulfillJson(route, { classes: [operationsClass] });
      return;
    }

    if (pathname === "/v1/pos/classes/class-pan-dulce/products") {
      await fulfillJson(route, {
        products: [
          {
            ...operationsProduct,
            unit_price: "24.00",
          },
        ],
      });
      return;
    }

    if (pathname === "/v1/transfers/inbound/pending") {
      await fulfillJson(route, { transfers: [pendingInboundTransfer] });
      return;
    }

    if (pathname === "/v1/transfers/transfer-1") {
      await fulfillJson(route, inboundTransferDetail);
      return;
    }

    if (pathname === "/v1/cash-close/summary") {
      await fulfillJson(route, cashCloseSummary);
      return;
    }

    if (pathname === "/v1/cash-close/bootstrap") {
      await fulfillJson(route, cashCloseBootstrap);
      return;
    }

    if (pathname === "/v1/cash-close/preview" && request.method() === "POST") {
      await fulfillJson(route, cashClosePreview);
      return;
    }

    if (pathname === "/v1/operations/bootstrap") {
      await fulfillJson(route, {
        branch,
        local_timestamp: "2026-04-15T19:30:00Z",
        waste_controls: {
          attachment_evidence_supported: false,
          high_impact_quantity_threshold: "10",
          high_impact_requires_acknowledgement: true,
          high_impact_requires_note: true,
          stock_validated_source_bucket_codes: ["COUNTER"],
        },
        destination_branches: [
          { code: "NORTE", id: "branch-north", name: "Sucursal Norte" },
          { code: "SUR", id: "branch-south", name: "Sucursal Sur" },
        ],
        waste_reasons: [
          { code: "EXPIRED", name: "Caducado" },
          { code: "DAMAGED", name: "Danado" },
        ],
        user,
        workstation,
      });
      return;
    }

    if (pathname === "/v1/operations/catalog") {
      await fulfillJson(route, { classes: [operationsClass] });
      return;
    }

    if (pathname === "/v1/operations/classes/class-pan-dulce/products") {
      await fulfillJson(route, { products: [operationsProduct] });
      return;
    }

    if (pathname === "/v1/orders/bootstrap") {
      await fulfillJson(route, {
        branch,
        status_counters: [
          { count: 1, status: "PENDING" },
          { count: 0, status: "READY" },
          { count: 0, status: "DELIVERED" },
          { count: 0, status: "CANCELED" },
        ],
        user,
        workstation,
      });
      return;
    }

    if (pathname === "/v1/orders" && request.method() === "GET") {
      await fulfillJson(route, { orders: [orderListItem] });
      return;
    }

    if (pathname === "/v1/orders/catalog") {
      await fulfillJson(route, { classes: [operationsClass] });
      return;
    }

    if (pathname === "/v1/orders/classes/class-pan-dulce/products") {
      await fulfillJson(route, {
        products: [
          {
            ...operationsProduct,
            unit_price: "12.00",
          },
        ],
      });
      return;
    }

    if (pathname === "/v1/orders/order-1") {
      await fulfillJson(route, orderDetail);
      return;
    }

    if (pathname === "/v1/tickets/bootstrap") {
      await fulfillJson(route, {
        available_scopes: [
          { code: "CURRENT_SHIFT", label: "Turno actual" },
          { code: "TODAY", label: "Hoy" },
          { code: "RECENT", label: "Recientes" },
        ],
        branch,
        default_scope: "CURRENT_SHIFT",
        user,
        workstation,
      });
      return;
    }

    if (pathname === "/v1/tickets") {
      await fulfillJson(route, { tickets: [ticketListItem] });
      return;
    }

    if (pathname === "/v1/tickets/ticket-1") {
      await fulfillJson(route, ticketDetail);
      return;
    }

    if (pathname === "/v1/returns/bootstrap") {
      await fulfillJson(route, {
        available_scopes: [
          { code: "CURRENT_SHIFT", label: "Turno actual" },
          { code: "TODAY", label: "Hoy" },
          { code: "RECENT", label: "Recientes" },
        ],
        branch,
        default_scope: "CURRENT_SHIFT",
        current_open_cash_session: activeCashSession,
        local_timestamp: "2026-04-15T19:30:00Z",
        refund_methods: [
          { availability_note: null, code: "CASH", is_enabled: true, label: "Efectivo" },
          {
            availability_note: "Reverso de tarjeta pendiente de integracion.",
            code: "CARD",
            is_enabled: false,
            label: "Tarjeta",
          },
        ],
        return_controls: {
          high_refund_amount_threshold: "200.00",
          high_risk_requires_acknowledgement: true,
          old_sale_days_threshold: 7,
        },
        return_operations_allowed: true,
        return_reasons: [
          { code: "WRONG_ITEM", label: "Producto incorrecto" },
          { code: "QUALITY_ISSUE", label: "Problema de calidad" },
        ],
        user,
      });
      return;
    }

    if (pathname === "/v1/returns/search-sales") {
      await fulfillJson(route, { sales: [returnSaleSearchItem] });
      return;
    }

    if (pathname === "/v1/returns/sales/sale-1") {
      await fulfillJson(route, returnSaleDetail);
      return;
    }

    if (pathname === "/v1/corrections/bootstrap") {
      await fulfillJson(route, {
        branch,
        correction_controls: {
          high_impact_quantity_threshold: "10",
          high_impact_requires_acknowledgement: true,
        },
        correction_operations_allowed: true,
        current_open_cash_session: activeCashSession,
        local_timestamp: "2026-04-15T19:30:00Z",
        workstation,
        correction_reasons: [
          { code: "COUNT_MISMATCH", name: "Descuadre de conteo" },
          { code: "WRONG_DESTINATION", name: "Wrong Destination" },
          { code: "OTHER", name: "Otro motivo" },
        ],
        destination_branches: [
          {
            id: "branch-north",
            code: "NORTE",
            name: "Sucursal Norte",
            timezone: branch.timezone,
            brand_key: branch.brand_key,
          },
          {
            id: "branch-south",
            code: "SUR",
            name: "Sucursal Sur",
            timezone: branch.timezone,
            brand_key: branch.brand_key,
          },
        ],
        user,
      });
      return;
    }

    if (pathname === "/v1/corrections/search") {
      await fulfillJson(route, { documents: [correctionSearchDocument] });
      return;
    }

    if (pathname === "/v1/corrections/correction-target-1") {
      await fulfillJson(route, correctionTargetDetail);
      return;
    }

    if (pathname === "/v1/corrections/products") {
      await fulfillJson(route, { products: [] });
      return;
    }

    if (pathname === "/v1/payments/bootstrap") {
      await fulfillJson(route, {
        active_categories: categoryCatalog,
        active_payment_methods: paymentMethods,
        available_scopes: [
          { code: "CURRENT_SHIFT", label: "Turno actual" },
          { code: "TODAY", label: "Hoy" },
          { code: "RECENT", label: "Recientes" },
        ],
        branch,
        current_open_cash_session: activeCashSession,
        default_scope: "CURRENT_SHIFT",
        local_timestamp: "2026-04-15T19:30:00Z",
        payment_registration_allowed: true,
        user,
        workstation,
      });
      return;
    }

    if (pathname === "/v1/payments" && request.method() === "GET") {
      await fulfillJson(route, { payments: [paymentListItem] });
      return;
    }

    if (pathname === "/v1/payments/payment-1") {
      await fulfillJson(route, paymentDetail);
      return;
    }

    if (pathname === "/v1/discounts/bootstrap") {
      await fulfillJson(route, {
        active_categories: [
          { code: "STAFF", display_order: 10, name: "Personal" },
          { code: "OTHER", display_order: 20, name: "Otros" },
        ],
        active_discount_methods: discountMethods,
        branch,
        user,
      });
      return;
    }

    if (pathname === "/v1/discounts" && request.method() === "GET") {
      await fulfillJson(route, { discounts: [discountListItem] });
      return;
    }

    if (pathname === "/v1/discounts/discount-1") {
      await fulfillJson(route, discountDetail);
      return;
    }

    await route.fulfill(buildJsonResponse({ message: `Unhandled mock for ${pathname}` }, 404));
  });
}

async function openModule(page: Page, modulePath: string, waitForText: string) {
  await page.goto(modulePath);
  await page.locator("main").getByText(waitForText, { exact: false }).first().waitFor();
  await page.waitForLoadState("networkidle");
  await page.waitForTimeout(250);
}

async function saveModuleScreenshot(page: Page, filename: string) {
  const screenshotDirectory = test.info().outputPath("screenshots");
  mkdirSync(screenshotDirectory, { recursive: true });
  await page.screenshot({
    fullPage: false,
    path: path.join(screenshotDirectory, filename),
  });
}

test.describe.configure({ mode: "serial" });

test("captures operational module screenshots", async ({ page }) => {
  test.setTimeout(240_000);
  await installAuthSession(page);
  await installApiMocks(page);
  await page.setViewportSize({ height: 1000, width: 1600 });

  await openModule(page, "/pos", "Punto de venta");
  await page.locator("button:has-text('Pan dulce')").first().click();
  await page.getByPlaceholder("0", { exact: true }).first().fill("4");
  await page.getByRole("button", { name: "Agregar" }).click();
  await saveModuleScreenshot(page, "pos.png");

  await openModule(page, "/enviar-a-sucursal", "Enviar a sucursal");
  await page.getByLabel("Sucursal destino").selectOption("branch-north");
  await page.locator("button:has-text('Pan dulce')").first().click();
  await page.locator("button:has-text('Concha vainilla')").first().click();
  await page.getByRole("textbox", { name: "Cantidad", exact: true }).fill("12");
  await page.getByRole("button", { name: "Agregar linea", exact: true }).click();
  await saveModuleScreenshot(page, "enviar-a-sucursal.png");

  await openModule(page, "/pedidos", "Pedidos");
  await page.getByRole("button", { name: "Nuevo pedido" }).click();
  await page.getByPlaceholder("Nombre del cliente").fill("Maria Lopez");
  await page.getByPlaceholder("Telefono").fill("6621234567");
  const pickupDate = new Date(Date.now() + 86_400_000).toISOString().slice(0, 10);
  await page.locator("input[type='date']").first().fill(pickupDate);
  await page.getByPlaceholder("00", { exact: true }).nth(0).fill("12");
  await page.getByPlaceholder("00", { exact: true }).nth(1).fill("00");
  await page.locator("button:has-text('Pan dulce')").first().click();
  await page.locator("button:has-text('Concha vainilla')").first().click();
  await page.getByPlaceholder("0", { exact: true }).first().fill("12");
  await page.getByRole("button", { name: "Agregar linea" }).click();
  await saveModuleScreenshot(page, "pedidos.png");

  await openModule(page, "/tickets", "Tickets");
  await page.getByRole("row").filter({ hasText: "TK-5001" }).click();
  await page.getByRole("button", { name: "Iniciar devolucion" }).waitFor();
  await saveModuleScreenshot(page, "tickets.png");

  await openModule(page, "/devoluciones", "Devoluciones");
  await page.getByRole("row").filter({ hasText: "TK-5001" }).click();
  const returnQuantity = page.getByRole("textbox", {
    name: "Cantidad a devolver de Concha vainilla",
  });
  await returnQuantity.click();
  await returnQuantity.fill("1");
  await expect(returnQuantity).toHaveValue("1");
  await saveModuleScreenshot(page, "devoluciones.png");

  await openModule(page, "/correcciones", "Ajustes");
  await page.getByRole("row").filter({ hasText: "ENV-2001" }).click();
  await page
    .getByRole("button", { name: /^Editar cantidad de/ })
    .first()
    .click();
  await page.waitForTimeout(300);
  await saveModuleScreenshot(page, "correcciones.png");

  await openModule(page, "/pagos", "Pagos operativos");
  await page.getByRole("button", { name: "Nuevo pago" }).click();
  await page.getByLabel("Beneficiario").fill("Distribuidora Norte");
  await page.getByLabel("Categoria").selectOption("SUPPLIES");
  await page.getByLabel("Monto").fill("250");
  await page.getByRole("button", { name: /Efectivo/ }).click();
  await saveModuleScreenshot(page, "pagos.png");

  await page.goto("/descuentos");
  await expect(page).toHaveURL(/\/pos$/);
  await saveModuleScreenshot(page, "discounts-release-redirect.png");

  await openModule(page, "/recibir-envio", "Recibir envio");
  await page.getByRole("row").filter({ hasText: "ENV-3101" }).click();
  await saveModuleScreenshot(page, "recibir-envio.png");

  await openModule(page, "/registrar-merma", "Registrar merma");
  await page.getByRole("button", { name: "Mostrador", exact: true }).click();
  await page.getByRole("button", { name: "Caducado", exact: true }).click();
  await page.locator("button:has-text('Pan dulce')").first().click();
  await page.locator("button:has-text('Concha vainilla')").first().click();
  await page.getByRole("textbox", { name: "Cantidad", exact: true }).fill("3");
  await page.getByRole("button", { name: /^Agregar( linea)?$/ }).click();
  await saveModuleScreenshot(page, "registrar-merma.png");

  await openModule(page, "/cerrar-turno", "Cierre de turno");
  await saveModuleScreenshot(page, "cerrar-turno.png");
});
