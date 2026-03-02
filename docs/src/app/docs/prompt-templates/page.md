---
title: Prompt templates
---

Agent prompts are version-controlled markdown files that define each agent's persona, domain expertise, analysis framework, and output guidelines. {% .lead %}

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

The prompt is sent as a `SystemMessage` to the LLM, with the event data as a `HumanMessage`:

```python
result = await structured_llm.ainvoke([
    SystemMessage(content=_load_prompt()),
    HumanMessage(content=_format_event(state)),
])
```

---

## Prompt structure

Every prompt follows a consistent format:

```shell
# {Role} Agent — SwarmOps

You are a senior {role description}. You analyze business events for {domain}.

## Your Domain
- Domain area 1
- Domain area 2
- ...

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

---

## Agent prompts

### Compliance

Defines the agent as a senior AML/KYC compliance analyst. Analysis framework covers regulatory triggers, KYC context, jurisdictional risk, pattern analysis, and recommended actions. Cites BSA, 4AMLD, FATF Recommendation 20.

### Security

Defines the agent as a senior security analyst for financial systems. Framework covers authentication chain, behavioral anomalies, technical indicators, attack pattern matching. Emphasizes evidence over speculation.

### Engineering

Defines the agent as a senior fintech platform engineer. Framework covers technical validity, integration context, system patterns, data consistency. Focuses on what the data actually shows.

### Moderator

Defines the role as a synthesis moderator (not an analyst). Rules cover consensus, dissent, risk level assignment, key decisions, and action item generation. Emphasizes conciseness and transparency about disagreements.

---

## Design principles

- **Version-controlled** — Prompts are `.md` files in the repo, reviewed in PRs like any other code
- **Separation of concerns** — Each agent has a single prompt file defining its complete behavior
- **Loaded at runtime** — Changes to prompts take effect on next request without code changes
- **Testable** — Mocked LLM tests route based on prompt content headers (e.g., `startswith("# Compliance")`)

---

## Modifying prompts

To adjust agent behavior:

1. Edit the relevant `.md` file in `backend/app/agents/prompts/`
2. Test with a representative event using `requests.http` or curl
3. Review the structured output for appropriate risk levels and findings
4. Commit the change — prompt changes are tracked in git history

{% callout title="Testing prompt changes" %}
Use the example events in `backend/requests.http` to test prompt changes against known scenarios. The wire transfer to Cyprus and the new device login from Istanbul are good test cases that exercise all three agents.
{% /callout %}
