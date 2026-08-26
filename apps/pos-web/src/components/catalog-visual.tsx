import { cn } from "../lib/utils";

function getCatalogMonogram(code: string, name: string): string {
  const normalizedName = name.trim();
  const nameTokens = normalizedName
    .split(/\s+/)
    .map((token) => token[0]?.toUpperCase() ?? "")
    .filter(Boolean);

  if (nameTokens.length >= 2) {
    return `${nameTokens[0]}${nameTokens[1]}`;
  }

  if (nameTokens.length === 1) {
    const fallbackCode = code.replace(/[^A-Za-z0-9]/g, "").toUpperCase();
    return `${nameTokens[0]}${fallbackCode[0] ?? nameTokens[0]}`.slice(0, 2);
  }

  const sanitizedCode = code.replace(/[^A-Za-z0-9]/g, "").toUpperCase();
  return sanitizedCode.slice(0, 2) || "IT";
}

function getCatalogCodeLabel(code: string): string {
  const normalizedCode = code.trim().toUpperCase();
  return normalizedCode.length > 0 ? normalizedCode : "CATALOGO";
}

export function CatalogVisual({
  className,
  code,
  name,
}: {
  className?: string;
  code: string;
  name: string;
}) {
  const monogram = getCatalogMonogram(code, name);
  const codeLabel = getCatalogCodeLabel(code);

  return (
    <div
      className={cn(
        "relative overflow-hidden rounded-[1.1rem] border border-[var(--pos-shell-border)] bg-[linear-gradient(180deg,#FFFFFF_0%,#F9FBFD_100%)]",
        className,
      )}
    >
      <div
        aria-hidden="true"
        className="absolute inset-0 opacity-90"
        style={{
          backgroundImage:
            "linear-gradient(135deg, rgba(31,75,110,0.06) 0%, rgba(31,75,110,0) 38%), radial-gradient(circle at 88% 16%, rgba(197,164,106,0.18) 0%, rgba(197,164,106,0) 32%)",
        }}
      />
      <div
        aria-hidden="true"
        className="absolute inset-x-0 bottom-0 h-16"
        style={{
          backgroundImage:
            "linear-gradient(180deg, rgba(255,255,255,0) 0%, rgba(15,23,42,0.04) 100%)",
        }}
      />
      <div className="relative flex h-full flex-col justify-between p-3.5">
        <span className="pos-chip max-w-full self-start border-white/80 bg-white/88 text-slate-500 shadow-sm">
          <span className="truncate">{codeLabel}</span>
        </span>

        <div className="flex items-end justify-between gap-3">
          <div className="grid h-16 w-16 shrink-0 place-items-center rounded-[1.25rem] border border-[var(--pos-shell-border)] bg-white/92 text-2xl font-semibold tracking-tight text-[var(--pos-primary)] shadow-sm">
            {monogram}
          </div>
        </div>
      </div>
    </div>
  );
}
