"""Belief extraction: ask Claude to pull structured beliefs from text.

Uses a forced tool call so the API guarantees schema-valid output — no
JSON-in-prose parsing or code-fence stripping needed.
"""

from __future__ import annotations

import asyncio

import anthropic

from . import db
from .config import settings


EXTRACTION_PROMPT = """Extract the speaker's beliefs and assumptions from the text below, \
then record them with the record_beliefs tool.

For each belief provide:
- statement: a short, declarative sentence stating the belief
- confidence: "high", "medium", or "low" — how strongly the speaker holds it
- evidence: a brief quote or paraphrase from the text that supports it

Be concise. Skip filler. If there are no clear beliefs, record an empty list.

TEXT:
"""

RECORD_BELIEFS_TOOL = {
    "name": "record_beliefs",
    "description": "Record the beliefs extracted from the text.",
    "input_schema": {
        "type": "object",
        "properties": {
            "beliefs": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "statement": {"type": "string"},
                        "confidence": {
                            "type": "string",
                            "enum": ["high", "medium", "low"],
                        },
                        "evidence": {"type": "string"},
                    },
                    "required": ["statement", "confidence"],
                },
            }
        },
        "required": ["beliefs"],
    },
}


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
        tools=[RECORD_BELIEFS_TOOL],
        tool_choice={"type": "tool", "name": "record_beliefs"},
        messages=[{"role": "user", "content": EXTRACTION_PROMPT + text}],
    )

    tool_use = next(
        (b for b in response.content if getattr(b, "type", None) == "tool_use"),
        None,
    )
    parsed = tool_use.input if tool_use else {}

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
