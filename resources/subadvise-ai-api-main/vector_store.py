import json
from pathlib import Path
from uuid import UUID

import chromadb

from models import ChatMessage, ChatSearchResult


class VectorChatHistoryStore:
    """Persist and semantically search chat messages with local ChromaDB."""

    def __init__(self, storage_dir: str | Path) -> None:
        path = Path(storage_dir)
        path.mkdir(parents=True, exist_ok=True)
        try:
            self._client = chromadb.PersistentClient(path=str(path))
            self._collection = self._client.get_or_create_collection(
                name="subadvise_chat_history",
                metadata={"hnsw:space": "cosine"},
            )
        except Exception as exc:
            raise RuntimeError("Could not initialize the local chat vector store.") from exc

    def upsert_message(self, message: ChatMessage) -> None:
        """Index or replace one message; message IDs make writes idempotent."""
        try:
            self._collection.upsert(
                ids=[str(message.message_id)],
                documents=[message.content],
                metadatas=[
                    {
                        "session_id": str(message.session_id),
                        "role": message.role,
                        "timestamp": message.timestamp.isoformat(),
                        "message_id": str(message.message_id),
                        "message_metadata": json.dumps(message.metadata),
                    }
                ],
            )
        except Exception as exc:
            raise RuntimeError(
                f"Could not index chat message {message.message_id}."
            ) from exc

    def query_history(
        self,
        query_text: str,
        session_id: UUID | None = None,
        top_k: int = 5,
    ) -> list[ChatSearchResult]:
        """Return the closest prior messages, optionally restricted to a session."""
        if not query_text.strip():
            raise ValueError("query_text must not be empty.")
        if top_k < 1:
            raise ValueError("top_k must be at least one.")

        try:
            count = self._collection.count()
            if count == 0:
                return []
            query: dict[str, object] = {
                "query_texts": [query_text],
                "n_results": min(top_k, count),
                "include": ["documents", "metadatas", "distances"],
            }
            if session_id is not None:
                query["where"] = {"session_id": str(session_id)}
                matching = self._collection.get(
                    where={"session_id": str(session_id)},
                    include=["metadatas"],
                )
                match_count = len(matching["ids"])
                if match_count == 0:
                    return []
                query["n_results"] = min(top_k, match_count)
            result = self._collection.query(**query)
        except Exception as exc:
            raise RuntimeError("Could not query the chat vector store.") from exc

        ids = result["ids"][0]
        documents = result["documents"][0] or []
        metadatas = result["metadatas"][0] or []
        distances = result["distances"][0] or []
        results = []
        for message_id, document, metadata, distance in zip(
            ids,
            documents,
            metadatas,
            distances,
        ):
            results.append(
                ChatSearchResult(
                    message=ChatMessage(
                        message_id=UUID(message_id),
                        session_id=UUID(metadata["session_id"]),
                        role=metadata["role"],
                        content=document,
                        timestamp=metadata["timestamp"],
                        metadata=json.loads(metadata.get("message_metadata", "{}")),
                    ),
                    distance=distance,
                )
            )
        return results

    def delete_session(self, session_id: UUID) -> int:
        """Delete and count all indexed messages belonging to a session."""
        try:
            result = self._collection.get(
                where={"session_id": str(session_id)},
                include=["metadatas"],
            )
            message_ids = result["ids"]
            if message_ids:
                self._collection.delete(ids=message_ids)
        except Exception as exc:
            raise RuntimeError(
                f"Could not clear chat context for session {session_id}."
            ) from exc
        return len(message_ids)
