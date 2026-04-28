import type { PosBootstrapResponse } from "../lib/api-contracts";
import { AlertTriangleIcon } from "./pos-icons";

interface TrainingModeBannerProps {
  trainingMode: PosBootstrapResponse["training_mode"];
}

export function TrainingModeBanner({ trainingMode }: TrainingModeBannerProps) {
  if (!trainingMode?.is_enabled) {
    return null;
  }

  return (
    <div className="border-b border-amber-300 bg-amber-100 text-amber-950">
      <div
        className="mx-auto flex w-full items-start gap-3 px-[var(--pos-shell-workstation-padding)] py-3"
        style={{ maxWidth: "var(--pos-shell-max-width)" }}
      >
        <span className="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-amber-200 text-amber-900">
          <AlertTriangleIcon className="h-4 w-4" />
        </span>

        <div className="min-w-0">
          <p className="text-sm font-semibold leading-5">{trainingMode.label}</p>
          <p className="text-sm leading-5 text-amber-950/90">{trainingMode.safeguard_note}</p>
        </div>
      </div>
    </div>
  );
}
