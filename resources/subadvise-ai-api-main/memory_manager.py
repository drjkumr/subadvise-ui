from pathlib import Path
from uuid import UUID

from json_store import JSONChatHistoryManager
from models import ChatMessage, ChatSearchResult, ChatSession, HybridChatContext
from vector_store import VectorChatHistoryStore


class HybridChatMemory:
    """Coordinate JSON conversation history and semantic vector memory."""

    def __init__(
        self,
        json_store: JSONChatHistoryManager,
        vector_store: VectorChatHistoryStore,
    ) -> None:
        self.json_store = json_store
        self.vector_store = vector_store

    @classmethod
    def from_paths(
        cls,
        history_dir: str | Path,
        vector_dir: str | Path,
    ) -> "HybridChatMemory":
        """Create the JSON and Chroma stores at the supplied local paths."""
        return cls(
            json_store=JSONChatHistoryManager(history_dir),
            vector_store=VectorChatHistoryStore(vector_dir),
        )

    def create_session(
        self,
        metadata: dict[str, str | int | float | bool | None] | None = None,
    ) -> ChatSession:
        """Create a new JSON-backed chat session."""
        return self.json_store.create_session(metadata)

    def get_session(self, session_id: UUID) -> ChatSession:
        """Return a session and its complete ordered history."""
        return self.json_store.get_session(session_id)

    def append_message(
        self,
        session_id: UUID,
        role: str,
        content: str,
        metadata: dict[str, str | int | float | bool | None] | None = None,
    ) -> ChatMessage:
        """Persist a message to JSON and upsert it into the vector index."""
        message = self.json_store.append_message(
            session_id,
            role,
            content,
            metadata,
        )
        self.vector_store.upsert_message(message)
        return message

    def get_context(
        self,
        session_id: UUID,
        query_text: str,
        recent_turns: int = 6,
        relevant_top_k: int = 5,
    ) -> HybridChatContext:
        """Combine recent full history with non-recent semantic matches."""
        recent = self.json_store.get_recent_messages(session_id, recent_turns)
        relevant = self.vector_store.query_history(
            query_text,
            session_id=session_id,
            top_k=relevant_top_k + len(recent),
        )
        recent_ids = {message.message_id for message in recent}
        relevant = [
            result for result in relevant
            if result.message.message_id not in recent_ids
        ]
        return HybridChatContext(
            recent_history=recent,
            relevant_context=relevant,
        )

    def search_history(
        self,
        query_text: str,
        session_id: UUID | None = None,
        top_k: int = 5,
    ) -> list[ChatSearchResult]:
        """Search all indexed messages or filter the search to one session."""
        return self.vector_store.query_history(query_text, session_id, top_k)

    def reindex_history(self) -> int:
        """Upsert all JSON-persisted messages into ChromaDB and return the count."""
        messages = [
            message
            for session in self.json_store.list_sessions()
            for message in session.messages
        ]
        for message in messages:
            self.vector_store.upsert_message(message)
        return len(messages)

    def clear_chat_history(self, session_id: UUID) -> int:
        """Clear the JSON transcript while preserving its session metadata."""
        return self.json_store.clear_messages(session_id)

    def clear_context(self, session_id: UUID) -> int:
        """Clear semantic context for an existing session."""
        self.json_store.get_session(session_id)
        return self.vector_store.delete_session(session_id)

    def clear_all(self, session_id: UUID) -> tuple[int, int]:
        """Clear an existing session's JSON transcript and semantic context."""
        self.json_store.get_session(session_id)
        deleted_messages = self.json_store.clear_messages(session_id)
        deleted_context_items = self.vector_store.delete_session(session_id)
        return deleted_messages, deleted_context_items

    def delete_session(self, session_id: UUID) -> None:
        """Delete a session and its associated semantic context."""
        self.json_store.get_session(session_id)
        self.vector_store.delete_session(session_id)
        self.json_store.delete_session(session_id)
