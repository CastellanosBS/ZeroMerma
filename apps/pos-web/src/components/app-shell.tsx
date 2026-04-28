import { useNavigate, useRouterState } from "@tanstack/react-router";
import {
  type CSSProperties,
  type PropsWithChildren,
  type ReactNode,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";

import { AppShellRightPanelContext } from "./app-shell-right-panel";
import { AppShellSidebar } from "./app-shell-sidebar";
import { InlineNotice, RightPanelBlock } from "./pos-module-primitives";
import { PosStatusBadge } from "./pos-foundations";
import { TrainingModeBanner } from "./training-mode-banner";
import { Button } from "./ui/button";
import { PosCheckoutPanel } from "../features/pos-terminal/pos-checkout-panel";
import { useCashCloseSummaryQuery } from "../features/cash-close/queries";
import { useOrdersListQuery } from "../features/orders/queries";
import {
  KeyboardHelpOverlay,
  KeyboardShortcutRegistry,
  type KeyboardShortcutDefinition,
  useModuleHotkeys,
} from "../features/pos-shell/keyboard";
import {
  posModules,
  resolveActivePosModule,
} from "../features/pos-shell/modules";
import { usePosShellStore } from "../features/pos-shell/shell-store";
import { getPosBranchTheme, posOutlineButtonClass } from "../features/pos-theme/theme";
import { usePendingInboundTransfersQuery } from "../features/transfers/queries";
import type { CashSessionView, PosBootstrapResponse } from "../lib/api-contracts";
import { formatCurrency } from "../lib/formatters";
import { cn } from "../lib/utils";
import {
  AlertTriangleIcon,
  ClockIcon,
  LogoutIcon,
  MenuIcon,
  MoneyIcon,
  OperatorIcon,
  ReceiptIcon,
  SearchIcon,
  XIcon,
} from "./pos-icons";

interface AppShellProps extends PropsWithChildren {
  bootstrap: PosBootstrapResponse;
  cashSession: CashSessionView | null;
  onSignOut: () => void;
}

interface CommandAction {
  description: string;
  disabled?: boolean;
  key: string;
  label: string;
  onSelect: () => void;
  shortcut?: string;
  tag?: string;
}

function getBrandLabel(brandKey: string): string {
  if (brandKey === "EL_MEJOR_PAN") {
    return "El Mejor Pan";
  }

  return "Merenna";
}

function getShiftStateLabel(cashSession: CashSessionView | null): string {
  return cashSession ? "Caja abierta" : "Apertura pendiente";
}

function formatLiveLocalClock(timeZone: string, timestamp: number): string {
  return new Intl.DateTimeFormat("es-MX", {
    day: "2-digit",
    hour: "numeric",
    minute: "2-digit",
    month: "short",
    timeZone,
    year: "numeric",
  }).format(new Date(timestamp));
}

function formatElapsedDuration(openedAtUtc: string, timestamp: number): string {
  const openedAt = new Date(openedAtUtc).getTime();
  if (Number.isNaN(openedAt)) {
    return "Sin referencia";
  }

  const totalMinutes = Math.max(Math.floor((timestamp - openedAt) / 60_000), 0);
  const hours = Math.floor(totalMinutes / 60);
  const minutes = totalMinutes % 60;

  if (hours <= 0) {
    return `${minutes} min`;
  }

  return `${hours} h ${minutes.toString().padStart(2, "0")} min`;
}

function getCountValue(count: number | null): string {
  if (count === null) {
    return "--";
  }

  return `${count}`;
}

function ShellSummaryMetric({
  label,
  tone = "default",
  value,
}: {
  label: string;
  tone?: "default" | "financial";
  value: string;
}) {
  return (
    <div
      className="pos-tonal-surface grid min-w-0 content-start gap-1.5 rounded-[1.35rem] px-3 py-3"
      data-tone={tone === "financial" ? "financial" : undefined}
    >
      <p className="min-w-0 text-[13px] font-semibold leading-4 text-slate-700 [overflow-wrap:anywhere]">
        {label}
      </p>
      <p
        className={cn(
          "min-w-0 whitespace-normal text-[1rem] font-semibold leading-5 text-slate-950 [overflow-wrap:anywhere]",
          value.length <= 3 && "text-[1.2rem] leading-6 [font-variant-numeric:tabular-nums]",
        )}
      >
        {value}
      </p>
    </div>
  );
}

function ShellInfoPill({
  icon,
  label,
  tone = "default",
  value,
}: {
  icon: ReactNode;
  label: string;
  tone?: "default" | "warning";
  value: string;
}) {
  return (
    <div
      className={cn(
        "flex min-w-0 items-center gap-2 rounded-[var(--pos-radius-control)] border px-3 py-2",
        tone === "warning"
          ? "border-[var(--ui-color-warning-soft)] bg-[var(--ui-color-warning-soft)]"
          : "border-[var(--pos-shell-border)] bg-white",
      )}
    >
      <span
        className={cn(
          "flex h-8 w-8 shrink-0 items-center justify-center rounded-xl",
          tone === "warning"
            ? "bg-white text-[var(--ui-color-warning)]"
            : "bg-[var(--pos-shell-muted)] text-[var(--pos-primary)]",
        )}
      >
        {icon}
      </span>
      <span className="min-w-0">
        <span className="pos-label-text block">{label}</span>
        <span className="block truncate text-sm font-semibold leading-5 text-slate-950">{value}</span>
      </span>
    </div>
  );
}

function CommandPalette({
  actions,
  isOpen,
  onClose,
}: {
  actions: CommandAction[];
  isOpen: boolean;
  onClose: () => void;
}) {
  const [query, setQuery] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!isOpen) {
      setQuery("");
      return;
    }

    window.setTimeout(() => inputRef.current?.focus(), 0);
  }, [isOpen]);

  const filteredActions = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase();
    if (normalizedQuery.length === 0) {
      return actions;
    }

    return actions.filter((action) =>
      `${action.label} ${action.description} ${action.tag ?? ""}`.toLowerCase().includes(normalizedQuery),
    );
  }, [actions, query]);

  if (!isOpen) {
    return null;
  }

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center bg-slate-950/30 px-4 py-10 backdrop-blur-[2px]">
      <div className="w-full max-w-2xl overflow-hidden rounded-[28px] border border-[var(--pos-shell-border)] bg-white shadow-[var(--ui-shadow-overlay)]">
        <div className="flex items-center gap-3 border-b border-[var(--pos-shell-border)] px-5 py-4">
          <span className="flex h-10 w-10 items-center justify-center rounded-2xl bg-[var(--pos-primary-soft)] text-[var(--pos-primary)]">
            <SearchIcon className="h-4 w-4" />
          </span>
          <input
            aria-label="Buscar accion"
            className="h-11 flex-1 border-0 bg-transparent text-base text-slate-950 outline-none placeholder:text-slate-400"
            onChange={(event) => setQuery(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Escape") {
                event.preventDefault();
                onClose();
              }
            }}
            placeholder="Buscar modulo o accion rapida"
            ref={inputRef}
            value={query}
          />
          <Button className={cn("h-11 w-11 p-0", posOutlineButtonClass)} onClick={onClose} size="icon" type="button" variant="outline">
            <XIcon className="h-4 w-4" />
          </Button>
        </div>

        <div className="max-h-[26rem] overflow-y-auto px-3 py-3">
          <div className="grid gap-2">
            {filteredActions.length === 0 ? (
              <div className="rounded-2xl border border-dashed border-[var(--pos-shell-border)] bg-[var(--pos-shell-muted)] px-4 py-8 text-center text-sm text-slate-600">
                No hay acciones para la busqueda actual.
              </div>
            ) : (
              filteredActions.map((action) => (
                <button
                  className={cn(
                    "grid gap-1 rounded-2xl border px-4 py-3 text-left transition",
                    action.disabled
                      ? "cursor-not-allowed border-[var(--pos-shell-border)] bg-[var(--pos-shell-muted)] text-slate-400"
                      : "border-[var(--pos-shell-border)] bg-white hover:border-[var(--pos-primary)] hover:bg-[var(--pos-primary-soft)]",
                  )}
                  disabled={action.disabled}
                  key={action.key}
                  onClick={() => {
                    action.onSelect();
                    onClose();
                  }}
                  type="button"
                >
                  <div className="flex items-center justify-between gap-3">
                    <p className="text-sm font-semibold text-slate-950">{action.label}</p>
                    {action.shortcut ? (
                      <span className="pos-kbd-chip">
                        {action.shortcut}
                      </span>
                    ) : null}
                  </div>
                  <p className="text-sm leading-5 text-slate-600">{action.description}</p>
                </button>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function DefaultShellRightPanel({
  activeModuleDescription,
  activeModuleLabel,
  branchLabel,
  closeBlockersCount,
  closeWarningsCount,
  hasCashSession,
  openingAmount,
  onOpenQuickActions,
  pendingInboundTransfersCount,
  pendingOrdersCount,
}: {
  activeModuleDescription: string;
  activeModuleLabel: string;
  branchLabel: string;
  closeBlockersCount: number | null;
  closeWarningsCount: number | null;
  hasCashSession: boolean;
  onOpenQuickActions: () => void;
  openingAmount: string;
  pendingInboundTransfersCount: number | null;
  pendingOrdersCount: number | null;
}) {
  const closeIssueCount = (closeBlockersCount ?? 0) + (closeWarningsCount ?? 0);

  return (
    <div className="pos-shell-panel grid h-full min-h-0 grid-rows-[auto_auto_1fr_auto] gap-[var(--pos-section-gap)] p-[var(--pos-shell-workstation-padding)]">
      <RightPanelBlock
        action={
          <span className="pos-chip" data-tone="accent">
            {branchLabel}
          </span>
        }
        description={activeModuleDescription}
        title={activeModuleLabel}
      />

      <RightPanelBlock title="Operacion actual" tone="muted">
        <div className="grid gap-2 sm:grid-cols-2">
          <ShellSummaryMetric label="Turno" value={hasCashSession ? "Activo" : "Pendiente"} />
          <ShellSummaryMetric label="Apertura" tone="financial" value={openingAmount} />
          <ShellSummaryMetric label="Pedidos pendientes" value={getCountValue(pendingOrdersCount)} />
          <ShellSummaryMetric
            label="Envios por recibir"
            value={getCountValue(pendingInboundTransfersCount)}
          />
        </div>
      </RightPanelBlock>

      <div className="grid min-h-0 content-start gap-[var(--pos-section-gap)]">
        {closeIssueCount > 0 ? (
          <InlineNotice tone="warning">
            <p>
              Hay {closeBlockersCount ?? 0} bloqueos y {closeWarningsCount ?? 0} alertas de cierre
              por revisar.
            </p>
          </InlineNotice>
        ) : null}

        <RightPanelBlock title="Acciones rapidas" tone="muted">
          <div className="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-2.5 rounded-[var(--pos-radius-control)] border border-[var(--pos-shell-border)] bg-white px-3 py-2.5 text-sm">
            <span className="min-w-0 font-medium leading-5 text-slate-900 [overflow-wrap:anywhere]">
              Abrir buscador operativo
            </span>
            <span className="pos-kbd-chip shrink-0 whitespace-nowrap px-2 text-[0.6875rem]">
              Ctrl/Cmd + K
            </span>
          </div>
        </RightPanelBlock>
      </div>

      <Button className="h-11 w-full" onClick={onOpenQuickActions} type="button">
        Abrir acciones rapidas
      </Button>
    </div>
  );
}

function getModulePathForResume(pathname: string): boolean {
  return pathname !== "/" && pathname !== "/cash-session/open" && pathname !== "/login" && pathname !== "/health";
}

function AppShellFrame({ bootstrap, cashSession, children, onSignOut }: AppShellProps) {
  const navigate = useNavigate();
  const branchTheme = getPosBranchTheme(bootstrap);
  const pathname = useRouterState({
    select: (state) => state.location.pathname,
  });
  const activeModule = resolveActivePosModule(pathname);
  const isSidebarCollapsed = usePosShellStore((state) => state.isSidebarCollapsed);
  const lastOperationalPath = usePosShellStore((state) => state.lastOperationalPath);
  const setLastOperationalPath = usePosShellStore((state) => state.setLastOperationalPath);
  const toggleSidebar = usePosShellStore((state) => state.toggleSidebar);
  const ordersQuery = useOrdersListQuery("PENDING", "", "", "", cashSession !== null);
  const pendingInboundTransfersQuery = usePendingInboundTransfersQuery(cashSession !== null);
  const cashCloseSummaryQuery = useCashCloseSummaryQuery(cashSession !== null);
  const [rightPanelContent, setRightPanelContent] = useState<ReactNode | null>(null);
  const [isCommandPaletteOpen, setIsCommandPaletteOpen] = useState(false);
  const [isCompactShell, setIsCompactShell] = useState(false);
  const [isMediumShell, setIsMediumShell] = useState(false);
  const [isInlineRightPanel, setIsInlineRightPanel] = useState(true);
  const [isSidebarKeyboardNavigationEnabled, setIsSidebarKeyboardNavigationEnabled] = useState(false);
  const [isSidebarDrawerOpen, setIsSidebarDrawerOpen] = useState(false);
  const [isRightPanelDrawerOpen, setIsRightPanelDrawerOpen] = useState(false);
  const [liveTimestamp, setLiveTimestamp] = useState(() => Date.now());

  useEffect(() => {
    const intervalId = window.setInterval(() => setLiveTimestamp(Date.now()), 1_000);
    return () => window.clearInterval(intervalId);
  }, []);

  useEffect(() => {
    const compactQuery = window.matchMedia("(max-width: 1023px)");
    const mediumQuery = window.matchMedia("(max-width: 1439px)");
    const inlineRightPanelQuery = window.matchMedia("(min-width: 1200px)");

    const syncViewportState = () => {
      setIsCompactShell(compactQuery.matches);
      setIsMediumShell(mediumQuery.matches);
      setIsInlineRightPanel(inlineRightPanelQuery.matches);
    };

    syncViewportState();

    compactQuery.addEventListener("change", syncViewportState);
    mediumQuery.addEventListener("change", syncViewportState);
    inlineRightPanelQuery.addEventListener("change", syncViewportState);
    return () => {
      compactQuery.removeEventListener("change", syncViewportState);
      mediumQuery.removeEventListener("change", syncViewportState);
      inlineRightPanelQuery.removeEventListener("change", syncViewportState);
    };
  }, []);

  useEffect(() => {
    if (!getModulePathForResume(pathname)) {
      return;
    }

    setLastOperationalPath(activeModule.path);
    setIsSidebarKeyboardNavigationEnabled(false);
    setIsSidebarDrawerOpen(false);
    setIsRightPanelDrawerOpen(false);
  }, [activeModule.path, pathname, setLastOperationalPath]);

  const localClock = useMemo(
    () => formatLiveLocalClock(bootstrap.branch.timezone, liveTimestamp),
    [bootstrap.branch.timezone, liveTimestamp],
  );
  const shiftStateLabel = getShiftStateLabel(cashSession);
  const shiftElapsed = cashSession
    ? formatElapsedDuration(cashSession.opened_at, liveTimestamp)
    : "Sin turno";
  const pendingOrdersCount = ordersQuery.data?.orders.length ?? null;
  const pendingInboundTransfersCount = pendingInboundTransfersQuery.data?.transfers.length ?? null;
  const closeBlockersCount = cashCloseSummaryQuery.data?.blockers.length ?? null;
  const closeWarningsCount = cashCloseSummaryQuery.data?.warnings.length ?? null;
  const isInlineSidebar = !isCompactShell;
  const effectiveSidebarCollapsed = isInlineSidebar && (isSidebarCollapsed || isMediumShell);
  const rightPanelContextValue = useMemo(
    () => ({ setRightPanelContent }),
    [setRightPanelContent],
  );
  const shellGridStyle = useMemo(
    () =>
      ({
        "--pos-shell-right-current": isMediumShell
          ? "var(--pos-shell-right-width-medium)"
          : "var(--pos-shell-right-width)",
        "--pos-shell-sidebar-current": effectiveSidebarCollapsed
          ? "var(--pos-shell-sidebar-collapsed-width)"
          : "var(--pos-shell-sidebar-width)",
      }) as CSSProperties,
    [effectiveSidebarCollapsed, isMediumShell],
  );

  const focusSidebarNavigation = useCallback(() => {
    setIsSidebarKeyboardNavigationEnabled(true);

    const focusSidebarTarget = (sidebarMode: "drawer" | "inline") => {
      window.setTimeout(() => {
        document
          .querySelector<HTMLElement>(
            `[data-pos-shell-region="sidebar"][data-pos-shell-sidebar-mode="${sidebarMode}"] [data-pos-shell-nav-item][data-state="active"], ` +
              `[data-pos-shell-region="sidebar"][data-pos-shell-sidebar-mode="${sidebarMode}"] [data-pos-shell-nav-item][data-state="idle"]`,
          )
          ?.focus();
      }, 0);
    };

    if (!isInlineSidebar) {
      setIsSidebarDrawerOpen(true);
      focusSidebarTarget("drawer");
      return;
    }

    focusSidebarTarget("inline");
  }, [isInlineSidebar]);

  const commandActions = useMemo<CommandAction[]>(() => {
    const actions = posModules.map((module) => ({
      description: module.description,
      disabled: cashSession === null && module.key !== "pos",
      key: module.key,
      label: module.label,
      onSelect: () => void navigate({ to: module.path }),
      shortcut: module.navigationShortcut,
      tag: module.shortLabel,
    }));

    return [
      ...actions,
      {
        description: "Abrir o revisar el estado de la caja actual.",
        key: "cash-session",
        label: cashSession ? "Revisar caja abierta" : "Abrir caja",
        onSelect: () => void navigate({ to: cashSession ? (lastOperationalPath ?? "/pos") : "/cash-session/open" }),
        tag: "Caja",
      },
      {
        description: "Cerrar la sesion del cajero en esta estacion.",
        key: "sign-out",
        label: "Cerrar sesion",
        onSelect: onSignOut,
        tag: "Cuenta",
      },
    ];
  }, [cashSession, lastOperationalPath, navigate, onSignOut]);

  const shellShortcuts = useMemo<KeyboardShortcutDefinition[]>(
    () => [
      {
        chords: ["Ctrl+K", "Meta+K"],
        description: "Abre el buscador operativo y las acciones rapidas.",
        group: "Shell",
        handler: () => setIsCommandPaletteOpen(true),
        id: "shell-open-command-palette",
        label: "Abrir acciones rapidas",
        order: 10,
        priority: 100,
      },
      {
        chords: ["Ctrl+Shift+B"],
        description: "Lleva el foco a la navegacion lateral del POS.",
        group: "Shell",
        handler: () => focusSidebarNavigation(),
        id: "shell-focus-sidebar",
        label: "Ir a modulos",
        order: 20,
        priority: 100,
      },
      ...posModules.map((module, index) => ({
        chords: [module.navigationShortcut],
        description: `Abre ${module.label} desde cualquier flujo del POS.`,
        group: "Modulos",
        handler: () => {
          if (cashSession === null && module.key !== "pos") {
            return;
          }

          void navigate({ to: module.path });
        },
        id: `shell-go-to-${module.key}`,
        isEnabled: () => cashSession !== null || module.key === "pos",
        label: `Ir a ${module.label}`,
        order: 100 + index,
        priority: 90,
      })),
      {
        chords: ["Escape"],
        description: "Cierra paneles temporales o el buscador operativo.",
        group: "Shell",
        handler: () => {
          setIsSidebarDrawerOpen(false);
          setIsRightPanelDrawerOpen(false);
          setIsCommandPaletteOpen(false);
          setIsSidebarKeyboardNavigationEnabled(false);
        },
        id: "shell-close-transient-ui",
        isEnabled: () =>
          isSidebarDrawerOpen ||
          isRightPanelDrawerOpen ||
          isCommandPaletteOpen ||
          isSidebarKeyboardNavigationEnabled,
        label: "Cerrar panel temporal",
        order: 30,
        priority: 10,
      },
    ],
    [
      cashSession,
      focusSidebarNavigation,
      isCommandPaletteOpen,
      isRightPanelDrawerOpen,
      isSidebarDrawerOpen,
      isSidebarKeyboardNavigationEnabled,
      navigate,
    ],
  );

  useModuleHotkeys(shellShortcuts);

  const defaultRightPanel = (
    <DefaultShellRightPanel
      activeModuleDescription={activeModule.description}
      activeModuleLabel={activeModule.label}
      branchLabel={getBrandLabel(branchTheme.brandKey)}
      closeBlockersCount={closeBlockersCount}
      closeWarningsCount={closeWarningsCount}
      hasCashSession={cashSession !== null}
      onOpenQuickActions={() => setIsCommandPaletteOpen(true)}
      openingAmount={cashSession ? formatCurrency(cashSession.opening_amount) : "--"}
      pendingInboundTransfersCount={pendingInboundTransfersCount}
      pendingOrdersCount={pendingOrdersCount}
    />
  );
  const resolvedRightPanel =
    rightPanelContent ??
    (pathname === "/pos" && cashSession ? <PosCheckoutPanel bootstrap={bootstrap} /> : defaultRightPanel);
  const sidebarNavigation = (
    <AppShellSidebar
      activeModuleKey={activeModule.key}
      collapsed={effectiveSidebarCollapsed}
      hasCashSession={cashSession !== null}
      isKeyboardNavigationEnabled={isSidebarKeyboardNavigationEnabled}
      modules={posModules}
      onNavigate={(path) => {
        setIsSidebarDrawerOpen(false);
        setIsSidebarKeyboardNavigationEnabled(false);
        void navigate({ to: path });
      }}
      onNavigationModeChange={setIsSidebarKeyboardNavigationEnabled}
    />
  );

  return (
    <div
      className="flex h-[100dvh] flex-col overflow-hidden bg-[var(--pos-shell-bg)] text-slate-950"
      data-pos-brand={branchTheme.brandKey}
      data-pos-workstation="true"
      style={branchTheme.style}
    >
      <TrainingModeBanner trainingMode={bootstrap.training_mode} />
      <header
        className="relative z-10 shrink-0 border-b border-[var(--pos-shell-border)] bg-[var(--pos-shell-topbar)]"
        style={{ minHeight: "var(--pos-shell-topbar-height)" }}
      >
        <div
          className="mx-auto flex w-full flex-wrap items-center gap-3 px-[var(--pos-shell-workstation-padding)] py-3"
          style={{ maxWidth: "var(--pos-shell-max-width)" }}
        >
          <div className="flex min-w-0 flex-1 items-center gap-3">
            <Button
              aria-expanded={isCompactShell ? isSidebarDrawerOpen : !effectiveSidebarCollapsed}
              aria-label={isCompactShell ? "Abrir navegacion" : effectiveSidebarCollapsed ? "Expandir barra lateral" : "Contraer barra lateral"}
              className={cn("h-10 px-3", posOutlineButtonClass)}
              onClick={() => {
                if (isCompactShell) {
                  setIsSidebarKeyboardNavigationEnabled(false);
                  setIsSidebarDrawerOpen(true);
                  return;
                }

                setIsSidebarKeyboardNavigationEnabled(false);
                toggleSidebar();
              }}
              title={isCompactShell ? "Abrir navegacion" : effectiveSidebarCollapsed ? "Expandir barra lateral" : "Contraer barra lateral"}
              type="button"
              variant="outline"
            >
              <MenuIcon className="h-4 w-4" />
            </Button>

            <div className="pos-shell-panel flex min-w-0 items-center gap-3 px-3 py-2">
              <div
                className="flex h-10 w-10 items-center justify-center rounded-[var(--pos-radius-control)] text-sm font-semibold"
                style={{
                  backgroundColor: "var(--pos-brand-mark-bg)",
                  color: "var(--pos-brand-mark-fg)",
                }}
              >
                {branchTheme.brandMark}
              </div>
              <div className="min-w-0">
                <div className="flex min-w-0 items-center gap-2">
                  <p className="truncate text-base font-semibold text-slate-950">
                    {bootstrap.branch.name}
                  </p>
                  <span className="pos-chip" data-tone="accent">
                    {getBrandLabel(branchTheme.brandKey)}
                  </span>
                  <PosStatusBadge status="confirmed">{activeModule.label}</PosStatusBadge>
                </div>
                <p className="truncate text-xs text-slate-500">
                  {bootstrap.workstation.name} | {bootstrap.workstation.code}
                </p>
              </div>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <ShellInfoPill
              icon={<OperatorIcon className="h-4 w-4" />}
              label="Cajero"
              value={bootstrap.user.full_name}
            />
            <ShellInfoPill
              icon={<MoneyIcon className="h-4 w-4" />}
              label="Turno"
              value={cashSession ? `${shiftStateLabel} - ${shiftElapsed}` : shiftStateLabel}
            />
            <ShellInfoPill
              icon={<ClockIcon className="h-4 w-4" />}
              label="Hora local"
              value={localClock}
            />
            <ShellInfoPill
              icon={<AlertTriangleIcon className="h-4 w-4" />}
              label="Cierre"
              tone={(closeBlockersCount ?? 0) > 0 ? "warning" : "default"}
              value={
                (closeBlockersCount ?? 0) > 0
                  ? `${closeBlockersCount} bloqueos`
                  : (closeWarningsCount ?? 0) > 0
                    ? `${closeWarningsCount} alertas`
                    : "Sin alertas"
              }
            />

            {!isInlineRightPanel ? (
              <Button
                aria-label="Abrir resumen operativo"
                className={cn("h-10 gap-2 px-3", posOutlineButtonClass)}
                onClick={() => setIsRightPanelDrawerOpen(true)}
                title="Abrir resumen operativo"
                type="button"
                variant="outline"
              >
                <ReceiptIcon className="h-4 w-4" />
                <span className="hidden sm:inline">Resumen</span>
              </Button>
            ) : null}

            <Button
              aria-label="Acciones rapidas"
              className={cn("h-10 px-3", posOutlineButtonClass)}
              onClick={() => setIsCommandPaletteOpen(true)}
              title="Acciones rapidas"
              type="button"
              variant="outline"
            >
              <SearchIcon className="h-4 w-4" />
            </Button>

            <Button
              aria-label="Cerrar sesion"
              className={cn("h-10 px-3", posOutlineButtonClass)}
              onClick={onSignOut}
              title="Cerrar sesion"
              type="button"
              variant="outline"
            >
              <LogoutIcon className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </header>

      <AppShellRightPanelContext.Provider value={rightPanelContextValue}>
        <div
          className="mx-auto flex min-h-0 w-full flex-1 overflow-hidden px-[var(--pos-shell-workstation-padding)] py-[var(--pos-shell-workstation-padding)]"
          style={{ maxWidth: "var(--pos-shell-max-width)" }}
        >
          <div className="pos-shell-grid" style={shellGridStyle}>
            {isInlineSidebar ? (
              <aside
                className="pos-shell-panel min-h-0 overflow-hidden p-2.5"
                data-pos-shell-region="sidebar"
                data-pos-shell-sidebar-mode="inline"
              >
                {sidebarNavigation}
              </aside>
            ) : null}

            <main className="min-w-0 min-h-0 overflow-hidden" data-pos-shell-region="center">
              {children}
            </main>

            {isInlineRightPanel ? (
              <aside
                className="min-h-0 min-w-0 overflow-hidden"
                data-pos-shell-region="right"
              >
                {resolvedRightPanel}
              </aside>
            ) : null}
          </div>
        </div>
      </AppShellRightPanelContext.Provider>

      {!isInlineSidebar && isSidebarDrawerOpen ? (
        <div className="fixed inset-0 z-40 flex" role="presentation">
          <button
            aria-label="Cerrar navegacion"
            className="flex-1 bg-slate-950/35"
            onClick={() => {
              setIsSidebarDrawerOpen(false);
              setIsSidebarKeyboardNavigationEnabled(false);
            }}
            type="button"
          />
          <aside
            className="pos-shell-panel relative z-10 h-full w-[min(20rem,88vw)] rounded-none rounded-l-[var(--pos-radius-panel)] p-2.5 shadow-[var(--ui-shadow-overlay)]"
            data-pos-shell-region="sidebar"
            data-pos-shell-sidebar-mode="drawer"
          >
            {sidebarNavigation}
          </aside>
        </div>
      ) : null}

      {!isInlineRightPanel && isRightPanelDrawerOpen ? (
        <div className="fixed inset-0 z-40 flex justify-end" role="presentation">
          <button
            aria-label="Cerrar resumen operativo"
            className="flex-1 bg-slate-950/35"
            onClick={() => setIsRightPanelDrawerOpen(false)}
            type="button"
          />
          <aside className="relative z-10 h-full min-w-0 w-[min(20rem,92vw)] overflow-hidden bg-[var(--pos-shell-bg)] p-[var(--pos-shell-workstation-padding)] shadow-[var(--ui-shadow-overlay)]">
            {resolvedRightPanel}
          </aside>
        </div>
      ) : null}

      <CommandPalette
        actions={commandActions}
        isOpen={isCommandPaletteOpen}
        onClose={() => setIsCommandPaletteOpen(false)}
      />
      <KeyboardHelpOverlay />
    </div>
  );
}

export function AppShell(props: AppShellProps) {
  return (
    <KeyboardShortcutRegistry>
      <AppShellFrame {...props} />
    </KeyboardShortcutRegistry>
  );
}
