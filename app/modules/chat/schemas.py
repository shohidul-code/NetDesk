import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ChatMessageCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    content: str = Field(min_length=1, max_length=1000)


class SessionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    created_at: datetime
    updated_at: datetime


class MessageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    role: str
    content: str
    tools_used: list[dict[str, Any]]
    sources: list[dict[str, Any]]
    created_at: datetime


class ToolUse(BaseModel):
    name: str
    ok: bool


class Source(BaseModel):
    ref: str
    document_slug: str
    title: str


class TokenUsage(BaseModel):
    input_tokens: int
    output_tokens: int


class ChatReply(BaseModel):
    """PROPOSAL §8.2, plus messages_left_today for the assistant page (§11.2)."""

    message_id: uuid.UUID
    content: str
    tools_used: list[ToolUse]
    sources: list[Source]
    usage: TokenUsage
    messages_left_today: int
