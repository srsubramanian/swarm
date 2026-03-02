---
title: Compliance agent
---

The Compliance Agent is a senior AML/KYC analyst that evaluates business events for regulatory risk, sanctions exposure, and suspicious transaction patterns. It uses investigative tools to gather evidence before forming its assessment. {% .lead %}

---

## Domain coverage

- **Anti-Money Laundering (AML)** — Suspicious transaction patterns, structuring, layering, integration
- **Know Your Customer (KYC)** — Beneficial ownership, PEP screening, adverse media
- **Sanctions** — OFAC, EU, UN sanctions list matches, secondary sanctions exposure
- **Regulatory Reporting** — SAR/STR filing thresholds, CTR requirements, cross-border reporting
- **Transaction Typologies** — Trade-based laundering, mirror trades, rapid movement of funds

---

## Available tools

The compliance agent has access to three investigative tools:

| Tool | Purpose | Example data |
|------|---------|-------------|
| `search_sanctions_list(name, country)` | OFAC/EU/UN sanctions lookup | Returns match scores (0-1), jurisdiction risk level, FATF status |
| `get_client_transaction_history(client_name)` | Recent transaction patterns | Account age, risk rating, flags like `deposits_near_ctr_threshold` |
| `check_regulatory_thresholds(event_type, amount, jurisdiction)` | Regulatory rule checking | CTR thresholds, structuring detection, FATF grey/black list status |

Tools return simulated mock data keyed on the 4 built-in scenarios. For example, `search_sanctions_list("Meridian Holdings", "CY")` returns a partial match (score 0.72) from the EU Consolidated list with "monitored" FATF status, while `check_regulatory_thresholds("cash_deposit", 9800, "US")` triggers the `STRUCTURING_SUSPICION` rule.

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
    return await run_agent_with_tools(
        state=state,
        agent_role="compliance",
        system_prompt=_load_prompt(),
        event_message=_format_event(state),
        tools=COMPLIANCE_TOOLS,
    )
```

The agent delegates to the shared `run_agent_with_tools()` helper which:

1. Loads the compliance prompt template from `agents/prompts/compliance.md`
2. Formats the event data as a structured markdown message
3. Runs a **tool-calling loop** — the LLM calls compliance tools to gather evidence (sanctions checks, transaction history, regulatory thresholds)
4. Makes a final structured output call to extract the `AgentAnalysis`
5. Sets `agent_role` to `"compliance"` and returns the result for the state reducer

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
