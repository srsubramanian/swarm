"""Security agent node."""

import json
from pathlib import Path

from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.llm import get_llm
from app.agents.schemas import AgentAnalysis
from app.agents.state import SwarmState

_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "security.md"


def _load_prompt() -> str:
    return _PROMPT_PATH.read_text()


def _format_event(state: SwarmState) -> str:
    parts = [
        f"## Event: {state['event_type']}",
        f"**Title:** {state['title']}",
        f"**Client:** {state['client_name']}",
        "",
        "### Event Data",
        "```json",
        json.dumps(state["event_data"], indent=2, default=str),
        "```",
    ]

    if state.get("client_memory"):
        parts.extend(["", "### Client Memory", state["client_memory"]])

    return "\n".join(parts)


async def security_agent(state: SwarmState) -> dict:
    llm = get_llm()
    structured_llm = llm.with_structured_output(AgentAnalysis)
    result = await structured_llm.ainvoke(
        [
            SystemMessage(content=_load_prompt()),
            HumanMessage(content=_format_event(state)),
        ]
    )
    result.agent_role = "security"
    return {"analyses": [result]}
