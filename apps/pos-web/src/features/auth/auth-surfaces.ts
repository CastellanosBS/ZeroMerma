
export const AUTH_SURFACE_POS = "POS";
export const AUTH_SURFACE_BACKOFFICE = "BACKOFFICE";



export function buildBackofficeLoginUrl(backofficeBaseUrl: string) {
  const redirectUrl = new URL("/login", backofficeBaseUrl);
  return redirectUrl.toString();
}
