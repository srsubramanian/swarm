"""History endpoints — list, get, and clear persisted conversations."""

from fastapi import APIRouter, HTTPException

from app.schemas.conversations import ConversationRecord
from app.services.store import conversation_store

router = APIRouter(prefix="/api/conversations", tags=["history"])


@router.get("", response_model=list[ConversationRecord])
async def list_conversations() -> list[ConversationRecord]:
    """Return all conversations, newest first."""
    return conversation_store.list_all()


@router.get("/{conversation_id}", response_model=ConversationRecord)
async def get_conversation(conversation_id: str) -> ConversationRecord:
    """Return a single conversation by ID."""
    record = conversation_store.get(conversation_id)
    if not record:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return record


@router.delete("")
async def clear_conversations() -> dict:
    """Clear all stored conversations. Returns count cleared."""
    count = conversation_store.clear()
    return {"cleared": count}
