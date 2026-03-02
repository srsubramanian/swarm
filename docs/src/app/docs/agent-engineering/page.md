---
title: Engineering agent
---

The Engineering Agent is a senior fintech platform engineer that analyzes events for technical integrity, API correctness, SDK health, and system behavior patterns. {% .lead %}

---

## Domain coverage

- **API Integrity** — Request validation, payload structure, idempotency, versioning
- **SDK & Integration Patterns** — Client SDK versions, integration health, deprecation compliance
- **Metadata Validation** — Timestamps, reference IDs, correlation chains, data consistency
- **Rate Limiting & Quotas** — Throughput patterns, burst detection, quota consumption
- **System Behavior** — Latency anomalies, error rate spikes, cascade failure indicators

---

## Analysis framework

For every event, the engineering agent assesses:

1. **Technical Validity** — Is the request well-formed? Are all required fields present and valid?
2. **Integration Context** — Which SDK/API version initiated this? Is it current or deprecated?
3. **System Patterns** — Is the transaction volume/velocity within expected parameters for this client?
4. **Data Consistency** — Do reference IDs, timestamps, and metadata form a coherent chain?
5. **Recommended Action** — Proceed, rate-limit, require resubmission, flag for review, or clear

---

## Implementation

**File:** `backend/app/agents/nodes/engineering.py`

Same implementation pattern as the other agent nodes:

```python
async def engineering_agent(state: SwarmState) -> dict:
    llm = get_llm()
    structured_llm = llm.with_structured_output(AgentAnalysis)
    result = await structured_llm.ainvoke([
        SystemMessage(content=_load_prompt()),
        HumanMessage(content=_format_event(state)),
    ])
    result.agent_role = "engineering"
    return {"analyses": [result]}
```

---

## Output guidelines

The engineering agent is instructed to:

- Provide concrete technical evidence (specific fields, values, version numbers)
- Distinguish between "technically invalid" and "unusual but valid"
- Offer benign technical explanations when compliance or security flags something
- Focus on what the system data actually shows, not hypothetical risks

---

## Example analysis

For a velocity alert of 47 transactions in 3 minutes:

| Field | Value |
|-------|-------|
| **position** | CLEAR — Consistent with known batch ACH pattern |
| **risk_level** | low |
| **confidence** | high |
| **key_findings** | Client is a payroll processor, 47 txns within normal 40-60 range, SDK v3.0 is current |
| **recommended_action** | Proceed — matches established client pattern |

---

## Cross-agent interaction

The engineering agent often provides context that moderates compliance or security concerns:

- A high transaction velocity may be a normal batch payroll run
- A large transfer to an unusual jurisdiction may match the client's documented trade finance patterns
- SDK version and API metadata can confirm or refute automation/bot concerns

When the engineering perspective conflicts with compliance or security, the moderator surfaces the disagreement and lets the RM decide.
