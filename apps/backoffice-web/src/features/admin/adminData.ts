import type { AdminModuleDefinition } from "./adminTypes";

export interface AdminModuleRecord {
  id: string;
  values: Record<string, string>;
}

export interface AdminModuleDataState {
  error: Error | null;
  isBackendConnected: boolean;
  isError: boolean;
  isLoading: boolean;
  records: AdminModuleRecord[];
}

export function useAdminModuleRecords(module: AdminModuleDefinition): AdminModuleDataState {
  void module;

  return {
    error: null,
    isBackendConnected: false,
    isError: false,
    isLoading: false,
    records: [],
  };
}
