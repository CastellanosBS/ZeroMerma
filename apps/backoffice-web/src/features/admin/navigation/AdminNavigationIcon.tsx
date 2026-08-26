import type { ReactNode } from "react";

export type AdminNavigationIconName =
  | "alertTriangle"
  | "arrows"
  | "beaker"
  | "boxes"
  | "building"
  | "calculator"
  | "chartBar"
  | "chefHat"
  | "clipboardCheck"
  | "clipboardList"
  | "fileSearch"
  | "home"
  | "layers"
  | "lock"
  | "menu"
  | "monitor"
  | "package"
  | "percent"
  | "receipt"
  | "scale"
  | "settings"
  | "shieldCheck"
  | "shoppingCart"
  | "tag"
  | "trash"
  | "trendingUp"
  | "truck"
  | "users"
  | "wallet"
  | "wrench";

const iconPaths: Record<AdminNavigationIconName, ReactNode> = {
  alertTriangle: (
    <>
      <path d="M10.3 3.2 2.2 17.1a1.7 1.7 0 0 0 1.5 2.6h16.6a1.7 1.7 0 0 0 1.5-2.6L13.7 3.2a2 2 0 0 0-3.4 0Z" />
      <path d="M12 8v5" />
      <path d="M12 17h.01" />
    </>
  ),
  arrows: (
    <>
      <path d="M7 7h12" />
      <path d="m15 3 4 4-4 4" />
      <path d="M17 17H5" />
      <path d="m9 13-4 4 4 4" />
    </>
  ),
  beaker: (
    <>
      <path d="M9 3h6" />
      <path d="M10 3v5.4L5.6 17a2.4 2.4 0 0 0 2.1 3.5h8.6a2.4 2.4 0 0 0 2.1-3.5L14 8.4V3" />
      <path d="M7.2 15h9.6" />
    </>
  ),
  boxes: (
    <>
      <path d="M3 7.5 8 5l5 2.5v6L8 16l-5-2.5Z" />
      <path d="M13 7.5 18 5l3 1.5v6L16 15l-3-1.5" />
      <path d="M8 16v5l5-2.5v-5" />
      <path d="M8 10.5 3 8" />
      <path d="m18 5 3 1.5" />
    </>
  ),
  building: (
    <>
      <path d="M4 21V5a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v16" />
      <path d="M17 9h1a2 2 0 0 1 2 2v10" />
      <path d="M8 7h1" />
      <path d="M12 7h1" />
      <path d="M8 11h1" />
      <path d="M12 11h1" />
      <path d="M8 15h1" />
      <path d="M12 15h1" />
      <path d="M3 21h18" />
    </>
  ),
  calculator: (
    <>
      <rect x="5" y="3" width="14" height="18" rx="2" />
      <path d="M8 7h8" />
      <path d="M8 11h.01" />
      <path d="M12 11h.01" />
      <path d="M16 11h.01" />
      <path d="M8 15h.01" />
      <path d="M12 15h.01" />
      <path d="M16 15h.01" />
    </>
  ),
  chartBar: (
    <>
      <path d="M4 19h16" />
      <path d="M7 16V9" />
      <path d="M12 16V5" />
      <path d="M17 16v-4" />
    </>
  ),
  chefHat: (
    <>
      <path d="M6.5 12.5a4 4 0 0 1 .7-7.9A5 5 0 0 1 17 4.9a4 4 0 0 1 .5 7.6" />
      <path d="M7 12h10v7H7z" />
      <path d="M9 16h6" />
    </>
  ),
  clipboardCheck: (
    <>
      <path d="M9 4h6" />
      <path d="M9 4a3 3 0 0 0 6 0" />
      <path d="M8 5H6a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2h-2" />
      <path d="m9 14 2 2 4-5" />
    </>
  ),
  clipboardList: (
    <>
      <path d="M9 4h6" />
      <path d="M9 4a3 3 0 0 0 6 0" />
      <path d="M8 5H6a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2h-2" />
      <path d="M8 12h.01" />
      <path d="M11 12h5" />
      <path d="M8 16h.01" />
      <path d="M11 16h5" />
    </>
  ),
  fileSearch: (
    <>
      <path d="M14 3v5h5" />
      <path d="M19 10V5.5L16.5 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h5" />
      <circle cx="15.5" cy="15.5" r="2.5" />
      <path d="m17.4 17.4 2.1 2.1" />
    </>
  ),
  home: (
    <>
      <path d="m3 11 9-8 9 8" />
      <path d="M5 10v10h14V10" />
      <path d="M10 20v-6h4v6" />
    </>
  ),
  layers: (
    <>
      <path d="m12 3 9 5-9 5-9-5Z" />
      <path d="m3 12 9 5 9-5" />
      <path d="m3 16 9 5 9-5" />
    </>
  ),
  lock: (
    <>
      <rect x="5" y="10" width="14" height="11" rx="2" />
      <path d="M8 10V7a4 4 0 0 1 8 0v3" />
    </>
  ),
  menu: (
    <>
      <path d="M4 7h16" />
      <path d="M4 12h16" />
      <path d="M4 17h16" />
    </>
  ),
  monitor: (
    <>
      <rect x="3" y="4" width="18" height="12" rx="2" />
      <path d="M8 21h8" />
      <path d="M12 16v5" />
    </>
  ),
  package: (
    <>
      <path d="m12 3 8 4.5v9L12 21l-8-4.5v-9Z" />
      <path d="m4.5 7.8 7.5 4.3 7.5-4.3" />
      <path d="M12 12v9" />
    </>
  ),
  percent: (
    <>
      <path d="m19 5-14 14" />
      <circle cx="7" cy="7" r="2" />
      <circle cx="17" cy="17" r="2" />
    </>
  ),
  receipt: (
    <>
      <path d="M6 3h12v18l-2-1-2 1-2-1-2 1-2-1-2 1Z" />
      <path d="M9 8h6" />
      <path d="M9 12h6" />
      <path d="M9 16h4" />
    </>
  ),
  scale: (
    <>
      <path d="M12 3v18" />
      <path d="M5 6h14" />
      <path d="m6 6-3 7h6Z" />
      <path d="m18 6-3 7h6Z" />
    </>
  ),
  settings: (
    <>
      <path d="M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8Z" />
      <path d="M4 12h2" />
      <path d="M18 12h2" />
      <path d="m6.3 6.3 1.4 1.4" />
      <path d="m16.3 16.3 1.4 1.4" />
      <path d="m17.7 6.3-1.4 1.4" />
      <path d="m7.7 16.3-1.4 1.4" />
      <path d="M12 2v2" />
      <path d="M12 20v2" />
    </>
  ),
  shieldCheck: (
    <>
      <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10Z" />
      <path d="m9 12 2 2 4-5" />
    </>
  ),
  shoppingCart: (
    <>
      <path d="M3 4h2l2.2 10.5a2 2 0 0 0 2 1.5h7.8a2 2 0 0 0 2-1.6L20 8H6" />
      <circle cx="10" cy="20" r="1" />
      <circle cx="17" cy="20" r="1" />
    </>
  ),
  tag: (
    <>
      <path d="M20 13 13 20 4 11V4h7Z" />
      <path d="M7.5 7.5h.01" />
    </>
  ),
  trash: (
    <>
      <path d="M4 7h16" />
      <path d="M10 11v6" />
      <path d="M14 11v6" />
      <path d="M6 7l1 14h10l1-14" />
      <path d="M9 7V4h6v3" />
    </>
  ),
  trendingUp: (
    <>
      <path d="m3 17 6-6 4 4 7-8" />
      <path d="M14 7h6v6" />
    </>
  ),
  truck: (
    <>
      <path d="M3 6h11v10H3Z" />
      <path d="M14 9h4l3 3v4h-7Z" />
      <circle cx="7" cy="18" r="2" />
      <circle cx="17" cy="18" r="2" />
    </>
  ),
  users: (
    <>
      <path d="M16 21v-2a4 4 0 0 0-4-4H7a4 4 0 0 0-4 4v2" />
      <circle cx="9.5" cy="7" r="4" />
      <path d="M22 21v-2a4 4 0 0 0-3-3.8" />
      <path d="M16 3.2a4 4 0 0 1 0 7.6" />
    </>
  ),
  wallet: (
    <>
      <path d="M4 7h15a2 2 0 0 1 2 2v10H5a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h12" />
      <path d="M16 13h5" />
      <path d="M18 13h.01" />
    </>
  ),
  wrench: (
    <>
      <path d="M14.7 6.3a4 4 0 0 0-5.1 5.1L3.5 17.5 6.5 20.5l6.1-6.1a4 4 0 0 0 5.1-5.1l-2.6 2.6-3-3Z" />
    </>
  ),
};

interface AdminNavigationIconProps {
  className?: string;
  name: AdminNavigationIconName;
}

export function AdminNavigationIcon({ className, name }: AdminNavigationIconProps) {
  return (
    <svg
      aria-hidden="true"
      className={className}
      fill="none"
      stroke="currentColor"
      strokeLinecap="round"
      strokeLinejoin="round"
      strokeWidth="2"
      viewBox="0 0 24 24"
    >
      {iconPaths[name]}
    </svg>
  );
}
