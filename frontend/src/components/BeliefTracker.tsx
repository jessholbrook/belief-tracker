import { useEffect, useState } from "react";
import { CornerDownRight, X } from "lucide-react";

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
  // When set, extracted beliefs become children of this belief.
  const [parent, setParent] = useState<Belief | null>(null);

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
      await api.extractBeliefs(text, parent?.id);
      setText("");
      setParent(null);
      await refresh();
    } finally {
      setLoading(false);
    }
  }

  async function remove(id: string) {
    await api.deleteBelief(id);
    if (parent?.id === id) setParent(null);
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
                <BeliefNode
                  key={b.id}
                  belief={b}
                  onDelete={remove}
                  onExtractUnder={setParent}
                />
              ))}
            </ul>
          )}
        </div>
      </ScrollArea>
      <Separator />
      <div className="bg-card p-4">
        {parent && (
          <div className="mb-2 flex items-center gap-2 text-xs text-muted-foreground">
            <CornerDownRight className="size-3.5 shrink-0" />
            <span className="truncate">
              Extracting sub-beliefs under: <em>{parent.statement}</em>
            </span>
            <button
              className="hover:text-foreground"
              onClick={() => setParent(null)}
              aria-label="Clear parent belief"
            >
              <X className="size-3.5" />
            </button>
          </div>
        )}
        <Textarea
          className="bg-background"
          rows={4}
          placeholder="Paste a transcript, doc, or quote here…"
          value={text}
          onChange={(e) => setText(e.target.value)}
        />
        <div className="mt-2 flex justify-end">
          <Button onClick={extract} disabled={loading || !text.trim()}>
            {loading ? "Extracting…" : parent ? "Extract sub-beliefs" : "Extract beliefs"}
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
  onExtractUnder,
}: {
  belief: Belief;
  onDelete: (id: string) => void;
  onExtractUnder: (belief: Belief) => void;
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
            onClick={() => onExtractUnder(belief)}
            title="Extract sub-beliefs under this"
            aria-label="Extract sub-beliefs under this belief"
          >
            <CornerDownRight className="size-4" />
          </button>
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
              <BeliefNode
                key={c.id}
                belief={c}
                onDelete={onDelete}
                onExtractUnder={onExtractUnder}
              />
            ))}
          </ul>
        )}
      </Card>
    </li>
  );
}
