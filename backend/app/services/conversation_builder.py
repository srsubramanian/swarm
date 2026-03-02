"""Build a ConversationRecord from graph inputs and outputs."""

import uuid
from datetime import UTC, datetime

from app.agents.schemas import AgentAnalysis, ModeratorSynthesis
from app.schemas.conversations import (
    ActionOptionRecord,
    ActionRequiredRecord,
    AgentInfoRecord,
    ClientMemoryRecord,
    ConversationRecord,
    MessageRecord,
    ModeratorSummaryRecord,
)
from app.schemas.events import AnalyzeRequest

_AGENT_NAMES = {
    "compliance": "Compliance Analyst",
    "security": "Security Analyst",
    "engineering": "Platform Engineer",
}


def build_conversation(
    req: AnalyzeRequest,
    analyses: list[AgentAnalysis],
    synthesis: ModeratorSynthesis,
) -> ConversationRecord:
    now = datetime.now(UTC).isoformat()

    agents = [
        AgentInfoRecord(
            role=a.agent_role,
            name=_AGENT_NAMES.get(a.agent_role, a.agent_role),
            status="complete",
            position=a.position,
        )
        for a in analyses
    ]

    messages = [
        MessageRecord(
            id=str(uuid.uuid4()),
            agent_role=a.agent_role,
            agent_name=_AGENT_NAMES.get(a.agent_role, a.agent_role),
            content=a.analysis,
            timestamp=now,
        )
        for a in analyses
    ]

    consensus = synthesis.consensus
    if synthesis.dissent and synthesis.dissent.lower() != "none":
        consensus += f"\n\n**Dissent:** {synthesis.dissent}"

    moderator_summary = ModeratorSummaryRecord(
        status=synthesis.status,
        consensus=consensus,
        key_decisions=synthesis.key_decisions,
        risk_assessment=synthesis.risk_assessment,
        next_steps=synthesis.next_steps,
    )

    action_required = ActionRequiredRecord(
        status="pending",
        options=[
            ActionOptionRecord(
                id=str(uuid.uuid4()),
                label=item.label,
                variant=item.variant,
            )
            for item in synthesis.action_items
        ],
    )

    client_memory = ClientMemoryRecord(
        client_name=req.client_name,
        content=req.client_memory or "",
        last_updated=now,
    )

    return ConversationRecord(
        id=str(uuid.uuid4()),
        title=req.title,
        client_name=req.client_name,
        risk_level=synthesis.risk_level,
        status="awaiting_decision",
        event_type=req.event_type,
        started_at=now,
        message_count=len(messages),
        agents=agents,
        messages=messages,
        moderator_summary=moderator_summary,
        action_required=action_required,
        client_memory=client_memory,
    )
