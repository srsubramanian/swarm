---
title: Testing
---

SwarmOps uses pytest with mocked LLM calls to test graph topology, agent orchestration, tool use, and API endpoints without requiring AWS Bedrock access. {% .lead %}

---

## Running tests

```shell
cd backend
uv run pytest tests/ -v
```

Or run a specific test file:

```shell
uv run pytest tests/test_orchestrator.py -v
uv run pytest tests/test_tool_agents.py -v
```

---

## Test structure

Tests are spread across four files (69 tests total):

- `backend/tests/test_orchestrator.py` — Graph topology, mocked LLM execution, API response (6 tests)
- `backend/tests/test_queue.py` — Scenario registry and queue endpoint tests (11 tests)
- `backend/tests/test_conversations.py` — Store, builder, history endpoints, camelCase serialization (18 tests)
- `backend/tests/test_tool_agents.py` — Tool unit tests, tool loop tests, full graph integration with tools (34 tests)

### test_orchestrator.py

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

### test_tool_agents.py

Tests the deep agent tool use system across three layers:

**Layer 1 — Tool unit tests** (26 tests):

Each tool is tested for known inputs and sensible defaults for unknown inputs:

```python
class TestComplianceTools:
    def test_sanctions_cyprus_partial_match(self):
        result = json.loads(search_sanctions_list.invoke({...}))
        assert result["match_count"] == 1
        assert result["jurisdiction_risk"] == "medium"

    def test_regulatory_structuring_detection(self):
        result = json.loads(check_regulatory_thresholds.invoke({...}))
        assert result["triggered_rules"][0]["rule"] == "STRUCTURING_SUSPICION"

class TestSecurityTools:
    def test_ip_tor_exit_node(self):
        result = json.loads(lookup_ip_reputation.invoke({...}))
        assert result["is_tor"] is True
        assert result["threat_score"] == 78

    def test_geo_velocity_atlas_impossible_travel(self):
        result = json.loads(check_geo_velocity.invoke({...}))
        assert result["impossible_travel"] is True

class TestEngineeringTools:
    def test_sdk_eol_with_critical_vulns(self):
        result = json.loads(check_sdk_version_status.invoke({...}))
        assert result["status"] == "end_of_life"
        assert len(result["known_cves"]) == 2
```

**Layer 2 — Tool loop tests** (3 tests):

Tests the `run_agent_with_tools()` helper with mocked LLM:

```python
class TestToolLoop:
    async def test_agent_with_tool_calls(self):
        """Agent makes tool calls, then produces structured output."""
    async def test_agent_no_tool_calls(self):
        """Agent makes zero tool calls — loop exits immediately."""
    async def test_agent_hallucinated_tool_name(self):
        """Agent calls a tool that doesn't exist — gets error, self-corrects."""
```

**Layer 3 — Full graph integration** (1 test):

Full graph with mocked tool-calling agents produces valid synthesis:

```python
class TestFullGraphWithTools:
    async def test_full_graph_produces_valid_synthesis(self):
        result = await graph.ainvoke(state)
        assert len(result["analyses"]) == 3
        assert result["moderator_synthesis"].status == "HOLD RECOMMENDED"
        assert mock_llm.bind_tools.call_count == 3  # one per agent
```

**Tool registry tests** (4 tests):

Validates the `TOOLS_BY_DOMAIN` registry:

```python
class TestToolRegistry:
    def test_all_domains_registered(self): ...
    def test_each_domain_has_three_tools(self): ...
    def test_tools_have_names(self): ...
```

---

### test_conversations.py

Tests the in-memory store, conversation builder, and history endpoints. Uses an `autouse` fixture to clear the store between tests.

**TestInMemoryStore** — Unit tests for `InMemoryConversationStore`:

```python
class TestInMemoryStore:
    def test_save_and_get(self): ...
    def test_list_newest_first(self): ...
    def test_clear_returns_count(self): ...
    def test_overwrite_by_id(self): ...
    def test_get_nonexistent_returns_none(self): ...
```

**TestBuildConversation** — Validates `build_conversation()` output:

```python
class TestBuildConversation:
    def test_builds_valid_record(self): ...
    def test_agents_populated(self): ...
    def test_messages_populated(self): ...
    def test_moderator_summary_populated(self): ...
    def test_action_required_populated(self): ...
    def test_client_memory_populated(self): ...
    def test_camel_case_serialization(self): ...
```

**TestConversationEndpoints** — Integration tests for the full flow:

```python
class TestConversationEndpoints:
    async def test_queue_persists_and_list_returns(self): ...
    async def test_get_by_id(self): ...
    async def test_get_nonexistent_returns_404(self): ...
    async def test_delete_clears_all(self): ...
    async def test_analyze_does_not_persist(self): ...
    async def test_queue_response_has_camel_case_keys(self): ...
```

---

## Mocking strategy

The tests mock the LLM at two patch points:

1. **`app.agents.tool_loop.get_llm`** — Used by all three domain agents (they delegate to `run_agent_with_tools()` which imports `get_llm`)
2. **`app.agents.nodes.moderator.get_llm`** — Used by the moderator (which still calls `get_llm` directly)

The mock LLM supports both `bind_tools()` and `with_structured_output()`:

```python
def _create_mock_llm():
    async def mock_structured_ainvoke(messages):
        system_content = messages[0].content
        if system_content.startswith("# Moderator"):
            return _mock_moderator_synthesis()
        elif system_content.startswith("# Compliance"):
            return _mock_agent_analysis("compliance")
        # ... security, engineering ...

    mock_structured = AsyncMock()
    mock_structured.ainvoke = mock_structured_ainvoke

    # Tool-bound LLM returns AIMessage with no tool_calls (loop exits immediately)
    mock_tool_bound = AsyncMock()
    mock_tool_bound.ainvoke = AsyncMock(return_value=AIMessage(content="Analysis complete."))

    mock_llm = MagicMock()
    mock_llm.with_structured_output.return_value = mock_structured
    mock_llm.bind_tools.return_value = mock_tool_bound
    return mock_llm
```

The mock is patched at two locations (down from four before tool use):

```python
with patch("app.agents.tool_loop.get_llm", return_value=mock_llm), \
     patch("app.agents.nodes.moderator.get_llm", return_value=mock_llm):
    result = await graph.ainvoke(_sample_input())
```

The tool-bound mock returns an `AIMessage` with no `tool_calls`, so the tool loop exits immediately in tests. This tests the full graph topology and state flow without making actual LLM or tool calls.

---

### test_queue.py

Tests the scenario registry and queue endpoints, organized into two classes:

**TestScenarios** — Validates the scenario registry:

```python
class TestScenarios:
    def test_all_four_scenarios_exist(self): ...
    def test_scenarios_are_valid_requests(self): ...
    def test_wire_transfer_has_expected_data(self): ...
    def test_velocity_alert_has_expected_data(self): ...
    def test_security_alert_has_expected_data(self): ...
    def test_cash_deposit_has_expected_data(self): ...
```

**TestQueueEndpoints** — API integration tests using the same mocked-LLM pattern:

```python
class TestQueueEndpoints:
    async def test_list_scenarios(self): ...
    async def test_queue_sync_returns_full_analysis(self): ...
    async def test_queue_unknown_scenario_returns_404(self): ...
    async def test_queue_stream_unknown_scenario_returns_404(self): ...
    async def test_queue_delegates_to_analyze(self): ...
```

---

## Manual API testing

**File:** `backend/requests.http`

An HTTP client file with pre-built test requests:

**Analyze endpoints** (require Bedrock):

1. `GET /health` — Health check
2. `POST /api/analyze` — $2.4M wire to Cyprus (sync)
3. `POST /api/analyze` — 47-transaction velocity alert (sync)
4. `POST /api/analyze` — New device login (sync)
5. `POST /api/analyze` — $9,800 cash deposit structuring (sync)
6. `POST /api/analyze/stream` — Wire transfer (SSE)
7. `POST /api/analyze/stream` — Suspicious login (SSE)

**Queue endpoints** (submit scenarios by name):

8. `GET /api/queue/scenarios` — List available scenarios
9. `POST /api/queue` — Wire transfer (sync)
10. `POST /api/queue` — Velocity alert (sync)
11. `POST /api/queue` — Security alert (sync)
12. `POST /api/queue` — Cash deposit (sync)
13. `POST /api/queue/stream` — Wire transfer (SSE)
14. `POST /api/queue/stream` — Security alert (SSE)

**History endpoints:**

15. `GET /api/conversations` — List all persisted conversations
16. `GET /api/conversations/{id}` — Get a single conversation by ID
17. `DELETE /api/conversations` — Clear all persisted conversations

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
