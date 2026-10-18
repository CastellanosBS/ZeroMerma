import type { Page } from "@playwright/test";
import type { SessionResponse } from "@zeromerma/api-client";

export function mockSessionResponse(): SessionResponse {
  const now = Date.now();
  return {
    csrf_token: "mock-csrf-memory-only",
    session: {
      id: "00000000-0000-0000-0000-000000000001", audience: "POS", status: "ACTIVE",
      created_at: new Date(now).toISOString(), last_activity_at: new Date(now).toISOString(),
      idle_expires_at: new Date(now + 1_800_000).toISOString(),
      absolute_expires_at: new Date(now + 43_200_000).toISOString(),
      workstation_id: "00000000-0000-0000-0000-000000000002", cash_session_id: null,
      revoked_at: null, revocation_reason: null,
    },
    user: {
      id: "00000000-0000-0000-0000-000000000003", email: "cashier@zeromerma.local",
      full_name: "Main Branch Cashier", is_active: true, allowed_surfaces: ["POS"],
      default_surface: "POS", authorization_surface: "POS", authorization_version: "mock-auth-v1",
      is_superadministrator: false, password_reset_required: false,
      effective_grants: [{ capability: "pos.operate", scope_type: "GLOBAL", branch_ids: [] }],
    },
  };
}

export async function installMockCookieSession(page: Page, initiallyAuthenticated = false) {
  let authenticated = initiallyAuthenticated;
  let locked = false;
  await page.route("**/v1/auth/**", async route => {
    const path = new URL(route.request().url()).pathname;
    const session = mockSessionResponse();
    if (path.endsWith("/login")) authenticated = true;
    if (path.endsWith("/logout")) {
      authenticated = false;
      await route.fulfill({ status: 204 }); return;
    }
    if (!authenticated) {
      await route.fulfill({ status: 401, json: { code: "SESSION_REQUIRED", message: "Inicia sesión.", details: null, request_id: null, field_errors: null } }); return;
    }
    if (path.endsWith("/lock")) locked = true;
    if (path.endsWith("/reauthenticate")) locked = false;
    session.session.status = locked ? "LOCKED" : "ACTIVE";
    await route.fulfill({ json: path.endsWith("/activity") || path.endsWith("/lock") ? session.session : session });
  });
}
