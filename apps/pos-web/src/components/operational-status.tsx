import type { ReactNode } from "react";

import { PosStatePanel } from "./pos-feedback";
import { AlertTriangleIcon } from "./pos-icons";

interface OperationalStatusProps {
  action?: ReactNode;
  description: string;
  eyebrow?: string;
  title: string;
}

export function OperationalStatus({
  action,
  description,
  eyebrow,
  title,
}: OperationalStatusProps) {
  return (
    <PosStatePanel
      action={action}
      description={description}
      eyebrow={eyebrow}
      icon={<AlertTriangleIcon className="h-5 w-5" />}
      title={title}
      tone="info"
    />
  );
}
