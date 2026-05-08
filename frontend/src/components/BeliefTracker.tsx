import { useEffect, useState } from "react";
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
      <div className="border-b border-stone-200 bg-white p-4">
        <h2 className="text-lg font-semibold">Beliefs</h2>
        <p className="mt-1 text-sm text-stone-600">
          Paste text and extract the speaker's beliefs and assumptions.
        </p>
      </div>
      <div className="flex-1 overflow-y-auto p-4">
        {beliefs.length === 0 ? (
          <div className="text-sm text-stone-500">
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
      <div className="border-t border-stone-200 bg-white p-4">
        <textarea
          className="w-full resize-none rounded-md border border-stone-300 px-3 py-2 text-sm focus:border-stone-500 focus:outline-none"
          rows={4}
          placeholder="Paste a transcript, doc, or quote here…"
          value={text}
          onChange={(e) => setText(e.target.value)}
        />
        <div className="mt-2 flex justify-end">
          <button
            className="rounded-md bg-stone-900 px-4 py-1.5 text-sm text-white disabled:opacity-50"
            onClick={extract}
            disabled={loading || !text.trim()}
          >
            {loading ? "Extracting…" : "Extract beliefs"}
          </button>
        </div>
      </div>
    </div>
  );
}

const confidenceColor: Record<Belief["confidence"], string> = {
  high: "bg-emerald-100 text-emerald-800",
  medium: "bg-amber-100 text-amber-800",
  low: "bg-stone-100 text-stone-700",
};

function BeliefNode({
  belief,
  onDelete,
}: {
  belief: Belief;
  onDelete: (id: string) => void;
}) {
  return (
    <li className="rounded-md border border-stone-200 bg-white p-3">
      <div className="flex items-start gap-2">
        <span
          className={`rounded px-1.5 py-0.5 text-xs ${
            confidenceColor[belief.confidence]
          }`}
        >
          {belief.confidence}
        </span>
        <div className="flex-1">
          <div className="text-sm font-medium">{belief.statement}</div>
          {belief.evidence && (
            <div className="mt-1 text-xs italic text-stone-500">
              "{belief.evidence}"
            </div>
          )}
        </div>
        <button
          className="text-stone-400 hover:text-stone-700"
          onClick={() => onDelete(belief.id)}
        >
          ×
        </button>
      </div>
      {belief.children.length > 0 && (
        <ul className="ml-4 mt-2 space-y-2 border-l border-stone-200 pl-3">
          {belief.children.map((c) => (
            <BeliefNode key={c.id} belief={c} onDelete={onDelete} />
          ))}
        </ul>
      )}
    </li>
  );
}
