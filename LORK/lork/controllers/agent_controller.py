"""
Agent Controller
================

Continuously reconciles agent state with desired state.

Similar to Kubernetes controllers.
"""

from __future__ import annotations

import asyncio
import logging

from lork.control_plane.agent_registry import AgentRegistry
from lork.models import AgentStatus

logger = logging.getLogger(__name__)


class AgentController:
    def __init__(self, registry: AgentRegistry, interval: int = 10):
        self._registry = registry
        self._interval = interval
        self._running = False

    async def start(self):
        self._running = True
        logger.info("agent controller started")

        while self._running:
            try:
                await self._reconcile()
            except Exception:
                logger.exception("controller reconcile failed")

            await asyncio.sleep(self._interval)

    async def stop(self):
        self._running = False

    async def _reconcile(self):
        """
        Ensure desired agent state matches actual state.
        """
        agents = await self._registry.list("default")

        for agent in agents:
            if agent.status == AgentStatus.PENDING:
                logger.info("auto activating agent %s", agent.id)
                await self._registry.activate(agent.id)
