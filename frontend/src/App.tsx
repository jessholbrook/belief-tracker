import { useEffect, useRef, useState } from "react";
import { api, openChatSocket } from "./api";
import type { AgentEvent, Conversation, Message } from "./types";
import { BeliefTracker } from "./components/BeliefTracker";
import { Composer } from "./components/Composer";
import { Message as MessageView } from "./components/Message";
import { Sidebar } from "./components/Sidebar";
import { TaskView } from "./components/TaskView";

type View = "chat" | "beliefs";

export default function App() {
  const [view, setView] = useState<View>("chat");
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [events, setEvents] = useState<AgentEvent[]>([]);
  const [busy, setBusy] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    api.listConversations().then(setConversations);
  }, []);

  useEffect(() => {
    if (!activeId) {
      setMessages([]);
      return;
    }
    api.getConversation(activeId).then((c) => setMessages(c.messages ?? []));
  }, [activeId]);

  useEffect(() => {
    return () => wsRef.current?.close();
  }, []);

  async function newChat() {
    const c = await api.createConversation();
    setConversations([c, ...conversations]);
    setActiveId(c.id);
    setView("chat");
    setMessages([]);
    setEvents([]);
  }

  async function selectChat(id: string) {
    setActiveId(id);
    setView("chat");
    setEvents([]);
  }

  async function deleteChat(id: string) {
    await api.deleteConversation(id);
    setConversations((cs) => cs.filter((c) => c.id !== id));
    if (activeId === id) {
      setActiveId(null);
      setMessages([]);
    }
  }

  function send(text: string) {
    if (!activeId) return;

    // Optimistically add user message.
    setMessages((ms) => [
      ...ms,
      {
        id: `tmp_${Date.now()}`,
        conversation_id: activeId,
        role: "user",
        content: text,
        created_at: new Date().toISOString(),
      },
    ]);
    setEvents([]);
    setBusy(true);

    const ws =
      wsRef.current && wsRef.current.readyState === WebSocket.OPEN
        ? wsRef.current
        : openChatSocket(activeId);
    wsRef.current = ws;

    const cleanup = () => {
      setBusy(false);
      // Refresh persisted messages so we drop the optimistic placeholder.
      if (activeId) {
        api.getConversation(activeId).then((c) => setMessages(c.messages ?? []));
      }
    };

    const handle = (event: AgentEvent) => {
      setEvents((es) => [...es, event]);
      if (event.type === "task_complete" || event.type === "error") {
        cleanup();
      }
    };

    if (ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: "user_message", content: text }));
    } else {
      ws.addEventListener("open", () => {
        ws.send(JSON.stringify({ type: "user_message", content: text }));
      });
    }

    ws.addEventListener("message", (e) => {
      try {
        handle(JSON.parse(e.data) as AgentEvent);
      } catch {
        // Ignore unparseable messages.
      }
    });
    ws.addEventListener("close", cleanup);
    ws.addEventListener("error", cleanup);
  }

  return (
    <div className="flex h-full">
      <Sidebar
        conversations={conversations}
        activeId={activeId}
        view={view}
        onSelectChat={selectChat}
        onNewChat={newChat}
        onShowBeliefs={() => setView("beliefs")}
        onDeleteChat={deleteChat}
      />
      <main className="flex-1 overflow-hidden">
        {view === "beliefs" ? (
          <BeliefTracker />
        ) : !activeId ? (
          <div className="flex h-full items-center justify-center text-stone-500">
            Pick a conversation or start a new one.
          </div>
        ) : (
          <div className="flex h-full flex-col">
            <div className="flex-1 space-y-3 overflow-y-auto p-4">
              {messages.map((m) => (
                <MessageView key={m.id} message={m} />
              ))}
              <TaskView events={events} />
            </div>
            <Composer disabled={busy} onSend={send} />
          </div>
        )}
      </main>
    </div>
  );
}
