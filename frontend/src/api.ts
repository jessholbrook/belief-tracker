import type { Belief, Conversation } from "./types";

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`/api${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`${res.status}: ${text}`);
  }
  return res.json();
}

export const api = {
  listConversations: () => req<Conversation[]>("/conversations"),
  createConversation: (title = "New conversation") =>
    req<Conversation>("/conversations", {
      method: "POST",
      body: JSON.stringify({ title }),
    }),
  getConversation: (id: string) => req<Conversation>(`/conversations/${id}`),
  deleteConversation: (id: string) =>
    req<{ ok: true }>(`/conversations/${id}`, { method: "DELETE" }),
  listBeliefs: () => req<Belief[]>("/beliefs"),
  extractBeliefs: (text: string, parent_belief?: string) =>
    req<Belief[]>("/beliefs/extract", {
      method: "POST",
      body: JSON.stringify({ text, parent_belief }),
    }),
  deleteBelief: (id: string) =>
    req<{ ok: true }>(`/beliefs/${id}`, { method: "DELETE" }),
};

export function openChatSocket(conversationId: string): WebSocket {
  const proto = location.protocol === "https:" ? "wss" : "ws";
  return new WebSocket(`${proto}://${location.host}/ws/chat/${conversationId}`);
}
