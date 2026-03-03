"""Tests for client memory store, prepare node, and memory API endpoints."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from langchain_core.messages import AIMessage

from app.agents.schemas import ActionItem, AgentAnalysis, ModeratorSynthesis
from app.services.memory_store import memory_store
from app.services.store import conversation_store, thread_store


# --- Fixtures ---


@pytest.fixture(autouse=True)
def _clear_stores():
    """Clear all stores before each test."""
    memory_store.clear()
    conversation_store.clear()
    thread_store.clear()
    yield
    memory_store.clear()
    conversation_store.clear()
    thread_store.clear()


# --- Memory Store Unit Tests ---


class TestClientMemoryStore:
    def test_get_empty_memory(self):
        assert memory_store.get_memory("Unknown Client") == ""

    def test_set_and_get_memory(self):
        memory_store.set_memory("Test Client", "Known since 2020.")
        assert memory_store.get_memory("Test Client") == "Known since 2020."

    def test_propose_update(self):
        proposal_id = memory_store.propose_update("Test Client", "New pattern observed.")
        assert proposal_id
        proposal = memory_store.get_proposal(proposal_id)
        assert proposal.client_name == "Test Client"
        assert proposal.proposed_content == "New pattern observed."
        assert proposal.status == "pending"

    def test_approve_merges_into_memory(self):
        memory_store.set_memory("Test Client", "Original memory.")
        proposal_id = memory_store.propose_update("Test Client", "New observation.")
        assert memory_store.approve_update(proposal_id)

        memory = memory_store.get_memory("Test Client")
        assert "Original memory." in memory
        assert "New observation." in memory

    def test_approve_creates_memory_if_none(self):
        proposal_id = memory_store.propose_update("New Client", "First observation.")
        assert memory_store.approve_update(proposal_id)
        assert memory_store.get_memory("New Client") == "First observation."

    def test_reject_discards_proposal(self):
        proposal_id = memory_store.propose_update("Test Client", "Bad update.")
        assert memory_store.reject_update(proposal_id)
        proposal = memory_store.get_proposal(proposal_id)
        assert proposal.status == "rejected"
        assert memory_store.get_memory("Test Client") == ""

    def test_approve_nonexistent_returns_false(self):
        assert not memory_store.approve_update("nonexistent-id")

    def test_reject_nonexistent_returns_false(self):
        assert not memory_store.reject_update("nonexistent-id")

    def test_double_approve_returns_false(self):
        proposal_id = memory_store.propose_update("Test Client", "Update.")
        assert memory_store.approve_update(proposal_id)
        assert not memory_store.approve_update(proposal_id)

    def test_list_pending(self):
        memory_store.propose_update("Client A", "Update A")
        memory_store.propose_update("Client B", "Update B")
        pid = memory_store.propose_update("Client C", "Update C")
        memory_store.approve_update(pid)

        pending = memory_store.list_pending()
        assert len(pending) == 2
        names = {p.client_name for p in pending}
        assert names == {"Client A", "Client B"}


# --- Prepare Node Tests ---


class TestPrepareNode:
    @pytest.mark.asyncio
    async def test_prepare_injects_stored_memory(self):
        from app.agents.nodes.prepare import prepare_context

        memory_store.set_memory("Meridian Holdings", "Stored: Known client with EU focus.")
        state = {
            "event_type": "wire_transfer",
            "title": "Test",
            "client_name": "Meridian Holdings",
            "event_data": {},
            "client_memory": "Request-provided memory.",
            "analyses": [],
            "moderator_synthesis": None,
            "decision": None,
            "memory_update_proposal": None,
            "triage_result": None,
        }
        result = await prepare_context(state)
        assert "client_memory" in result
        assert "Request-provided memory." in result["client_memory"]
        assert "Stored: Known client with EU focus." in result["client_memory"]

    @pytest.mark.asyncio
    async def test_prepare_returns_empty_when_no_stored_memory(self):
        from app.agents.nodes.prepare import prepare_context

        state = {
            "event_type": "wire_transfer",
            "title": "Test",
            "client_name": "Unknown Client",
            "event_data": {},
            "client_memory": "",
            "analyses": [],
            "moderator_synthesis": None,
            "decision": None,
            "memory_update_proposal": None,
            "triage_result": None,
        }
        result = await prepare_context(state)
        assert result == {}


# --- Memory API Endpoint Tests ---


class TestMemoryEndpoints:
    @pytest.mark.asyncio
    async def test_get_client_memory(self):
        memory_store.set_memory("Meridian Holdings", "Known since 2019.")
        from app.main import app
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/memory/Meridian%20Holdings")
        assert resp.status_code == 200
        data = resp.json()
        assert data["client_name"] == "Meridian Holdings"
        assert data["content"] == "Known since 2019."

    @pytest.mark.asyncio
    async def test_get_empty_client_memory(self):
        from app.main import app
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/memory/Unknown%20Client")
        assert resp.status_code == 200
        assert resp.json()["content"] == ""

    @pytest.mark.asyncio
    async def test_list_pending_proposals(self):
        memory_store.propose_update("Client A", "Update A")
        memory_store.propose_update("Client B", "Update B")

        from app.main import app
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/memory/pending")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2

    @pytest.mark.asyncio
    async def test_approve_proposal(self):
        memory_store.set_memory("Test Client", "Original.")
        proposal_id = memory_store.propose_update("Test Client", "New observation.")

        from app.main import app
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(f"/api/memory/pending/{proposal_id}/approve")
        assert resp.status_code == 200
        assert resp.json()["status"] == "approved"

        # Memory should be updated
        assert "New observation." in memory_store.get_memory("Test Client")

    @pytest.mark.asyncio
    async def test_reject_proposal(self):
        proposal_id = memory_store.propose_update("Test Client", "Bad update.")

        from app.main import app
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(f"/api/memory/pending/{proposal_id}/reject")
        assert resp.status_code == 200
        assert resp.json()["status"] == "rejected"

    @pytest.mark.asyncio
    async def test_approve_nonexistent_returns_404(self):
        from app.main import app
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post("/api/memory/pending/nonexistent/approve")
        assert resp.status_code == 404
