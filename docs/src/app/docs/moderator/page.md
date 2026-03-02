---
title: Moderator
---

The Moderator synthesizes analyses from all three domain agents into an actionable summary for the Relationship Manager. It does not add new analysis — it surfaces consensus, dissent, and concrete next steps. {% .lead %}

---

## Role

The moderator:

- Synthesizes what the agents provided (does NOT add new analysis)
- Identifies consensus and dissent across agents
- Produces a clear risk assessment
- Generates 2-4 action items for the RM queue

---

## Synthesis rules

1. **Consensus** — Where do all agents agree? Stated clearly and concisely.
2. **Dissent** — Where do agents disagree? Both sides presented fairly. If one agent's evidence is stronger, the moderator notes why.
3. **Risk Level** — Overall risk (critical/high/medium/low) based on the combined analysis, with brief justification.
4. **Key Decisions** — The 1-3 most important findings the RM needs to know.
5. **Next Steps** — Specific, actionable recommendations.

---

## Implementation

**File:** `backend/app/agents/nodes/moderator.py`

```python
async def moderator_node(state: SwarmState) -> dict:
    llm = get_llm()
    structured_llm = llm.with_structured_output(ModeratorSynthesis)
    result = await structured_llm.ainvoke([
        SystemMessage(content=_load_prompt()),
        HumanMessage(content=_format_analyses(state)),
    ])
    return {"moderator_synthesis": result}
```

The moderator receives all three agent analyses formatted as markdown:

```shell
## Event: wire_transfer
**Title:** $2.4M Wire to Cyprus
**Client:** Meridian Holdings

---

## Agent Analyses

### Compliance Agent
**Position:** HOLD — elevated jurisdictional risk
**Risk Level:** high
**Confidence:** high

[full analysis]

**Key Findings:**
- Transfer to Cyprus (FATF monitored)
- Amount 2x typical monthly volume

**Recommended Action:** Hold pending EDD

### Security Agent
...

### Engineering Agent
...
```

---

## Action item guidelines

The moderator generates 2-4 action items with variant priorities:

| Variant | Meaning | Example |
|---------|---------|---------|
| `primary` | Recommended action | "Hold Transfer" |
| `secondary` | Alternative option | "Approve with Conditions" |
| `danger` | Risky/irreversible option | "Escalate to BSA Officer" |

Each action item includes a rationale explaining why the RM would choose it.

---

## Output schema

```python
class ModeratorSynthesis(BaseModel):
    status: str              # "HOLD RECOMMENDED", "CLEAR", "ESCALATE"
    consensus: str           # Where agents agree
    dissent: str             # Where agents disagree
    risk_level: str          # "critical" | "high" | "medium" | "low"
    risk_assessment: str     # Brief justification
    key_decisions: list[str] # 1-3 most important findings
    next_steps: list[str]    # Concrete next steps
    action_items: list[ActionItem]  # 2-4 actions for RM queue
```

---

## Output guidelines

- **Be concise** — RMs are busy. Lead with the most important information.
- **Use plain language** — Avoid jargon unless it adds precision.
- **Don't paper over disagreement** — Surface dissent prominently when agents disagree.
- **Routine events** — If the event is clearly routine, say so and recommend clearing quickly.
