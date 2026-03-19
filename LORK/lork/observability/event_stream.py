"""
LORK Event Stream
=================

Central event system for the LORK platform.

Every major action emits an event:

task.created
task.started
task.completed
agent.registered
policy.denied
run.step

Events can be consumed by:

monitoring systems
metrics exporters
audit logs
external integrations
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List

logger = logging.getLogger(__name__)


class Event:
    """
    Platform event emitted by LORK.
    """

    def __init__(
        self,
        event_type: str,
        payload: Dict[str, Any],
        source: str = "lork",
    ):
        self.type = event_type
        self.payload = payload
        self.source = source
        self.timestamp = datetime.now(timezone.utc)

    def to_dict(self):
        return {
            "type": self.type,
            "payload": self.payload,
            "source": self.source,
            "timestamp": self.timestamp.isoformat(),
        }


class EventBus:
    """
    In-process event bus.
    """

    def __init__(self):
        self._subscribers: Dict[str, List[Callable]] = {}

    def subscribe(self, event_type: str, handler: Callable):
        """
        Subscribe to events.
        """
        self._subscribers.setdefault(event_type, []).append(handler)

    async def publish(self, event: Event):
        """
        Publish an event to subscribers.
        """
        handlers = self._subscribers.get(event.type, [])

        logger.debug("publishing event %s", event.type)

        await asyncio.gather(
            *(handler(event) for handler in handlers),
            return_exceptions=True,
        )


class EventLogger:
    """
    Logs all events to console.
    """

    async def handle(self, event: Event):
        logger.info(
            "EVENT %s %s",
            event.type,
            event.payload,
        )


class EventRecorder:
    """
    Stores events in memory (useful for debugging).
    """

    def __init__(self):
        self.events: List[Event] = []

    async def handle(self, event: Event):
        self.events.append(event)

    def get_events(self):
        return [e.to_dict() for e in self.events]


def create_default_event_bus():
    """
    Create event bus with default subscribers.
    """

    bus = EventBus()

    logger_handler = EventLogger()
    recorder = EventRecorder()

    bus.subscribe("task.created", logger_handler.handle)
    bus.subscribe("task.started", logger_handler.handle)
    bus.subscribe("task.completed", logger_handler.handle)
    bus.subscribe("agent.registered", logger_handler.handle)

    bus.subscribe("task.created", recorder.handle)
    bus.subscribe("task.started", recorder.handle)
    bus.subscribe("task.completed", recorder.handle)

    return bus
