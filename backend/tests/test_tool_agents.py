"""Tests for deep agent tools, tool loop, and integration.

Layer 1: Tool unit tests — each tool returns valid JSON for known/unknown inputs
Layer 2: Tool loop tests — agent makes tool calls, zero iteration, error handling
Layer 3: Full graph integration — mocked tool-calling agents produce valid synthesis
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.messages import AIMessage, ToolCall

from app.agents.schemas import ActionItem, AgentAnalysis, ModeratorSynthesis
from app.agents.tool_loop import run_agent_with_tools
from app.agents.tools import TOOLS_BY_DOMAIN
from app.agents.tools.compliance_tools import (
    COMPLIANCE_TOOLS,
    check_regulatory_thresholds,
    get_client_transaction_history,
    search_sanctions_list,
)
from app.agents.tools.engineering_tools import (
    ENGINEERING_TOOLS,
    check_sdk_version_status,
    get_api_rate_limit_status,
    validate_transaction_metadata,
)
from app.agents.tools.security_tools import (
    SECURITY_TOOLS,
    check_geo_velocity,
    get_device_fingerprint_history,
    lookup_ip_reputation,
)


# ============================================================
# Layer 1: Tool Unit Tests
# ============================================================


class TestComplianceTools:
    """Tests for compliance domain tools."""

    def test_sanctions_cyprus_partial_match(self):
        result = json.loads(search_sanctions_list.invoke({"name": "Meridian Holdings", "country": "CY"}))
        assert result["match_count"] == 1
        assert result["jurisdiction_risk"] == "medium"
        assert result["fatf_status"] == "monitored"
        assert result["matches"][0]["score"] == 0.72

    def test_sanctions_turkey_grey_list(self):
        result = json.loads(search_sanctions_list.invoke({"name": "Atlas Capital", "country": "TR"}))
        assert result["match_count"] == 0
        assert result["jurisdiction_risk"] == "elevated"
        assert result["fatf_status"] == "grey_list"

    def test_sanctions_unknown_country_low_risk(self):
        result = json.loads(search_sanctions_list.invoke({"name": "Test Corp", "country": "US"}))
        assert result["match_count"] == 0
        assert result["jurisdiction_risk"] == "low"
        assert result["fatf_status"] == "compliant"

    def test_sanctions_iran_critical(self):
        result = json.loads(search_sanctions_list.invoke({"name": "Test Entity", "country": "IR"}))
        assert result["match_count"] == 1
        assert result["jurisdiction_risk"] == "critical"
        assert result["fatf_status"] == "black_list"

    def test_transaction_history_meridian(self):
        result = json.loads(get_client_transaction_history.invoke({"client_name": "Meridian Holdings"}))
        assert result["account_age_years"] == 6
        assert result["risk_rating"] == "medium"
        assert len(result["recent_transactions"]) == 3

    def test_transaction_history_riverside_flags(self):
        result = json.loads(get_client_transaction_history.invoke({"client_name": "Riverside Deli LLC"}))
        assert "sudden_volume_increase" in result["flags"]
        assert "deposits_near_ctr_threshold" in result["flags"]

    def test_transaction_history_unknown_client(self):
        result = json.loads(get_client_transaction_history.invoke({"client_name": "Unknown Corp"}))
        assert result["risk_rating"] == "unknown"
        assert result["recent_transactions"] == []

    def test_regulatory_structuring_detection(self):
        result = json.loads(check_regulatory_thresholds.invoke({
            "event_type": "cash_deposit", "amount": 9800, "jurisdiction": "US"
        }))
        assert result["rules_triggered"] == 1
        assert result["triggered_rules"][0]["rule"] == "STRUCTURING_SUSPICION"
        assert not result["compliant"]

    def test_regulatory_ctr_threshold(self):
        result = json.loads(check_regulatory_thresholds.invoke({
            "event_type": "cash_deposit", "amount": 15000, "jurisdiction": "US"
        }))
        rules = [r["rule"] for r in result["triggered_rules"]]
        assert "CTR_FILING" in rules

    def test_regulatory_large_wire_edd(self):
        result = json.loads(check_regulatory_thresholds.invoke({
            "event_type": "wire_transfer", "amount": 2400000, "jurisdiction": "CY"
        }))
        rules = [r["rule"] for r in result["triggered_rules"]]
        assert "LARGE_WIRE_EDD" in rules

    def test_regulatory_fatf_grey_list(self):
        result = json.loads(check_regulatory_thresholds.invoke({
            "event_type": "wire_transfer", "amount": 100000, "jurisdiction": "TR"
        }))
        rules = [r["rule"] for r in result["triggered_rules"]]
        assert "FATF_GREY_LIST" in rules


class TestSecurityTools:
    """Tests for security domain tools."""

    def test_ip_tor_exit_node(self):
        result = json.loads(lookup_ip_reputation.invoke({"ip_address": "185.220.101.42"}))
        assert result["threat_score"] == 78
        assert result["is_tor"] is True
        assert result["threat_level"] == "high"

    def test_ip_istanbul_residential(self):
        result = json.loads(lookup_ip_reputation.invoke({"ip_address": "91.108.56.130"}))
        assert result["threat_score"] == 35
        assert result["threat_level"] == "moderate"
        assert result["is_tor"] is False
        assert result["city"] == "Istanbul"

    def test_ip_unknown_low_risk(self):
        result = json.loads(lookup_ip_reputation.invoke({"ip_address": "1.2.3.4"}))
        assert result["threat_score"] == 10
        assert result["threat_level"] == "low"

    def test_geo_velocity_atlas_impossible_travel(self):
        result = json.loads(check_geo_velocity.invoke({
            "client_name": "Atlas Capital", "current_location": "Istanbul, Turkey"
        }))
        assert result["impossible_travel"] is True
        assert result["distance_miles"] == 5013
        assert result["risk_assessment"] == "high"

    def test_geo_velocity_meridian_typical(self):
        result = json.loads(check_geo_velocity.invoke({
            "client_name": "Meridian Holdings", "current_location": "London, UK"
        }))
        assert result["is_typical_location"] is True
        assert result["risk_assessment"] == "low"

    def test_geo_velocity_unknown_client(self):
        result = json.loads(check_geo_velocity.invoke({
            "client_name": "Unknown Corp", "current_location": "London, UK"
        }))
        assert result["analysis"] == "unknown_client"

    def test_device_fingerprint_atlas_new_device(self):
        result = json.loads(get_device_fingerprint_history.invoke({"client_name": "Atlas Capital"}))
        assert result["total_known_devices"] == 1
        assert result["total_new_devices"] == 1
        assert len(result["risk_indicators"]) > 0
        assert result["new_devices"][0]["trust_level"] == "unverified"

    def test_device_fingerprint_meridian_clean(self):
        result = json.loads(get_device_fingerprint_history.invoke({"client_name": "Meridian Holdings"}))
        assert result["total_new_devices"] == 0
        assert result["risk_indicators"] == []


class TestEngineeringTools:
    """Tests for engineering domain tools."""

    def test_sdk_current_version(self):
        result = json.loads(check_sdk_version_status.invoke({"version": "3.1.2"}))
        assert result["status"] == "current"
        assert result["known_cves"] == []
        assert result["upgrade_urgency"] == "none"

    def test_sdk_deprecated_with_cve(self):
        result = json.loads(check_sdk_version_status.invoke({"version": "3.0"}))
        assert result["status"] == "deprecated"
        assert len(result["known_cves"]) == 1
        assert result["upgrade_urgency"] == "high"

    def test_sdk_eol_with_critical_vulns(self):
        result = json.loads(check_sdk_version_status.invoke({"version": "2.9.1"}))
        assert result["status"] == "end_of_life"
        assert len(result["known_cves"]) == 2
        assert result["upgrade_urgency"] == "critical"

    def test_sdk_unknown_version(self):
        result = json.loads(check_sdk_version_status.invoke({"version": "99.0"}))
        assert result["status"] == "unknown"

    def test_rate_limit_quantum_burst(self):
        result = json.loads(get_api_rate_limit_status.invoke({"client_id": "Quantum Dynamics"}))
        assert result["burst_detected"] is True
        assert result["throttled"] is False
        assert result["burst_details"]["classification"] == "within_limits_but_bursty"

    def test_rate_limit_unknown_client(self):
        result = json.loads(get_api_rate_limit_status.invoke({"client_id": "Unknown"}))
        assert result["tier"] == "unknown"

    def test_metadata_valid_reference(self):
        result = json.loads(validate_transaction_metadata.invoke({"reference_id": "INV-2024-0847"}))
        assert result["format_valid"] is True
        assert result["is_duplicate"] is False
        assert len(result["correlation_chain"]) == 3

    def test_metadata_unknown_format(self):
        result = json.loads(validate_transaction_metadata.invoke({"reference_id": "GARBAGE-123"}))
        assert result["format_valid"] is False
        assert result["metadata_consistency"] == "invalid_format"


class TestToolRegistry:
    """Tests for the tools registry."""

    def test_all_domains_registered(self):
        assert set(TOOLS_BY_DOMAIN.keys()) == {"compliance", "security", "engineering"}

    def test_each_domain_has_three_tools(self):
        for domain, tools in TOOLS_BY_DOMAIN.items():
            assert len(tools) == 3, f"{domain} has {len(tools)} tools, expected 3"

    def test_tools_have_names(self):
        for domain, tools in TOOLS_BY_DOMAIN.items():
            for tool in tools:
                assert tool.name, f"Tool in {domain} has no name"
                assert tool.description, f"Tool {tool.name} in {domain} has no description"


# ============================================================
# Layer 2: Tool Loop Tests
# ============================================================


def _sample_state() -> dict:
    return {
        "event_type": "wire_transfer",
        "title": "$2.4M Wire to Cyprus",
        "client_name": "Meridian Holdings",
        "event_data": {"amount": 2_400_000, "currency": "USD"},
        "client_memory": "",
        "analyses": [],
        "moderator_synthesis": None,
    }


def _mock_analysis(role: str = "compliance") -> AgentAnalysis:
    return AgentAnalysis(
        agent_role=role,
        position="Mock position",
        analysis="Mock analysis",
        risk_level="high",
        confidence="medium",
        key_findings=["finding 1"],
        recommended_action="Mock recommendation",
    )


class TestToolLoop:
    """Tests for the run_agent_with_tools() helper."""

    @pytest.mark.asyncio
    async def test_agent_with_tool_calls(self):
        """Agent makes tool calls, then produces structured output."""
        # First call: LLM returns tool call
        tool_call_response = AIMessage(
            content="",
            tool_calls=[
                ToolCall(name="search_sanctions_list", args={"name": "Test", "country": "CY"}, id="call_1")
            ],
        )
        # Second call: LLM returns no tool calls (done gathering evidence)
        no_tool_response = AIMessage(content="I have gathered enough evidence.")

        mock_tool_bound = AsyncMock()
        mock_tool_bound.ainvoke = AsyncMock(side_effect=[tool_call_response, no_tool_response])

        mock_structured = AsyncMock()
        mock_structured.ainvoke = AsyncMock(return_value=_mock_analysis())

        mock_llm = MagicMock()
        mock_llm.bind_tools.return_value = mock_tool_bound
        mock_llm.with_structured_output.return_value = mock_structured

        with patch("app.agents.tool_loop.get_llm", return_value=mock_llm):
            result = await run_agent_with_tools(
                state=_sample_state(),
                agent_role="compliance",
                system_prompt="# Compliance Agent",
                event_message="Test event",
                tools=COMPLIANCE_TOOLS,
            )

        assert len(result["analyses"]) == 1
        assert result["analyses"][0].agent_role == "compliance"
        # bind_tools was called with compliance tools
        mock_llm.bind_tools.assert_called_once_with(COMPLIANCE_TOOLS)
        # Tool-bound LLM was called twice (tool call + no tool call)
        assert mock_tool_bound.ainvoke.call_count == 2
        # Structured extraction was called once
        mock_structured.ainvoke.assert_called_once()

    @pytest.mark.asyncio
    async def test_agent_no_tool_calls(self):
        """Agent makes zero tool calls — loop exits immediately."""
        no_tool_response = AIMessage(content="No tools needed for this analysis.")

        mock_tool_bound = AsyncMock()
        mock_tool_bound.ainvoke = AsyncMock(return_value=no_tool_response)

        mock_structured = AsyncMock()
        mock_structured.ainvoke = AsyncMock(return_value=_mock_analysis())

        mock_llm = MagicMock()
        mock_llm.bind_tools.return_value = mock_tool_bound
        mock_llm.with_structured_output.return_value = mock_structured

        with patch("app.agents.tool_loop.get_llm", return_value=mock_llm):
            result = await run_agent_with_tools(
                state=_sample_state(),
                agent_role="security",
                system_prompt="# Security Agent",
                event_message="Test event",
                tools=SECURITY_TOOLS,
            )

        assert len(result["analyses"]) == 1
        assert result["analyses"][0].agent_role == "security"
        # Tool-bound LLM was called once, then loop exited
        assert mock_tool_bound.ainvoke.call_count == 1

    @pytest.mark.asyncio
    async def test_agent_hallucinated_tool_name(self):
        """Agent calls a tool that doesn't exist — gets error, self-corrects."""
        # First call: LLM hallucinates a tool name
        bad_tool_response = AIMessage(
            content="",
            tool_calls=[
                ToolCall(name="nonexistent_tool", args={"query": "test"}, id="call_bad")
            ],
        )
        # Second call: LLM gives up on tools
        no_tool_response = AIMessage(content="I'll proceed without that tool.")

        mock_tool_bound = AsyncMock()
        mock_tool_bound.ainvoke = AsyncMock(side_effect=[bad_tool_response, no_tool_response])

        mock_structured = AsyncMock()
        mock_structured.ainvoke = AsyncMock(return_value=_mock_analysis("engineering"))

        mock_llm = MagicMock()
        mock_llm.bind_tools.return_value = mock_tool_bound
        mock_llm.with_structured_output.return_value = mock_structured

        with patch("app.agents.tool_loop.get_llm", return_value=mock_llm):
            result = await run_agent_with_tools(
                state=_sample_state(),
                agent_role="engineering",
                system_prompt="# Engineering Agent",
                event_message="Test event",
                tools=ENGINEERING_TOOLS,
            )

        assert len(result["analyses"]) == 1
        assert result["analyses"][0].agent_role == "engineering"


# ============================================================
# Layer 3: Full Graph Integration
# ============================================================


class TestFullGraphWithTools:
    """Full graph run with mocked tool-calling agents."""

    @pytest.mark.asyncio
    async def test_full_graph_produces_valid_synthesis(self):
        """Full graph with deep agents produces valid moderator synthesis."""
        from app.agents.orchestrator import graph

        def _mock_agent(role: str) -> AgentAnalysis:
            return AgentAnalysis(
                agent_role=role,
                position=f"Deep {role} position with tool evidence",
                analysis=f"Deep {role} analysis based on tool results.",
                risk_level="high",
                confidence="high",
                key_findings=[f"{role} tool finding 1", f"{role} tool finding 2"],
                recommended_action=f"Deep {role} recommendation",
            )

        mock_synthesis = ModeratorSynthesis(
            status="HOLD RECOMMENDED",
            consensus="All agents converge on high risk with tool-backed evidence.",
            dissent="None",
            risk_level="high",
            risk_assessment="High risk — tool evidence supports all agent positions.",
            key_decisions=["Tool-verified sanctions risk", "Tool-verified anomalies"],
            next_steps=["Hold pending review", "Request additional docs"],
            action_items=[
                ActionItem(label="Hold Transfer", variant="primary", rationale="Tool evidence supports hold"),
                ActionItem(label="Escalate", variant="danger", rationale="Multiple red flags"),
            ],
        )

        async def mock_structured_ainvoke(messages):
            system_content = messages[0].content
            if system_content.startswith("# Moderator"):
                return mock_synthesis
            elif system_content.startswith("# Compliance"):
                return _mock_agent("compliance")
            elif system_content.startswith("# Security"):
                return _mock_agent("security")
            elif system_content.startswith("# Engineering"):
                return _mock_agent("engineering")
            raise ValueError(f"Unexpected prompt: {system_content[:100]}")

        mock_structured = AsyncMock()
        mock_structured.ainvoke = mock_structured_ainvoke

        mock_tool_bound = AsyncMock()
        mock_tool_bound.ainvoke = AsyncMock(return_value=AIMessage(content="Analysis complete."))

        mock_llm = MagicMock()
        mock_llm.with_structured_output.return_value = mock_structured
        mock_llm.bind_tools.return_value = mock_tool_bound

        state = {
            "event_type": "wire_transfer",
            "title": "$2.4M Wire to Cyprus",
            "client_name": "Meridian Holdings",
            "event_data": {"amount": 2_400_000, "currency": "USD"},
            "client_memory": "",
            "analyses": [],
            "moderator_synthesis": None,
        }

        with patch("app.agents.tool_loop.get_llm", return_value=mock_llm), \
             patch("app.agents.nodes.moderator.get_llm", return_value=mock_llm):
            result = await graph.ainvoke(state)

        # 3 analyses from deep agents
        assert len(result["analyses"]) == 3
        roles = {a.agent_role for a in result["analyses"]}
        assert roles == {"compliance", "security", "engineering"}

        # Moderator synthesis
        synthesis = result["moderator_synthesis"]
        assert synthesis is not None
        assert synthesis.status == "HOLD RECOMMENDED"
        assert synthesis.risk_level == "high"
        assert len(synthesis.action_items) == 2

        # bind_tools was called 3 times (once per agent)
        assert mock_llm.bind_tools.call_count == 3
