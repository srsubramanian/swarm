"""Shared tool-calling loop for deep agent nodes.

Each domain agent uses this helper to run an internal tool-calling loop:
the LLM can call domain-specific tools, receive results, and iterate
until it has enough evidence. Then a final structured-output call extracts
the AgentAnalysis result.

The LangGraph topology is unchanged — this loop is entirely internal
to each agent node function.
"""

import logging

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage

from app.agents.llm import get_llm
from app.agents.schemas import AgentAnalysis
from app.agents.state import SwarmState

logger = logging.getLogger(__name__)


async def run_agent_with_tools(
    state: SwarmState,
    agent_role: str,
    system_prompt: str,
    event_message: str,
    tools: list,
    max_iterations: int = 5,
) -> dict:
    """Run an agent with an internal tool-calling loop.

    1. Bind tools to the LLM for the evidence-gathering phase.
    2. Loop: invoke LLM → if tool_calls, execute tools → append results → repeat.
    3. After loop: use structured output to extract AgentAnalysis.

    Args:
        state: Current graph state (not mutated).
        agent_role: One of 'compliance', 'security', 'engineering'.
        system_prompt: System prompt loaded from the agent's prompt template.
        event_message: Formatted event data as a human message.
        tools: List of langchain tools available to this agent.
        max_iterations: Max tool-calling rounds before forcing extraction.

    Returns:
        Dict with 'analyses' key containing a single-element list of AgentAnalysis.
    """
    llm = get_llm()

    # Phase 1: Tool-calling loop (evidence gathering)
    tool_map = {t.name: t for t in tools}
    llm_with_tools = llm.bind_tools(tools)

    messages: list = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=event_message),
    ]

    for iteration in range(max_iterations):
        response: AIMessage = await llm_with_tools.ainvoke(messages)
        messages.append(response)

        if not response.tool_calls:
            logger.info(
                "Agent %s: no tool calls at iteration %d, moving to extraction",
                agent_role,
                iteration,
            )
            break

        for tool_call in response.tool_calls:
            tool_name = tool_call["name"]
            tool_args = tool_call["args"]

            if tool_name not in tool_map:
                logger.warning(
                    "Agent %s: unknown tool '%s', returning error",
                    agent_role,
                    tool_name,
                )
                messages.append(
                    ToolMessage(
                        content=f"Error: tool '{tool_name}' not found. Available tools: {list(tool_map.keys())}",
                        tool_call_id=tool_call["id"],
                    )
                )
                continue

            try:
                result = await tool_map[tool_name].ainvoke(tool_args)
                logger.info(
                    "Agent %s: called %s(%s)",
                    agent_role,
                    tool_name,
                    ", ".join(f"{k}={v!r}" for k, v in tool_args.items()),
                )
            except Exception as exc:
                logger.error(
                    "Agent %s: tool %s raised %s: %s",
                    agent_role,
                    tool_name,
                    type(exc).__name__,
                    exc,
                )
                result = f"Error executing {tool_name}: {exc}"

            messages.append(
                ToolMessage(
                    content=str(result),
                    tool_call_id=tool_call["id"],
                )
            )
    else:
        logger.warning(
            "Agent %s: hit max iterations (%d), forcing extraction",
            agent_role,
            max_iterations,
        )

    # Phase 2: Structured output extraction
    messages.append(
        HumanMessage(
            content="Based on your analysis and tool results above, provide your final structured assessment."
        )
    )

    structured_llm = llm.with_structured_output(AgentAnalysis)
    analysis: AgentAnalysis = await structured_llm.ainvoke(messages)
    analysis.agent_role = agent_role

    return {"analyses": [analysis]}
