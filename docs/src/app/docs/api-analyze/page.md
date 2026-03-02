---
title: POST /api/analyze
---

The synchronous analyze endpoint runs all three agents and the moderator, returning the complete result in a single JSON response. {% .lead %}

---

## Endpoint

```shell
POST /api/analyze
Content-Type: application/json
```

---

## Request body

```json
{
  "event_type": "wire_transfer",
  "title": "$2.4M Wire to Cyprus",
  "client_name": "Meridian Holdings",
  "event_data": {
    "amount": 2400000,
    "currency": "USD",
    "destination_country": "CY",
    "destination_bank": "Bank of Cyprus",
    "reference": "INV-2024-0847"
  },
  "client_memory": "Known client since 2019. Regular EU transfers for trade finance."
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `event_type` | string | Yes | Event category (e.g., `wire_transfer`, `velocity_alert`, `security_alert`, `cash_deposit`) |
| `title` | string | Yes | Human-readable event title |
| `client_name` | string | Yes | Client name |
| `event_data` | object | Yes | Arbitrary event payload — agents interpret this based on `event_type` |
| `client_memory` | string | No | Markdown string with client history and known patterns |

---

## Response

```json
{
  "agents": [
    {
      "agent_role": "compliance",
      "agent_name": "Compliance Analyst",
      "position": "HOLD — elevated jurisdictional risk",
      "analysis": "Detailed markdown analysis...",
      "risk_level": "high",
      "confidence": "high",
      "key_findings": [
        "Transfer to Cyprus (FATF monitored)",
        "Amount 2x typical monthly volume"
      ],
      "recommended_action": "Hold pending enhanced due diligence"
    },
    {
      "agent_role": "security",
      "agent_name": "Security Analyst",
      "position": "...",
      "analysis": "...",
      "risk_level": "medium",
      "confidence": "medium",
      "key_findings": ["..."],
      "recommended_action": "..."
    },
    {
      "agent_role": "engineering",
      "agent_name": "Platform Engineer",
      "position": "...",
      "analysis": "...",
      "risk_level": "low",
      "confidence": "high",
      "key_findings": ["..."],
      "recommended_action": "..."
    }
  ],
  "moderator_summary": {
    "status": "HOLD RECOMMENDED",
    "consensus": "All agents flag elevated risk for this transfer.",
    "dissent": "Engineering notes the client has a history of similar transfers.",
    "risk_level": "high",
    "risk_assessment": "High risk due to jurisdiction and amount.",
    "key_decisions": [
      "Transfer exceeds normal pattern",
      "Cyprus is high-risk jurisdiction"
    ],
    "next_steps": [
      "Hold transfer pending EDD",
      "Request source of funds documentation"
    ],
    "action_items": [
      { "id": "uuid-1", "label": "Hold Transfer", "variant": "primary" },
      { "id": "uuid-2", "label": "Approve with Conditions", "variant": "secondary" },
      { "id": "uuid-3", "label": "Escalate to BSA Officer", "variant": "danger" }
    ]
  }
}
```

---

## Agent roles

| Role | Agent Name | Domain |
|------|-----------|--------|
| `compliance` | Compliance Analyst | AML/KYC/sanctions |
| `security` | Security Analyst | Threats/fraud/auth |
| `engineering` | Platform Engineer | API/SDK/metadata |

---

## Example: velocity alert

```json
{
  "event_type": "velocity_alert",
  "title": "47 Transactions in 3 Minutes",
  "client_name": "Quantum Dynamics",
  "event_data": {
    "transaction_count": 47,
    "time_window_seconds": 180,
    "total_amount": 892000,
    "currency": "USD",
    "transaction_type": "batch_ach"
  },
  "client_memory": "Payroll processor. Monthly batch of 40-60 ACH transactions is normal."
}
```

---

## Example: security alert

```json
{
  "event_type": "security_alert",
  "title": "New Device Login — Atlas Capital",
  "client_name": "Atlas Capital",
  "event_data": {
    "alert_type": "new_device",
    "ip_address": "91.108.56.130",
    "geo_location": "Istanbul, Turkey",
    "device_fingerprint": "d4e5f6a7-new",
    "previous_geo": "New York, NY",
    "failed_attempts_24h": 3,
    "mfa_method": "sms"
  },
  "client_memory": "US-based hedge fund. All prior logins from NYC office."
}
```
