from __future__ import annotations

import asyncio
import logging
import re
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from . import beliefs, db
from .agent import run_agent, serialize_event
from .config import settings
from .models import (
    Belief,
    Conversation,
    ConversationWithMessages,
    CreateConversationRequest,
    ExtractBeliefsRequest,
    SendMessageRequest,
)


logging.basicConfig(level=settings.log_level)
log = logging.getLogger("belief-tracker")


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init_db()
    log.info("DB initialized at %s", settings.db_path)
    yield


app = FastAPI(title="belief-tracker", lifespan=lifespan)


@app.middleware("http")
async def require_auth(request: Request, call_next):
    """Optional shared-token auth: active only when API_AUTH_TOKEN is set."""
    if (
        settings.api_auth_token
        and request.url.path.startswith("/api")
        and request.url.path != "/api/health"
        and request.headers.get("authorization") != f"Bearer {settings.api_auth_token}"
    ):
        return JSONResponse({"detail": "Unauthorized"}, status_code=401)
    return await call_next(request)


# Added after the auth middleware so CORS is outermost — error responses
# (including 401s) still carry CORS headers.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origins_list,
    allow_origin_regex=settings.allowed_origin_regex,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _origin_allowed(origin: str) -> bool:
    if origin in settings.origins_list:
        return True
    if settings.allowed_origin_regex:
        return re.fullmatch(settings.allowed_origin_regex, origin) is not None
    return False


@app.get("/api/health")
def health() -> dict:
    return {"ok": True, "model": settings.model}


# ----- Conversations -----


@app.get("/api/conversations", response_model=list[Conversation])
def get_conversations():
    return db.list_conversations()


@app.post("/api/conversations", response_model=Conversation)
def post_conversation(body: CreateConversationRequest):
    return db.create_conversation(body.title)


@app.get("/api/conversations/{cid}", response_model=ConversationWithMessages)
def get_conversation(cid: str):
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


@app.get("/api/beliefs", response_model=list[Belief])
def get_beliefs():
    return beliefs.belief_tree()


@app.post("/api/beliefs/extract", response_model=list[Belief])
async def post_extract_beliefs(body: ExtractBeliefsRequest):
    if body.parent_belief and not db.get_belief(body.parent_belief):
        raise HTTPException(404, "Parent belief not found")
    return await beliefs.extract_beliefs(body.text, body.parent_belief)


@app.delete("/api/beliefs/{bid}")
def remove_belief(bid: str) -> dict:
    db.delete_belief(bid)
    return {"ok": True}


# ----- WebSocket: streaming agent run -----


@app.websocket("/ws/chat/{conversation_id}")
async def ws_chat(websocket: WebSocket, conversation_id: str) -> None:
    # CORS middleware does not cover WebSockets: enforce origin (for browsers)
    # and the shared token (for everyone) before accepting.
    origin = websocket.headers.get("origin")
    if origin and not _origin_allowed(origin):
        await websocket.close(code=4403, reason="Origin not allowed")
        return
    if (
        settings.api_auth_token
        and websocket.query_params.get("token") != settings.api_auth_token
    ):
        await websocket.close(code=4401, reason="Unauthorized")
        return

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
