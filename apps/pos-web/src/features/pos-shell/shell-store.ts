import { create } from "zustand";
import { createJSONStorage, persist } from "zustand/middleware";

interface PosShellUiState {
  isSidebarCollapsed: boolean;
  lastOperationalPath: string | null;
  setLastOperationalPath: (lastOperationalPath: string | null) => void;
  setSidebarCollapsed: (isSidebarCollapsed: boolean) => void;
  toggleSidebar: () => void;
}

export const usePosShellStore = create<PosShellUiState>()(
  persist(
    (set) => ({
      isSidebarCollapsed: false,
      lastOperationalPath: "/pos",
      setLastOperationalPath: (lastOperationalPath) => set({ lastOperationalPath }),
      setSidebarCollapsed: (isSidebarCollapsed) => set({ isSidebarCollapsed }),
      toggleSidebar: () =>
        set((state) => ({
          isSidebarCollapsed: !state.isSidebarCollapsed,
        })),
    }),
    {
      name: "zeromerma-pos-shell",
      storage: createJSONStorage(() => localStorage),
    },
  ),
);
