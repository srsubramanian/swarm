"""Prepare context node — fetches client memory before agent analysis."""

from app.agents.state import SwarmState
from app.services.memory_store import memory_store


async def prepare_context(state: SwarmState) -> dict:
    """Fetch client memory from the memory store and inject into state.

    If the store has memory for this client, it supplements (or replaces)
    the client_memory field passed in the request.
    """
    stored_memory = memory_store.get_memory(state["client_name"])
    if stored_memory:
        # Combine request-provided memory with stored memory
        request_memory = state.get("client_memory", "")
        if request_memory:
            combined = request_memory + "\n\n---\n\n**Stored Memory:**\n" + stored_memory
        else:
            combined = stored_memory
        return {"client_memory": combined}
    return {}
