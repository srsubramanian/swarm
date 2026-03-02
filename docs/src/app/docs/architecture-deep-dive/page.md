---
title: Architecture deep dive
---

A comprehensive technical walkthrough of how SwarmOps orchestrates multi-agent AI analysis — from the LangGraph framework and state management to structured LLM output, parallel execution, and the end-to-end event pipeline. {% .lead %}

---

## LangGraph: the orchestration framework

SwarmOps uses [LangGraph](https://langchain-ai.github.io/langgraph/) to orchestrate its multi-agent pipeline. LangGraph is a framework for building stateful, graph-based workflows on top of LangChain. It models computation as a **directed graph** where:

- **Nodes** are async Python functions that read shared state and return partial updates
- **Edges** define execution order and parallelism
- **State** is a typed dictionary threaded through every node

LangGraph handles the hard parts — parallel dispatch, state merging, streaming, and error propagation — so the application code only needs to define the graph topology and implement each node's logic.

### Why LangGraph (not raw asyncio)

You could run three LLM calls with `asyncio.gather()`, but LangGraph provides:

| Capability | Raw asyncio | LangGraph |
|---|---|---|
| Parallel execution | Manual `gather()` | Automatic from edge topology |
| State merging | Manual dict merging | Typed reducers (`operator.add`) |
| Streaming | Custom SSE plumbing | Built-in `astream(stream_mode="updates")` |
| Retry / error isolation | Manual try/except per call | Per-node error handling |
| Visualization | None | Built-in graph visualization |
| Extensibility | Rewrite orchestration | Add a node, add an edge |

---

## The SwarmOps graph

The entire agent pipeline is defined in a single file (`backend/app/agents/orchestrator.py`) in under 50 lines:

```python
from langgraph.graph import END, START, StateGraph

builder = StateGraph(SwarmState)

# Five nodes
builder.add_node("prepare", prepare_context)
builder.add_node("compliance", compliance_agent)
builder.add_node("security", security_agent)
builder.add_node("engineering", engineering_agent)
builder.add_node("moderator", moderator_node)

# Edges define the topology
builder.add_edge(START, "prepare")

# Fan-out: prepare → 3 agents in parallel
builder.add_edge("prepare", "compliance")
builder.add_edge("prepare", "security")
builder.add_edge("prepare", "engineering")

# Fan-in: all agents → moderator
builder.add_edge("compliance", "moderator")
builder.add_edge("security", "moderator")
builder.add_edge("engineering", "moderator")

builder.add_edge("moderator", END)

graph = builder.compile()
```

The compiled graph is a **module-level singleton** — built once at import time, reused for every request. This avoids the overhead of rebuilding the graph on each call.

### Topology: fan-out / fan-in

```shell
START → prepare → ┌─ compliance  ─┐
                   ├─ security    ─┤ → moderator → END
                   └─ engineering ─┘
```

This is called a **fan-out / fan-in** pattern:

1. **Fan-out**: The `prepare` node has three outgoing edges. LangGraph sees that `compliance`, `security`, and `engineering` are all reachable from `prepare` with no dependencies between them, so it dispatches all three **concurrently**.

2. **Fan-in**: The `moderator` node has three incoming edges. LangGraph waits for **all three** agents to complete before executing the moderator. This is implicit — you don't write any join logic.

The key insight: **edges define parallelism**. If node A has edges to B and C, and B and C have no edge between them, LangGraph runs B and C in parallel. The moderator's three incoming edges create an automatic barrier (join point).

---

## Shared state

Every node in the graph reads from and writes to a shared `SwarmState` dictionary:

```python
class SwarmState(TypedDict):
    # Input fields — set by the caller
    event_type: str
    title: str
    client_name: str
    event_data: dict[str, Any]
    client_memory: str

    # Accumulated by agent nodes (fan-out reducer)
    analyses: Annotated[list[AgentAnalysis], operator.add]

    # Set by the moderator node (fan-in)
    moderator_synthesis: ModeratorSynthesis | None
```

### The state reducer pattern

The `analyses` field is the critical design choice. Three agents run in parallel and each wants to append its result to the same list. Without coordination, the last writer wins and overwrites the others.

LangGraph solves this with **reducers**. The type annotation:

```python
analyses: Annotated[list[AgentAnalysis], operator.add]
```

tells LangGraph: *when merging updates to this field, use `operator.add` (list concatenation) instead of replacement*. So:

1. Compliance returns `{"analyses": [compliance_result]}`
2. Security returns `{"analyses": [security_result]}`
3. Engineering returns `{"analyses": [engineering_result]}`

LangGraph concatenates all three → `analyses = [compliance_result, security_result, engineering_result]`

The moderator then receives the full list. The order may vary depending on which agent finishes first, but the moderator processes all three regardless of order.

### State flow through the graph

```shell
Caller sets:                       Agents append:              Moderator sets:
┌──────────────────┐              ┌──────────────────┐        ┌──────────────────┐
│ event_type       │──→ prepare ──│ analyses: [      │──→     │ moderator_       │
│ title            │              │   compliance,    │   join  │   synthesis      │
│ client_name      │              │   security,      │──→     │                  │
│ event_data       │              │   engineering    │──→     │                  │
│ client_memory    │              │ ]                │        │                  │
│ analyses: []     │              └──────────────────┘        └──────────────────┘
│ moderator_       │
│   synthesis: null │
└──────────────────┘
```

---

## Deep agents with tool use

Each domain agent is a **deep agent** — instead of a single LLM call, it runs an internal tool-calling loop to gather evidence before forming its assessment. The LangGraph topology is unchanged; the tool loop is entirely internal to each node function.

### The two-phase approach

Each agent uses a shared `run_agent_with_tools()` helper that runs two LLM phases:

**Phase 1 — Evidence gathering** (tool-calling loop):
```python
llm_with_tools = llm.bind_tools(tools)  # e.g., sanctions lookup, IP reputation
# Loop up to max_iterations:
#   LLM decides which tools to call → execute tools → append results → repeat
#   Exit when LLM returns a message with no tool_calls
```

**Phase 2 — Structured extraction**:
```python
structured_llm = llm.with_structured_output(AgentAnalysis)
# Final call with all gathered evidence → validated Pydantic output
```

Why two phases? `bind_tools()` adds tool definitions to the LLM request so it can call tools. `with_structured_output()` sets up JSON schema enforcement for the final result. They serve different purposes and can't be combined — the tool loop phase needs tool calling, the extraction phase needs structured output.

### Tool-calling loop internals

```python
async def run_agent_with_tools(
    state, agent_role, system_prompt, event_message, tools, max_iterations=5
) -> dict:
    llm = get_llm()
    tool_map = {t.name: t for t in tools}
    llm_with_tools = llm.bind_tools(tools)

    messages = [SystemMessage(content=system_prompt), HumanMessage(content=event_message)]

    for iteration in range(max_iterations):
        response = await llm_with_tools.ainvoke(messages)
        messages.append(response)

        if not response.tool_calls:
            break  # LLM has gathered enough evidence

        for tool_call in response.tool_calls:
            result = await tool_map[tool_call["name"]].ainvoke(tool_call["args"])
            messages.append(ToolMessage(content=result, tool_call_id=tool_call["id"]))

    # Phase 2: extract structured output with all evidence in context
    messages.append(HumanMessage(content="Provide your final structured assessment."))
    structured_llm = llm.with_structured_output(AgentAnalysis)
    analysis = await structured_llm.ainvoke(messages)
    analysis.agent_role = agent_role
    return {"analyses": [analysis]}
```

Error handling: unknown tool names get an error message (the LLM self-corrects on the next iteration), and tool exceptions are caught and returned as error strings.

### Domain tools (9 total)

Each agent has 3 domain-specific tools. All tools use the `@tool` decorator from `langchain_core.tools`, accept snake_case parameters, and return JSON strings. Current implementations return **simulated mock data** keyed on the 4 built-in scenarios — the interfaces are designed for easy swap to real APIs later.

| Domain | Tool | Purpose |
|--------|------|---------|
| **Compliance** | `search_sanctions_list(name, country)` | OFAC/EU/UN sanctions lookup with match scores and FATF status |
| | `get_client_transaction_history(client_name)` | Recent patterns, account age, risk rating, flags |
| | `check_regulatory_thresholds(event_type, amount, jurisdiction)` | CTR/SAR thresholds, structuring detection, FATF grey/black list |
| **Security** | `lookup_ip_reputation(ip_address)` | Threat score, ISP, VPN/proxy/Tor detection, abuse history |
| | `check_geo_velocity(client_name, current_location)` | Impossible travel detection with distance/time analysis |
| | `get_device_fingerprint_history(client_name)` | Known/new devices, trust levels, risk indicators |
| **Engineering** | `check_sdk_version_status(version)` | SDK lifecycle status, known CVEs, upgrade urgency |
| | `get_api_rate_limit_status(client_id)` | Rate limit consumption, burst detection, throttling status |
| | `validate_transaction_metadata(reference_id)` | Format validation, duplicate check, correlation chain |

Tools are registered in `agents/tools/__init__.py` via a `TOOLS_BY_DOMAIN` dictionary.

---

## Agent node anatomy

Every agent node delegates to the shared `run_agent_with_tools()` helper. Here's the compliance agent:

```python
async def compliance_agent(state: SwarmState) -> dict:
    return await run_agent_with_tools(
        state=state,
        agent_role="compliance",
        system_prompt=_load_prompt(),       # from prompts/compliance.md
        event_message=_format_event(state), # event data as markdown
        tools=COMPLIANCE_TOOLS,             # 3 compliance-specific tools
    )
```

### How the pipeline works for each agent

1. **Load prompt** — `_load_prompt()` reads the domain prompt from disk (`prompts/compliance.md`)
2. **Format event** — `_format_event()` converts graph state into a structured markdown message
3. **Tool loop** — The LLM calls domain tools to gather evidence (sanctions checks, IP lookups, etc.)
4. **Structured extraction** — A final LLM call with all evidence produces a validated `AgentAnalysis`
5. **Role tagging** — `agent_role` is set explicitly in code (not trusting LLM self-identification)
6. **State update** — Returns `{"analyses": [result]}` for the `operator.add` reducer

### Why all agents are identical in structure

The three agents (`compliance_agent`, `security_agent`, `engineering_agent`) have **identical code structure**. The only differences are:

1. Which prompt file they load (`compliance.md` vs `security.md` vs `engineering.md`)
2. The `agent_role` string they set
3. Which tool list they pass (`COMPLIANCE_TOOLS` vs `SECURITY_TOOLS` vs `ENGINEERING_TOOLS`)

Domain expertise lives in the **prompt templates** and **tool definitions**, not in code.

---

## The moderator: synthesis, not analysis

The moderator is structurally different from the three domain agents. Instead of analyzing the raw event, it synthesizes the agents' analyses:

```python
async def moderator_node(state: SwarmState) -> dict:
    llm = get_llm()
    structured_llm = llm.with_structured_output(ModeratorSynthesis)

    result = await structured_llm.ainvoke([
        SystemMessage(content=_load_prompt()),       # prompts/moderator.md
        HumanMessage(content=_format_analyses(state)), # all 3 agent results
    ])

    return {"moderator_synthesis": result}
```

Key differences from agent nodes:

| Aspect | Agent nodes | Moderator |
|---|---|---|
| Input | Raw event data | All agent analyses |
| Output field | `analyses` (list, reducer) | `moderator_synthesis` (single value) |
| LLM prompt | Domain-specific analysis | Synthesis instructions |
| Adds new analysis? | Yes | No — synthesizes only |

The moderator's `_format_analyses()` function serializes all three agent results into a structured markdown document that the LLM can reason over:

```yaml
## Event: wire_transfer
**Title:** $2.4M Wire to Cyprus
**Client:** Meridian Holdings

---

## Agent Analyses

### Compliance Agent
**Position:** Hold recommended pending EDD
**Risk Level:** high
**Confidence:** high
[full analysis text]
**Key Findings:**
- Amount exceeds typical monthly volume by 2x
- Cyprus is FATF-monitored jurisdiction
**Recommended Action:** File SAR, request EDD

### Security Agent
[...]

### Engineering Agent
[...]
```

---

## Structured LLM output

Every LLM call in SwarmOps returns validated, structured data — not free-form text. This is achieved through Pydantic schemas and LangChain's structured output binding.

### AgentAnalysis schema

```python
class AgentAnalysis(BaseModel):
    agent_role: str       # "compliance" | "security" | "engineering"
    position: str         # One-sentence position statement
    analysis: str         # Detailed markdown analysis
    risk_level: str       # "critical" | "high" | "medium" | "low"
    confidence: str       # "high" | "medium" | "low"
    key_findings: list[str]  # 2-5 bullet points
    recommended_action: str  # Specific next step
```

### ModeratorSynthesis schema

```python
class ModeratorSynthesis(BaseModel):
    status: str              # e.g. "HOLD RECOMMENDED"
    consensus: str           # Where agents agree
    dissent: str             # Where they disagree (or "None")
    risk_level: str          # Overall: critical/high/medium/low
    risk_assessment: str     # Brief risk justification
    key_decisions: list[str] # 1-3 most important findings
    next_steps: list[str]    # Concrete next steps
    action_items: list[ActionItem]  # 2-4 RM actions

class ActionItem(BaseModel):
    label: str     # "Hold Transfer"
    variant: str   # "primary" | "secondary" | "danger"
    rationale: str # Why this option exists
```

### Defensive validators

LLMs don't always return perfectly formatted JSON. The schemas include validators that handle common output quirks:

```python
@field_validator("key_findings", mode="before")
@classmethod
def coerce_key_findings(cls, v):
    """LLMs sometimes return a bullet-point string instead of a JSON array."""
    if isinstance(v, list):
        return v
    if isinstance(v, str):
        # Parse "- finding 1\n- finding 2" into ["finding 1", "finding 2"]
        lines = re.split(r"\n(?:[•\-\*]\s*|\d+\.\s*)", v)
        ...
    return [str(v)]
```

This `_coerce_to_list` validator handles three cases:
1. **Valid list** → pass through
2. **Bullet-point string** → split on bullet markers (`-`, `*`, `•`, `1.`)
3. **Anything else** → wrap in a list

The same validator is applied to `key_decisions` and `next_steps` on `ModeratorSynthesis`.

---

## LLM configuration

SwarmOps uses **AWS Bedrock** as its LLM provider, accessed through LangChain's `ChatBedrockConverse` class:

```python
@lru_cache
def get_llm() -> ChatBedrockConverse:
    settings = get_settings()
    return ChatBedrockConverse(
        model=settings.bedrock_model_id,
        region_name=settings.bedrock_region,
        temperature=0.3,
        max_tokens=2048,
        config=BotoConfig(
            retries={"max_attempts": 8, "mode": "adaptive"},
        ),
    )
```

### Configuration

| Setting | Env var | Default |
|---|---|---|
| Model | `SWARM_BEDROCK_MODEL_ID` | `us.anthropic.claude-haiku-4-5-20251001-v1:0` |
| Region | `SWARM_BEDROCK_REGION` | `us-east-1` |
| Temperature | `SWARM_LLM_TEMPERATURE` | `0.3` |
| Max tokens | `SWARM_LLM_MAX_TOKENS` | `2048` |

### Adaptive retry

The retry configuration is important. When three agents call Bedrock simultaneously, you can hit rate limits. The adaptive retry strategy:

- Starts with `max_attempts=8` (generous retry budget)
- Uses `mode="adaptive"` — Boto3's most sophisticated retry mode, which:
  - Tracks a **token bucket** of available retries
  - Applies **exponential backoff with jitter**
  - Adjusts retry behavior based on recent error rates
  - Distinguishes between throttling errors (retry) and client errors (don't retry)

This means even with three concurrent Bedrock calls, the system gracefully handles throttling without failing.

### Caching

The `@lru_cache` on `get_llm()` ensures a single LLM instance is created and reused. This matters because `ChatBedrockConverse` initializes a Boto3 session internally — creating one per request would be wasteful.

---

## Prompt engineering

Agent behavior is entirely controlled by markdown prompt files in `backend/app/agents/prompts/`. The code is generic; the prompts are specific.

### Prompt structure

Each prompt follows the same pattern:

```yaml
# [Role Name] — SwarmOps

You are a [role description]. You analyze business events for [domain].

## Your Domain
- [Domain area 1]
- [Domain area 2]
...

## Analysis Framework
For every event, assess:
1. [Assessment criterion 1]
2. [Assessment criterion 2]
...

## Client Memory Context
If client memory is provided, use it to [specific instruction].

## Output Guidelines
- [Guideline 1]
- [Guideline 2]
...
```

### Runtime loading

Prompts are loaded from disk at request time via `_load_prompt()`:

```python
_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "compliance.md"

def _load_prompt() -> str:
    return _PROMPT_PATH.read_text()
```

This means you can **edit a prompt file and see the change on the next request** without restarting the server (in development) or rebuilding the container.

### Message construction

Each agent formats the event data into a structured markdown document:

```python
def _format_event(state: SwarmState) -> str:
    parts = [
        f"## Event: {state['event_type']}",
        f"**Title:** {state['title']}",
        f"**Client:** {state['client_name']}",
        "",
        "### Event Data",
        "```json",
        json.dumps(state["event_data"], indent=2),
        "```",
    ]
    if state.get("client_memory"):
        parts.extend(["", "### Client Memory", state["client_memory"]])
    return "\n".join(parts)
```

The LLM receives:
1. **System message**: The full prompt template (role, domain, analysis framework, guidelines)
2. **Human message**: The formatted event with JSON data and client memory

---

## Execution modes

The graph supports two execution modes, exposed through two API endpoints.

### Synchronous (`POST /api/analyze`)

```python
result = await graph.ainvoke(build_input(req))
```

`ainvoke()` runs the entire graph to completion and returns the final state. The response includes all three agent analyses and the moderator synthesis in a single JSON payload.

### Streaming (`POST /api/analyze/stream`)

```python
async for event in graph.astream(build_input(req), stream_mode="updates"):
    for node_name, node_output in event.items():
        if node_name in ("compliance", "security", "engineering"):
            yield {"event": "agent_complete", "data": ...}
        elif node_name == "moderator":
            yield {"event": "moderator_complete", "data": ...}
```

`astream(stream_mode="updates")` yields an event each time a node completes. This enables **Server-Sent Events (SSE)** — the client sees each agent's analysis as it finishes, rather than waiting for all agents plus the moderator.

The SSE event sequence:

```yaml
event: start
data: {"status": "processing"}

event: agent_complete          # first agent finishes
data: {"agent_role": "security", "position": "...", ...}

event: agent_complete          # second agent finishes
data: {"agent_role": "compliance", "position": "...", ...}

event: agent_complete          # third agent finishes
data: {"agent_role": "engineering", "position": "...", ...}

event: moderator_complete      # moderator synthesizes all three
data: {"status": "HOLD RECOMMENDED", "consensus": "...", ...}

event: done
data: {"status": "complete"}
```

The order of `agent_complete` events varies per request — whichever agent's LLM call returns first emits first.

---

## Event queue and persistence

The **event queue** (`/api/queue`) provides a shortcut for running pre-built scenarios. Instead of constructing full JSON payloads, you submit a scenario name:

```shell
curl -X POST /api/queue -H "Content-Type: application/json" -d '{"scenario": "wire_transfer"}'
```

### How it works

1. Four pre-built `AnalyzeRequest` objects are defined in `backend/app/agents/scenarios.py`, each representing a realistic fintech scenario with different risk profiles
2. The queue endpoint looks up the scenario by name
3. It calls the same LangGraph pipeline as `/api/analyze`
4. The result is automatically persisted to the **in-memory conversation store**
5. The response includes a `conversationId` that can be used to retrieve the full result later

### Conversation store

Results are persisted in an `InMemoryConversationStore` — a simple `dict[str, ConversationRecord]` wrapped in a class:

```python
class InMemoryConversationStore:
    def save(self, record): ...          # upsert by id
    def get(self, conversation_id): ...  # returns record or None
    def list_all(self): ...              # newest first (by startedAt)
    def clear(self): ...                 # returns count cleared
```

The store is a module-level singleton, shared across all requests. Data is lost on server restart — this is intentional for demo use.

### Conversation builder

The `build_conversation()` function transforms graph output into the `ConversationRecord` shape that the frontend expects:

```shell
Graph output                    →  ConversationRecord (frontend shape)
─────────────────────────────      ──────────────────────────────────
AgentAnalysis.agent_role        →  agents[].role
AgentAnalysis.analysis          →  messages[].content
ModeratorSynthesis.risk_level   →  riskLevel
ModeratorSynthesis.action_items →  actionRequired.options
ModeratorSynthesis.consensus    →  moderatorSummary.consensus
ModeratorSynthesis.dissent      →  (folded into consensus string)
AnalyzeRequest.client_memory    →  clientMemory.content
```

All field names are converted to camelCase via Pydantic aliases so the JSON matches the frontend TypeScript types exactly.

---

## End-to-end event journey

Here's what happens when you submit a wire transfer scenario, from HTTP request to rendered UI:

```shell
1. POST /api/queue {"scenario": "wire_transfer"}
      |
2.    v Look up scenario -> AnalyzeRequest object
      |
3.    v build_input(req) -> SwarmState dict
      |
4.    v graph.ainvoke(state)
      |
5.    +-> prepare_context()     -> {} (passthrough)
      |
6.    +-> compliance_agent()    -+
      +-> security_agent()      -+ (parallel, each runs tool loop)
      +-> engineering_agent()   -+
      |         |  (tools: sanctions, IP reputation, SDK checks, etc.)
      |         v operator.add merges analyses
      |
7.    v moderator_node()        -> ModeratorSynthesis
      |
8.    v build_conversation(req, analyses, synthesis)
      |         -> ConversationRecord (UUID, camelCase)
      |
9.    v conversation_store.save(record)
      |
10.   v Return ConversationRecord as JSON
      |
11.   v Frontend polls GET /api/conversations (every 3s)
      |         -> Sees new conversation in list
      |
12.   v User clicks conversation in sidebar
              -> Sees agent analyses, moderator summary, action buttons
```

### Timing

A typical request takes **5-15 seconds** end-to-end, depending on LLM latency:

| Phase | Duration |
|---|---|
| Request parsing + scenario lookup | < 1ms |
| Prepare node | < 1ms |
| Agent tool loops (3 parallel, 1-3 tool calls each) | 5-15s |
| Agent structured extraction (3 parallel) | 2-5s |
| Moderator LLM call | 2-5s |
| Conversation building + persistence | < 1ms |
| Response serialization | < 1ms |

The agents run in parallel, so the total agent time is the **slowest** agent, not the sum of all three. Each agent typically makes 1-3 tool calls before extraction, adding 2-5 LLM round trips per agent.

---

## Design decisions

### Why three agents, not one?

A single LLM call with "analyze this from compliance, security, and engineering perspectives" would be simpler. Three separate agents provide:

1. **Parallel execution** — 3x faster than sequential (limited by slowest, not sum)
2. **Structured disagreement** — Agents can genuinely disagree because they have different system prompts and perspectives. A single call tends to produce internally consistent (but potentially one-sided) analysis.
3. **Independent confidence levels** — Security might be "high confidence: this is an account takeover" while Engineering says "low confidence: the technical data is inconclusive"
4. **Composability** — Add or remove agents without changing the others
5. **Debuggability** — You can see exactly what each agent said and why

### Why structured output, not free text?

Structured output (Pydantic schemas) over free-form markdown provides:

1. **Type safety** — The frontend knows exactly what fields exist
2. **Reliable parsing** — No regex-based extraction of risk levels from prose
3. **Consistent UI** — Every analysis has the same fields in the same format
4. **Validation** — Pydantic validators catch and fix LLM output quirks
5. **API contracts** — The response schema is part of the API specification

### Why in-memory store, not a database?

The current in-memory store is a deliberate choice for the demo phase:

1. **Zero dependencies** — No SQLAlchemy, no Alembic, no connection strings
2. **Instant reset** — `DELETE /api/conversations` clears everything, or just restart the server
3. **Frontend development** — The store's shape exactly matches the frontend TypeScript types, so frontend development can proceed without a database
4. **Migration path** — When persistence is needed, the `InMemoryConversationStore` interface can be replaced with a database-backed implementation without changing any calling code

---

## Adding a new agent

To add a fourth agent (e.g., a Legal agent):

**1. Create the prompt** — `backend/app/agents/prompts/legal.md`

```yaml
# Legal Agent — SwarmOps

You are a senior legal counsel specializing in financial regulations...

## Your Domain
...

## Available Tools
- **search_case_law(query, jurisdiction)** — Search relevant case law...
- **check_contract_terms(client_name)** — Retrieve contract terms...

## Analysis Framework
...
```

**2. Create the tools** — `backend/app/agents/tools/legal_tools.py`

```python
from langchain_core.tools import tool

@tool
def search_case_law(query: str, jurisdiction: str) -> str:
    """Search relevant case law for a legal question."""
    # Mock implementation — swap for real API later
    return json.dumps({"results": [...]})

LEGAL_TOOLS = [search_case_law, ...]
```

Register in `agents/tools/__init__.py`:

```python
from app.agents.tools.legal_tools import LEGAL_TOOLS
TOOLS_BY_DOMAIN["legal"] = LEGAL_TOOLS
```

**3. Create the node** — `backend/app/agents/nodes/legal.py`

```python
async def legal_agent(state: SwarmState) -> dict:
    return await run_agent_with_tools(
        state=state,
        agent_role="legal",
        system_prompt=_load_prompt(),
        event_message=_format_event(state),
        tools=LEGAL_TOOLS,
    )
```

**4. Wire it into the graph** — `backend/app/agents/orchestrator.py`

```python
builder.add_node("legal", legal_agent)
builder.add_edge("prepare", "legal")       # fan-out
builder.add_edge("legal", "moderator")     # fan-in
```

That's it. The moderator automatically receives the legal analysis because it reads all entries in `state["analyses"]`. The frontend automatically renders it because it iterates over all agents in the conversation. No changes needed to the moderator prompt, the schemas, or the frontend.

---

## Source file reference

| File | Purpose |
|---|---|
| `backend/app/agents/orchestrator.py` | Graph definition and compilation |
| `backend/app/agents/state.py` | `SwarmState` TypedDict with reducer |
| `backend/app/agents/schemas.py` | `AgentAnalysis`, `ModeratorSynthesis`, `ActionItem` |
| `backend/app/agents/llm.py` | Cached `ChatBedrockConverse` with adaptive retry |
| `backend/app/agents/tool_loop.py` | Shared `run_agent_with_tools()` — two-phase tool loop + structured extraction |
| `backend/app/agents/scenarios.py` | 4 pre-built `AnalyzeRequest` objects |
| `backend/app/agents/tools/__init__.py` | `TOOLS_BY_DOMAIN` registry |
| `backend/app/agents/tools/compliance_tools.py` | Sanctions, transaction history, regulatory thresholds |
| `backend/app/agents/tools/security_tools.py` | IP reputation, geo-velocity, device fingerprints |
| `backend/app/agents/tools/engineering_tools.py` | SDK versions, rate limits, metadata validation |
| `backend/app/agents/nodes/prepare.py` | Context preparation (passthrough stub) |
| `backend/app/agents/nodes/compliance.py` | Compliance deep agent node (delegates to tool loop) |
| `backend/app/agents/nodes/security.py` | Security deep agent node (delegates to tool loop) |
| `backend/app/agents/nodes/engineering.py` | Engineering deep agent node (delegates to tool loop) |
| `backend/app/agents/nodes/moderator.py` | Moderator synthesis node (single structured output call) |
| `backend/app/agents/prompts/compliance.md` | Compliance domain prompt (includes Available Tools) |
| `backend/app/agents/prompts/security.md` | Security domain prompt (includes Available Tools) |
| `backend/app/agents/prompts/engineering.md` | Engineering domain prompt (includes Available Tools) |
| `backend/app/agents/prompts/moderator.md` | Moderator synthesis prompt |
| `backend/app/api/conversations.py` | `/api/analyze` and `/api/analyze/stream` |
| `backend/app/api/queue.py` | `/api/queue` (sync + stream) |
| `backend/app/api/history.py` | `/api/conversations` (list, get, clear) |
| `backend/app/services/store.py` | In-memory conversation store |
| `backend/app/services/conversation_builder.py` | Graph output → frontend shape |
| `backend/app/core/config.py` | Settings (Bedrock, CORS, LLM params) |
