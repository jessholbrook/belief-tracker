import type { Belief, Conversation } from "./types";

// In dev: VITE_API_BASE is unset; relative `/api` paths get proxied to
// localhost:1337 by vite.config.ts. In prod: set VITE_API_BASE to the
// absolute backend URL (e.g. https://belief-tracker-api.fly.dev).
const API_BASE = import.meta.env.VITE_API_BASE ?? "";

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}/api${path}`, {
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
  if (API_BASE) {
    // Prod: convert https://x.fly.dev → wss://x.fly.dev
    const wsBase = API_BASE.replace(/^http/, "ws");
    return new WebSocket(`${wsBase}/ws/chat/${conversationId}`);
  }
  // Dev: vite proxy handles /ws
  const proto = location.protocol === "https:" ? "wss" : "ws";
  return new WebSocket(`${proto}://${location.host}/ws/chat/${conversationId}`);
}
