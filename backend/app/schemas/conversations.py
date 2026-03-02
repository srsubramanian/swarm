"""Conversation models matching frontend/src/types/index.ts (camelCase JSON)."""

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class _CamelModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )


class AgentInfoRecord(_CamelModel):
    role: str
    name: str
    status: str  # "analyzing" | "complete"
    position: str


class MessageRecord(_CamelModel):
    id: str
    agent_role: str  # "compliance" | "security" | "engineering" | "moderator"
    agent_name: str
    content: str
    timestamp: str


class ActionOptionRecord(_CamelModel):
    id: str
    label: str
    variant: str  # "primary" | "secondary" | "danger"


class ActionRequiredRecord(_CamelModel):
    status: str  # "pending" | "actioned"
    options: list[ActionOptionRecord]
    actioned_option: str | None = None


class ClientMemoryRecord(_CamelModel):
    client_name: str
    content: str
    last_updated: str


class ModeratorSummaryRecord(_CamelModel):
    status: str
    consensus: str
    key_decisions: list[str]
    risk_assessment: str
    next_steps: list[str]


class ConversationRecord(_CamelModel):
    id: str
    title: str
    client_name: str
    risk_level: str
    status: str  # "live" | "awaiting_decision" | "concluded"
    event_type: str
    started_at: str
    message_count: int
    agents: list[AgentInfoRecord]
    messages: list[MessageRecord]
    moderator_summary: ModeratorSummaryRecord
    action_required: ActionRequiredRecord
    client_memory: ClientMemoryRecord
