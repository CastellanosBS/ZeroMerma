import type { SVGProps } from "react";

type IconProps = SVGProps<SVGSVGElement>;

function BaseIcon(props: IconProps) {
  return (
    <svg
      aria-hidden="true"
      fill="none"
      height="20"
      stroke="currentColor"
      strokeLinecap="round"
      strokeLinejoin="round"
      strokeWidth="1.8"
      viewBox="0 0 24 24"
      width="20"
      {...props}
    />
  );
}

export function ArrowLeftIcon(props: IconProps) {
  return (
    <BaseIcon {...props}>
      <path d="M19 12H5" />
      <path d="m12 19-7-7 7-7" />
    </BaseIcon>
  );
}

export function BagIcon(props: IconProps) {
  return (
    <BaseIcon {...props}>
      <path d="M6 9h12l-1 11H7L6 9Z" />
      <path d="M9 9V7a3 3 0 0 1 6 0v2" />
    </BaseIcon>
  );
}

export function AlertTriangleIcon(props: IconProps) {
  return (
    <BaseIcon {...props}>
      <path d="M12 3 2 20h20L12 3Z" />
      <path d="M12 9v4" />
      <path d="M12 17h.01" />
    </BaseIcon>
  );
}

export function CheckCircleIcon(props: IconProps) {
  return (
    <BaseIcon {...props}>
      <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
      <path d="m9 11 3 3L22 4" />
    </BaseIcon>
  );
}

export function ClockIcon(props: IconProps) {
  return (
    <BaseIcon {...props}>
      <circle cx="12" cy="12" r="9" />
      <path d="M12 7v5l3 2" />
    </BaseIcon>
  );
}

export function ChevronRightIcon(props: IconProps) {
  return (
    <BaseIcon {...props}>
      <path d="m9 6 6 6-6 6" />
    </BaseIcon>
  );
}

export function CardIcon(props: IconProps) {
  return (
    <BaseIcon {...props}>
      <rect height="14" rx="2" width="18" x="3" y="5" />
      <path d="M3 10h18" />
      <path d="M7 15h3" />
    </BaseIcon>
  );
}

export function ClipboardIcon(props: IconProps) {
  return (
    <BaseIcon {...props}>
      <path d="M9 4h6" />
      <path d="M10 3h4a1 1 0 0 1 1 1v1H9V4a1 1 0 0 1 1-1Z" />
      <rect height="17" rx="2" width="14" x="5" y="4" />
      <path d="M9 10h6" />
      <path d="M9 14h6" />
    </BaseIcon>
  );
}

export function DownloadIcon(props: IconProps) {
  return (
    <BaseIcon {...props}>
      <path d="M12 4v10" />
      <path d="m8 10 4 4 4-4" />
      <path d="M4 19h16" />
    </BaseIcon>
  );
}

export function HealthIcon(props: IconProps) {
  return (
    <BaseIcon {...props}>
      <path d="M3 12h4l2-5 4 10 2-5h6" />
    </BaseIcon>
  );
}

export function LogoutIcon(props: IconProps) {
  return (
    <BaseIcon {...props}>
      <path d="M14 8V5a2 2 0 0 0-2-2H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h6a2 2 0 0 0 2-2v-3" />
      <path d="M9 12h12" />
      <path d="m16 7 5 5-5 5" />
    </BaseIcon>
  );
}

export function MenuIcon(props: IconProps) {
  return (
    <BaseIcon {...props}>
      <path d="M4 7h16" />
      <path d="M4 12h16" />
      <path d="M4 17h16" />
    </BaseIcon>
  );
}

export function MinusIcon(props: IconProps) {
  return (
    <BaseIcon {...props}>
      <path d="M5 12h14" />
    </BaseIcon>
  );
}

export function MoneyIcon(props: IconProps) {
  return (
    <BaseIcon {...props}>
      <rect height="12" rx="2" width="18" x="3" y="6" />
      <circle cx="12" cy="12" r="2.5" />
      <path d="M7 10h.01" />
      <path d="M17 14h.01" />
    </BaseIcon>
  );
}

export function HashIcon(props: IconProps) {
  return (
    <BaseIcon {...props}>
      <path d="M9 4 7 20" />
      <path d="M17 4 15 20" />
      <path d="M4 9h16" />
      <path d="M3 15h16" />
    </BaseIcon>
  );
}

export function InboxIcon(props: IconProps) {
  return (
    <BaseIcon {...props}>
      <path d="M4 6h16l1 10a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2L4 6Z" />
      <path d="M4 12h4l2 3h4l2-3h5" />
    </BaseIcon>
  );
}

export function PackageIcon(props: IconProps) {
  return (
    <BaseIcon {...props}>
      <path d="m12 3 8 4.5v9L12 21l-8-4.5v-9L12 3Z" />
      <path d="m12 12 8-4.5" />
      <path d="M12 12 4 7.5" />
      <path d="M12 21v-9" />
    </BaseIcon>
  );
}

export function SplitIcon(props: IconProps) {
  return (
    <BaseIcon {...props}>
      <path d="M12 4v16" />
      <path d="M12 8h6" />
      <path d="m18 8-2-2" />
      <path d="m18 8-2 2" />
      <path d="M12 16H6" />
      <path d="m6 16 2-2" />
      <path d="m6 16 2 2" />
    </BaseIcon>
  );
}

export function OperatorIcon(props: IconProps) {
  return (
    <BaseIcon {...props}>
      <path d="M20 21a8 8 0 0 0-16 0" />
      <circle cx="12" cy="8" r="4" />
    </BaseIcon>
  );
}

export function PlusIcon(props: IconProps) {
  return (
    <BaseIcon {...props}>
      <path d="M12 5v14" />
      <path d="M5 12h14" />
    </BaseIcon>
  );
}

export function PercentIcon(props: IconProps) {
  return (
    <BaseIcon {...props}>
      <path d="m19 5-14 14" />
      <circle cx="7" cy="7" r="2" />
      <circle cx="17" cy="17" r="2" />
    </BaseIcon>
  );
}

export function PencilSquareIcon(props: IconProps) {
  return (
    <BaseIcon {...props}>
      <path d="M4 5a2 2 0 0 1 2-2h8" />
      <path d="M4 9v9a2 2 0 0 0 2 2h9" />
      <path d="m14 5 5 5" />
      <path d="m12 17 1.5-5.5L19 6l-5-5-5.5 5.5L3 18l9-1Z" />
    </BaseIcon>
  );
}

export function PrinterIcon(props: IconProps) {
  return (
    <BaseIcon {...props}>
      <path d="M7 9V4h10v5" />
      <rect height="8" rx="1.5" width="10" x="7" y="12" />
      <path d="M6 17H5a2 2 0 0 1-2-2v-4a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2v4a2 2 0 0 1-2 2h-1" />
      <path d="M17 16h.01" />
    </BaseIcon>
  );
}

export function SearchIcon(props: IconProps) {
  return (
    <BaseIcon {...props}>
      <circle cx="11" cy="11" r="7" />
      <path d="m20 20-3.5-3.5" />
    </BaseIcon>
  );
}

export function ReceiptIcon(props: IconProps) {
  return (
    <BaseIcon {...props}>
      <path d="M7 3h10v18l-2-1-2 1-2-1-2 1-2-1-2 1V5a2 2 0 0 1 2-2Z" />
      <path d="M9 8h6" />
      <path d="M9 12h6" />
      <path d="M9 16h4" />
    </BaseIcon>
  );
}

export function RotateCcwIcon(props: IconProps) {
  return (
    <BaseIcon {...props}>
      <path d="M3 12a9 9 0 1 0 3-6.7" />
      <path d="M3 4v5h5" />
    </BaseIcon>
  );
}

export function StationIcon(props: IconProps) {
  return (
    <BaseIcon {...props}>
      <rect height="12" rx="2" width="16" x="4" y="4" />
      <path d="M8 20h8" />
      <path d="M12 16v4" />
    </BaseIcon>
  );
}

export function StoreIcon(props: IconProps) {
  return (
    <BaseIcon {...props}>
      <path d="M4 10h16" />
      <path d="M6 10v10h12V10" />
      <path d="m3 10 2-5h14l2 5" />
    </BaseIcon>
  );
}

export function TruckIcon(props: IconProps) {
  return (
    <BaseIcon {...props}>
      <path d="M3 7h11v8H3z" />
      <path d="M14 10h4l3 3v2h-7z" />
      <circle cx="8" cy="18" r="2" />
      <circle cx="18" cy="18" r="2" />
    </BaseIcon>
  );
}

export function TrashIcon(props: IconProps) {
  return (
    <BaseIcon {...props}>
      <path d="M3 6h18" />
      <path d="M8 6V4h8v2" />
      <path d="M19 6l-1 14H6L5 6" />
      <path d="M10 10v6" />
      <path d="M14 10v6" />
    </BaseIcon>
  );
}

export function XIcon(props: IconProps) {
  return (
    <BaseIcon {...props}>
      <path d="m18 6-12 12" />
      <path d="m6 6 12 12" />
    </BaseIcon>
  );
}
