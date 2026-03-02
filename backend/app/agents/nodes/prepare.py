"""Prepare context node — extension point for client memory / RAG lookup."""

from app.agents.state import SwarmState


async def prepare_context(state: SwarmState) -> dict:
    """Passthrough for now. Future: fetch client memory from DB/DynamoDB, run RAG."""
    return {}
