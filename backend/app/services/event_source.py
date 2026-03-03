"""Event simulator — generates realistic events on a timer for demo purposes."""

import asyncio
import logging
import random
import uuid

from app.agents.orchestrator import event_graph
from app.agents.scenarios import SCENARIOS
from app.api.conversations import build_input
from app.services.conversation_builder import build_conversation
from app.services.store import conversation_store, thread_store

logger = logging.getLogger(__name__)


class EventSimulator:
    """Generates demo events on a configurable interval."""

    def __init__(self, interval_seconds: float = 30.0):
        self._interval = interval_seconds
        self._task: asyncio.Task | None = None
        self._running = False

    @property
    def running(self) -> bool:
        return self._running

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._loop())
        logger.info("Event simulator started (interval: %.1fs)", self._interval)

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        logger.info("Event simulator stopped")

    async def _loop(self) -> None:
        scenario_names = list(SCENARIOS.keys())
        while self._running:
            try:
                scenario = random.choice(scenario_names)
                await self._submit_event(scenario)
            except Exception:
                logger.exception("Event simulator: error processing event")
            await asyncio.sleep(self._interval)

    async def _submit_event(self, scenario_name: str) -> None:
        """Submit a random scenario through the event graph (with triage)."""
        req = SCENARIOS[scenario_name]
        thread_id = str(uuid.uuid4())
        config = {"configurable": {"thread_id": thread_id}}

        logger.info("Event simulator: submitting '%s' (%s)", req.title, scenario_name)

        result = await event_graph.ainvoke(build_input(req), config=config)

        # Only persist if the triage result was "respond" (full analysis was done)
        triage = result.get("triage_result", "respond")
        if triage == "respond" and result.get("analyses") and result.get("moderator_synthesis"):
            record = build_conversation(req, result["analyses"], result["moderator_synthesis"])
            conversation_store.save(record)
            thread_store.set(record.id, thread_id)
            logger.info(
                "Event simulator: persisted conversation %s (triage: %s)",
                record.id,
                triage,
            )
        else:
            logger.info(
                "Event simulator: triage=%s for '%s', not persisting",
                triage,
                req.title,
            )


# Module-level singleton
event_simulator = EventSimulator()
