---
title: Engineering agent
---

The Engineering Agent is a senior fintech platform engineer that analyzes events for technical integrity, API correctness, SDK health, and system behavior patterns. It uses investigative tools to verify technical details before forming its assessment. {% .lead %}

---

## Domain coverage

- **API Integrity** — Request validation, payload structure, idempotency, versioning
- **SDK & Integration Patterns** — Client SDK versions, integration health, deprecation compliance
- **Metadata Validation** — Timestamps, reference IDs, correlation chains, data consistency
- **Rate Limiting & Quotas** — Throughput patterns, burst detection, quota consumption
- **System Behavior** — Latency anomalies, error rate spikes, cascade failure indicators

---

## Available tools

The engineering agent has access to three investigative tools:

| Tool | Purpose | Example data |
|------|---------|-------------|
| `check_sdk_version_status(version)` | SDK lifecycle and CVE check | Status (current/deprecated/EOL), known CVEs, upgrade urgency |
| `get_api_rate_limit_status(client_id)` | Rate limit monitoring | Quota consumption, burst detection, throttling status |
| `validate_transaction_metadata(reference_id)` | Reference ID validation | Format check, duplicate detection, correlation chain |

Tools return simulated mock data keyed on the 4 built-in scenarios. For example, `check_sdk_version_status("2.9.1")` reports end-of-life status with 2 unpatched CVEs (including a critical RCE), while `get_api_rate_limit_status("Quantum Dynamics")` detects a burst pattern classified as "within_limits_but_bursty".

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

```python
async def engineering_agent(state: SwarmState) -> dict:
    return await run_agent_with_tools(
        state=state,
        agent_role="engineering",
        system_prompt=_load_prompt(),
        event_message=_format_event(state),
        tools=ENGINEERING_TOOLS,
    )
```

Same pattern as all agent nodes — delegates to the shared `run_agent_with_tools()` helper.

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
| **key_findings** | Client is a payroll processor, 47 txns within normal 40-60 range, SDK v3.0 deprecated with known CVE, burst detected but within limits |
| **recommended_action** | Proceed — matches established pattern, but flag SDK upgrade needed |

---

## Cross-agent interaction

The engineering agent often provides context that moderates compliance or security concerns:

- A high transaction velocity may be a normal batch payroll run
- A large transfer to an unusual jurisdiction may match the client's documented trade finance patterns
- SDK version and API metadata can confirm or refute automation/bot concerns

When the engineering perspective conflicts with compliance or security, the moderator surfaces the disagreement and lets the RM decide.
