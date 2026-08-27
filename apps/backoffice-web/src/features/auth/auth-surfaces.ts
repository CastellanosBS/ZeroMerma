import { appEnv } from "../../env";
import type { AuthenticatedUser } from "../../lib/api";

export const AUTH_SURFACE_POS = "POS";
export const AUTH_SURFACE_BACKOFFICE = "BACKOFFICE";

type AuthSurfaceUser = Pick<AuthenticatedUser, "default_surface"> &
  Partial<Pick<AuthenticatedUser, "allowed_surfaces">>;

export function isBackofficeUser(user: AuthSurfaceUser) {
  return (
    user.allowed_surfaces?.includes(AUTH_SURFACE_BACKOFFICE) ??
    user.default_surface === AUTH_SURFACE_BACKOFFICE
  );
}

export function isPosUser(user: AuthSurfaceUser) {
  return (
    user.allowed_surfaces?.includes(AUTH_SURFACE_POS) ??
    user.default_surface === AUTH_SURFACE_POS
  );
}

export function getUrlWithoutDisallowedAccessToken(url: URL) {
  const sanitizedUrl = new URL(url.toString());
  const hashParams = new URLSearchParams(url.hash.startsWith("#") ? url.hash.slice(1) : url.hash);
  hashParams.delete("access_token");
  sanitizedUrl.searchParams.delete("access_token");
  sanitizedUrl.hash = hashParams.toString();
  return `${sanitizedUrl.pathname}${sanitizedUrl.search}${sanitizedUrl.hash}`;
}

export function clearDisallowedAccessTokenFromCurrentUrl() {
  const url = new URL(window.location.href);
  const sanitizedUrl = getUrlWithoutDisallowedAccessToken(url);
  const currentUrl = `${url.pathname}${url.search}${url.hash}`;
  if (sanitizedUrl !== currentUrl) {
    window.history.replaceState(null, "", sanitizedUrl);
  }
}

export function redirectToPos() {
  window.location.assign(appEnv.VITE_POS_BASE_URL);
}
