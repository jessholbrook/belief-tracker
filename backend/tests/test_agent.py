import asyncio
import json
from types import SimpleNamespace

import app.agent as agent
from app import db


def _resp(blocks, stop_reason):
    return SimpleNamespace(content=blocks, stop_reason=stop_reason)


def _text(text):
    return SimpleNamespace(type="text", text=text)


def _tool_use(id, name, input):
    return SimpleNamespace(type="tool_use", id=id, name=name, input=input)


class FakeClient:
    def __init__(self, responses):
        self.calls = []
        self._responses = list(responses)
        self.messages = SimpleNamespace(create=self._create)

    def _create(self, **kwargs):
        # Snapshot: run_agent mutates its messages list after the call.
        self.calls.append({**kwargs, "messages": list(kwargs["messages"])})
        return self._responses.pop(0)


def collect(gen):
    async def _run():
        return [e async for e in gen]

    return asyncio.run(_run())


def _run_calc_conversation(monkeypatch):
    """One agent run that calls `calculate` then answers."""
    conv = db.create_conversation("New conversation")
    fake = FakeClient(
        [
            _resp(
                [_tool_use("tu_1", "calculate", {"expression": "2+2"})], "tool_use"
            ),
            _resp([_text("The answer is 4.")], "end_turn"),
        ]
    )
    monkeypatch.setattr(agent, "_client", lambda: fake)
    events = collect(agent.run_agent(conv["id"], "what is 2+2?"))
    return conv, fake, events


def test_agent_tool_loop(test_db, monkeypatch):
    conv, fake, events = _run_calc_conversation(monkeypatch)

    assert [e["type"] for e in events] == [
        "task_started",
        "tool_use",
        "tool_result",
        "assistant_text",
        "task_complete",
    ]
    assert events[-1]["data"]["final_text"] == "The answer is 4."

    # The tool actually executed.
    tool_result = next(e for e in events if e["type"] == "tool_result")
    assert tool_result["data"]["content"] == "4"
    assert tool_result["data"]["is_error"] is False


def test_first_message_titles_conversation(test_db, monkeypatch):
    conv, _, _ = _run_calc_conversation(monkeypatch)
    assert db.get_conversation(conv["id"])["title"] == "what is 2+2?"


def test_turns_persist_raw_blocks(test_db, monkeypatch):
    conv, _, _ = _run_calc_conversation(monkeypatch)

    msgs = db.list_messages(conv["id"])
    assert [m["role"] for m in msgs] == ["user", "assistant", "user", "assistant"]
    assert json.loads(msgs[1]["api_blocks"])[0]["type"] == "tool_use"
    assert json.loads(msgs[2]["api_blocks"])[0]["type"] == "tool_result"
    # The tool-result turn is an API artifact, not UI content.
    assert msgs[2]["content"] == ""


def test_history_round_trips_tool_blocks(test_db, monkeypatch):
    """A follow-up run must see the prior turn's tool calls, not just text."""
    conv, _, _ = _run_calc_conversation(monkeypatch)

    fake2 = FakeClient([_resp([_text("Still 4.")], "end_turn")])
    monkeypatch.setattr(agent, "_client", lambda: fake2)
    collect(agent.run_agent(conv["id"], "you sure?"))

    sent = fake2.calls[0]["messages"]
    assert len(sent) == 5  # user, assistant(tool_use), user(tool_result), assistant, user
    assert sent[1]["content"][0]["name"] == "calculate"
    assert sent[2]["content"][0]["type"] == "tool_result"
    assert sent[4] == {"role": "user", "content": "you sure?"}


def test_warning_on_early_stop(test_db, monkeypatch):
    conv = db.create_conversation("New conversation")
    fake = FakeClient([_resp([_text("Truncated ans")], "max_tokens")])
    monkeypatch.setattr(agent, "_client", lambda: fake)

    events = collect(agent.run_agent(conv["id"], "hi"))
    warning = next(e for e in events if e["type"] == "warning")
    assert "max_tokens" in warning["data"]["message"]
    assert events[-1]["type"] == "task_complete"


def test_derive_title_truncates():
    assert agent._derive_title("short") == "short"
    long = "word " * 30
    title = agent._derive_title(long)
    assert len(title) <= 60
    assert title.endswith("…")
