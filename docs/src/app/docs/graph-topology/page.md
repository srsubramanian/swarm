---
title: Graph topology
---

SwarmOps maintains three graph variants with different topologies for different use cases. The standard queue graph has 7 nodes; the event graph adds triage for 9 nodes. {% .lead %}

---

## Standard graph (queue)

Used by `POST /api/queue`. Includes checkpointing and the interrupt/resume pattern for RM decisions.

```shell
START
  │
  ▼
prepare          ← Client memory lookup
  │
  ├──────────────┐
  │              │
  ▼              ▼
compliance    security    engineering    ← 3 agents in parallel
  │              │              │
  └──────────────┴──────┬───────┘
                        │
                        ▼
                    moderator    ← Synthesis node
                        │
                        ▼
                  await_decision ← interrupt() pauses graph
                        │
                        ▼
                  post_decision  ← Records outcome, proposes memory update
                        │
                        ▼
                       END
```

## Event graph (webhook + simulator)

Used by `POST /api/events/webhook` and the event simulator. Adds a triage router after prepare.

```shell
START
  │
  ▼
prepare
  │
  ▼
triage ──────────────────────────── (conditional)
  │              │              │
  ▼              ▼              ▼
"respond"      "notify"      "ignore"
  │              │              │
  ├──┬──┐     notify_rm       END
  │  │  │        │
  ▼  ▼  ▼       END
 C   S   E   ← 3 agents in parallel
  │  │  │
  └──┴──┘
     │
  moderator → await_decision → post_decision → END
```

## Stateless graph (analyze)

Used by `POST /api/analyze`. No checkpointer, no interrupt — runs to completion and returns.

```shell
START → prepare → [compliance | security | engineering] → moderator → END
```

---

## Nodes

### prepare

**File:** `backend/app/agents/nodes/prepare.py`

Fetches stored client memory from `ClientMemoryStore` and injects it into the state. If the request already includes client memory, the stored memory is appended.

```python
async def prepare_context(state: SwarmState) -> dict:
    stored_memory = memory_store.get_memory(state["client_name"])
    if stored_memory:
        return {"client_memory": stored_memory}
    return {}
```

### compliance

**File:** `backend/app/agents/nodes/compliance.py`

AML/KYC compliance analysis. Loads the compliance prompt template, formats the event as markdown, and calls the LLM with `AgentAnalysis` structured output.

### security

**File:** `backend/app/agents/nodes/security.py`

Threat detection and fraud analysis. Same pattern as compliance, with a security-focused prompt template.

### engineering

**File:** `backend/app/agents/nodes/engineering.py`

Technical integrity analysis. Validates API payloads, SDK versions, metadata consistency, and rate limit patterns.

### moderator

**File:** `backend/app/agents/nodes/moderator.py`

Synthesizes all three agent analyses into a `ModeratorSynthesis` with consensus, dissent, risk level, and action items.

### await_decision

**File:** `backend/app/agents/nodes/await_decision.py`

Calls `interrupt()` to pause the graph. The RM reviews the action items and submits a decision via `POST /api/decisions/{id}`. The graph resumes with `Command(resume=payload)`.

### post_decision

**File:** `backend/app/agents/nodes/post_decision.py`

Processes the RM's decision. Records the outcome and calls the LLM to propose a client memory update based on the event, analysis, and decision.

### triage *(event graph only)*

**File:** `backend/app/agents/nodes/triage.py`

LLM-based event classification. Returns `respond`, `notify`, or `ignore`. Uses `Send()` objects for conditional fan-out on the `respond` path.

### notify_rm *(event graph only)*

**File:** `backend/app/agents/nodes/notify.py`

Lightweight notification for events triaged as `notify`.

---

## Edge structure (standard graph)

| From | To | Type |
|------|-----|------|
| `START` | `prepare` | Sequential |
| `prepare` | `compliance` | Fan-out (parallel) |
| `prepare` | `security` | Fan-out (parallel) |
| `prepare` | `engineering` | Fan-out (parallel) |
| `compliance` | `moderator` | Fan-in (waits for all) |
| `security` | `moderator` | Fan-in (waits for all) |
| `engineering` | `moderator` | Fan-in (waits for all) |
| `moderator` | `await_decision` | Sequential |
| `await_decision` | `post_decision` | Sequential (after resume) |
| `post_decision` | `END` | Sequential |

---

## State reducer

The fan-out/fan-in pattern works because of the `operator.add` reducer on `analyses`:

```python
analyses: Annotated[list[AgentAnalysis], operator.add]
```

When compliance returns `{"analyses": [compliance_result]}` and security returns `{"analyses": [security_result]}`, LangGraph merges them into `[compliance_result, security_result]` using list concatenation. The moderator always receives all three.

---

## Agent node pattern

All three agent nodes follow the same implementation pattern:

```python
async def agent_node(state: SwarmState) -> dict:
    llm = get_llm()
    structured_llm = llm.with_structured_output(AgentAnalysis)
    result = await structured_llm.ainvoke([
        SystemMessage(content=load_prompt()),
        HumanMessage(content=format_event(state)),
    ])
    result.agent_role = "agent_name"
    return {"analyses": [result]}
```

1. Get the cached LLM instance
2. Bind it to the `AgentAnalysis` schema for structured output
3. Send the system prompt + formatted event
4. Set the `agent_role` field
5. Return as a single-element list (the reducer handles merging)
