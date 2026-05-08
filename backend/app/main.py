from __future__ import annotations

import asyncio
import logging

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from . import beliefs, db
from .agent import run_agent, serialize_event
from .config import settings
from .models import (
    CreateConversationRequest,
    ExtractBeliefsRequest,
    SendMessageRequest,
)


logging.basicConfig(level=settings.log_level)
log = logging.getLogger("belief-tracker")

app = FastAPI(title="belief-tracker")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def _startup() -> None:
    db.init_db()
    log.info("DB initialized at %s", settings.db_path)


@app.get("/api/health")
def health() -> dict:
    return {"ok": True, "model": settings.model}


# ----- Conversations -----


@app.get("/api/conversations")
def get_conversations() -> list[dict]:
    return db.list_conversations()


@app.post("/api/conversations")
def post_conversation(body: CreateConversationRequest) -> dict:
    return db.create_conversation(body.title)


@app.get("/api/conversations/{cid}")
def get_conversation(cid: str) -> dict:
    conv = db.get_conversation(cid)
    if not conv:
        raise HTTPException(404, "Conversation not found")
    conv["messages"] = db.list_messages(cid)
    return conv


@app.delete("/api/conversations/{cid}")
def remove_conversation(cid: str) -> dict:
    db.delete_conversation(cid)
    return {"ok": True}


# ----- Messages (HTTP fallback; primary path is the WebSocket below) -----


@app.post("/api/conversations/{cid}/messages")
async def post_message(cid: str, body: SendMessageRequest) -> dict:
    if not db.get_conversation(cid):
        raise HTTPException(404, "Conversation not found")
    events = []
    async for event in run_agent(cid, body.content):
        events.append(event)
    return {"events": events}


# ----- Beliefs -----


@app.get("/api/beliefs")
def get_beliefs() -> list[dict]:
    return beliefs.belief_tree()


@app.post("/api/beliefs/extract")
async def post_extract_beliefs(body: ExtractBeliefsRequest) -> list[dict]:
    return await beliefs.extract_beliefs(body.text, body.parent_belief)


@app.delete("/api/beliefs/{bid}")
def remove_belief(bid: str) -> dict:
    db.delete_belief(bid)
    return {"ok": True}


# ----- WebSocket: streaming agent run -----


@app.websocket("/ws/chat/{conversation_id}")
async def ws_chat(websocket: WebSocket, conversation_id: str) -> None:
    await websocket.accept()
    if not db.get_conversation(conversation_id):
        await websocket.send_text(
            serialize_event(
                {
                    "type": "error",
                    "task_id": "",
                    "data": {"message": "Conversation not found"},
                }
            )
        )
        await websocket.close()
        return

    try:
        while True:
            msg = await websocket.receive_json()
            if msg.get("type") != "user_message":
                continue
            content = msg.get("content", "").strip()
            if not content:
                continue
            try:
                async for event in run_agent(conversation_id, content):
                    await websocket.send_text(serialize_event(event))
            except Exception as e:  # noqa: BLE001
                log.exception("agent run failed")
                await websocket.send_text(
                    serialize_event(
                        {
                            "type": "error",
                            "task_id": "",
                            "data": {"message": str(e)},
                        }
                    )
                )
    except WebSocketDisconnect:
        pass
    except asyncio.CancelledError:
        raise
