import { create } from "zustand";
import { createJSONStorage, persist } from "zustand/middleware";

import { queryClient } from "../../lib/query-client";

interface BackofficeAuthState {
  accessToken: string | null;
  clearSession: () => void;
  setAccessToken: (accessToken: string) => void;
}

export const useBackofficeAuthStore = create<BackofficeAuthState>()(
  persist(
    (set, get) => ({
      accessToken: null,
      clearSession: () => {
        queryClient.clear();
        set({ accessToken: null });
      },
      setAccessToken: (accessToken) => {
        if (get().accessToken !== accessToken) queryClient.clear();
        set({ accessToken });
      },
    }),
    {
      name: "zeromerma-backoffice-auth",
      storage: createJSONStorage(() => localStorage),
    },
  ),
);
