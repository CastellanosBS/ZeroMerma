import type { ButtonHTMLAttributes } from "react";

import { hasEffectiveCapability, type PermissionCode } from "../../auth/authorization";
import { useBackofficeAuthorization } from "../../auth/authorization-context";

type AdminActionButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  capability: PermissionCode;
  branchIds?: readonly string[];
  globalOnly?: boolean;
  additionalCapabilities?: readonly PermissionCode[];
};

export function AdminActionButton({
  capability,
  additionalCapabilities = [],
  branchIds,
  globalOnly,
  disabled,
  title,
  ...props
}: AdminActionButtonProps) {
  const actor = useBackofficeAuthorization();
  const permitted = [capability, ...additionalCapabilities].every((required) =>
    hasEffectiveCapability(actor, required, branchIds, globalOnly),
  );
  return (
    <button
      {...props}
      disabled={disabled || !permitted}
      title={permitted ? title : "No tienes permiso para esta acción."}
    />
  );
}
