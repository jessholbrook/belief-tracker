"""Belief extraction: ask Claude to pull structured beliefs from text."""

from __future__ import annotations

import asyncio
import json

import anthropic

from . import db
from .config import settings


EXTRACTION_PROMPT = """Extract the speaker's beliefs and assumptions from the text below.

For each belief, return:
- statement: a short, declarative sentence stating the belief
- confidence: "high", "medium", or "low" — how strongly the speaker holds it
- evidence: a brief quote or paraphrase from the text that supports it

Return STRICTLY valid JSON of the form:
{"beliefs": [{"statement": "...", "confidence": "...", "evidence": "..."}]}

Be concise. Skip filler. If there are no clear beliefs, return {"beliefs": []}.

TEXT:
"""


def _client() -> anthropic.Anthropic:
    if not settings.anthropic_api_key:
        raise RuntimeError("ANTHROPIC_API_KEY is not set in backend/.env")
    return anthropic.Anthropic(api_key=settings.anthropic_api_key)


async def extract_beliefs(text: str, parent_id: str | None = None) -> list[dict]:
    client = _client()
    response = await asyncio.to_thread(
        client.messages.create,
        model=settings.model,
        max_tokens=2048,
        messages=[{"role": "user", "content": EXTRACTION_PROMPT + text}],
    )

    raw = next(
        (b.text for b in response.content if getattr(b, "type", None) == "text"),
        "",
    )
    raw = raw.strip()
    # Strip optional code fences.
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1] if "\n" in raw else raw
        if raw.endswith("```"):
            raw = raw[:-3]
        raw = raw.strip()

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return []

    saved: list[dict] = []
    for b in parsed.get("beliefs", []):
        statement = str(b.get("statement", "")).strip()
        if not statement:
            continue
        confidence = str(b.get("confidence", "medium")).lower()
        if confidence not in ("high", "medium", "low"):
            confidence = "medium"
        saved.append(
            db.insert_belief(
                statement=statement,
                confidence=confidence,
                evidence=str(b.get("evidence", "")).strip(),
                parent_id=parent_id,
            )
        )
    return saved


def belief_tree() -> list[dict]:
    """Return all beliefs nested by parent_id."""
    rows = db.list_beliefs()
    by_parent: dict[str | None, list[dict]] = {}
    for r in rows:
        node = {**r, "children": []}
        by_parent.setdefault(r["parent_id"], []).append(node)

    def attach(node: dict) -> dict:
        node["children"] = [attach(c) for c in by_parent.get(node["id"], [])]
        return node

    return [attach(n) for n in by_parent.get(None, [])]
