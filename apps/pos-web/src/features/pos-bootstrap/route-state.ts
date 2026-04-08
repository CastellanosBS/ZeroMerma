export function resolvePosEntryRoute({
  hasAccessToken,
  hasActiveCashSession,
}: {
  hasAccessToken: boolean;
  hasActiveCashSession: boolean;
}): "/login" | "/" | "/cash-session/open" {
  if (!hasAccessToken) {
    return "/login";
  }

  if (!hasActiveCashSession) {
    return "/cash-session/open";
  }

  return "/";
}
