import type { AuthenticatedUser } from "../../lib/api-contracts";

export const AUTH_SURFACE_POS = "POS";
export const AUTH_SURFACE_BACKOFFICE = "BACKOFFICE";

export function shouldRouteToBackoffice(user: Pick<AuthenticatedUser, "default_surface">) {
  return user.default_surface === AUTH_SURFACE_BACKOFFICE;
}

export function buildBackofficeAdminUrl(backofficeBaseUrl: string, accessToken: string) {
  const redirectUrl = new URL("/admin", backofficeBaseUrl);
  redirectUrl.hash = new URLSearchParams({ access_token: accessToken }).toString();
  return redirectUrl.toString();
}
