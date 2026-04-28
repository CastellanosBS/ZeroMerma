import { create } from "zustand";

import type { PosMessageAction, PosOperationResultMessage } from "../../lib/pos-messages";

export type StatusMessageTone = "error" | "info" | "success" | "warning";

type BasicStatusMessage = {
  actions?: PosMessageAction[];
  autoDismissMs?: number | null;
  description?: string;
  id: string;
  kind: "basic";
  onSelectAction?: (actionKey: string) => void;
  title: string;
  tone: StatusMessageTone;
};

type OperationResultStatusMessage = {
  autoDismissMs?: number | null;
  id: string;
  kind: "operationResult";
  onSelectAction?: (actionKey: string) => void;
  result: PosOperationResultMessage;
  tone: "success";
};

export type StatusMessage = BasicStatusMessage | OperationResultStatusMessage;

interface StatusMessageStore {
  dismissMessage: (id: string) => void;
  messages: StatusMessage[];
  pushMessage: (message: Omit<BasicStatusMessage, "id"> | Omit<OperationResultStatusMessage, "id">) => string;
  showError: (message: string) => void;
  showInfo: (message: string) => void;
  showOperationResult: (message: PosOperationResultMessage) => void;
  showSuccess: (message: string) => void;
  showWarning: (message: string) => void;
}

function createMessageId() {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }

  return `message-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function scheduleDismiss(
  dismissMessage: (id: string) => void,
  id: string,
  autoDismissMs?: number | null,
) {
  if (!autoDismissMs || autoDismissMs <= 0) {
    return;
  }

  globalThis.setTimeout(() => {
    dismissMessage(id);
  }, autoDismissMs);
}

export const useStatusMessageStore = create<StatusMessageStore>()((set, get) => ({
  dismissMessage: (id) =>
    set((state) => ({
      messages: state.messages.filter((message) => message.id !== id),
    })),
  messages: [],
  pushMessage: (message) => {
    const nextMessage = {
      ...message,
      id: createMessageId(),
    } as StatusMessage;

    set((state) => ({
      messages: [...state.messages, nextMessage],
    }));

    scheduleDismiss(get().dismissMessage, nextMessage.id, nextMessage.autoDismissMs);

    return nextMessage.id;
  },
  showError: (message) => {
    get().pushMessage({
      kind: "basic",
      title: message,
      tone: "error",
    });
  },
  showInfo: (message) => {
    get().pushMessage({
      autoDismissMs: 3600,
      kind: "basic",
      title: message,
      tone: "info",
    });
  },
  showOperationResult: (result) => {
    get().pushMessage({
      autoDismissMs: 5200,
      kind: "operationResult",
      result,
      tone: "success",
    });
  },
  showSuccess: (message) => {
    get().pushMessage({
      autoDismissMs: 3600,
      kind: "basic",
      title: message,
      tone: "success",
    });
  },
  showWarning: (message) => {
    get().pushMessage({
      autoDismissMs: 4200,
      kind: "basic",
      title: message,
      tone: "warning",
    });
  },
}));
