import { useState, type KeyboardEvent } from "react";

interface Props {
  disabled?: boolean;
  onSend: (text: string) => void;
}

export function Composer({ disabled, onSend }: Props) {
  const [value, setValue] = useState("");

  function send() {
    const text = value.trim();
    if (!text || disabled) return;
    onSend(text);
    setValue("");
  }

  function onKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  }

  return (
    <div className="flex gap-2 border-t border-stone-200 bg-white p-3">
      <textarea
        className="flex-1 resize-none rounded-md border border-stone-300 px-3 py-2 text-sm focus:border-stone-500 focus:outline-none"
        rows={2}
        placeholder={
          disabled ? "Agent is working..." : "Ask anything (Shift+Enter for newline)"
        }
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={onKeyDown}
        disabled={disabled}
      />
      <button
        className="self-end rounded-md bg-stone-900 px-4 py-2 text-sm text-white disabled:opacity-50"
        onClick={send}
        disabled={disabled || !value.trim()}
      >
        Send
      </button>
    </div>
  );
}
