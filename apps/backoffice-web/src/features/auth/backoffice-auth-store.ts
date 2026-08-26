import { create } from "zustand";
import { createJSONStorage, persist } from "zustand/middleware";

interface BackofficeAuthState {
  accessToken: string | null;
  clearSession: () => void;
  setAccessToken: (accessToken: string) => void;
}

export const useBackofficeAuthStore = create<BackofficeAuthState>()(
  persist(
    (set) => ({
      accessToken: null,
      clearSession: () => set({ accessToken: null }),
      setAccessToken: (accessToken) => set({ accessToken }),
    }),
    {
      name: "zeromerma-backoffice-auth",
      storage: createJSONStorage(() => localStorage),
    },
  ),
);
