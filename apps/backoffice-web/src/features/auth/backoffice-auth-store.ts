import { create } from "zustand";
import { removeLegacyAuthStorage, type AuthSessionView, type SessionResponse } from "@zeromerma/api-client";
import { queryClient } from "../../lib/query-client";

type SessionPhase = "restoring" | "ready" | "signedOut" | "locked" | "passwordChange";
interface BackofficeAuthState {
  isAuthenticated: boolean;
  csrfToken: string | null;
  user: SessionResponse["user"] | null;
  session: AuthSessionView | null;
  phase: SessionPhase;
  generation: number;
  setSession: (response: SessionResponse) => void;
  updateSession: (session: AuthSessionView) => void;
  markLocked: () => void;
  requirePasswordChange: () => void;
  clearSession: () => void;
}
removeLegacyAuthStorage();
export const useBackofficeAuthStore = create<BackofficeAuthState>()((set, get) => ({
  isAuthenticated: false,
  csrfToken: null,
  user: null,
  session: null,
  phase: "restoring",
  generation: 0,
  setSession: (response) => {
    const previous = get();
    if (response.session.audience !== "BACKOFFICE" || (response.session.status !== "ACTIVE" && response.session.status !== "LOCKED")) {
      get().clearSession(); return;
    }
    const phase = response.session.status === "LOCKED" ? "locked" :
      response.user.password_reset_required ? "passwordChange" : "ready";
    const identityChanged = previous.session?.id !== response.session.id ||
      previous.user?.authorization_version !== response.user.authorization_version;
    if (identityChanged || (phase !== "ready" && previous.phase === "ready")) {
      void queryClient.cancelQueries();
      queryClient.clear();

    }
    set({ session: response.session, user: response.user, csrfToken: response.csrf_token,
      phase, isAuthenticated: phase === "ready",
      generation: previous.generation + (previous.csrfToken !== response.csrf_token || previous.phase !== phase ? 1 : 0) });
  },
  updateSession: (session) => set({ session }),
  markLocked: () => {
    void queryClient.cancelQueries();
    queryClient.clear();
    set({ phase: "locked", isAuthenticated: false, generation: get().generation + 1 });
  },
  requirePasswordChange: () => {
    void queryClient.cancelQueries();
    queryClient.clear();
    set({ phase: "passwordChange", isAuthenticated: false, generation: get().generation + 1 });
  },
  clearSession: () => {
    void queryClient.cancelQueries();
    queryClient.clear();

    removeLegacyAuthStorage();
    set({ isAuthenticated: false, csrfToken: null, user: null, session: null,
      phase: "signedOut", generation: get().generation + 1 });
  },
}));
