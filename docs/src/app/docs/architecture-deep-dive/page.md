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

The agent pipeline is defined in `backend/app/agents/orchestrator.py` via a parameterized `build_graph` function that produces three graph variants:

```python
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph

_saver = InMemorySaver()

def build_graph(checkpointer=_saver, include_triage=True):
    builder = StateGraph(SwarmState)

    # Core nodes (always present)
    builder.add_node("prepare", prepare_context)
    builder.add_node("compliance", compliance_agent)
    builder.add_node("security", security_agent)
    builder.add_node("engineering", engineering_agent)
    builder.add_node("moderator", moderator_node)
    builder.add_node("await_decision", await_decision)
    builder.add_node("post_decision", post_decision)

    builder.add_edge(START, "prepare")

    if include_triage:
        builder.add_node("triage", triage_router)
        builder.add_node("notify_rm", notify_rm)
        builder.add_edge("prepare", "triage")
        builder.add_conditional_edges("triage", triage_edge)
        builder.add_edge("notify_rm", END)
    else:
        # Direct fan-out (no triage)
        builder.add_edge("prepare", "compliance")
        builder.add_edge("prepare", "security")
        builder.add_edge("prepare", "engineering")

    # Fan-in: all agents -> moderator
    builder.add_edge("compliance", "moderator")
    builder.add_edge("security", "moderator")
    builder.add_edge("engineering", "moderator")

    # Decision flow
    builder.add_edge("moderator", "await_decision")
    builder.add_edge("await_decision", "post_decision")
    builder.add_edge("post_decision", END)

    return builder.compile(checkpointer=checkpointer)

# Three module-level singletons
stateless_graph = build_graph(checkpointer=None, include_triage=False)
graph           = build_graph(checkpointer=_saver, include_triage=False)
event_graph     = build_graph(checkpointer=_saver, include_triage=True)
```

The two parameters control the graph's behaviour:

- **checkpointer** -- pass `None` for stateless mode (no interrupt support) or an `InMemorySaver` for stateful mode with interrupt/resume.
- **include_triage** -- when `True`, a triage node is inserted between prepare and the fan-out, with conditional routing via `Send` objects.

The three compiled graphs are **module-level singletons** -- built once at import time, reused for every request.

| Graph | Checkpointer | Triage | Used by |
|---|---|---|---|
| stateless_graph | None | No | /api/analyze |
| graph | InMemorySaver | No | /api/queue |
| event_graph | InMemorySaver | Yes | /api/events/webhook, simulator |

### Topology -- stateful graph without triage

```shell
START -> prepare -> +-  compliance  -+                   +-> post_decision -> END
                    +-- security   --+ -> moderator -> await_decision
                    +-- engineering -+
```

This is called a **fan-out / fan-in** pattern with an **interrupt point**:

1. **Fan-out**: The `prepare` node has three outgoing edges. LangGraph sees that `compliance`, `security`, and `engineering` are all reachable from `prepare` with no dependencies between them, so it dispatches all three **concurrently**.

2. **Fan-in**: The `moderator` node has three incoming edges. LangGraph waits for **all three** agents to complete before executing the moderator. This is implicit -- you don't write any join logic.

3. **Interrupt**: After the moderator, `await_decision` calls `interrupt` to pause the graph. The RM submits a decision, and the graph resumes through `post_decision` to END.

The key insight: **edges define parallelism**. If node A has edges to B and C, and B and C have no edge between them, LangGraph runs B and C in parallel. The moderator's three incoming edges create an automatic barrier (join point).

### Topology -- event graph with triage

```shell
START -> prepare -> triage -> (conditional)
    respond:  [compliance | security | engineering] -> moderator -> await_decision -> post_decision -> END
    notify:   notify_rm -> END
    ignore:   END
```

The triage node classifies each event as respond, notify, or ignore. When the classification is "respond", the `triage_edge` function returns a list of `Send` objects that fan out to the three agent nodes -- the same fan-out/fan-in pattern as above. For "notify", it routes to a lightweight notification node. For "ignore", it routes directly to END.

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

    # RM decision — populated by Command(resume=) after interrupt
    decision: dict | None

    # Memory update proposal from post_decision node
    memory_update_proposal: dict | None

    # Triage classification — respond, notify, or ignore
    triage_result: str | None
```

### The state reducer pattern

The `analyses` field is the critical design choice. Three agents run in parallel and each wants to append its result to the same list. Without coordination, the last writer wins and overwrites the others.

LangGraph solves this with **reducers**. The type annotation:

```python
analyses: Annotated[list[AgentAnalysis], operator.add]
```

tells LangGraph: *when merging updates to this field, use `operator.add` (list concatenation) instead of replacement*. So:

1. Compliance returns a dict with `analyses` containing its result
2. Security returns a dict with `analyses` containing its result
3. Engineering returns a dict with `analyses` containing its result

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
6. **State update** — Returns a dict with `analyses` list for the `operator.add` reducer

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

The graph supports three execution modes, each backed by a different compiled graph.

### Stateless analysis

The stateless_graph has no checkpointer and no interrupt support. It runs the entire pipeline to completion in a single call:

```python
result = await stateless_graph.ainvoke(build_input(req))
```

`ainvoke` runs the graph from START to END and returns the final state. The response includes all three agent analyses and the moderator synthesis in a single JSON payload. Used by the /api/analyze endpoint.

### Stateful with interrupt

The stateful graph has an InMemorySaver checkpointer and pauses at await_decision for RM input:

```python
# Initial run — pauses at await_decision
thread_id = str(uuid.uuid4())
config = {"configurable": {"thread_id": thread_id}}
result = await graph.ainvoke(build_input(req), config=config)

# Later — RM submits decision, graph resumes
from langgraph.types import Command
await graph.ainvoke(Command(resume=decision_payload), config=config)
```

The thread_id links the initial run to the resume call. A ThreadStore maps conversation_id to thread_id so the decision API can look up the correct thread. Used by the /api/queue endpoint.

### Streaming

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
1.  POST /api/queue {"scenario": "wire_transfer"}
       |
2.     v Look up scenario -> AnalyzeRequest object
       |
3.     v build_input(req) -> SwarmState dict
       |
4.     v graph.ainvoke(state, config={"configurable": {"thread_id": tid}})
       |
5.     +-> prepare_context()     -> fetches client memory from memory store
       |
6.     +-> compliance_agent()    -+
       +-> security_agent()      -+ (parallel, each runs tool loop)
       +-> engineering_agent()   -+
       |         |  (tools: sanctions, IP reputation, SDK checks, etc.)
       |         v operator.add merges analyses
       |
7.     v moderator_node()        -> ModeratorSynthesis with action items
       |
8.     v await_decision()        -> calls interrupt(), graph pauses
       |
9.     v build_conversation(req, analyses, synthesis)
       |         -> ConversationRecord (status: "awaiting_decision")
       |
10.    v conversation_store.save(record) + thread_store.set(id, tid)
       |
11.    v Return ConversationRecord as JSON
       |
12.    v Frontend polls GET /api/conversations (every 5s)
       |         -> Sees new conversation with status "awaiting_decision"
       |
13.    v RM clicks conversation in sidebar
       |         -> Sees agent analyses, moderator summary, action buttons
       |
14.    v RM submits decision via POST /api/decisions/<id>
       |         -> API resumes graph: Command(resume=decision_payload)
       |
15.    v post_decision()         -> logs decision, proposes memory update via LLM
       |
16.    v Conversation status becomes "concluded"
              -> Frontend shows actioned state
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

## Interrupt and resume pattern

The await_decision node is the key mechanism for human-in-the-loop control. When the moderator finishes synthesizing agent analyses, the graph does not proceed to END. Instead, it pauses and waits for an RM decision.

### How interrupt works

The await_decision node calls `interrupt` from `langgraph.types`, passing the action item data from the moderator synthesis as context:

```python
from langgraph.types import interrupt

async def await_decision(state: SwarmState) -> dict:
    synthesis = state["moderator_synthesis"]
    decision = interrupt({
        "action_items": [item.model_dump() for item in synthesis.action_items],
        "status": synthesis.status,
        "risk_level": synthesis.risk_level,
    })
    return {"decision": decision}
```

When `interrupt` is called, LangGraph saves the current graph state to the checkpointer and returns control to the caller. The graph is now **suspended** -- it will not proceed until explicitly resumed.

### How resume works

The decision API endpoint resumes the graph by looking up the thread_id and invoking the graph with a Command:

```python
from langgraph.types import Command

thread_id = thread_store.get(conversation_id)
config = {"configurable": {"thread_id": thread_id}}
decision_payload = {"action": "approve", "option_id": "opt-1", "justification": "..."}
await graph.ainvoke(Command(resume=decision_payload), config=config)
```

The `Command(resume=...)` value becomes the return value of the `interrupt` call inside await_decision. The node then returns the decision in state, and execution continues to post_decision and then to END.

### ThreadStore mapping

A ThreadStore singleton maps conversation_id to thread_id. This is necessary because the conversation_id is a SwarmOps concept (used in the API and frontend), while the thread_id is a LangGraph concept (used by the checkpointer). The mapping is set when the initial graph run is submitted and looked up when the RM submits a decision.

---

## Triage classification

The event graph includes a triage node that classifies incoming events before deciding whether to run the full agent pipeline.

### TriageResult schema

The triage node uses structured LLM output to produce a classification:

```python
class TriageClassification(str, Enum):
    respond = "respond"
    notify = "notify"
    ignore = "ignore"

class TriageResult(BaseModel):
    classification: TriageClassification  # respond, notify, or ignore
    reasoning: str  # brief explanation
```

### Conditional routing with Send

The triage_edge function inspects the classification and returns either a list of Send objects (for fan-out) or a string (for single-node routing):

```python
def triage_edge(state: SwarmState) -> Union[str, list[Send]]:
    classification = state.get("triage_result", "respond")
    if classification == "respond":
        return [
            Send("compliance", state),
            Send("security", state),
            Send("engineering", state),
        ]
    elif classification == "notify":
        return "notify_rm"
    else:  # ignore
        return "__end__"
```

When the classification is "respond", the `Send` objects trigger the same fan-out pattern as the non-triage graph -- three agents run in parallel, fan in to the moderator, and proceed through the decision flow. For "notify", a lightweight notify_rm node logs the event for the RM without running any agents. For "ignore", the graph routes directly to END.

---

## Client memory

Each client has a dedicated memory store that accumulates learned behaviours over time. Memory provides context to agents so they can distinguish between anomalous and expected activity.

### Prepare node reads memory

The prepare_context node runs before the agent fan-out. It looks up the client name in the ClientMemoryStore and injects any stored memory into the graph state:

```python
async def prepare_context(state: SwarmState) -> dict:
    stored_memory = memory_store.get_memory(state["client_name"])
    if stored_memory:
        request_memory = state.get("client_memory", "")
        if request_memory:
            combined = request_memory + "\n\n---\n\n**Stored Memory:**\n" + stored_memory
        else:
            combined = stored_memory
        return {"client_memory": combined}
    return {}
```

Agents receive this memory as part of the formatted event message and can use it to inform their analysis -- for example, recognising that a velocity spike was previously identified as legitimate payroll processing.

### Post-decision proposes memory updates

After the RM submits a decision, the post_decision node calls an LLM with the full context (event, analyses, synthesis, and decision) to propose a memory update. The prompt template lives in `prompts/memory_update.md`. The proposal is saved as pending in the ClientMemoryStore:

```python
proposal_id = memory_store.propose_update(
    client_name=state["client_name"],
    proposed_content=proposed_content,
)
return {"memory_update_proposal": {"proposal_id": proposal_id, "content": proposed_content}}
```

### Approval workflow

Memory updates are never applied automatically. The RM reviews pending proposals via the /api/memory endpoints:

1. **List pending** -- GET /api/memory/pending returns all unapproved proposals
2. **Approve** -- POST to the approve endpoint merges the proposed content into the client's memory
3. **Reject** -- POST to the reject endpoint discards the proposal

This human-in-the-loop design ensures that the memory store remains accurate. Agents propose; humans decide.

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
| `backend/app/agents/orchestrator.py` | build_graph with 3 variants -- stateless, stateful, event |
| `backend/app/agents/state.py` | SwarmState TypedDict with reducer, decision, memory, and triage fields |
| `backend/app/agents/schemas.py` | AgentAnalysis, ModeratorSynthesis, ActionItem |
| `backend/app/agents/llm.py` | Cached ChatBedrockConverse with adaptive retry |
| `backend/app/agents/tool_loop.py` | Shared run_agent_with_tools -- two-phase tool loop + structured extraction |
| `backend/app/agents/scenarios.py` | 4 pre-built AnalyzeRequest objects |
| `backend/app/agents/tools/__init__.py` | TOOLS_BY_DOMAIN registry |
| `backend/app/agents/tools/compliance_tools.py` | Sanctions, transaction history, regulatory thresholds |
| `backend/app/agents/tools/security_tools.py` | IP reputation, geo-velocity, device fingerprints |
| `backend/app/agents/tools/engineering_tools.py` | SDK versions, rate limits, metadata validation |
| `backend/app/agents/nodes/prepare.py` | Fetches client memory from memory store before analysis |
| `backend/app/agents/nodes/compliance.py` | Compliance deep agent node (delegates to tool loop) |
| `backend/app/agents/nodes/security.py` | Security deep agent node (delegates to tool loop) |
| `backend/app/agents/nodes/engineering.py` | Engineering deep agent node (delegates to tool loop) |
| `backend/app/agents/nodes/moderator.py` | Moderator synthesis node (single structured output call) |
| `backend/app/agents/nodes/await_decision.py` | Calls interrupt to pause graph for RM decision |
| `backend/app/agents/nodes/post_decision.py` | Records decision, proposes memory updates via LLM |
| `backend/app/agents/nodes/triage.py` | Triage router -- classifies events as respond, notify, or ignore |
| `backend/app/agents/nodes/notify.py` | Lightweight RM notification for triaged events |
| `backend/app/agents/prompts/compliance.md` | Compliance domain prompt (includes Available Tools) |
| `backend/app/agents/prompts/security.md` | Security domain prompt (includes Available Tools) |
| `backend/app/agents/prompts/engineering.md` | Engineering domain prompt (includes Available Tools) |
| `backend/app/agents/prompts/moderator.md` | Moderator synthesis prompt |
| `backend/app/agents/prompts/triage.md` | Triage classification prompt |
| `backend/app/agents/prompts/memory_update.md` | Memory update proposal prompt |
| `backend/app/api/conversations.py` | /api/analyze and /api/analyze/stream |
| `backend/app/api/queue.py` | /api/queue (sync + stream) |
| `backend/app/api/history.py` | /api/conversations (list, get, clear) |
| `backend/app/api/decisions.py` | /api/decisions -- RM submits decision, resumes interrupted graph |
| `backend/app/api/memory.py` | /api/memory -- client memory CRUD and pending update approval |
| `backend/app/api/events.py` | /api/events -- webhook ingestion and simulator control |
| `backend/app/schemas/conversations.py` | ConversationRecord and nested models with camelCase aliases |
| `backend/app/services/store.py` | InMemoryConversationStore + ThreadStore singletons |
| `backend/app/services/conversation_builder.py` | Graph output to frontend shape |
| `backend/app/services/memory_store.py` | ClientMemoryStore -- per-client memory with pending update approval |
| `backend/app/services/event_source.py` | EventSimulator -- generates random events on a timer |
| `backend/app/core/config.py` | Settings (Bedrock, CORS, LLM params) |
