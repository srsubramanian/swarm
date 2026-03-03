"""Event endpoints — webhook ingestion and simulator control."""

import uuid

from fastapi import APIRouter

from app.agents.orchestrator import event_graph
from app.api.conversations import build_input
from app.schemas.events import AnalyzeRequest
from app.services.conversation_builder import build_conversation
from app.services.event_source import event_simulator
from app.services.store import conversation_store, thread_store

router = APIRouter(prefix="/api/events", tags=["events"])


@router.post("/webhook")
async def webhook(req: AnalyzeRequest) -> dict:
    """Accept external events — runs through triage + full pipeline if needed."""
    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}

    result = await event_graph.ainvoke(build_input(req), config=config)

    triage = result.get("triage_result", "respond")
    conversation_id = None

    if triage == "respond" and result.get("analyses") and result.get("moderator_synthesis"):
        record = build_conversation(req, result["analyses"], result["moderator_synthesis"])
        conversation_store.save(record)
        thread_store.set(record.id, thread_id)
        conversation_id = record.id

    return {
        "triage_result": triage,
        "conversation_id": conversation_id,
    }


@router.post("/simulate/start")
async def start_simulator() -> dict:
    """Start the event simulator."""
    if event_simulator.running:
        return {"status": "already_running"}
    await event_simulator.start()
    return {"status": "started"}


@router.post("/simulate/stop")
async def stop_simulator() -> dict:
    """Stop the event simulator."""
    if not event_simulator.running:
        return {"status": "already_stopped"}
    await event_simulator.stop()
    return {"status": "stopped"}
