"""Queue endpoints — submit pre-built scenarios by name, persist results."""

import json
import uuid
from collections.abc import AsyncGenerator

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

from app.agents.orchestrator import graph
from app.agents.scenarios import SCENARIOS
from app.api.conversations import analysis_to_response, build_input, synthesis_to_response
from app.schemas.conversations import ConversationRecord
from app.services.conversation_builder import build_conversation
from app.services.store import conversation_store, thread_store

router = APIRouter(prefix="/api/queue", tags=["queue"])


class QueueRequest(BaseModel):
    scenario: str = Field(description="Scenario name, e.g. 'wire_transfer'")


class ScenarioInfo(BaseModel):
    name: str
    title: str
    client_name: str
    event_type: str


@router.get("/scenarios", response_model=list[ScenarioInfo])
async def list_scenarios() -> list[ScenarioInfo]:
    """List all available mock scenarios."""
    return [
        ScenarioInfo(
            name=name,
            title=req.title,
            client_name=req.client_name,
            event_type=req.event_type,
        )
        for name, req in SCENARIOS.items()
    ]


@router.post("", response_model=ConversationRecord)
async def queue_analyze(body: QueueRequest) -> ConversationRecord:
    """Submit a scenario by name — runs pipeline, pauses at interrupt, returns conversation."""
    req = SCENARIOS.get(body.scenario)
    if not req:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown scenario '{body.scenario}'. Available: {list(SCENARIOS.keys())}",
        )

    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}
    inp = build_input(req)

    # Graph will run until interrupt() in await_decision node
    result = await graph.ainvoke(inp, config=config)

    record = build_conversation(req, result["analyses"], result["moderator_synthesis"])
    conversation_store.save(record)
    thread_store.set(record.id, thread_id)
    return record


async def _queue_event_generator(
    body: QueueRequest,
) -> AsyncGenerator[dict, None]:
    """Yield SSE events as the graph executes, then persist the result."""
    req = SCENARIOS.get(body.scenario)
    if not req:
        raise

    yield {"event": "start", "data": json.dumps({"status": "processing"})}

    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}

    analyses = []
    synthesis = None

    async for event in graph.astream(build_input(req), config=config, stream_mode="updates"):
        for node_name, node_output in event.items():
            if node_name in ("compliance", "security", "engineering"):
                for analysis in node_output.get("analyses", []):
                    analyses.append(analysis)
                    resp = analysis_to_response(analysis)
                    yield {
                        "event": "agent_complete",
                        "data": resp.model_dump_json(),
                    }
            elif node_name == "moderator":
                synthesis = node_output.get("moderator_synthesis")
                if synthesis:
                    resp = synthesis_to_response(synthesis)
                    yield {
                        "event": "moderator_complete",
                        "data": resp.model_dump_json(),
                    }

    conversation_id = None
    if analyses and synthesis:
        record = build_conversation(req, analyses, synthesis)
        conversation_store.save(record)
        thread_store.set(record.id, thread_id)
        conversation_id = record.id

    yield {
        "event": "done",
        "data": json.dumps({"status": "complete", "conversation_id": conversation_id}),
    }


@router.post("/stream")
async def queue_stream(body: QueueRequest):
    """Submit a scenario by name — returns SSE stream, persists result."""
    req = SCENARIOS.get(body.scenario)
    if not req:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown scenario '{body.scenario}'. Available: {list(SCENARIOS.keys())}",
        )
    return EventSourceResponse(_queue_event_generator(body))
