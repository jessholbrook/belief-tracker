# belief-tracker

A lean Claude-powered agent platform — chat with an autonomous AI that can search the web, run tools, and extract beliefs from text. Inspired by [Copilot Vibes](https://github.com), trimmed to a buildable starting point.

## What it does

- **Chat with an agent** that loops `plan → tool call → result` until it has an answer
- **Stream every step** to the UI over WebSocket — you see thinking, tool calls, and results in real time
- **Extract beliefs** from arbitrary text: pulls structured statements with confidence and supporting evidence
- **Persist conversations** in SQLite

## Tools the agent has

| Tool | Where it runs |
|---|---|
| `web_search` | Anthropic-hosted server-side tool |
| `web_fetch` | Anthropic-hosted server-side tool |
| `calculate` | Local — sandboxed `eval` over the `math` module |
| `current_datetime` | Local |

Add more in [`backend/app/agent.py`](backend/app/agent.py) — both Anthropic server-side tools and locally-executed custom tools work in the same loop.

## Stack

- **Backend** — Python 3.11 · FastAPI · SQLite · Anthropic SDK (`claude-sonnet-4-6`)
- **Frontend** — React 18 · TypeScript · Vite · Tailwind CSS
- **Real-time** — native WebSocket (FastAPI)

## Quick start

```bash
./setup.sh
# Edit backend/.env and set ANTHROPIC_API_KEY (get one at https://console.anthropic.com)
./start.sh
```

| Service | URL |
|---|---|
| Frontend | http://localhost:5173 |
| Backend | http://localhost:1337 |
| API docs | http://localhost:1337/docs |

To stop: Ctrl+C, or `./stop.sh` if anything's still bound to a port.

## Project layout

```
backend/app/
  main.py        FastAPI app + REST routes + WebSocket
  agent.py       Agent loop, tool definitions, custom tool execution
  beliefs.py     Belief extraction via Claude
  db.py          SQLite helpers (conversations, messages, beliefs)
  models.py      Pydantic request/response models
  config.py      Env-var settings

frontend/src/
  App.tsx        Top-level state + WebSocket handling
  api.ts         REST + WebSocket client
  components/    Sidebar, Composer, Message, TaskView, BeliefTracker
```

## Adding a tool

In [`backend/app/agent.py`](backend/app/agent.py), append to `CUSTOM_TOOLS` and add a branch in `execute_custom_tool`:

```python
CUSTOM_TOOLS.append({
    "name": "my_tool",
    "description": "What it does (Claude reads this)",
    "input_schema": {
        "type": "object",
        "properties": {"arg": {"type": "string"}},
        "required": ["arg"],
    },
})

def execute_custom_tool(name, tool_input):
    if name == "my_tool":
        return run_my_tool(tool_input["arg"]), False
    # ...
```

## Things that were intentionally skipped

This is a starting point, not a clone of the original. The following are TODOs:

- Authentication / multi-user
- File uploads + document generation (pptx/docx/xlsx)
- Playwright server-side browser automation
- Chrome extension for client-side browser control
- Recurring/scheduled tasks
- SMS notifications
- Sharing / public links
- Docker
