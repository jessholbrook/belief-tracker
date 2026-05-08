import type { Message as MessageType } from "../types";

export function Message({ message }: { message: MessageType }) {
  const isUser = message.role === "user";
  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-[80%] whitespace-pre-wrap rounded-lg px-4 py-2 text-sm ${
          isUser ? "bg-stone-900 text-white" : "bg-stone-100 text-stone-900"
        }`}
      >
        {message.content}
      </div>
    </div>
  );
}
