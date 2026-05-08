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
    <aside className="flex h-full w-64 flex-col border-r border-stone-200 bg-white">
      <div className="border-b border-stone-200 p-3">
        <h1 className="text-base font-semibold">belief-tracker</h1>
      </div>
      <div className="flex flex-col gap-1 p-2">
        <button
          className="rounded-md bg-stone-900 px-3 py-1.5 text-sm text-white"
          onClick={onNewChat}
        >
          + New chat
        </button>
        <button
          className={`rounded-md px-3 py-1.5 text-left text-sm ${
            view === "beliefs"
              ? "bg-stone-100 font-medium"
              : "hover:bg-stone-50"
          }`}
          onClick={onShowBeliefs}
        >
          Beliefs
        </button>
      </div>
      <div className="flex-1 overflow-y-auto p-2">
        <div className="mb-1 px-2 text-xs uppercase tracking-wide text-stone-400">
          Chats
        </div>
        {conversations.length === 0 && (
          <div className="px-2 text-sm text-stone-400">No conversations yet</div>
        )}
        {conversations.map((c) => (
          <div
            key={c.id}
            className={`group flex items-center justify-between rounded-md px-2 py-1.5 text-sm ${
              view === "chat" && activeId === c.id
                ? "bg-stone-100"
                : "hover:bg-stone-50"
            }`}
          >
            <button
              className="flex-1 truncate text-left"
              onClick={() => onSelectChat(c.id)}
            >
              {c.title}
            </button>
            <button
              className="opacity-0 transition group-hover:opacity-100"
              onClick={() => onDeleteChat(c.id)}
              title="Delete"
            >
              ×
            </button>
          </div>
        ))}
      </div>
    </aside>
  );
}
