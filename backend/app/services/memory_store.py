"""Per-client memory store with pending update approval."""

import uuid
from datetime import UTC, datetime

from pydantic import BaseModel


class MemoryProposal(BaseModel):
    """A proposed memory update awaiting RM approval."""

    id: str
    client_name: str
    proposed_content: str
    source_conversation_id: str | None = None
    created_at: str
    status: str = "pending"  # "pending" | "approved" | "rejected"


class ClientMemoryStore:
    """Per-client memory with pending update approval.

    In-memory implementation — interface ready for Postgres migration later.
    """

    def __init__(self) -> None:
        self._memories: dict[str, str] = {}
        self._proposals: dict[str, MemoryProposal] = {}

    def get_memory(self, client_name: str) -> str:
        """Return current memory markdown for a client."""
        return self._memories.get(client_name, "")

    def set_memory(self, client_name: str, content: str) -> None:
        """Directly set client memory (used for initial seeding or testing)."""
        self._memories[client_name] = content

    def propose_update(
        self,
        client_name: str,
        proposed_content: str,
        source_conversation_id: str | None = None,
    ) -> str:
        """Save a pending memory update (needs RM approval). Returns proposal_id."""
        proposal_id = str(uuid.uuid4())
        now = datetime.now(UTC).isoformat()
        self._proposals[proposal_id] = MemoryProposal(
            id=proposal_id,
            client_name=client_name,
            proposed_content=proposed_content,
            source_conversation_id=source_conversation_id,
            created_at=now,
        )
        return proposal_id

    def approve_update(self, proposal_id: str) -> bool:
        """RM approves — merge proposal into client memory. Returns True if found."""
        proposal = self._proposals.get(proposal_id)
        if not proposal or proposal.status != "pending":
            return False

        existing = self._memories.get(proposal.client_name, "")
        if existing:
            self._memories[proposal.client_name] = existing + "\n\n" + proposal.proposed_content
        else:
            self._memories[proposal.client_name] = proposal.proposed_content

        proposal.status = "approved"
        return True

    def reject_update(self, proposal_id: str) -> bool:
        """RM rejects — discard proposal. Returns True if found."""
        proposal = self._proposals.get(proposal_id)
        if not proposal or proposal.status != "pending":
            return False
        proposal.status = "rejected"
        return True

    def get_proposal(self, proposal_id: str) -> MemoryProposal | None:
        return self._proposals.get(proposal_id)

    def list_pending(self) -> list[MemoryProposal]:
        """List all pending memory updates across clients."""
        return [p for p in self._proposals.values() if p.status == "pending"]

    def clear(self) -> None:
        """Clear all data (for testing)."""
        self._memories.clear()
        self._proposals.clear()


memory_store = ClientMemoryStore()
