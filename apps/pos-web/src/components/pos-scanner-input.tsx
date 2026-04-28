import { type KeyboardEvent, type Ref } from "react";

import { posInputClass, posOutlineButtonClass } from "../features/pos-theme/theme";
import { cn } from "../lib/utils";
import { PosButton } from "./pos-foundations";
import { ModuleStateChip, SearchField } from "./pos-module-primitives";

export function PosScannerInput({
  ariaLabel,
  className,
  description = "El escaner funciona como teclado y confirma con Enter.",
  disabled = false,
  inputRef,
  modeLabel,
  onChange,
  onSubmit,
  placeholder,
  submitLabel = "Procesar",
  value,
}: {
  ariaLabel: string;
  className?: string;
  description?: string;
  disabled?: boolean;
  inputRef?: Ref<HTMLInputElement>;
  modeLabel: string;
  onChange: (value: string) => void;
  onSubmit: () => void;
  placeholder: string;
  submitLabel?: string;
  value: string;
}) {
  function handleKeyDown(event: KeyboardEvent<HTMLInputElement>) {
    if (event.key !== "Enter" && event.key !== "NumpadEnter") {
      return;
    }

    event.preventDefault();
    onSubmit();
  }

  return (
    <div
      className={cn(
        "grid gap-2 rounded-xl border border-[var(--pos-shell-border)] bg-[var(--pos-shell-muted)]/75 px-3 py-3",
        className,
      )}
    >
      <div className="flex flex-wrap items-center justify-between gap-2">
        <ModuleStateChip tone="info">{modeLabel}</ModuleStateChip>
        <span className="text-xs font-medium text-slate-500">{description}</span>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <SearchField
          ariaLabel={ariaLabel}
          className="min-w-0 flex-1"
          disabled={disabled}
          inputClassName={cn("h-10 rounded-lg text-sm shadow-sm", posInputClass)}
          inputRef={inputRef}
          onChange={onChange}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          value={value}
        />
        <PosButton
          className={cn("h-10 shrink-0 px-3 text-sm", posOutlineButtonClass)}
          disabled={disabled || value.trim().length === 0}
          onClick={onSubmit}
          type="button"
          variant="neutral"
        >
          {submitLabel}
        </PosButton>
      </div>
    </div>
  );
}
