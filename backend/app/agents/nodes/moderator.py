"""Moderator node — synthesizes all agent analyses."""

import json
from pathlib import Path

from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.llm import get_llm
from app.agents.schemas import ModeratorSynthesis
from app.agents.state import SwarmState

_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "moderator.md"


def _load_prompt() -> str:
    return _PROMPT_PATH.read_text()


def _format_analyses(state: SwarmState) -> str:
    parts = [
        f"## Event: {state['event_type']}",
        f"**Title:** {state['title']}",
        f"**Client:** {state['client_name']}",
        "",
        "---",
        "",
        "## Agent Analyses",
    ]

    for analysis in state["analyses"]:
        data = analysis.model_dump() if hasattr(analysis, "model_dump") else analysis
        parts.extend(
            [
                "",
                f"### {data['agent_role'].title()} Agent",
                f"**Position:** {data['position']}",
                f"**Risk Level:** {data['risk_level']}",
                f"**Confidence:** {data['confidence']}",
                "",
                data["analysis"],
                "",
                "**Key Findings:**",
            ]
        )
        for finding in data["key_findings"]:
            parts.append(f"- {finding}")
        parts.append(f"\n**Recommended Action:** {data['recommended_action']}")

    return "\n".join(parts)


async def moderator_node(state: SwarmState) -> dict:
    llm = get_llm()
    structured_llm = llm.with_structured_output(ModeratorSynthesis)
    result = await structured_llm.ainvoke(
        [
            SystemMessage(content=_load_prompt()),
            HumanMessage(content=_format_analyses(state)),
        ]
    )
    return {"moderator_synthesis": result}
