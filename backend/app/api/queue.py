"""Queue endpoints — submit pre-built scenarios by name."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.agents.scenarios import SCENARIOS
from app.api.conversations import analyze, analyze_stream

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


@router.post("")
async def queue_analyze(body: QueueRequest):
    """Submit a scenario by name — returns full sync result."""
    req = SCENARIOS.get(body.scenario)
    if not req:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown scenario '{body.scenario}'. Available: {list(SCENARIOS.keys())}",
        )
    return await analyze(req)


@router.post("/stream")
async def queue_stream(body: QueueRequest):
    """Submit a scenario by name — returns SSE stream."""
    req = SCENARIOS.get(body.scenario)
    if not req:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown scenario '{body.scenario}'. Available: {list(SCENARIOS.keys())}",
        )
    return await analyze_stream(req)
