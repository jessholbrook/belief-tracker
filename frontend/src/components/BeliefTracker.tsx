import { useEffect, useState } from "react";
import { X } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import { Textarea } from "@/components/ui/textarea";
import { api } from "../api";
import type { Belief } from "../types";

export function BeliefTracker() {
  const [beliefs, setBeliefs] = useState<Belief[]>([]);
  const [text, setText] = useState("");
  const [loading, setLoading] = useState(false);

  async function refresh() {
    setBeliefs(await api.listBeliefs());
  }

  useEffect(() => {
    refresh();
  }, []);

  async function extract() {
    if (!text.trim() || loading) return;
    setLoading(true);
    try {
      await api.extractBeliefs(text);
      setText("");
      await refresh();
    } finally {
      setLoading(false);
    }
  }

  async function remove(id: string) {
    await api.deleteBelief(id);
    await refresh();
  }

  return (
    <div className="flex h-full flex-col">
      <div className="bg-card p-4">
        <h2 className="text-lg font-semibold">Beliefs</h2>
        <p className="mt-1 text-sm text-muted-foreground">
          Paste text and extract the speaker's beliefs and assumptions.
        </p>
      </div>
      <Separator />
      <ScrollArea className="flex-1">
        <div className="p-4">
          {beliefs.length === 0 ? (
            <div className="text-sm text-muted-foreground">
              No beliefs yet. Extract some below.
            </div>
          ) : (
            <ul className="space-y-2">
              {beliefs.map((b) => (
                <BeliefNode key={b.id} belief={b} onDelete={remove} />
              ))}
            </ul>
          )}
        </div>
      </ScrollArea>
      <Separator />
      <div className="bg-card p-4">
        <Textarea
          className="bg-background"
          rows={4}
          placeholder="Paste a transcript, doc, or quote here…"
          value={text}
          onChange={(e) => setText(e.target.value)}
        />
        <div className="mt-2 flex justify-end">
          <Button onClick={extract} disabled={loading || !text.trim()}>
            {loading ? "Extracting…" : "Extract beliefs"}
          </Button>
        </div>
      </div>
    </div>
  );
}

const confidenceVariant: Record<
  Belief["confidence"],
  "success" | "warning" | "secondary"
> = {
  high: "success",
  medium: "warning",
  low: "secondary",
};

function BeliefNode({
  belief,
  onDelete,
}: {
  belief: Belief;
  onDelete: (id: string) => void;
}) {
  return (
    <li>
      <Card className="p-3 shadow-sm">
        <div className="flex items-start gap-2">
          <Badge variant={confidenceVariant[belief.confidence]}>
            {belief.confidence}
          </Badge>
          <div className="flex-1">
            <div className="text-sm font-medium">{belief.statement}</div>
            {belief.evidence && (
              <div className="mt-1 text-xs italic text-muted-foreground">
                "{belief.evidence}"
              </div>
            )}
          </div>
          <button
            className="text-muted-foreground hover:text-foreground"
            onClick={() => onDelete(belief.id)}
            aria-label="Delete belief"
          >
            <X className="size-4" />
          </button>
        </div>
        {belief.children.length > 0 && (
          <ul className="ml-4 mt-2 space-y-2 border-l pl-3">
            {belief.children.map((c) => (
              <BeliefNode key={c.id} belief={c} onDelete={onDelete} />
            ))}
          </ul>
        )}
      </Card>
    </li>
  );
}
