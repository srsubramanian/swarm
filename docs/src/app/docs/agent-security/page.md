---
title: Security agent
---

The Security Agent specializes in financial systems threat detection, analyzing events for authentication anomalies, fraud indicators, and infrastructure security risks. It uses investigative tools to look up threat intelligence before forming its assessment. {% .lead %}

---

## Domain coverage

- **Authentication & Authorization** — Session anomalies, credential compromise, privilege escalation
- **Network & API Security** — Unusual access patterns, API abuse, rate limit violations
- **Fraud Indicators** — Account takeover signals, device fingerprint changes, geolocation anomalies
- **Insider Threats** — Unusual employee access patterns, data exfiltration signals
- **Infrastructure Security** — System integrity, configuration drift, vulnerability exposure

---

## Available tools

The security agent has access to three investigative tools:

| Tool | Purpose | Example data |
|------|---------|-------------|
| `lookup_ip_reputation(ip_address)` | Threat intelligence lookup | Threat score (0-100), ISP, VPN/proxy/Tor detection, abuse history |
| `check_geo_velocity(client_name, current_location)` | Impossible travel detection | Distance in miles, min flight hours, time since last login |
| `get_device_fingerprint_history(client_name)` | Device trust assessment | Known/new devices, trust levels, risk indicators |

Tools return simulated mock data keyed on the 4 built-in scenarios. For example, `lookup_ip_reputation("185.220.101.42")` identifies a Tor exit node (threat score 78), while `check_geo_velocity("Atlas Capital", "Istanbul, Turkey")` detects impossible travel (5,013 miles in 6.7 hours from NYC).

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

```python
async def security_agent(state: SwarmState) -> dict:
    return await run_agent_with_tools(
        state=state,
        agent_role="security",
        system_prompt=_load_prompt(),
        event_message=_format_event(state),
        tools=SECURITY_TOOLS,
    )
```

Same pattern as all agent nodes — delegates to the shared `run_agent_with_tools()` helper which runs a tool-calling loop followed by structured extraction.

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
| **key_findings** | New device from Istanbul, 3 failed attempts in 24h, SMS MFA only, Tor exit node IP, impossible travel detected |
| **recommended_action** | Step-up authentication required, block until verified |

---

## Cross-agent interaction

The security agent may disagree with engineering when:

- A technically valid API call comes from a suspicious IP address
- Device fingerprint changes suggest account takeover despite valid credentials
- Rate patterns indicate bot activity even though individual requests are well-formed

These findings are weighted alongside compliance and engineering perspectives by the moderator.
