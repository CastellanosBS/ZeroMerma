import { create } from "zustand";

interface BackofficeShellState {
  workspaceName: string;
  setWorkspaceName: (workspaceName: string) => void;
}

export const useBackofficeShellStore = create<BackofficeShellState>((set) => ({
  workspaceName: "Operations workspace",
  setWorkspaceName: (workspaceName) => set({ workspaceName }),
}));
