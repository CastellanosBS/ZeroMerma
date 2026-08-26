import { AdminPageShell } from "../components/AdminPageShell";
import { getAdminModule } from "../adminModules";

export function AdminDashboardPage() {
  return <AdminPageShell module={getAdminModule("dashboard")} />;
}
