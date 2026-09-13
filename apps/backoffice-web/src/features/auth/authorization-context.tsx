import { createContext, useContext } from "react";

import type { AuthenticatedUser } from "../../lib/api";
import { hasEffectiveCapability, type PermissionCode } from "./authorization";

export const BackofficeAuthorizationContext = createContext<AuthenticatedUser | null>(null);

export function useBackofficeAuthorization() {
  return useContext(BackofficeAuthorizationContext);
}

export function useCapability(
  capability: PermissionCode,
  branchIds: readonly string[] = [],
  globalOnly = false,
) {
  return hasEffectiveCapability(useBackofficeAuthorization(), capability, branchIds, globalOnly);
}
