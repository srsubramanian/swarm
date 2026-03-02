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


conversation_store = InMemoryConversationStore()
