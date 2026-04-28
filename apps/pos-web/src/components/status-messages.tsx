import { PosOperationResultToast, PosToastMessage } from "./pos-feedback";
import { useStatusMessageStore } from "../features/status-messages/store";

export function StatusMessagesViewport() {
  const messages = useStatusMessageStore((state) => state.messages);
  const dismissMessage = useStatusMessageStore((state) => state.dismissMessage);

  if (messages.length === 0) {
    return null;
  }

  return (
    <div className="pointer-events-none fixed inset-x-0 top-3 z-50 flex justify-center px-3">
      <div className="grid w-full max-w-xl gap-2.5">
        {messages.map((message) =>
          message.kind === "operationResult" ? (
            <PosOperationResultToast
              key={message.id}
              message={message.result}
              onDismiss={() => dismissMessage(message.id)}
              onSelectAction={message.onSelectAction}
            />
          ) : (
            <PosToastMessage
              actions={message.actions}
              key={message.id}
              description={message.description}
              onDismiss={message.tone === "error" ? () => dismissMessage(message.id) : undefined}
              onSelectAction={message.onSelectAction}
              title={message.title}
              tone={message.tone}
            />
          ),
        )}
      </div>
    </div>
  );
}
