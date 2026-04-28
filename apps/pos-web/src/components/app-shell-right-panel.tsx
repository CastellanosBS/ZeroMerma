import { createContext, useContext, useEffect, type ReactNode } from "react";

interface AppShellRightPanelContextValue {
  setRightPanelContent: (content: ReactNode | null) => void;
}

export const AppShellRightPanelContext =
  createContext<AppShellRightPanelContextValue | null>(null);

export function useAppShellRightPanel(content: ReactNode | null) {
  const context = useContext(AppShellRightPanelContext);

  useEffect(() => {
    if (!context) {
      return;
    }

    context.setRightPanelContent(content);
    return () => context.setRightPanelContent(null);
  }, [content, context]);
}
