"""Agent service: runs the plan→execute→stream loop using Claude with tools.

Custom tools (executed locally) and Anthropic server-side tools coexist in one
loop. Custom tools surface as `tool_use` blocks we must satisfy with
`tool_result`; server-side tools (web_search, web_fetch) are handled by
Anthropic and arrive as completed `server_tool_use` + `*_tool_result` pairs.
"""

from __future__ import annotations

import asyncio
import json
import math
from collections.abc import AsyncIterator
from datetime import datetime, timezone
from typing import Any

import anthropic

from .config import settings
from .db import add_message, list_messages, new_id


SYSTEM_PROMPT = """You are a capable AI agent that helps the user accomplish tasks.

You have access to a small toolkit:
- web_search: research current information on the internet
- web_fetch: read the contents of a specific URL
- calculate: evaluate a math expression
- current_datetime: get the current date and time

When a task needs multiple steps, plan them out, then use tools as needed. Show
your reasoning briefly between tool calls. Be concise and direct.
"""


# ----- Custom tool definitions and implementations -----

CUSTOM_TOOLS = [
    {
        "name": "calculate",
        "description": "Evaluate a math expression. Supports +, -, *, /, **, parens, and the math module (e.g. math.sqrt, math.pi).",
        "input_schema": {
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "Math expression, e.g. '2 * (3 + 4)' or 'math.sqrt(2)'",
                }
            },
            "required": ["expression"],
        },
    },
    {
        "name": "current_datetime",
        "description": "Returns the current date and time in ISO 8601 format (UTC).",
        "input_schema": {"type": "object", "properties": {}},
    },
]

SERVER_TOOLS = [
    {"type": "web_search_20260209", "name": "web_search"},
    {"type": "web_fetch_20260209", "name": "web_fetch"},
]


def _safe_eval(expression: str) -> str:
    allowed = {"math": math, "__builtins__": {}}
    return str(eval(expression, allowed, {}))  # noqa: S307 — sandbox restricted


def execute_custom_tool(name: str, tool_input: dict) -> tuple[str, bool]:
    """Returns (output, is_error)."""
    try:
        if name == "calculate":
            return _safe_eval(tool_input["expression"]), False
        if name == "current_datetime":
            return datetime.now(timezone.utc).isoformat(), False
        return f"Unknown tool: {name}", True
    except Exception as e:  # noqa: BLE001
        return f"Tool error: {e}", True


# ----- Agent loop -----


def _client() -> anthropic.Anthropic:
    if not settings.anthropic_api_key:
        raise RuntimeError("ANTHROPIC_API_KEY is not set in backend/.env")
    return anthropic.Anthropic(api_key=settings.anthropic_api_key)


def _history(conversation_id: str) -> list[dict]:
    msgs = list_messages(conversation_id)
    return [{"role": m["role"], "content": m["content"]} for m in msgs]


def _block_to_event(block: Any) -> dict | None:
    """Map a single Claude content block to a frontend event payload."""
    btype = getattr(block, "type", None)
    if btype == "text":
        return {"type": "assistant_text", "text": block.text}
    if btype == "tool_use":
        return {
            "type": "tool_use",
            "id": block.id,
            "name": block.name,
            "input": block.input,
            "server": False,
        }
    if btype == "server_tool_use":
        return {
            "type": "tool_use",
            "id": block.id,
            "name": block.name,
            "input": block.input,
            "server": True,
        }
    if btype in ("web_search_tool_result", "web_fetch_tool_result"):
        return {
            "type": "tool_result",
            "tool_use_id": getattr(block, "tool_use_id", ""),
            "content": _summarize_server_result(block),
        }
    return None


def _summarize_server_result(block: Any) -> str:
    content = getattr(block, "content", None)
    if isinstance(content, list):
        parts = []
        for item in content:
            t = getattr(item, "type", "")
            if t == "web_search_result":
                parts.append(f"- {getattr(item, 'title', '')} ({getattr(item, 'url', '')})")
            elif t == "web_fetch_result":
                parts.append(f"Fetched {getattr(item, 'url', '')}")
            else:
                parts.append(str(item))
        return "\n".join(parts) if parts else "(no results)"
    return str(content) if content else "(no content)"


async def run_agent(
    conversation_id: str, user_message: str
) -> AsyncIterator[dict]:
    """Run the agent and yield events for the WebSocket layer."""
    task_id = new_id("task")
    yield {"type": "task_started", "task_id": task_id, "data": {}}

    add_message(conversation_id, "user", user_message)
    messages = _history(conversation_id)

    client = _client()
    final_text_parts: list[str] = []

    # Cap iterations as a safety net for the manual loop.
    for _ in range(10):
        try:
            # SDK call is sync; run in thread to avoid blocking the event loop.
            response = await asyncio.to_thread(
                client.messages.create,
                model=settings.model,
                max_tokens=settings.max_tokens,
                system=[
                    {
                        "type": "text",
                        "text": SYSTEM_PROMPT,
                        "cache_control": {"type": "ephemeral"},
                    }
                ],
                tools=SERVER_TOOLS + CUSTOM_TOOLS,
                messages=messages,
            )
        except anthropic.APIError as e:
            yield {
                "type": "error",
                "task_id": task_id,
                "data": {"message": f"{type(e).__name__}: {e}"},
            }
            return

        # Emit one event per content block.
        custom_tool_uses: list[Any] = []
        for block in response.content:
            event = _block_to_event(block)
            if event:
                yield {"type": event["type"], "task_id": task_id, "data": event}
            if getattr(block, "type", None) == "text":
                final_text_parts.append(block.text)
            if getattr(block, "type", None) == "tool_use":
                custom_tool_uses.append(block)

        # Persist the full assistant turn (raw blocks for round-tripping).
        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason == "end_turn":
            break

        if response.stop_reason == "pause_turn":
            # Server-side tool loop limit hit; re-send to continue.
            continue

        if not custom_tool_uses:
            break

        # Execute custom tools and feed results back as a single user turn.
        tool_results = []
        for tu in custom_tool_uses:
            output, is_error = execute_custom_tool(tu.name, tu.input)
            yield {
                "type": "tool_result",
                "task_id": task_id,
                "data": {
                    "tool_use_id": tu.id,
                    "content": output,
                    "is_error": is_error,
                },
            }
            tool_results.append(
                {
                    "type": "tool_result",
                    "tool_use_id": tu.id,
                    "content": output,
                    "is_error": is_error,
                }
            )
        messages.append({"role": "user", "content": tool_results})

    final_text = "\n".join(final_text_parts).strip() or "(no response)"
    add_message(conversation_id, "assistant", final_text)
    yield {
        "type": "task_complete",
        "task_id": task_id,
        "data": {"final_text": final_text},
    }


def serialize_event(event: dict) -> str:
    return json.dumps(event, default=str)
