"""Tests for scenario registry and queue endpoints."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.agents.scenarios import SCENARIOS
from app.agents.schemas import ActionItem, AgentAnalysis, ModeratorSynthesis
from app.schemas.events import AnalyzeRequest


# --- Fixtures ---


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
    """Create a mock LLM that routes responses by prompt header."""

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


# --- Scenario Registry Tests ---


class TestScenarios:
    def test_all_four_scenarios_exist(self):
        assert set(SCENARIOS.keys()) == {
            "wire_transfer", "velocity_alert", "security_alert", "cash_deposit"
        }

    def test_scenarios_are_valid_requests(self):
        for name, req in SCENARIOS.items():
            assert isinstance(req, AnalyzeRequest), name
            assert req.event_type == name
            assert req.title
            assert req.client_name
            assert req.event_data

    def test_wire_transfer_has_expected_data(self):
        req = SCENARIOS["wire_transfer"]
        assert req.client_name == "Meridian Holdings"
        assert req.event_data["amount"] == 2_400_000
        assert req.event_data["destination_country"] == "CY"

    def test_velocity_alert_has_expected_data(self):
        req = SCENARIOS["velocity_alert"]
        assert req.client_name == "Quantum Dynamics"
        assert req.event_data["transaction_count"] == 47

    def test_security_alert_has_expected_data(self):
        req = SCENARIOS["security_alert"]
        assert req.client_name == "Atlas Capital"
        assert req.event_data["geo_location"] == "Istanbul, Turkey"

    def test_cash_deposit_has_expected_data(self):
        req = SCENARIOS["cash_deposit"]
        assert req.client_name == "Riverside Deli LLC"
        assert req.event_data["amount"] == 9_800


# --- Queue Endpoint Tests ---


class TestQueueEndpoints:
    @pytest.mark.asyncio
    async def test_list_scenarios(self):
        from app.main import app
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/queue/scenarios")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 4
        names = {s["name"] for s in data}
        assert names == {"wire_transfer", "velocity_alert", "security_alert", "cash_deposit"}
        for s in data:
            assert "title" in s
            assert "client_name" in s
            assert "event_type" in s

    @pytest.mark.asyncio
    async def test_queue_sync_returns_full_analysis(self):
        mock_llm = _create_mock_llm()

        with patch("app.agents.nodes.compliance.get_llm", return_value=mock_llm), \
             patch("app.agents.nodes.security.get_llm", return_value=mock_llm), \
             patch("app.agents.nodes.engineering.get_llm", return_value=mock_llm), \
             patch("app.agents.nodes.moderator.get_llm", return_value=mock_llm):
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
        assert len(data["agents"]) == 3
        roles = {a["agent_role"] for a in data["agents"]}
        assert roles == {"compliance", "security", "engineering"}
        assert data["moderator_summary"]["status"] == "HOLD RECOMMENDED"

    @pytest.mark.asyncio
    async def test_queue_unknown_scenario_returns_404(self):
        from app.main import app
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/queue",
                json={"scenario": "nonexistent"},
            )
        assert resp.status_code == 404
        assert "nonexistent" in resp.json()["detail"]

    @pytest.mark.asyncio
    async def test_queue_stream_unknown_scenario_returns_404(self):
        from app.main import app
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/queue/stream",
                json={"scenario": "nonexistent"},
            )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_queue_delegates_to_analyze(self):
        """Queue endpoint produces the same shape as /api/analyze."""
        mock_llm = _create_mock_llm()

        with patch("app.agents.nodes.compliance.get_llm", return_value=mock_llm), \
             patch("app.agents.nodes.security.get_llm", return_value=mock_llm), \
             patch("app.agents.nodes.engineering.get_llm", return_value=mock_llm), \
             patch("app.agents.nodes.moderator.get_llm", return_value=mock_llm):
            from app.main import app
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post(
                    "/api/queue",
                    json={"scenario": "cash_deposit"},
                    timeout=30,
                )

        assert resp.status_code == 200
        data = resp.json()
        # Same shape as /api/analyze response
        assert "agents" in data
        assert "moderator_summary" in data
        summary = data["moderator_summary"]
        assert "status" in summary
        assert "action_items" in summary
        assert len(summary["action_items"]) >= 2
