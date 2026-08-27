import type { AuthenticatedUser } from "../../lib/api-contracts";

export const AUTH_SURFACE_POS = "POS";
export const AUTH_SURFACE_BACKOFFICE = "BACKOFFICE";

export function shouldRouteToBackoffice(user: Pick<AuthenticatedUser, "default_surface">) {
  return user.default_surface === AUTH_SURFACE_BACKOFFICE;
}

export function buildBackofficeLoginUrl(backofficeBaseUrl: string) {
  const redirectUrl = new URL("/login", backofficeBaseUrl);
  return redirectUrl.toString();
}
