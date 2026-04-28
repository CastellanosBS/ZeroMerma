import { DialogBody, DialogFooter, DialogHeader, DialogSurface } from "@zeromerma/ui";
import { useMemo } from "react";

import { PosButton, PosSectionTitle, PosStatusBadge } from "../../../components/pos-foundations";
import { SearchIcon, XIcon } from "../../../components/pos-icons";
import { cn } from "../../../lib/utils";
import {
  formatShortcutChordLabel,
} from "./keyboard-shortcut-registry-context";
import { useKeyboardShortcutRegistry } from "./use-keyboard-shortcut-registry";

export function KeyboardHelpOverlay() {
  const { closeHelp, isHelpOpen, shortcuts } = useKeyboardShortcutRegistry();

  const groupedShortcuts = useMemo(() => {
    return shortcuts.reduce<Record<string, typeof shortcuts>>((groups, shortcut) => {
      const currentGroup = groups[shortcut.group] ?? [];
      currentGroup.push(shortcut);
      groups[shortcut.group] = currentGroup;
      return groups;
    }, {});
  }, [shortcuts]);

  if (!isHelpOpen) {
    return null;
  }

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center bg-slate-950/35 px-4 py-10 backdrop-blur-[2px]">
      <DialogSurface className="w-full max-w-3xl overflow-hidden rounded-[28px] border border-[var(--pos-shell-border)] bg-white shadow-[var(--ui-shadow-overlay)]">
        <DialogHeader
          action={
            <PosButton leadingIcon={<XIcon className="h-4 w-4" />} onClick={closeHelp} variant="ghost">
              Cerrar
            </PosButton>
          }
        >
          <PosSectionTitle
            action={<PosStatusBadge status="ready">F1 / Ctrl+/</PosStatusBadge>}
            description="Usa estos atajos para operar sin salir del flujo actual."
            eyebrow="Ayuda de teclado"
            title="Atajos del POS"
          />
        </DialogHeader>
        <DialogBody className="grid gap-4 px-5 py-4">
          {Object.entries(groupedShortcuts).map(([group, groupShortcuts]) => (
            <section
              className="rounded-2xl border border-[var(--pos-shell-border)] bg-[var(--pos-shell-muted)]/65 p-3"
              key={group}
            >
              <div className="flex items-center gap-2">
                <span className="flex h-8 w-8 items-center justify-center rounded-xl bg-white text-[var(--pos-primary)]">
                  <SearchIcon className="h-4 w-4" />
                </span>
                <h3 className="text-sm font-semibold text-slate-950">{group}</h3>
              </div>
              <div className="mt-3 grid gap-2">
                {groupShortcuts.map((shortcut) => (
                  <div
                    className="grid gap-2 rounded-xl border border-[var(--pos-shell-border)] bg-white px-3 py-2.5 sm:grid-cols-[minmax(0,1fr)_auto]"
                    key={shortcut.id}
                  >
                    <div className="min-w-0">
                      <p className="text-sm font-semibold text-slate-950">{shortcut.label}</p>
                      <p className="text-sm leading-5 text-slate-600">{shortcut.description}</p>
                    </div>
                    <div className="flex flex-wrap items-center justify-start gap-1.5 sm:justify-end">
                      {shortcut.chords.map((chord) => (
                        <span
                          className={cn("pos-kbd-chip px-2 text-[0.6875rem] whitespace-nowrap")}
                          key={`${shortcut.id}-${chord}`}
                        >
                          {formatShortcutChordLabel(chord)}
                        </span>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </section>
          ))}
        </DialogBody>
        <DialogFooter>
          <PosButton onClick={closeHelp} variant="primary">
            Volver al flujo
          </PosButton>
        </DialogFooter>
      </DialogSurface>
    </div>
  );
}
