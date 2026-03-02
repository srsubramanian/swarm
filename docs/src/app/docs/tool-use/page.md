---
title: Tool use
---

Each domain agent uses an internal tool-calling loop to gather evidence before forming its assessment. This page covers the tool architecture, available tools, mock data strategy, and how to add new tools. {% .lead %}

---

## Overview

Instead of a single LLM call, each agent runs a **two-phase pipeline**:

1. **Evidence gathering** — The LLM calls domain-specific tools (sanctions lookup, IP reputation check, SDK version status, etc.), receives results, and iterates until it has enough evidence
2. **Structured extraction** — A final LLM call with all gathered evidence produces a validated `AgentAnalysis`

The LangGraph topology is unchanged — the tool loop is entirely internal to each agent node function. The moderator does not use tools.

```shell
Agent Node
├── Phase 1: Tool Loop (bind_tools)
│   ├── LLM decides which tools to call
│   ├── Execute tools, append results
│   └── Repeat (up to 5 iterations)
└── Phase 2: Extraction (with_structured_output)
    └── Final AgentAnalysis with all evidence in context
```

---

## Tool registry

All tools are registered in `backend/app/agents/tools/__init__.py`:

```python
from app.agents.tools.compliance_tools import COMPLIANCE_TOOLS
from app.agents.tools.security_tools import SECURITY_TOOLS
from app.agents.tools.engineering_tools import ENGINEERING_TOOLS

TOOLS_BY_DOMAIN = {
    "compliance": COMPLIANCE_TOOLS,
    "security": SECURITY_TOOLS,
    "engineering": ENGINEERING_TOOLS,
}
```

Each domain has exactly 3 tools (9 total). Tools use the `@tool` decorator from `langchain_core.tools`, accept snake_case parameters, and return JSON strings.

---

## Compliance tools

**File:** `backend/app/agents/tools/compliance_tools.py`

### search_sanctions_list(name, country)

Searches OFAC, EU, and UN sanctions lists. Returns partial matches with scores (not just yes/no), jurisdiction risk level, and FATF status.

| Input | Result |
|-------|--------|
| `("Meridian Holdings", "CY")` | 1 partial match (score 0.72), jurisdiction risk: medium, FATF: monitored |
| `("Atlas Capital", "TR")` | 0 matches, jurisdiction risk: elevated, FATF: grey_list |
| `("Test Entity", "IR")` | 1 exact match (score 0.95), jurisdiction risk: critical, FATF: black_list |
| Unknown country | 0 matches, jurisdiction risk: low, FATF: compliant |

### get_client_transaction_history(client_name)

Retrieves recent transaction patterns, account age, risk rating, and flags. Has entries for all 4 scenario clients.

| Client | Key data |
|--------|----------|
| Meridian Holdings | 6yr account, medium risk, avg $850K/mo, Cyprus transfer previously cleared after EDD |
| Riverside Deli LLC | 3yr account, low risk, avg $18K/mo — but deposits tripled and all near $10K CTR threshold |
| Quantum Dynamics | 4yr account, low risk, consistent payroll batches of 40-60 ACH transactions |
| Atlas Capital | 7yr account, medium risk, significant international wire activity from NYC |

### check_regulatory_thresholds(event_type, amount, jurisdiction)

Rule-based logic that checks regulatory reporting requirements:

| Rule | Trigger condition |
|------|-------------------|
| `CTR_FILING` | Cash deposit >= $10,000 |
| `STRUCTURING_SUSPICION` | Cash deposit $8,000-$9,999 |
| `LARGE_WIRE_EDD` | Wire transfer >= $1,000,000 |
| `FATF_GREY_LIST` | Destination in FATF grey list (TR, MM, PH, etc.) |
| `FATF_BLACK_LIST` | Destination in FATF black list (IR, KP) |

---

## Security tools

**File:** `backend/app/agents/tools/security_tools.py`

### lookup_ip_reputation(ip_address)

Threat intelligence lookup for IP addresses. Returns threat score (0-100), ISP info, VPN/proxy/Tor detection, and abuse history.

| IP | Result |
|----|--------|
| `185.220.101.42` | Threat score 78, Tor exit node, 142 abuse reports in 30 days |
| `91.108.56.130` | Threat score 35, Turk Telekom residential, no abuse history |
| `203.0.113.50` | Threat score 5, Comcast Business (Atlas Capital NYC office) |
| Unknown IP | Threat score 10, low risk default |

### check_geo_velocity(client_name, current_location)

Impossible travel detection. Compares current location to last known login and calculates whether the distance could have been traveled in the elapsed time.

| Client + Location | Result |
|-------------------|--------|
| Atlas Capital → Istanbul, Turkey | Impossible travel: 5,013 miles in 6.7 hours (min flight: 10.5h) |
| Meridian Holdings → London, UK | Typical location, low risk |
| Unknown client | Returns "unknown_client" analysis |

### get_device_fingerprint_history(client_name)

Device trust assessment. Returns known devices, new unverified devices, and risk indicators.

| Client | Result |
|--------|--------|
| Atlas Capital | 1 known desktop (NYC), 1 new unverified mobile (Istanbul) — 3 risk indicators |
| Meridian Holdings | 1 known desktop, no new devices, no risk |
| Quantum Dynamics | 1 known server (API client), clean |

---

## Engineering tools

**File:** `backend/app/agents/tools/engineering_tools.py`

### check_sdk_version_status(version)

SDK lifecycle and vulnerability check. Returns version status, known CVEs, deprecation notices, and upgrade urgency.

| Version | Status | CVEs | Urgency |
|---------|--------|------|---------|
| `3.1.2` | current | 0 | none |
| `3.0` | deprecated | 1 (medium — HMAC timing side-channel) | high |
| `2.9.1` | end_of_life | 2 (high — RCE, medium — HMAC) | critical |
| Unknown | unknown | 0 | unknown |

### get_api_rate_limit_status(client_id)

Rate limit monitoring and burst detection.

| Client | Tier | Burst? | Notes |
|--------|------|--------|-------|
| Quantum Dynamics | enterprise | Yes (3x avg) | Within limits, consistent with batch processing |
| Meridian Holdings | business | No | Normal usage (2 RPM) |
| Atlas Capital | enterprise | No | Normal usage (8 RPM) |
| Riverside Deli LLC | basic | No | Minimal usage (1 RPM) |

### validate_transaction_metadata(reference_id)

Reference ID format validation, duplicate check, and correlation chain analysis.

| Reference | Valid? | Chain | Notes |
|-----------|--------|-------|-------|
| `INV-2024-0847` | Yes | 3 steps (ERP → Treasury → SWIFT) | Complete correlation |
| `BATCH-20260301-QD` | Yes | 2 steps (Payroll → ACH Gateway) | Valid batch reference |
| Unknown format | No | Empty | Invalid format |

---

## Mock data strategy

All tools return **simulated mock data** — realistic enough for demos, with no external API dependencies. The data is keyed on the 4 built-in scenarios:

- **Wire transfer** (Meridian Holdings → Cyprus) — Sanctions partial match, large wire EDD, Tor exit node IP
- **Velocity alert** (Quantum Dynamics) — Normal payroll batch, deprecated SDK, burst within limits
- **Security alert** (Atlas Capital → Istanbul) — Impossible travel, new device, residential Turkish IP, EOL SDK with critical CVEs
- **Cash deposit** (Riverside Deli) — Structuring suspicion, sudden volume increase, deposits near CTR threshold

Unknown inputs always return sensible defaults (low risk, empty results) rather than errors.

### Swapping to real implementations

Each tool has a clean interface — same parameters, same JSON return format. To connect to a real API:

1. Replace the mock lookup dict with an API call
2. Parse the API response into the same JSON structure
3. No changes needed to the agent code, tool loop, or tests (beyond updating expected mock values)

---

## The tool loop helper

**File:** `backend/app/agents/tool_loop.py`

The shared `run_agent_with_tools()` function handles the two-phase pipeline for all three agents:

```python
async def run_agent_with_tools(
    state: SwarmState,
    agent_role: str,
    system_prompt: str,
    event_message: str,
    tools: list,
    max_iterations: int = 5,
) -> dict:
```

### Phase 1: Evidence gathering

1. `llm.bind_tools(tools)` — Adds tool definitions to the LLM request
2. Messages start with `[SystemMessage(prompt), HumanMessage(event)]`
3. Loop up to `max_iterations`:
   - `await llm_with_tools.ainvoke(messages)` → AIMessage
   - If no `tool_calls` → break (LLM has enough evidence)
   - For each tool call: look up in `tool_map`, execute, append `ToolMessage`
   - Unknown tool name → return error string (LLM self-corrects)
   - Tool exception → return error string

### Phase 2: Structured extraction

1. Append extraction prompt: "Based on your analysis and tool results, provide your final structured assessment."
2. `llm.with_structured_output(AgentAnalysis)` — Sets up JSON schema enforcement
3. `await structured_llm.ainvoke(messages)` → Validated `AgentAnalysis`
4. Set `agent_role`, return `{"analyses": [result]}`

### Why two phases?

`bind_tools()` and `with_structured_output()` serve different purposes and can't be combined:
- **Tool phase**: The LLM needs tool definitions in the request to know what it can call
- **Extraction phase**: The LLM needs JSON schema enforcement to produce validated structured output

---

## Adding a new tool

To add a tool to an existing agent:

1. Define the tool in the appropriate `*_tools.py` file:

```python
@tool
def my_new_tool(param1: str, param2: int) -> str:
    """Description of what this tool does.

    Args:
        param1: Description of param1.
        param2: Description of param2.
    """
    result = {"data": "mock response"}
    return json.dumps(result, indent=2)
```

2. Add it to the domain's tool list:

```python
COMPLIANCE_TOOLS = [search_sanctions_list, ..., my_new_tool]
```

3. Document it in the agent's prompt template:

```markdown
## Available Tools
...
- **my_new_tool(param1, param2)** — Description of what this tool does.
```

4. Add tests in `test_tool_agents.py`:

```python
def test_my_new_tool_known_input(self):
    result = json.loads(my_new_tool.invoke({"param1": "test", "param2": 42}))
    assert result["data"] == "mock response"
```

No changes needed to the tool loop, agent nodes, orchestrator, or graph topology.
