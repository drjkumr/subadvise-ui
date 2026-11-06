import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from threading import RLock
from uuid import UUID

from models import ChatMessage, ChatSession


class JSONChatHistoryManager:
    """Persist complete chat sessions as atomically replaced JSON files."""

    def __init__(self, storage_dir: str | Path) -> None:
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self._lock = RLock()

    def create_session(
        self,
        metadata: dict[str, str | int | float | bool | None] | None = None,
    ) -> ChatSession:
        """Create and persist a new empty session."""
        session = ChatSession(metadata=metadata or {})
        with self._lock:
            self._write_session(session)
        return session

    def get_session(self, session_id: UUID) -> ChatSession:
        """Load a session, raising FileNotFoundError if it does not exist."""
        path = self._session_path(session_id)
        with self._lock:
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except FileNotFoundError:
                raise
            except (json.JSONDecodeError, OSError) as exc:
                raise RuntimeError(f"Could not read chat session {session_id}.") from exc

        try:
            return ChatSession.model_validate(payload)
        except ValueError as exc:
            raise RuntimeError(f"Chat session {session_id} contains invalid data.") from exc

    def list_sessions(self) -> list[ChatSession]:
        """Load all valid session files in creation-time order."""
        with self._lock:
            paths = sorted(self.storage_dir.glob("*.json"))
        sessions = []
        for path in paths:
            try:
                session_id = UUID(path.stem)
                sessions.append(self.get_session(session_id))
            except (ValueError, FileNotFoundError):
                continue
        return sorted(sessions, key=lambda session: session.created_at)

    def append_message(
        self,
        session_id: UUID,
        role: str,
        content: str,
        metadata: dict[str, str | int | float | bool | None] | None = None,
    ) -> ChatMessage:
        """Append a message and atomically persist its containing session."""
        with self._lock:
            session = self.get_session(session_id)
            message = ChatMessage(
                session_id=session_id,
                role=role,
                content=content,
                metadata=metadata or {},
            )
            session.messages.append(message)
            session.updated_at = datetime.now(timezone.utc)
            self._write_session(session)
        return message

    def get_recent_messages(
        self,
        session_id: UUID,
        turns: int,
    ) -> list[ChatMessage]:
        """Return the messages from the most recent N user/assistant turns."""
        if turns < 0:
            raise ValueError("turns must be zero or greater.")
        messages = self.get_session(session_id).messages
        conversational = [message for message in messages if message.role != "system"]
        if turns == 0:
            return []
        user_turns = [
            index
            for index, message in enumerate(conversational)
            if message.role == "user"
        ]
        if len(user_turns) <= turns:
            return conversational
        return conversational[user_turns[-turns] :]

    def get_full_context(self, session_id: UUID) -> list[ChatMessage]:
        """Return all messages in their original order."""
        return self.get_session(session_id).messages

    def clear_messages(self, session_id: UUID) -> int:
        """Remove a session's messages while preserving its metadata."""
        with self._lock:
            session = self.get_session(session_id)
            deleted_count = len(session.messages)
            session.messages = []
            session.updated_at = datetime.now(timezone.utc)
            self._write_session(session)
        return deleted_count

    def delete_session(self, session_id: UUID) -> None:
        """Delete a session file."""
        with self._lock:
            self._session_path(session_id).unlink()

    def _session_path(self, session_id: UUID) -> Path:
        return self.storage_dir / f"{session_id}.json"

    def _write_session(self, session: ChatSession) -> None:
        path = self._session_path(session.session_id)
        payload = json.dumps(
            session.model_dump(mode="json"),
            ensure_ascii=False,
            indent=2,
        )
        file_descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{session.session_id}.",
            suffix=".tmp",
            dir=self.storage_dir,
        )
        try:
            with os.fdopen(file_descriptor, "w", encoding="utf-8") as temporary_file:
                temporary_file.write(payload)
                temporary_file.flush()
                os.fsync(temporary_file.fileno())
            os.replace(temporary_name, path)
        except OSError:
            try:
                os.unlink(temporary_name)
            except FileNotFoundError:
                pass
            raise
