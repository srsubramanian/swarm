"""Tests for the LangGraph orchestrator — topology + full run with mocked LLM."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.messages import AIMessage

from app.agents.orchestrator import build_graph, event_graph, graph, stateless_graph
from app.agents.schemas import ActionItem, AgentAnalysis, ModeratorSynthesis
from app.agents.state import SwarmState


# --- Fixtures ---


def _sample_input() -> dict:
    return {
        "event_type": "wire_transfer",
        "title": "$2.4M Wire to Cyprus",
        "client_name": "Meridian Holdings",
        "event_data": {
            "amount": 2_400_000,
            "currency": "USD",
            "destination_country": "CY",
            "destination_bank": "Bank of Cyprus",
            "reference": "INV-2024-0847",
        },
        "client_memory": "Known client since 2019. Regular EU transfers for trade finance.",
        "analyses": [],
        "moderator_synthesis": None,
        "decision": None,
        "memory_update_proposal": None,
        "triage_result": None,
    }


def _mock_agent_analysis(role: str) -> AgentAnalysis:
    return AgentAnalysis(
        agent_role=role,
        position=f"Mock {role} position",
        analysis=f"Mock {role} analysis content.",
        risk_level="high",
        confidence="medium",
        key_findings=[f"{role} finding 1", f"{role} finding 2"],
        recommended_action=f"Mock {role} recommendation",
    )


def _mock_moderator_synthesis() -> ModeratorSynthesis:
    return ModeratorSynthesis(
        status="HOLD RECOMMENDED",
        consensus="All agents flag elevated risk for this transfer.",
        dissent="Engineering notes the client has a history of similar transfers.",
        risk_level="high",
        risk_assessment="High risk due to jurisdiction and amount.",
        key_decisions=["Transfer exceeds normal pattern", "Cyprus is high-risk jurisdiction"],
        next_steps=["Hold transfer pending EDD", "Request source of funds documentation"],
        action_items=[
            ActionItem(label="Hold Transfer", variant="primary", rationale="Recommended pending review"),
            ActionItem(label="Approve with Conditions", variant="secondary", rationale="If source docs provided"),
            ActionItem(label="Escalate to BSA Officer", variant="danger", rationale="If SAR filing needed"),
        ],
    )


def _create_mock_llm():
    """Create a mock LLM that supports bind_tools() and with_structured_output()."""

    async def mock_structured_ainvoke(messages):
        system_content = messages[0].content
        if system_content.startswith("# Moderator"):
            return _mock_moderator_synthesis()
        elif system_content.startswith("# Compliance"):
            return _mock_agent_analysis("compliance")
        elif system_content.startswith("# Security"):
            return _mock_agent_analysis("security")
        elif system_content.startswith("# Engineering"):
            return _mock_agent_analysis("engineering")
        raise ValueError(f"Unexpected prompt: {system_content[:100]}")

    mock_structured = AsyncMock()
    mock_structured.ainvoke = mock_structured_ainvoke

    # Tool-bound LLM returns AIMessage with no tool_calls (loop exits immediately)
    mock_tool_bound = AsyncMock()
    mock_tool_bound.ainvoke = AsyncMock(return_value=AIMessage(content="Analysis complete."))

    mock_llm = MagicMock()
    mock_llm.with_structured_output.return_value = mock_structured
    mock_llm.bind_tools.return_value = mock_tool_bound
    return mock_llm


# --- Topology Tests ---


class TestGraphTopology:
    def test_graph_compiles(self):
        """Graph builds without error."""
        g = build_graph()
        assert g is not None

    def test_graph_has_expected_nodes(self):
        """All 7 nodes are present (including await_decision and post_decision)."""
        node_names = set(graph.nodes.keys())
        expected = {"prepare", "compliance", "security", "engineering", "moderator",
                    "await_decision", "post_decision", "__start__"}
        assert expected.issubset(node_names), f"Missing nodes: {expected - node_names}"

    def test_singleton_graph_matches_builder(self):
        """Module-level graphs have expected structure."""
        fresh = build_graph(include_triage=False)
        assert set(fresh.nodes.keys()) == set(graph.nodes.keys())

    def test_event_graph_has_triage_nodes(self):
        """Event graph includes triage and notify_rm nodes."""
        node_names = set(event_graph.nodes.keys())
        assert "triage" in node_names
        assert "notify_rm" in node_names


# --- Full Run Tests (mocked LLM) ---


class TestGraphExecution:
    @pytest.mark.asyncio
    async def test_full_run_produces_moderator_synthesis(self):
        """Full graph run with mocked LLM produces a moderator synthesis."""
        mock_llm = _create_mock_llm()

        with patch("app.agents.tool_loop.get_llm", return_value=mock_llm), \
             patch("app.agents.nodes.moderator.get_llm", return_value=mock_llm):
            result = await stateless_graph.ainvoke(_sample_input())

        # Verify 3 analyses accumulated
        assert len(result["analyses"]) == 3
        roles = {a.agent_role for a in result["analyses"]}
        assert roles == {"compliance", "security", "engineering"}

        # Verify moderator synthesis
        synthesis = result["moderator_synthesis"]
        assert synthesis is not None
        assert synthesis.status == "HOLD RECOMMENDED"
        assert synthesis.risk_level == "high"
        assert len(synthesis.action_items) == 3

    @pytest.mark.asyncio
    async def test_analyses_contain_expected_fields(self):
        """Each agent analysis has all required fields populated."""
        mock_llm = _create_mock_llm()

        with patch("app.agents.tool_loop.get_llm", return_value=mock_llm), \
             patch("app.agents.nodes.moderator.get_llm", return_value=mock_llm):
            result = await stateless_graph.ainvoke(_sample_input())

        for analysis in result["analyses"]:
            assert analysis.agent_role in ("compliance", "security", "engineering")
            assert analysis.position
            assert analysis.analysis
            assert analysis.risk_level in ("critical", "high", "medium", "low")
            assert analysis.confidence in ("high", "medium", "low")
            assert len(analysis.key_findings) >= 1
            assert analysis.recommended_action


# --- API Response Tests ---


class TestAPIResponse:
    @pytest.mark.asyncio
    async def test_analyze_endpoint(self):
        """POST /api/analyze returns properly shaped response."""
        from httpx import ASGITransport, AsyncClient
        from app.main import app

        mock_llm = _create_mock_llm()

        with patch("app.agents.tool_loop.get_llm", return_value=mock_llm), \
             patch("app.agents.nodes.moderator.get_llm", return_value=mock_llm):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post("/api/analyze", json={
                    "event_type": "wire_transfer",
                    "title": "$2.4M Wire to Cyprus",
                    "client_name": "Meridian Holdings",
                    "event_data": {"amount": 2_400_000, "currency": "USD"},
                })

        assert resp.status_code == 200
        data = resp.json()

        # 3 agents
        assert len(data["agents"]) == 3
        for agent in data["agents"]:
            assert "agent_role" in agent
            assert "agent_name" in agent
            assert "position" in agent
            assert "analysis" in agent

        # moderator summary
        summary = data["moderator_summary"]
        assert summary["status"] == "HOLD RECOMMENDED"
        assert summary["risk_level"] == "high"
        assert len(summary["action_items"]) == 3
        for item in summary["action_items"]:
            assert "id" in item
            assert "label" in item
            assert "variant" in item
