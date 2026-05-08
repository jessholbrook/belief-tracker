export type Role = "user" | "assistant";

export interface Message {
  id: string;
  conversation_id: string;
  role: Role;
  content: string;
  created_at: string;
}

export interface Conversation {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
  messages?: Message[];
}

export interface Belief {
  id: string;
  parent_id: string | null;
  statement: string;
  confidence: "high" | "medium" | "low";
  evidence: string;
  created_at: string;
  children: Belief[];
}

export type AgentEvent =
  | { type: "task_started"; task_id: string; data: Record<string, never> }
  | { type: "assistant_text"; task_id: string; data: { text: string } }
  | {
      type: "tool_use";
      task_id: string;
      data: {
        id: string;
        name: string;
        input: unknown;
        server: boolean;
      };
    }
  | {
      type: "tool_result";
      task_id: string;
      data: {
        tool_use_id: string;
        content: string;
        is_error?: boolean;
      };
    }
  | { type: "task_complete"; task_id: string; data: { final_text: string } }
  | { type: "error"; task_id: string; data: { message: string } };
