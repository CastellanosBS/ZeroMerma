import { create } from "zustand";
import { removeLegacyAuthStorage, type AuthSessionView, type SessionResponse } from "@zeromerma/api-client";
import { queryClient } from "../../lib/query-client";
import { usePosTerminalStore } from "../pos-terminal/store";
import { useStatusMessageStore } from "../status-messages/store";

function clearSensitiveMessages() {
  useStatusMessageStore.setState({ messages: [] });
}

type SessionPhase = "restoring" | "ready" | "signedOut" | "locked" | "passwordChange";
interface PosAuthState {
  isAuthenticated: boolean;
  csrfToken: string | null;
  user: SessionResponse["user"] | null;
  session: AuthSessionView | null;
  phase: SessionPhase;
  generation: number;
  setSession: (response: SessionResponse) => void;
  updateSession: (session: AuthSessionView) => void;
  markLocked: () => void;
  requireVerification: () => void;
  requirePasswordChange: () => void;
  clearSession: () => void;
}
removeLegacyAuthStorage();
export const usePosAuthStore = create<PosAuthState>()((set, get) => ({
  isAuthenticated: false,
  csrfToken: null,
  user: null,
  session: null,
  phase: "restoring",
  generation: 0,
  setSession: (response) => {
    const previous = get();
    if (response.session.audience !== "POS" || (response.session.status !== "ACTIVE" && response.session.status !== "LOCKED")) {
      get().clearSession(); return;
    }
    const phase = response.session.status === "LOCKED" ? "locked" :
      response.user.password_reset_required ? "passwordChange" : "ready";
    const identityChanged = previous.session?.id !== response.session.id ||
      previous.user?.authorization_version !== response.user.authorization_version;
    if (identityChanged || (phase !== "ready" && previous.phase === "ready")) {
      clearSensitiveMessages();
      void queryClient.cancelQueries();
      queryClient.clear();
      if (identityChanged) usePosTerminalStore.getState().reset();
    }
    set({ session: response.session, user: response.user, csrfToken: response.csrf_token,
      phase, isAuthenticated: phase === "ready",
      generation: previous.generation + (previous.csrfToken !== response.csrf_token || previous.phase !== phase ? 1 : 0) });
  },
  updateSession: (session) => set({ session }),
  requireVerification: () => {
    clearSensitiveMessages();
    void queryClient.cancelQueries();
    queryClient.clear();
    set({ phase: "restoring", isAuthenticated: false, generation: get().generation + 1 });
  },
  markLocked: () => {
    clearSensitiveMessages();
    void queryClient.cancelQueries();
    queryClient.clear();
    set({ phase: "locked", isAuthenticated: false, generation: get().generation + 1 });
  },
  requirePasswordChange: () => {
    clearSensitiveMessages();
    void queryClient.cancelQueries();
    queryClient.clear();
    set({ phase: "passwordChange", isAuthenticated: false, generation: get().generation + 1 });
  },
  clearSession: () => {
    clearSensitiveMessages();
    void queryClient.cancelQueries();
    queryClient.clear();
    usePosTerminalStore.getState().reset();
    removeLegacyAuthStorage();
    set({ isAuthenticated: false, csrfToken: null, user: null, session: null,
      phase: "signedOut", generation: get().generation + 1 });
  },
}));
