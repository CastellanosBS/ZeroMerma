export function resolvePosEntryRoute({
  hasActiveCashSession = false,
  isAuthenticated,
}: {
  hasActiveCashSession?: boolean;
  isAuthenticated: boolean;
}): "/login" | "/cash-session/open" | "/pos" {
  if (!isAuthenticated) {
    return "/login";
  }

  return hasActiveCashSession ? "/pos" : "/cash-session/open";
}
