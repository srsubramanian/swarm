"""Decision endpoint — RM submits a decision to resume an interrupted graph."""

from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException
from langgraph.types import Command
from pydantic import BaseModel, Field

from app.agents.orchestrator import graph
from app.schemas.conversations import ConversationRecord, DecisionRecord
from app.services.store import conversation_store, thread_store

router = APIRouter(prefix="/api/decisions", tags=["decisions"])


class DecisionRequest(BaseModel):
    option_id: str = Field(description="ID of the selected action option")
    action: str = Field(description="One of: approve, reject, escalate, override")
    justification: str = Field(default="", description="RM justification for this decision")


@router.post("/{conversation_id}", response_model=ConversationRecord)
async def submit_decision(conversation_id: str, body: DecisionRequest) -> ConversationRecord:
    """RM submits a decision — resumes the interrupted graph."""
    record = conversation_store.get(conversation_id)
    if not record:
        raise HTTPException(status_code=404, detail="Conversation not found")

    if record.status != "awaiting_decision":
        raise HTTPException(
            status_code=400,
            detail=f"Conversation status is '{record.status}', not 'awaiting_decision'",
        )

    thread_id = thread_store.get(conversation_id)
    if not thread_id:
        raise HTTPException(status_code=404, detail="No thread found for this conversation")

    config = {"configurable": {"thread_id": thread_id}}
    decision_payload = body.model_dump()

    # Resume the graph from the interrupt point
    await graph.ainvoke(Command(resume=decision_payload), config=config)

    # Update the conversation record
    now = datetime.now(UTC).isoformat()
    record.action_required.status = "actioned"
    record.action_required.actioned_option = body.option_id
    record.status = "concluded"
    record.decision = DecisionRecord(
        option_id=body.option_id,
        action=body.action,
        justification=body.justification,
        decided_at=now,
    )
    conversation_store.save(record)
    return record
