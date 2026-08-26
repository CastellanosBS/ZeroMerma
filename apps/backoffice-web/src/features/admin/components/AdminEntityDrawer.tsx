import { useEffect, useRef, type ReactNode } from "react";

interface AdminEntityDrawerProps {
  children: ReactNode;
  description?: string;
  isOpen: boolean;
  onClose: () => void;
  title: string;
}

export function AdminEntityDrawer({
  children,
  description,
  isOpen,
  onClose,
  title,
}: AdminEntityDrawerProps) {
  const closeButtonRef = useRef<HTMLButtonElement | null>(null);

  useEffect(() => {
    if (!isOpen) {
      return undefined;
    }

    closeButtonRef.current?.focus();

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        onClose();
      }
    }

    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) {
    return null;
  }

  return (
    <div className="fixed inset-0 z-50" role="presentation">
      <button
        aria-label="Cerrar panel"
        className="absolute inset-0 h-full w-full cursor-default bg-slate-950/25"
        type="button"
        onClick={onClose}
      />
      <aside
        aria-label={title}
        aria-modal="true"
        className="absolute right-0 top-0 flex h-full w-full max-w-[40rem] flex-col border-l border-[var(--ui-color-border)] bg-slate-50 shadow-2xl"
        role="dialog"
      >
        <header className="flex shrink-0 items-start justify-between gap-3 border-b border-[var(--ui-color-border)] bg-white px-4 py-3">
          <div className="min-w-0">
            <h2 className="truncate text-lg font-semibold text-slate-950">{title}</h2>
            {description ? <p className="mt-0.5 text-sm text-slate-500">{description}</p> : null}
          </div>
          <button
            ref={closeButtonRef}
            className="rounded-full border border-[var(--ui-color-border)] bg-white px-3 py-1.5 text-xs font-semibold text-slate-600 transition hover:bg-slate-50 focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
            type="button"
            onClick={onClose}
          >
            Cerrar
          </button>
        </header>

        <div className="min-h-0 flex-1 overflow-y-auto p-3">{children}</div>
      </aside>
    </div>
  );
}
