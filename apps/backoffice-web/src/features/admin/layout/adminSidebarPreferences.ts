export const ADMIN_SIDEBAR_COLLAPSED_STORAGE_KEY = "zeromerma.admin.sidebar.collapsed";

type SidebarPreferenceStorage = Pick<Storage, "getItem" | "setItem">;

function getSidebarPreferenceStorage(): SidebarPreferenceStorage | null {
  if (typeof window === "undefined") {
    return null;
  }

  return window.localStorage;
}

export function getInitialAdminSidebarCollapsed(storage = getSidebarPreferenceStorage()) {
  if (!storage) {
    return true;
  }

  return storage.getItem(ADMIN_SIDEBAR_COLLAPSED_STORAGE_KEY) !== "false";
}

export function persistAdminSidebarCollapsed(
  isCollapsed: boolean,
  storage = getSidebarPreferenceStorage(),
) {
  storage?.setItem(ADMIN_SIDEBAR_COLLAPSED_STORAGE_KEY, String(isCollapsed));
}
