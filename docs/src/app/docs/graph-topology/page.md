---
title: Graph topology
---

The SwarmOps orchestrator follows a fixed five-node topology with parallel execution in the middle layer. {% .lead %}

---

## Node map

```shell
START
  │
  ▼
prepare          ← Context preparation (passthrough stub)
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
                       END
```

---

## Nodes

### prepare

**File:** `backend/app/agents/nodes/prepare.py`

Currently a passthrough stub that returns an empty dict. This is the extension point for:

- Client memory lookup from PostgreSQL
- RAG retrieval from pgvector
- Event enrichment from external APIs

```python
async def prepare_context(state: SwarmState) -> dict:
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

---

## Edge structure

| From | To | Type |
|------|-----|------|
| `START` | `prepare` | Sequential |
| `prepare` | `compliance` | Fan-out (parallel) |
| `prepare` | `security` | Fan-out (parallel) |
| `prepare` | `engineering` | Fan-out (parallel) |
| `compliance` | `moderator` | Fan-in (waits for all) |
| `security` | `moderator` | Fan-in (waits for all) |
| `engineering` | `moderator` | Fan-in (waits for all) |
| `moderator` | `END` | Sequential |

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
