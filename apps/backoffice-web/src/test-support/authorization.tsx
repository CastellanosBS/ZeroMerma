import type { ReactNode } from "react";

import type { AuthenticatedUser } from "../lib/api";
import type { EffectiveGrant, PermissionCode } from "../features/auth/authorization";
import { BackofficeAuthorizationContext } from "../features/auth/authorization-context";

export function authorizationUser(grants: EffectiveGrant[] = []): AuthenticatedUser {
  return {
    id: "11111111-1111-4111-8111-111111111111",
    email: "test-actor@example.invalid",
    full_name: "Test actor",
    is_active: true,
    allowed_surfaces: ["BACKOFFICE"],
    default_surface: "BACKOFFICE",
    effective_grants: grants,
    authorization_version: "test-authorization-version",
    authorization_surface: "BACKOFFICE",
    is_superadministrator: false,
  };
}

export function withCapabilities(children: ReactNode, capabilities: PermissionCode[]) {
  const user = authorizationUser(
    capabilities.map((capability) => ({ capability, scope_type: "GLOBAL", branch_ids: [] })),
  );
  return (
    <BackofficeAuthorizationContext.Provider value={user}>
      {children}
    </BackofficeAuthorizationContext.Provider>
  );
}
