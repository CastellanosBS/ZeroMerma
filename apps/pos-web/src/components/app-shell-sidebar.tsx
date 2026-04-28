import { type ComponentType, type SVGProps } from "react";

import {
  type PosModuleDefinition,
  type PosModuleKey,
} from "../features/pos-shell/modules";
import { cn } from "../lib/utils";

interface AppShellSidebarProps {
  activeModuleKey: PosModuleKey;
  collapsed: boolean;
  hasCashSession: boolean;
  isKeyboardNavigationEnabled: boolean;
  modules: PosModuleDefinition[];
  onNavigate: (path: string) => void;
  onNavigationModeChange: (isEnabled: boolean) => void;
}

function SidebarModuleIcon({
  icon: Icon,
  isActive,
}: {
  icon: ComponentType<SVGProps<SVGSVGElement>>;
  isActive: boolean;
}) {
  return (
    <Icon
      className={cn(
        "h-[var(--pos-sidebar-icon-size)] w-[var(--pos-sidebar-icon-size)] shrink-0 transition",
        isActive ? "text-[var(--pos-active-item-fg)]" : "text-slate-500 group-hover:text-slate-900",
      )}
    />
  );
}

export function AppShellSidebar({
  activeModuleKey,
  collapsed,
  hasCashSession,
  isKeyboardNavigationEnabled,
  modules,
  onNavigate,
  onNavigationModeChange,
}: AppShellSidebarProps) {
  return (
    <div className="grid h-full min-h-0 grid-rows-[auto_minmax(0,1fr)] gap-2">
      {!collapsed ? (
        <div className="border-b border-[var(--pos-shell-border)] px-2 pb-2 pt-1">
          <p className="pos-label-text">Modulos</p>
        </div>
      ) : null}

      <nav
        aria-label="Modulos del POS"
        className="pos-shell-nav-list"
        data-pos-shell-navigation="true"
        onBlurCapture={(event) => {
          const nextTarget = event.relatedTarget as Node | null;
          if (!nextTarget || !event.currentTarget.contains(nextTarget)) {
            onNavigationModeChange(false);
          }
        }}
        onFocusCapture={() => onNavigationModeChange(true)}
        onPointerDownCapture={() => onNavigationModeChange(true)}
      >
        {modules.map((module) => {
          const isActive = activeModuleKey === module.key;
          const isDisabled = !hasCashSession && module.key !== "pos" && !isActive;
          const tabIndex = isDisabled ? -1 : isKeyboardNavigationEnabled ? 0 : -1;

          return (
            <button
              aria-current={isActive ? "page" : undefined}
              aria-disabled={isDisabled || undefined}
              aria-label={
                collapsed
                  ? `${module.label}${module.navigationShortcut ? ` · ${module.navigationShortcut}` : ""}`
                  : undefined
              }
              className="pos-shell-nav-item group"
              data-collapsed={collapsed || undefined}
              data-pos-shell-nav-item="true"
              data-state={isDisabled ? "disabled" : isActive ? "active" : "idle"}
              disabled={isDisabled}
              key={module.key}
              onClick={() => onNavigate(module.path)}
              tabIndex={tabIndex}
              title={
                collapsed
                  ? `${module.label}${module.navigationShortcut ? ` · ${module.navigationShortcut}` : ""}`
                  : module.label
              }
              type="button"
            >
              <span className="pos-shell-nav-item__content">
                <SidebarModuleIcon icon={module.icon} isActive={isActive} />
                {!collapsed ? (
                  <span className="pos-shell-nav-item__label">{module.label}</span>
                ) : null}
                {collapsed ? (
                  <span className="pos-shell-nav-item__tooltip" role="tooltip">
                    <span>{module.label}</span>
                    {module.navigationShortcut ? (
                      <span className="pos-kbd-chip shrink-0 whitespace-nowrap">
                        {module.navigationShortcut}
                      </span>
                    ) : null}
                  </span>
                ) : null}
              </span>
            </button>
          );
        })}
      </nav>
    </div>
  );
}
