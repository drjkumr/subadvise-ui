from datetime import datetime, timezone
from typing import Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


class ChatMessage(BaseModel):
    """One timestamped message belonging to a chat session."""

    model_config = ConfigDict(extra="forbid")

    message_id: UUID = Field(default_factory=uuid4)
    session_id: UUID
    role: Literal["user", "assistant", "system"]
    content: str = Field(min_length=1)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, str | int | float | bool | None] = Field(default_factory=dict)


class ChatSession(BaseModel):
    """A persisted chat thread with ordered messages and session metadata."""

    model_config = ConfigDict(extra="forbid")

    session_id: UUID = Field(default_factory=uuid4)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    messages: list[ChatMessage] = Field(default_factory=list)
    metadata: dict[str, str | int | float | bool | None] = Field(default_factory=dict)


class ChatSessionCreated(BaseModel):
    """The identifiers returned when a new chat session is created."""

    session_id: UUID
    created_at: datetime


class ChatSearchResult(BaseModel):
    """A message returned by vector search and its cosine distance."""

    message: ChatMessage
    distance: float


class HybridChatContext(BaseModel):
    """Recent short-term history combined with relevant older messages."""

    recent_history: list[ChatMessage]
    relevant_context: list[ChatSearchResult]
