import type { Page, Route } from "@playwright/test";

const branch = {
  brand_key: "EL_MEJOR_PAN",
  code: "MAIN",
  id: "branch-1",
  is_active: true,
  name: "Sucursal Centro",
  timezone: "America/Hermosillo",
};

const workstation = {
  code: "POS-01",
  id: "workstation-1",
  is_active: true,
  name: "Caja 01",
};

const user = {
  email: "cashier@zeromerma.local",
  full_name: "Ana Cajera",
  id: "user-1",
  is_active: true,
};

const activeCashSession = {
  branch_code: branch.code,
  branch_id: branch.id,
  branch_name: branch.name,
  id: "cash-session-1",
  opening_amount: "500.00",
  opened_at: "2026-04-15T08:00:00Z",
  status: "OPEN",
  user_email: user.email,
  user_full_name: user.full_name,
  user_id: user.id,
  workstation_code: workstation.code,
  workstation_id: workstation.id,
  workstation_name: workstation.name,
};

const operationsClass = {
  code: "PAN-DULCE",
  display_order: 10,
  id: "class-pan-dulce",
  name: "Pan dulce",
  product_count: 1,
  quick_name: "Pan",
};

const operationsProduct = {
  code: "CONCHA-VAN",
  currency_code: "MXN",
  display_order: 10,
  id: "product-concha",
  name: "Concha vainilla",
  quick_name: "Concha",
  unit_price: "12.00",
};

const posCatalogClasses = [
  {
    capture_mode_default: "CLASS_CAPTURE",
    class_capture_unit_price: "3.00",
    code: "BOLILLO",
    currency_code: "MXN",
    display_order: 10,
    id: "class-bolillo",
    name: "Bolillo",
    product_count: 0,
    quick_name: "Bolillo",
  },
  {
    capture_mode_default: "CLASS_CAPTURE",
    class_capture_unit_price: "12.00",
    code: "PAN-DULCE",
    currency_code: "MXN",
    display_order: 20,
    id: "class-pan-dulce",
    name: "Pan dulce",
    product_count: 0,
    quick_name: "Dulce",
  },
  {
    capture_mode_default: "PRODUCT_DIRECT",
    class_capture_unit_price: null,
    code: "BEBIDAS",
    currency_code: "MXN",
    display_order: 30,
    id: "class-bebidas",
    name: "Bebidas",
    product_count: 2,
    quick_name: "Bebidas",
  },
];

const posProducts = [
  {
    code: "COCA-355",
    currency_code: "MXN",
    display_order: 10,
    id: "product-coca-355",
    name: "Coca-Cola 355 ml",
    quick_name: "Coca 355",
    unit_price: "18.00",
  },
  {
    code: "AGUA-600",
    currency_code: "MXN",
    display_order: 20,
    id: "product-agua-600",
    name: "Agua natural 600 ml",
    quick_name: "Agua 600",
    unit_price: "12.00",
  },
];

const orderListItem = {
  advance_amount: "60.00",
  created_at_utc: "2026-04-15T10:00:00Z",
  currency_code: "MXN",
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
  ],
  notes: "Entregar a las 18:30.",
  requires_settlement_on_delivery: true,
};

const ticketListItem = {
  change_amount: "26.00",
  confirmed_at: "2026-04-15T11:00:00Z",
  currency_code: "MXN",
  folio: "TCK-5001",
  id: "sale-1",
  item_count: 2,
  operator_full_name: user.full_name,
  payment_summary: [{ amount: "94.00", currency_code: "MXN", payment_method_code: "CASH" }],
  return_count: 0,
  return_status: "NOT_RETURNED",
  returned_amount: "0.00",
  total_amount: "94.00",
  total_quantity: "4.000",
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
  ],
  operator: {
    full_name: user.full_name,
  },
  paid_amount: "94.00",
  payments: [
    {
      applied_amount: "94.00",
      change_amount: "26.00",
      currency_code: "MXN",
      id: "ticket-payment-1",
      payment_method_code: "CASH",
      received_at: "2026-04-15T11:00:05Z",
      sequence: 1,
      tendered_amount: "120.00",
    },
  ],
  status: "CONFIRMED",
  subtotal_amount: "94.00",
  total_quantity: "4.000",
  workstation,
};

const returnSaleSearchItem = {
  confirmed_at: "2026-04-15T09:30:00Z",
  currency_code: "MXN",
  folio: "TCK-5001",
  has_returnable_quantity: true,
  id: "sale-1",
  item_count: 1,
  operator_full_name: user.full_name,
  return_count: 0,
  return_status: "NOT_RETURNED",
  returned_amount: "0.00",
  total_amount: "72.00",
  total_quantity: "6",
};

const returnSaleDetail = {
  branch,
  cash_session_id: activeCashSession.id,
  change_amount: "0.00",
  confirmed_at: "2026-04-15T09:30:00Z",
  currency_code: "MXN",
  folio: "TCK-5001",
  has_returnable_lines: true,
  id: "sale-1",
  lines: [
    {
      already_returned_quantity: "0",
      capture_mode: "PRODUCT_DIRECT",
      catalog_name_snapshot: "Concha vainilla",
      id: "sale-line-1",
      line_total_amount: "72.00",
      product_class_code: "PAN-DULCE",
      product_class_id: "class-pan-dulce",
      product_class_name: "Pan dulce",
      product_code: "CONCHA-VAN",
      product_id: "product-concha",
      product_name: "Concha vainilla",
      quantity: "6",
      remaining_returnable_quantity: "2",
      requires_exact_product_selection: false,
      sequence: 1,
      unit_price: "12.00",
    },
  ],
  operator: {
    full_name: user.full_name,
  },
  paid_amount: "72.00",
  payments: [
    {
      applied_amount: "72.00",
      change_amount: "0.00",
      currency_code: "MXN",
      payment_method_code: "CASH",
      received_at: "2026-04-15T09:30:00Z",
      tendered_amount: "72.00",
    },
  ],
  return_count: 0,
  return_status: "NOT_RETURNED",
  returned_amount: "0.00",
  status: "CONFIRMED",
  subtotal_amount: "72.00",
  total_amount: "72.00",
  workstation,
};

const correctionSearchDocument = {
  committed_at_utc: "2026-04-15T08:45:00Z",
  correction_count: 0,
  destination_branch_name: "Sucursal Norte",
  display_title: "ENV-2001",
  document_type: "BRANCH_TRANSFER_SHIPMENT",
  folio: "ENV-2001",
  id: "correction-target-1",
  source_branch_name: branch.name,
  workstation_name: workstation.name,
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
    source_branch_name: branch.name,
    workstation_name: workstation.name,
  },
};

const paymentListItem = {
  affects_cash_drawer: true,
  branch_code: branch.code,
  branch_name: branch.name,
  cash_amount: "250.00",
  category_code: "SUPPLIES",
  category_name: "Insumos",
  concept: "REF-9001",
  created_at_utc: "2026-04-15T12:00:00Z",
  currency_code: "MXN",
  folio: "PAG-2001",
  id: "payment-1",
  non_cash_amount: "0.00",
  operator_full_name: user.full_name,
  payee_name: "Distribuidora Norte",
  payment_method_code: "CASH",
  status: "COMMITTED",
  total_amount: "250.00",
  workstation_code: workstation.code,
  workstation_name: workstation.name,
};

const discountListItem = {
  affects_cash_drawer: false,
  branch_code: branch.code,
  branch_name: branch.name,
  cash_amount: "0.00",
  category_code: "STAFF",
  category_name: "Personal",
  concept: "Prestamo interno abril",
  created_at_utc: "2026-04-15T13:00:00Z",
  currency_code: "MXN",
  folio: "DES-3001",
  id: "discount-1",
  non_cash_amount: "180.00",
  operator_full_name: user.full_name,
  payment_method_code: "CARD",
  status: "COMMITTED",
  subject_name: "Equipo de reparto",
  total_amount: "180.00",
  workstation_code: workstation.code,
  workstation_name: workstation.name,
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
  receipt: null,
  receipt_summary: null,
  shipment: {
    committed_at_utc: "2026-04-15T09:15:00Z",
    created_at_utc: "2026-04-15T09:00:00Z",
    created_by_user_email: user.email,
    created_by_user_full_name: user.full_name,
    created_by_user_id: user.id,
    destination_branch_code: branch.code,
    destination_branch_id: branch.id,
    destination_branch_name: branch.name,
    destination_bucket_code: "BACKROOM",
    document_type: "BRANCH_TRANSFER_SHIPMENT",
    folio: "ENV-3101",
    id: "transfer-1",
    lines: [
      {
        expected_quantity: "12",
        id: "transfer-line-1",
        line_number: 1,
        notes: null,
        product_class_code_snapshot: "PAN-DULCE",
        product_class_id: "class-pan-dulce",
        product_class_name_snapshot: "Pan dulce",
        product_code_snapshot: "CONCHA-VAN",
        product_id: "product-concha",
        product_name_snapshot: "Concha vainilla",
        quantity: "12",
        received_quantity: null,
        unit_of_measure_code: "EACH",
        variance_reason: null,
      },
    ],
    notes: "Recibir en cuanto llegue el surtido.",
    reason_code: null,
    reason_name: null,
    reference_document_id: null,
    source_branch_code: "NORTE",
    source_branch_id: "branch-north",
    source_branch_name: "Sucursal Norte",
    source_bucket_code: "BACKROOM",
    status: "IN_TRANSIT",
    workstation_code: workstation.code,
    workstation_id: workstation.id,
    workstation_name: workstation.name,
  },
  shipment_summary: {
    committed_at_utc: "2026-04-15T09:15:00Z",
    document_id: "transfer-1",
    folio: "ENV-3101",
    linked_shipment_id: null,
    quantity_summary: {
      expected_total_quantity: "12",
      has_variance: false,
      line_count: 1,
      received_total_quantity: "0",
      variance_line_count: 0,
    },
    status: "IN_TRANSIT",
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

const cashCloseReconciliation = {
  baseline_snapshot: cashCloseBootstrap.baseline_snapshot,
  blockers: [],
  can_commit: false,
  cash_session: activeCashSession,
  class_reconciliations: [
    {
      attribution_lines: [],
      auto_attributed_quantity: "5.000",
      discrepancy_quantity: "0.000",
      final_attributed_quantity: "5.000",
      notes: null,
      pending_quantity: "5.000",
      product_class_code: "PAN-DULCE",
      product_class_id: "class-pan-dulce",
      product_class_name: "Pan dulce",
      resolution_status: "AUTO_RESOLVED",
    },
  ],
  pending_class_capture: cashCloseBootstrap.pending_class_capture,
  reconciliation_status: "REVIEW_REQUIRED",
  relevant_products: [
    {
      counted_quantity: null,
      discrepancy_quantity: null,
      expected_quantity_before_deferred_attr: "5.000",
      final_expected_quantity: "5.000",
      notes: null,
      product_class_code: "PAN-DULCE",
      product_class_id: "class-pan-dulce",
      product_class_name: "Pan dulce",
      product_code: "CONCHA-VAN",
      product_id: "product-concha",
      product_name: "Concha vainilla",
    },
  ],
  warnings: [],
};

async function fulfillJson(route: Route, body: unknown, status = 200) {
  await route.fulfill({
    body: JSON.stringify(body),
    contentType: "application/json",
    status,
  });
}

export async function installAuthenticatedOperatorSession(page: Page) {
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

export async function installOperationalRegressionApiMocks(page: Page) {
  await page.route("**/v1/**", async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    const pathname = url.pathname;

    if (pathname === "/v1/auth/login") {
      await fulfillJson(route, {
        access_token: "test-access-token",
        token_type: "bearer",
      });
      return;
    }

    if (pathname === "/v1/pos/bootstrap") {
      await fulfillJson(route, {
        branch,
        local_timestamp: "2026-04-15T19:30:00Z",
        training_mode: null,
        user,
        workstation,
      });
      return;
    }

    if (pathname === "/v1/cash-sessions/current") {
      await fulfillJson(route, activeCashSession);
      return;
    }

    if (pathname === "/v1/pos/catalog") {
      await fulfillJson(route, { classes: posCatalogClasses });
      return;
    }

    if (pathname === "/v1/pos/classes/class-bebidas/products") {
      await fulfillJson(route, { products: posProducts });
      return;
    }

    if (pathname === "/v1/operations/bootstrap") {
      await fulfillJson(route, {
        branch,
        branch_brand_key: branch.brand_key,
        destination_branches: [
          { code: "NORTE", id: "branch-north", name: "Sucursal Norte", timezone: branch.timezone },
          { code: "SUR", id: "branch-south", name: "Sucursal Sur", timezone: branch.timezone },
        ],
        local_timestamp: "2026-04-15T19:30:00Z",
        user,
        waste_controls: {
          attachment_evidence_supported: false,
          high_impact_quantity_threshold: "10",
          high_impact_requires_acknowledgement: true,
          high_impact_requires_note: true,
          stock_validated_source_bucket_codes: ["COUNTER"],
        },
        waste_reasons: [
          { code: "OLD_COUNTER", display_order: 10, name: "Producto rezagado", requires_note: false },
          { code: "DAMAGED", display_order: 20, name: "Danado", requires_note: true },
        ],
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
        branch_brand_key: branch.brand_key,
        local_timestamp: "2026-04-15T19:30:00Z",
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
      await fulfillJson(route, { products: [operationsProduct] });
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
        local_timestamp: "2026-04-15T19:30:00Z",
        user,
      });
      return;
    }

    if (pathname === "/v1/tickets") {
      await fulfillJson(route, { tickets: [ticketListItem] });
      return;
    }

    if (pathname === "/v1/tickets/sale-1") {
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
        current_open_cash_session: activeCashSession,
        default_scope: "CURRENT_SHIFT",
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
        workstation,
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
        branch_brand_key: branch.brand_key,
        correction_controls: {
          high_impact_quantity_threshold: "10",
          high_impact_requires_acknowledgement: true,
        },
        correction_operations_allowed: true,
        correction_reasons: [
          { code: "COUNT_MISMATCH", name: "Descuadre de conteo" },
          { code: "OTHER", name: "Otro motivo" },
        ],
        current_open_cash_session: activeCashSession,
        destination_branches: [
          { code: "NORTE", id: "branch-north", name: "Sucursal Norte", timezone: branch.timezone },
          { code: "SUR", id: "branch-south", name: "Sucursal Sur", timezone: branch.timezone },
        ],
        local_timestamp: "2026-04-15T19:30:00Z",
        user,
        workstation,
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
        active_categories: [
          { code: "SUPPLIES", display_order: 10, name: "Insumos" },
          { code: "SERVICES", display_order: 20, name: "Servicios" },
        ],
        active_payment_methods: [
          { affects_cash_drawer: true, code: "CASH", helper_text: null, is_enabled: true, label: "Efectivo" },
          { affects_cash_drawer: false, code: "CARD", helper_text: null, is_enabled: true, label: "Tarjeta" },
        ],
        available_scopes: [
          { code: "CURRENT_SHIFT", label: "Turno actual" },
          { code: "TODAY", label: "Hoy" },
          { code: "RECENT", label: "Recientes" },
        ],
        branch,
        branch_brand_key: branch.brand_key,
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
      await fulfillJson(route, {
        available_users: [{ label: user.full_name, value: user.id }],
        category: null,
        created_by_user_id: null,
        payment_method: null,
        payments: [paymentListItem],
        query: null,
        scope: "CURRENT_SHIFT",
        workstation_code: workstation.code,
      });
      return;
    }

    if (pathname === "/v1/discounts/bootstrap") {
      await fulfillJson(route, {
        active_categories: [
          { code: "STAFF", display_order: 10, name: "Personal" },
          { code: "OTHER", display_order: 20, name: "Otros" },
        ],
        active_discount_methods: [
          { affects_cash_drawer: true, code: "CASH", helper_text: null, is_enabled: true, label: "Efectivo" },
          { affects_cash_drawer: false, code: "CARD", helper_text: null, is_enabled: true, label: "Tarjeta" },
        ],
        available_scopes: [
          { code: "CURRENT_SHIFT", label: "Turno actual" },
          { code: "TODAY", label: "Hoy" },
          { code: "RECENT", label: "Recientes" },
        ],
        branch,
        branch_brand_key: branch.brand_key,
        current_open_cash_session: activeCashSession,
        default_scope: "CURRENT_SHIFT",
        discount_controls: {
          high_value_amount_threshold: "200.00",
          high_value_requires_acknowledgement: true,
        },
        discount_registration_allowed: true,
        local_timestamp: "2026-04-15T19:30:00Z",
        user,
        workstation,
      });
      return;
    }

    if (pathname === "/v1/discounts" && request.method() === "GET") {
      await fulfillJson(route, {
        available_users: [{ label: user.full_name, value: user.id }],
        category: null,
        created_by_user_id: null,
        discounts: [discountListItem],
        payment_method: null,
        query: null,
        scope: "CURRENT_SHIFT",
        workstation_code: workstation.code,
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

    if (pathname === "/v1/cash-close/bootstrap") {
      await fulfillJson(route, cashCloseBootstrap);
      return;
    }

    if (pathname === "/v1/cash-close/summary") {
      await fulfillJson(route, cashCloseSummary);
      return;
    }

    if (pathname === "/v1/cash-close/reconciliation") {
      await fulfillJson(route, cashCloseReconciliation);
      return;
    }

    await fulfillJson(route, { message: `Unhandled operational regression mock for ${pathname}` }, 404);
  });
}
