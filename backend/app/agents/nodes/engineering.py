"""Engineering agent node — deep agent with tool use."""

import json
from pathlib import Path

from app.agents.state import SwarmState
from app.agents.tool_loop import run_agent_with_tools
from app.agents.tools import ENGINEERING_TOOLS

_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "engineering.md"


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


async def engineering_agent(state: SwarmState) -> dict:
    return await run_agent_with_tools(
        state=state,
        agent_role="engineering",
        system_prompt=_load_prompt(),
        event_message=_format_event(state),
        tools=ENGINEERING_TOOLS,
    )
