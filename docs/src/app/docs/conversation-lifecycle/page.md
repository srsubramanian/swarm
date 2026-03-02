---
title: Conversation lifecycle
---

Every event analysis in SwarmOps follows a defined lifecycle from creation through eventual purging. {% .lead %}

---

## Lifecycle stages

```shell
Live → Concluded → Indexed → Archived → Purged
```

### Live

The event is actively being processed. Agents are running, the moderator hasn't synthesized yet, or the RM hasn't made a decision.

- SSE stream is active
- Agent results arrive as `agent_complete` events
- UI shows real-time progress indicators

### Concluded

The RM has made a decision (approve, reject, escalate, or override). The conversation is closed for new agent activity.

- RM's decision is recorded with timestamp
- If overriding, a written justification is required (audit trail)
- Conversation moves to the concluded queue

### Indexed

Knowledge from the conversation is extracted and embedded for future RAG retrieval. This happens via a background ARQ task.

- Key findings are embedded in pgvector
- Client memory update proposals are generated
- Conversation is searchable via vector similarity

### Archived

Message content is moved to S3 for long-term storage. Only metadata remains in PostgreSQL.

- Full message history available via S3 retrieval
- Metadata (risk level, decision, timestamps) stays in Postgres
- Reduces database storage footprint

### Purged

Conversation data is deleted per retention policy. Only aggregate statistics may remain.

---

## Current implementation status

{% callout type="warning" title="Partial implementation" %}
The conversation lifecycle is designed but not yet fully implemented. Currently, the system supports the Live stage through the analyze endpoints. Concluded, Indexed, Archived, and Purged stages require the database models, conversation CRUD, and ARQ background tasks that are on the build roadmap.
{% /callout %}

---

## RM actions at conclusion

When an RM concludes a conversation, they choose from the moderator's action items:

| Action | Description |
|--------|-------------|
| **Approve** | Standard approval, event proceeds |
| **Approve with conditions** | Event proceeds with documented conditions |
| **Reject** | Event is blocked |
| **Escalate** | Routed to a senior reviewer or BSA officer |
| **Override** | RM overrides agent recommendations (requires justification) |

Every action creates an audit trail entry with the RM's identity, timestamp, and rationale.
