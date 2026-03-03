---
title: Memory API
---

The memory endpoints manage per-client persistent memory. Memory accumulates learned behaviors from RM decisions and is injected into agent context for future events involving the same client. All memory updates require RM approval. {% .lead %}

---

## How client memory works

1. An event arrives for a client (e.g., "Meridian Holdings")
2. The `prepare` node fetches stored memory from `ClientMemoryStore`
3. Memory is injected into `state["client_memory"]` — all agents see it
4. After the RM makes a decision, the `post_decision` node proposes a memory update via an LLM call
5. The proposed update is saved as `pending` in the memory store
6. The RM reviews and approves or rejects the proposal
7. Approved updates are merged into the client's memory
8. Next event for the same client benefits from richer context

---

## GET /api/memory/{client_name}

Get the current memory for a client.

### Request

```shell
GET /api/memory/Meridian%20Holdings
```

### Response

```json
{
  "client_name": "Meridian Holdings",
  "memory": "Known client since 2019. Regular EU transfers averaging $500K monthly.",
  "pending_count": 1
}
```

Returns an empty string for `memory` if no memory exists for the client.

---

## GET /api/memory/pending

List all pending memory update proposals across all clients.

### Request

```shell
GET /api/memory/pending
```

### Response

```json
[
  {
    "id": "prop-abc123",
    "client_name": "Meridian Holdings",
    "proposed_content": "Client cleared for $2.4M wire to Cyprus after compliance review. Pattern: large EU transfers are routine for this client.",
    "source_conversation_id": "conv-xyz789",
    "created_at": "2026-03-02T12:50:00+00:00"
  }
]
```

---

## POST /api/memory/pending/{proposal_id}/approve

Approve a pending memory update. The proposed content is merged into the client's memory.

### Request

```shell
POST /api/memory/pending/prop-abc123/approve
```

### Response

```json
{
  "status": "approved",
  "client_name": "Meridian Holdings"
}
```

### Errors

| Status | Description |
|--------|-------------|
| 404 | Proposal not found |

---

## POST /api/memory/pending/{proposal_id}/reject

Reject a pending memory update. The proposal is discarded.

### Request

```shell
POST /api/memory/pending/prop-abc123/reject
```

### Response

```json
{
  "status": "rejected"
}
```

### Errors

| Status | Description |
|--------|-------------|
| 404 | Proposal not found |

---

## ClientMemoryStore

The memory store manages per-client memory with a pending update approval workflow:

```python
class ClientMemoryStore:
    def get_memory(self, client_name: str) -> str:
        """Return current memory markdown for a client."""

    def propose_update(self, client_name, proposed_content, source_conversation_id=None) -> str:
        """Save a pending memory update. Returns proposal_id."""

    def approve_update(self, proposal_id: str) -> bool:
        """Merge proposal into client memory. Returns True on success."""

    def reject_update(self, proposal_id: str) -> bool:
        """Discard proposal. Returns True on success."""

    def list_pending(self) -> list[MemoryProposal]:
        """List all pending memory updates across clients."""
```

The store is currently in-memory (dict-backed). The interface is designed for easy swap to a database-backed implementation.

---

## Memory in the pipeline

### prepare node reads memory

```python
async def prepare_context(state: SwarmState) -> dict:
    stored_memory = memory_store.get_memory(state["client_name"])
    if stored_memory:
        existing = state.get("client_memory", "")
        if existing:
            combined = existing + "\n\n---\n\n**Stored Memory:**\n" + stored_memory
        else:
            combined = stored_memory
        return {"client_memory": combined}
    return {}
```

### post_decision proposes updates

After recording an RM decision, the `post_decision` node calls an LLM with the `memory_update.md` prompt to propose what should be remembered about this client based on the event, analysis, and decision outcome.

---

## Examples

```shell
# Check client memory
curl localhost:3000/api/memory/Meridian%20Holdings

# List pending updates
curl localhost:3000/api/memory/pending

# Approve a pending update
curl -X POST localhost:3000/api/memory/pending/prop-abc123/approve

# Reject a pending update
curl -X POST localhost:3000/api/memory/pending/prop-abc123/reject
```

---

## Implementation

**File:** `backend/app/api/memory.py` — Memory API endpoints.

**File:** `backend/app/services/memory_store.py` — `ClientMemoryStore` with propose/approve/reject workflow.

**File:** `backend/app/agents/prompts/memory_update.md` — Prompt for LLM to propose memory updates.

**File:** `backend/app/agents/nodes/prepare.py` — Reads client memory from store before analysis.

**File:** `backend/app/agents/nodes/post_decision.py` — Proposes memory updates after RM decision.
