"""Agent service: runs the plan→execute→stream loop using Claude with tools.

Custom tools (executed locally) and Anthropic server-side tools coexist in one
loop. Custom tools surface as `tool_use` blocks we must satisfy with
`tool_result`; server-side tools (web_search, web_fetch) are handled by
Anthropic and arrive as completed `server_tool_use` + `*_tool_result` pairs.
"""

from __future__ import annotations

import ast
import asyncio
import json
import math
import operator
from collections import defaultdict
from collections.abc import AsyncIterator
from datetime import datetime, timezone
from typing import Any

import anthropic

from .config import settings
from .db import add_message, list_messages, new_id, set_conversation_title


SYSTEM_PROMPT = """You are a capable AI agent that helps the user accomplish tasks.

You have access to a small toolkit:
- web_search: research current information on the internet
- web_fetch: read the contents of a specific URL
- calculate: evaluate a math expression
- current_datetime: get the current date and time

When a task needs multiple steps, plan them out, then use tools as needed. Show
your reasoning briefly between tool calls. Be concise and direct.
"""

MAX_ITERATIONS = 10


# ----- Custom tool definitions and implementations -----

CUSTOM_TOOLS = [
    {
        "name": "calculate",
        "description": "Evaluate a math expression. Supports +, -, *, /, //, %, **, parens, and math-module functions/constants (e.g. math.sqrt, sqrt, math.pi, pi).",
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


# AST-whitelist evaluator. `eval` — even with empty __builtins__ — is escapable
# via attribute chains like ().__class__.__bases__, so we only interpret an
# explicit set of arithmetic nodes and math-module names.

_BIN_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}
_UNARY_OPS = {ast.UAdd: operator.pos, ast.USub: operator.neg}
_MATH_NAMES = {n: getattr(math, n) for n in dir(math) if not n.startswith("_")}
_MAX_POW_EXPONENT = 10_000


def _eval_node(node: ast.AST) -> Any:
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _BIN_OPS:
        left, right = _eval_node(node.left), _eval_node(node.right)
        if isinstance(node.op, ast.Pow) and abs(right) > _MAX_POW_EXPONENT:
            raise ValueError(f"Exponent too large (max {_MAX_POW_EXPONENT})")
        return _BIN_OPS[type(node.op)](left, right)
    if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY_OPS:
        return _UNARY_OPS[type(node.op)](_eval_node(node.operand))
    if isinstance(node, ast.Name):
        if node.id in _MATH_NAMES:
            return _MATH_NAMES[node.id]
        raise ValueError(f"Unknown name: {node.id}")
    if isinstance(node, ast.Attribute):
        if isinstance(node.value, ast.Name) and node.value.id == "math" and node.attr in _MATH_NAMES:
            return _MATH_NAMES[node.attr]
        raise ValueError("Only math.<name> attributes are allowed")
    if isinstance(node, ast.Call):
        if node.keywords:
            raise ValueError("Keyword arguments are not supported")
        func = _eval_node(node.func)
        if not callable(func):
            raise ValueError("Not a callable")
        return func(*[_eval_node(a) for a in node.args])
    raise ValueError(f"Unsupported syntax: {type(node).__name__}")


def _safe_eval(expression: str) -> str:
    tree = ast.parse(expression, mode="eval")
    return str(_eval_node(tree.body))


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

# Serialize concurrent runs on the same conversation so history can't interleave.
_conversation_locks: defaultdict[str, asyncio.Lock] = defaultdict(asyncio.Lock)


def _client() -> anthropic.Anthropic:
    if not settings.anthropic_api_key:
        raise RuntimeError("ANTHROPIC_API_KEY is not set in backend/.env")
    return anthropic.Anthropic(api_key=settings.anthropic_api_key)


def _dump_block(block: Any) -> dict:
    if hasattr(block, "model_dump"):
        return block.model_dump(mode="json", exclude_none=True)
    if isinstance(block, dict):
        return block
    return dict(vars(block))


def _history(conversation_id: str) -> list[dict]:
    """Rebuild API-format history. Messages persisted with raw content blocks
    (tool calls and results) round-trip so the agent keeps tool context
    across turns; plain-text rows fall back to their text content."""
    out: list[dict] = []
    for m in list_messages(conversation_id):
        if m.get("api_blocks"):
            out.append({"role": m["role"], "content": json.loads(m["api_blocks"])})
        elif m["content"]:
            out.append({"role": m["role"], "content": m["content"]})
    return out


def _derive_title(text: str, limit: int = 60) -> str:
    title = " ".join(text.split())
    return title[: limit - 1] + "…" if len(title) > limit else title


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

    async with _conversation_locks[conversation_id]:
        is_first_message = not list_messages(conversation_id)
        add_message(conversation_id, "user", user_message)
        if is_first_message:
            set_conversation_title(conversation_id, _derive_title(user_message))
        messages = _history(conversation_id)

        client = _client()
        final_text_parts: list[str] = []
        stopped_cleanly = False
        stop_reason = None

        for _ in range(MAX_ITERATIONS):
            try:
                # SDK call is sync; run in thread to avoid blocking the event loop.
                response = await asyncio.to_thread(
                    client.messages.create,
                    model=settings.model,
                    max_tokens=settings.max_tokens,
                    system=SYSTEM_PROMPT,
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
            stop_reason = response.stop_reason

            # Emit one event per content block.
            custom_tool_uses: list[Any] = []
            turn_text_parts: list[str] = []
            for block in response.content:
                event = _block_to_event(block)
                if event:
                    yield {"type": event["type"], "task_id": task_id, "data": event}
                if getattr(block, "type", None) == "text":
                    turn_text_parts.append(block.text)
                if getattr(block, "type", None) == "tool_use":
                    custom_tool_uses.append(block)
            final_text_parts.extend(turn_text_parts)

            # Persist the full assistant turn (raw blocks for round-tripping).
            add_message(
                conversation_id,
                "assistant",
                "\n".join(turn_text_parts).strip(),
                api_blocks=json.dumps([_dump_block(b) for b in response.content]),
            )
            messages.append({"role": "assistant", "content": response.content})

            if response.stop_reason == "end_turn":
                stopped_cleanly = True
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
            add_message(
                conversation_id, "user", "", api_blocks=json.dumps(tool_results)
            )
            messages.append({"role": "user", "content": tool_results})

        if not stopped_cleanly:
            message = (
                f"Run stopped early (stop_reason={stop_reason}); the response may be incomplete."
                if stop_reason and stop_reason != "tool_use"
                else f"Run hit the {MAX_ITERATIONS}-iteration safety cap; the response may be incomplete."
            )
            yield {"type": "warning", "task_id": task_id, "data": {"message": message}}

        final_text = "\n".join(final_text_parts).strip() or "(no response)"
        yield {
            "type": "task_complete",
            "task_id": task_id,
            "data": {"final_text": final_text},
        }


def serialize_event(event: dict) -> str:
    return json.dumps(event, default=str)
