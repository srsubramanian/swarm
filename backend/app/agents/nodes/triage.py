"""Triage router node — classifies events by urgency."""

import json
import logging
from enum import Enum
from pathlib import Path
from typing import Union

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.types import Send
from pydantic import BaseModel, Field

from app.agents.llm import get_llm
from app.agents.state import SwarmState

logger = logging.getLogger(__name__)

_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "triage.md"


def _load_prompt() -> str:
    return _PROMPT_PATH.read_text()


class TriageClassification(str, Enum):
    respond = "respond"
    notify = "notify"
    ignore = "ignore"


class TriageResult(BaseModel):
    classification: TriageClassification = Field(
        description="One of: respond, notify, ignore"
    )
    reasoning: str = Field(description="Brief explanation for the classification")


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


async def triage_router(state: SwarmState) -> dict:
    """Classify event urgency using LLM."""
    llm = get_llm()
    structured_llm = llm.with_structured_output(TriageResult)
    messages = [
        SystemMessage(content=_load_prompt()),
        HumanMessage(content=_format_event(state)),
    ]
    result = await structured_llm.ainvoke(messages)
    logger.info(
        "Triage for '%s': %s — %s",
        state["title"],
        result.classification.value,
        result.reasoning,
    )
    return {"triage_result": result.classification.value}


def triage_edge(state: SwarmState) -> Union[str, list[Send]]:
    """Conditional edge: fan-out to 3 agents for 'respond', or single node for others."""
    classification = state.get("triage_result", "respond")
    if classification == "respond":
        return [
            Send("compliance", state),
            Send("security", state),
            Send("engineering", state),
        ]
    elif classification == "notify":
        return "notify_rm"
    else:  # "ignore"
        return "__end__"
