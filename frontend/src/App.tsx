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
  // The socket URL embeds a conversation id; track whose socket we hold so a
  // reused socket can never deliver a message to the wrong conversation.
  const wsConvIdRef = useRef<string | null>(null);
  const activeIdRef = useRef<string | null>(null);
  activeIdRef.current = activeId;

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

  function finishRun(cid: string) {
    // Ignore events from sockets we've already replaced (e.g. the close event
    // fired by deliberately discarding an old conversation's socket).
    if (wsConvIdRef.current !== cid) return;
    setBusy(false);
    // Refresh persisted messages (drops the optimistic placeholder) and the
    // sidebar (first message auto-titles the conversation) — but only if the
    // user is still looking at this conversation.
    if (activeIdRef.current === cid) {
      api.getConversation(cid).then((c) => {
        if (activeIdRef.current === cid) setMessages(c.messages ?? []);
      });
    }
    api.listConversations().then(setConversations);
  }

  /** Return an open socket for `cid`, creating one (with listeners attached
   * exactly once) if the current socket is missing, closed, or belongs to a
   * different conversation. */
  function getSocket(cid: string): WebSocket {
    if (
      wsRef.current &&
      wsConvIdRef.current === cid &&
      (wsRef.current.readyState === WebSocket.OPEN ||
        wsRef.current.readyState === WebSocket.CONNECTING)
    ) {
      return wsRef.current;
    }
    wsRef.current?.close();

    const ws = openChatSocket(cid);
    wsRef.current = ws;
    wsConvIdRef.current = cid;

    ws.addEventListener("message", (e) => {
      let event: AgentEvent;
      try {
        event = JSON.parse(e.data) as AgentEvent;
      } catch {
        return; // Ignore unparseable messages.
      }
      if (wsConvIdRef.current !== cid) return;
      setEvents((es) => [...es, event]);
      if (event.type === "task_complete" || event.type === "error") {
        finishRun(cid);
      }
    });
    ws.addEventListener("close", () => finishRun(cid));
    ws.addEventListener("error", () => finishRun(cid));
    return ws;
  }

  async function newChat() {
    const c = await api.createConversation();
    setConversations((cs) => [c, ...cs]);
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
    const cid = activeId;

    // Optimistically add user message.
    setMessages((ms) => [
      ...ms,
      {
        id: `tmp_${Date.now()}`,
        conversation_id: cid,
        role: "user",
        content: text,
        created_at: new Date().toISOString(),
      },
    ]);
    setEvents([]);
    setBusy(true);

    const ws = getSocket(cid);
    const payload = JSON.stringify({ type: "user_message", content: text });
    if (ws.readyState === WebSocket.OPEN) {
      ws.send(payload);
    } else {
      ws.addEventListener("open", () => ws.send(payload), { once: true });
    }
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
          <div className="flex h-full items-center justify-center text-muted-foreground">
            Pick a conversation or start a new one.
          </div>
        ) : (
          <div className="flex h-full flex-col">
            <div className="flex-1 space-y-3 overflow-y-auto p-4">
              {messages
                .filter((m) => m.content)
                .map((m) => (
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
