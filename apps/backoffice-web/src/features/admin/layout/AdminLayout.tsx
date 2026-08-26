import { useQuery } from "@tanstack/react-query";
import { Link, Outlet, useRouterState } from "@tanstack/react-router";
import { useEffect, useState } from "react";

import { getCurrentBackofficeUser } from "../../../lib/api";
import { useBackofficeAuthStore } from "../../auth/backoffice-auth-store";
import { AdminNavigationIcon } from "../navigation/AdminNavigationIcon";
import {
  type AdminNavigationItem,
  type AdminNavigationSection,
  adminNavigationSections,
  getAdminNavigationItem,
} from "../navigation/adminNavigation";
import {
  getInitialAdminSidebarCollapsed,
  persistAdminSidebarCollapsed,
} from "./adminSidebarPreferences";

function isNavigationItemActive(pathname: string, item: AdminNavigationItem) {
  return pathname === item.path || pathname.startsWith(`${item.path}/`);
}

function isNavigationSectionActive(pathname: string, section: AdminNavigationSection) {
  return section.items.some((item) => isNavigationItemActive(pathname, item));
}

function CollapsedTooltip({ children }: { children: string }) {
  return (
    <span className="pointer-events-none absolute left-full top-1/2 z-50 ml-3 max-w-[18rem] -translate-y-1/2 whitespace-nowrap rounded-xl border border-[var(--ui-color-border)] bg-slate-950 px-3 py-2 text-xs font-semibold text-white opacity-0 shadow-lg transition group-hover/nav:opacity-100 group-focus-visible/nav:opacity-100">
      {children}
    </span>
  );
}

function SidebarItemLink({ item, pathname }: { item: AdminNavigationItem; pathname: string }) {
  const isActive = isNavigationItemActive(pathname, item);

  return (
    <Link
      aria-current={isActive ? "page" : undefined}
      className={[
        "group/item relative flex min-w-0 items-center rounded-xl px-3 py-2 text-sm font-semibold transition focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]",
        isActive
          ? "bg-[var(--ui-color-surface-tint)] text-[var(--ui-color-info)]"
          : "text-slate-700 hover:bg-slate-50 hover:text-slate-950",
      ].join(" ")}
      key={item.path}
      title={item.label}
      to={item.path as never}
    >
      <span
        className={[
          "absolute left-0 top-1/2 h-5 w-1 -translate-y-1/2 rounded-r-full transition",
          isActive ? "bg-[var(--ui-color-info)]" : "bg-transparent group-hover/item:bg-slate-300",
        ].join(" ")}
      />
      <span className="block min-w-0 flex-1 truncate pl-1">{item.label}</span>
    </Link>
  );
}

function CollapsedSidebarSection({
  onOpenSection,
  section,
  pathname,
}: {
  onOpenSection: (sectionTitle: string) => void;
  pathname: string;
  section: AdminNavigationSection;
}) {
  const isActive = isNavigationSectionActive(pathname, section);

  return (
    <div className="border-b border-[var(--ui-color-border)] pb-2 last:border-b-0">
      <button
        aria-label={section.title}
        className={[
          "group/nav relative mx-auto mb-1 flex h-10 w-10 items-center justify-center rounded-2xl border transition focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]",
          isActive
            ? "border-[var(--ui-color-info)] bg-[var(--ui-color-surface-tint)] text-[var(--ui-color-info)]"
            : "border-transparent text-slate-500 hover:border-[var(--ui-color-border)] hover:bg-slate-50 hover:text-slate-950",
        ].join(" ")}
        title={section.title}
        type="button"
        onClick={() => onOpenSection(section.title)}
      >
        <span
          className={[
            "absolute left-0 top-1/2 h-5 w-1 -translate-y-1/2 rounded-r-full transition",
            isActive ? "bg-[var(--ui-color-info)]" : "bg-transparent",
          ].join(" ")}
        />
        <AdminNavigationIcon className="h-[1.125rem] w-[1.125rem]" name={section.icon} />
        <CollapsedTooltip>{section.title}</CollapsedTooltip>
      </button>
    </div>
  );
}

export function AdminLayout() {
  const pathname = useRouterState({ select: (state) => state.location.pathname });
  const activeItem = getAdminNavigationItem(pathname);
  const accessToken = useBackofficeAuthStore((state) => state.accessToken);
  const clearSession = useBackofficeAuthStore((state) => state.clearSession);
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(getInitialAdminSidebarCollapsed);
  const [openSections, setOpenSections] = useState<Set<string>>(() => new Set());
  const currentUserQuery = useQuery({
    enabled: Boolean(accessToken),
    queryFn: () => getCurrentBackofficeUser(accessToken ?? ""),
    queryKey: ["backoffice-auth", "me", accessToken],
    retry: false,
  });

  useEffect(() => {
    if (currentUserQuery.isError) {
      clearSession();
    }
  }, [clearSession, currentUserQuery.isError]);

  useEffect(() => {
    persistAdminSidebarCollapsed(isSidebarCollapsed);
  }, [isSidebarCollapsed]);

  function toggleSidebar() {
    setOpenSections(new Set());
    setIsSidebarCollapsed((current) => !current);
  }

  function openCollapsedSection(sectionTitle: string) {
    setOpenSections(new Set([sectionTitle]));
    setIsSidebarCollapsed(false);
  }

  function toggleExpandedSection(sectionTitle: string) {
    setOpenSections((current) => (current.has(sectionTitle) ? new Set() : new Set([sectionTitle])));
  }

  // TODO: Enforce granular admin permissions once the backend exposes module/action/scope grants.
  return (
    <div className="min-h-screen min-w-0 bg-slate-50 text-slate-950">
      <header className="sticky top-0 z-30 border-b border-[var(--ui-color-border)] bg-white/95 shadow-[var(--ui-shadow-subtle)] backdrop-blur">
        <div className="mx-auto flex min-w-0 max-w-[1680px] flex-wrap items-center justify-between gap-3 px-4 py-3">
          <div className="flex min-w-0 items-center gap-3">
            <button
              aria-expanded={!isSidebarCollapsed}
              aria-label="Toggle admin sidebar"
              className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl border border-[var(--ui-color-border)] bg-white text-slate-700 transition hover:border-[var(--ui-color-info)] hover:bg-slate-50 focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
              title={isSidebarCollapsed ? "Expandir navegación" : "Contraer navegación"}
              type="button"
              onClick={toggleSidebar}
            >
              <AdminNavigationIcon className="h-5 w-5" name="menu" />
            </button>
            <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-[var(--ui-color-primary)] text-sm font-semibold text-white">
              ZM
            </div>
            <div className="min-w-0">
              <div className="flex flex-wrap items-center gap-2">
                <h1 className="truncate text-lg font-semibold text-slate-950">
                  Administración ZeroMerma
                </h1>
                <span
                  className="max-w-[14rem] truncate rounded-full border border-[var(--ui-color-border)] bg-[var(--ui-color-surface-tint)] px-3 py-1 text-xs font-semibold text-[var(--ui-color-info)]"
                  title={activeItem.label}
                >
                  {activeItem.label}
                </span>
              </div>
              <p className="truncate text-sm text-slate-600">Centro de mando multisucursal</p>
            </div>
          </div>

          <div className="flex min-w-0 flex-wrap items-center justify-end gap-2 text-sm">
            <span
              className="max-w-[16rem] truncate rounded-full border border-[var(--ui-color-border)] bg-white px-3 py-2 font-medium text-slate-700"
              title={currentUserQuery.data?.full_name ?? "Usuario administrativo"}
            >
              {currentUserQuery.data?.full_name ?? "Usuario administrativo"}
            </span>
            <span className="rounded-full border border-[var(--ui-color-financial-border)] bg-[var(--ui-color-financial-soft)] px-3 py-2 font-medium text-[var(--ui-color-warning)]">
              Entorno local
            </span>
            <button
              className="rounded-full border border-[var(--ui-color-border)] bg-white px-3 py-2 font-semibold text-slate-700 transition hover:bg-slate-50 focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
              onClick={clearSession}
              type="button"
            >
              Salir
            </button>
          </div>
        </div>
      </header>

      <div
        className={[
          "mx-auto grid min-h-0 max-w-[1680px] gap-3 px-4 py-3 transition-[grid-template-columns] duration-200 lg:h-[calc(100vh-4.75rem)] lg:overflow-hidden",
          isSidebarCollapsed
            ? "lg:grid-cols-[4.5rem_minmax(0,1fr)]"
            : "lg:grid-cols-[17.5rem_minmax(0,1fr)]",
        ].join(" ")}
      >
        <aside className="min-w-0 overflow-visible rounded-[24px] border border-[var(--ui-color-border)] bg-white shadow-[var(--ui-shadow-subtle)] transition-[width] duration-200 lg:h-full">
          <div
            className={[
              "border-b border-[var(--ui-color-border)]",
              isSidebarCollapsed
                ? "flex h-[4.55rem] items-center justify-center px-2"
                : "px-4 py-3",
            ].join(" ")}
          >
            {isSidebarCollapsed ? (
              <>
                <span className="sr-only">Administración</span>
                <span className="flex h-10 w-10 items-center justify-center rounded-2xl bg-[var(--ui-color-surface-tint)] text-[var(--ui-color-info)]">
                  <AdminNavigationIcon className="h-5 w-5" name="settings" />
                </span>
              </>
            ) : (
              <p className="text-sm font-semibold text-slate-950">Administración</p>
            )}
          </div>

          <nav
            aria-label="Navegación administrativa"
            className="h-[calc(100%-4.55rem)] space-y-2 overflow-y-auto overflow-x-visible p-2"
          >
            {isSidebarCollapsed
              ? adminNavigationSections.map((section) => (
                  <CollapsedSidebarSection
                    key={section.title}
                    onOpenSection={openCollapsedSection}
                    pathname={pathname}
                    section={section}
                  />
                ))
              : adminNavigationSections.map((section) => {
                  const isOpen = openSections.has(section.title);
                  const isActive = isNavigationSectionActive(pathname, section);

                  return (
                    <section
                      className={[
                        "rounded-2xl border transition",
                        isOpen
                          ? "border-[var(--ui-color-border)] bg-slate-50/70"
                          : "border-transparent",
                      ].join(" ")}
                      key={section.title}
                    >
                      <button
                        aria-expanded={isOpen}
                        className={[
                          "flex w-full cursor-pointer items-center justify-between rounded-xl px-2 py-2 text-[0.68rem] font-semibold uppercase tracking-[0.14em] transition focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]",
                          isActive
                            ? "text-[var(--ui-color-info)]"
                            : "text-slate-500 hover:bg-slate-50",
                        ].join(" ")}
                        title={section.title}
                        type="button"
                        onClick={() => toggleExpandedSection(section.title)}
                      >
                        <span className="flex min-w-0 items-center gap-2">
                          <span
                            className={[
                              "flex h-8 w-8 shrink-0 items-center justify-center rounded-xl border bg-white",
                              isActive
                                ? "border-[var(--ui-color-info)] text-[var(--ui-color-info)]"
                                : "border-[var(--ui-color-border)] text-slate-500",
                            ].join(" ")}
                          >
                            <AdminNavigationIcon className="h-4 w-4" name={section.icon} />
                          </span>
                          <span className="block min-w-0 truncate">{section.title}</span>
                        </span>
                        <span className="ml-2 rounded-full bg-slate-100 px-2 py-0.5 text-[0.62rem] tracking-normal text-slate-500">
                          {section.items.length}
                        </span>
                      </button>
                      {isOpen ? (
                        <div className="grid gap-0.5 px-1 pb-2">
                          {section.items.map((item) => (
                            <SidebarItemLink item={item} key={item.path} pathname={pathname} />
                          ))}
                        </div>
                      ) : null}
                    </section>
                  );
                })}
          </nav>
        </aside>

        <main className="min-h-0 min-w-0 lg:overflow-hidden">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
