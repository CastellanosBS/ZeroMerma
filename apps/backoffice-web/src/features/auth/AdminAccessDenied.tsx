import { Navigate } from "@tanstack/react-router";

import { getAuthorizedAdminLanding } from "../admin/navigation/adminNavigation";
import { useBackofficeAuthorization } from "./authorization-context";

export function AdminAccessDenied() {
  return (
    <section className="grid gap-3 rounded-2xl bg-white p-6" role="status">
      <h2 className="text-xl font-semibold">Sin acceso autorizado</h2>
      <p>
        Tu cuenta no tiene permiso para consultar este módulo. Solicita acceso a un administrador.
      </p>
    </section>
  );
}

export function AuthorizedAdminHome() {
  const landing = getAuthorizedAdminLanding(useBackofficeAuthorization());
  return landing ? <Navigate to={landing as never} /> : <AdminAccessDenied />;
}
