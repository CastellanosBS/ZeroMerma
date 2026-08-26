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

export function readAccessTokenFromUrl(url: URL) {
  const hashParams = new URLSearchParams(url.hash.startsWith("#") ? url.hash.slice(1) : url.hash);
  return hashParams.get("access_token") ?? url.searchParams.get("access_token");
}

export function clearAccessTokenFromCurrentUrl() {
  const url = new URL(window.location.href);
  const hashParams = new URLSearchParams(url.hash.startsWith("#") ? url.hash.slice(1) : url.hash);
  hashParams.delete("access_token");
  url.searchParams.delete("access_token");
  url.hash = hashParams.toString();
  window.history.replaceState(null, "", `${url.pathname}${url.search}${url.hash}`);
}

export function redirectToPos() {
  window.location.assign(appEnv.VITE_POS_BASE_URL);
}
