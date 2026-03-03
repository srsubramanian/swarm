"""Notify node — lightweight notification for events that don't need full analysis."""

import logging

from app.agents.state import SwarmState

logger = logging.getLogger(__name__)


async def notify_rm(state: SwarmState) -> dict:
    """Log a notification for the RM (future: push to notification queue)."""
    logger.info(
        "RM notification: %s — %s (client: %s)",
        state["event_type"],
        state["title"],
        state["client_name"],
    )
    return {}
