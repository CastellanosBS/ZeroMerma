import {
  DialogBody,
  DialogFooter,
  DialogHeader,
  DialogSurface,
} from "@zeromerma/ui";
import type { ReactNode } from "react";

import type {
  PosBlockerMessage,
  PosConfirmationCopy,
  PosMessageAction,
  PosOperationResultMessage,
} from "../lib/pos-messages";
import { cn } from "../lib/utils";
import {
  AlertTriangleIcon,
  CheckCircleIcon,
  ClockIcon,
  InboxIcon,
} from "./pos-icons";
import { PosButton, PosPanel, PosSectionTitle, PosStatusBadge } from "./pos-foundations";

type PosFeedbackTone = "error" | "info" | "success" | "warning";

function getToastToneClasses(tone: PosFeedbackTone): string {
  switch (tone) {
    case "success":
      return "border-[rgba(18,122,90,0.16)] bg-[var(--ui-color-success-soft)]/96 text-[var(--ui-color-success)]";
    case "warning":
      return "border-[rgba(187,122,22,0.16)] bg-[var(--ui-color-warning-soft)]/96 text-[var(--ui-color-warning)]";
    case "error":
      return "border-[rgba(180,35,24,0.16)] bg-[var(--ui-color-danger-soft)]/97 text-[var(--ui-color-danger)]";
    default:
      return "border-[rgba(37,99,235,0.16)] bg-[var(--pos-primary-soft)]/96 text-[var(--pos-primary)]";
  }
}

function getStateToneClasses(tone: PosFeedbackTone): string {
  switch (tone) {
    case "success":
      return "bg-[var(--ui-color-success-soft)] text-[var(--ui-color-success)]";
    case "warning":
      return "bg-[var(--ui-color-warning-soft)] text-[var(--ui-color-warning)]";
    case "error":
      return "bg-[var(--ui-color-danger-soft)] text-[var(--ui-color-danger)]";
    default:
      return "bg-[var(--pos-primary-soft)] text-[var(--pos-primary)]";
  }
}

function getInlineToneClasses(tone: PosFeedbackTone): string {
  switch (tone) {
    case "success":
      return "border-[rgba(18,122,90,0.16)] bg-[var(--ui-color-success-soft)] text-[var(--ui-color-success)]";
    case "warning":
      return "border-[rgba(187,122,22,0.16)] bg-[var(--ui-color-warning-soft)] text-[var(--ui-color-warning)]";
    case "error":
      return "border-[rgba(180,35,24,0.16)] bg-[var(--ui-color-danger-soft)] text-[var(--ui-color-danger)]";
    default:
      return "border-[rgba(37,99,235,0.16)] bg-[var(--pos-primary-soft)] text-[var(--pos-primary)]";
  }
}

export function PosStatePanel({
  action,
  description,
  eyebrow,
  icon,
  status,
  statusLabel,
  title,
  tone = "info",
}: {
  action?: ReactNode;
  description: string;
  eyebrow?: string;
  icon: ReactNode;
  status?: "draft" | "error" | "pending" | "success" | "warning";
  statusLabel?: string;
  title: string;
  tone?: PosFeedbackTone;
}) {
  return (
    <PosPanel className="w-full px-5 py-4" data-pos-state-panel="true">
      <div className="flex items-start gap-4">
        <div
          className={cn(
            "flex h-11 w-11 shrink-0 items-center justify-center rounded-[var(--pos-radius-control)]",
            getStateToneClasses(tone),
          )}
        >
          {icon}
        </div>
        <div className="min-w-0 flex-1">
          <PosSectionTitle
            action={
              status && statusLabel ? (
                <PosStatusBadge status={status}>{statusLabel}</PosStatusBadge>
              ) : undefined
            }
            description={description}
            eyebrow={eyebrow}
            title={title}
          />
        </div>
      </div>
      {action ? <div className="mt-4">{action}</div> : null}
    </PosPanel>
  );
}

export function PosLoadingState({
  action,
  description,
  eyebrow,
  title,
}: {
  action?: ReactNode;
  description: string;
  eyebrow?: string;
  title: string;
}) {
  return (
    <PosStatePanel
      action={action}
      description={description}
      eyebrow={eyebrow}
      icon={<ClockIcon className="h-5 w-5" />}
      status="pending"
      statusLabel="Cargando"
      title={title}
      tone="info"
    />
  );
}

export function PosEmptyState({
  action,
  description,
  eyebrow,
  title,
}: {
  action?: ReactNode;
  description: string;
  eyebrow?: string;
  title: string;
}) {
  return (
    <PosStatePanel
      action={action}
      description={description}
      eyebrow={eyebrow}
      icon={<InboxIcon className="h-5 w-5" />}
      status="draft"
      statusLabel="Sin datos"
      title={title}
      tone="info"
    />
  );
}

export function PosErrorState({
  action,
  description,
  eyebrow,
  title,
}: {
  action?: ReactNode;
  description: string;
  eyebrow?: string;
  title: string;
}) {
  return (
    <PosStatePanel
      action={action}
      description={description}
      eyebrow={eyebrow}
      icon={<AlertTriangleIcon className="h-5 w-5" />}
      status="error"
      statusLabel="Atencion"
      title={title}
      tone="error"
    />
  );
}

export function PosInlineValidationMessage({
  action,
  children,
  tone = "info",
}: {
  action?: ReactNode;
  children: ReactNode;
  tone?: PosFeedbackTone;
}) {
  return (
    <div
      className={cn(
        "flex min-w-0 items-start gap-2 rounded-[var(--pos-radius-control)] border px-3 py-2 text-sm leading-6",
        getInlineToneClasses(tone),
      )}
      data-pos-inline-validation="true"
      data-tone={tone}
    >
      <div className="min-w-0 flex-1">{children}</div>
      {action ? <div className="shrink-0">{action}</div> : null}
    </div>
  );
}

function PosToastActionRow({
  actions,
  onSelectAction,
}: {
  actions: PosMessageAction[];
  onSelectAction?: (actionKey: string) => void;
}) {
  if (actions.length === 0) {
    return null;
  }

  return (
    <div className="mt-2 flex flex-wrap gap-2">
      {actions.map((action) => (
        <button
          className="inline-flex items-center rounded-full border border-current/20 bg-white/75 px-2.5 py-1 text-xs font-semibold transition hover:bg-white"
          key={action.key}
          onClick={() => onSelectAction?.(action.key)}
          type="button"
        >
          {action.label}
        </button>
      ))}
    </div>
  );
}

function PosToastSurface({
  actions = [],
  children,
  dismissLabel,
  onDismiss,
  onSelectAction,
  title,
  tone,
}: {
  actions?: PosMessageAction[];
  children?: ReactNode;
  dismissLabel?: string;
  onDismiss?: () => void;
  onSelectAction?: (actionKey: string) => void;
  title: string;
  tone: PosFeedbackTone;
}) {
  const icon =
    tone === "error" ? (
      <AlertTriangleIcon className="h-4 w-4" />
    ) : tone === "warning" ? (
      <AlertTriangleIcon className="h-4 w-4" />
    ) : tone === "info" ? (
      <ClockIcon className="h-4 w-4" />
    ) : (
      <CheckCircleIcon className="h-4 w-4" />
    );

  return (
    <div
      className={cn(
        "pointer-events-auto flex items-start gap-3 rounded-[var(--pos-radius-control)] border px-4 py-3 shadow-[var(--pos-subtle-shadow)] backdrop-blur",
        getToastToneClasses(tone),
      )}
      data-pos-toast="true"
      data-tone={tone}
      role={tone === "error" ? "alertdialog" : "status"}
    >
      <div className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-white/75">
        {icon}
      </div>

      <div className="min-w-0 flex-1 pt-0.5">
        <p className="text-[15px] font-semibold leading-6">{title}</p>
        {children ? <div className="mt-0.5 text-sm leading-6 text-current/95">{children}</div> : null}
        <PosToastActionRow actions={actions} onSelectAction={onSelectAction} />
      </div>

      {onDismiss ? (
        <button
          className="inline-flex h-9 items-center justify-center rounded-[0.875rem] border border-current/20 bg-white px-3 text-sm font-medium text-current transition hover:bg-white/80"
          onClick={onDismiss}
          type="button"
        >
          {dismissLabel ?? "Aceptar"}
        </button>
      ) : null}
    </div>
  );
}

export function PosToastMessage({
  actions = [],
  description,
  onDismiss,
  onSelectAction,
  title,
  tone,
}: {
  actions?: PosMessageAction[];
  description?: ReactNode;
  onDismiss?: () => void;
  onSelectAction?: (actionKey: string) => void;
  title: string;
  tone: PosFeedbackTone;
}) {
  return (
    <PosToastSurface
      actions={actions}
      onDismiss={onDismiss}
      onSelectAction={onSelectAction}
      title={title}
      tone={tone}
    >
      {description}
    </PosToastSurface>
  );
}

export function PosSuccessToast({
  actions = [],
  description,
  onDismiss,
  onSelectAction,
  title,
}: {
  actions?: PosMessageAction[];
  description?: ReactNode;
  onDismiss?: () => void;
  onSelectAction?: (actionKey: string) => void;
  title: string;
}) {
  return (
    <PosToastMessage
      actions={actions}
      description={description}
      onDismiss={onDismiss}
      onSelectAction={onSelectAction}
      title={title}
      tone="success"
    />
  );
}

export function PosOperationResultToast({
  message,
  onDismiss,
  onSelectAction,
}: {
  message: PosOperationResultMessage;
  onDismiss?: () => void;
  onSelectAction?: (actionKey: string) => void;
}) {
  return (
    <PosSuccessToast
      actions={message.nextActions ?? []}
      description={
        <>
          {message.referenceId ? (
            <p>
              {message.referenceLabel ?? "Folio"} <span className="font-semibold">{message.referenceId}</span>
            </p>
          ) : null}
          {message.description ? <p>{message.description}</p> : null}
        </>
      }
      onDismiss={onDismiss}
      onSelectAction={onSelectAction}
      title={message.successTitle}
    />
  );
}

function getActionVariant(
  action: PosMessageAction,
): "neutral" | "primary" | "secondary" {
  switch (action.kind) {
    case "newOperation":
      return "primary";
    case "viewHistory":
      return "secondary";
    default:
      return "neutral";
  }
}

export function PosOperationResultPanel({
  message,
  onSelectAction,
}: {
  message: PosOperationResultMessage;
  onSelectAction?: (actionKey: string) => void;
}) {
  return (
    <PosPanel className="grid gap-4 px-4 py-4" tone="success" data-pos-operation-result-panel="true">
      <PosSectionTitle
        action={<PosStatusBadge status="success">Operacion lista</PosStatusBadge>}
        description={message.description}
        eyebrow="Resultado"
        title={message.successTitle}
      />

      {message.referenceId ? (
        <div className="rounded-[var(--pos-radius-control)] border border-[rgba(18,122,90,0.16)] bg-white px-3 py-2.5">
          <p className="pos-label-text">{message.referenceLabel ?? "Folio"}</p>
          <p className="mt-1 text-lg font-semibold text-slate-950">{message.referenceId}</p>
        </div>
      ) : null}

      {message.nextActions && message.nextActions.length > 0 ? (
        <div className="flex flex-wrap items-center gap-2">
          {message.nextActions.map((action) => (
            <PosButton
              className="min-w-[8.5rem]"
              key={action.key}
              onClick={() => onSelectAction?.(action.key)}
              variant={getActionVariant(action)}
            >
              {action.label}
            </PosButton>
          ))}
        </div>
      ) : null}
    </PosPanel>
  );
}

export function PosConfirmationDialog({
  confirmation,
  details,
  isOpen,
  isPending = false,
  onCancel,
  onConfirm,
}: {
  confirmation: PosConfirmationCopy;
  details?: ReactNode;
  isOpen: boolean;
  isPending?: boolean;
  onCancel: () => void;
  onConfirm: () => void;
}) {
  if (!isOpen) {
    return null;
  }

  const confirmVariant = confirmation.tone === "danger" ? "danger" : "primary";

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/25 p-4">
      <DialogSurface className="w-full max-w-md">
        <DialogHeader>
          <div className="min-w-0">
            {confirmation.eyebrow ? <p className="pos-label-text">{confirmation.eyebrow}</p> : null}
            <h2 className="mt-1 text-lg font-semibold text-slate-950">{confirmation.title}</h2>
            {confirmation.description ? (
              <p className="mt-2 text-sm leading-6 text-slate-700">{confirmation.description}</p>
            ) : null}
          </div>
          <PosStatusBadge status={confirmation.tone === "danger" ? "blocked" : "warning"}>
            {confirmation.tone === "danger" ? "Operacion sensible" : "Confirmacion"}
          </PosStatusBadge>
        </DialogHeader>

        {details ? <DialogBody className="grid gap-3">{details}</DialogBody> : null}

        <DialogFooter>
          <PosButton disabled={isPending} onClick={onCancel} type="button" variant="neutral">
            {confirmation.cancelLabel}
          </PosButton>
          <PosButton disabled={isPending} onClick={onConfirm} type="button" variant={confirmVariant}>
            {isPending ? "Confirmando..." : confirmation.confirmLabel}
          </PosButton>
        </DialogFooter>
      </DialogSurface>
    </div>
  );
}

export function PosBlockerPanel({
  blockers,
  title = "Bloqueos operativos",
}: {
  blockers: PosBlockerMessage[];
  title?: string;
}) {
  if (blockers.length === 0) {
    return null;
  }

  return (
    <PosPanel className="px-3.5 py-3" tone="warning" data-pos-blocker-panel="true">
      <PosSectionTitle
        action={<PosStatusBadge status="blocked">Bloqueado</PosStatusBadge>}
        description="Resuelve los pendientes antes de confirmar."
        title={title}
      />
      <div className="mt-3 grid gap-2">
        {blockers.map((blocker) => (
          <PosInlineValidationMessage
            key={blocker.key}
            tone={blocker.tone === "error" ? "error" : "warning"}
          >
            {blocker.message}
          </PosInlineValidationMessage>
        ))}
      </div>
    </PosPanel>
  );
}
