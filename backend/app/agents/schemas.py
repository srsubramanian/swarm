"""Pydantic models for structured LLM output from agents and moderator."""

import re

from pydantic import BaseModel, Field, field_validator


def _coerce_to_list(v: object) -> list[str]:
    """LLMs sometimes return a bullet-point string instead of a JSON array."""
    if isinstance(v, list):
        return v
    if isinstance(v, str):
        lines = re.split(r"\n(?:[•\-\*]\s*|\d+\.\s*)", v)
        # First element may start with a bullet too
        first = re.sub(r"^[•\-\*]\s*", "", lines[0])
        return [l.strip() for l in [first, *lines[1:]] if l.strip()]
    return [str(v)]


class AgentAnalysis(BaseModel):
    """Structured output from a single domain agent."""

    agent_role: str = Field(description="One of: compliance, security, engineering")
    position: str = Field(description="One-sentence position statement")
    analysis: str = Field(description="Detailed analysis in markdown")
    risk_level: str = Field(description="One of: critical, high, medium, low")
    confidence: str = Field(description="One of: high, medium, low")
    key_findings: list[str] = Field(description="2-5 key findings as a JSON array of strings")
    recommended_action: str = Field(description="Specific recommended next step")

    @field_validator("key_findings", mode="before")
    @classmethod
    def coerce_key_findings(cls, v: object) -> list[str]:
        return _coerce_to_list(v)


class ActionItem(BaseModel):
    """A concrete action the RM can take."""

    label: str = Field(description="Short action label, e.g. 'Hold Transfer'")
    variant: str = Field(
        description="One of: primary (recommended), secondary, danger"
    )
    rationale: str = Field(description="One-sentence reason for this option")


class ModeratorSynthesis(BaseModel):
    """Structured output from the moderator node."""

    status: str = Field(description="Overall status, e.g. 'HOLD RECOMMENDED'")
    consensus: str = Field(description="Where agents agree")
    dissent: str = Field(
        description="Where agents disagree, or 'None' if full consensus"
    )
    risk_level: str = Field(description="Overall risk: critical, high, medium, low")
    risk_assessment: str = Field(description="Brief risk justification")
    key_decisions: list[str] = Field(description="1-3 most important findings for RM as a JSON array of strings")
    next_steps: list[str] = Field(description="Concrete next steps as a JSON array of strings")
    action_items: list[ActionItem] = Field(description="2-4 actions for the RM queue")

    @field_validator("key_decisions", "next_steps", mode="before")
    @classmethod
    def coerce_lists(cls, v: object) -> list[str]:
        return _coerce_to_list(v)
