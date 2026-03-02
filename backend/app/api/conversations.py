"""Analyze endpoints — sync and SSE streaming."""

import json
import uuid
from collections.abc import AsyncGenerator

from fastapi import APIRouter
from sse_starlette.sse import EventSourceResponse

from app.agents.orchestrator import graph
from app.agents.schemas import AgentAnalysis, ModeratorSynthesis
from app.schemas.events import (
    ActionOptionResponse,
    AgentAnalysisResponse,
    AnalyzeRequest,
    AnalyzeResponse,
    ModeratorSynthesisResponse,
)

router = APIRouter(prefix="/api", tags=["analyze"])

_AGENT_NAMES = {
    "compliance": "Compliance Analyst",
    "security": "Security Analyst",
    "engineering": "Platform Engineer",
}


def analysis_to_response(a: AgentAnalysis) -> AgentAnalysisResponse:
    return AgentAnalysisResponse(
        agent_role=a.agent_role,
        agent_name=_AGENT_NAMES.get(a.agent_role, a.agent_role),
        position=a.position,
        analysis=a.analysis,
        risk_level=a.risk_level,
        confidence=a.confidence,
        key_findings=a.key_findings,
        recommended_action=a.recommended_action,
    )


def synthesis_to_response(s: ModeratorSynthesis) -> ModeratorSynthesisResponse:
    return ModeratorSynthesisResponse(
        status=s.status,
        consensus=s.consensus,
        dissent=s.dissent,
        risk_level=s.risk_level,
        risk_assessment=s.risk_assessment,
        key_decisions=s.key_decisions,
        next_steps=s.next_steps,
        action_items=[
            ActionOptionResponse(
                id=str(uuid.uuid4()),
                label=item.label,
                variant=item.variant,
            )
            for item in s.action_items
        ],
    )


def build_input(req: AnalyzeRequest) -> dict:
    return {
        "event_type": req.event_type,
        "title": req.title,
        "client_name": req.client_name,
        "event_data": req.event_data,
        "client_memory": req.client_memory,
        "analyses": [],
        "moderator_synthesis": None,
    }


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze(req: AnalyzeRequest) -> AnalyzeResponse:
    """Run all agents synchronously and return the full result."""
    result = await graph.ainvoke(build_input(req))

    agents = [analysis_to_response(a) for a in result["analyses"]]
    moderator = synthesis_to_response(result["moderator_synthesis"])

    return AnalyzeResponse(agents=agents, moderator_summary=moderator)


async def _event_generator(req: AnalyzeRequest) -> AsyncGenerator[dict, None]:
    """Yield SSE events as the graph executes."""
    yield {"event": "start", "data": json.dumps({"status": "processing"})}

    async for event in graph.astream(build_input(req), stream_mode="updates"):
        for node_name, node_output in event.items():
            if node_name in ("compliance", "security", "engineering"):
                analyses = node_output.get("analyses", [])
                for analysis in analyses:
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

    yield {"event": "done", "data": json.dumps({"status": "complete"})}


@router.post("/analyze/stream")
async def analyze_stream(req: AnalyzeRequest) -> EventSourceResponse:
    """Stream agent results as SSE events."""
    return EventSourceResponse(_event_generator(req))
