import type { AuthenticatedUser } from "../../lib/api";

export type EffectiveGrant = NonNullable<AuthenticatedUser["effective_grants"]>[number];
export type PermissionCode = EffectiveGrant["capability"];

// This reflects a server-resolved grant for presentation. It never composes roles,
// derives authority from surfaces or substitutes for request authorization.
export function hasEffectiveCapability(
  user: AuthenticatedUser | null,
  capability: PermissionCode,
  branchIds: readonly string[] = [],
  globalOnly = false,
): boolean {
  if (!user?.is_active || user.authorization_surface !== "BACKOFFICE") return false;
  const grant = user.effective_grants?.find((item) => item.capability === capability);
  if (!grant) return false;
  if (grant.scope_type === "GLOBAL") return true;
  if (globalOnly) return false;
  return (
    grant.scope_type === "BRANCH_SET" &&
    grant.branch_ids.length > 0 &&
    branchIds.every((id) => grant.branch_ids.includes(id))
  );
}

export function authorizationIdentity(user: AuthenticatedUser): string {
  return `${user.id}:${user.authorization_version}`;
}
