import {
  CheckCircle2,
  ChevronRight,
  CircleAlert,
  CornerDownRight,
  Globe,
  TriangleAlert,
  Wrench,
} from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import type { AgentEvent } from "../types";

export function TaskView({ events }: { events: AgentEvent[] }) {
  if (events.length === 0) return null;
  return (
    <Card>
      <CardHeader className="p-4 pb-2">
        <CardTitle className="text-xs uppercase tracking-wide text-muted-foreground">
          Agent activity
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-1.5 p-4 pt-0 text-xs">
        {events.map((e, i) => (
          <EventRow key={i} event={e} />
        ))}
      </CardContent>
    </Card>
  );
}

function EventRow({ event }: { event: AgentEvent }) {
  switch (event.type) {
    case "task_started":
      return (
        <div className="flex items-center gap-1.5 text-muted-foreground">
          <ChevronRight className="size-3.5" /> Task started
        </div>
      );
    case "assistant_text":
      return (
        <div className="whitespace-pre-wrap text-foreground/80">
          {event.data.text}
        </div>
      );
    case "tool_use": {
      const inputStr = JSON.stringify(event.data.input);
      const Icon = event.data.server ? Globe : Wrench;
      return (
        <div className="flex items-start gap-1.5 font-mono text-muted-foreground">
          <Icon className="mt-0.5 size-3.5 shrink-0" />
          <span>
            {event.data.name}({inputStr})
          </span>
        </div>
      );
    }
    case "tool_result":
      return (
        <div
          className={cn(
            "flex items-start gap-1.5 pl-4 font-mono text-muted-foreground",
            event.data.is_error && "text-destructive",
          )}
        >
          <CornerDownRight className="mt-0.5 size-3.5 shrink-0" />
          <span>{truncate(event.data.content, 240)}</span>
        </div>
      );
    case "warning":
      return (
        <div className="flex items-center gap-1.5 text-amber-600">
          <TriangleAlert className="size-3.5" /> {event.data.message}
        </div>
      );
    case "task_complete":
      return (
        <div className="flex items-center gap-1.5 text-emerald-700">
          <CheckCircle2 className="size-3.5" /> Task complete
        </div>
      );
    case "error":
      return (
        <div className="flex items-center gap-1.5 text-destructive">
          <CircleAlert className="size-3.5" /> {event.data.message}
        </div>
      );
  }
}

function truncate(s: string, n: number) {
  return s.length > n ? `${s.slice(0, n)}…` : s;
}
