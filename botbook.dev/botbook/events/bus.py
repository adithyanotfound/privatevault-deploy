"""
BotBook Event Bus (in-memory, Kafka-ready)
Replace with aiokafka later without changing callers.
"""

import asyncio
from typing import Dict, Callable, Any

class EventBus:
    def __init__(self):
        self.topics: Dict[str, list[Callable]] = {}

    def subscribe(self, topic: str, handler: Callable):
        self.topics.setdefault(topic, []).append(handler)

    async def publish(self, topic: str, payload: Any):
        handlers = self.topics.get(topic, [])
        for h in handlers:
            asyncio.create_task(h(payload))

bus = EventBus()
