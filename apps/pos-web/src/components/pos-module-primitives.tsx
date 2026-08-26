import type { KeyboardEvent, ReactNode, Ref } from "react";

import { focusEdgeItem, focusRelativeItem } from "../lib/keyboard-shortcuts";
import { cn } from "../lib/utils";
import { SearchIcon } from "./pos-icons";

type MetricTone = "default" | "financial" | "info" | "muted" | "negative" | "positive" | "warning";
type NoticeTone = "error" | "info" | "success" | "warning";

function getToneDataAttribute<TTone extends string>(
  tone: TTone,
  fallback: TTone,
): TTone | undefined {
  return tone === fallback ? undefined : tone;
}

export function WorkstationPanel({
  children,
  className,
  tone = "default",
}: {
  children: ReactNode;
  className?: string;
  tone?: "default" | "muted";
}) {
  return (
    <section
      className={cn("pos-shell-panel min-w-0", className)}
      data-tone={getToneDataAttribute(tone, "default")}
    >
      {children}
    </section>
  );
}

export function SectionHeader({
  action,
  badge,
  className,
  description,
  eyebrow,
  title,
  titleAs = "h2",
}: {
  action?: ReactNode;
  badge?: ReactNode;
  className?: string;
  description?: string;
  eyebrow?: string;
  title: string;
  titleAs?: "h1" | "h2" | "h3";
}) {
  const TitleTag = titleAs;

  return (
    <div className={cn("flex flex-wrap items-start justify-between gap-3", className)}>
      <div className="min-w-0 flex-1">
        {eyebrow ? <p className="pos-eyebrow-text">{eyebrow}</p> : null}
        <div className="mt-1 flex flex-wrap items-center gap-2.5">
          <TitleTag className="text-[1.05rem] font-semibold tracking-tight text-slate-950">
            {title}
          </TitleTag>
          {badge}
        </div>
        {description ? <p className="pos-helper-text mt-1.5 max-w-3xl">{description}</p> : null}
      </div>
      {action ? <div className="shrink-0">{action}</div> : null}
    </div>
  );
}

type FlowGuideStep = {
  icon?: ReactNode;
  isBlocked?: boolean;
  key: string;
  label: string;
  state?: "blocked" | "completed" | "current" | "upcoming";
};

export function CompactPageHeader({
  activeStep,
  ariaLabel,
  chips = [],
  children,
  contextLine,
  eyebrow,
  flowSteps,
  flowVariant = "process",
  onStepSelect,
  secondaryChips,
  stateChip,
  title,
}: {
  activeStep?: string;
  ariaLabel?: string;
  chips?: ReactNode[];
  children?: ReactNode;
  contextLine?: string;
  eyebrow?: string;
  flowSteps?: FlowGuideStep[];
  flowVariant?: "compact" | "default" | "process" | "stepper";
  onStepSelect?: (stepKey: string) => void;
  secondaryChips?: ReactNode;
  stateChip?: ReactNode;
  title: string;
}) {
  void contextLine;
  void eyebrow;
  const visibleChips = [stateChip, secondaryChips, ...chips].filter(Boolean);
  const hasChips = visibleChips.length > 0;
  const hasFlow = Boolean(flowSteps?.length) && Boolean(activeStep);

  return (
    <div className="pos-page-header">
      <div className="pos-page-header-title-row">
        <h1 className="pos-module-title">{title}</h1>
        {hasChips ? <HeaderChipCluster chips={visibleChips.slice(0, 3)} /> : null}
      </div>
      {hasFlow ? (
        <HeaderFlowStrip>
          <FlowGuide
            activeStepKey={activeStep!}
            ariaLabel={ariaLabel}
            onStepSelect={onStepSelect}
            steps={flowSteps!}
            variant={flowVariant}
          />
        </HeaderFlowStrip>
      ) : children ? (
        <HeaderFlowStrip>{children}</HeaderFlowStrip>
      ) : null}
    </div>
  );
}

export function HeaderChipCluster({
  chips,
  className,
}: {
  chips: ReactNode[];
  className?: string;
}) {
  return (
    <div className={cn("pos-page-header-chips", className)}>
      {chips.map((chip, index) => (
        <span className="contents" key={index}>
          {chip}
        </span>
      ))}
    </div>
  );
}

export function HeaderFlowStrip({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) {
  return <div className={cn("pos-page-header-flow", className)}>{children}</div>;
}

export function PageHeader(props: {
  children?: ReactNode;
  secondaryChips?: ReactNode;
  stateChip?: ReactNode;
  title: string;
}) {
  const { children, secondaryChips, stateChip, title } = props;
  return (
    <CompactPageHeader chips={[stateChip, secondaryChips]} title={title}>
      {children}
    </CompactPageHeader>
  );
}

export function CentralWorkspaceSheet({
  children,
  className,
  contentClassName,
  header,
  toolbar,
  toolbarClassName,
}: {
  children: ReactNode;
  className?: string;
  contentClassName?: string;
  header: ReactNode;
  toolbar?: ReactNode;
  toolbarClassName?: string;
}) {
  return (
    <WorkstationPanel
      className={cn(
        "grid h-full min-h-0 overflow-hidden",
        toolbar ? "grid-rows-[auto_auto_minmax(0,1fr)]" : "grid-rows-[auto_minmax(0,1fr)]",
        className,
      )}
    >
      <div className="px-[var(--pos-panel-padding-x)] py-[var(--pos-header-padding-y)]">
        {header}
      </div>
      {toolbar ? (
        <div
          className={cn(
            "border-t border-[var(--pos-shell-border)] px-[var(--pos-panel-padding-x)] py-[var(--pos-toolbar-padding-y)]",
            toolbarClassName,
          )}
        >
          {toolbar}
        </div>
      ) : null}
      <div
        className={cn(
          "min-h-0 min-w-0 overflow-hidden border-t border-[var(--pos-shell-border)]",
          toolbar && "border-t-0",
          contentClassName,
        )}
      >
        {children}
      </div>
    </WorkstationPanel>
  );
}

export const ContinuousWorkspaceSheet = CentralWorkspaceSheet;

export function SectionDivider({ className }: { className?: string }) {
  return (
    <div
      aria-hidden="true"
      className={cn("border-t border-[var(--pos-shell-border)]", className)}
    />
  );
}

export function ModuleStateChip({
  children,
  tone = "muted",
}: {
  children: ReactNode;
  tone?: "accent" | "danger" | "info" | "muted" | "primary" | "success" | "warning";
}) {
  return (
    <span
      className="pos-chip pos-state-chip"
      data-tone={getToneDataAttribute(tone, "muted")}
      title={typeof children === "string" ? children : undefined}
    >
      {children}
    </span>
  );
}

export function SectionCard({
  action,
  children,
  className,
  contentClassName,
  description,
  title,
}: {
  action?: ReactNode;
  children: ReactNode;
  className?: string;
  contentClassName?: string;
  description?: string;
  title: string;
}) {
  return (
    <WorkstationPanel
      className={cn("px-[var(--pos-panel-padding-x)] py-[var(--pos-panel-padding-y)]", className)}
    >
      <SectionHeader action={action} description={description} title={title} />
      <div className="mt-[var(--pos-section-gap)] border-t border-[var(--pos-shell-border)] pt-[var(--pos-section-gap)]">
        <div className={cn(contentClassName)}>{children}</div>
      </div>
    </WorkstationPanel>
  );
}

export function RightPanelBlock({
  action,
  children,
  className,
  contentClassName,
  description,
  title,
  tone = "default",
}: {
  action?: ReactNode;
  children?: ReactNode;
  className?: string;
  contentClassName?: string;
  description?: string;
  title: string;
  tone?: "default" | "muted";
}) {
  return (
    <section
      className={cn("pos-tonal-surface min-w-0 px-3.5 py-3", className)}
      data-tone={getToneDataAttribute(tone, "default")}
    >
      <SectionHeader action={action} description={description} title={title} />
      {children ? (
        <div className={cn("mt-[var(--pos-stack-gap)] min-w-0", contentClassName)}>{children}</div>
      ) : null}
    </section>
  );
}

export function RightPanelKpiStack({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) {
  return <div className={cn("grid min-w-0 gap-[var(--pos-stack-gap)]", className)}>{children}</div>;
}

export function CompactInfoTile({
  className,
  helper,
  label,
  tone = "muted",
  value,
  valueClassName,
}: {
  className?: string;
  helper?: ReactNode;
  label: string;
  tone?: MetricTone;
  value: ReactNode;
  valueClassName?: string;
}) {
  return (
    <div
      className={cn("pos-tonal-surface grid min-w-0 gap-1.5 px-3 py-2.5", className)}
      data-tone={getToneDataAttribute(tone, "muted")}
    >
      <p className="text-[13px] font-medium text-slate-600">{label}</p>
      <div
        className={cn(
          "min-w-0 text-sm font-semibold leading-6 text-slate-950 [font-variant-numeric:tabular-nums]",
          valueClassName,
        )}
      >
        {typeof value === "string" ? <span className="block truncate">{value}</span> : value}
      </div>
      {helper ? <div className="text-xs leading-5 text-slate-500">{helper}</div> : null}
    </div>
  );
}

export function KeyValueGroup({
  children,
  className,
  tone = "default",
}: {
  children: ReactNode;
  className?: string;
  tone?: "default" | "muted";
}) {
  return (
    <div
      className={cn(
        "pos-tonal-surface grid min-w-0 gap-2 rounded-xl border border-[var(--pos-shell-border)] px-3 py-3",
        className,
      )}
      data-tone={getToneDataAttribute(tone, "default")}
    >
      {children}
    </div>
  );
}

export function KeyValueRow({
  className,
  label,
  title,
  value,
  valueClassName,
}: {
  className?: string;
  label: string;
  title?: string;
  value: ReactNode;
  valueClassName?: string;
}) {
  return (
    <div className={cn("flex min-w-0 items-start justify-between gap-3 text-sm", className)}>
      <span className="font-medium text-slate-600">{label}</span>
      <div
        className={cn(
          "min-w-0 text-right font-semibold text-slate-950 [font-variant-numeric:tabular-nums]",
          valueClassName,
        )}
        title={title}
      >
        {typeof value === "string" ? <span className="block truncate">{value}</span> : value}
      </div>
    </div>
  );
}

export function ScrollPane({ children, className }: { children: ReactNode; className?: string }) {
  return <div className={cn("pos-scroll-pane", className)}>{children}</div>;
}

export function ListDetailShell({
  activePane = "list",
  className,
  compactMode = "stack",
  detail,
  detailClassName,
  list,
  listClassName,
  splitVariant = "default",
}: {
  activePane?: "detail" | "list";
  className?: string;
  compactMode?: "single" | "stack";
  detail: ReactNode;
  detailClassName?: string;
  list: ReactNode;
  listClassName?: string;
  splitVariant?: "default" | "narrow-list";
}) {
  return (
    <div
      className="pos-list-detail-query min-h-0 min-w-0 h-full overflow-hidden"
      data-pos-list-detail-shell="true"
    >
      <div
        className={cn("pos-list-detail-shell min-w-0 h-full", className)}
        data-active-pane={activePane}
        data-compact-mode={compactMode}
        data-split-variant={splitVariant}
      >
        <div className={cn("pos-list-detail-pane min-w-0", listClassName)} data-pane="list">
          {list}
        </div>
        <div className={cn("pos-list-detail-pane min-w-0", detailClassName)} data-pane="detail">
          {detail}
        </div>
      </div>
    </div>
  );
}

export const ResponsivePaneLayout = ListDetailShell;

export function ListDetailColumn({
  action,
  children,
  className,
  contentClassName,
  description,
  title,
  toolbar,
  tone = "default",
}: {
  action?: ReactNode;
  children: ReactNode;
  className?: string;
  contentClassName?: string;
  description?: string;
  title: string;
  toolbar?: ReactNode;
  tone?: "default" | "muted";
}) {
  return (
    <section
      className={cn(
        "pos-tonal-surface pos-list-detail-column flex h-full min-h-0 min-w-0 flex-col overflow-hidden px-3.5 py-3",
        className,
      )}
      data-tone={getToneDataAttribute(tone, "default")}
    >
      <SectionHeader action={action} description={description} title={title} />
      {toolbar ? (
        <div className="mt-[var(--pos-stack-gap)] border-t border-[var(--pos-shell-border)] pt-[var(--pos-stack-gap)]">
          {toolbar}
        </div>
      ) : null}
      <div
        className={cn(
          "mt-[var(--pos-stack-gap)] min-h-0 flex-1 overflow-hidden",
          !toolbar && "border-t border-[var(--pos-shell-border)] pt-[var(--pos-stack-gap)]",
          contentClassName,
        )}
      >
        {children}
      </div>
    </section>
  );
}

export function ListDetailToolbar({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <div className={cn("flex flex-wrap items-center justify-between gap-2.5", className)}>
      {children}
    </div>
  );
}

export function SelectableListCard({
  buttonRef,
  children,
  className,
  isSelected,
  onClick,
}: {
  buttonRef?: Ref<HTMLButtonElement>;
  children: ReactNode;
  className?: string;
  isSelected?: boolean;
  onClick: () => void;
}) {
  return (
    <button
      data-pos-selectable-card="true"
      className={cn(
        "grid w-full gap-2.5 rounded-xl border px-3 py-3 text-left shadow-sm transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--pos-ring)] focus-visible:ring-offset-2 focus-visible:ring-offset-white",
        isSelected
          ? "border-[var(--pos-primary)] bg-[var(--pos-primary-soft)]"
          : "border-[var(--pos-shell-border)] bg-white hover:-translate-y-0.5 hover:border-[var(--pos-primary)] hover:shadow-md",
        className,
      )}
      onClick={onClick}
      onKeyDown={(event) => {
        if (event.key === "ArrowDown") {
          if (
            focusRelativeItem({
              currentTarget: event.currentTarget,
              direction: 1,
              selector: "[data-pos-selectable-card='true']",
            })
          ) {
            event.preventDefault();
          }
          return;
        }

        if (event.key === "ArrowUp") {
          if (
            focusRelativeItem({
              currentTarget: event.currentTarget,
              direction: -1,
              selector: "[data-pos-selectable-card='true']",
            })
          ) {
            event.preventDefault();
          }
          return;
        }

        if (event.key === "Home") {
          if (
            focusEdgeItem({
              currentTarget: event.currentTarget,
              edge: "first",
              selector: "[data-pos-selectable-card='true']",
            })
          ) {
            event.preventDefault();
          }
          return;
        }

        if (event.key === "End") {
          if (
            focusEdgeItem({
              currentTarget: event.currentTarget,
              edge: "last",
              selector: "[data-pos-selectable-card='true']",
            })
          ) {
            event.preventDefault();
          }
        }
      }}
      ref={buttonRef}
      type="button"
    >
      {children}
    </button>
  );
}

export function OperationalField({
  children,
  className,
  helper,
  label,
}: {
  children: ReactNode;
  className?: string;
  helper?: string;
  label: string;
}) {
  return (
    <label className={cn("grid gap-2", className)}>
      <span className="pos-label-text text-slate-800">{label}</span>
      {children}
      {helper ? <span className="pos-helper-text">{helper}</span> : null}
    </label>
  );
}

export function ContextPill({
  icon,
  label,
  value,
}: {
  icon: ReactNode;
  label: string;
  value: string;
}) {
  return (
    <div className="pos-tonal-surface px-3 py-2.5" data-tone="muted">
      <div className="flex items-center gap-2 text-[13px] font-medium text-slate-600">
        <span className="text-[var(--pos-primary)]">{icon}</span>
        <span>{label}</span>
      </div>
      <p className="mt-1.5 text-[15px] font-semibold text-slate-950">{value}</p>
    </div>
  );
}

export function SummaryMetric({
  helper,
  icon,
  label,
  tone = "default",
  value,
}: {
  helper?: string;
  icon?: ReactNode;
  label: string;
  tone?: MetricTone;
  value: ReactNode;
}) {
  return (
    <div
      className="pos-tonal-surface px-3 py-2.5"
      data-tone={getToneDataAttribute(tone, "default")}
    >
      <div className="flex items-center gap-2 text-[13px] font-semibold text-slate-700">
        {icon ? <span className="text-[var(--pos-primary)]">{icon}</span> : null}
        <span>{label}</span>
      </div>
      <div className="mt-1.5 min-w-0 break-words text-[1.45rem] font-semibold leading-tight text-slate-950 [font-variant-numeric:tabular-nums] sm:text-[1.55rem]">
        {value}
      </div>
      {helper ? <p className="pos-helper-text mt-1.5">{helper}</p> : null}
    </div>
  );
}

export function MetricCard({
  helper,
  icon,
  tone = "default",
  value,
}: {
  helper?: string;
  icon?: ReactNode;
  tone?: MetricTone;
  value: ReactNode;
}) {
  return (
    <div
      className="pos-tonal-surface px-3 py-2.5"
      data-tone={getToneDataAttribute(tone, "default")}
    >
      <div className="flex items-center gap-2 text-[13px] font-semibold text-slate-700">
        {icon ? <span className="text-[var(--pos-primary)]">{icon}</span> : null}
        {helper ? <span>{helper}</span> : null}
      </div>
      <div className="mt-1.5 min-w-0 break-words text-[1.4rem] font-semibold leading-tight text-slate-950 [font-variant-numeric:tabular-nums] sm:text-[1.5rem]">
        {value}
      </div>
    </div>
  );
}

export function SearchField({
  ariaLabel,
  className,
  disabled = false,
  inputClassName,
  inputRef,
  onChange,
  onKeyDown,
  placeholder,
  value,
}: {
  ariaLabel: string;
  className?: string;
  disabled?: boolean;
  inputClassName: string;
  inputRef?: Ref<HTMLInputElement>;
  onChange: (value: string) => void;
  onKeyDown?: (event: KeyboardEvent<HTMLInputElement>) => void;
  placeholder: string;
  value: string;
}) {
  return (
    <label className={cn("relative block min-w-0 overflow-hidden", className)}>
      <span className="pointer-events-none absolute inset-y-0 left-3.5 flex items-center text-slate-400">
        <SearchIcon className="h-4 w-4" />
      </span>
      <input
        aria-label={ariaLabel}
        className={cn("w-full min-w-0 pl-11 pr-3.5", inputClassName)}
        disabled={disabled}
        onChange={(event) => onChange(event.target.value)}
        onKeyDown={onKeyDown}
        placeholder={placeholder}
        ref={inputRef}
        value={value}
      />
    </label>
  );
}

export type ProgressStepperStep = {
  completed?: boolean;
  disabled?: boolean;
  id: string;
  label: string;
  state?: "blocked" | "completed" | "current" | "upcoming";
};

export function ProgressStepper({
  ariaLabel = "Progreso del flujo",
  className,
  clickable = false,
  currentLabel,
  currentStep,
  onStepClick,
  onStepSelect,
  steps,
  stepLabels,
  totalSteps,
  variant = "progress",
}: {
  ariaLabel?: string;
  className?: string;
  clickable?: boolean;
  currentLabel?: string;
  currentStep: number;
  onStepClick?: (stepId: string) => void;
  onStepSelect?: (stepIndex: number) => void;
  steps?: ProgressStepperStep[];
  stepLabels?: string[];
  totalSteps?: number;
  variant?: "navigation" | "progress" | "workflow";
}) {
  const safeTotal = Math.max(1, steps?.length ?? totalSteps ?? stepLabels?.length ?? 1);
  const safeCurrentStep = Math.min(Math.max(1, currentStep), safeTotal);
  const normalizedSteps = Array.from({ length: safeTotal }, (_, index) => {
    const explicitStep = steps?.[index];
    const stepNumber = index + 1;
    const state = explicitStep?.state;

    return {
      completed:
        explicitStep?.completed ?? (state ? state === "completed" : stepNumber < safeCurrentStep),
      disabled: explicitStep?.disabled ?? state === "blocked",
      id: explicitStep?.id ?? String(stepNumber),
      label: explicitStep?.label ?? stepLabels?.[index] ?? `Paso ${stepNumber}`,
      state,
    };
  });
  const activeStep = normalizedSteps[safeCurrentStep - 1];
  const resolvedLabel = currentLabel ?? activeStep?.label ?? "";

  return (
    <div
      aria-label={ariaLabel}
      aria-valuemax={clickable ? undefined : safeTotal}
      aria-valuemin={clickable ? undefined : 1}
      aria-valuenow={clickable ? undefined : safeCurrentStep}
      className={cn("grid gap-2", variant === "navigation" && "gap-2.5", className)}
      role={clickable ? undefined : "progressbar"}
    >
      <div className="flex min-w-0 items-center justify-between gap-3">
        <p className="min-w-0 truncate text-[12px] font-semibold uppercase tracking-[0.08em] text-slate-500">
          Paso {safeCurrentStep} de {safeTotal}
          {resolvedLabel ? (
            <>
              {" \u00b7 "}
              <span className="text-slate-700">{resolvedLabel}</span>
            </>
          ) : null}
        </p>
      </div>

      <ol className="grid min-w-0 grid-flow-col gap-1.5" data-pos-progress-stepper="true">
        {normalizedSteps.map((step, index) => {
          const stepNumber = index + 1;
          const isCompleted = step.completed || stepNumber < safeCurrentStep;
          const isCurrent = step.state === "current" || stepNumber === safeCurrentStep;
          const isDisabled = step.disabled;
          const activateStep = () => {
            if (isDisabled) {
              return;
            }

            onStepClick?.(step.id);
            onStepSelect?.(stepNumber);
          };
          const segmentClassName = cn(
            "h-1.5 rounded-full transition-colors",
            isCompleted
              ? "bg-[var(--pos-primary)]/70"
              : isCurrent
                ? "bg-[var(--pos-primary)]"
                : isDisabled
                  ? "bg-slate-200/70"
                  : "bg-slate-200",
          );

          return (
            <li className="min-w-0" key={step.id}>
              {clickable ? (
                <button
                  aria-disabled={isDisabled || undefined}
                  aria-current={isCurrent ? "step" : undefined}
                  aria-label={`${step.label} (${stepNumber} de ${safeTotal})`}
                  className={cn(
                    "block w-full rounded-full focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--pos-ring)] focus-visible:ring-offset-2 focus-visible:ring-offset-white",
                    segmentClassName,
                    isDisabled && "cursor-not-allowed",
                  )}
                  disabled={isDisabled}
                  onClick={activateStep}
                  onKeyDown={(event) => {
                    if (event.key !== "Enter" && event.key !== " ") {
                      return;
                    }

                    event.preventDefault();
                    activateStep();
                  }}
                  title={step.label}
                  type="button"
                />
              ) : (
                <span
                  aria-current={isCurrent ? "step" : undefined}
                  aria-label={`${step.label} (${stepNumber} de ${safeTotal})`}
                  className={cn("block w-full", segmentClassName)}
                  title={step.label}
                />
              )}
            </li>
          );
        })}
      </ol>
    </div>
  );
}

export function FlowGuide({
  activeStepKey,
  ariaLabel = "Flujo operativo",
  onStepSelect,
  steps,
  variant = "default",
}: {
  activeStepKey: string;
  ariaLabel?: string;
  onStepSelect?: (stepKey: string) => void;
  steps: Array<{
    icon?: ReactNode;
    isBlocked?: boolean;
    key: string;
    label: string;
    state?: "blocked" | "completed" | "current" | "upcoming";
  }>;
  variant?: "compact" | "default" | "process" | "stepper";
}) {
  const activeStepIndex = steps.findIndex((step) => step.key === activeStepKey);
  const safeActiveStepIndex = activeStepIndex >= 0 ? activeStepIndex : 0;
  const normalizedSteps = steps.map((step, index) => {
    const derivedState =
      step.state ??
      (step.key === activeStepKey
        ? "current"
        : step.isBlocked
          ? "blocked"
          : activeStepIndex >= 0 && index < activeStepIndex
            ? "completed"
            : "upcoming");

    return {
      completed: derivedState === "completed",
      disabled: derivedState === "blocked",
      id: step.key,
      label: step.label,
      state: derivedState,
    };
  });

  return (
    <ProgressStepper
      ariaLabel={ariaLabel}
      clickable={Boolean(onStepSelect)}
      currentStep={safeActiveStepIndex + 1}
      onStepClick={onStepSelect}
      steps={normalizedSteps}
      variant={onStepSelect ? "navigation" : variant === "process" ? "workflow" : "progress"}
    />
  );
}

export function FilterButton({
  className,
  count,
  isActive,
  label,
  onClick,
}: {
  className?: string;
  count?: number;
  isActive: boolean;
  label: string;
  onClick: () => void;
}) {
  return (
    <button
      className={cn(
        "inline-flex min-h-9 items-center gap-2 rounded-full border px-3 py-1.5 text-sm font-medium transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--pos-ring)] focus-visible:ring-offset-2 focus-visible:ring-offset-white",
        isActive
          ? "border-[var(--pos-primary)] bg-[var(--pos-primary-soft)] text-[var(--pos-primary)]"
          : "border-[var(--pos-shell-border)] bg-white text-slate-700 hover:border-[var(--pos-primary)] hover:bg-[var(--pos-shell-muted)]",
        className,
      )}
      data-active={isActive || undefined}
      onClick={onClick}
      type="button"
    >
      <span>{label}</span>
      {typeof count === "number" ? (
        <span
          className={cn(
            "pos-filter-button__count rounded-full px-1.5 py-0.5 text-[12px] font-semibold",
            isActive ? "bg-white/80" : "bg-[var(--pos-shell-muted)] text-slate-500",
          )}
        >
          {count}
        </span>
      ) : null}
    </button>
  );
}

export function SegmentedControl({
  className,
  onChange,
  options,
  value,
}: {
  className?: string;
  onChange: (value: string) => void;
  options: Array<{
    icon?: ReactNode;
    label: string;
    value: string;
  }>;
  value: string;
}) {
  return (
    <div className={cn("flex flex-wrap items-center gap-2", className)}>
      {options.map((option) => {
        const isActive = option.value === value;

        return (
          <button
            className={cn(
              "inline-flex min-h-10 items-center gap-2 rounded-[var(--pos-radius-control)] border px-3 py-2 text-sm font-medium transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--pos-ring)] focus-visible:ring-offset-2 focus-visible:ring-offset-white",
              isActive
                ? "border-[var(--pos-primary)] bg-[var(--pos-primary-soft)] text-[var(--pos-primary)]"
                : "border-[var(--pos-shell-border)] bg-white text-slate-700 hover:border-[var(--pos-primary)] hover:bg-[var(--pos-shell-muted)]",
            )}
            key={option.value}
            onClick={() => onChange(option.value)}
            type="button"
          >
            {option.icon ? <span className="shrink-0">{option.icon}</span> : null}
            <span>{option.label}</span>
          </button>
        );
      })}
    </div>
  );
}

export function InlineNotice({
  action,
  children,
  tone = "info",
}: {
  action?: ReactNode;
  children: ReactNode;
  tone?: NoticeTone;
}) {
  return (
    <div className="pos-inline-notice" data-tone={tone}>
      <div className="min-w-0 flex-1 text-sm leading-6">{children}</div>
      {action ? <div className="shrink-0">{action}</div> : null}
    </div>
  );
}

export function InlineMessage({
  action,
  children,
  tone = "info",
}: {
  action?: ReactNode;
  children: ReactNode;
  tone?: NoticeTone;
}) {
  return (
    <InlineNotice action={action} tone={tone}>
      {children}
    </InlineNotice>
  );
}
