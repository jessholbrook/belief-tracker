import { Brain, MessageSquarePlus, X } from "lucide-react";

import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import { cn } from "@/lib/utils";
import type { Conversation } from "../types";

interface Props {
  conversations: Conversation[];
  activeId: string | null;
  view: "chat" | "beliefs";
  onSelectChat: (id: string) => void;
  onNewChat: () => void;
  onShowBeliefs: () => void;
  onDeleteChat: (id: string) => void;
}

export function Sidebar({
  conversations,
  activeId,
  view,
  onSelectChat,
  onNewChat,
  onShowBeliefs,
  onDeleteChat,
}: Props) {
  return (
    <aside className="flex h-full w-64 flex-col border-r bg-card">
      <div className="p-3">
        <h1 className="text-base font-semibold">belief-tracker</h1>
      </div>
      <Separator />
      <div className="flex flex-col gap-1 p-2">
        <Button className="justify-start" onClick={onNewChat}>
          <MessageSquarePlus />
          New chat
        </Button>
        <Button
          variant={view === "beliefs" ? "secondary" : "ghost"}
          className="justify-start"
          onClick={onShowBeliefs}
        >
          <Brain />
          Beliefs
        </Button>
      </div>
      <Separator />
      <div className="px-4 py-2 text-xs uppercase tracking-wide text-muted-foreground">
        Chats
      </div>
      <ScrollArea className="flex-1 px-2">
        {conversations.length === 0 && (
          <div className="px-2 text-sm text-muted-foreground">
            No conversations yet
          </div>
        )}
        {conversations.map((c) => (
          <div
            key={c.id}
            className={cn(
              "group flex items-center justify-between rounded-md px-2 py-1.5 text-sm",
              view === "chat" && activeId === c.id
                ? "bg-secondary"
                : "hover:bg-accent",
            )}
          >
            <button
              className="flex-1 truncate text-left"
              onClick={() => onSelectChat(c.id)}
            >
              {c.title}
            </button>
            <button
              className="ml-1 text-muted-foreground opacity-0 transition hover:text-foreground group-hover:opacity-100"
              onClick={() => onDeleteChat(c.id)}
              title="Delete"
              aria-label="Delete conversation"
            >
              <X className="size-4" />
            </button>
          </div>
        ))}
      </ScrollArea>
    </aside>
  );
}
