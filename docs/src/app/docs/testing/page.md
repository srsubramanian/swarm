---
title: Testing
---

SwarmOps uses pytest with mocked LLM calls to test graph topology, agent orchestration, and API endpoints without requiring AWS Bedrock access. {% .lead %}

---

## Running tests

```shell
cd backend
uv run pytest tests/ -v
```

Or run a specific test file:

```shell
uv run pytest tests/test_orchestrator.py -v
```

---

## Test structure

**File:** `backend/tests/test_orchestrator.py`

Tests are organized into three classes:

### TestGraphTopology

Validates the LangGraph structure without executing agents:

```python
class TestGraphTopology:
    def test_graph_compiles(self):
        """Graph builds without error."""
        g = build_graph()
        assert g is not None

    def test_graph_has_expected_nodes(self):
        """All 5 nodes are present."""
        node_names = set(graph.nodes.keys())
        expected = {"prepare", "compliance", "security",
                    "engineering", "moderator", "__start__"}
        assert expected.issubset(node_names)

    def test_singleton_graph_matches_builder(self):
        """Module-level graph matches build_graph()."""
        fresh = build_graph()
        assert set(fresh.nodes.keys()) == set(graph.nodes.keys())
```

### TestGraphExecution

Full graph runs with a mocked LLM:

```python
class TestGraphExecution:
    @pytest.mark.asyncio
    async def test_full_run_produces_moderator_synthesis(self):
        """Full graph run with mocked LLM produces a moderator synthesis."""
        # ... mock setup ...
        result = await graph.ainvoke(_sample_input())

        assert len(result["analyses"]) == 3
        roles = {a.agent_role for a in result["analyses"]}
        assert roles == {"compliance", "security", "engineering"}

        synthesis = result["moderator_synthesis"]
        assert synthesis is not None
        assert synthesis.status == "HOLD RECOMMENDED"
        assert len(synthesis.action_items) == 3
```

### TestAPIResponse

End-to-end API tests using `httpx.AsyncClient`:

```python
class TestAPIResponse:
    @pytest.mark.asyncio
    async def test_analyze_endpoint(self):
        """POST /api/analyze returns properly shaped response."""
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post("/api/analyze", json={...})

        assert resp.status_code == 200
        assert len(data["agents"]) == 3
        assert data["moderator_summary"]["status"] == "HOLD RECOMMENDED"
```

---

## Mocking strategy

The tests mock the LLM at the agent node level, routing responses based on the system prompt header:

```python
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
```

The mock is patched into each agent node:

```python
with patch("app.agents.nodes.compliance.get_llm", return_value=mock_llm), \
     patch("app.agents.nodes.security.get_llm", return_value=mock_llm), \
     patch("app.agents.nodes.engineering.get_llm", return_value=mock_llm), \
     patch("app.agents.nodes.moderator.get_llm", return_value=mock_llm):
    result = await graph.ainvoke(_sample_input())
```

This approach tests the full graph topology and state flow without making actual LLM calls.

---

## Manual API testing

**File:** `backend/requests.http`

An HTTP client file with 7 pre-built test requests:

1. `GET /health` — Health check
2. `POST /api/analyze` — $2.4M wire to Cyprus (sync)
3. `POST /api/analyze` — 47-transaction velocity alert (sync)
4. `POST /api/analyze` — New device login (sync)
5. `POST /api/analyze` — $9,800 cash deposit structuring (sync)
6. `POST /api/analyze/stream` — Wire transfer (SSE)
7. `POST /api/analyze/stream` — Suspicious login (SSE)

Use with VS Code REST Client extension or IntelliJ HTTP Client.

---

## Test data

The test fixtures provide representative scenarios:

```python
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
        "client_memory": "Known client since 2019. Regular EU transfers.",
        "analyses": [],
        "moderator_synthesis": None,
    }
```
