from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


Role = Literal["user", "assistant"]


class Message(BaseModel):
    id: str
    conversation_id: str
    role: Role
    content: str
    created_at: datetime


class Conversation(BaseModel):
    id: str
    title: str
    created_at: datetime
    updated_at: datetime


class ConversationWithMessages(Conversation):
    messages: list[Message] = Field(default_factory=list)


class CreateConversationRequest(BaseModel):
    title: str = "New conversation"


class SendMessageRequest(BaseModel):
    content: str


class ExtractBeliefsRequest(BaseModel):
    text: str
    parent_belief: str | None = None


class Belief(BaseModel):
    id: str
    parent_id: str | None = None
    statement: str
    confidence: Literal["high", "medium", "low"]
    evidence: str = ""
    created_at: datetime
    children: list["Belief"] = Field(default_factory=list)


Belief.model_rebuild()


class AgentEvent(BaseModel):
    type: Literal[
        "task_started",
        "assistant_text",
        "tool_use",
        "tool_result",
        "warning",
        "task_complete",
        "error",
    ]
    task_id: str
    data: dict[str, Any] = Field(default_factory=dict)
