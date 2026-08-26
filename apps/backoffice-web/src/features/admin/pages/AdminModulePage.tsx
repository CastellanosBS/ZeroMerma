import { AdminPageShell } from "../components/AdminPageShell";
import { getAdminModule } from "../adminModules";
import type { AdminModuleKey } from "../adminTypes";

export function AdminModulePage({ moduleKey }: { moduleKey: AdminModuleKey }) {
  return <AdminPageShell module={getAdminModule(moduleKey)} />;
}
