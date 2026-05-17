import { useState, type KeyboardEvent } from "react";
import { SendHorizonal } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";

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
    <div className="flex items-end gap-2 border-t bg-card p-3">
      <Textarea
        className="flex-1 resize-none bg-background"
        rows={2}
        placeholder={
          disabled
            ? "Agent is working…"
            : "Ask anything (Shift+Enter for newline)"
        }
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={onKeyDown}
        disabled={disabled}
      />
      <Button onClick={send} disabled={disabled || !value.trim()}>
        <SendHorizonal />
        Send
      </Button>
    </div>
  );
}
