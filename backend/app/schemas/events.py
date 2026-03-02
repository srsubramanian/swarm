"""API-facing Pydantic models for analyze endpoints.

Aligned with frontend types in frontend/src/types/index.ts.
"""

from typing import Any

from pydantic import BaseModel, Field


# --- Request ---


class AnalyzeRequest(BaseModel):
    event_type: str = Field(description="e.g. wire_transfer, velocity_alert")
    title: str = Field(description="Human-readable event title")
    client_name: str = Field(description="Client name")
    event_data: dict[str, Any] = Field(description="Arbitrary event payload")
    client_memory: str = Field(default="", description="Client memory markdown")


# --- Response models aligned with frontend types ---


class ActionOptionResponse(BaseModel):
    """Maps to frontend ActionOption."""

    id: str
    label: str
    variant: str  # primary | secondary | danger


class AgentAnalysisResponse(BaseModel):
    """Maps to frontend AgentInfo + Message content."""

    agent_role: str
    agent_name: str
    position: str
    analysis: str
    risk_level: str
    confidence: str
    key_findings: list[str]
    recommended_action: str


class ModeratorSynthesisResponse(BaseModel):
    """Maps to frontend ModeratorSummaryData."""

    status: str
    consensus: str
    dissent: str
    risk_level: str
    risk_assessment: str
    key_decisions: list[str]
    next_steps: list[str]
    action_items: list[ActionOptionResponse]


class AnalyzeResponse(BaseModel):
    """Full synchronous response from /api/analyze."""

    agents: list[AgentAnalysisResponse]
    moderator_summary: ModeratorSynthesisResponse
