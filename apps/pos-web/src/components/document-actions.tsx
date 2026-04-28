import { useCallback, useRef } from "react";
import type { ReactNode } from "react";

import { useStatusMessageStore } from "../features/status-messages/store";
import { copyDocumentReferenceToClipboard } from "../lib/document-actions";
import { cn } from "../lib/utils";
import { PosButton, type PosButtonProps } from "./pos-foundations";
import {
  ClipboardIcon,
  DownloadIcon,
  MenuIcon,
  PrinterIcon,
} from "./pos-icons";

export interface DocumentActionsMenuItem {
  disabled?: boolean;
  disabledReason?: string;
  key: string;
  label: string;
  leadingIcon?: ReactNode;
  onSelect: () => void;
  tone?: "danger" | "default";
}

export function CopyFolioAction({
  className,
  errorMessage = "No se pudo copiar el folio.",
  label = "Copiar folio",
  onCopied,
  onError,
  referenceValue,
  successMessage = "Folio copiado.",
  title,
  variant = "neutral",
  ...props
}: Omit<PosButtonProps, "children" | "leadingIcon" | "onClick"> & {
  errorMessage?: string;
  label?: string;
  onCopied?: () => void;
  onError?: () => void;
  referenceValue: string | null | undefined;
  successMessage?: string;
  title?: string;
}) {
  const showError = useStatusMessageStore((state) => state.showError);
  const showSuccess = useStatusMessageStore((state) => state.showSuccess);
  const isDisabled = props.disabled ?? !referenceValue;

  const handleCopy = useCallback(() => {
    if (!referenceValue) {
      showError(errorMessage);
      onError?.();
      return;
    }

    void copyDocumentReferenceToClipboard(referenceValue)
      .then(() => {
        showSuccess(successMessage);
        onCopied?.();
      })
      .catch(() => {
        showError(errorMessage);
        onError?.();
      });
  }, [errorMessage, onCopied, onError, referenceValue, showError, showSuccess, successMessage]);

  return (
    <PosButton
      className={className}
      disabled={isDisabled}
      leadingIcon={<ClipboardIcon className="h-4 w-4" />}
      onClick={handleCopy}
      title={title}
      variant={variant}
      {...props}
    >
      {label}
    </PosButton>
  );
}

export function PrintAction({
  availabilityNote,
  className,
  isPending = false,
  label = "Imprimir",
  onPrint,
  title,
  variant = "secondary",
  ...props
}: Omit<PosButtonProps, "children" | "leadingIcon" | "onClick"> & {
  availabilityNote?: string;
  isPending?: boolean;
  label?: string;
  onPrint?: () => void;
  title?: string;
}) {
  const isDisabled = props.disabled ?? !onPrint;

  return (
    <PosButton
      className={className}
      disabled={isDisabled}
      leadingIcon={<PrinterIcon className="h-4 w-4" />}
      onClick={() => onPrint?.()}
      title={title ?? availabilityNote}
      variant={variant}
      {...props}
    >
      {isPending ? "Imprimiendo..." : label}
    </PosButton>
  );
}

export function ExportPdfAction({
  availabilityNote,
  className,
  label = "Exportar PDF",
  onExport,
  title,
  variant = "ghost",
  ...props
}: Omit<PosButtonProps, "children" | "leadingIcon" | "onClick"> & {
  availabilityNote?: string;
  label?: string;
  onExport?: () => void;
  title?: string;
}) {
  const isDisabled = props.disabled ?? !onExport;

  return (
    <PosButton
      className={className}
      disabled={isDisabled}
      leadingIcon={<DownloadIcon className="h-4 w-4" />}
      onClick={() => onExport?.()}
      title={title ?? availabilityNote}
      variant={variant}
      {...props}
    >
      {label}
    </PosButton>
  );
}

export function DocumentActionsMenu({
  actions,
  className,
  triggerLabel = "Acciones del documento",
}: {
  actions: DocumentActionsMenuItem[];
  className?: string;
  triggerLabel?: string;
}) {
  const menuRef = useRef<HTMLDetailsElement | null>(null);

  if (actions.length === 0) {
    return null;
  }

  function focusFirstMenuItem() {
    const firstEnabledItem = menuRef.current?.querySelector<HTMLButtonElement>(
      ".pos-document-action-menu__item:not(:disabled)",
    );
    firstEnabledItem?.focus();
  }

  return (
    <details className={cn("pos-document-action-menu", className)} ref={menuRef}>
      <summary
        aria-label={triggerLabel}
        className="pos-document-action-menu__trigger"
        onClick={(event) => event.stopPropagation()}
        onKeyDown={(event) => {
          if (event.key === "ArrowDown") {
            event.preventDefault();
            menuRef.current?.setAttribute("open", "true");
            window.setTimeout(() => focusFirstMenuItem(), 0);
            return;
          }

          if (event.key === "Enter" || event.key === " ") {
            event.preventDefault();
            if (menuRef.current?.hasAttribute("open")) {
              menuRef.current?.removeAttribute("open");
              return;
            }

            menuRef.current?.setAttribute("open", "true");
            window.setTimeout(() => focusFirstMenuItem(), 0);
          }
        }}
      >
        <MenuIcon className="h-4 w-4" />
        <span className="sr-only">{triggerLabel}</span>
      </summary>
      <div
        className="pos-document-action-menu__surface"
        onKeyDown={(event) => {
          if (event.key === "Escape") {
            event.preventDefault();
            menuRef.current?.removeAttribute("open");
            menuRef.current?.querySelector<HTMLElement>(".pos-document-action-menu__trigger")?.focus();
          }
        }}
        role="menu"
      >
        {actions.map((action) => (
          <button
            className={cn(
              "pos-document-action-menu__item",
              action.tone === "danger" && "pos-document-action-menu__item--danger",
            )}
            disabled={action.disabled}
            key={action.key}
            onClick={(event) => {
              event.stopPropagation();
              action.onSelect();
              menuRef.current?.removeAttribute("open");
            }}
            role="menuitem"
            title={action.disabledReason}
            type="button"
          >
            {action.leadingIcon ? (
              <span aria-hidden="true" className="pos-document-action-menu__icon">
                {action.leadingIcon}
              </span>
            ) : null}
            <span className="min-w-0">
              <span className="block">{action.label}</span>
              {action.disabled && action.disabledReason ? (
                <span className="pos-document-action-menu__hint">{action.disabledReason}</span>
              ) : null}
            </span>
          </button>
        ))}
      </div>
    </details>
  );
}
