import type { AgentEvent } from "../types";

export function TaskView({ events }: { events: AgentEvent[] }) {
  if (events.length === 0) return null;
  return (
    <div className="rounded-lg border border-stone-200 bg-white p-3 text-xs">
      <div className="mb-2 font-semibold text-stone-700">Agent activity</div>
      <div className="space-y-1.5">
        {events.map((e, i) => (
          <EventRow key={i} event={e} />
        ))}
      </div>
    </div>
  );
}

function EventRow({ event }: { event: AgentEvent }) {
  switch (event.type) {
    case "task_started":
      return <div className="text-stone-500">▸ Task started</div>;
    case "assistant_text":
      return (
        <div className="whitespace-pre-wrap text-stone-700">
          {event.data.text}
        </div>
      );
    case "tool_use": {
      const inputStr = JSON.stringify(event.data.input);
      const label = event.data.server ? "🌐" : "🔧";
      return (
        <div className="font-mono text-stone-600">
          {label} {event.data.name}({inputStr})
        </div>
      );
    }
    case "tool_result":
      return (
        <div
          className={`pl-4 font-mono text-stone-500 ${
            event.data.is_error ? "text-red-600" : ""
          }`}
        >
          ↳ {truncate(event.data.content, 240)}
        </div>
      );
    case "task_complete":
      return <div className="text-emerald-700">✓ Task complete</div>;
    case "error":
      return <div className="text-red-600">✗ {event.data.message}</div>;
  }
}

function truncate(s: string, n: number) {
  return s.length > n ? `${s.slice(0, n)}…` : s;
}
