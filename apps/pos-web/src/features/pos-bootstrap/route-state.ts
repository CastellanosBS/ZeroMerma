export function resolvePosEntryRoute({
  hasActiveCashSession = false,
  hasAccessToken,
}: {
  hasActiveCashSession?: boolean;
  hasAccessToken: boolean;
}): "/login" | "/cash-session/open" | "/pos" {
  if (!hasAccessToken) {
    return "/login";
  }

  return hasActiveCashSession ? "/pos" : "/cash-session/open";
}
