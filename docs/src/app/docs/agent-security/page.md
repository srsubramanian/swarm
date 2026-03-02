---
title: Security agent
---

The Security Agent specializes in financial systems threat detection, analyzing events for authentication anomalies, fraud indicators, and infrastructure security risks. {% .lead %}

---

## Domain coverage

- **Authentication & Authorization** — Session anomalies, credential compromise, privilege escalation
- **Network & API Security** — Unusual access patterns, API abuse, rate limit violations
- **Fraud Indicators** — Account takeover signals, device fingerprint changes, geolocation anomalies
- **Insider Threats** — Unusual employee access patterns, data exfiltration signals
- **Infrastructure Security** — System integrity, configuration drift, vulnerability exposure

---

## Analysis framework

For every event, the security agent assesses:

1. **Authentication Chain** — Is the session valid? Signs of credential compromise or session hijacking?
2. **Behavioral Anomalies** — Does the actor's behavior deviate from their established baseline?
3. **Technical Indicators** — IP reputation, device fingerprint, geolocation consistency, TLS certificate issues
4. **Attack Pattern Matching** — Does this resemble known attacks (credential stuffing, ATO, BEC)?
5. **Recommended Action** — Block, step-up auth, flag for review, monitor, or clear

---

## Implementation

**File:** `backend/app/agents/nodes/security.py`

The security agent follows the same pattern as all agent nodes:

1. Load prompt template from `agents/prompts/security.md`
2. Format the event state as markdown
3. Call the LLM with `AgentAnalysis` structured output
4. Return `{"analyses": [result]}` for the state reducer

---

## Output guidelines

The security agent is instructed to:

- Focus on technical evidence, not speculation
- Distinguish between confirmed indicators and suspicious-but-inconclusive signals
- Push back explicitly if engineering overlooks a security concern
- Rate confidence based on available evidence quality

---

## Example analysis

For a new device login from Istanbul when the client typically logs in from NYC:

| Field | Value |
|-------|-------|
| **position** | HIGH RISK — Geolocation anomaly with failed auth attempts |
| **risk_level** | high |
| **confidence** | high |
| **key_findings** | New device from Istanbul, 3 failed attempts in 24h, SMS MFA only |
| **recommended_action** | Step-up authentication required, block until verified |

---

## Cross-agent interaction

The security agent may disagree with engineering when:

- A technically valid API call comes from a suspicious IP address
- Device fingerprint changes suggest account takeover despite valid credentials
- Rate patterns indicate bot activity even though individual requests are well-formed

These findings are weighted alongside compliance and engineering perspectives by the moderator.
