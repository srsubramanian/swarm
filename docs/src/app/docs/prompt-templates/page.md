---
title: Prompt templates
---

Agent prompts are version-controlled markdown files that define each agent's persona, domain expertise, available tools, analysis framework, and output guidelines. {% .lead %}

---

## Location

```shell
backend/app/agents/prompts/
├── compliance.md
├── security.md
├── engineering.md
└── moderator.md
```

---

## How prompts are loaded

Each agent node loads its prompt at invocation time:

```python
_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "compliance.md"

def _load_prompt() -> str:
    return _PROMPT_PATH.read_text()
```

The prompt is sent as a `SystemMessage` to the LLM. In the tool-calling phase, the LLM uses it to decide which tools to call. In the extraction phase, it guides the final structured assessment:

```python
# Tool-calling phase
messages = [SystemMessage(content=_load_prompt()), HumanMessage(content=event)]
response = await llm_with_tools.ainvoke(messages)

# After tool loop, extraction phase uses the same prompt context
structured_llm = llm.with_structured_output(AgentAnalysis)
analysis = await structured_llm.ainvoke(messages)
```

---

## Prompt structure

Every agent prompt follows a consistent format:

```shell
# {Role} Agent — SwarmOps

You are a senior {role description}. You analyze business events for {domain}.

## Your Domain
- Domain area 1
- Domain area 2
- ...

## Available Tools
- **tool_name(param1, param2)** — Description of what this tool does.
- **another_tool(param)** — Description.
Call the tools that are relevant to this event.

## Analysis Framework
1. First assessment dimension
2. Second assessment dimension
3. ...

## Client Memory Context
How to use client memory when provided.

## Output Guidelines
- Output instruction 1
- Output instruction 2
- ...
```

### The "Available Tools" section

Added between "Your Domain" and "Analysis Framework", this section tells the LLM which tools it can call during the evidence-gathering phase:

```markdown
## Available Tools

You have access to the following investigative tools. **Use them** to gather evidence
before forming your assessment — do not rely solely on the event data provided.

- **search_sanctions_list(name, country)** — Search OFAC, EU, and UN sanctions lists.
- **get_client_transaction_history(client_name)** — Retrieve recent transaction patterns.
- **check_regulatory_thresholds(event_type, amount, jurisdiction)** — Check SAR/CTR thresholds.

Call the tools that are relevant to this event. Not every tool is needed for every event.
```

The tools are also programmatically bound to the LLM via `bind_tools()`, so the prompt section serves as guidance — the LLM knows the tools exist from the API schema, and the prompt tells it *when* and *why* to use them.

---

## Agent prompts

### Compliance

Defines the agent as a senior AML/KYC compliance analyst. Has tools for sanctions lookup, transaction history, and regulatory thresholds. Analysis framework covers regulatory triggers, KYC context, jurisdictional risk, pattern analysis, and recommended actions. Cites BSA, 4AMLD, FATF Recommendation 20.

### Security

Defines the agent as a senior security analyst for financial systems. Has tools for IP reputation, geo-velocity, and device fingerprints. Framework covers authentication chain, behavioral anomalies, technical indicators, attack pattern matching. Emphasizes evidence over speculation.

### Engineering

Defines the agent as a senior fintech platform engineer. Has tools for SDK version checks, rate limit monitoring, and metadata validation. Framework covers technical validity, integration context, system patterns, data consistency. Focuses on what the data actually shows.

### Moderator

Defines the role as a synthesis moderator (not an analyst). Has **no tools** — the moderator synthesizes agent analyses, it doesn't gather evidence. Rules cover consensus, dissent, risk level assignment, key decisions, and action item generation. Emphasizes conciseness and transparency about disagreements.

---

## Design principles

- **Version-controlled** — Prompts are `.md` files in the repo, reviewed in PRs like any other code
- **Separation of concerns** — Each agent has a single prompt file defining its complete behavior
- **Loaded at runtime** — Changes to prompts take effect on next request without code changes
- **Tool-aware** — Prompts document available tools so the LLM knows when to use them
- **Testable** — Mocked LLM tests route based on prompt content headers (e.g., `startswith("# Compliance")`)

---

## Modifying prompts

To adjust agent behavior:

1. Edit the relevant `.md` file in `backend/app/agents/prompts/`
2. Test with a representative event using `requests.http` or curl
3. Review the structured output for appropriate risk levels and findings
4. Commit the change — prompt changes are tracked in git history

{% callout title="Testing prompt changes" %}
Use the example events in `backend/requests.http` to test prompt changes against known scenarios. The wire transfer to Cyprus and the new device login from Istanbul are good test cases that exercise all three agents and their tools.
{% /callout %}
