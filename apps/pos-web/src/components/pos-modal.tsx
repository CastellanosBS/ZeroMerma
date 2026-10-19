import { useEffect, useRef, type PropsWithChildren } from "react";

const focusableSelector = "button:not(:disabled), a[href], input:not(:disabled), select:not(:disabled), textarea:not(:disabled), [tabindex]:not([tabindex='-1'])";

/** Keep both focus and global POS shortcuts inside the active modal. */
export function PosModal({ children, label, onClose, onConfirm, busy = false }: PropsWithChildren<{
  label: string;
  onClose: () => void;
  onConfirm?: () => void;
  busy?: boolean;
}>) {
  const modal = useRef<HTMLDivElement>(null);
  const close = useRef(onClose);
  const pending = useRef(busy);
  const confirm = useRef(onConfirm);
  close.current = onClose;
  pending.current = busy;
  confirm.current = onConfirm;

  useEffect(() => {
    const surface = modal.current!;
    const previous = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    const candidates = () => Array.from(surface.querySelectorAll<HTMLElement>("*"))
      .filter((node) => node.matches(focusableSelector) && !node.closest("[hidden], [inert], [aria-hidden='true']"));
    const focusFirst = () => (candidates()[0] ?? surface).focus();
    focusFirst();
    const focusInside = (event: FocusEvent) => {
      const dialogs = document.querySelectorAll("[data-pos-modal='true']");
      if (dialogs[dialogs.length - 1] !== surface) return;
      if (event.target instanceof Node && !surface.contains(event.target)) focusFirst();
    };
    const handleKey = (event: KeyboardEvent) => {
      const dialogs = document.querySelectorAll("[data-pos-modal='true']");
      if (dialogs[dialogs.length - 1] !== surface) return;
      if (event.key === "Enter" && (event.ctrlKey || event.metaKey) && confirm.current) {
        event.preventDefault();
        event.stopImmediatePropagation();
        if (!pending.current) confirm.current();
        return;
      }
      if (event.key === "Escape") {
        event.preventDefault();
        event.stopImmediatePropagation();
        if (!pending.current) close.current();
        return;
      }
      if (event.key === "Tab") {
        const entries = candidates();
        const first = entries[0] ?? surface;
        const last = entries[entries.length - 1] ?? surface;
        if (event.shiftKey && (document.activeElement === first || document.activeElement === surface)) {
          event.preventDefault(); last.focus();
        } else if (!event.shiftKey && (document.activeElement === last || document.activeElement === surface)) {
          event.preventDefault(); first.focus();
        }
      }
      // Bubble-phase document/window shortcuts must never confirm the underlying form.
      // Native input editing, tab navigation and button activation remain available.
      if (!(event.target instanceof Node) || !surface.contains(event.target)) {
        event.preventDefault();
        event.stopImmediatePropagation();
      }
    };
    window.addEventListener("keydown", handleKey, true);
    document.addEventListener("focusin", focusInside);
    return () => {
      window.removeEventListener("keydown", handleKey, true);
      document.removeEventListener("focusin", focusInside);
      if (previous?.isConnected) previous.focus();
    };
  }, []);

  return <div
    ref={modal}
    role="dialog"
    aria-modal="true"
    aria-label={label}
    aria-busy={busy}
    data-pos-modal="true"
    className="pos-modal fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-slate-950/30 p-4 sm:py-8"
    tabIndex={-1}
    onKeyDown={(event) => event.stopPropagation()}
  >{children}</div>;
}
