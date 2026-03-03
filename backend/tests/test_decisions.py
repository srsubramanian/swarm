"""Tests for the RM decision endpoint — interrupt/resume with checkpointing."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from langchain_core.messages import AIMessage

from app.agents.schemas import ActionItem, AgentAnalysis, ModeratorSynthesis
from app.services.store import conversation_store, thread_store


# --- Fixtures ---


@pytest.fixture(autouse=True)
def _clear_stores():
    """Clear stores before each test."""
    conversation_store.clear()
    thread_store.clear()
    yield
    conversation_store.clear()
    thread_store.clear()


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
        dissent="Engineering notes history of similar transfers.",
        risk_level="high",
        risk_assessment="High risk due to jurisdiction and amount.",
        key_decisions=["Transfer exceeds normal pattern"],
        next_steps=["Hold transfer pending EDD"],
        action_items=[
            ActionItem(label="Hold Transfer", variant="primary", rationale="Recommended"),
            ActionItem(label="Escalate", variant="danger", rationale="If SAR needed"),
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

    mock_tool_bound = AsyncMock()
    mock_tool_bound.ainvoke = AsyncMock(return_value=AIMessage(content="Analysis complete."))

    mock_llm = MagicMock()
    mock_llm.with_structured_output.return_value = mock_structured
    mock_llm.bind_tools.return_value = mock_tool_bound
    return mock_llm


def _llm_patches():
    mock_llm = _create_mock_llm()
    return (
        patch("app.agents.tool_loop.get_llm", return_value=mock_llm),
        patch("app.agents.nodes.moderator.get_llm", return_value=mock_llm),
    )


# --- Decision Flow Tests ---


class TestDecisionFlow:
    @pytest.mark.asyncio
    async def test_queue_returns_awaiting_decision(self):
        """POST /api/queue returns conversation with status 'awaiting_decision'."""
        p1, p2 = _llm_patches()
        with p1, p2:
            from app.main import app
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post(
                    "/api/queue",
                    json={"scenario": "wire_transfer"},
                    timeout=30,
                )

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "awaiting_decision"
        assert data["actionRequired"]["status"] == "pending"

    @pytest.mark.asyncio
    async def test_full_decision_flow(self):
        """Submit scenario → get awaiting_decision → submit decision → get concluded."""
        p1, p2 = _llm_patches()
        with p1, p2:
            from app.main import app
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                # Step 1: Submit scenario
                resp = await client.post(
                    "/api/queue",
                    json={"scenario": "wire_transfer"},
                    timeout=30,
                )
                assert resp.status_code == 200
                data = resp.json()
                conv_id = data["id"]
                option_id = data["actionRequired"]["options"][0]["id"]
                assert data["status"] == "awaiting_decision"

                # Step 2: Submit decision
                resp = await client.post(
                    f"/api/decisions/{conv_id}",
                    json={
                        "option_id": option_id,
                        "action": "approve",
                        "justification": "Cleared after review",
                    },
                    timeout=30,
                )
                assert resp.status_code == 200
                result = resp.json()
                assert result["status"] == "concluded"
                assert result["actionRequired"]["status"] == "actioned"
                assert result["actionRequired"]["actionedOption"] == option_id
                assert result["decision"]["action"] == "approve"
                assert result["decision"]["justification"] == "Cleared after review"

    @pytest.mark.asyncio
    async def test_decision_on_nonexistent_conversation(self):
        """POST /api/decisions/{id} on nonexistent conversation returns 404."""
        from app.main import app
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/decisions/nonexistent-id",
                json={
                    "option_id": "test",
                    "action": "approve",
                    "justification": "",
                },
            )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_decision_on_already_concluded(self):
        """POST /api/decisions/{id} on concluded conversation returns 400."""
        p1, p2 = _llm_patches()
        with p1, p2:
            from app.main import app
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                # Submit and decide
                resp = await client.post(
                    "/api/queue",
                    json={"scenario": "wire_transfer"},
                    timeout=30,
                )
                data = resp.json()
                conv_id = data["id"]
                option_id = data["actionRequired"]["options"][0]["id"]

                await client.post(
                    f"/api/decisions/{conv_id}",
                    json={
                        "option_id": option_id,
                        "action": "approve",
                        "justification": "Cleared",
                    },
                    timeout=30,
                )

                # Try to decide again
                resp = await client.post(
                    f"/api/decisions/{conv_id}",
                    json={
                        "option_id": option_id,
                        "action": "reject",
                        "justification": "Changed my mind",
                    },
                )
                assert resp.status_code == 400
                assert "awaiting_decision" in resp.json()["detail"]

    @pytest.mark.asyncio
    async def test_conversation_shows_decision_after_action(self):
        """GET /api/conversations/{id} shows decision details after RM action."""
        p1, p2 = _llm_patches()
        with p1, p2:
            from app.main import app
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post(
                    "/api/queue",
                    json={"scenario": "wire_transfer"},
                    timeout=30,
                )
                data = resp.json()
                conv_id = data["id"]
                option_id = data["actionRequired"]["options"][0]["id"]

                await client.post(
                    f"/api/decisions/{conv_id}",
                    json={
                        "option_id": option_id,
                        "action": "escalate",
                        "justification": "Needs BSA review",
                    },
                    timeout=30,
                )

                # Fetch conversation
                resp = await client.get(f"/api/conversations/{conv_id}")
                assert resp.status_code == 200
                data = resp.json()
                assert data["status"] == "concluded"
                assert data["decision"]["action"] == "escalate"
                assert data["decision"]["optionId"] == option_id


class TestStatelessGraphUnchanged:
    @pytest.mark.asyncio
    async def test_analyze_endpoint_still_works(self):
        """POST /api/analyze still works with stateless graph (no checkpointer)."""
        p1, p2 = _llm_patches()
        with p1, p2:
            from app.main import app
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post(
                    "/api/analyze",
                    json={
                        "event_type": "wire_transfer",
                        "title": "Test Wire",
                        "client_name": "Test Client",
                        "event_data": {"amount": 1000},
                    },
                    timeout=30,
                )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["agents"]) == 3
        assert data["moderator_summary"]["status"] == "HOLD RECOMMENDED"
