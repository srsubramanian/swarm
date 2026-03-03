"""Memory endpoints — view client memory, approve/reject pending updates."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.memory_store import MemoryProposal, memory_store

router = APIRouter(prefix="/api/memory", tags=["memory"])


class ClientMemoryResponse(BaseModel):
    client_name: str
    content: str


@router.get("/{client_name}", response_model=ClientMemoryResponse)
async def get_client_memory(client_name: str) -> ClientMemoryResponse:
    """Get a client's current memory."""
    content = memory_store.get_memory(client_name)
    return ClientMemoryResponse(client_name=client_name, content=content)


@router.get("/pending", response_model=list[MemoryProposal])
async def list_pending_proposals() -> list[MemoryProposal]:
    """List all pending memory update proposals."""
    return memory_store.list_pending()


@router.post("/pending/{proposal_id}/approve")
async def approve_proposal(proposal_id: str) -> dict:
    """RM approves a memory update — merges into client memory."""
    if not memory_store.approve_update(proposal_id):
        raise HTTPException(status_code=404, detail="Proposal not found or already processed")
    proposal = memory_store.get_proposal(proposal_id)
    return {"status": "approved", "proposal_id": proposal_id, "client_name": proposal.client_name}


@router.post("/pending/{proposal_id}/reject")
async def reject_proposal(proposal_id: str) -> dict:
    """RM rejects a memory update — discards it."""
    if not memory_store.reject_update(proposal_id):
        raise HTTPException(status_code=404, detail="Proposal not found or already processed")
    return {"status": "rejected", "proposal_id": proposal_id}
