import { create } from "zustand";
import { createJSONStorage, persist } from "zustand/middleware";

interface PosAuthState {
  accessToken: string | null;
  clearSession: () => void;
  setAccessToken: (accessToken: string) => void;
}

export const usePosAuthStore = create<PosAuthState>()(
  persist(
    (set) => ({
      accessToken: null,
      clearSession: () => set({ accessToken: null }),
      setAccessToken: (accessToken) => set({ accessToken }),
    }),
    {
      name: "zeromerma-pos-auth",
      storage: createJSONStorage(() => localStorage),
    },
  ),
);
