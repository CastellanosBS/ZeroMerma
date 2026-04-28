import { createContext } from "react";

export interface KeyboardShortcutDefinition {
  allowInEditable?: boolean;
  chords: readonly string[];
  description: string;
  group: string;
  handler: (event: KeyboardEvent) => void;
  id: string;
  isEnabled?: () => boolean;
  label: string;
  order?: number;
  preventDefault?: boolean;
  priority?: number;
  stopPropagation?: boolean;
}

export interface RegisteredKeyboardShortcut extends KeyboardShortcutDefinition {
  source: "builtin" | "module";
}

export interface KeyboardShortcutRegistryContextValue {
  closeHelp: () => void;
  isHelpOpen: boolean;
  openHelp: () => void;
  registerShortcuts: (shortcuts: readonly KeyboardShortcutDefinition[]) => () => void;
  shortcuts: RegisteredKeyboardShortcut[];
  toggleHelp: () => void;
}

export const KeyboardShortcutRegistryContext =
  createContext<KeyboardShortcutRegistryContextValue | null>(null);

export function formatShortcutChordLabel(chord: string): string {
  return chord.replace("Meta", "Cmd").replace(/\+/g, " + ");
}
