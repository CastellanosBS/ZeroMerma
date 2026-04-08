import { create } from "zustand";

interface PosShellState {
  branchName: string;
  setBranchName: (branchName: string) => void;
}

export const usePosShellStore = create<PosShellState>((set) => ({
  branchName: "Main branch",
  setBranchName: (branchName) => set({ branchName }),
}));
