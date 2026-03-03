"""Tests for triage classification, event webhook, and simulator control."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from langchain_core.messages import AIMessage

from app.agents.nodes.triage import TriageClassification, TriageResult, triage_edge
from app.agents.schemas import ActionItem, AgentAnalysis, ModeratorSynthesis
from app.services.memory_store import memory_store
from app.services.store import conversation_store, thread_store


# --- Fixtures ---


@pytest.fixture(autouse=True)
def _clear_stores():
    """Clear all stores before each test."""
    conversation_store.clear()
    thread_store.clear()
    memory_store.clear()
    yield
    conversation_store.clear()
    thread_store.clear()
    memory_store.clear()


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
        consensus="All agents flag elevated risk.",
        dissent="None",
        risk_level="high",
        risk_assessment="High risk.",
        key_decisions=["Transfer exceeds normal pattern"],
        next_steps=["Hold transfer"],
        action_items=[
            ActionItem(label="Hold Transfer", variant="primary", rationale="Recommended"),
            ActionItem(label="Escalate", variant="danger", rationale="If needed"),
        ],
    )


def _create_mock_llm(triage_classification="respond"):
    """Create a mock LLM that handles triage + agent + moderator calls."""

    async def mock_structured_ainvoke(messages):
        system_content = messages[0].content
        if "Triage" in system_content:
            return TriageResult(
                classification=TriageClassification(triage_classification),
                reasoning="Mock triage reasoning",
            )
        elif system_content.startswith("# Moderator"):
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

    mock_tool_bound = AsyncMock()
    mock_tool_bound.ainvoke = AsyncMock(return_value=AIMessage(content="Analysis complete."))

    # For memory update LLM call in post_decision
    mock_base = AsyncMock()
    mock_base.ainvoke = AsyncMock(return_value=AIMessage(content="- Mock memory update"))

    mock_llm = MagicMock()
    mock_llm.with_structured_output.return_value = mock_structured
    mock_llm.bind_tools.return_value = mock_tool_bound
    mock_llm.ainvoke = mock_base.ainvoke
    return mock_llm


def _triage_patches(classification="respond"):
    mock_llm = _create_mock_llm(classification)
    return (
        patch("app.agents.tool_loop.get_llm", return_value=mock_llm),
        patch("app.agents.nodes.moderator.get_llm", return_value=mock_llm),
        patch("app.agents.nodes.triage.get_llm", return_value=mock_llm),
        patch("app.agents.nodes.post_decision.get_llm", return_value=mock_llm),
    )


# --- Triage Edge Tests ---


class TestTriageEdge:
    def test_respond_returns_send_list(self):
        state = {"triage_result": "respond"}
        result = triage_edge(state)
        assert isinstance(result, list)
        assert len(result) == 3

    def test_notify_returns_string(self):
        state = {"triage_result": "notify"}
        result = triage_edge(state)
        assert result == "notify_rm"

    def test_ignore_returns_end(self):
        state = {"triage_result": "ignore"}
        result = triage_edge(state)
        assert result == "__end__"

    def test_default_is_respond(self):
        state = {}
        result = triage_edge(state)
        assert isinstance(result, list)
        assert len(result) == 3


# --- Event Graph Tests ---


class TestEventGraphRespond:
    @pytest.mark.asyncio
    async def test_respond_triage_runs_full_pipeline(self):
        """When triage says 'respond', full agent pipeline runs."""
        from app.agents.orchestrator import event_graph

        p1, p2, p3, p4 = _triage_patches("respond")
        with p1, p2, p3, p4:
            import uuid
            config = {"configurable": {"thread_id": str(uuid.uuid4())}}
            result = await event_graph.ainvoke(
                {
                    "event_type": "wire_transfer",
                    "title": "$2.4M Wire to Cyprus",
                    "client_name": "Meridian Holdings",
                    "event_data": {"amount": 2_400_000},
                    "client_memory": "",
                    "analyses": [],
                    "moderator_synthesis": None,
                    "decision": None,
                    "memory_update_proposal": None,
                    "triage_result": None,
                },
                config=config,
            )

        assert result["triage_result"] == "respond"
        assert len(result["analyses"]) == 3


class TestEventGraphIgnore:
    @pytest.mark.asyncio
    async def test_ignore_triage_skips_agents(self):
        """When triage says 'ignore', no agents run."""
        from app.agents.orchestrator import event_graph

        p1, p2, p3, p4 = _triage_patches("ignore")
        with p1, p2, p3, p4:
            import uuid
            config = {"configurable": {"thread_id": str(uuid.uuid4())}}
            result = await event_graph.ainvoke(
                {
                    "event_type": "wire_transfer",
                    "title": "Routine transfer",
                    "client_name": "Known Client",
                    "event_data": {"amount": 500},
                    "client_memory": "Regular small transfers.",
                    "analyses": [],
                    "moderator_synthesis": None,
                    "decision": None,
                    "memory_update_proposal": None,
                    "triage_result": None,
                },
                config=config,
            )

        assert result["triage_result"] == "ignore"
        assert result["analyses"] == []
        assert result["moderator_synthesis"] is None


class TestEventGraphNotify:
    @pytest.mark.asyncio
    async def test_notify_triage_skips_agents(self):
        """When triage says 'notify', notify_rm runs but not the full pipeline."""
        from app.agents.orchestrator import event_graph

        p1, p2, p3, p4 = _triage_patches("notify")
        with p1, p2, p3, p4:
            import uuid
            config = {"configurable": {"thread_id": str(uuid.uuid4())}}
            result = await event_graph.ainvoke(
                {
                    "event_type": "velocity_alert",
                    "title": "Slightly elevated volume",
                    "client_name": "Known Client",
                    "event_data": {"transaction_count": 15},
                    "client_memory": "Normal batch size 10-20.",
                    "analyses": [],
                    "moderator_synthesis": None,
                    "decision": None,
                    "memory_update_proposal": None,
                    "triage_result": None,
                },
                config=config,
            )

        assert result["triage_result"] == "notify"
        assert result["analyses"] == []
        assert result["moderator_synthesis"] is None


# --- Webhook Endpoint Tests ---


class TestWebhookEndpoint:
    @pytest.mark.asyncio
    async def test_webhook_respond_creates_conversation(self):
        """Webhook with 'respond' triage creates a conversation."""
        p1, p2, p3, p4 = _triage_patches("respond")
        with p1, p2, p3, p4:
            from app.main import app
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post(
                    "/api/events/webhook",
                    json={
                        "event_type": "wire_transfer",
                        "title": "External Wire",
                        "client_name": "External Client",
                        "event_data": {"amount": 1_000_000},
                    },
                    timeout=30,
                )

        assert resp.status_code == 200
        data = resp.json()
        assert data["triage_result"] == "respond"
        assert data["conversation_id"] is not None

    @pytest.mark.asyncio
    async def test_webhook_ignore_no_conversation(self):
        """Webhook with 'ignore' triage does not create a conversation."""
        p1, p2, p3, p4 = _triage_patches("ignore")
        with p1, p2, p3, p4:
            from app.main import app
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post(
                    "/api/events/webhook",
                    json={
                        "event_type": "wire_transfer",
                        "title": "Tiny Transfer",
                        "client_name": "Known Client",
                        "event_data": {"amount": 50},
                    },
                    timeout=30,
                )

        assert resp.status_code == 200
        data = resp.json()
        assert data["triage_result"] == "ignore"
        assert data["conversation_id"] is None


# --- Simulator Control Endpoint Tests ---


class TestSimulatorEndpoints:
    @pytest.mark.asyncio
    async def test_start_stop_simulator(self):
        from app.main import app
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Start
            resp = await client.post("/api/events/simulate/start")
            assert resp.status_code == 200
            assert resp.json()["status"] == "started"

            # Double start
            resp = await client.post("/api/events/simulate/start")
            assert resp.json()["status"] == "already_running"

            # Stop
            resp = await client.post("/api/events/simulate/stop")
            assert resp.status_code == 200
            assert resp.json()["status"] == "stopped"

            # Double stop
            resp = await client.post("/api/events/simulate/stop")
            assert resp.json()["status"] == "already_stopped"
