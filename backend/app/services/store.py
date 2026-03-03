"""In-memory conversation store for demo use."""

from app.schemas.conversations import ConversationRecord


class InMemoryConversationStore:
    def __init__(self) -> None:
        self._data: dict[str, ConversationRecord] = {}

    def save(self, record: ConversationRecord) -> None:
        self._data[record.id] = record

    def get(self, conversation_id: str) -> ConversationRecord | None:
        return self._data.get(conversation_id)

    def list_all(self) -> list[ConversationRecord]:
        return sorted(
            self._data.values(),
            key=lambda r: r.started_at,
            reverse=True,
        )

    def clear(self) -> int:
        count = len(self._data)
        self._data.clear()
        return count


class ThreadStore:
    """Maps conversation_id → LangGraph thread_id for resuming interrupted graphs."""

    def __init__(self) -> None:
        self._data: dict[str, str] = {}

    def set(self, conversation_id: str, thread_id: str) -> None:
        self._data[conversation_id] = thread_id

    def get(self, conversation_id: str) -> str | None:
        return self._data.get(conversation_id)

    def clear(self) -> None:
        self._data.clear()


conversation_store = InMemoryConversationStore()
thread_store = ThreadStore()
