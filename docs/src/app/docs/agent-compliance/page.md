---
title: Compliance agent
---

The Compliance Agent is a senior AML/KYC analyst that evaluates business events for regulatory risk, sanctions exposure, and suspicious transaction patterns. {% .lead %}

---

## Domain coverage

- **Anti-Money Laundering (AML)** — Suspicious transaction patterns, structuring, layering, integration
- **Know Your Customer (KYC)** — Beneficial ownership, PEP screening, adverse media
- **Sanctions** — OFAC, EU, UN sanctions list matches, secondary sanctions exposure
- **Regulatory Reporting** — SAR/STR filing thresholds, CTR requirements, cross-border reporting
- **Transaction Typologies** — Trade-based laundering, mirror trades, rapid movement of funds

---

## Analysis framework

For every event, the compliance agent assesses:

1. **Regulatory Triggers** — Does the event cross reporting thresholds or match known typologies?
2. **KYC Context** — Is this consistent with the client's known profile, business type, and transaction history?
3. **Jurisdictional Risk** — Are high-risk jurisdictions involved (FATF grey/black list, tax havens, sanctions targets)?
4. **Pattern Analysis** — Does this fit a sequence of suspicious activity or is it isolated?
5. **Recommended Action** — Hold, escalate, file SAR, request enhanced due diligence, or clear with documentation

---

## Implementation

**File:** `backend/app/agents/nodes/compliance.py`

```python
async def compliance_agent(state: SwarmState) -> dict:
    llm = get_llm()
    structured_llm = llm.with_structured_output(AgentAnalysis)
    result = await structured_llm.ainvoke([
        SystemMessage(content=_load_prompt()),
        HumanMessage(content=_format_event(state)),
    ])
    result.agent_role = "compliance"
    return {"analyses": [result]}
```

The agent:

1. Loads the compliance prompt template from `agents/prompts/compliance.md`
2. Formats the event data as a structured markdown message
3. Calls the LLM with `AgentAnalysis` structured output
4. Sets `agent_role` to `"compliance"`
5. Returns the analysis wrapped in a list for the state reducer

---

## Event formatting

The agent receives events formatted as structured text with the event type, title, client name, event data as JSON, and optional client memory context. For example, a wire transfer event includes the amount, currency, destination country, and reference ID.

---

## Output guidelines

The compliance agent is instructed to:

- Cite specific regulations (BSA, 4AMLD, FATF Recommendation 20)
- Be precise about risk level — not default to "high" without justification
- Acknowledge routine activity when the client profile supports it
- Flag disagreements with other agents when technical assessments overlook regulatory obligations

---

## Cross-agent interaction

The compliance agent may push back on engineering's assessment if:

- A technically valid transaction has regulatory implications
- Pattern analysis reveals structuring below CTR thresholds ($10,000)
- Jurisdictional risk factors that engineering wouldn't evaluate

These disagreements surface in the moderator's `dissent` field.
