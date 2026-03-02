"""Tests for conversation store, builder, and history endpoints."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.agents.schemas import ActionItem, AgentAnalysis, ModeratorSynthesis
from app.schemas.conversations import ConversationRecord
from app.schemas.events import AnalyzeRequest
from app.services.conversation_builder import build_conversation
from app.services.store import conversation_store


# --- Fixtures ---


@pytest.fixture(autouse=True)
def _clear_store():
    """Clear the in-memory store before each test."""
    conversation_store.clear()
    yield
    conversation_store.clear()


def _sample_request() -> AnalyzeRequest:
    return AnalyzeRequest(
        event_type="wire_transfer",
        title="$2.4M Wire to Cyprus",
        client_name="Meridian Holdings",
        event_data={"amount": 2_400_000, "currency": "USD"},
        client_memory="Known client since 2019.",
    )


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


def _mock_analyses() -> list[AgentAnalysis]:
    return [
        _mock_agent_analysis("compliance"),
        _mock_agent_analysis("security"),
        _mock_agent_analysis("engineering"),
    ]


def _create_mock_llm():
    async def mock_ainvoke(messages):
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
    mock_structured.ainvoke = mock_ainvoke

    mock_llm = MagicMock()
    mock_llm.with_structured_output.return_value = mock_structured
    return mock_llm


def _llm_patches():
    mock_llm = _create_mock_llm()
    return (
        patch("app.agents.nodes.compliance.get_llm", return_value=mock_llm),
        patch("app.agents.nodes.security.get_llm", return_value=mock_llm),
        patch("app.agents.nodes.engineering.get_llm", return_value=mock_llm),
        patch("app.agents.nodes.moderator.get_llm", return_value=mock_llm),
    )


# --- Store Tests ---


class TestInMemoryStore:
    def test_save_and_get(self):
        record = build_conversation(
            _sample_request(), _mock_analyses(), _mock_moderator_synthesis()
        )
        conversation_store.save(record)
        retrieved = conversation_store.get(record.id)
        assert retrieved is not None
        assert retrieved.id == record.id
        assert retrieved.title == record.title

    def test_list_newest_first(self):
        req = _sample_request()
        analyses = _mock_analyses()
        synthesis = _mock_moderator_synthesis()

        r1 = build_conversation(req, analyses, synthesis)
        r2 = build_conversation(req, analyses, synthesis)

        # Force ordering: r1 older, r2 newer
        r1.started_at = "2026-01-01T00:00:00+00:00"
        r2.started_at = "2026-01-02T00:00:00+00:00"

        conversation_store.save(r1)
        conversation_store.save(r2)

        result = conversation_store.list_all()
        assert len(result) == 2
        assert result[0].id == r2.id
        assert result[1].id == r1.id

    def test_clear_returns_count(self):
        req = _sample_request()
        analyses = _mock_analyses()
        synthesis = _mock_moderator_synthesis()

        conversation_store.save(build_conversation(req, analyses, synthesis))
        conversation_store.save(build_conversation(req, analyses, synthesis))

        count = conversation_store.clear()
        assert count == 2
        assert conversation_store.list_all() == []

    def test_overwrite_by_id(self):
        record = build_conversation(
            _sample_request(), _mock_analyses(), _mock_moderator_synthesis()
        )
        conversation_store.save(record)

        record.title = "Updated Title"
        conversation_store.save(record)

        assert len(conversation_store.list_all()) == 1
        assert conversation_store.get(record.id).title == "Updated Title"

    def test_get_nonexistent_returns_none(self):
        assert conversation_store.get("nonexistent-id") is None


# --- Builder Tests ---


class TestBuildConversation:
    def test_builds_valid_record(self):
        record = build_conversation(
            _sample_request(), _mock_analyses(), _mock_moderator_synthesis()
        )

        assert isinstance(record, ConversationRecord)
        assert record.id
        assert record.title == "$2.4M Wire to Cyprus"
        assert record.client_name == "Meridian Holdings"
        assert record.risk_level == "high"
        assert record.status == "awaiting_decision"
        assert record.event_type == "wire_transfer"
        assert record.started_at
        assert record.message_count == 3

    def test_agents_populated(self):
        record = build_conversation(
            _sample_request(), _mock_analyses(), _mock_moderator_synthesis()
        )
        assert len(record.agents) == 3
        roles = {a.role for a in record.agents}
        assert roles == {"compliance", "security", "engineering"}
        for agent in record.agents:
            assert agent.status == "complete"
            assert agent.name
            assert agent.position

    def test_messages_populated(self):
        record = build_conversation(
            _sample_request(), _mock_analyses(), _mock_moderator_synthesis()
        )
        assert len(record.messages) == 3
        for msg in record.messages:
            assert msg.id
            assert msg.agent_role
            assert msg.agent_name
            assert msg.content
            assert msg.timestamp

    def test_moderator_summary_populated(self):
        record = build_conversation(
            _sample_request(), _mock_analyses(), _mock_moderator_synthesis()
        )
        summary = record.moderator_summary
        assert summary.status == "HOLD RECOMMENDED"
        assert "elevated risk" in summary.consensus
        assert "Dissent" in summary.consensus  # dissent folded in
        assert len(summary.key_decisions) >= 1
        assert summary.risk_assessment
        assert len(summary.next_steps) >= 1

    def test_action_required_populated(self):
        record = build_conversation(
            _sample_request(), _mock_analyses(), _mock_moderator_synthesis()
        )
        action = record.action_required
        assert action.status == "pending"
        assert len(action.options) == 2
        for opt in action.options:
            assert opt.id
            assert opt.label
            assert opt.variant

    def test_client_memory_populated(self):
        record = build_conversation(
            _sample_request(), _mock_analyses(), _mock_moderator_synthesis()
        )
        mem = record.client_memory
        assert mem.client_name == "Meridian Holdings"
        assert mem.content == "Known client since 2019."
        assert mem.last_updated

    def test_camel_case_serialization(self):
        record = build_conversation(
            _sample_request(), _mock_analyses(), _mock_moderator_synthesis()
        )
        data = record.model_dump(by_alias=True)
        assert "clientName" in data
        assert "riskLevel" in data
        assert "eventType" in data
        assert "startedAt" in data
        assert "messageCount" in data
        assert "moderatorSummary" in data
        assert "actionRequired" in data
        assert "clientMemory" in data
        # Nested models also camelCase
        assert "agentRole" in data["messages"][0]
        assert "agentName" in data["messages"][0]
        assert "keyDecisions" in data["moderatorSummary"]
        assert "riskAssessment" in data["moderatorSummary"]
        assert "nextSteps" in data["moderatorSummary"]


# --- Endpoint Tests ---


class TestConversationEndpoints:
    @pytest.mark.asyncio
    async def test_queue_persists_and_list_returns(self):
        """POST /api/queue persists result, GET /api/conversations returns it."""
        p1, p2, p3, p4 = _llm_patches()
        with p1, p2, p3, p4:
            from app.main import app

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                # Submit a scenario
                resp = await client.post(
                    "/api/queue",
                    json={"scenario": "wire_transfer"},
                    timeout=30,
                )
                assert resp.status_code == 200
                queue_data = resp.json()
                assert "id" in queue_data
                assert queue_data["clientName"] == "Meridian Holdings"
                conv_id = queue_data["id"]

                # List conversations
                resp = await client.get("/api/conversations")
                assert resp.status_code == 200
                convs = resp.json()
                assert len(convs) == 1
                assert convs[0]["id"] == conv_id

    @pytest.mark.asyncio
    async def test_get_by_id(self):
        """GET /api/conversations/{id} returns the correct conversation."""
        p1, p2, p3, p4 = _llm_patches()
        with p1, p2, p3, p4:
            from app.main import app

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post(
                    "/api/queue",
                    json={"scenario": "wire_transfer"},
                    timeout=30,
                )
                conv_id = resp.json()["id"]

                resp = await client.get(f"/api/conversations/{conv_id}")
                assert resp.status_code == 200
                data = resp.json()
                assert data["id"] == conv_id
                assert data["title"] == "$2.4M Wire to Cyprus"

    @pytest.mark.asyncio
    async def test_get_nonexistent_returns_404(self):
        from app.main import app

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/conversations/nonexistent")
            assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_clears_all(self):
        """DELETE /api/conversations clears the store."""
        p1, p2, p3, p4 = _llm_patches()
        with p1, p2, p3, p4:
            from app.main import app

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                # Add two conversations
                await client.post(
                    "/api/queue",
                    json={"scenario": "wire_transfer"},
                    timeout=30,
                )
                await client.post(
                    "/api/queue",
                    json={"scenario": "cash_deposit"},
                    timeout=30,
                )

                # List should have 2
                resp = await client.get("/api/conversations")
                assert len(resp.json()) == 2

                # Clear
                resp = await client.delete("/api/conversations")
                assert resp.status_code == 200
                assert resp.json()["cleared"] == 2

                # List should be empty
                resp = await client.get("/api/conversations")
                assert resp.json() == []

    @pytest.mark.asyncio
    async def test_analyze_does_not_persist(self):
        """POST /api/analyze remains stateless — no conversations stored."""
        p1, p2, p3, p4 = _llm_patches()
        with p1, p2, p3, p4:
            from app.main import app

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post(
                    "/api/analyze",
                    json={
                        "event_type": "wire_transfer",
                        "title": "Test",
                        "client_name": "Test",
                        "event_data": {"amount": 100},
                    },
                    timeout=30,
                )
                assert resp.status_code == 200

                # No conversations should be stored
                resp = await client.get("/api/conversations")
                assert resp.json() == []

    @pytest.mark.asyncio
    async def test_queue_response_has_camel_case_keys(self):
        """POST /api/queue response uses camelCase keys."""
        p1, p2, p3, p4 = _llm_patches()
        with p1, p2, p3, p4:
            from app.main import app

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post(
                    "/api/queue",
                    json={"scenario": "wire_transfer"},
                    timeout=30,
                )
                data = resp.json()
                # Top-level camelCase
                assert "clientName" in data
                assert "riskLevel" in data
                assert "eventType" in data
                assert "startedAt" in data
                assert "messageCount" in data
                assert "moderatorSummary" in data
                assert "actionRequired" in data
                assert "clientMemory" in data
